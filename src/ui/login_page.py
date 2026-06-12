import streamlit as st
from src.auth.supabase_client import sign_in, sign_up

def show_login_page():
    st.markdown('<div class="login-wrap">', unsafe_allow_html=True)
    st.markdown('<div class="login-card">', unsafe_allow_html=True)
    st.markdown('<div class="login-brand">◈ StockPicker</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-sub">AI Investment Terminal</div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["Sign In", "Sign Up"])

    with tab1:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Sign In", use_container_width=True)

            if submit:
                if not email or not password:
                    st.error("Please enter email and password.")
                else:
                    try:
                        # CRITICAL FIX: Removed the hardcoded admin backdoor.
                        # All logins now securely route through Supabase.
                        user_data = sign_in(email, password)
                        if user_data:
                            st.session_state.user = user_data
                            st.rerun()
                    except Exception as e:
                        st.error(f"Login failed: {str(e)}")

    with tab2:
        with st.form("signup_form"):
            new_email = st.text_input("Email")
            new_password = st.text_input("Password", type="password")
            name = st.text_input("Full Name")
            submit_up = st.form_submit_button("Create Account", use_container_width=True)

            if submit_up:
                if not new_email or not new_password or not name:
                    st.error("Please fill all fields.")
                else:
                    try:
                        user_data = sign_up(new_email, new_password, name)
                        if user_data:
                            st.success("Account created! Please sign in.")
                    except Exception as e:
                        st.error(f"Signup failed: {str(e)}")

    st.markdown('</div></div>', unsafe_allow_html=True)