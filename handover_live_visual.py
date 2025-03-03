from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
from matplotlib.patches import Circle
from matplotlib.lines import Line2D

def animate_cell_mobility(df, resolution=10, interval=200):
    """
    Animate UE mobility between cells based on a DataFrame df with columns:
      time, NrCellId, supi, tac
      
    Each UE is assumed to move in a straight line from the center of one cell
    to the center of the next. A UE’s connection (reflected by a colored circle
    around its marker) changes exactly when the UE crosses the coverage boundary
    of the current cell (coverage radius = 120).
    
    Parameters:
      df         : DataFrame with connection events.
      resolution : Time step in seconds for the animation frames.
      interval   : Delay in milliseconds between frames.
    """
    # Convert the time column to datetime and sort by time
    df['time'] = pd.to_datetime(df['time'])
    df = df.sort_values('time')
    
    # Define cell positions (same as before)
    cells = {
        30: (5, 170),
        40: (5, 5),
        50: (170, 5),
        60: (170, 170)
    }
    coverage_radius = 120  # Each cell's coverage radius

    # Define a color for each cell (for the connection circle)
    cell_colors = {
        30: 'blue',
        40: 'green',
        50: 'orange',
        60: 'purple'
    }
    
    # Create segments for each UE.
    # For each UE (identified by supi), we sort its events by time.
    # Then for each consecutive pair, we assume the UE travels
    # from the center of the start cell to the center of the end cell.
    # We also compute the fraction of the travel at which the UE
    # crosses the coverage boundary of the starting cell.
    segments_by_ue = {}
    ue_ids = df['supi'].unique()
    
    for supi in ue_ids:
        ue_data = df[df['supi'] == supi].sort_values('time').reset_index(drop=True)
        segments = []
        # If a UE has only one event, create a dummy segment (stationary for 1 minute)
        if len(ue_data) == 1:
            row = ue_data.iloc[0]
            t_start = row['time']
            t_end = t_start + pd.Timedelta(minutes=1)
            cell_start = row['NrCellId']
            pos_start = cells[cell_start]
            segments.append({
                'start_time': t_start,
                'end_time': t_end,
                'start_cell': cell_start,
                'end_cell': cell_start,
                'start_pos': pos_start,
                'end_pos': pos_start,
                'handover_fraction': 1.0
            })
        else:
            for i in range(len(ue_data) - 1):
                row_start = ue_data.iloc[i]
                row_end = ue_data.iloc[i+1]
                t_start = row_start['time']
                t_end = row_end['time']
                cell_start = row_start['NrCellId']
                cell_end = row_end['NrCellId']
                pos_start = cells[cell_start]
                pos_end = cells[cell_end]
                # Compute the distance between the cell centers
                dist = np.linalg.norm(np.array(pos_end) - np.array(pos_start))
                # Compute the fraction along the travel when the UE crosses
                # the coverage boundary of the starting cell.
                # If the distance is less than the coverage radius, no handover occurs.
                if dist > 0:
                    f_handover = min(1, coverage_radius / dist)
                else:
                    f_handover = 1.0
                segments.append({
                    'start_time': t_start,
                    'end_time': t_end,
                    'start_cell': cell_start,
                    'end_cell': cell_end,
                    'start_pos': pos_start,
                    'end_pos': pos_end,
                    'handover_fraction': f_handover
                })
        segments_by_ue[supi] = segments

    # Create time frames covering the overall time range
    t_min = df['time'].min()
    t_max = df['time'].max()
    total_seconds = int((t_max - t_min).total_seconds())
    time_frames = [t_min + pd.Timedelta(seconds=s) for s in range(0, total_seconds + 1, resolution)]
    
    # Set up the plot
    fig, ax = plt.subplots(figsize=(10, 10))
    
    # Plot the cells with their coverage areas and centers
    for cell_id, (x, y) in cells.items():
        circle = plt.Circle((x, y), coverage_radius, color=cell_colors.get(cell_id, 'gray'),
                            fill=False, linestyle='--', alpha=0.5)
        ax.add_patch(circle)
        ax.plot(x, y, 'ko')  # cell centers as black dots
        ax.text(x + 5, y + 5, cell_id, color=cell_colors.get(cell_id, 'gray'), fontsize=10)
    
    # For each UE, create two plot elements:
    # 1. A marker for the UE (its own color).
    # 2. A small circle (patch) that will show the color of the cell it's connected to.
    ue_markers = {}
    ue_conn_circles = {}
    cmap = plt.cm.get_cmap('tab10', len(ue_ids))
    ue_colors = {supi: cmap(i) for i, supi in enumerate(ue_ids)}
    
    for supi in ue_ids:
        marker, = ax.plot([], [], marker='o', markersize=10, color=ue_colors[supi],
                            label=f'UE {supi}')
        ue_markers[supi] = marker
        conn_circle = Circle((0, 0), radius=8, color='white', fill=True, alpha=0.5)
        ax.add_patch(conn_circle)
        ue_conn_circles[supi] = conn_circle

    ax.set_xlim(-50, 300)
    ax.set_ylim(-50, 300)
    ax.set_xlabel('X coordinate')
    ax.set_ylabel('Y coordinate')
    ax.set_title('UE Mobility Between Cells Animation')
    ax.grid(True)
    
    # Create a combined legend for cell colors and UE colors.
    cell_handles = [Line2D([0], [0], marker='o', color='w', label=f'Cell {cid}',
                             markerfacecolor=cell_colors[cid], markersize=10)
                    for cid in cell_colors]
    ue_handles = [Line2D([0], [0], marker='o', color='w', label=f'UE {supi}',
                         markerfacecolor=ue_colors[supi], markersize=10)
                  for supi in ue_ids]
    handles = cell_handles + ue_handles
    ax.legend(handles=handles, loc='upper right', fontsize=8)
    
    # Add a text annotation for the current time
    time_text = ax.text(0.02, 0.95, '', transform=ax.transAxes)
    
    def get_position_and_connection(segments, current_time):
        """
        Given a UE's segments and the current time, return:
          - the UE's interpolated position (as an (x,y) tuple)
          - the cell (cell id) the UE is connected to.
        The connection is determined by checking whether the fraction f along the segment
        is less than the handover fraction (f_handover); if so, the UE is still connected
        to the starting cell. Otherwise, it has handed over to the new cell.
        """
        # If current_time is before the first event, use the first event's position.
        if current_time < segments[0]['start_time']:
            return segments[0]['start_pos'], segments[0]['start_cell']
        # If after the last event, use the last event's position.
        if current_time > segments[-1]['end_time']:
            return segments[-1]['end_pos'], segments[-1]['end_cell']
        # Otherwise, find the segment that covers current_time.
        for seg in segments:
            if seg['start_time'] <= current_time <= seg['end_time']:
                total_seg = (seg['end_time'] - seg['start_time']).total_seconds()
                elapsed = (current_time - seg['start_time']).total_seconds()
                f = elapsed / total_seg if total_seg > 0 else 0
                start_pos = np.array(seg['start_pos'])
                end_pos = np.array(seg['end_pos'])
                pos = start_pos + f * (end_pos - start_pos)
                # Determine connection based on the handover fraction.
                if f < seg['handover_fraction']:
                    return pos, seg['start_cell']
                else:
                    return pos, seg['end_cell']
        return segments[-1]['end_pos'], segments[-1]['end_cell']
    
    def update(frame_time):
        time_text.set_text(f"Time: {frame_time.strftime('%Y-%m-%d %H:%M:%S')}")
        for supi in ue_ids:
            segments = segments_by_ue[supi]
            pos, conn_cell = get_position_and_connection(segments, frame_time)
            ue_markers[supi].set_data([pos[0]], [pos[1]])
            # Update the connection circle (position and color).
            ue_conn_circles[supi].center = (pos[0], pos[1])
            ue_conn_circles[supi].set_color(cell_colors.get(conn_cell, 'gray'))
        return list(ue_markers.values()) + list(ue_conn_circles.values()) + [time_text]
    
    anim = animation.FuncAnimation(fig, update, frames=time_frames,
                                   interval=interval, blit=False, repeat=True)
    plt.show()

# Example usage:
# Assuming df_location is your DataFrame with the columns: time, NrCellId, supi, tac.
# For example:
if __name__ == '__main__':
    df_location = pd.read_csv('df_location.csv')
    df_location['time'] = pd.to_datetime(df_location['time'])
    start_time = datetime(2025, 2, 4, 10, 30, 45)
    end_time = datetime(2025, 2, 4, 20, 30, 45)

    # Filter the DataFrame
    df_location = df_location[(df_location['time'] >= start_time) & (df_location['time'] <= end_time)]
    animate_cell_mobility(df_location, resolution=10, interval=10)
