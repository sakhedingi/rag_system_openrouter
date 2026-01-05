"""
List of available OpenRouter models (OpenAI and other providers)
"""

# OpenAI models available through OpenRouter
OPENROUTER_MODELS = {
    "chat": [
        {"id": "meta-llama/llama-3.3-70b-instruct:free", "name": "Meta Llama 3.3 70B (Free!)", "provider": "Meta"},
        {"id": "openai/gpt-4o", "name": "OpenAI GPT-4o", "provider": "OpenAI"},
        {"id": "openai/gpt-4-turbo", "name": "OpenAI GPT-4 Turbo", "provider": "OpenAI"},
        {"id": "openai/gpt-4-32k", "name": "OpenAI GPT-4 32K", "provider": "OpenAI"},
        {"id": "openai/gpt-3.5-turbo", "name": "OpenAI GPT-3.5 Turbo", "provider": "OpenAI"},
        {"id": "anthropic/claude-3.5-sonnet", "name": "Anthropic Claude 3.5 Sonnet", "provider": "Anthropic"},
        {"id": "anthropic/claude-3-opus", "name": "Anthropic Claude 3 Opus", "provider": "Anthropic"},
        {"id": "meta-llama/llama-2-70b-chat", "name": "Meta Llama 2 70B Chat", "provider": "Meta"},
    ],
    "embedding": [
        {"id": "openai/text-embedding-3-small", "name": "OpenAI Text Embedding 3 Small", "provider": "OpenAI"},
        {"id": "openai/text-embedding-3-large", "name": "OpenAI Text Embedding 3 Large", "provider": "OpenAI"},
    ]
}

def list_openrouter_models():
    """List available chat and embedding models from OpenRouter"""
    try:
        chat_models = OPENROUTER_MODELS.get("chat", [])
        embedding_models = OPENROUTER_MODELS.get("embedding", [])

        if not chat_models or not embedding_models:
            print("[WARN] Using hardcoded model list. Consider updating OPENROUTER_MODELS.")

        return chat_models, embedding_models

    except Exception as e:
        print(f"Error listing OpenRouter models: {e}")
        return [], []

