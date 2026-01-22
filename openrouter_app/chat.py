import json
import requests
from .openrouter_client import get_openrouter_client


def invoke_model_stream(model_id, messages, temperature=0.7, top_p=0.9, character_stream=True):
    """
    Stream response tokens from OpenRouter model using OpenAI-compatible API.

    Yields text tokens one by one for real-time display.

    Args:
        model_id: OpenRouter model ID (e.g., "openai/gpt-4o")
        messages: List of message dicts with 'role' and 'content'
        temperature: Sampling temperature (0.0-2.0)
        top_p: Nucleus sampling parameter (0.0-1.0)
        character_stream: If True, break larger chunks into character-level streams

    Yields:
        Text tokens (chars or words) from the model response
    """
    try:
        client = get_openrouter_client()
        headers = {
            "Authorization": f"Bearer {client['api_key']}",
            "HTTP-Referer": "http://localhost:8501",  # Streamlit default
            "Content-Type": "application/json"
        }

        payload = {
            "model": model_id,
            "messages": messages,
            "temperature": min(max(temperature, 0.0), 2.0),  # Clamp to valid range
            "top_p": min(max(top_p, 0.0), 1.0),  # Clamp to valid range
            "max_tokens": 2000,
            "stream": True
        }

        response = client["session"].post(
            f"{client['base_url']}/chat/completions",
            json=payload,
            headers=headers,
            stream=True,
            timeout=60
        )

        if response.status_code != 200:
            error_msg = response.text
            if response.status_code == 402:
                yield "Error: Insufficient credits. Please add credits to your OpenRouter account at https://openrouter.ai/settings/credits"
            elif response.status_code == 401:
                yield "Error: Invalid API key. Please check your OPENROUTER_API_KEY environment variable."
            elif response.status_code == 429:
                yield "Error: Rate limited. Please wait a moment and try again."
            else:
                yield f"Error: {response.status_code} - {error_msg}"
            return

        # Parse SSE stream (OpenAI format)
        for line in response.iter_lines():
            if not line:
                continue

            line_str = line.decode('utf-8') if isinstance(line, bytes) else line

            if line_str.startswith("data: "):
                data_str = line_str[6:]  # Remove "data: " prefix

                if data_str == "[DONE]":
                    break

                try:
                    chunk = json.loads(data_str)
                    # Extract token from OpenAI format
                    if "choices" in chunk and len(chunk["choices"]) > 0:
                        delta = chunk["choices"][0].get("delta", {})
                        if "content" in delta:
                            text = delta["content"]
                            # Stream character by character for smoother UI
                            if character_stream:
                                for char in text:
                                    yield char
                            else:
                                yield text
                except json.JSONDecodeError:
                    continue

    except Exception as e:
        print(f"Error streaming from model: {e}")
        yield f"Error: {str(e)}"


def chat_with_openrouter(model_id, user_message, message_history=None, temperature=0.7, top_p=0.9):
    """
    Send a message to OpenRouter and get a response (non-streaming).

    Args:
        model_id: OpenRouter model ID
        user_message: The user's message string
        message_history: Optional list of prior messages (role/content dicts)
        temperature: Sampling temperature
        top_p: Nucleus sampling parameter

    Returns:
        Response text from the model
    """
    try:
        if message_history is None:
            message_history = []

        client = get_openrouter_client()

        messages = message_history + [{"role": "user", "content": user_message}]

        headers = {
            "Authorization": f"Bearer {client['api_key']}",
            "HTTP-Referer": "http://localhost:8501",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model_id,
            "messages": messages,
            "temperature": min(max(temperature, 0.0), 2.0),
            "top_p": min(max(top_p, 0.0), 1.0),
            "max_tokens": 2000
        }

        response = client["session"].post(
            f"{client['base_url']}/chat/completions",
            json=payload,
            headers=headers,
            timeout=60
        )

        if response.status_code != 200:
            if response.status_code == 402:
                return "Error: Insufficient credits. Please add credits to your OpenRouter account at https://openrouter.ai/settings/credits"
            elif response.status_code == 401:
                return "Error: Invalid API key. Please check your OPENROUTER_API_KEY environment variable."
            elif response.status_code == 429:
                return "Error: Rate limited. Please wait a moment and try again."
            else:
                return f"Error: {response.status_code} - {response.text}"

        response_data = response.json()

        if "choices" in response_data and len(response_data["choices"]) > 0:
            return response_data["choices"][0]["message"]["content"]
        else:
            return "No response from model"

    except Exception as e:
        print(f"Error invoking model: {e}")
        return f"Error: {str(e)}"


def chat_stream(model_id, user_message, message_history=None, temperature=0.7, top_p=0.9, character_stream=True):
    """
    Stream a conversational response from OpenRouter token-by-token.

    Yields text pieces (chars or small chunks) for real-time UI updates.

    Args:
        model_id: OpenRouter model id
        user_message: The user's message string
        message_history: Optional list of prior messages (role/content dicts)
        temperature: Sampling temperature
        top_p: Nucleus sampling parameter
        character_stream: If True, yield character-level pieces for smoother UI

    Yields:
        str tokens from the model streaming endpoint
    """
    try:
        if message_history is None:
            message_history = []

        messages = message_history + [{"role": "user", "content": user_message}]

        # Delegate to the generic streaming helper
        for chunk in invoke_model_stream(model_id, messages, temperature, top_p, character_stream):
            yield chunk

    except Exception as e:
        print(f"Error in chat_stream: {e}")
        yield f"Error: {str(e)}"

