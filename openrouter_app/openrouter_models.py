"""
List of available OpenRouter models (OpenAI and other providers)
"""

# OpenAI models available through OpenRouter

OPENROUTER_MODELS = {
    "chat": [
        {
            "id": "meta-llama/llama-4-maverick:free",
            "name": "Meta Llama 4 Maverick (Free)",
            "provider": "Meta"
        },
        {
            "id": "xiaomi/mimo-v2-flash:free",
            "name": "Xiaomi MiMo V2 Flash (Free)",
            "provider": "Xiaomi"
        },
        {
            "id": "tngtech/deepseek-r1t2-chimera:free",
            "name": "DeepSeek R1T2 Chimera (Free)",
            "provider": "TNG Tech / DeepSeek"
        },
        {
            "id": "mistralai/devstral-2:free",
            "name": "Mistral Devstral 2 (Free)",
            "provider": "Mistral"
        },
        {
            "id": "meta-llama/llama-3.1-8b-instruct:free",
            "name": "Meta Llama 3.1 8B Instruct (Free)",
            "provider": "Meta"
        }
    ],

    "embedding": [
        {
            "id": "nomic-ai/nomic-embed-text-v1.5",
            "name": "Nomic Embed Text v1.5 (Free)",
            "provider": "Nomic AI"
        },
        {
            "id": "baai/bge-small-en-v1.5",
            "name": "BGE Small EN v1.5 (Free)",
            "provider": "BAAI"
        }
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

