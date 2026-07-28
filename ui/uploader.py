import streamlit as st
from pathlib import Path

from database.database import create_chat, update_chat_title, delete_chat
from rag.ingestion import ingest_documents
from rag.graph import ask_question

UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

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
                try:
                    st.session_state.chat_id = create_chat(st.session_state.user_id, title="New Chat")
                except Exception as e:
                    st.error(f"Failed to create chat session: {e}")
                    st.stop()

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
                    tenant=st.session_state.user_id,
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
                                tenant=st.session_state.user_id,
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
