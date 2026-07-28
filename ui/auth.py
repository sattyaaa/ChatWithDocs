import streamlit as st
from database.auth import login_user, register_user

def render_auth_screen():
    st.title("📚 Document QA Assistant")
    tab1, tab2 = st.tabs(["🔑 Login", "👤 Sign Up"])
    
    with tab1:
        with st.form("login_form"):
            username = st.text_input("Username").strip()
            password = st.text_input("Password", type="password")
            submit_login = st.form_submit_button("Log In", type="primary")
            if submit_login:
                user = login_user(username, password)
                if user:
                    st.session_state.authenticated = True
                    st.session_state.user_id = user["user_id"]
                    st.session_state.username = user["username"]
                    st.success("Successfully logged in!")
                    st.rerun()
                else:
                    st.error("Invalid username or password.")

    with tab2:
        with st.form("signup_form"):
            new_username = st.text_input("Username").strip()
            new_password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            submit_signup = st.form_submit_button("Sign Up", type="primary")
            if submit_signup:
                if not new_username or not new_password:
                    st.error("Fields cannot be empty.")
                elif new_password != confirm_password:
                    st.error("Passwords do not match.")
                else:
                    try:
                        user_id = register_user(new_username, new_password)
                        # Pre-create Weaviate tenant
                        try:
                            from rag.config import get_client, COLLECTION_NAME
                            c = get_client()
                            collection = c.collections.get(COLLECTION_NAME)
                            collection.tenants.create([user_id])
                        except Exception:
                            # Keep going even if Weaviate auto tenant creation is enabled or setup fails
                            pass
                        st.success("Registration successful! Please log in on the Login tab.")
                    except ValueError as e:
                        st.error(str(e))
                    except Exception as e:
                        st.error(f"Registration failed: {e}")
