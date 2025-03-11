import json
import requests
import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
api_key = os.getenv('API_KEY')
client = OpenAI(api_key=api_key)

def load_intent_prompts(file_path):
    intent_categories = {}
    category = None
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            line = line.strip()
            if line.startswith('##'):
                category = line.strip('#').strip()
                intent_categories[category] = []
            elif category and line:
                intent_categories[category].append(line.split('. ', 1)[-1])  # Remove numbering
    return intent_categories

intent_file_path = "intent prompts.txt"
test_file_path = "test_prompts2.txt"
intent_categories = load_intent_prompts(intent_file_path)
test_intents = load_intent_prompts(test_file_path) 

def get_best_intent_match(user_query):
    """ Use OpenAI to find the best matching intent """
    all_intents = [intent for category, intents in intent_categories.items() for intent in intents]
    intent_list_prompt = "\n".join([f"{intent}" for intent in all_intents])
    prompt = (
        "You are an intent matching assistant. Given a user query, select the most relevant intent from the list below.\n\n"
        "User Query: " + user_query + "\n\n"
        "Available Intents:\n" + intent_list_prompt + "\n\n"
        "STRICT REQUIREMENT.Return the best matching intent exactly as it appears in the Available Intents, Do not add any extra text, letter, number, hyphen, dot or anything.This is very Important"
    )
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": "You match user queries to predefined intents."},
                  {"role": "user", "content": prompt}],
    )
    best_match = response.choices[0].message.content.strip()
    
    for category, intents in intent_categories.items():
        if best_match in intents:
            return best_match, category
    
    return best_match, None

def test_intent_matching():
    total_tests = 0
    correct_matches = 0
    mismatches = []
    
    total_queries = sum(len(test_queries) for test_queries in test_intents.values())
    processed_queries = 0
    
    for category, test_queries in test_intents.items():
        for query in test_queries:
            total_tests += 1
            predicted_intent, predicted_category = get_best_intent_match(query)
            if predicted_category == category:
                correct_matches += 1
                print(f"correct matches are {correct_matches}")
            else:
                mismatches.append((query, predicted_intent, predicted_category, category))
                print(f"incorrect matches are {len(mismatches)}")
                print(f"Query: {query}\nbest match: {predicted_intent}\nPredicted: {predicted_category} | Actual: {category}\n")
            processed_queries += 1
            if processed_queries % 10 == 0 or processed_queries == total_queries:
                print(f"Progress: {processed_queries}/{total_queries} queries processed...")
    
    accuracy = (correct_matches / total_tests) * 100 if total_tests > 0 else 0
    
    
    if mismatches:
        print("\nMismatched Cases:")
        for query, intent, predicted, actual in mismatches:
            print(f"Query: {query}\nbest match: {intent}\nPredicted: {predicted} | Actual: {actual}\n")
    print(f"\nIntent Matching Accuracy: {accuracy:.2f}%")
    print(f"Total Tests: {total_tests}, Correct Matches: {correct_matches}, Mismatches: {len(mismatches)}")
if __name__ == "__main__":
    test_intent_matching()









# import json
# import sys
# import requests
# import os
# import re
# from openai import OpenAI
# from prom_query import query_prometheus
# from dotenv import load_dotenv

# # Load environment variables
# load_dotenv()
# api_key = os.getenv('API_KEY')
# client = OpenAI(api_key=api_key)

# # Load intent prompts into a dictionary without numbering
# def load_intent_prompts(file_path):
#     intent_categories = {}
#     category = None
#     with open(file_path, 'r', encoding='utf-8') as file:
#         for line in file:
#             line = line.strip()
#             if line.startswith('##'):
#                 category = line.strip('#').strip()
#                 intent_categories[category] = []
#             elif category and line:
#                 clean_intent = re.sub(r'^\d+\.\s*', '', line)  # Remove numbering
#                 intent_categories[category].append(clean_intent)
#     return intent_categories

# intent_file_path = "intent prompts.txt"
# intent_categories = load_intent_prompts(intent_file_path)

# def get_best_intent_match(user_query):
#     """ Use OpenAI to find the best matching intent """
#     all_intents = [intent for category, intents in intent_categories.items() for intent in intents]
#     intent_list_prompt = "\n".join([f"- {intent}" for intent in all_intents])  # Ensure no numbering
#     prompt = (
#         "You are an intent matching assistant. Given a user query, select the most relevant intent from the list below.\n\n"
#         "User Query: " + user_query + "\n\n"
#         "Available Intents:\n" + intent_list_prompt + "\n\n"
#         "Return only the best matching intent exactly as it appears in the list, without adding numbers or extra text."
#     )
    
#     response = client.chat.completions.create(
#         model="gpt-4o",
#         messages=[{"role": "system", "content": "You match user queries to predefined intents."},
#                   {"role": "user", "content": prompt}],
#     )
#     best_match = response.choices[0].message.content.strip()
    
#     # Find the category of the matched intent
#     for category, intents in intent_categories.items():
#         if best_match in intents:
#             return best_match, category
    
#     return None, None

# def nwdaf_subscription_command(action, target):
#     """ Send NWDAF subscription command """
#     nwdaf_url = "http://127.0.0.71:8001/nwdaf/command"
#     payload = {"action": action, "target": target}
#     response = requests.post(nwdaf_url, json=payload)
#     return response.json()

# def process_user_query(user_query):
#     best_intent, category = get_best_intent_match(user_query)
#     if not best_intent:
#         return {"error": "No matching intent found."}
    
#     print(f"Matched Intent: {best_intent} (Category: {category})")
    
#     # Map category to function calls
#     if "Subscribe" in category:
#         target = "amf" if "AMF" in category else "smf"
#         function_result = nwdaf_subscription_command("subscribe", target)
#     elif "Unsubscribe" in category:
#         target = "amf" if "AMF" in category else "smf"
#         function_result = nwdaf_subscription_command("unsubscribe", target)
#     elif "Active_UEs" in category:
#         function_result = query_prometheus("active_UEs")
#     elif "UE_location_report" in category:
#         function_result = query_prometheus("UE_location_report")
#     elif "Registration State" in category:
#         function_result = query_prometheus("amf_ue_registration_state")
#     elif "ue_destination_visits_total" in category:
#         function_result = query_prometheus("ue_destination_visits_total")
#     else:
#         return {"error": "Unknown category match."}
    
#     # Feed the function result back into OpenAI for interpretation
#     messages = [
#         {"role": "system", "content": "You are a helpful assistant that interprets network analytics and subscription responses."},
#         {"role": "user", "content": user_query},
#         {"role": "function", "name": "function_result", "content": json.dumps(function_result)}
#     ]
#     second_response = client.chat.completions.create(
#         model="gpt-4o",
#         messages=messages
#     )
#     return second_response.choices[0].message.content

# if __name__ == "__main__":
#     while True:
#         try:
#             user_question = input("\nEnter your query (Ctrl+C to exit): ")
#             if not user_question.strip():
#                 continue
            
#             response = process_user_query(user_question)
#             print("Response:", response)
#         except KeyboardInterrupt:
#             print("\nExiting...")
#             sys.exit(0)
