import numpy as np
from numpy.linalg import norm

def match(table, data):
    """
    Finds the top 5 users with the most similar interest area embeddings to the current user.

    Parameters:
    - table: DynamoDB table resource
    - data: Dictionary containing at least the 'email' key for the current user

    Returns:
    - List of dictionaries with the closest users' emails, usernames, and similarity scores
    """
    current_email = data["email"]

    # Retrieve current user's embeddings
    response = table.get_item(Key={"Email": current_email})
    item = response.get("Item")
    if not item or "interest_area_embeddings" not in item:
        return {"error": "No embeddings found for current user"}

    current_embeddings = item["interest_area_embeddings"]

    # Compute average embedding for the current user
    current_vectors = [np.array([float(x) for x in vec]) for vec in current_embeddings.values()]
    if not current_vectors:
        return {"error": "Current user has no embeddings"}
    current_avg = np.mean(current_vectors, axis=0)

    # List to store all matches
    matches = []

    # Scan the table to compare with other users
    scan_kwargs = {
        'ProjectionExpression': 'Email, username, interest_area_embeddings'  # Include username in the projection expression
    }
    done = False
    start_key = None

    while not done:
        if start_key:
            scan_kwargs['ExclusiveStartKey'] = start_key
        response = table.scan(**scan_kwargs)
        for user in response.get("Items", []):
            other_email = user["Email"]
            other_username = other_email.split("@")[0]  # Default to "Unknown" if username is missing
            if other_email == current_email:
                continue
            embeddings = user.get("interest_area_embeddings")
            if not embeddings:
                continue
            vectors = [np.array([float(x) for x in vec]) for vec in embeddings.values()]
            if not vectors:
                continue
            other_avg = np.mean(vectors, axis=0)
            # Compute cosine similarity
            similarity = np.dot(current_avg, other_avg) / (norm(current_avg) * norm(other_avg))
            matches.append({
                "email": other_email,
                "username": other_username,  # Include username in the match
                "similarity": round(similarity, 4)
            })
        start_key = response.get('LastEvaluatedKey', None)
        done = start_key is None

    # Sort matches by similarity score (descending) and pick top 5
    top_matches = sorted(matches, key=lambda x: x["similarity"], reverse=True)[:5]

    if top_matches:
        return {"top_matches": top_matches}
    else:
        return {"message": "No similar users found"}
