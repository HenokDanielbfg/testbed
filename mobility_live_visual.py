import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np

def animate_mobility(df, start_time, end_time, resolution=60, interval=50, custom_locations=None):
    """
    Animate UE mobility between start_time and end_time.
    
    Parameters:
       df         : Pandas DataFrame with columns: 
                    ['time','supi','location_type','duration','time_of_day','NrCellId']
       start_time : Start time as a string or pd.Timestamp
       end_time   : End time as a string or pd.Timestamp
       resolution : Time step in seconds for the animation frames (default 60 sec)
       interval   : Delay in milliseconds between frames
       custom_locations  : A dictionary mapping (supi, location_type) to (x, y)
                           for 'home' and 'work'. For example:
                           {("208930000000001", "home"): (100, 200),
                            ("208930000000001", "work"): (150, 50),
                            ...}
    """
    # Convert the 'time' column and input times to datetime
    df['time'] = pd.to_datetime(df['time'])
    start_time = pd.to_datetime(start_time)
    end_time   = pd.to_datetime(end_time)
    
    # Filter DataFrame for the desired time period
    df_time = df[(df['time'] >= start_time) & (df['time'] <= end_time)]
    
    # --- Define static elements: cells and fixed places ---
    cells = {
        '000000030': (5, 170),
        '000000040': (5, 5),
        '000000050': (170, 5),
        '000000060': (170, 170)
    }
    coverage_radius = 120  # cell coverage radius

    fixed_places = {
        'gym1': (100.0, 5.0),
        'gym2': (50.0, 140.0),
        'coffee1': (35.0, 40.0),
        'coffee2': (120.0, 64.0),
        'restaurant1': (75.0, 162.5),
        'restaurant2': (63.4, 107.0),
        'leisure1': (4.0, 80.0),
        'leisure2': (171.0, 100.0),
        'cinema': (200.0, 230.0),
        'park': (250.0, 10.0),
        "home1": (90, 90),
        "work1": (105, 105),
        "home2": (80, 80),
        "work2": (95, 95),
        "home3": (70, 70),
        "work3": (104, 104),
        "home4": (60, 60),
        "work4": (45, 45)
    }
    
    # For UEs, 'home' and 'work' are unique; store generated coordinates here.
    home_work_coords = {}
    
    def get_location_coord(supi, location_type):
        """
        Returns the (x,y) coordinate for a given location_type.
        For fixed places, use fixed_places.
        For 'home' or 'work', first check custom_locations (if provided),
        then fall back to generating a random coordinate.
        """
        if location_type in fixed_places:
            return fixed_places[location_type]
        elif location_type in ['home', 'work']:
            key = (supi, location_type)
            print(key)
            if custom_locations is not None and key in custom_locations:
                print("custom location given")
                return custom_locations[key]
            else:
                # If no custom coordinate is provided, generate one (or raise an error if preferred)
                if key not in home_work_coords:
                    print("custom location not given")

                    home_work_coords[key] = tuple(np.random.uniform(0, 300, 2))
                return home_work_coords[key]
        else:
            return None

    # --- Build timeline segments for each UE ---
    # For each event, we create:
    #   1. A stationary segment: from arrival until departure (arrival + duration)
    #   2. A moving segment: from departure of the current event until the next arrival, 
    #      with linear interpolation between locations.
    segments_by_ue = {}
    ue_ids = df_time['supi'].unique()
    
    for supi in ue_ids:
        ue_data = df_time[df_time['supi'] == supi].sort_values('time').reset_index(drop=True)
        segments = []
        for i in range(len(ue_data)):
            row = ue_data.iloc[i]
            arrival = row['time']
            # departure = arrival + pd.Timedelta(seconds=row['duration'])
            departure = arrival + pd.Timedelta(seconds=int(row['duration']))

            coord = get_location_coord(supi, row['location_type'])
            # Stationary segment at the location
            segments.append({
                'start': arrival,
                'end': departure,
                'start_coord': coord,
                'end_coord': coord,
                'type': 'stationary'
            })
            # If there's a subsequent event, add a moving segment for travel
            if i < len(ue_data) - 1:
                next_arrival = ue_data.iloc[i+1]['time']
                next_coord = get_location_coord(supi, ue_data.iloc[i+1]['location_type'])
                # Only add a moving segment if there is a gap between departure and next arrival
                if departure < next_arrival:
                    segments.append({
                        'start': departure,
                        'end': next_arrival,
                        'start_coord': coord,
                        'end_coord': next_coord,
                        'type': 'moving'
                    })
        segments_by_ue[supi] = segments

    def get_position(segments, current_time):
        """
        Given the segments for a UE and the current time, compute the UE's position.
        If the UE is stationary, return the fixed coordinate.
        If moving, interpolate linearly between start_coord and end_coord.
        If current_time is before the first event or after the last, return the nearest coordinate.
        """
        for seg in segments:
            if seg['start'] <= current_time <= seg['end']:
                if seg['type'] == 'stationary':
                    return seg['start_coord']
                else:
                    # Calculate interpolation fraction between seg['start'] and seg['end']
                    fraction = (current_time - seg['start']).total_seconds() / (seg['end'] - seg['start']).total_seconds()
                    x = seg['start_coord'][0] + fraction * (seg['end_coord'][0] - seg['start_coord'][0])
                    y = seg['start_coord'][1] + fraction * (seg['end_coord'][1] - seg['start_coord'][1])
                    return (x, y)
        # If current_time is before the first event, return the first known coordinate;
        # if after the last event, return the last coordinate.
        if segments:
            if current_time < segments[0]['start']:
                return segments[0]['start_coord']
            elif current_time > segments[-1]['end']:
                return segments[-1]['end_coord']
        return None

    # --- Create a list of time frames (with the given resolution in seconds) ---
    total_seconds = int((end_time - start_time).total_seconds())
    time_frames = [start_time + pd.Timedelta(seconds=s) for s in range(0, total_seconds + 1, resolution)]
    
    # --- Prepare the plot ---
    fig, ax = plt.subplots(figsize=(10, 10))
    
    # Plot cells with their coverage areas
    for cell_id, (x, y) in cells.items():
        circle = plt.Circle((x, y), coverage_radius, color='blue', fill=False, linestyle='--')
        ax.add_patch(circle)
        ax.plot(x, y, 'bo')
        ax.text(x + 5, y + 5, cell_id, color='blue', fontsize=10)
        
    # Plot fixed places
    for place, (x, y) in fixed_places.items():
        ax.plot(x, y, marker='*', color='red', markersize=12)
        ax.text(x + 2, y + 2, place, color='red', fontsize=9)
    
    # Setup scatter plots for UEs – one marker per UE.
    scatters = {}
    colors = plt.cm.get_cmap('tab10', len(ue_ids))
    for i, supi in enumerate(ue_ids):
        scatter, = ax.plot([], [], marker='o', markersize=10, color=colors(i), label=f'UE {supi}')
        scatters[supi] = scatter
        
    ax.set_xlim(-50, 300)
    ax.set_ylim(-50, 300)
    ax.set_xlabel('X coordinate')
    ax.set_ylabel('Y coordinate')
    ax.set_title(f'UE Mobility Animation\n{start_time.strftime("%Y-%m-%d %H:%M:%S")} to {end_time.strftime("%Y-%m-%d %H:%M:%S")}')
    ax.grid(True)
    ax.legend(loc='upper right', fontsize=8)
    
    # Text annotation to show the current time in the animation
    time_text = ax.text(0.02, 0.95, '', transform=ax.transAxes)
    
    # --- Update function for the animation ---
    def update(frame_time):
    # Update the time annotation
        time_text.set_text(f'Time: {frame_time.strftime("%Y-%m-%d %H:%M:%S")}')
        # For each UE, update its position based on the current time
        for supi in ue_ids:
            pos = get_position(segments_by_ue[supi], frame_time)
            if pos is not None:
                # Wrap the coordinates in lists to satisfy the set_data requirements
                scatters[supi].set_data([pos[0]], [pos[1]])
        return list(scatters.values()) + [time_text]

    
    # Create the animation
    anim = animation.FuncAnimation(fig, update, frames=time_frames, interval=interval, blit=True, repeat=True)
    plt.show()



if __name__ == '__main__':
    df_loc_des = pd.read_csv('df_loc_des.csv')
    # df_loc_des = df_loc_des[df_loc_des['supi']==208930000000004]
    custom_locations = {
        (208930000000001, 'home'): (90, 90),
        (208930000000001, 'work'): (105, 105),
        (208930000000002, 'home'): (80, 80),
        (208930000000002, 'work'): (95, 95),
        (208930000000003, 'home'): (70, 70),
        (208930000000003, 'work'): (104, 104),
        (208930000000004, 'home'): (60, 60),
        (208930000000004, 'work'): (45, 45)
    }
    animate_mobility(df_loc_des, "2025-02-07 10:00:00", "2025-02-07 20:00:00", custom_locations=custom_locations)






import pandas as pd
# import matplotlib.pyplot as plt
# import matplotlib.animation as animation
# import numpy as np
# from matplotlib.patches import Circle

# def animate_mobility(df, df_cell, start_time, end_time, resolution=60, interval=200, custom_locations=None):
#     """
#     Animate UE mobility and display a colored circle around each UE to indicate the connected cell.
    
#     Parameters:
#        df              : Pandas DataFrame with mobility data columns: 
#                          ['time','supi','location_type','duration','time_of_day','NrCellId'] 
#                          (for the UE’s geographic movement)
#        df_cell         : Pandas DataFrame with cell connectivity data columns:
#                          ['time','NrCellId','supi','tac']
#        start_time      : Start time as a string or pd.Timestamp
#        end_time        : End time as a string or pd.Timestamp
#        resolution      : Time step in seconds for the animation frames (default 60 sec)
#        interval        : Delay in milliseconds between frames
#        custom_locations: Dictionary mapping (supi, location_type) to (x,y) for 'home' and 'work'
#                          e.g., {("208930000000001", "home"): (120, 250), ...}
#     """
#     # --- Convert time columns to datetime ---
#     df['time'] = pd.to_datetime(df['time'])
#     df_cell['time'] = pd.to_datetime(df_cell['time'])
#     start_time = pd.to_datetime(start_time)
#     end_time   = pd.to_datetime(end_time)
    
#     # --- Filter both DataFrames for the time period ---
#     df_time = df[(df['time'] >= start_time) & (df['time'] <= end_time)]
#     df_cell_time = df_cell[(df_cell['time'] >= start_time) & (df_cell['time'] <= end_time)]
    
#     # --- Define static elements: cells and fixed places ---
#     cells = {
#         '000000030': (5, 170),
#         '000000040': (5, 5),
#         '000000050': (170, 5),
#         '000000060': (170, 170)
#     }
#     coverage_radius = 120  # radius for cell coverage circles

#     fixed_places = {
#         'gym1': (100.0, 5.0),
#         'gym2': (50.0, 140.0),
#         'coffee1': (35.0, 40.0),
#         'coffee2': (120.0, 64.0),
#         'restaurant1': (75.0, 162.5),
#         'restaurant2': (63.4, 107.0),
#         'leisure1': (4.0, 80.0),
#         'leisure2': (171.0, 100.0),
#         'cinema': (200.0, 230.0),
#         'park': (250.0, 10.0)
#     }
    
#     # --- Define colors for cells ---
#     cell_colors = {
#         '30': 'blue',
#         '40': 'green',
#         '50': 'orange',
#         '60': 'purple'
#     }
    
#     # --- For UEs, set up home and work coordinates ---
#     home_work_coords = {}
#     def get_location_coord(supi, location_type):
#         """
#         Return the (x,y) coordinate for a given location.
#         For fixed places, use fixed_places.
#         For 'home' or 'work', check custom_locations first; otherwise fall back to a random coordinate.
#         """
#         if location_type in fixed_places:
#             return fixed_places[location_type]
#         elif location_type in ['home', 'work']:
#             key = (supi, location_type)
#             if custom_locations is not None and key in custom_locations:
#                 return custom_locations[key]
#             else:
#                 if key not in home_work_coords:
#                     home_work_coords[key] = tuple(np.random.uniform(0, 300, 2))
#                 return home_work_coords[key]
#         else:
#             return None

#     # --- Build mobility segments for each UE (for geographic positions) ---
#     segments_by_ue = {}
#     ue_ids = df_time['supi'].unique()
    
#     for supi in ue_ids:
#         ue_data = df_time[df_time['supi'] == supi].sort_values('time').reset_index(drop=True)
#         segments = []
#         for i in range(len(ue_data)):
#             row = ue_data.iloc[i]
#             arrival = row['time']
#             departure = arrival + pd.Timedelta(seconds=float(row['duration']))
#             coord = get_location_coord(supi, row['location_type'])
#             # Stationary segment at the location
#             segments.append({
#                 'start': arrival,
#                 'end': departure,
#                 'start_coord': coord,
#                 'end_coord': coord,
#                 'type': 'stationary'
#             })
#             # Add a moving segment if there is a subsequent event
#             if i < len(ue_data) - 1:
#                 next_arrival = ue_data.iloc[i+1]['time']
#                 next_coord = get_location_coord(supi, ue_data.iloc[i+1]['location_type'])
#                 if departure < next_arrival:
#                     segments.append({
#                         'start': departure,
#                         'end': next_arrival,
#                         'start_coord': coord,
#                         'end_coord': next_coord,
#                         'type': 'moving'
#                     })
#         segments_by_ue[supi] = segments

#     def get_position(segments, current_time):
#         """
#         Given a list of segments for a UE and the current time, return its geographic position.
#         If moving, interpolate between start and end coordinates.
#         """
#         for seg in segments:
#             if seg['start'] <= current_time <= seg['end']:
#                 if seg['type'] == 'stationary':
#                     return seg['start_coord']
#                 else:
#                     fraction = (current_time - seg['start']).total_seconds() / (seg['end'] - seg['start']).total_seconds()
#                     x = seg['start_coord'][0] + fraction * (seg['end_coord'][0] - seg['start_coord'][0])
#                     y = seg['start_coord'][1] + fraction * (seg['end_coord'][1] - seg['start_coord'][1])
#                     return (x, y)
#         # Before or after the segments:
#         if segments:
#             if current_time < segments[0]['start']:
#                 return segments[0]['start_coord']
#             elif current_time > segments[-1]['end']:
#                 return segments[-1]['end_coord']
#         return None

#     # --- Build cell connectivity segments for each UE from df_cell_time ---
#     segments_by_cell = {}
#     ue_ids_cell = df_cell_time['supi'].unique()
#     for supi in ue_ids_cell:
#         ue_cell_data = df_cell_time[df_cell_time['supi'] == supi].sort_values('time').reset_index(drop=True)
#         segments = []
#         for i in range(len(ue_cell_data)):
#             row = ue_cell_data.iloc[i]
#             event_time = row['time']
#             cell_id = row['NrCellId']
#             if i < len(ue_cell_data) - 1:
#                 next_time = ue_cell_data.iloc[i+1]['time']
#             else:
#                 next_time = end_time
#             segments.append({
#                 'start': event_time,
#                 'end': next_time,
#                 'cell': cell_id
#             })
#         segments_by_cell[supi] = segments

#     def get_connected_cell(segments, current_time):
#         """
#         Given cell connectivity segments for a UE and a time,
#         return the cell id to which the UE is connected.
#         """
#         for seg in segments:
#             if seg['start'] <= current_time <= seg['end']:
#                 return seg['cell']
#         if segments:
#             if current_time < segments[0]['start']:
#                 return segments[0]['cell']
#             elif current_time > segments[-1]['end']:
#                 return segments[-1]['cell']
#         return None

#     # --- Create time frames for the animation ---
#     total_seconds = int((end_time - start_time).total_seconds())
#     time_frames = [start_time + pd.Timedelta(seconds=s) for s in range(0, total_seconds + 1, resolution)]
    
#     # --- Prepare the plot ---
#     fig, ax = plt.subplots(figsize=(10, 10))
    
#     # Plot cells with their coverage areas
#     for cell_id, (x, y) in cells.items():
#         circle = plt.Circle((x, y), coverage_radius, color='blue', fill=False, linestyle='--')
#         ax.add_patch(circle)
#         ax.plot(x, y, 'bo')
#         ax.text(x + 5, y + 5, cell_id, color='blue', fontsize=10)
        
#     # Plot fixed places
#     for place, (x, y) in fixed_places.items():
#         ax.plot(x, y, marker='*', color='red', markersize=12)
#         ax.text(x + 2, y + 2, place, color='red', fontsize=9)
    
#     # --- Prepare markers and colored circles for each UE ---
#     markers = {}
#     circles = {}  # these circles will have their edge color updated based on connected cell
#     for supi in ue_ids:
#         # Create a marker for the UE (e.g., a black dot)
#         marker, = ax.plot([], [], marker='o', markersize=10, color='black')
#         markers[supi] = marker
#         # Create a circle patch around the marker; adjust radius as needed
#         circ = Circle((0, 0), radius=10, fill=False, lw=2, edgecolor='black')
#         ax.add_patch(circ)
#         circles[supi] = circ
        
#     ax.set_xlim(-50, 300)
#     ax.set_ylim(-50, 300)
#     ax.set_xlabel('X coordinate')
#     ax.set_ylabel('Y coordinate')
#     ax.set_title(f'UE Mobility Animation\n{start_time.strftime("%Y-%m-%d %H:%M:%S")} to {end_time.strftime("%Y-%m-%d %H:%M:%S")}')
#     ax.grid(True)
#     ax.legend(loc='upper right', fontsize=8)
    
#     # Add a time annotation text
#     time_text = ax.text(0.02, 0.95, '', transform=ax.transAxes)
    
#     def update(frame_time):
#         time_text.set_text(f'Time: {frame_time.strftime("%Y-%m-%d %H:%M:%S")}')
#         for supi in ue_ids:
#             pos = get_position(segments_by_ue[supi], frame_time)
#             if pos is not None:
#                 # Update marker position
#                 markers[supi].set_data([pos[0]], [pos[1]])
#                 # Update the corresponding circle's center
#                 circles[supi].center = pos
#                 # Determine the cell connectivity (if available) and update the circle's edge color
#                 if supi in segments_by_cell:
#                     cell_id = get_connected_cell(segments_by_cell[supi], frame_time)
#                     print(cell_id)
#                     color = cell_colors.get(str(cell_id))
#                     print(color)
#                     circles[supi].set_edgecolor(color)
#                 else:
#                     circles[supi].set_edgecolor('black')
#         return list(markers.values()) + list(circles.values()) + [time_text]
    
#     anim = animation.FuncAnimation(fig, update, frames=time_frames, interval=interval, blit=False, repeat=True)
#     plt.show()