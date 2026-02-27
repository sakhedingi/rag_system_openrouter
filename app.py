import streamlit as st
from openrouter_app.chat import chat_stream
from openrouter_app.semantic_search import build_vector_store_from_folder, semantic_search_local
from openrouter_app.rag import answer_with_context_stream
from openrouter_app.optimized_rag import OptimizedRAG
from openrouter_app.prompt_cache import PromptCache
from openrouter_app.openrouter_client import test_openrouter_connection
from openrouter_app.openrouter_models import list_openrouter_models
import os
import html
import base64

os.makedirs("./temp_docs", exist_ok=True)

# ----------------------------
# Startup checks
# ----------------------------
if not os.getenv("OPENROUTER_API_KEY"):
    st.error("⚠️ OPENROUTER_API_KEY environment variable not set. Please configure it before using the app.")
    st.stop()

if not test_openrouter_connection():
    st.warning(
        "⚠️ Could not connect to OpenRouter API. Please check your API key and ensure your account has credits at https://openrouter.ai/settings/credits"
    )


# ----------------------------
# Cached singletons
# ----------------------------
@st.cache_resource
def get_optimized_rag():
    return OptimizedRAG()


@st.cache_resource
def get_prompt_cache():
    return PromptCache()


st.set_page_config(page_title="SDQA Assistant", layout="wide")


# ----------------------------
# UI Styling (CSS)
# ----------------------------
def load_css(file_path: str):
    with open(file_path, "r") as f:
        css_content = f.read()
    st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)

load_css("css/styles.css")

# ----------------------------
# Top header (logo + title)
# ----------------------------

def img_to_base64(path: str) -> str | None:
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception:
        return None

# ----------------------------
# Message rendering helpers
# ----------------------------

def bubble_html(content: str) -> str:
    safe = html.escape(content).replace("\n", "<br>")
    return f'<div class="user-bubble">{safe}</div>'


def render_message(role: str, content: str, placeholder=None):
    target = placeholder if placeholder is not None else st
    if role == "user":
        target.markdown(bubble_html(content), unsafe_allow_html=True)
    else:
        target.markdown(content)


# ----------------------------
# Sidebar
# ----------------------------
with st.sidebar:
    st.image("assets/download.png", width=150)

st.sidebar.title("SDQA Assistant")

mode = st.sidebar.radio(
    "Select Assistant Mode",
    ["Conversational Mode or RAG", "Intelligent Document Querying Mode (RAG)"],
)

chat_models, embedding_models = list_openrouter_models()

selected_chat_name = "Meta Llama 3.3 70B"
selected_chat_model = chat_models[0]
for chat_model in chat_models:
    if chat_model.get("name") == selected_chat_name:
        selected_chat_model = chat_model
        break

chat_model_names = [m["name"] for m in chat_models]
selected_chat_name = st.sidebar.selectbox("Choose AI Model", chat_model_names, index=0)
selected_chat_model = next(m for m in chat_models if m["name"] == selected_chat_name)

st.sidebar.markdown("### Model Behavior Settings")
temperature = st.sidebar.slider("Temperature", min_value=0.0, max_value=1.0, value=0.7, step=0.05)
top_p = st.sidebar.slider("Top-p (nucleus sampling)", min_value=0.0, max_value=1.0, value=0.9, step=0.05)

if mode == "Intelligent Document Querying Mode (RAG)":
    embed_model = embedding_models[1]
    st.sidebar.markdown(f"**Embedding Model:** {embed_model['name']}")
    kb_folder = "./knowledge_base"
    st.sidebar.markdown(f"**Knowledge Base:** `{kb_folder}`")

    optimized_rag = get_optimized_rag()
    if "kb_initialized" not in st.session_state:
        with st.spinner("Initializing knowledge base..."):
            optimized_rag.initialize_knowledge_base(kb_folder, embed_model["id"])
            st.session_state.kb_initialized = True

logo_b64 = img_to_base64("assets/download1.png")
avater_b64 = img_to_base64("assets/user-4254_1024.png")

if mode == "Conversational Mode or RAG":
        st.markdown(
        f"""
<div class="app-header">
  <img class="logo" src="data:image/png;base64,{logo_b64}" alt="Logo"/>
  <span class="title">You can ask questions or upload a document to get started...</span>
</div><br>
""",
        unsafe_allow_html=True,
    )
else:
            st.markdown(
        f"""
<div class="app-header">
  <img class="logo" src="data:image/png;base64,{logo_b64}" alt="Logo"/>
  <span class="title">Ask a question based on your knowledge base...</span>
</div><br>
""",
        unsafe_allow_html=True,
    )

if "mode_histories" not in st.session_state:
    st.session_state.mode_histories = {
        "Conversational Mode or RAG": [],
        "Intelligent Document Querying Mode (RAG)": [],
    }

chat_container = st.container()


def render_history(container, history):
    placeholders = []
    for msg in history:
        ph = container.empty()
        with ph.container():
            avatar = "assets/user-4254_1024.png" if msg["role"] == "user" else "https://help.vodacom.co.za/static/media/tobi-chat.8fcbfe07.svg"
            with st.chat_message(msg["role"], avatar=avatar):
                cp = st.empty()
                render_message(msg["role"], msg["content"], placeholder=cp)
                placeholders.append(cp)
    return placeholders


placeholders = render_history(chat_container, st.session_state.mode_histories[mode])

user_input = st.chat_input("Ask AI Assistant.")

uploaded_file = None
if mode == "Conversational Mode or RAG":
    uploaded_file = st.sidebar.file_uploader("Drop Your File Here", type=["pdf", "txt", "docx", "png", "jpg", "jpeg", "gif", "bmp", "webp"])
    if uploaded_file:
        temp_path = f"./temp_docs/{uploaded_file.name}"
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        embed_model = embedding_models[1]
        st.session_state.temp_vector_store = build_vector_store_from_folder("./temp_docs", embed_model["id"])

if user_input:
    current_history = st.session_state.mode_histories[mode]
    temp_history = current_history + [{"role": "user", "content": user_input}]

    if mode == "Conversational Mode or RAG":
        if uploaded_file:
            embed_model = embedding_models[1]
            results = semantic_search_local(user_input, embed_model["id"], st.session_state.temp_vector_store)
            if results:
                context = "\n\n".join([r[2] for r in results])

                current_history.append({"role": "user", "content": user_input})
                ph = chat_container.empty()
                with ph.container():
                    with st.chat_message("user", avatar="assets/user-4254_1024.png"):
                        cp = st.empty()
                        render_message("user", user_input, placeholder=cp)
                        placeholders.append(cp)

                response_stream = answer_with_context_stream(
                    selected_chat_model["id"],
                    user_input,
                    context,
                    message_history=temp_history,
                    temperature=temperature,
                    top_p=top_p,
                    character_stream=True,
                )

                ph = chat_container.empty()
                with ph.container():
                    with st.chat_message("assistant", avatar="https://help.vodacom.co.za/static/media/tobi-chat.8fcbfe07.svg"):
                        assistant_cp = st.empty()
                        placeholders.append(assistant_cp)
                        full_response = ""
                        with st.spinner(""):
                            for token in response_stream:
                                full_response += token
                                render_message("assistant", full_response, placeholder=assistant_cp)

                response = full_response
                current_history.append({"role": "assistant", "content": response})
            else:
                st.info("No relevant documents found.")
        else:
            selected_model_id = selected_chat_model["id"]

            current_history.append({"role": "user", "content": user_input})
            ph = chat_container.empty()
            with ph.container():
                with st.chat_message("user", avatar="assets/user-4254_1024.png"):
                    cp = st.empty()
                    render_message("user", user_input, placeholder=cp)
                    placeholders.append(cp)

            response_stream = chat_stream(
                selected_model_id,
                user_input,
                message_history=temp_history,
                temperature=temperature,
                top_p=top_p,
                character_stream=True,
            )

            ph = chat_container.empty()
            with ph.container():
                with st.chat_message("assistant", avatar="https://help.vodacom.co.za/static/media/tobi-chat.8fcbfe07.svg"):
                    assistant_cp = st.empty()
                    placeholders.append(assistant_cp)
                    full_response = ""
                    with st.spinner(""):
                        for token in response_stream:
                            full_response += token
                            render_message("assistant", full_response, placeholder=assistant_cp)

            response = full_response
            current_history.append({"role": "assistant", "content": response})

    else:
        embed_model = embedding_models[1]
        optimized_rag = get_optimized_rag()

        current_history.append({"role": "user", "content": user_input})
        ph = chat_container.empty()
        with ph.container():
            with st.chat_message("user", avatar="assets/user-4254_1024.png"):
                cp = st.empty()
                render_message("user", user_input, placeholder=cp)
                placeholders.append(cp)

        response_stream = optimized_rag.answer_with_optimization_stream(
            model_id=selected_chat_model["id"],
            user_question=user_input,
            embed_model_id=embed_model["id"],
            message_history=temp_history,
            temperature=temperature,
            top_p=top_p,
            use_cache=True,
            store_memory=True,
            retrieve_past_contexts=True,
        )

        ph = chat_container.empty()
        with ph.container():
            with st.chat_message("assistant", avatar="https://help.vodacom.co.za/static/media/tobi-chat.8fcbfe07.svg"):
                assistant_cp = st.empty()
                placeholders.append(assistant_cp)
                full_response = ""
                with st.spinner(""):
                    for token, _stats in response_stream:
                        full_response += token
                        render_message("assistant", full_response, placeholder=assistant_cp)

        response = full_response
        current_history.append({"role": "assistant", "content": response})
