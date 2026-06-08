# src/ui/app.py  ─  StockPicker Terminal (Final with Auth + Per-user Portfolio)
# Run: uv run streamlit run src/ui/app.py

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import streamlit as st
import pandas as pd
import yfinance as yf
import pytz, json
from datetime import datetime, timezone, timedelta
from sqlalchemy import or_
from streamlit_option_menu import option_menu

from src.database.models        import init_db, Session, Pick, Portfolio, get_usage_stats
from src.database.paper_trading import (
    add_to_portfolio, sell_position,
    get_portfolio, get_portfolio_metrics, save_picks
)

st.set_page_config(page_title="StockPicker Terminal", page_icon="📊",
                   layout="wide", initial_sidebar_state="expanded")
init_db()

# ═══════════════════════════════════════════════════════════════════════════════
# CSS
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Outfit:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Outfit', sans-serif; color: #e2e8f0; }
.stApp { background: #07080f; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 0 2rem 3rem !important; max-width: 100% !important; }

section[data-testid="stSidebar"] > div:first-child {
    background: #0b0d17 !important;
    border-right: 1px solid rgba(255,255,255,0.05) !important;
    padding: 0 !important;
}
.nav-link { border-radius: 8px !important; margin: 2px 8px !important; }
.nav-link:hover { background: rgba(255,255,255,0.04) !important; }
.nav-link-selected { background: rgba(99,102,241,0.13) !important; }
.nav-link .nav-link-label { font-size: 13px !important; font-weight: 400; }
.nav-link-selected .nav-link-label { font-weight: 500 !important; color: #818cf8 !important; }

.ticker-outer { overflow: hidden; width: 100%; padding: 7px 0; }
.ticker-outer.india {
    background: linear-gradient(90deg,#0f0800,#0b0d17 40%,#0b0d17 60%,#0f0800);
    border-bottom: 1.5px solid rgba(249,115,22,0.25);
}
.ticker-outer.us {
    background: linear-gradient(90deg,#05091a,#0b0d17 40%,#0b0d17 60%,#05091a);
    border-bottom: 1.5px solid rgba(99,102,241,0.25);
}
.ticker-track { display:inline-flex; white-space:nowrap; min-width:200%; animation:scroll-left 70s linear infinite; }
.ticker-track:hover { animation-play-state:paused; }
@keyframes scroll-left { from{transform:translateX(0);} to{transform:translateX(-50%);} }
.t-chip { display:inline-flex; align-items:center; gap:8px; padding:0 20px; border-right:1px solid rgba(255,255,255,0.05); font-family:'IBM Plex Mono',monospace; font-size:11.5px; }
.t-name  { color:#475569; }
.t-price { color:#cbd5e1; font-weight:500; }
.t-up { color:#10b981; font-size:10.5px; }
.t-dn { color:#ef4444; font-size:10.5px; }

.mbar { display:flex; align-items:center; justify-content:space-between; padding:14px 0 16px; border-bottom:1px solid rgba(255,255,255,0.04); margin-bottom:1.6rem; }
.app-brand { font-size:20px; font-weight:700; letter-spacing:-0.5px; background:linear-gradient(120deg,#c7d2fe,#818cf8); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
.app-sub { font-size:10px; color:#334155; letter-spacing:.12em; text-transform:uppercase; margin-top:2px; }
.mkt-pill { display:inline-flex; align-items:center; gap:7px; padding:5px 13px; border-radius:99px; font-size:11.5px; font-weight:500; margin-left:8px; }
.mk-open { background:rgba(16,185,129,.1); border:1px solid rgba(16,185,129,.2); color:#10b981; }
.mk-shut { background:rgba(239,68,68,.07); border:1px solid rgba(239,68,68,.15); color:#ef4444; }
.mk-dot { width:6px; height:6px; border-radius:50%; flex-shrink:0; }
.mk-dot.on  { background:#10b981; animation:blink 2s infinite; }
.mk-dot.off { background:#ef4444; }
@keyframes blink { 0%,100%{opacity:1;} 60%{opacity:.3;} }

.metric-strip { display:grid; grid-template-columns:repeat(4,1fr); gap:10px; margin-bottom:1.8rem; }
.mc { background:rgba(255,255,255,0.022); border:1px solid rgba(255,255,255,0.06); border-radius:10px; padding:16px 18px; transition:border-color .2s; }
.mc:hover { border-color:rgba(255,255,255,0.12); }
.mc-lbl { font-size:10.5px; color:#475569; text-transform:uppercase; letter-spacing:.08em; margin-bottom:6px; }
.mc-val { font-family:'IBM Plex Mono',monospace; font-size:22px; font-weight:600; color:#e2e8f0; line-height:1; }
.mc-sub { font-size:12px; margin-top:5px; }
.c-up{color:#10b981;} .c-dn{color:#ef4444;} .c-mu{color:#64748b;}

.pcard { background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.06); border-radius:12px; padding:16px 18px; margin-bottom:8px; transition:border-color .2s,background .2s; }
.pcard:hover { border-color:rgba(255,255,255,0.12); background:rgba(255,255,255,0.03); }
.pcard.bull { border-left:3px solid #10b981; }
.pcard.bear { border-left:3px solid #ef4444; }
.pcard.neut { border-left:3px solid #f59e0b; }
.pc-sym  { font-family:'IBM Plex Mono',monospace; font-size:17px; font-weight:600; color:#e2e8f0; }
.pc-co   { font-size:12px; color:#475569; margin-top:1px; }
.pc-price{ font-family:'IBM Plex Mono',monospace; font-size:15px; font-weight:500; }
.pc-meta { font-size:11px; color:#334155; margin:9px 0; }
.badge   { display:inline-block; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:500; margin:2px; }
.b-bull{background:rgba(16,185,129,.13);color:#10b981;}
.b-bear{background:rgba(239,68,68,.13);color:#ef4444;}
.b-neut{background:rgba(245,158,11,.13);color:#f59e0b;}
.b-high{background:rgba(99,102,241,.15);color:#818cf8;}
.b-med{background:rgba(148,163,184,.1);color:#94a3b8;}
.b-low{background:rgba(100,116,139,.08);color:#64748b;}

.sdiv { font-size:10.5px; font-weight:500; color:#334155; text-transform:uppercase; letter-spacing:.1em; margin:1.8rem 0 1rem; padding-bottom:8px; border-bottom:1px solid rgba(255,255,255,0.04); }

button[data-baseweb="tab"] { background:transparent !important; border-radius:8px !important; color:#64748b !important; font-size:13px !important; font-family:'Outfit',sans-serif !important; padding:8px 28px !important; font-weight:400 !important; border:none !important; margin:0 2px !important; }
button[data-baseweb="tab"]:hover { background:rgba(255,255,255,0.04) !important; color:#94a3b8 !important; }
button[data-baseweb="tab"][aria-selected="true"] { background:rgba(99,102,241,0.15) !important; color:#818cf8 !important; font-weight:500 !important; }
div[data-baseweb="tab-border"], div[data-baseweb="tab-highlight"] { display:none !important; }
div[data-baseweb="tab-list"] { background:rgba(255,255,255,0.02) !important; border:1px solid rgba(255,255,255,0.06) !important; border-radius:10px !important; padding:4px !important; gap:0 !important; margin-bottom:1.2rem !important; }

.stSelectbox>div>div { background:rgba(255,255,255,0.03) !important; border-color:rgba(255,255,255,0.08) !important; font-size:13px !important; border-radius:8px !important; }
.stNumberInput input { background:rgba(255,255,255,0.03) !important; border-color:rgba(255,255,255,0.08) !important; font-size:13px !important; border-radius:8px !important; color:#e2e8f0 !important; }
.stTextInput input { background:rgba(255,255,255,0.03) !important; border-color:rgba(255,255,255,0.08) !important; font-size:13px !important; border-radius:8px !important; color:#e2e8f0 !important; }
.stButton>button { background:rgba(99,102,241,0.12) !important; border:1px solid rgba(99,102,241,0.25) !important; color:#818cf8 !important; font-size:13px !important; border-radius:8px !important; font-family:'Outfit',sans-serif !important; font-weight:500 !important; padding:6px 18px !important; transition:all .18s !important; }
.stButton>button:hover { background:rgba(99,102,241,0.2) !important; border-color:rgba(99,102,241,0.4) !important; color:#c7d2fe !important; }
.stButton>button[kind="primary"] { background:#4f46e5 !important; border-color:#4f46e5 !important; color:white !important; }
.stButton>button[kind="primary"]:hover { background:#4338ca !important; }
div[data-testid="stExpander"] { background:rgba(255,255,255,0.018) !important; border-color:rgba(255,255,255,0.06) !important; border-radius:8px !important; }
div[data-testid="stForm"] { background:rgba(255,255,255,0.015) !important; border:1px solid rgba(255,255,255,0.06) !important; border-radius:10px !important; padding:16px !important; }

.guest-banner { background:rgba(100,116,139,.08); border:1px solid rgba(100,116,139,.2); border-radius:8px; padding:10px 14px; font-size:12.5px; color:#64748b; margin-bottom:1rem; }

/* Login */
.login-wrap { max-width:440px; margin:60px auto 0; padding:0 1rem; }
.login-card { background:rgba(255,255,255,0.025); border:1px solid rgba(255,255,255,0.07); border-radius:16px; padding:36px 32px; }
.login-brand { font-size:28px; font-weight:700; background:linear-gradient(120deg,#c7d2fe,#818cf8); -webkit-background-clip:text; -webkit-text-fill-color:transparent; text-align:center; margin-bottom:4px; }
.login-sub { font-size:11px; color:#475569; text-align:center; letter-spacing:.1em; text-transform:uppercase; margin-bottom:28px; }
.at-tags { display:flex; gap:5px; justify-content:center; margin-top:20px; flex-wrap:wrap; }
.at { display:inline-block; padding:3px 10px; border-radius:4px; font-size:11px; font-weight:500; }
.at-a{background:rgba(239,68,68,.12);color:#ef4444;}
.at-p{background:rgba(99,102,241,.12);color:#818cf8;}
.at-f{background:rgba(16,185,129,.12);color:#10b981;}
.at-g{background:rgba(100,116,139,.12);color:#94a3b8;}
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# AUTH GATE
# ═══════════════════════════════════════════════════════════════════════════════
if "user" not in st.session_state:
    st.markdown("""
    <style>
    section[data-testid="stSidebar"] { display:none !important; }
    .block-container { max-width:460px !important; margin:0 auto !important; }
    </style>""", unsafe_allow_html=True)
    from src.ui.login_page import show_login_page
    show_login_page()
    st.stop()

_u           = st.session_state.user
CURRENT_USER = _u.get("name", "User")
CURRENT_UID  = _u.get("user_id", "")
ACCOUNT_TYPE = _u.get("account_type", "free")

ACCOUNT_COLORS = {
    "admin":   ("#ef4444", "rgba(239,68,68,.12)"),
    "premium": ("#818cf8", "rgba(99,102,241,.12)"),
    "free":    ("#10b981", "rgba(16,185,129,.12)"),
    "guest":   ("#94a3b8", "rgba(100,116,139,.12)"),
}
ACTION_STYLE = {
    "HOLD":     ("🟡", "rgba(245,158,11,.12)",  "#f59e0b", "Hold"),
    "SELL":     ("🔴", "rgba(239,68,68,.12)",   "#ef4444", "Sell"),
    "BUY_MORE": ("🟢", "rgba(16,185,129,.12)",  "#10b981", "Buy More"),
}

INDIA_SYMS = ("RELIANCE.NS","TCS.NS","HDFCBANK.NS","INFY.NS","ICICIBANK.NS",
               "BHARTIARTL.NS","SBIN.NS","BAJFINANCE.NS","WIPRO.NS","KOTAKBANK.NS",
               "HINDUNILVR.NS","NTPC.NS","MARUTI.NS","AXISBANK.NS","ADANIENT.NS")
US_SYMS    = ("AAPL","MSFT","NVDA","GOOGL","AMZN","META","TSLA",
               "JPM","V","UNH","AMD","CRM","NFLX","GS","INTC")
SCHED_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "scheduler_settings.json")


# ═══════════════════════════════════════════════════════════════════════════════
# ACCOUNT HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
def can_run_analysis() -> bool:
    if ACCOUNT_TYPE == "guest": return False
    if ACCOUNT_TYPE in ("admin", "premium"): return True
    from src.database.models import ApiUsage
    sess     = Session()
    week_ago = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7)
    runs     = sess.query(ApiUsage).filter(
        ApiUsage.user_id  == CURRENT_UID,
        ApiUsage.timestamp >= week_ago,
    ).count()
    sess.close()
    return runs < 3

def runs_remaining():
    if ACCOUNT_TYPE != "free": return None
    from src.database.models import ApiUsage
    sess     = Session()
    week_ago = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7)
    used     = sess.query(ApiUsage).filter(
        ApiUsage.user_id   == CURRENT_UID,
        ApiUsage.timestamp >= week_ago,
    ).count()
    sess.close()
    return max(0, 3 - used)

def run_denied_msg():
    if ACCOUNT_TYPE == "guest":
        return "👁 Guest accounts cannot run analysis. Create a free account to get 3 runs/week."
    return "⏳ Weekly limit reached (3/3). Upgrade to Premium for unlimited access."


# ═══════════════════════════════════════════════════════════════════════════════
# DATA HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=300)
def fetch_tape(syms: tuple, cur: str) -> list:
    try:
        raw   = yf.download(list(syms), period="2d", auto_adjust=True, progress=False, threads=True)
        close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw
        out   = []
        for s in syms:
            try:
                col = close[s]; p = float(col.iloc[-1])
                prev = float(col.iloc[-2]) if len(col) >= 2 else p
                chg  = (p - prev) / prev * 100 if prev else 0.0
                out.append({"sym": s.replace(".NS","").replace(".BO",""), "p":p, "chg":chg, "cur":cur})
            except Exception: pass
        return out
    except Exception: return []

@st.cache_data(ttl=60)
def market_status() -> dict:
    now = datetime.now(timezone.utc)
    ni  = now.astimezone(pytz.timezone("Asia/Kolkata"))
    ne  = now.astimezone(pytz.timezone("America/New_York"))
    def m(dt): return dt.hour * 60 + dt.minute
    return {
        "nse":  {"open": ni.weekday()<5 and 9*60+15<=m(ni)<=15*60+30, "time": ni.strftime("%I:%M %p IST"), "label": "NSE / BSE"},
        "nyse": {"open": ne.weekday()<5 and 9*60+30<=m(ne)<=16*60,    "time": ne.strftime("%I:%M %p ET"),  "label": "NYSE / NASDAQ"},
    }

@st.cache_data(ttl=60)
def get_user_open_tickers(uid: str) -> set:
    if not uid or uid == "guest": return set()
    sess = Session()
    rows = sess.query(Portfolio).filter(
        Portfolio.is_open == True,
        or_(Portfolio.user_id  == uid,
            Portfolio.username == uid)
    ).all()
    sess.close()
    return {r.ticker for r in rows}

@st.cache_data(ttl=120)
def cached_portfolio(market=None, uid=None):
    return get_portfolio(market=market, username=uid)

@st.cache_data(ttl=120)
def cached_metrics(uid=None):
    return get_portfolio_metrics(username=uid)

@st.cache_data(ttl=600)
def usd_inr_rate() -> float:
    try:
        h = yf.Ticker("USDINR=X").history(period="1d")
        if not h.empty: return round(float(h["Close"].iloc[-1]), 2)
    except Exception: pass
    return 84.0

def cs(m): return "₹" if m in ("INDIA","INR") else "$"

def sbadge(s):
    c = {"Bullish":"b-bull","Bearish":"b-bear"}.get(s,"b-neut")
    return f'<span class="badge {c}">{s or "—"}</span>'

def cbadge(c):
    cl = {"High":"b-high","Medium":"b-med","Low":"b-low"}.get(c,"b-low")
    return f'<span class="badge {cl}">{c or "—"} confidence</span>'

def load_sched():
    if os.path.exists(SCHED_FILE):
        with open(SCHED_FILE) as f: return json.load(f)
    return {"enabled":False,"day":"mon","hour":6,"minute":0,"markets":["INDIA","US"],"last_run":None}

def save_sched(cfg):
    with open(SCHED_FILE,"w") as f: json.dump(cfg,f,indent=2)

def picks_db(market=None, sector=None, size=None, limit=60):
    s = Session(); q = s.query(Pick)
    if market: q = q.filter(Pick.market == market)
    if sector: q = q.filter(Pick.sector == sector)
    if size:   q = q.filter(Pick.size   == size)
    out = q.order_by(Pick.created_at.desc()).limit(limit).all()
    s.close(); return out

def sectors_db(mkt):
    s = Session()
    r = s.query(Pick.sector).filter(Pick.market == mkt).distinct().all()
    s.close(); return sorted([x[0] for x in r])

def sizes_db(mkt):
    s = Session()
    r = s.query(Pick.size).filter(Pick.market == mkt).distinct().all()
    s.close(); return sorted([x[0] for x in r])


# ═══════════════════════════════════════════════════════════════════════════════
# RENDER HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
def render_ticker(mode="both"):
    if mode in ("both","india"): items, cls = fetch_tape(INDIA_SYMS,"₹"), "india"
    else:                        items, cls = fetch_tape(US_SYMS,"$"),    "us"
    if not items: return
    def chip(it):
        cc = "t-up" if it["chg"]>=0 else "t-dn"; arr = "▲" if it["chg"]>=0 else "▼"
        return (f'<span class="t-chip"><span class="t-name">{it["sym"]}</span>'
                f'<span class="t-price">{it["cur"]}{it["p"]:,.2f}</span>'
                f'<span class="{cc}">{arr}{abs(it["chg"]):.2f}%</span></span>')
    inner = "".join(chip(i) for i in items)
    st.markdown(f'<div class="ticker-outer {cls}"><div class="ticker-track">{inner}{inner}</div></div>',
                unsafe_allow_html=True)

def render_mbar():
    s = market_status()
    def pill(info):
        cls = "mk-open" if info["open"] else "mk-shut"
        dot = "on"      if info["open"] else "off"
        txt = "Open"    if info["open"] else "Closed"
        return (f'<span class="mkt-pill {cls}"><span class="mk-dot {dot}"></span>'
                f'{info["label"]} &nbsp;·&nbsp; {txt} &nbsp;·&nbsp; {info["time"]}</span>')
    st.markdown(f'<div class="mbar"><div><div class="app-brand">◈ StockPicker</div>'
                f'<div class="app-sub">AI Investment Terminal</div></div>'
                f'<div>{pill(s["nse"])}{pill(s["nyse"])}</div></div>', unsafe_allow_html=True)

def guest_banner():
    if ACCOUNT_TYPE == "guest":
        st.markdown('<div class="guest-banner">👁 Guest mode — read only. '
                    'Create a free account to add picks and run AI analysis.</div>',
                    unsafe_allow_html=True)

def render_pick_card(p, prefix="", user_tickers: set = None):
    """
    Renders one pick card.
    user_tickers = set of tickers the CURRENT USER has open.
    Each user sees their own Add / ✓ state independently.
    """
    cls        = {"Bullish":"bull","Bearish":"bear"}.get(p.sentiment or "","neut")
    cur        = cs(p.currency or p.market)
    sym        = p.ticker.replace(".NS","").replace(".BO","")
    already_in = p.ticker in (user_tickers or set())

    st.markdown(f"""
    <div class="pcard {cls}">
      <div style="display:flex;justify-content:space-between;align-items:flex-start">
        <div><div class="pc-sym">{sym}</div><div class="pc-co">{p.company[:38]}</div></div>
        <div style="text-align:right">
          <div class="pc-price">{cur}{p.price_at_pick:,.2f}</div>
          <div style="margin-top:6px">{sbadge(p.technical_signal)}{sbadge(p.sentiment)}{cbadge(p.confidence)}</div>
        </div>
      </div>
      <div class="pc-meta">{p.sector} &nbsp;·&nbsp; {p.size} Cap &nbsp;·&nbsp; {p.analysis_date}</div>
    </div>""", unsafe_allow_html=True)

    c_det, c_add = st.columns([5, 1])
    with c_det:
        with st.expander("Analysis details"):
            w1, w2 = st.columns(2)
            with w1:
                st.markdown("**Why Buy**")
                for pt in (p.why_buy or []):
                    st.markdown(f"<div style='font-size:12.5px;color:#94a3b8;margin-bottom:5px;line-height:1.5'>• {pt}</div>", unsafe_allow_html=True)
            with w2:
                st.markdown("**Why Not Buy**")
                for pt in (p.why_not_buy or []):
                    st.markdown(f"<div style='font-size:12.5px;color:#64748b;margin-bottom:5px;line-height:1.5'>• {pt}</div>", unsafe_allow_html=True)

    with c_add:
        if ACCOUNT_TYPE == "guest":
            st.caption("Sign in\nto add")
        elif already_in:
            # This USER already has this stock open
            st.markdown('<div style="text-align:center;padding:8px 0;font-size:18px">✓</div>',
                        unsafe_allow_html=True)
            st.caption("In portfolio")
        else:
            # Show add button for this user
            qty = st.number_input("", 1, 10000, 10, 5,
                                  key=f"q_{prefix}_{p.id}",
                                  label_visibility="collapsed")
            if st.button("＋ Add", key=f"a_{prefix}_{p.id}", use_container_width=True):
                try:
                    add_to_portfolio(p.ticker, qty,
                                     user_id=CURRENT_UID,
                                     username=CURRENT_USER,
                                     pick_id=p.id)
                    st.cache_data.clear()
                    st.success("Added!")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))


def render_analysis_card(res: dict):
    action = res.get("action","HOLD")
    icon, bg, color, label = ACTION_STYLE.get(action, ACTION_STYLE["HOLD"])
    reasons_html = "".join(
        f'<li style="margin-bottom:4px;color:#94a3b8;font-size:12.5px">{r}</li>'
        for r in res.get("reasons",[]))
    targets = ""
    try:
        sl = res.get("stop_loss"); tp = res.get("target_price")
        sl_v = float(sl) if sl and str(sl).lower() not in ("null","none","") else None
        tp_v = float(tp) if tp and str(tp).lower() not in ("null","none","") else None
        if sl_v: targets += f'<span style="color:#ef4444;font-size:12px;margin-right:14px">Stop Loss: {sl_v:,.2f}</span>'
        if tp_v: targets += f'<span style="color:#10b981;font-size:12px">Target: {tp_v:,.2f}</span>'
    except Exception: pass

    st.markdown(f"""
    <div style="background:{bg};border:1px solid {color}33;border-radius:10px;padding:14px 16px;margin-bottom:8px">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
        <div>
          <span style="font-family:'IBM Plex Mono',monospace;font-weight:600;color:#e2e8f0;font-size:14px">
            {res.get('ticker','').replace('.NS','').replace('.BO','')}
          </span>
          <span style="margin-left:10px;font-size:20px">{icon}</span>
          <span style="margin-left:6px;font-weight:600;color:{color};font-size:13px">{label}</span>
        </div>
        <span style="font-size:11px;color:#64748b;background:rgba(255,255,255,0.04);padding:2px 8px;border-radius:4px">
          {res.get('confidence','')} confidence
        </span>
      </div>
      <div style="font-size:13px;color:#cbd5e1;margin-bottom:8px;font-style:italic">{res.get('summary','')}</div>
      <ul style="margin:0;padding-left:16px">{reasons_html}</ul>
      {f'<div style="margin-top:8px">{targets}</div>' if targets else ''}
    </div>""", unsafe_allow_html=True)


def render_ptab(market=None, pfx="all"):
    h    = cached_portfolio(market=market, uid=CURRENT_UID)
    rate = usd_inr_rate()

    # Currency toggle — All tab only
    display_inr = True
    if pfx == "all":
        tl, tr = st.columns([3, 1])
        with tr:
            tog = st.radio("", ["₹ INR","$ USD"], horizontal=True,
                           key="curr_tog", label_visibility="collapsed")
            display_inr = (tog == "₹ INR")
        tl.markdown(f'<div style="font-size:11.5px;color:#475569;padding-top:6px">Live rate &nbsp;·&nbsp; '
                    f'<span style="color:#818cf8;font-family:IBM Plex Mono,monospace">1 USD = ₹{rate:.2f}</span></div>',
                    unsafe_allow_html=True)

    if h:
        # Build display rows with currency conversion
        disp = []
        for x in h:
            dx = dict(x)
            if pfx == "all":
                if display_inr and dx["currency"] == "USD":
                    for k in ("entry_price","current_price","invested","current_value","pnl_amount"):
                        dx[k] *= rate
                    dx["dcur"] = "₹"
                elif not display_inr and dx["currency"] == "INR":
                    for k in ("entry_price","current_price","invested","current_value","pnl_amount"):
                        dx[k] /= rate
                    dx["dcur"] = "$"
                else:
                    dx["dcur"] = "₹" if dx["currency"] == "INR" else "$"
            else:
                dx["dcur"] = "₹" if market == "INDIA" else "$"
            disp.append(dx)

        inv = sum(x["invested"]      for x in disp)
        val = sum(x["current_value"] for x in disp)
        pnl = val - inv
        pct = pnl / inv * 100 if inv else 0
        pc  = "c-up" if pnl >= 0 else "c-dn"
        cur = disp[0]["dcur"] if disp else ""

        st.markdown(f"""
        <div class="metric-strip" style="grid-template-columns:repeat(3,1fr);margin-bottom:1.2rem">
          <div class="mc"><div class="mc-lbl">Invested</div><div class="mc-val" style="font-size:18px">{cur}{inv:,.2f}</div></div>
          <div class="mc"><div class="mc-lbl">Current Value</div><div class="mc-val" style="font-size:18px">{cur}{val:,.2f}</div></div>
          <div class="mc"><div class="mc-lbl">Unrealised P&L</div><div class="mc-val {pc}" style="font-size:18px">{cur}{pnl:+,.2f}</div><div class="mc-sub {pc}">{pct:+.2f}%</div></div>
        </div>""", unsafe_allow_html=True)

        rows = []
        for x in disp:
            c = x["dcur"]
            rows.append({
                "Ticker":  x["ticker"].replace(".NS","").replace(".BO",""),
                "Company": x["company"][:22],
                "Market":  x["market"],
                "Entry":   f"{c}{x['entry_price']:,.2f}",
                "Current": f"{c}{x['current_price']:,.2f}",
                "Qty":     int(x["quantity"]),
                "P&L %":   x["pnl_pct"],
                "P&L Amt": f"{c}{x['pnl_amount']:+,.2f}",
                "Days":    x["days_held"],
            })
        df = pd.DataFrame(rows)
        st.dataframe(
            df.style
              .map(lambda v: f"color:{'#10b981' if v>=0 else '#ef4444'}", subset=["P&L %"])
              .format({"P&L %": "{:+.2f}%"})
              .hide(axis="index"),
            use_container_width=True, hide_index=True)
    else:
        st.markdown('<div style="color:#334155;text-align:center;padding:2rem 0;font-size:14px">No open positions</div>',
                    unsafe_allow_html=True)

    if ACCOUNT_TYPE == "guest":
        st.markdown('<div class="guest-banner">👁 Sign in to add positions and get AI analysis.</div>',
                    unsafe_allow_html=True)
        return

    # AI Analysis
    st.markdown('<div class="sdiv">🤖 AI Portfolio Analysis</div>', unsafe_allow_html=True)
    if not h:
        st.caption("Add positions first.")
    else:
        cb, ci = st.columns([1, 3])
        with cb:
            run_ai = st.button("🤖 Analyse Positions", key=f"run_ai_btn_{pfx}", use_container_width=True)
        with ci:
            st.markdown('<div style="font-size:12px;color:#475569;padding-top:8px">Claude Haiku · ~5 sec/stock · ~$0.001/position</div>',
                        unsafe_allow_html=True)
        if run_ai:
            with st.spinner("AI reading your positions..."):
                from src.agents.portfolio_analyzer import analyze_all_positions
                st.session_state[f"ai_results_{pfx}"] = analyze_all_positions(
                    market=market, user_id=CURRENT_UID)
        if f"ai_results_{pfx}" in st.session_state:
            results = st.session_state[f"ai_results_{pfx}"]
            if isinstance(results, list) and results:
                acts = [r.get("action","HOLD") for r in results]
                st.markdown(f"""
                <div style="display:flex;gap:10px;margin-bottom:12px">
                  <span style="background:rgba(16,185,129,.1);border:1px solid rgba(16,185,129,.2);color:#10b981;padding:4px 14px;border-radius:6px;font-size:12px">🟢 Buy More: {acts.count("BUY_MORE")}</span>
                  <span style="background:rgba(245,158,11,.1);border:1px solid rgba(245,158,11,.2);color:#f59e0b;padding:4px 14px;border-radius:6px;font-size:12px">🟡 Hold: {acts.count("HOLD")}</span>
                  <span style="background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.2);color:#ef4444;padding:4px 14px;border-radius:6px;font-size:12px">🔴 Sell: {acts.count("SELL")}</span>
                </div>""", unsafe_allow_html=True)
                for res in results:
                    render_analysis_card(res)

    # Add Position
    st.markdown('<div class="sdiv">➕ Add Position</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:12px;color:#475569;margin-bottom:12px">Enter your actual buy price, or leave as 0 for live market price.</div>',
                unsafe_allow_html=True)
    with st.form(key=f"add_{pfx}", clear_on_submit=True):
        a1, a2, a3, a4 = st.columns([2, 1.5, 1.5, 2])
        new_ticker = a1.text_input("Ticker *",  placeholder="WIPRO.NS  or  AAPL")
        new_price  = a2.number_input("Entry Price", min_value=0.0, value=0.0, step=0.01, format="%.2f")
        new_qty    = a3.number_input("Quantity *", min_value=1, value=10, step=1)
        new_date   = a4.text_input("Buy Date", placeholder="YYYY-MM-DD  (optional)")
        new_notes  = st.text_input("Notes", placeholder="e.g. Bought after earnings dip  (optional)")
        if st.form_submit_button("➕ Add to Portfolio", use_container_width=True):
            if not new_ticker.strip():
                st.error("Ticker is required.")
            else:
                try:
                    add_to_portfolio(
                        ticker       = new_ticker.strip().upper(),
                        quantity     = new_qty,
                        user_id      = CURRENT_UID,
                        username     = CURRENT_USER,
                        custom_price = new_price if new_price > 0 else None,
                        custom_date  = new_date.strip() or None,
                        notes        = new_notes.strip() or None,
                    )
                    st.cache_data.clear()
                    pn = f"@ {new_price:,.2f}" if new_price > 0 else "@ live price"
                    st.success(f"✅ Added {new_ticker.upper()} × {new_qty} {pn}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    # Close Position
    if h:
        st.markdown('<div class="sdiv">💰 Close Position</div>', unsafe_allow_html=True)
        with st.form(key=f"sell_{pfx}", clear_on_submit=True):
            opts = [f"{x['id']}  ·  {x['ticker']}  ·  {int(x['quantity'])} shares  ·  P&L: {x['pnl_pct']:+.2f}%"
                    for x in h]
            sel     = st.selectbox("Position", opts, label_visibility="collapsed")
            s1, s2  = st.columns([2, 3])
            exit_p  = s1.number_input("Exit Price (0=live)", min_value=0.0, value=0.0, step=0.01, format="%.2f")
            sell_n  = s2.text_input("Notes", placeholder="e.g. Taking profit")
            if st.form_submit_button("💰 Sell Position", use_container_width=True) and sel:
                pid = int(sel.split("·")[0].strip())
                try:
                    r = sell_position(pid, notes=sell_n or None,
                                      custom_price=exit_p if exit_p > 0 else None)
                    st.cache_data.clear()
                    for k in [f"ai_results_{pfx}"]:
                        if k in st.session_state: del st.session_state[k]
                    em = "🟢" if r["pnl_amount"] >= 0 else "🔴"
                    st.success(f"{em} {r['ticker']} sold · P&L: {r['pnl_pct']:+.2f}%")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    ac, ab = ACCOUNT_COLORS.get(ACCOUNT_TYPE, ("#94a3b8","rgba(100,116,139,.12)"))
    st.markdown(f"""
    <div style="padding:20px 16px 10px">
      <div style="font-size:20px;font-weight:700;letter-spacing:-0.5px;
                  background:linear-gradient(120deg,#c7d2fe,#818cf8);
                  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                  font-family:'Outfit',sans-serif;margin-bottom:12px">◈ StockPicker</div>
      <div style="background:{ab};border:1px solid {ac}33;border-radius:8px;
                  padding:10px 12px;display:flex;align-items:center;gap:10px">
        <div style="width:32px;height:32px;border-radius:50%;
                    background:linear-gradient(135deg,{ac},{ac}66);
                    display:flex;align-items:center;justify-content:center;
                    font-size:14px;font-weight:700;color:#07080f;flex-shrink:0">
          {CURRENT_USER[0].upper()}
        </div>
        <div>
          <div style="font-size:13px;font-weight:500;color:#e2e8f0">{CURRENT_USER}</div>
          <div style="font-size:10px;color:{ac};text-transform:uppercase;letter-spacing:.07em;margin-top:1px">{ACCOUNT_TYPE}</div>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

    nav_opts  = ["Dashboard","India","US Markets","Portfolio","Metrics","Settings"]
    nav_icons = ["grid-3x3-gap-fill","currency-rupee","currency-dollar",
                 "graph-up-arrow","bar-chart-line-fill","gear-fill"]
    if ACCOUNT_TYPE == "admin":
        nav_opts.insert(1, "Admin")
        nav_icons.insert(1, "shield-fill")

    page = option_menu(
        menu_title=None, options=nav_opts, icons=nav_icons, default_index=0,
        styles={
            "container":         {"background":"transparent","padding":"0 8px"},
            "menu-icon":         {"display":"none"},
            "nav-link":          {"font-size":"13px","color":"#64748b",
                                  "font-family":"'Outfit',sans-serif","padding":"9px 14px",
                                  "border-radius":"8px","margin":"2px 0",
                                  "--hover-color":"rgba(255,255,255,0.04)"},
            "nav-link-selected": {"background":"rgba(99,102,241,0.12)",
                                  "color":"#818cf8","font-weight":"500"},
            "icon":              {"font-size":"14px"},
        })

    st.markdown('<hr style="border:none;border-top:1px solid rgba(255,255,255,0.05);margin:8px 0">',
                unsafe_allow_html=True)

    rem = runs_remaining()
    if rem is not None:
        pct_bar   = rem / 3
        bar_color = "#10b981" if pct_bar > 0.5 else "#f59e0b" if pct_bar > 0 else "#ef4444"
        st.markdown(f"""
        <div style="padding:0 12px;margin-bottom:10px">
          <div style="font-size:10px;color:#334155;text-transform:uppercase;letter-spacing:.1em;margin-bottom:6px">Weekly Runs</div>
          <div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);border-radius:8px;padding:10px 12px">
            <span style="font-size:13px;color:{bar_color};font-weight:500">{rem} / 3 remaining</span>
            <div style="height:3px;background:rgba(255,255,255,0.05);border-radius:2px;margin-top:8px;overflow:hidden">
              <div style="height:100%;width:{int(pct_bar*100)}%;background:{bar_color};border-radius:2px"></div>
            </div>
          </div>
        </div>""", unsafe_allow_html=True)

    cfg = load_sched()
    dc  = "#10b981" if cfg["enabled"] else "#ef4444"
    dl  = "Active"  if cfg["enabled"] else "Off"
    nr  = (f'<div style="color:#6366f1;font-size:11px;margin-top:5px">Every {cfg["day"].title()} at {cfg["hour"]:02d}:{cfg["minute"]:02d}</div>'
           if cfg["enabled"] else "")
    st.markdown(f"""
    <div style="padding:0 12px;margin-bottom:10px">
      <div style="font-size:10px;color:#334155;text-transform:uppercase;letter-spacing:.1em;margin-bottom:8px">Auto Scheduler</div>
      <div style="background:rgba(255,255,255,0.025);border:1px solid rgba(255,255,255,0.06);border-radius:8px;padding:10px 13px">
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span style="color:#94a3b8;font-size:12.5px">Schedule</span>
          <span style="display:flex;align-items:center;gap:6px;color:#94a3b8;font-size:12px">
            <span style="width:6px;height:6px;border-radius:50%;background:{dc};display:inline-block"></span>{dl}
          </span>
        </div>{nr}
      </div>
    </div>""", unsafe_allow_html=True)

    ca, cb = st.columns(2)
    with ca:
        if st.button("▶ Run", use_container_width=True, key="sb_run"):
            if not can_run_analysis():
                st.error(run_denied_msg())
            else:
                st.session_state["quick_run"] = True
    with cb:
        if st.button("↻ Refresh", use_container_width=True, key="sb_ref"):
            st.cache_data.clear(); st.rerun()

    st.markdown("")
    if st.button("⎋ Sign Out", use_container_width=True, key="signout"):
        if ACCOUNT_TYPE != "guest":
            try:
                from src.auth.supabase_auth import sign_out
                sign_out()
            except Exception: pass
        del st.session_state["user"]
        st.cache_data.clear(); st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE ROUTING
# ═══════════════════════════════════════════════════════════════════════════════
def _run_crew(rm, rs, rz):
    from src.agents.crew import run_stock_picker
    res = run_stock_picker(rm, rs, rz, user_id=CURRENT_UID, username=CURRENT_USER)
    if res.get("picks"):
        save_picks(res); st.cache_data.clear()
        st.success(f"✅ {len(res['picks'])} picks saved!")
    else:
        st.warning("No picks returned.")


# ── DASHBOARD ─────────────────────────────────────────────────────────────────
if page == "Dashboard":
    render_ticker("both"); render_mbar(); guest_banner()
    m   = cached_metrics(uid=CURRENT_UID)
    inv = m.get("total_invested",0) or 0; val = m.get("current_value",0) or 0
    pnl = m.get("unrealised_pnl",0) or 0; pct = m.get("unrealised_pnl_pct",0) or 0
    wr  = m.get("win_rate"); pc = "c-up" if pnl>=0 else "c-dn"; arr = "▲" if pnl>=0 else "▼"
    st.markdown(f"""
    <div class="metric-strip">
      <div class="mc"><div class="mc-lbl">Portfolio Value</div><div class="mc-val">{val:,.0f}</div><div class="mc-sub c-mu">Invested: {inv:,.0f}</div></div>
      <div class="mc"><div class="mc-lbl">Unrealised P&L</div><div class="mc-val {pc}">{arr} {abs(pnl):,.0f}</div><div class="mc-sub {pc}">{pct:+.2f}%</div></div>
      <div class="mc"><div class="mc-lbl">Win Rate</div><div class="mc-val">{f"{wr}%" if wr else "—"}</div><div class="mc-sub c-mu">{m.get('wins',0)} W / {m.get('losses',0)} L</div></div>
      <div class="mc"><div class="mc-lbl">Positions</div><div class="mc-val">{m.get('open_positions',0)}</div><div class="mc-sub c-mu">{m.get('closed_positions',0)} closed</div></div>
    </div>""", unsafe_allow_html=True)

    if st.session_state.get("quick_run"):
        st.session_state.pop("quick_run")
        st.markdown('<div class="sdiv">Run Analysis</div>', unsafe_allow_html=True)
        from src.data.stock_universe import get_all_sectors, get_all_sizes
        c1, c2, c3 = st.columns(3)
        rm = c1.selectbox("Market", ["INDIA","US"], key="d_mkt")
        rs = c2.selectbox("Sector", get_all_sectors(rm), key="d_sec")
        rz = c3.selectbox("Size",   get_all_sizes(rm),   key="d_siz")
        if st.button("🚀 Launch Crew", type="primary"):
            with st.spinner(f"4 agents: {rm} · {rs} · {rz}  (2-4 min)"):
                try: _run_crew(rm, rs, rz)
                except Exception as e: st.error(str(e))

    st.markdown('<div class="sdiv">Recent Picks</div>', unsafe_allow_html=True)
    recent = picks_db(limit=6)
    if recent:
        user_tickers = get_user_open_tickers(CURRENT_UID)
        c1, c2 = st.columns(2)
        for i, p in enumerate(recent):
            with (c1 if i%2==0 else c2):
                render_pick_card(p, "dash", user_tickers)
    else:
        st.markdown('<div style="color:#334155;text-align:center;padding:4rem 0;font-size:14px">No picks yet — click ▶ Run in the sidebar</div>',
                    unsafe_allow_html=True)


# ── ADMIN ─────────────────────────────────────────────────────────────────────
elif page == "Admin":
    if ACCOUNT_TYPE != "admin":
        st.error("Access denied."); st.stop()
    render_mbar()
    from src.ui.admin_page import show_admin_page
    show_admin_page()


# ── INDIA ─────────────────────────────────────────────────────────────────────
elif page == "India":
    render_ticker("india"); render_mbar(); guest_banner()
    st.markdown('<div class="sdiv">Indian Market Picks &nbsp;·&nbsp; NSE / BSE</div>',
                unsafe_allow_html=True)
    secs = sectors_db("INDIA"); szs = sizes_db("INDIA")
    if not secs:
        st.markdown('<div style="color:#334155;text-align:center;padding:4rem 0">No India picks yet.</div>',
                    unsafe_allow_html=True)
    else:
        c1, c2 = st.columns(2)
        ss = c1.selectbox("Sector", ["All"]+secs, key="in_sec")
        sz = c2.selectbox("Size",   ["All"]+szs,  key="in_siz")
        picks        = picks_db("INDIA", None if ss=="All" else ss, None if sz=="All" else sz)
        user_tickers = get_user_open_tickers(CURRENT_UID)
        st.caption(f"{len(picks)} picks · India")
        ca, cb = st.columns(2)
        for i, p in enumerate(picks):
            with (ca if i%2==0 else cb):
                render_pick_card(p, "in", user_tickers)


# ── US MARKETS ────────────────────────────────────────────────────────────────
elif page == "US Markets":
    render_ticker("us"); render_mbar(); guest_banner()
    st.markdown('<div class="sdiv">US Market Picks &nbsp;·&nbsp; NYSE / NASDAQ</div>',
                unsafe_allow_html=True)
    secs = sectors_db("US"); szs = sizes_db("US")
    if not secs:
        st.markdown('<div style="color:#334155;text-align:center;padding:4rem 0">No US picks yet.</div>',
                    unsafe_allow_html=True)
    else:
        c1, c2 = st.columns(2)
        ss = c1.selectbox("Sector", ["All"]+secs, key="us_sec")
        sz = c2.selectbox("Size",   ["All"]+szs,  key="us_siz")
        picks        = picks_db("US", None if ss=="All" else ss, None if sz=="All" else sz)
        user_tickers = get_user_open_tickers(CURRENT_UID)
        st.caption(f"{len(picks)} picks · US")
        ca, cb = st.columns(2)
        for i, p in enumerate(picks):
            with (ca if i%2==0 else cb):
                render_pick_card(p, "us", user_tickers)


# ── PORTFOLIO ─────────────────────────────────────────────────────────────────
elif page == "Portfolio":
    render_ticker("both"); render_mbar()
    st.markdown('<div class="sdiv">Paper Trading Portfolio</div>', unsafe_allow_html=True)
    t_in, t_us, t_all = st.tabs(["🇮🇳  India", "🇺🇸  US", "🌐  All"])
    with t_in:  render_ptab("INDIA", "in")
    with t_us:  render_ptab("US",    "us")
    with t_all: render_ptab(None,    "all")


# ── METRICS ───────────────────────────────────────────────────────────────────
elif page == "Metrics":
    render_ticker("both"); render_mbar()
    st.markdown('<div class="sdiv">Performance Analytics</div>', unsafe_allow_html=True)
    m   = cached_metrics(uid=CURRENT_UID)
    bp  = m.get("best_pick");  bpp = m.get("best_pick_pct")
    wp  = m.get("worst_pick"); wpp = m.get("worst_pick_pct")
    wr  = m.get("win_rate")
    st.markdown(f"""
    <div class="metric-strip">
      <div class="mc"><div class="mc-lbl">Win Rate</div><div class="mc-val">{f"{wr}%" if wr else "—"}</div><div class="mc-sub c-mu">{m.get('wins',0)} W · {m.get('losses',0)} L</div></div>
      <div class="mc"><div class="mc-lbl">Open / Closed</div><div class="mc-val">{m.get('open_positions',0)} / {m.get('closed_positions',0)}</div></div>
      <div class="mc"><div class="mc-lbl">Best Pick</div><div class="mc-val c-up">{f"{bpp:+.1f}%" if bpp else "—"}</div><div class="mc-sub c-mu">{bp or "No closed trades"}</div></div>
      <div class="mc"><div class="mc-lbl">Worst Pick</div><div class="mc-val c-dn">{f"{wpp:+.1f}%" if wpp else "—"}</div><div class="mc-sub c-mu">{wp or "No closed trades"}</div></div>
    </div>""", unsafe_allow_html=True)

    if ACCOUNT_TYPE != "guest":
        st.markdown('<div class="sdiv">My API Usage</div>', unsafe_allow_html=True)
        my_stats = get_usage_stats(user_id=CURRENT_UID)
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Calls",  my_stats["total_calls"])
        c2.metric("Total Cost",   f"${my_stats['total_cost']:.4f}")
        c3.metric("Total Tokens", f"{my_stats['total_input']+my_stats['total_output']:,}")

    st.markdown('<div class="sdiv">All Picks History</div>', unsafe_allow_html=True)
    sess = Session()
    ap   = sess.query(Pick).order_by(Pick.created_at.desc()).all()
    sess.close()
    if ap:
        df = pd.DataFrame([{
            "Date": p.analysis_date, "Ticker": p.ticker, "Company": p.company[:26],
            "Market": p.market, "Sector": p.sector, "Size": p.size,
            "Signal": p.technical_signal, "Sentiment": p.sentiment, "Confidence": p.confidence,
            "Price": f"{cs(p.currency)}{p.price_at_pick:,.2f}",
        } for p in ap])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No picks yet.")


# ── SETTINGS ──────────────────────────────────────────────────────────────────
elif page == "Settings":
    render_mbar()
    st.markdown('<div class="sdiv">Auto-Scheduler Configuration</div>', unsafe_allow_html=True)
    if ACCOUNT_TYPE in ("guest","free"):
        st.warning("Scheduler configuration requires a Premium or Admin account.")
    else:
        cfg = load_sched()
        from src.data.stock_universe import INDIAN_STOCKS, US_STOCKS, get_all_sectors, get_all_sizes
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Schedule**")
            enabled = st.toggle("Enable auto-scheduler", cfg.get("enabled",False))
            day     = st.selectbox("Day", ["mon","tue","wed","thu","fri"],
                                   index=["mon","tue","wed","thu","fri"].index(cfg.get("day","mon")))
            ch, cm  = st.columns(2)
            hour    = ch.number_input("Hour (24h)", 0, 23, cfg.get("hour",6))
            minute  = cm.selectbox("Minute", [0,15,30,45],
                                    index=[0,15,30,45].index(cfg.get("minute",0)))
        with c2:
            st.markdown("**Scope**")
            markets  = st.multiselect("Markets", ["INDIA","US"], cfg.get("markets",["INDIA","US"]))
            ind_secs = st.multiselect("India sectors (empty=all)", list(INDIAN_STOCKS.keys()), cfg.get("india_sectors",[]))
            us_secs  = st.multiselect("US sectors (empty=all)",    list(US_STOCKS.keys()),     cfg.get("us_sectors",[]))
            sizes    = st.multiselect("Cap sizes", ["Large","Mid","Small","Mega"], cfg.get("sizes",["Large","Mid"]))
        if st.button("💾 Save Settings", type="primary"):
            nc = {"enabled":enabled,"day":day,"hour":int(hour),"minute":int(minute),
                  "markets":markets,"india_sectors":ind_secs,"us_sectors":us_secs,
                  "sizes":sizes,"last_run":cfg.get("last_run")}
            save_sched(nc)
            if enabled:
                try:
                    from src.scheduler import get_scheduler, schedule_job
                    schedule_job(get_scheduler(), nc)
                    st.success(f"✅ Scheduler ON — every {day.title()} at {int(hour):02d}:{int(minute):02d}")
                except Exception as e:
                    st.warning(f"Saved (scheduler error: {e})")
            else:
                st.success("Settings saved · Scheduler off")

    st.markdown('<div class="sdiv">Manual Run</div>', unsafe_allow_html=True)
    if not can_run_analysis():
        st.warning(run_denied_msg())
    else:
        from src.data.stock_universe import get_all_sectors, get_all_sizes
        mc1, mc2, mc3 = st.columns(3)
        rm = mc1.selectbox("Market", ["INDIA","US"], key="s_mkt")
        rs = mc2.selectbox("Sector", get_all_sectors(rm), key="s_sec")
        rz = mc3.selectbox("Size",   get_all_sizes(rm),   key="s_siz")
        if st.button("🚀 Run Now", use_container_width=True):
            with st.spinner(f"Agents: {rm} · {rs} · {rz} ..."):
                try: _run_crew(rm, rs, rz)
                except Exception as e: st.error(str(e))

    if ACCOUNT_TYPE != "guest":
        st.markdown('<div class="sdiv">Change Password</div>', unsafe_allow_html=True)
        with st.form("chpwd_form", clear_on_submit=True):
            new_p  = st.text_input("New password", type="password",
                                    placeholder="New password (min 6 chars)",
                                    label_visibility="collapsed")
            new_p2 = st.text_input("Confirm", type="password",
                                    placeholder="Confirm new password",
                                    label_visibility="collapsed")
            if st.form_submit_button("Update Password", use_container_width=True):
                if new_p != new_p2:     st.error("Passwords don't match.")
                elif len(new_p) < 6:    st.error("Minimum 6 characters.")
                else:
                    try:
                        from src.auth.supabase_auth import get_client
                        get_client().auth.update_user({"password": new_p})
                        st.success("✅ Password updated.")
                    except Exception as e: st.error(str(e))