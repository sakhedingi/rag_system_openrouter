from .chat import invoke_model_stream, chat_with_openrouter

def answer_with_context(model_id, user_question, retrieved_text, message_history=None, temperature=0.7, top_p=0.9):
    """Uses OpenRouter model to answer a question using retrieved context

    Args:
        model_id: OpenRouter model ID (e.g., "openai/gpt-4o")
        user_question: The question to answer
        retrieved_text: Context retrieved from knowledge base
        message_history: Optional list of prior messages for conversation context
        temperature: Sampling temperature
        top_p: Nucleus sampling parameter

    Returns:
        Response text from the model
    """
    if message_history is None:
        message_history = []

    # Build the OpenAI-format messages
    messages = message_history.copy() if message_history else []
    messages.append({
        "role": "user",
        "content": f"Use the following context to answer the question.\n\nContext:\n{retrieved_text}\n\nQuestion:\n{user_question}"
    })

    try:
        response = chat_with_openrouter(
            model_id,
            "",  # Message is already in history
            message_history=messages[:-1],  # Pass all but the last message as history
            temperature=temperature,
            top_p=top_p
        )

        if message_history:
            message_history.append({"role": "assistant", "content": response})

        return response

    except Exception as e:
        print(f"Error answering with context: {e}")
        return None


def answer_with_context_stream(model_id, user_question, retrieved_text, message_history=None, temperature=0.7, top_p=0.9, character_stream=True):
    """Stream a response from OpenRouter using the provided retrieved context.

    Args:
        model_id: OpenRouter model ID
        user_question: The question to answer
        retrieved_text: Context retrieved from knowledge base
        message_history: Optional list of prior messages
        temperature: Sampling temperature
        top_p: Nucleus sampling parameter
        character_stream: If True, stream character by character for smoother UI

    Yields:
        Small text chunks suitable for real-time UI updates
    """
    if message_history is None:
        message_history = []

    # Build the OpenAI-format messages
    messages = message_history.copy() if message_history else []
    messages.append({
        "role": "user",
        "content": f"Use the following context to answer the question.\n\nContext:\n{retrieved_text}\n\nQuestion:\n{user_question}"
    })

    try:
        for chunk in invoke_model_stream(model_id, messages, temperature, top_p, character_stream):
            yield chunk
    except Exception as e:
        print(f"Error streaming answer_with_context: {e}")
        yield f"Error: {str(e)}"

