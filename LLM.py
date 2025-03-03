import json
import sys
import requests
from openai import OpenAI
from prom_query import query_prometheus
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv('API_KEY')
# Your OpenAI API key and client setup
client = OpenAI(api_key=api_key)

# Function spec for querying Prometheus (analytics)
function_spec_prometheus = {
    "name": "query_prometheus",
    "description": "Query Prometheus with PromQL and return the raw JSON response.",
    "parameters": {
        "type": "object",
        "properties": {
            "promql": {
                "type": "string",
                "description": "Metric name to query in Prometheus (one of: 'active_UEs', 'amf_ue_registration_state', 'ue_destination_visits_total', 'UE_location_report')."
            }
        },
        "required": ["promql"]
    }
}

# New function spec for NWDAF subscription commands
function_spec_subscription = {
    "name": "nwdaf_subscription_command",
    "description": "Perform subscription or unsubscription for NWDAF events. Accepts an action ('subscribe' or 'unsubscribe') and a target ('amf' or 'smf').",
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["subscribe", "unsubscribe"],
                "description": "The action to perform: subscribe or unsubscribe."
            },
            "target": {
                "type": "string",
                "enum": ["amf", "smf"],
                "description": "The target NF: amf or smf."
            }
        },
        "required": ["action", "target"]
    }
}

def nwdaf_subscription_command(action, target):
    """
    Call NWDAF's command endpoint to perform subscribe/unsubscribe actions.
    Ensure that your NWDAF service exposes a REST endpoint (e.g., /nwdaf/command) to handle these commands.
    """
    nwdaf_url = "http://127.0.0.71:8001/nwdaf/command"  # Replace with the actual NWDAF address.
    payload = {"action": action, "target": target}
    response = requests.post(nwdaf_url, json=payload)
    print(action, target)
    # return {"status": "success", "action": action, "target": target}
    return response.json()

def run_llm_conversation(user_message):
    # Build the conversation messages with both function specs
    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful assistant that can either generate PromQL queries to answer metrics questions "
                "or issue NWDAF subscription commands. When a user query is about analytics metrics, select one of "
                "the four metrics: 'active_UEs', 'amf_ue_registration_state', 'ue_destination_visits_total', 'UE_location_report' "
                "and call the function query_prometheus. When the query is about subscribing or unsubscribing NWDAF events, "
                "call the function nwdaf_subscription_command with parameters 'action' (subscribe/unsubscribe) and 'target' (amf/smf)."
                "When a user query is about analytics metrics, select one of "
                "the four metrics: 'active_UEs', 'amf_ue_registration_state', 'ue_destination_visits_total', 'UE_location_report' "
                "and call the function query_prometheus to get the relevant data needed to make the analytics. You have access to a function called `query_prometheus` that takes ONLY a simple metric name as input. "
                "there are 4 query metrics: 'active_UEs' (tracks number of active UEs), 'amf_ue_registration_state' (current registration state of UEs), 'ue_destination_visits_total' (exact locations visited by UEs), 'UE_location_report' (GNB handover reports of UEs). "
                "\n‼️ STRICT REQUIREMENT FOR QUERY PARAMETER ‼️\n"
                "The query parameter must be EXACTLY one of these four metric names without any labels, filters, or modifications:\n"
                "1. 'active_UEs'\n"
                "2. 'amf_ue_registration_state'\n"
                "3. 'ue_destination_visits_total'\n"
                "4. 'UE_location_report'\n"
                "\nEXAMPLES:\n"
                "CORRECT: query_prometheus(query='UE_location_report')\n"
                "INCORRECT: query_prometheus(query='UE_location_report{supi=\"208930000000004\"}')\n"
                "INCORRECT: query_prometheus(query='count(UE_location_report)')\n"
                "\nDo not add any labels, functions, or modifiers to the metric name. The function only accepts the raw metric name."
                "When the user asks about metrics, select the most appropriate metric from the four options above and pass ONLY the metric name. "
                "The query_prometheus function will handle all filtering and processing internally."
            )
        },
        {
            "role": "user",
            "content": user_message
        },
    ]

    response = client.chat.completions.create(
        model="gpt-4o-mini",  # or 'gpt-3.5-turbo-0613'
        messages=messages,
        functions=[function_spec_prometheus, function_spec_subscription],
        function_call="auto"
    )
    response_dict = response.to_dict()
    response_message = response_dict["choices"][0]["message"]

    if response_message.get("function_call"):
        function_name = response_message["function_call"]["name"]
        function_args_json = response_message["function_call"]["arguments"]
        function_args = json.loads(function_args_json)

        if function_name == "query_prometheus":
            try:
                prom_result = query_prometheus(**function_args)
                # print(prom_result)
                messages.append(response_message)
                messages.append({
                    "role": "function",
                    "name": function_name,
                    "content": json.dumps(prom_result)
                })
                second_response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages
                )
                return second_response.choices[0].message.content
            except Exception as e:
                error_message = {
                    "role": "function",
                    "name": function_name,
                    "content": json.dumps({"error": str(e), "status": "failed"})
                }
                messages.append(response_message)
                # print(response_message)
                # print(error_message)
                messages.append(error_message)
                error_response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages
                )
                return error_response.choices[0].message.content

        elif function_name == "nwdaf_subscription_command":
            try:
                sub_result = nwdaf_subscription_command(**function_args)
                messages.append(response_message)
                messages.append({
                    "role": "function",
                    "name": function_name,
                    "content": json.dumps(sub_result)
                })
                second_response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages
                )
                return second_response.choices[0].message.content
            except Exception as e:
                error_message = {
                    "role": "function",
                    "name": function_name,
                    "content": json.dumps({"error": str(e), "status": "failed"})
                }
                messages.append(response_message)
                messages.append(error_message)
                error_response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages
                )
                return error_response.choices[0].message.content

    else:
        # If no function call is returned, just relay the LLM's plain text answer.
        return response_message["content"]

if __name__ == "__main__":
    while True:
        try:
            user_question = input("\nEnter your question (Ctrl+C to exit): ")
            print("User question:", user_question)
            if not user_question.strip():
                continue

            answer = run_llm_conversation(user_question)
            print("LLM Answer:", answer)
        except KeyboardInterrupt:
            print("\nExiting the program...")
            sys.exit(0)































# from openai import OpenAI
# import json
# import sys
# from prom_query import query_prometheus
# #henokdaniel678
# api_key = "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"

# #henokbfg
# # api_key = "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"
# client = OpenAI(api_key="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")



# # 1. Define a JSON schema for the function arguments
# function_spec = {
#     "name": "query_prometheus",
#     "description": "Query Prometheus with PromQL and return the raw JSON response.",
#     "parameters": {
#         "type": "object",
#         "properties": {
#             "promql": {
#                 "type": "string",
#                 "description": "metric name to query in Prometheus"
#             }
#         },
#         "required": ["promql"]
#     }
# }

# def run_llm_conversation(user_message):
#     # 2. We’ll build a chat message array with a system instruction
#     messages = [
#         {
#             "role": "system",
#             "content": (
#                 "You are a helpful assistant that can generate PromQL queries to answer metrics questions. "
#                 "You have access to a function called `query_prometheus` that takes ONLY a simple metric name as input. "
#                 "there are 4 query metrics: 'active_UEs' (tracks number of active UEs), 'amf_ue_registration_state' (current registration state of UEs), 'ue_destination_visits_total' (exact locations visited by UEs), 'UE_location_report' (GNB handover reports of UEs). "
#                 "\n‼️ STRICT REQUIREMENT FOR QUERY PARAMETER ‼️\n"
#                 "The query parameter must be EXACTLY one of these four metric names without any labels, filters, or modifications:\n"
#                 "1. 'active_UEs'\n"
#                 "2. 'amf_ue_registration_state'\n"
#                 "3. 'ue_destination_visits_total'\n"
#                 "4. 'UE_location_report'\n"
#                 "\nEXAMPLES:\n"
#                 "CORRECT: query_prometheus(query='UE_location_report')\n"
#                 "INCORRECT: query_prometheus(query='UE_location_report{supi=\"208930000000004\"}')\n"
#                 "INCORRECT: query_prometheus(query='count(UE_location_report)')\n"
#                 "\nDo not add any labels, functions, or modifiers to the metric name. The function only accepts the raw metric name."
#                 "When the user asks about metrics, select the most appropriate metric from the four options above and pass ONLY the metric name. "
#                 "The query_prometheus function will handle all filtering and processing internally."
#             )
#         },
#         {
#             "role": "user",
#             "content": user_message
#         },
#     ]

#     # 3. Call the OpenAI ChatCompletion endpoint with the function spec
#     response = client.chat.completions.create(model="gpt-4o-mini",  # or 'gpt-3.5-turbo-0613'
#     messages=messages,
#     functions=[function_spec],
#     function_call="auto" ) # let the model decide when to call the function)

#     # 4. Check if the model wants to call the function
#     # response_message = response.choices[0].message

#     # Convert the response to a dict explicitly (or use response.to_dict() in some versions)
#     response_dict = response.to_dict()

#     response_message = response_dict["choices"][0]["message"]


#     if response_message.get("function_call"):
#         # The model wants to call the function with certain arguments
#         function_name = response_message["function_call"]["name"]
#         function_args_json = response_message["function_call"]["arguments"]
#         function_args = json.loads(function_args_json)

#         if function_name == "query_prometheus":
#             try:
#                 # 4a. Call local function
#                 prom_result = query_prometheus(**function_args)
#                 # 4b. Feed result back to model
#                 messages.append(response_message)
#                 messages.append({
#                     "role": "function",
#                     "name": function_name,
#                     "content": json.dumps(prom_result)
#                 })
#                 # 5. Let model interpret the JSON
#                 second_response = client.chat.completions.create(
#                     model="gpt-4o-mini",
#                     messages=messages
#                 )
#                 print("successfully called the function")
#                 return second_response.choices[0].message.content
                
#             except Exception as e:
#                 # Handle the error
#                 error_message = {
#                     "role": "function",
#                     "name": function_name,
#                     "content": json.dumps({
#                         "error": str(e),
#                         "status": "failed"
#                     })
#                 }
#                 messages.append(response_message)
#                 messages.append(error_message)
#                 print(error_message)
#                 # Let the model handle the error response
#                 error_response = client.chat.completions.create(
#                     model="gpt-4o-mini",
#                     messages=messages
#                 )
#                 print("did not successfully call the function")

#                 return error_response.choices[0].message.content
#     else:
#         # No function call; just return whatever the LLM said
#         return response_message["content"]


# if __name__ == "__main__":
#     # Example user prompt
#     # user_question = (
#     #     "Out of the four cells, which one cell does supi 208930000000004 frequent? Use 'UE_location_report' metric"
#     # )
#     # answer = run_llm_conversation(user_question)
#     # print("LLM Answer:", answer)
#     while True:
#         try:
#             user_question = input("\nEnter your question (Ctrl+C to exit): ")
#             # If user presses Enter without typing anything, just ignore and re-prompt
#             print("User question:", user_question)
#             if not user_question.strip():
#                 continue
            
#             answer = run_llm_conversation(user_question)
#             print("LLM Answer:", answer)
#         except KeyboardInterrupt:
#             print("\nExiting the program...")
#             sys.exit(0)


