# src/ui/admin_page.py
# Admin-only dashboard — user management, all activity, API costs.
# Only rendered when st.session_state.user["account_type"] == "admin"

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from src.database.models import Session, UserProfile, ApiUsage, Portfolio, Pick, get_usage_stats


def show_admin_page():
    """Main admin dashboard — called from app.py when admin is logged in."""
    st.markdown('<div class="sdiv">🛡 Admin Dashboard</div>', unsafe_allow_html=True)

    tab_users, tab_usage, tab_activity, tab_manage = st.tabs([
        "👥 Users", "💰 API Costs", "📋 All Activity", "⚙️ Manage Users"
    ])

    with tab_users:   _render_users_tab()
    with tab_usage:   _render_usage_tab()
    with tab_activity:_render_activity_tab()
    with tab_manage:  _render_manage_tab()


# ── Tab 1: Users overview ─────────────────────────────────────────────────────

def _render_users_tab():
    session = Session()
    users   = session.query(UserProfile).order_by(UserProfile.created_at.desc()).all()
    session.close()

    total     = len(users)
    admins    = sum(1 for u in users if u.account_type == "admin")
    premiums  = sum(1 for u in users if u.account_type == "premium")
    frees     = sum(1 for u in users if u.account_type == "free")

    # Metric strip
    st.markdown(f"""
    <div class="metric-strip">
      <div class="mc"><div class="mc-lbl">Total Users</div>
        <div class="mc-val">{total}</div></div>
      <div class="mc"><div class="mc-lbl">Admins</div>
        <div class="mc-val" style="color:#ef4444">{admins}</div></div>
      <div class="mc"><div class="mc-lbl">Premium</div>
        <div class="mc-val" style="color:#818cf8">{premiums}</div></div>
      <div class="mc"><div class="mc-lbl">Free</div>
        <div class="mc-val" style="color:#10b981">{frees}</div></div>
    </div>""", unsafe_allow_html=True)

    if users:
        df = pd.DataFrame([{
            "Name":         u.name,
            "Email":        u.email,
            "Account":      u.account_type.title(),
            "Active":       "✓" if u.is_active else "✗",
            "Joined":       u.created_at.strftime("%d %b %Y"),
        } for u in users])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No users yet.")


# ── Tab 2: API cost dashboard ─────────────────────────────────────────────────

def _render_usage_tab():
    stats = get_usage_stats()   # all users

    total_cost  = stats["total_cost"]
    total_calls = stats["total_calls"]
    total_tok   = stats["total_input"] + stats["total_output"]

    st.markdown(f"""
    <div class="metric-strip">
      <div class="mc"><div class="mc-lbl">Total API Cost</div>
        <div class="mc-val" style="color:#f59e0b">${total_cost:.4f}</div>
        <div class="mc-sub c-mu">all time</div></div>
      <div class="mc"><div class="mc-lbl">Total Calls</div>
        <div class="mc-val">{total_calls:,}</div></div>
      <div class="mc"><div class="mc-lbl">Total Tokens</div>
        <div class="mc-val">{total_tok:,}</div>
        <div class="mc-sub c-mu">in + out</div></div>
      <div class="mc"><div class="mc-lbl">Avg Cost/Call</div>
        <div class="mc-val">${(total_cost/total_calls if total_calls else 0):.4f}</div></div>
    </div>""", unsafe_allow_html=True)

    # Per-user cost table
    st.markdown('<div class="sdiv">Cost by User</div>', unsafe_allow_html=True)
    by_user = stats.get("by_user", {})
    if by_user:
        rows = []
        for uname, s in sorted(by_user.items(), key=lambda x: x[1]["cost"], reverse=True):
            rows.append({
                "User":         uname,
                "Account":      s.get("account_type","—").title(),
                "API Calls":    s["calls"],
                "Total Tokens": f"{s['tokens']:,}",
                "Cost (USD)":   f"${s['cost']:.4f}",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No API usage recorded yet.")

    # Recent calls log
    st.markdown('<div class="sdiv">Recent API Calls</div>', unsafe_allow_html=True)
    recent = stats.get("recent", [])
    if recent:
        st.dataframe(pd.DataFrame(recent), use_container_width=True, hide_index=True)
    else:
        st.info("No recent calls.")


# ── Tab 3: All portfolio activity ─────────────────────────────────────────────

def _render_activity_tab():
    session  = Session()
    positions = session.query(Portfolio).order_by(Portfolio.entry_date.desc()).limit(100).all()
    picks_all = session.query(Pick).order_by(Pick.created_at.desc()).limit(50).all()
    session.close()

    st.markdown('<div class="sdiv">All Portfolio Positions</div>', unsafe_allow_html=True)
    if positions:
        rows = []
        for p in positions:
            rows.append({
                "User":     p.username or "—",
                "Ticker":   p.ticker,
                "Market":   p.market,
                "Qty":      int(p.quantity),
                "Entry":    f"{p.entry_price:,.2f}",
                "Status":   "Open" if p.is_open else "Closed",
                "Date":     p.entry_date.strftime("%d %b %Y"),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No positions yet.")

    st.markdown('<div class="sdiv">All AI Picks Generated</div>', unsafe_allow_html=True)
    if picks_all:
        rows = []
        for p in picks_all:
            rows.append({
                "Date":       p.analysis_date,
                "Ticker":     p.ticker,
                "Market":     p.market,
                "Sector":     p.sector,
                "Confidence": p.confidence,
                "Signal":     p.technical_signal,
                "Sentiment":  p.sentiment,
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No picks generated yet.")


# ── Tab 4: Manage users ───────────────────────────────────────────────────────

def _render_manage_tab():
    st.markdown("Change a user's account type or deactivate their account.")

    session = Session()
    users   = session.query(UserProfile).order_by(UserProfile.name).all()
    session.close()

    if not users:
        st.info("No users to manage.")
        return

    opts      = [f"{u.name} ({u.email})" for u in users]
    selection = st.selectbox("Select user", opts, label_visibility="collapsed")
    sel_user  = users[opts.index(selection)] if selection else None

    if sel_user:
        st.markdown(f"""
        <div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);
                    border-radius:10px;padding:14px 16px;margin-bottom:14px">
          <span style="color:#e2e8f0;font-weight:500">{sel_user.name}</span>
          &nbsp;·&nbsp;
          <span style="color:#64748b;font-size:13px">{sel_user.email}</span>
          &nbsp;·&nbsp;
          <span style="color:#818cf8;font-size:12px">{sel_user.account_type}</span>
        </div>""", unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            new_type = st.selectbox(
                "Change account type",
                ["admin","premium","free"],
                index=["admin","premium","free"].index(
                    sel_user.account_type if sel_user.account_type in ["admin","premium","free"] else "free"
                ),
                key="man_type"
            )
        with col2:
            new_active = st.toggle("Account active", value=sel_user.is_active, key="man_active")

        if st.button("💾 Save Changes", type="primary"):
            session = Session()
            try:
                user = session.query(UserProfile).filter_by(user_id=sel_user.user_id).first()
                if user:
                    user.account_type = new_type
                    user.is_active    = new_active
                    session.commit()
                    st.success(f"✅ {sel_user.name} updated → {new_type}"
                               + (" (active)" if new_active else " (deactivated)"))
                    st.rerun()
            except Exception as e:
                st.error(str(e))
            finally:
                session.close()