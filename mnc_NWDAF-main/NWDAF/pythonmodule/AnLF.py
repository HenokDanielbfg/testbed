from collections import defaultdict
from datetime import datetime

import pandas as pd
from sklearn.calibration import LabelEncoder
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.model_selection import train_test_split
from Model import *
import os.path
from prometheus_api_client import PrometheusConnect
from datetime import timedelta
from sklearn.pipeline import Pipeline
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score

PROMETHEUS_URL = "http://localhost:9090"
prom = PrometheusConnect(url=PROMETHEUS_URL, disable_ssl=True)




###################### Handover prediction ######################
def get_df_location(start_time=None, end_time=datetime.now()):   #  endtime set on 24th Jan 2025 at 11:30:45
    # Query Prometheus
    start_time=end_time - timedelta(days=10)
    metric_data = prom.custom_query_range(
        query='UE_location_report',
        start_time=start_time,
        end_time=end_time,
        step='10m'  # 1 minute intervals, adjust as needed
    )
    
    # Process the data into a list of dictionaries
    records = []
    for entry in metric_data:
        metric = entry['metric']
        # Extract only the desired labels
        record = {
            'time': metric['time'],
            'NrCellId': metric['NrCellId'],
            'supi': metric['supi'],
            'tac': metric['tac']
            
        }
        records.append(record)
    
    # Convert to DataFrame
    df = pd.DataFrame(records)

    # Convert time string to datetime
    # Remove 'UTC' and trailing timezone info for clean parsing
    df['time'] = df['time'].apply(lambda x: pd.to_datetime(x.split('+')[0].strip()))
    # Sort by 'supi' and 'time'
    
    df = df.sort_values(by=['supi', 'time'])
    # Drop consecutive rows with the same 'supi' and 'NrCellId'
    df = df.loc[
        ~(df['supi'] == df['supi'].shift()) | 
        ~(df['NrCellId'] == df['NrCellId'].shift())
    ]
    
    # Sort by time
    df = df.sort_values('time')
    df['time'] = df['time'] + pd.Timedelta(hours=4)
    df['supi'] = df['supi'].str.extract(r'imsi-(\d+)').astype(str)

    # Reset index after sorting
    df = df.reset_index(drop=True)
    
    return df

def predict_ue_location(target_ue):
    # Load the dataset
    df = get_df_location()
    # Convert the 'time' column to datetime
    df['time'] = pd.to_datetime(df['time'])

    # Extract the hour from the timestamp
    df['hour'] = df['time'].dt.hour
    # df['minute'] = df['time'].dt.minute
    # Define the time-of-day function
    def get_time_of_day(hour):
        if hour >= 7 and hour < 11:
            return 1#"MORNING"
        elif hour >= 11 and hour < 14:
            return 2#"LUNCH"
        elif hour >= 14 and hour < 17:
            return 3#"AFTERNOON"
        elif hour >= 17 and hour < 24:
            return 4#"EVENING"
        return 5#"NIGHT"
    df['time_of_day'] = df['hour'].apply(get_time_of_day)
    # Mapping of NrCellId to XY coordinates
    # cell_coords = {30: (5, 170), 40: (5, 5), 50: (170, 5), 60: (170, 170)}
    df = df.sort_values(by=['supi', 'time']) 
    # Add columns for the previous two cells (GNBs) each UE was connected to 
    df['prev_cell_1'] = df.groupby('supi')['NrCellId'].shift(1) 
    df['prev_cell_2'] = df.groupby('supi')['NrCellId'].shift(2)
    cell_freq = df.groupby(['supi', 'prev_cell_1','time_of_day']).size().reset_index(name='frequency') 
    df = pd.merge(df, cell_freq, on=['supi', 'prev_cell_1','time_of_day'], how='left') 
    # Drop rows where next_cell is missing (last record per subscriber) 
    df_model = df.dropna(subset=['prev_cell_1','prev_cell_2']).copy()
    # Define features and target 
    features = ['supi', 'frequency', 'prev_cell_1', 'prev_cell_2', 'time_of_day']
    target = 'NrCellId' 
    X = df_model[features] 
    y = df_model[target]   
    model = GradientBoostingClassifier(n_estimators=100, max_depth=9, subsample=1.0, learning_rate=0.05, random_state=42)
    # Split the data into training and testing sets (using stratification) 
    X_train, X_test, y_train, y_test = train_test_split( 
    X, y, test_size=0.2, random_state=42)  
    pipeline = Pipeline([('clf', model)]) 
    pipeline.fit(X_train, y_train)    
    latest = (
        df_model.loc[df_model['supi'] == target_ue]
                .sort_values('time')
                .tail(1)          # newest record
    )

    if latest.empty or latest[['prev_cell_1', 'prev_cell_2']].isna().any(axis=None):
        raise ValueError("Need at least two historical cells for this UE.")
    latest['prev_cell_2'] = latest['prev_cell_1']   # push old lag-1 into lag-2
    latest['prev_cell_1'] = latest['NrCellId']      # current cell becomes lag-1
    X_new = latest[features] 
    # Predict the next cell
    next_cell = pipeline.predict(X_new)[0]
    return {
        'predicted_cell': next_cell,
        'target_ue': target_ue
    }


# def predict_ue_location(target_ue, target_time):

#     data = get_df_location()
#     # Convert time to datetime
#     data['time'] = pd.to_datetime(data['time'])
#     data['hour'] = data['time'].dt.hour
#     # df['minute'] = df['time'].dt.minute
#     # Define the time-of-day function
#     def get_time_of_day(hour):
#         if hour >= 7 and hour < 11:
#             return 1#"MORNING"
#         elif hour >= 11 and hour < 14:
#             return 2#"LUNCH"
#         elif hour >= 14 and hour < 17:
#             return 3#"AFTERNOON"
#         elif hour >= 17 and hour < 24:
#             return 4#"EVENING"
#         return 5#"NIGHT"
#     # Filter data for specific UE
#     ue_data = data[data['supi'] == target_ue].copy()
#     # Extract hour from timestamp
#     ue_data['hour'] = ue_data['time'].dt.hour
    
#     # # Create time windows 
#     # def get_time_window(hour):
#     #     if 5 <= hour < 11: return 'morning'
#     #     elif 11 <= hour < 14: return 'lunch'
#     #     elif 14 <= hour < 17: return 'afternoon'
#     #     elif 17 <= hour < 24: return 'evening'
#     #     else: return 'night'
    
#     ue_data['time_window'] = ue_data['hour'].apply(get_time_window)
    
#     # Calculate probabilities for each cell during each time window
#     time_window_probs = defaultdict(lambda: defaultdict(int))
    
#     for window in ['morning', 'lunch', 'afternoon', 'evening', 'night']:
#         window_data = ue_data[ue_data['time_window'] == window]
#         total_records = len(window_data)
#         if total_records > 0:
#             cell_counts = window_data['NrCellId'].value_counts()
#             for cell in cell_counts.index:
#                 time_window_probs[window][cell] = cell_counts[cell] / total_records
    
#     # Get time window for target time
#     target_dt = datetime.strptime(target_time, '%Y-%m-%d %H:%M:%S')
#     target_window = get_time_window(target_dt.hour)
    
#     # Get probabilities for target time window
#     cell_probs = time_window_probs[target_window]
    
#     if not cell_probs:
#         return "Insufficient data for prediction"
    
#     # Get most likely cell
#     most_likely_cell = max(cell_probs.items(), key=lambda x: x[1])
#     # display(ue_data)
    
#     return {
#         'predicted_cell': most_likely_cell[0],
#         'confidence': most_likely_cell[1],
#         'all_probabilities': dict(cell_probs)
#     }


###################### registration/deregistration time prediction ######################

def get_df_reg(start_time=None, end_time=datetime.now()):   
    
    # Query Prometheus - filter for metrics with SUPI label
    query = 'amf_ue_registration_state{supi=~".+"}'
    result = prom.custom_query_range(
        query=query,
        start_time=start_time,
        end_time=end_time,
        step='5m' # 5 minute intervals, adjust as needed
    )
    
    # Convert to DataFrame
    dataframes = []
    
    if result:
        for metric in result:
            # Extract SUPI from metric metadata
            supi = metric['metric'].get('supi', 'unknown')
            
            # Create DataFrame for this SUPI
            df = pd.DataFrame(metric['values'], columns=['timestamp', 'state'])
            df['supi'] = supi
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            df['state'] = pd.to_numeric(df['state'])
            
            # Keep only state changes
            df = df[df['state'].shift() != df['state']]
            
            dataframes.append(df)
    
    if dataframes:
        # Combine all SUPIs into one DataFrame
        final_df = pd.concat(dataframes, ignore_index=True)
        
        # Sort by timestamp
        final_df = final_df.sort_values('timestamp')
        
      
        
        # Add state description
        final_df['state_desc'] = final_df['state'].map({1: 'active', 0: 'inactive'})
        
        # Reorder columns
        final_df = final_df[['timestamp', 'supi', 'state', 'state_desc']]#, 'duration_minutes']]
        final_df = final_df.drop('state', axis=1)
        final_df = final_df.sort_values(by=['supi', 'timestamp'])

        # Calculate duration in minutes
        final_df['duration_minutes'] = (
            final_df.groupby('supi')['timestamp'].diff().shift(-1).dt.total_seconds() / 60
        )
        final_df = final_df.sort_values(by='timestamp')
        final_df['timestamp'] = final_df['timestamp'] + pd.Timedelta(hours=4)
        # Reset index after sorting
        final_df = final_df.reset_index(drop=True)
    
        return final_df
    else:
        return pd.DataFrame(columns=['timestamp', 'supi', 'state', 'state_desc', 'duration_minutes'])

def predict_duration(supi):
    data = get_df_reg()
    # Drop rows where 'duration_minutes' is NaN for training purposes
    train_data = data.dropna(subset=['duration_minutes']).copy()
    # Use loc to set the index column
    train_data.loc[:, 'index'] = train_data.index
    grouped = train_data.groupby(['supi', 'state_desc'])
    models = {}
    for (supi, state), group in grouped:
        X = group['index'].values.reshape(-1, 1)  # Using index as the feature
        y = group['duration_minutes']
        model = LinearRegression()
        model.fit(X, y)
        models[(supi, state)] = model
    # Find the most recent entry for the specified supi
    last_entry = data[data['supi'] == supi].iloc[-1]
    if pd.isna(last_entry['duration_minutes']):
        model_key = (supi, last_entry['state_desc'])
        if model_key in models:
            # Predict using the index of the last entry
            index_value = last_entry.name
            predicted_duration = models[model_key].predict(np.array([[index_value]]))[0]
            return {'supi': supi,
                    'current_state': last_entry['state_desc'],
                    'predicted_duration': predicted_duration}
        else:
            return "No model available for this supi and state combination"
    else:
        return "Last entry already has a duration value"

###################### Active UE count prediction ######################

def get_df_active(start_time=None, end_time=datetime.now()):
    
    
    # Query Prometheus
    query = 'active_UEs{state="current"}'
    result = prom.custom_query_range(
        query=query,
        start_time=start_time,
        end_time=end_time,
        step='5m'  # 30 minute intervals, adjust as needed
    )
    
    # Convert to DataFrame
    if result and len(result) > 0:
        # Extract timestamps and values
        data = result[0]['values']  # values is a list of [timestamp, value] pairs
        df = pd.DataFrame(data, columns=['timestamp', 'active_UEs'])
        
        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
        
        # Convert active_UEs to numeric
        df['active_UEs'] = pd.to_numeric(df['active_UEs'])

        # Remove duplicate consecutive values
        df = df[df['active_UEs'].shift() != df['active_UEs']]
        df['duration'] = (df['timestamp'].shift(-1) - df['timestamp']).fillna(pd.Timedelta(seconds=0))

        # Reset index after sorting
        df = df.reset_index(drop=True)
        df['timestamp'] = df['timestamp'] + pd.Timedelta(hours=4)

        return df
    else:
        return pd.DataFrame(columns=['timestamp', 'active_UEs'])

def predict_ActiveUE_count():
    data = get_df_active()
    data['timestamp'] = pd.to_datetime(data['timestamp'])
    data['duration'] = pd.to_timedelta(data['duration'])

    # Feature engineering
    data['hour_of_day'] = data['timestamp'].dt.hour
    data['minute_of_hour'] = data['timestamp'].dt.minute
    data['day_of_week'] = data['timestamp'].dt.dayofweek

    # Prepare target variables
    duration_seconds = data['duration'].dt.total_seconds()
    label_encoder = LabelEncoder()
    active_ues_encoded = label_encoder.fit_transform(data['active_UEs'])

    # Split the dataset into training and testing sets
    X = data[['hour_of_day', 'minute_of_hour', 'day_of_week']]
    y_duration = duration_seconds
    y_active_ues = active_ues_encoded

    X_train, X_test, y_duration_train, y_duration_test, y_active_ues_train, y_active_ues_test = train_test_split(
        X, y_duration, y_active_ues, test_size=0.2, random_state=42)

    # Initialize the models
    model_duration = LinearRegression()
    model_active_ues = LogisticRegression(max_iter=500)  # Increase max_iter if needed for convergence

    # Train the models
    model_duration.fit(X_train, y_duration_train)
    model_active_ues.fit(X_train, y_active_ues_train)

    # Predicting the next entry
    next_timestamp_features = pd.DataFrame({
            'hour_of_day': [data['hour_of_day'].iloc[-1]],
            'minute_of_hour': [data['minute_of_hour'].iloc[-1]],
            'day_of_week': [data['day_of_week'].iloc[-1]]
        })
    predicted_duration_seconds = model_duration.predict(next_timestamp_features)
    predicted_active_ues = label_encoder.inverse_transform(model_active_ues.predict(next_timestamp_features).reshape(-1))

    # Calculate the next timestamp by adding the predicted duration to the last timestamp
    last_timestamp = data['timestamp'].iloc[-1]
    predicted_duration_timedelta = pd.to_timedelta(predicted_duration_seconds[0], unit='s')
    predicted_next_timestamp = last_timestamp + predicted_duration_timedelta
    return {'predicted_duration': predicted_duration_timedelta,
                    'predicted_Timestamp': predicted_next_timestamp,
                    'predicted_Active_UEs': predicted_active_ues[0]}