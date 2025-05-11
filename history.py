from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
from collections import Counter, defaultdict
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
from transformers import pipeline
from decimal import Decimal
import requests
import time

import numpy as np

# Load environment variables from .env file
load_dotenv()

# Access the token
api_token = os.getenv("HUGGING_FACE_KEY")
model = SentenceTransformer("all-MiniLM-L6-v2")
# generator = pipeline("text-generation", 
#                      model="mistralai/Mistral-7B-Instruct", 
#                      device_map="auto", 
#                      max_new_tokens=30)

def get_interest_area_remote(tag_list):
    prompt = f"""
You are a helpful assistant. Given a list of tags, return exactly 1 interest area. 
ONLY return a clean word. No explanations, no numbering, nothing else.

Tags: {', '.join(tag_list)}
Interest Areas:"""

    API_URL = "https://router.huggingface.co/nebius/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "deepseek-ai/DeepSeek-V3-0324-fast",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": 512
    }

    retries = 3
    delay = 5  # seconds

    
    response = requests.post(API_URL, headers=headers, json=payload)
    # print(type(response))
    if response.status_code== 200:
        try:
            # print(response.json()["choices"][0]["message"]["content"])
            # print("returning from interest areas\n")
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print("Parsing error:", e)
            return "Unknown"
    elif response.status_code == 503:
        print(f"Model not ready. Retrying in {delay} seconds... (Attempt {attempt+1})")
        # time.sleep(delay)
    else:
        print(f"Failed with status {response.status_code}: {response.text}")
        
    return "Unknown"

def save_history(table, payload):
    # Step 1: Get existing genre_counts for this user
    print(payload)
    response = table.get_item(Key={"Email": payload["email"]})
    existing = response.get("Item", {}).get("genre_counts", {})

    # Step 2: Count new genres and update
    new_genres = payload["vid"]  # list of genres from payload
    counter = Counter(existing)

    for genre in new_genres:
        counter[genre] += 1

    # Step 3: Handle overflow - keep only top 20
    if len(counter) > 20:
        min_count = min(counter.values())
        lowest = [g for g, c in counter.items() if c == min_count]
        for genre in new_genres:
            if genre in lowest:
                lowest.remove(genre)
        if lowest:
            to_remove = lowest[0]
            del counter[to_remove]
        elif len(counter) > 20:
            counter.popitem()

    # Step 4: Write back only top 20 genres
    top_20 = dict(counter.most_common(20))
    
    # Step 5: Generate embeddings
    tags = list(top_20.keys())
    freqs = np.array(list(top_20.values()))
    embeddings = model.encode(tags)

    # Step 6: Cluster into interest areas
    k = min(6, len(tags))
    kmeans = KMeans(n_clusters=k, random_state=42)
    kmeans.fit(embeddings, sample_weight=freqs)
    labels = kmeans.labels_

    # Step 7: Label each cluster using LLM
    cluster_tags = defaultdict(list)
    for tag, label in zip(tags, labels):
        cluster_tags[label].append(tag)

    interest_areas = {}
    # print(cluster_tags)
    for cluster_id, tag_list in cluster_tags.items():
        label = get_interest_area_remote(tag_list)
        # print(label)
        print(f"Cluster {cluster_id} - Interest Area: {label},  {tag_list}")
        interest_areas[label] = tag_list

    interest_area_embeddings = {}
    for label, tag_list in interest_areas.items():
        tag_embeddings = model.encode(tag_list)
        avg_embedding = np.mean(tag_embeddings, axis=0)
        # Convert float32 to Decimal for DynamoDB compatibility
        avg_embedding_decimal = [Decimal(str(x)) for x in avg_embedding]
        interest_area_embeddings[label] = avg_embedding_decimal
    # Step 8: Save to DynamoDB
    table.update_item(
    Key={"Email": payload["email"]},
    UpdateExpression="SET genre_counts = :top, interest_areas = :interests, interest_area_embeddings = :embeddings",
    ExpressionAttributeValues={
        ":top": top_20,
        ":interests": interest_areas,
        ":embeddings": interest_area_embeddings
    }
)

    return jsonify({"message": "History and interest areas updated"}), 200
