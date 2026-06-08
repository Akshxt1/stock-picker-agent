# src/ui/login_page.py
# Login, register, and guest access screen.
# Called from app.py when st.session_state.user is not set.

import streamlit as st
from src.auth.supabase_auth import sign_in, sign_up, sign_in_as_guest, reset_password_email

# ── CSS specific to login page ────────────────────────────────────────────────
LOGIN_CSS = """
<style>
.login-wrap {
    max-width: 420px; margin: 80px auto 0; padding: 0 1rem;
}
.login-card {
    background: rgba(255,255,255,0.025);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 16px; padding: 36px 32px;
}
.login-brand {
    font-size: 26px; font-weight: 700; letter-spacing: -0.5px;
    background: linear-gradient(120deg,#c7d2fe,#818cf8);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    text-align: center; margin-bottom: 4px;
}
.login-sub {
    font-size: 12px; color: #475569; text-align: center;
    letter-spacing: .1em; text-transform: uppercase; margin-bottom: 28px;
}
.divider-row {
    display: flex; align-items: center; gap: 10px;
    margin: 18px 0; color: #334155; font-size: 12px;
}
.divider-row::before, .divider-row::after {
    content: ""; flex: 1; height: 1px;
    background: rgba(255,255,255,0.06);
}
.guest-btn {
    width: 100%; padding: 10px; border-radius: 8px; cursor: pointer;
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    color: #64748b; font-size: 13px; font-family: 'Outfit',sans-serif;
    transition: all .18s; margin-top: 4px;
}
.guest-btn:hover { background: rgba(255,255,255,0.06); color: #94a3b8; }
.account-tags { display:flex; gap:6px; justify-content:center; margin-top:18px; flex-wrap:wrap; }
.at { display:inline-block;padding:3px 10px;border-radius:4px;font-size:11px;font-weight:500; }
.at-a{background:rgba(239,68,68,.12);color:#ef4444;}
.at-p{background:rgba(99,102,241,.12);color:#818cf8;}
.at-f{background:rgba(16,185,129,.12);color:#10b981;}
.at-g{background:rgba(100,116,139,.12);color:#94a3b8;}
</style>
"""


def show_login_page():
    """
    Render the login/register UI. Sets st.session_state.user on success.
    """
    st.markdown(LOGIN_CSS, unsafe_allow_html=True)
    st.markdown('<div class="login-wrap">', unsafe_allow_html=True)
    st.markdown("""
    <div class="login-card">
      <div class="login-brand">◈ StockPicker</div>
      <div class="login-sub">AI Investment Terminal</div>
    </div>
    """, unsafe_allow_html=True)

    # Tab switcher
    tab_login, tab_register = st.tabs(["Sign In", "Create Account"])

    # ── SIGN IN ───────────────────────────────────────────────────────────────
    with tab_login:
        with st.form("login_form", clear_on_submit=False):
            email    = st.text_input("Email", placeholder="you@example.com",
                                      label_visibility="collapsed")
            password = st.text_input("Password", type="password",
                                      placeholder="Password",
                                      label_visibility="collapsed")
            submitted = st.form_submit_button("Sign In →", use_container_width=True)

            if submitted:
                if not email or not password:
                    st.error("Please enter email and password.")
                else:
                    with st.spinner("Signing in..."):
                        result = sign_in(email, password)
                    if result["success"]:
                        st.session_state.user = result
                        st.success(f"Welcome back, {result['name']} 👋")
                        st.rerun()
                    else:
                        st.error(result["error"])

        # Forgot password
        with st.expander("Forgot password?"):
            reset_email = st.text_input("Enter your email", key="reset_email",
                                         placeholder="you@example.com")
            if st.button("Send reset link", key="reset_btn"):
                if reset_email:
                    r = reset_password_email(reset_email)
                    if r["success"]:
                        st.success("Check your email for a reset link.")
                    else:
                        st.error(r.get("error","Failed to send reset email."))

        # Guest access
        st.markdown('<div class="divider-row">or</div>', unsafe_allow_html=True)
        if st.button("👁 Continue as Guest  (read-only)",
                     use_container_width=True, key="guest_btn"):
            st.session_state.user = sign_in_as_guest()
            st.rerun()

    # ── REGISTER ─────────────────────────────────────────────────────────────
    with tab_register:
        with st.form("register_form", clear_on_submit=True):
            r_name  = st.text_input("Full name",  placeholder="Rahul Sharma",
                                     label_visibility="collapsed")
            r_email = st.text_input("Email",       placeholder="you@example.com",
                                     label_visibility="collapsed", key="r_email")
            r_pass  = st.text_input("Password",    type="password",
                                     placeholder="Min. 6 characters",
                                     label_visibility="collapsed")
            r_pass2 = st.text_input("Confirm",     type="password",
                                     placeholder="Confirm password",
                                     label_visibility="collapsed")
            submitted = st.form_submit_button("Create Account →", use_container_width=True)

            if submitted:
                if not all([r_name, r_email, r_pass, r_pass2]):
                    st.error("All fields are required.")
                elif r_pass != r_pass2:
                    st.error("Passwords don't match.")
                elif len(r_pass) < 6:
                    st.error("Password must be at least 6 characters.")
                else:
                    with st.spinner("Creating account..."):
                        result = sign_up(r_email, r_pass, r_name)
                    if result["success"]:
                        st.success(
                            "✅ Account created! Check your email to confirm, "
                            "then sign in."
                        )
                    else:
                        st.error(result["error"])

    # Account type legend
    st.markdown("""
    <div class="account-tags">
      <span class="at at-a">Admin — full access</span>
      <span class="at at-p">Premium — unlimited runs</span>
      <span class="at at-f">Free — 3 runs/week</span>
      <span class="at at-g">Guest — read-only</span>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)