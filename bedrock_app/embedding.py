import json
import numpy as np
from .openrouter_client import get_openrouter_client

def embed_with_openrouter(model_id, input_text):
    """
    Generate embeddings using OpenRouter (OpenAI text-embedding models).

    Args:
        model_id: OpenRouter embedding model ID (e.g., "openai/text-embedding-3-small")
        input_text: Text to embed

    Returns:
        List of floats representing the embedding vector
    """
    try:
        client = get_openrouter_client()

        headers = {
            "Authorization": f"Bearer {client['api_key']}",
            "HTTP-Referer": "http://localhost:8501",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model_id,
            "input": input_text
        }

        response = client["session"].post(
            f"{client['base_url']}/embeddings",
            json=payload,
            headers=headers,
            timeout=60
        )

        if response.status_code != 200:
            print(f"Error generating embedding: {response.status_code} - {response.text}")
            return []

        response_data = response.json()

        if "data" in response_data and len(response_data["data"]) > 0:
            return response_data["data"][0].get("embedding", [])
        else:
            print("No embedding returned from API")
            return []

    except Exception as e:
        print(f"Error generating embedding: {e}")
        return []


def cosine_similarity(vec1, vec2):
    """Calculate cosine similarity between two vectors"""
    v1 = np.array(vec1)
    v2 = np.array(vec2)
    dot_product = np.dot(v1, v2)
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot_product / (norm1 * norm2)

