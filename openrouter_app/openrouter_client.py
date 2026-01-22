import os
import requests

def get_openrouter_client():
    """Initialize OpenRouter HTTP client with API key from environment"""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENROUTER_API_KEY environment variable not set. "
            "Please set your OpenRouter API key: set OPENROUTER_API_KEY=your_key"
        )

    return {
        "api_key": api_key,
        "base_url": "https://openrouter.ai/api/v1",
        "session": requests.Session()
    }

def test_openrouter_connection():
    """Test if OpenRouter API is accessible"""
    try:
        client = get_openrouter_client()
        headers = {
            "Authorization": f"Bearer {client['api_key']}",
            "HTTP-Referer": "http://localhost:8501",  # Streamlit default port
        }
        response = client["session"].get(
            f"{client['base_url']}/models",
            headers=headers,
            timeout=5
        )
        return response.status_code == 200
    except Exception as e:
        print(f"Error testing OpenRouter connection: {e}")
        return False

