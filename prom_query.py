# prometheus_query.py

import ast
from datetime import datetime, timedelta
import os
import pandas as pd
import requests
from prometheus_api_client import PrometheusConnect

PROMETHEUS_URL = "http://localhost:9090"  # or wherever your Prometheus is hosted

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
    start_time= datetime(2025, 1, 17, 11, 30, 45)
    # end_time= datetime(2025, 1, 24, 11, 30, 45)
    prom = PrometheusConnect(url=PROMETHEUS_URL, disable_ssl=True)
    # Perform a range query using the supplied arguments
    response = prom.custom_query_range(
        query=query,
        start_time=start_time,
        end_time=end_time,
        step='10m'  # You can adjust the interval as needed
    )

    # Convert the response into a list of dictionaries
    records = []
    if query == 'UE_location_report':
        for entry in response:
            metric = entry['metric']
            record = {
                'time': metric.get('time'),  # or wherever you store your timestamp
                'NrCellId': metric.get('NrCellId'),
                'supi': metric.get('supi'),
                'tac': metric.get('tac')
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

        # Reset index after sorting
        df = df.reset_index(drop=True)
        df = df.to_json()
        return df
        
    elif query == 'active_UEs':
        for entry in response[0]['values']:
            record = {
                'time': datetime.fromtimestamp(entry[0]).strftime("%Y-%m-%d %H:%M:%S.%f +0000 UTC"),
                'active_UEs': entry[1]
            }
            records.append(record)
        
    elif query == 'amf_ue_registration_state':
        for metric in response:
            # Extract SUPI from metric metadata
            supi = metric['metric'].get('supi')
            for entry in metric['values']:
                record = {
                    'time': datetime.fromtimestamp(entry[0]).strftime("%Y-%m-%d %H:%M:%S.%f +0000 UTC"),
                    'supi': supi,
                    'state': entry[1]
                }
                records.append(record)
        
    elif query == 'ue_destination_visits_total':
        for entry in response:
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
    # print(records)
    return records
if __name__ == "__main__":
    print(query_prometheus('amf_ue_registration_state'))
    # query_prometheus('amf_ue_registration_state')

