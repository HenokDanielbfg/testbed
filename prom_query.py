# prometheus_query.py

import ast
from datetime import datetime, timedelta
import os
import pandas as pd
import requests
from prometheus_api_client import PrometheusConnect

PROMETHEUS_URL = "http://localhost:9090"  # or wherever your Prometheus is hosted
prom = PrometheusConnect(url=PROMETHEUS_URL, disable_ssl=True)

def extract_metric_name(promql):
    # List of valid metric names
    valid_metrics = {
        'active_UEs',
        'amf_ue_registration_state',
        'ue_destination_visits_total',
        'UE_location_report'
    }
    
    # Split the query string and look for valid metrics
    for word in promql.split('('):
        word = word.strip(')')  # Remove closing parenthesis
        if word in valid_metrics:
            return word
            
    # If no valid metric found
    raise ValueError(f"No valid metric name found in query: {promql}. Valid metrics are: {', '.join(valid_metrics)}")

def query_prometheus(promql) -> list:
    """
    Query Prometheus with a PromQL query string (range query) 
    and return a list of records with the same structure as before.
    
    :param query: A valid PromQL query for range queries.
    :param start_time: The datetime object for the start of the query range.
    :param end_time:   The datetime object for the end of the query range.
    :return: A list of dictionaries, each containing 'time', 'NrCellId', 'supi', and 'tac'.
    """
    # queryProm = ast.literal_eval(promql)
    print("I have accessed the query_prometheus function")
    
    query = extract_metric_name(promql)#queryProm['query']
    print(query)

    
    end_time= datetime.now()
    start_time= datetime(2025, 3, 3, 8, 30, 45)
    # end_time= datetime(2025, 1, 24, 11, 30, 45)
    # prom = PrometheusConnect(url=PROMETHEUS_URL, disable_ssl=True)


    if query == 'UE_location_report':
        return get_df_location(start_time, end_time)
    elif query == 'active_UEs':
        return get_df_active(start_time, end_time)
    elif query == 'amf_ue_registration_state':
        return get_reg(start_time, end_time)
    elif query == 'ue_destination_visits_total':
        return get_df_destination(start_time, end_time)




    # # Perform a range query using the supplied arguments
    # response = prom.custom_query_range(
    #     query=query,
    #     start_time=start_time,
    #     end_time=end_time,
    #     step='10m'  # You can adjust the interval as needed
    # )

    # # Convert the response into a list of dictionaries
    # records = []
    
    # if query == 'UE_location_report':
    #     for entry in response:
    #         metric = entry['metric']
    #         record = {
    #             'time': metric.get('time'),  # or wherever you store your timestamp
    #             'NrCellId': metric.get('NrCellId'),
    #             'supi': metric.get('supi'),
    #             'tac': metric.get('tac')
    #         }
    #         records.append(record)
    #     # Convert to DataFrame
    #     df = pd.DataFrame(records)

    #     # Convert time string to datetime
    #     # Remove 'UTC' and trailing timezone info for clean parsing
    #     df['time'] = df['time'].apply(lambda x: pd.to_datetime(x.split('+')[0].strip()))
    #     # Sort by 'supi' and 'time'
        
    #     df = df.sort_values(by=['supi', 'time'])
    #     # Drop consecutive rows with the same 'supi' and 'NrCellId'
    #     df = df.loc[
    #         ~(df['supi'] == df['supi'].shift()) | 
    #         ~(df['NrCellId'] == df['NrCellId'].shift())
    #     ]
    #     # df_location = df_location.sort_values('time')

    #     # # Reset the index if needed
    #     # df_location = df_location.reset_index(drop=True)
    #     # Sort by time
    #     df = df.sort_values('time')
    #     df['time'] = df['time'] + pd.Timedelta(hours=4)
    #     df['supi'] = df['supi'].str.extract(r'imsi-(\d+)').astype(str)

    #     # Reset index after sorting
    #     df = df.reset_index(drop=True)
    #     df = df.to_json()
    #     return df
        
    # elif query == 'active_UEs':
    #     for entry in response[0]['values']:
    #         record = {
    #             'time': datetime.fromtimestamp(entry[0]).strftime("%Y-%m-%d %H:%M:%S.%f +0000 UTC"),
    #             'active_UEs': entry[1]
    #         }
    #         records.append(record)
        
    # elif query == 'amf_ue_registration_state':
    #     for metric in response:
    #         # Extract SUPI from metric metadata
    #         supi = metric['metric'].get('supi')
    #         for entry in metric['values']:
    #             record = {
    #                 'time': datetime.fromtimestamp(entry[0]).strftime("%Y-%m-%d %H:%M:%S.%f +0000 UTC"),
    #                 'supi': supi,
    #                 'state': entry[1]
    #             }
    #             records.append(record)
        
    # elif query == 'ue_destination_visits_total':
    #     for entry in response:
    #         metric = entry['metric']
    #         # Extract only the desired labels
    #         record = {
    #             'time': metric['timestamp'],
    #             'supi': metric['supi'],
    #             'location_type': metric['location_type'],
    #             'duration': metric['duration'],
    #             'time_of_day': metric['time_of_day']
    #         }
    #         records.append(record)
    # # print(records)
    # return records




def get_df_location(start_time=None, end_time=None):
    # Query Prometheus
    query='UE_location_report'
    metric_data = prom.custom_query_range(
        query=query,
        start_time=start_time,
        end_time=end_time,
        step='5m'  # 1 minute intervals, adjust as needed
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
    # df_location = df_location.sort_values('time')

    # # Reset the index if needed
    # df_location = df_location.reset_index(drop=True)
    # Sort by time
    df = df.sort_values('time')
    df['time'] = df['time'] + pd.Timedelta(hours=4)
    df['supi'] = df['supi'].str.extract(r'imsi-(\d+)').astype(str)
    df['time'] = df['time'].dt.strftime('%Y-%m-%d %H:%M:%S')
    # Reset index after sorting
    df = df.reset_index(drop=True)
    
    return df.to_json()
def get_df_destination(start_time=None, end_time=None):
    # Query Prometheus
    metric_data = prom.custom_query_range(
        query='ue_destination_visits_total',
        start_time=start_time,
        end_time=end_time,
        step='5m'  # 1 minute intervals, adjust as needed
    )
    
    # Process the data into a list of dictionaries
    records = []
    for entry in metric_data:
        metric = entry['metric']
        # Extract only the desired labels
        record = {
            'time': metric['timestamp'],
            'supi': metric['supi'],
            'location_type': metric['location_type'],
            'duration': metric['duration'],
            'time_of_day': metric['time_of_day']
        }
        records.append(record)
    
    # Convert to DataFrame
    df = pd.DataFrame(records)

    # Convert time string to datetime
    # Remove 'UTC' and trailing timezone info for clean parsing
    df['time'] = df['time'].apply(lambda x: pd.to_datetime(x.split('+')[0].strip()))


    df = df.sort_values(by=['supi', 'time'])
    # Drop consecutive rows with the same 'supi' and 'NrCellId'
    df = df.loc[
        ~(df['supi'] == df['supi'].shift()) | 
        ~(df['location_type'] == df['location_type'].shift())
    ]
    
    # Sort by time
    df = df.sort_values('time')
    df['time'] = df['time'].dt.strftime('%Y-%m-%d %H:%M:%S')
    # Reset index after sorting
    df = df.reset_index(drop=True)
    
    return df.to_json()


def get_df_active(start_time=None, end_time=None):
    
    
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
        df['timestamp'] = df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')

        return df.to_json()
    else:
        return pd.DataFrame(columns=['timestamp', 'active_UEs']).to_json()

def get_reg(start_time=None, end_time=None):
    
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
        df['timestamp'] = df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')

        return final_df.to_json()
    else:
        return pd.DataFrame(columns=['timestamp', 'supi', 'state', 'state_desc', 'duration_minutes']).to_json()


if __name__ == "__main__":
    print(query_prometheus('active_UEs'))
    # query_prometheus('amf_ue_registration_state')

