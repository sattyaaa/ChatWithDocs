import streamlit as st
from database.database import get_all_chats, delete_chat
from rag.ingestion import delete_chat_embeddings

def render_sidebar():
    with st.sidebar:
        st.title("📚 Document QA")
        st.caption(f"Logged in as: **{st.session_state.username}**")
        if st.button("🚪 Log Out", key="logout_btn"):
            st.session_state.authenticated = False
            st.session_state.user_id = None
            st.session_state.username = None
            st.session_state.chat_id = None
            st.rerun()

        st.divider()

        if st.button(":material/add: New chat", type="primary"):
            st.session_state.chat_id = None
            st.rerun()

        st.divider()

        st.subheader("💬 Chat history")
        chats = get_all_chats(st.session_state.user_id)

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
                    try:
                        delete_chat(chat["chat_id"])
                        delete_chat_embeddings(chat["chat_id"], tenant=st.session_state.user_id)
                    except Exception as e:
                        st.error(f"Failed to delete chat record: {e}")
                    if st.session_state.chat_id == chat["chat_id"]:
                        st.session_state.chat_id = None
                    st.rerun()
