import json
import os
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from dotenv import load_dotenv
from openai import OpenAI

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
test_file_path = "test_prompts.txt"
intent_categories = load_intent_prompts(intent_file_path)
test_intents = load_intent_prompts(test_file_path) 

# Create global variables to store all intents and their categories
all_intents = []
all_categories = []
intent_to_category = {}
intent_embeddings = None

# Generate embeddings using OpenAI Embeddings API
def get_embedding(text):
    response = client.embeddings.create(
        input=text,
        model="text-embedding-ada-002"  # or "text-embedding-3-small" 
    )
    return response.data[0].embedding

# Generate and store embeddings for all intents
def prepare_intent_embeddings():
    global all_intents, all_categories, intent_to_category, intent_embeddings
    
    # Collect all intents and their categories
    for category, intents in intent_categories.items():
        for intent in intents:
            all_intents.append(intent)
            all_categories.append(category)
            intent_to_category[intent] = category
    
    # Generate embeddings for all intents
    print(f"Generating embeddings for {len(all_intents)} intents...")
    intent_embeddings = []
    
    # Process in batches to avoid rate limits
    batch_size = 20
    for i in range(0, len(all_intents), batch_size):
        batch = all_intents[i:i+batch_size]
        batch_response = client.embeddings.create(
            input=batch,
            model="text-embedding-ada-002"
        )
        batch_embeddings = [item.embedding for item in batch_response.data]
        intent_embeddings.extend(batch_embeddings)
        print(f"Processed {i+len(batch)}/{len(all_intents)} intents")
    
    intent_embeddings = np.array(intent_embeddings)
    print(f"Generated embeddings for {len(all_intents)} intents")

def get_best_intent_match_rag(user_query):
    """Use RAG approach to find the best matching intent"""
    # Get query embedding
    query_embedding = get_embedding(user_query)
    
    # Calculate similarity with all intents
    similarities = cosine_similarity([query_embedding], intent_embeddings)[0]
    
    # Get most similar intent
    best_idx = np.argmax(similarities)
    best_match = all_intents[best_idx]
    best_score = similarities[best_idx]
    
    # Find the category of the matched intent
    category = intent_to_category.get(best_match)
    
    # Get top 3 matches for logging/debugging
    top_indices = similarities.argsort()[-3:][::-1]
    top_intents = [all_intents[idx] for idx in top_indices]
    top_scores = [similarities[idx] for idx in top_indices]
    top_matches = list(zip(top_intents, top_scores))
    
    return best_match, category, best_score, top_matches

def test_intent_matching():
    # Prepare embeddings first
    prepare_intent_embeddings()
    
    total_tests = 0
    correct_matches = 0
    mismatches = []
    
    # Track confidence scores for analysis
    confidence_scores = []
    
    total_queries = sum(len(test_queries) for test_queries in test_intents.values())
    processed_queries = 0
    
    for category, test_queries in test_intents.items():
        for query in test_queries:
            total_tests += 1
            predicted_intent, predicted_category, confidence, top_matches = get_best_intent_match_rag(query)
            confidence_scores.append(confidence)
            
            if predicted_category == category:
                correct_matches += 1
                print(f"✓ Correct match #{correct_matches}: Score={confidence:.4f}")
            else:
                mismatches.append((query, predicted_intent, predicted_category, category, confidence, top_matches))
                print(f"✗ Incorrect match #{len(mismatches)}: Score={confidence:.4f}")
                print(f"Query: {query}")
                print(f"Predicted: {predicted_intent} ({predicted_category})")
                print(f"Actual: {category}")
                print(f"Top matches: {top_matches}\n")
            
            processed_queries += 1
            if processed_queries % 10 == 0 or processed_queries == total_queries:
                print(f"Progress: {processed_queries}/{total_queries} queries processed...")
    
    accuracy = (correct_matches / total_tests) * 100 if total_tests > 0 else 0
    
    # Analyze confidence scores
    avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
    median_confidence = sorted(confidence_scores)[len(confidence_scores)//2] if confidence_scores else 0
    correct_confidences = [score for i, score in enumerate(confidence_scores) 
                          if i < (correct_matches)]
    incorrect_confidences = [m[4] for m in mismatches]
    
    avg_correct_conf = sum(correct_confidences) / len(correct_confidences) if correct_confidences else 0
    avg_incorrect_conf = sum(incorrect_confidences) / len(incorrect_confidences) if incorrect_confidences else 0
    
    print("\nIntent Matching Performance:")
    print(f"Average confidence score: {avg_confidence:.4f}")
    print(f"Median confidence score: {median_confidence:.4f}")
    print(f"Average confidence for correct matches: {avg_correct_conf:.4f}")
    print(f"Average confidence for incorrect matches: {avg_incorrect_conf:.4f}")
    
    if mismatches:
        print("\nMismatched Cases:")
        for query, intent, predicted, actual, conf, top in mismatches:
            print(f"Query: {query}")
            print(f"Predicted: {intent} ({predicted}), Confidence: {conf:.4f}")
            print(f"Actual: {actual}")
            print(f"Top matches: {top}\n")
    
    print(f"\nIntent Matching Accuracy: {accuracy:.2f}%")
    print(f"Total Tests: {total_tests}, Correct Matches: {correct_matches}, Mismatches: {len(mismatches)}")
    
    # Suggest confidence threshold based on results
    if correct_confidences and incorrect_confidences:
        print("\nConfidence Score Analysis:")
        possible_thresholds = [0.85, 0.88, 0.9, 0.92, 0.95]
        for threshold in possible_thresholds:
            above_threshold = sum(1 for score in confidence_scores if score >= threshold)
            correct_above = sum(1 for score in correct_confidences if score >= threshold)
            if above_threshold > 0:
                precision_at_threshold = correct_above / above_threshold
                recall_at_threshold = correct_above / len(correct_confidences) if correct_confidences else 0
                print(f"Threshold {threshold}: Precision={precision_at_threshold:.2f}, " +
                      f"Recall={recall_at_threshold:.2f}, Coverage={above_threshold/len(confidence_scores):.2f}")

# Add a hybrid version that uses both embeddings and GPT-4o for classification
def get_best_intent_match_hybrid(user_query, top_k=5):
    """Use RAG approach with GPT-4o to find the best matching intent"""
    # Get query embedding
    query_embedding = get_embedding(user_query)
    
    # Calculate similarity with all intents
    similarities = cosine_similarity([query_embedding], intent_embeddings)[0]
    
    # Get top_k most similar intents
    top_indices = similarities.argsort()[-top_k:][::-1]
    top_intents = [all_intents[idx] for idx in top_indices]
    top_scores = [similarities[idx] for idx in top_indices]
    
    # If the top score is very high (>0.92), we can return directly without LLM
    if top_scores[0] > 0.92 and top_scores[0] - top_scores[1] > 0.05:
        best_match = top_intents[0]
        category = intent_to_category.get(best_match)
        return best_match, category, "embedding", top_scores[0]
    
    # Otherwise, send to GPT-4o for final decision among top candidates
    intent_list_prompt = "\n".join([f"{intent}" for intent in top_intents])
    prompt = (
        "You are an intent matching assistant. Given a user query, select the most relevant intent from the list below.\n\n"
        "User Query: " + user_query + "\n\n"
        "Available Intents:\n" + intent_list_prompt + "\n\n"
        "STRICT REQUIREMENT. Return the best matching intent exactly as it appears in the Available Intents. Do not add any extra text, letter, number, hyphen, dot or anything. This is very Important"
    )
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": "You match user queries to predefined intents."},
                 {"role": "user", "content": prompt}],
    )
    best_match = response.choices[0].message.content.strip()
    
    # Find the category of the matched intent
    category = intent_to_category.get(best_match)
    
    # Get the confidence score for the selected intent
    best_idx = all_intents.index(best_match) if best_match in all_intents else -1
    confidence = similarities[best_idx] if best_idx >= 0 else 0
    
    return best_match, category, "llm", confidence

if __name__ == "__main__":
    print("Testing pure embedding-based RAG intent matching...")
    test_intent_matching()
    
    # Uncomment to test the hybrid approach
    # print("\nHybrid approach is also available via get_best_intent_match_hybrid function")









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
