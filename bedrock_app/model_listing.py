from .openrouter_models import list_openrouter_models

def list_bedrock_models():
    """Lists available chat and embedding models from OpenRouter

    Note: Function renamed from list_bedrock_models for backward compatibility.
    Now uses OpenRouter API instead of AWS Bedrock.
    """
    return list_openrouter_models()
