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
st.markdown(
    """
<style>
:root{
  --voda-red: #E60000;
  --voda-red-dark: #C20000;
  --text-dark: #333333;
  --bot-bubble: #F2F3F5;
  --page-bg: #FFFFFF;
  --header-bg: #FFFFFF;
}

html, body, [data-testid="stAppViewContainer"] { background: var(--page-bg) !important; }

/* Center chats */
section.main > div.block-container {
  max-width: 1100px !important;
  margin-left: auto !important;
  margin-right: auto !important;
}

/* Remove grey backgrounds from common wrappers */
[data-testid="stLayoutWrapper"],
[data-testid="stVerticalBlock"],
[data-testid="stElementContainer"],
[data-testid="stMarkdown"],
[data-testid="stMarkdownContainer"],
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stBlock"] {
  background: transparent !important;
}

/* Header */
.app-header {
  position: sticky; top: 0; z-index: 1000;
  display: flex; align-items: center; gap: 10px;
  background: var(--header-bg) !important;
  padding: 6px 10px; border-bottom: 1px solid #e6e6e6;
}
.app-header img.logo { height: 20px; width: auto; }
.app-header .title { font-weight: 600; color: var(--text-dark); font-size: 1.0rem; }

/* Remove avatars */
[data-testid="stChatMessageAvatarUser"],
[data-testid="stChatMessageAvatarAssistant"],
[data-testid="stChatMessageAvatar"] {
  display: none !important;
}

/* Space between chat bubbles */
[data-testid="stChatMessage"] {
  background: transparent !important;
  padding: 0 !important;
  border-radius: 0 !important;
  box-shadow: none !important;
  margin: 0 0 20px 0 !important;
}

/* Chat content container */
[data-testid="stChatMessageContent"] {
  width: 100% !important;
  background: transparent !important;
  padding: 0 !important;
  border-radius: 0 !important;
  box-shadow: none !important;
  display: flex !important;
  align-items: flex-start !important;
  justify-content: flex-start !important; /* leave alignment left for now */
}

/* USER: keep your custom bubble */
[data-testid="stChatMessageContent"][aria-label*="user"] {
  justify-content: flex-start !important;
}

/* USER: remove any background on wrapper blocks BUT keep .user-bubble intact */
[data-testid="stChatMessageContent"][aria-label*="user"] *:not(.user-bubble) {
  background: transparent !important;
  box-shadow: none !important;
}

/* User bubble (RED) */
.user-bubble {
  display: inline-block !important;
  padding: 10px 12px !important;
  border-radius: 16px 16px 4px 16px !important;
  line-height: 1.35 !important;
  word-wrap: break-word !important;
  background: var(--voda-red) !important;
  color: #FFFFFF !important;
  box-shadow: 0 1px 1px rgba(0,0,0,0.04), 0 1px 3px rgba(0,0,0,0.06) !important;
  width: fit-content !important;
  max-width: min(900px, 92%) !important;
}

/* ---------------------------------------------------------
   ASSISTANT bubble fix:
   Apply bubble styling to the rendered markdown container so the
   background wraps the FULL height (prevents the "cut off" look).
--------------------------------------------------------- */

/* Remove any styling from the immediate wrapper so it doesn't interfere */
[data-testid="stChatMessageContent"]:not([aria-label*="user"]) > div {
  background: transparent !important;
  padding: 0 !important;
  border-radius: 0 !important;
  box-shadow: none !important;
}

/* Apply the bubble to the actual markdown container */
[data-testid="stChatMessageContent"]:not([aria-label*="user"]) [data-testid="stMarkdownContainer"] {
  background: var(--bot-bubble) !important;
  border-radius: 16px 16px 16px 4px !important;
  padding: 12px 14px !important;
  box-shadow: 0 1px 1px rgba(0,0,0,0.04), 0 1px 3px rgba(0,0,0,0.06) !important;
  display: inline-block !important;
  width: fit-content !important;
  max-width: min(900px, 92%) !important;
  overflow: visible !important;
  line-height: 1.45 !important;
}

/* Normalize markdown spacing inside assistant bubble */
[data-testid="stChatMessageContent"]:not([aria-label*="user"]) [data-testid="stMarkdownContainer"] p {
  margin: 0 !important;
}
[data-testid="stChatMessageContent"]:not([aria-label*="user"]) [data-testid="stMarkdownContainer"] p + p {
  margin-top: 0.6rem !important;
}

[data-testid="stChatMessageContent"]:not([aria-label*="user"]) [data-testid="stMarkdownContainer"] ul,
[data-testid="stChatMessageContent"]:not([aria-label*="user"]) [data-testid="stMarkdownContainer"] ol {
  margin: 0.25rem 0 0.25rem 1.2rem !important;
}

/* Sticky input bar */
[data-testid="stChatInput"] {
  position: sticky; bottom: 0; z-index: 999;
  background: var(--page-bg) !important;
  border-top: 1px solid #e6e6e6;
  padding-top: 0.5rem;
  backdrop-filter: blur(2px);
}

[data-testid="stChatInput"] textarea {
  border: none !important;
  box-shadow: none !important;
  outline: none !important;
  border-radius: 10px !important;
}

[data-testid="stChatInput"] textarea:focus {
  box-shadow: 0 0 0 2px rgba(230, 0, 0, 0.15) !important;
  outline: none !important;
}

[data-testid="stChatInput"] button[kind="primary"] {
  background: var(--voda-red) !important;
  border: 1px solid var(--voda-red) !important;
  color: #FFFFFF !important;
}

[data-testid="stChatInput"] button[kind="primary"]:hover {
  background: var(--voda-red-dark) !important;
  border-color: var(--voda-red-dark) !important;
}

@media (max-width: 768px) {
  section.main > div.block-container { max-width: 92vw !important; }
  [data-testid="stChatMessageContent"]:not([aria-label*="user"]) [data-testid="stMarkdownContainer"] { max-width: 92vw !important; }
  .user-bubble { max-width: 92vw !important; }
  .app-header .title { font-size: 0.9rem; }
}
</style>
""",
    unsafe_allow_html=True,
)


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

selected_chat_name = "Anthropic Claude 3.5 Sonnet"
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
  <span class="title">Ask a question based on your knowledge base....</span>
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
            with st.chat_message(msg["role"]):
                cp = st.empty()
                render_message(msg["role"], msg["content"], placeholder=cp)
                placeholders.append(cp)
    return placeholders


placeholders = render_history(chat_container, st.session_state.mode_histories[mode])

user_input = st.chat_input("Ask AI Assistant.")

uploaded_file = None
if mode == "Conversational Mode or RAG":
    uploaded_file = st.sidebar.file_uploader("Drop Your File Here", type=["pdf", "txt", "docx"])
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
                    with st.chat_message("user"):
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
                    with st.chat_message("assistant"):
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
                with st.chat_message("user"):
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
                with st.chat_message("assistant"):
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
            with st.chat_message("user"):
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
            with st.chat_message("assistant"):
                assistant_cp = st.empty()
                placeholders.append(assistant_cp)
                full_response = ""
                with st.spinner(""):
                    for token, _stats in response_stream:
                        full_response += token
                        render_message("assistant", full_response, placeholder=assistant_cp)

        response = full_response
        current_history.append({"role": "assistant", "content": response})
