import streamlit as st
from bedrock_app.chat import chat_stream
from bedrock_app.semantic_search import build_vector_store_from_folder, semantic_search_local
from bedrock_app.rag import answer_with_context_stream
from bedrock_app.optimized_rag import OptimizedRAG
from bedrock_app.prompt_cache import PromptCache
from bedrock_app.openrouter_client import test_openrouter_connection
from bedrock_app.openrouter_models import list_openrouter_models
import os

os.makedirs("./temp_docs", exist_ok=True)

# Check OpenRouter API key on startup
if not os.getenv("OPENROUTER_API_KEY"):
    st.error("⚠️ OPENROUTER_API_KEY environment variable not set. Please configure it before using the app.")
    st.stop()

# Test OpenRouter connection
if not test_openrouter_connection():
    st.warning("⚠️ Could not connect to OpenRouter API. Please check your API key and ensure your account has credits at https://openrouter.ai/settings/credits")

# Initialize optimized RAG system
@st.cache_resource
def get_optimized_rag():
    return OptimizedRAG()


@st.cache_resource
def get_prompt_cache():
    return PromptCache()

st.set_page_config(page_title="SDQA AI Assistant", layout="wide")

st.sidebar.title("SDQA AI Assistant")
mode = st.sidebar.radio("Select Assistant Mode", ["Conversational Mode or RAG", "Intelligent Document Querying Mode (RAG)"])
chat_models, embedding_models = list_openrouter_models()
# Select default model (Free Llama 3.3)
selected_chat_name = "Meta Llama 3.3 70B (Free!)"
for chat_model in chat_models:
    if chat_model['name'] == selected_chat_name:
        selected_chat_model = chat_model
        break
chat_model_names = [m['name'] for m in chat_models]
selected_chat_name = st.sidebar.selectbox("Choose AI Model", chat_model_names, index=0)
selected_chat_model = next(m for m in chat_models if m['name'] == selected_chat_name)
st.sidebar.markdown("###  Model Behavior Settings")
temperature = st.sidebar.slider("Temperature", min_value=0.0, max_value=1.0, value=0.7, step=0.05)
top_p = st.sidebar.slider("Top-p (nucleus sampling)", min_value=0.0, max_value=1.0, value=0.9, step=0.05)

if mode == "Intelligent Document Querying Mode (RAG)":
    embed_model = embedding_models[0]
    st.sidebar.markdown(f"**Embedding Model:** {embed_model['name']}")
    kb_folder = "./knowledge_base"
    st.sidebar.markdown(f"**Knowledge Base:** `{kb_folder}`")

    # Use optimized RAG with pre-vectorization
    optimized_rag = get_optimized_rag()
    if "kb_initialized" not in st.session_state:
        with st.spinner("Initializing knowledge base..."):
            optimized_rag.initialize_knowledge_base(kb_folder, embed_model['id'])
            st.session_state.kb_initialized = True

    # Show optimization stats
#    with st.sidebar.expander(" Optimization Stats"):
#        stats = optimized_rag.get_optimization_stats()
#        st.write("**Vector Store:**", stats["vector_store"])
#        st.write("**Prompt Cache:**", stats["prompt_cache"])
#        st.write("**Memory Store:**", stats["memory_store"])

if mode == "Conversational Mode or RAG":
    st.subheader("You can ask questions or upload a document to get started...")
else:
    st.subheader("Ask a question based on your knowledge base...")

# Initialize history if not present
if "mode_histories" not in st.session_state:
    st.session_state.mode_histories = {
        "Conversational Mode or RAG": [],
        "Intelligent Document Querying Mode (RAG)": []
    }

# Track how many messages have been rendered for each mode to avoid duplicates
if "rendered_counts" not in st.session_state:
    st.session_state.rendered_counts = {
        "Conversational Mode or RAG": 0,
        "Intelligent Document Querying Mode (RAG)": 0
    }

# Single chat container and placeholders for messages
chat_container = st.container()

# Render full chat history into placeholders so streaming can update the last assistant message
def render_history_into_placeholders(container, history):
    placeholders = []
    for msg in history:
        ph = container.empty()
        with ph.container():
            with st.chat_message(msg["role"]):
                cp = st.empty()
                # render the static content for now
                cp.markdown(msg["content"])
                placeholders.append(cp)
    return placeholders

# Render existing history and keep placeholders for runtime updates
placeholders = render_history_into_placeholders(chat_container, st.session_state.mode_histories[mode])

# Capture user input
if mode == "Conversational Mode or RAG":
    user_input = st.chat_input("Ask AI Asstistant.")
else:
    user_input = st.chat_input("Ask SDQA AI Assistant.")

if mode == "Conversational Mode or RAG":
    uploaded_file = st.sidebar.file_uploader("Drop Your File Here", type=["pdf", "txt", "docx"])
    if uploaded_file:
        # st.sidebar.success(f"Uploaded: {uploaded_file.name}")
        # Save uploaded file temporarily
        temp_path = f"./temp_docs/{uploaded_file.name}"
        print(f"Uploaded File: {uploaded_file.name}")
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        # Build vector store from uploaded document
        embed_model = embedding_models[0]
        st.session_state.temp_vector_store = build_vector_store_from_folder("./temp_docs", embed_model['id'])

# Only generate response if there's new input
if user_input:
    current_history = st.session_state.mode_histories[mode]
    # Temporarily extend history for context
    temp_history = current_history + [{"role": "user", "content": user_input}]
    skip_generic_append = False

    if mode == "Conversational Mode or RAG":
        if uploaded_file:

            results = semantic_search_local(user_input, embed_model['id'], st.session_state.temp_vector_store)
            if results:
                # Stream conversational response using retrieved context
                context = "\n\n".join([r[2] for r in results])

                # Initialize prompt cache and ensure context chunks are cached for reuse
                prompt_cache = get_prompt_cache()
                try:
                    for filename, score, content in results:
                        prompt_cache.cache_context_chunk(content, {"source": filename, "score": score})
                except Exception as e:
                    print(f"[WARN] Error caching context chunks: {e}")

                # Check prompt cache for an exact query+context hit
                try:
                    cached = prompt_cache.get_cached_response(user_input, context)
                except Exception as e:
                    print(f"[WARN] Error reading prompt cache: {e}")
                    cached = None

                # Display user message immediately (create placeholder)
                current_history.append({"role": "user", "content": user_input})
                ph = chat_container.empty()
                with ph.container():
                    with st.chat_message("user"):
                        cp = st.empty()
                        cp.markdown(user_input)
                        placeholders.append(cp)

                if cached:
                    # Serve cached response immediately (no model call)
                    cached_response_text = cached.get("response", "")
                    ph = chat_container.empty()
                    with ph.container():
                        with st.chat_message("assistant"):
                            cp = st.empty()
                            cp.markdown(cached_response_text)
                            placeholders.append(cp)

                    # Update sidebar with cache info
                    if cached.get("tokens_saved", 0) > 0:
                        st.sidebar.info(f"[CACHE] Estimated tokens saved: {cached['tokens_saved']}")

                    # Append cached response to history and skip generic append
                    current_history.append({"role": "assistant", "content": cached_response_text})
                    # Mark rendered count to avoid duplicate rendering
                    st.session_state.rendered_counts[mode] = len(current_history)
                    skip_generic_append = True
                else:
                    full_response = ""
                    # Streaming generator from rag streaming helper
                    response_stream = answer_with_context_stream(
                        selected_chat_model['id'],
                        user_input,
                        context,
                        message_history=temp_history,
                        temperature=temperature,
                        top_p=top_p,
                        character_stream=True
                    )


                ph = chat_container.empty()
                with ph.container():
                    with st.chat_message("assistant"):
                        assistant_cp = st.empty()
                        placeholders.append(assistant_cp)

                        full_response = ""

                        with st.spinner("_Assistant is generating response..._"):
                            for token in response_stream:
                                full_response += token
                                assistant_cp.markdown(full_response)


                    response = full_response
                    # Cache the new response for future queries
                    try:
                        estimated_tokens_saved = len(context.split()) // 4
                        prompt_cache.cache_response(user_input, context, response, selected_chat_model['id'], tokens_saved=estimated_tokens_saved)
                        if estimated_tokens_saved > 0:
                            st.sidebar.info(f"[SAVED] Estimated tokens saved: {estimated_tokens_saved}")
                    except Exception as e:
                        print(f"[WARN] Error caching response: {e}")

                    current_history.append({"role": "assistant", "content": response})
                    # assistant placeholder already updated in-place
                    skip_generic_append = True
            else:
                response = "No relevant documents found."
        else:
            # Stream conversational response token-by-token for better responsiveness
            # We'll display streaming tokens in the assistant chat bubble and
            # avoid the generic double-append later by setting `skip_generic_append`.
            selected_model_id = selected_chat_model['id']
            # Display user message immediately (create placeholder)
            current_history.append({"role": "user", "content": user_input})
            ph = chat_container.empty()
            with ph.container():
                with st.chat_message("user"):
                    cp = st.empty()
                    cp.markdown(user_input)
                    placeholders.append(cp)

            full_response = ""
            # Streaming generator from chat_stream
            response_stream = chat_stream(
                selected_model_id,
                user_input,
                message_history=temp_history,
                temperature=temperature,
                top_p=top_p,
                character_stream=True
            )

            ph = chat_container.empty()
            with ph.container():
                with st.chat_message("assistant"):
                    assistant_cp = st.empty()
                    placeholders.append(assistant_cp)

                    full_response = ""

                    with st.spinner("_Assistant is generating response..._"):
                        for token in response_stream:
                            full_response += token
                            assistant_cp.markdown(full_response)

                response = full_response
            # Append assistant response to history
            current_history.append({"role": "assistant", "content": response})
            # assistant placeholder already updated in-place
            # Prevent the generic append block below from duplicating entries
            skip_generic_append = True
    else:
        embed_model = embedding_models[0]
        optimized_rag = get_optimized_rag()

        # Append user message to history immediately and render placeholder
        current_history.append({"role": "user", "content": user_input})
        ph = chat_container.empty()
        with ph.container():
            with st.chat_message("user"):
                cp = st.empty()
                cp.markdown(user_input)
                placeholders.append(cp)

        # Use streaming for RAG responses
        response_stream = optimized_rag.answer_with_optimization_stream(
            model_id=selected_chat_model['id'],
            user_question=user_input,
            embed_model_id=embed_model['id'],
            message_history=temp_history,
            temperature=temperature,
            top_p=top_p,
            use_cache=True,
            store_memory=True,
            retrieve_past_contexts=True
        )

        # Display streaming response in chat using a placeholder
        full_response = ""
        stats_data = None
        ph = chat_container.empty()
        with ph.container():
            with st.chat_message("assistant"):
                assistant_cp = st.empty()
                placeholders.append(assistant_cp)

                full_response = ""

                with st.spinner("_Assistant is generating response..._"):
                    for token, stats_update in response_stream:
                        full_response += token
                        stats_data = stats_update
                        assistant_cp.markdown(full_response)

            response = full_response

        # Add assistant response to history (placeholder already has final content)
        current_history.append({"role": "assistant", "content": response})

        # Display optimization stats after streaming completes
    #        if stats_data and not stats_data.get("cache_hit", False):
    #            if stats_data.get('optimization_source'):
    #                st.sidebar.success(f" Optimizations: {', '.join(stats_data['optimization_source'])}")
    #                if stats_data.get('tokens_saved', 0) > 0:
    #                    st.sidebar.info(f"[SAVED] Estimated tokens saved: {stats_data['tokens_saved']}")

    # For non-RAG modes, append to history normally unless streaming already handled it
    if not ( 'skip_generic_append' in locals() and skip_generic_append ):
        if mode != "Intelligent Document Querying Mode (RAG)":
            current_history.append({"role": "user", "content": user_input})
            current_history.append({"role": "assistant", "content": response})
            # Display new messages via placeholders to keep single renderer behavior
            ph = chat_container.empty()
            with ph.container():
                with st.chat_message("user"):
                    ucp = st.empty()
                    ucp.markdown(user_input)
                    placeholders.append(ucp)
            ph2 = chat_container.empty()
            with ph2.container():
                with st.chat_message("assistant"):
                    acp = st.empty()
                    acp.markdown(response)
                    placeholders.append(acp)
