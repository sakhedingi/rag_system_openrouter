"""
List of available OpenRouter models (OpenAI and other providers)
"""

# OpenAI models available through OpenRouter
OPENROUTER_MODELS = {
    "chat": [
        # {"id": "openrouter/free", "name": "Free Models Router", "provider": "OpenRouter"},
        # {"id": "anthropic/claude-3.5-sonnet", "name": "Anthropic Claude 3.5 Sonnet", "provider": "Anthropic"},
        # {"id": "meta-llama/llama-3.3-70b-instruct:free", "name": "Llama 3.3 70B", "provider": "Meta"},
        # {"id": "meta-llama/llama-4-maverick:free", "name": "Meta Llama 4 Maverick (Free)", "provider": "Meta"},
        # {"id": "openai/gpt-4o", "name": "OpenAI GPT-4o", "provider": "OpenAI"},
        # {"id": "openai/gpt-4-turbo", "name": "OpenAI GPT-4 Turbo", "provider": "OpenAI"},
        # {"id": "openai/gpt-oss-120b:free", "name": "GPT-OSS 120B", "provider": "OpenAI"},
        # {"id": "openai/gpt-3.5-turbo", "name": "OpenAI GPT-3.5 Turbo", "provider": "OpenAI"},
        # {"id": "anthropic/claude-3-opus", "name": "Anthropic Claude 3 Opus", "provider": "Anthropic"},
        # {"id": "meta-llama/llama-2-70b-chat", "name": "Meta Llama 2 70B Chat", "provider": "Meta"},
         {"id": "arcee-ai/trinity-large-preview:free", "name": "Arcee Trinity Large", "provider": "Arcee-AI"},
        # {"id": "mistralai/mistral-small-3.1-24b-instruct:free", "name": "Mistral Small 3.1", "provider": "Mistral"},
        # {"id": "google/gemini-2.0-flash-exp:free", "name": "Gemini 2.0 Flash Experimental", "provider": "Google"},
         {"id": "stepfun/step-3.5-flash:free", "name": "Step 3.5 Flash", "provider": "StepFun"},
        # {"id": "deepseek/deepseek-r1:free", "name": "DeepSeek R1", "provider": "DeepSeek"},
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

