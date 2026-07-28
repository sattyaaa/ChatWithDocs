import streamlit as st
import tracemalloc
import logging
tracemalloc.start()

from database.database import (
    initialize_database,
    create_chat,
    get_all_chats,
    get_chat_messages,
    save_message,
    update_chat_title,
)

from ui.auth import render_auth_screen
from ui.sidebar import render_sidebar
from ui.uploader import render_document_uploader
from ui.components import render_sources_badges
from rag.graph import ask_question

# Page Configuration with modern Streamlit options
st.set_page_config(
    page_title="Document QA Assistant",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize database
try:
    initialize_database()
except Exception as e:
    st.error(f"⚠️ **Database Connection Error:** {e}")
    st.info("💡 **Troubleshooting Tip:** This error typically indicates that your IP address is not whitelisted in the MongoDB Atlas settings.")
    st.stop()

# Initialize session state variables
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_id = None
    st.session_state.username = None

if "chat_id" not in st.session_state:
    st.session_state.chat_id = None

# 1. Auth Guard
if not st.session_state.authenticated:
    render_auth_screen()
    st.stop()

# 2. Sidebar Layout
render_sidebar()

# 3. Welcome Screen (No Active Chat Session)
if st.session_state.chat_id is None:
    st.title("📄 Document QA Assistant")
    
    with st.container(border=True):
        st.markdown(
            """
            ### Get started with Document RAG
            1. Upload your files (**PDF, DOCX, TXT, MD**) using the document uploader below.
            2. Click **:material/upload: Process & ingest** to build the search index and start a new chat.
            3. Or click **:material/rocket_launch: Start a new chat** to start with an empty session.
            """
        )
        
        render_document_uploader("welcome")
        
        st.divider()
        if st.button(":material/rocket_launch: Start a new chat", type="primary"):
            try:
                st.session_state.chat_id = create_chat(st.session_state.user_id)
            except Exception as e:
                st.error(f"Failed to start chat: {e}")
                st.stop()
            st.rerun()
    st.stop()

# 4. Main Chat Interface
chats = get_all_chats(st.session_state.user_id)
current_chat = next((c for c in chats if c["chat_id"] == st.session_state.chat_id), None)
chat_title = current_chat["title"] if current_chat else "Chat session"

st.title(f"💬 {chat_title}")

if "ingestion_success" in st.session_state:
    st.success(st.session_state.ingestion_success)
    del st.session_state.ingestion_success

with st.expander("📂 Ingest more documents to this chat"):
    render_document_uploader("active")

# Display message history
messages = get_chat_messages(st.session_state.chat_id)

for msg_idx, message in enumerate(messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("role") == "assistant" and "sources" in message and message["sources"]:
            render_sources_badges(message["sources"], key_prefix=f"hist_btn_{msg_idx}")

# Chat Input & Answer Generation
if prompt := st.chat_input("Ask something about your documents...", submit_mode="disable"):

    # Update chat title automatically on first user prompt
    if chat_title == "New Chat" and not messages:
        new_title = prompt[:30] + "..." if len(prompt) > 30 else prompt
        try:
            update_chat_title(st.session_state.chat_id, new_title)
        except Exception:
            pass

    # Save and display user message
    try:
        save_message(
            chat_id=st.session_state.chat_id,
            role="user",
            content=prompt,
        )
    except Exception as e:
        st.warning("Database write was interrupted, but proceeding...")

    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate assistant answer
    with st.chat_message("assistant"):
        with st.spinner("Searching documents and generating answer..."):
            try:
                res = ask_question(
                    query=prompt,
                    chat_id=st.session_state.chat_id,
                    tenant=st.session_state.user_id,
                )
                assistant_response = res.get("answer", "")
                sources = res.get("sources", [])
                
                source_dicts = []
                for doc in sources:
                    source_dicts.append({
                        "filename": doc.metadata.get("filename", "Unknown file"),
                        "page": doc.metadata.get("page"),
                        "content": doc.page_content
                    })

            except Exception as e:
                assistant_response = f"An error occurred while generating the answer: {e}"
                source_dicts = []

            st.markdown(assistant_response)
            if source_dicts:
                render_sources_badges(source_dicts, key_prefix="new_btn")

    try:
        save_message(
            chat_id=st.session_state.chat_id,
            role="assistant",
            content=assistant_response,
            sources=source_dicts
        )
    except Exception:
        # Ignore thread cancellation exceptions silently
        pass

    st.rerun()