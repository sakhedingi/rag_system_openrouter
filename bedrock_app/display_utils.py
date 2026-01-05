def display_chat_models(chat_models):
    print("\n" + "=" * 80)
    print("AVAILABLE CHAT MODELS IN AMAZON BEDROCK")
    print("=" * 80 + "\n")

    if chat_models:
        for idx, model in enumerate(chat_models, 1):
            print(f"{idx}. {model['name']}\n   ID: {model['id']}\n   Provider: {model['provider']}\n")

def display_embed_models(embedding_models):
    print("\n" + "=" * 80)
    print("AVAILABLE EMBED MODELS IN AMAZON BEDROCK")
    print("=" * 80 + "\n")

    if embedding_models:
         for idx, model in enumerate(embedding_models, 1):
            print(f"{idx}. {model['name']}\n   ID: {model['id']}\n   Provider: {model['provider']}\n")