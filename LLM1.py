import json
import os
import pickle
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from dotenv import load_dotenv
from openai import OpenAI
import sys
import requests
from prom_query import query_prometheus


# Load environment variables
load_dotenv()
api_key = os.getenv('API_KEY')
client = OpenAI(api_key=api_key)

# File to store cached embeddings
EMBEDDINGS_FILE = "intent_embeddings.pkl"

def save_embeddings():
    """ Save intent embeddings, categories, and mappings to a file. """
    with open(EMBEDDINGS_FILE, "wb") as f:
        pickle.dump((intent_embeddings, all_intents, all_categories, intent_to_category), f)

def load_embeddings():
    """ Load intent embeddings, categories, and mappings from a file. """
    global intent_embeddings, all_intents, all_categories, intent_to_category
    with open(EMBEDDINGS_FILE, "rb") as f:
        intent_embeddings, all_intents, all_categories, intent_to_category = pickle.load(f)
    print(f"Loaded cached embeddings for {len(all_intents)} intents.")


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
intent_categories = load_intent_prompts(intent_file_path)

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
    
    # Check if embeddings file exists
    if os.path.exists(EMBEDDINGS_FILE):
        load_embeddings()
        return

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
    # Save embeddings for future use
    save_embeddings()
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
    
    return best_match, category#, best_score, top_matches

def nwdaf_subscription_command(action, target):
    """ Send NWDAF subscription command """
    nwdaf_url = "http://127.0.0.71:8001/nwdaf/command"
    payload = {"action": action, "target": target}
    response = requests.post(nwdaf_url, json=payload)
    return response.json()

def process_user_query(user_query):
    best_intent, category= get_best_intent_match_rag(user_query)
    if not best_intent:
        return {"error": "No matching intent found."}
    
    print(f"Matched Intent: {best_intent} (Category: {category})")
    
    # Map category to function calls
    if "Subscribe" in category:
        target = "amf" if "AMF" in category else "smf"
        function_result = nwdaf_subscription_command("subscribe", target)
    elif "Unsubscribe" in category:
        target = "amf" if "AMF" in category else "smf"
        function_result = nwdaf_subscription_command("unsubscribe", target)
    elif "Active_UEs" in category:
        function_result = query_prometheus("active_UEs")
    elif "UE_location_report" in category:
        function_result = query_prometheus("UE_location_report")
    elif "Registration State" in category:
        function_result = query_prometheus("amf_ue_registration_state")
    else:
        return {"error": "Unknown category match."}
    
    # Feed the function result back into OpenAI for interpretation
    messages = [
        {"role": "system", "content": "You are a helpful assistant that interprets network analytics and subscription responses."},
        {"role": "user", "content": user_query},
        {"role": "function", "name": "function_result", "content": json.dumps(function_result)}
    ]
    second_response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages
    )
    return second_response.choices[0].message.content

if __name__ == "__main__":
    # Prepare embeddings first
    prepare_intent_embeddings()
    while True:
        try:
            user_question = input("\nEnter your query (Ctrl+C to exit): ")
            if not user_question.strip():
                continue
            
            response = process_user_query(user_question)
            print("Response:", response)
        except KeyboardInterrupt:
            print("\nExiting...")
            sys.exit(0)
