import streamlit as st
from pathlib import Path
import tracemalloc
tracemalloc.start()


UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

from database.database import (
    initialize_database,
    create_chat,
    get_all_chats,
    get_chat_messages,
    save_message,
    delete_chat,
    update_chat_title,
)

from rag.ingestion import ingest_documents, delete_chat_embeddings
from rag.chain import ask_question

# Page Configuration with modern Streamlit options
st.set_page_config(
    page_title="Document QA Assistant",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize database
initialize_database()

# -----------------------
# Session State
# -----------------------
if "chat_id" not in st.session_state:
    st.session_state.chat_id = None


def render_document_uploader(key_suffix: str = ""):
    st.subheader("📂 Upload documents")

    uploaded_files = st.file_uploader(
        "Choose documents (.pdf, .txt, .docx, .md)",
        type=["pdf", "txt", "docx", "md"],
        accept_multiple_files=True,
        key=f"uploader_{key_suffix}",
    )

    if st.button(":material/upload: Process & ingest", key=f"process_btn_{key_suffix}"):
        if not uploaded_files:
            st.warning("Please select at least one document.")
        else:
            is_new_chat = st.session_state.chat_id is None
            if is_new_chat:
                st.session_state.chat_id = create_chat(title="New Chat")

            file_paths = []
            for uploaded_file in uploaded_files:
                file_path = UPLOAD_DIR / uploaded_file.name
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                file_paths.append(file_path)

            with st.spinner("Ingesting documents into vector database..."):
                num_chunks = ingest_documents(
                    file_paths=file_paths,
                    chat_id=st.session_state.chat_id,
                )

            if num_chunks > 0:
                success_msg = f"Ingested {len(file_paths)} document(s) ({num_chunks} chunks)."
                if is_new_chat:
                    with st.spinner("Analyzing document content to generate chat title..."):
                        try:
                            # Ask the RAG system directly what the document is about
                            rag_res = ask_question(
                                query="Summarize the main topic of these uploaded documents in a concise, professional title of 2 to 4 words. Respond with ONLY the title. Do not include quotes, markdown formatting, or preamble.",
                                chat_id=st.session_state.chat_id,
                            )
                            title = rag_res.get("answer", "").strip().strip('"').strip("'").strip("`")
                            if title and "couldn't find" not in title.lower():
                                update_chat_title(st.session_state.chat_id, title)
                            else:
                                update_chat_title(st.session_state.chat_id, uploaded_files[0].name)
                        except Exception:
                            update_chat_title(st.session_state.chat_id, uploaded_files[0].name)
                    
                    st.session_state.ingestion_success = success_msg
                    st.rerun()
                else:
                    st.success(success_msg)
            else:
                if is_new_chat:
                    # Clean up temporary chat if ingestion failed completely
                    delete_chat(st.session_state.chat_id)
                    st.session_state.chat_id = None
                st.error("Failed to ingest documents or document was empty.")


# -----------------------
# Sidebar
# -----------------------
with st.sidebar:
    st.title("📚 Document QA")

    if st.button(":material/add: New chat", type="primary"):
        st.session_state.chat_id = None
        st.rerun()

    st.divider()

    st.subheader("💬 Chat history")
    chats = get_all_chats()

    if not chats:
        st.caption("No chat history available.")

    for chat in chats:
        col1, col2 = st.sidebar.columns([5, 1])
        is_active = (chat["chat_id"] == st.session_state.chat_id)
        btn_label = f":material/chat: {chat['title']}" if is_active else chat["title"]

        with col1:
            if st.button(
                btn_label,
                key=f"chat_{chat['chat_id']}",
            ):
                st.session_state.chat_id = chat["chat_id"]
                st.rerun()

        with col2:
            if st.button(
                ":material/delete:",
                key=f"del_{chat['chat_id']}",
                help="Delete chat",
            ):
                delete_chat(chat["chat_id"])
                delete_chat_embeddings(chat["chat_id"])
                if st.session_state.chat_id == chat["chat_id"]:
                    st.session_state.chat_id = None
                st.rerun()

# -----------------------
# Welcome Screen (No Active Chat)
# -----------------------
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
            st.session_state.chat_id = create_chat()
            st.rerun()
    st.stop()

# -----------------------
# Main Chat Interface
# -----------------------
chats = get_all_chats()
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

for message in messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# -----------------------
# Chat Input & Answer Generation
# -----------------------
if prompt := st.chat_input("Ask something about your documents...", submit_mode="disable"):

    # Update chat title automatically on first user prompt
    if chat_title == "New Chat" and not messages:
        new_title = prompt[:30] + "..." if len(prompt) > 30 else prompt
        update_chat_title(st.session_state.chat_id, new_title)

    # Save and display user message
    save_message(
        chat_id=st.session_state.chat_id,
        role="user",
        content=prompt,
    )

    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate assistant answer
    with st.chat_message("assistant"):
        with st.spinner("Searching documents and generating answer..."):
            try:
                res = ask_question(
                    query=prompt,
                    chat_id=st.session_state.chat_id,
                )
                assistant_response = res.get("answer", "")
                sources = res.get("sources", [])

                if sources:
                    source_lines = []
                    seen_sources = set()
                    for doc in sources:
                        fname = doc.metadata.get("filename", "Unknown file")
                        page = doc.metadata.get("page")
                        label = f"- {fname}" + (f" (Page {page + 1})" if page is not None else "")
                        if label not in seen_sources:
                            seen_sources.add(label)
                            source_lines.append(label)

                    if source_lines:
                        assistant_response += "\n\n**Sources:**\n" + "\n".join(source_lines)

            except Exception as e:
                assistant_response = f"An error occurred while generating the answer: {e}"

            st.markdown(assistant_response)

    save_message(
        chat_id=st.session_state.chat_id,
        role="assistant",
        content=assistant_response,
    )

    st.rerun()