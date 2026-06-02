# src/ui/app.py  ─  StockPicker Terminal v2 (Full Premium Redesign)
# Run: uv run streamlit run src/ui/app.py

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import streamlit as st
import pandas as pd
import yfinance as yf
import pytz, json
from datetime import datetime, timezone
from streamlit_option_menu import option_menu

from src.database.models        import init_db, Session, Pick, Portfolio
from src.database.paper_trading import (
    add_to_portfolio, sell_position,
    get_portfolio, get_portfolio_metrics, save_picks
)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="StockPicker Terminal", page_icon="📊",
                   layout="wide", initial_sidebar_state="expanded")
init_db()

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Outfit:wght@300;400;500;600;700&display=swap');

/* ── Reset & base ── */
html, body, [class*="css"] { font-family: 'Outfit', sans-serif; color: #e2e8f0; }
.stApp { background: #07080f; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 0 2rem 3rem !important; max-width: 100% !important; }

/* ── Sidebar ── */
section[data-testid="stSidebar"] > div:first-child {
    background: #0b0d17 !important;
    border-right: 1px solid rgba(255,255,255,0.05) !important;
    padding: 0 !important;
}
/* option-menu overrides */
.nav-link { border-radius: 8px !important; margin: 2px 8px !important; }
.nav-link:hover { background: rgba(255,255,255,0.04) !important; }
.nav-link-selected { background: rgba(99,102,241,0.13) !important; }
.nav-link .nav-link-label { font-size: 13px !important; font-weight: 400; }
.nav-link-selected .nav-link-label { font-weight: 500 !important; color: #818cf8 !important; }
.nav-link .icon { font-size: 14px !important; }

/* ── Ticker tape ── */
.ticker-outer {
    overflow: hidden; width: 100%;
    padding: 7px 0; position: relative;
}
.ticker-outer.india {
    background: linear-gradient(90deg,#0f0800,#0b0d17 40%,#0b0d17 60%,#0f0800);
    border-bottom: 1.5px solid rgba(249,115,22,0.25);
}
.ticker-outer.us {
    background: linear-gradient(90deg,#05091a,#0b0d17 40%,#0b0d17 60%,#05091a);
    border-bottom: 1.5px solid rgba(99,102,241,0.25);
}
.ticker-track {
    display: inline-flex; gap: 0; white-space: nowrap;
    min-width: 200%;
    animation: scroll-left 70s linear infinite;
}
.ticker-track:hover { animation-play-state: paused; cursor: pointer; }
@keyframes scroll-left {
    from { transform: translateX(0); }
    to   { transform: translateX(-50%); }
}
.t-chip {
    display: inline-flex; align-items: center; gap: 8px;
    padding: 0 20px; border-right: 1px solid rgba(255,255,255,0.05);
    font-family: 'IBM Plex Mono', monospace; font-size: 11.5px;
}
.t-name  { color: #475569; font-weight: 400; letter-spacing:.03em; }
.t-price { color: #cbd5e1; font-weight: 500; }
.t-up    { color: #10b981; font-size: 10.5px; }
.t-dn    { color: #ef4444; font-size: 10.5px; }

/* ── Market status bar ── */
.mbar {
    display: flex; align-items: center; justify-content: space-between;
    padding: 14px 0 16px;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    margin-bottom: 1.6rem;
}
.app-brand {
    font-size: 20px; font-weight: 700; letter-spacing: -0.5px;
    font-family: 'Outfit', sans-serif;
    background: linear-gradient(120deg, #c7d2fe, #818cf8);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.app-sub { font-size: 10px; color: #334155; letter-spacing: .12em; text-transform: uppercase; margin-top: 2px; }
.mkt-pill {
    display: inline-flex; align-items: center; gap: 7px;
    padding: 5px 13px; border-radius: 99px; font-size: 11.5px;
    font-weight: 500; letter-spacing: .02em; margin-left: 8px;
}
.mk-open { background: rgba(16,185,129,.1); border: 1px solid rgba(16,185,129,.2); color: #10b981; }
.mk-shut { background: rgba(239,68,68,.07); border: 1px solid rgba(239,68,68,.15); color: #ef4444; }
.mk-dot  { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.mk-dot.on  { background: #10b981; animation: blink 2s infinite; }
.mk-dot.off { background: #ef4444; }
@keyframes blink { 0%,100%{opacity:1;} 60%{opacity:.3;} }

/* ── Metric strip ── */
.metric-strip {
    display: grid; grid-template-columns: repeat(4,1fr); gap: 10px;
    margin-bottom: 1.8rem;
}
.mc {
    background: rgba(255,255,255,0.022);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 10px; padding: 16px 18px;
    transition: border-color .2s;
}
.mc:hover { border-color: rgba(255,255,255,0.12); }
.mc-lbl { font-size: 10.5px; color: #475569; text-transform: uppercase; letter-spacing: .08em; margin-bottom: 6px; }
.mc-val { font-family: 'IBM Plex Mono', monospace; font-size: 22px; font-weight: 600; color: #e2e8f0; line-height: 1; }
.mc-sub { font-size: 12px; margin-top: 5px; }
.c-up  { color: #10b981; } .c-dn { color: #ef4444; } .c-mu { color: #64748b; }

/* ── Pick card ── */
.pcard {
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 12px; padding: 16px 18px; margin-bottom: 8px;
    transition: border-color .2s, background .2s;
}
.pcard:hover { border-color: rgba(255,255,255,0.12); background: rgba(255,255,255,0.03); }
.pcard.bull { border-left: 3px solid #10b981; }
.pcard.bear { border-left: 3px solid #ef4444; }
.pcard.neut { border-left: 3px solid #f59e0b; }
.pc-sym  { font-family:'IBM Plex Mono',monospace; font-size:17px; font-weight:600; color:#e2e8f0; }
.pc-co   { font-size:12px; color:#475569; margin-top:1px; }
.pc-price{ font-family:'IBM Plex Mono',monospace; font-size:15px; font-weight:500; }
.pc-meta { font-size:11px; color:#334155; margin: 9px 0; letter-spacing:.02em; }
.badge   { display:inline-block; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:500; margin:2px; }
.b-bull  { background:rgba(16,185,129,.13);  color:#10b981; }
.b-bear  { background:rgba(239,68,68,.13);   color:#ef4444; }
.b-neut  { background:rgba(245,158,11,.13);  color:#f59e0b; }
.b-high  { background:rgba(99,102,241,.15);  color:#818cf8; }
.b-med   { background:rgba(148,163,184,.1);  color:#94a3b8; }
.b-low   { background:rgba(100,116,139,.08); color:#64748b; }

/* ── Portfolio table ── */
.pt { width:100%; border-collapse:collapse; font-size:13px; margin-top:4px; }
.pt th {
    font-size:10.5px; color:#475569; text-transform:uppercase; letter-spacing:.07em;
    padding: 8px 14px; border-bottom: 1px solid rgba(255,255,255,0.05);
    text-align: left; font-weight:500;
}
.pt td { padding: 13px 14px; border-bottom: 1px solid rgba(255,255,255,0.035); vertical-align:middle; }
.pt tr:hover td { background: rgba(255,255,255,0.018); }
.pt .sym  { font-family:'IBM Plex Mono',monospace; font-weight:600; font-size:14px; }
.pt .co   { font-size:11px; color:#475569; margin-top:2px; }
.pt .mono { font-family:'IBM Plex Mono',monospace; }
.pnl-up   { color:#10b981; font-family:'IBM Plex Mono',monospace; font-weight:500; }
.pnl-dn   { color:#ef4444; font-family:'IBM Plex Mono',monospace; font-weight:500; }
.mkt-tag  { display:inline-block; padding:2px 7px; border-radius:3px; font-size:10px; font-weight:600; letter-spacing:.05em; }
.mkt-in   { background:rgba(249,115,22,.12); color:#f97316; }
.mkt-us   { background:rgba(99,102,241,.12); color:#818cf8; }

/* ── Section divider ── */
.sdiv {
    font-size: 10.5px; font-weight: 500; color: #334155;
    text-transform: uppercase; letter-spacing: .1em;
    margin: 1.8rem 0 1rem;
    padding-bottom: 8px;
    border-bottom: 1px solid rgba(255,255,255,0.04);
}

/* ── Streamlit widget overrides ── */
.stSelectbox > div > div { background: rgba(255,255,255,0.03) !important; border-color: rgba(255,255,255,0.08) !important; font-size: 13px !important; border-radius: 8px !important; }
.stNumberInput input { background: rgba(255,255,255,0.03) !important; border-color: rgba(255,255,255,0.08) !important; font-size: 13px !important; border-radius: 8px !important; color: #e2e8f0 !important; }
.stButton > button {
    background: rgba(99,102,241,0.12) !important;
    border: 1px solid rgba(99,102,241,0.25) !important;
    color: #818cf8 !important; font-size: 13px !important;
    border-radius: 8px !important; font-family: 'Outfit', sans-serif !important;
    font-weight: 500 !important; padding: 6px 18px !important;
    transition: all .18s !important;
}

/* ── Tab fix ── */
button[data-baseweb="tab"] {
    background: transparent !important; border-radius: 8px !important;
    color: #64748b !important; font-size: 13px !important;
    font-family: 'Outfit',sans-serif !important;
    padding: 8px 28px !important; font-weight: 400 !important;
    border: none !important; margin: 0 2px !important;
}
button[data-baseweb="tab"]:hover { background: rgba(255,255,255,0.04) !important; color: #94a3b8 !important; }
button[data-baseweb="tab"][aria-selected="true"] {
    background: rgba(99,102,241,0.15) !important;
    color: #818cf8 !important; font-weight: 500 !important;
}
div[data-baseweb="tab-border"], div[data-baseweb="tab-highlight"] { display: none !important; }
div[data-baseweb="tab-list"] {
    background: rgba(255,255,255,0.02) !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: 10px !important; padding: 4px !important;
    gap: 0 !important; margin-bottom: 1.2rem !important;
}

.stButton > button:hover { background: rgba(99,102,241,0.2) !important; border-color: rgba(99,102,241,0.4) !important; color: #c7d2fe !important; }
.stButton > button[kind="primary"] { background: #4f46e5 !important; border-color: #4f46e5 !important; color: white !important; }
.stButton > button[kind="primary"]:hover { background: #4338ca !important; }
div[data-testid="stExpander"] { background: rgba(255,255,255,0.018) !important; border-color: rgba(255,255,255,0.06) !important; border-radius: 8px !important; }
.stTabs [data-baseweb="tab-list"] { background: rgba(255,255,255,0.02); border-radius: 8px; padding: 3px; gap: 2px; }
.stTabs [data-baseweb="tab"] { border-radius: 6px; font-size: 13px; color: #64748b; }
.stTabs [aria-selected="true"] { background: rgba(99,102,241,0.15) !important; color: #818cf8 !important; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════

INDIA_SYMS = ("RELIANCE.NS","TCS.NS","HDFCBANK.NS","INFY.NS","ICICIBANK.NS",
              "BHARTIARTL.NS","SBIN.NS","BAJFINANCE.NS","WIPRO.NS","KOTAKBANK.NS",
              "HINDUNILVR.NS","NTPC.NS","MARUTI.NS","AXISBANK.NS","ADANIENT.NS")

US_SYMS = ("AAPL","MSFT","NVDA","GOOGL","AMZN","META","TSLA",
           "JPM","V","UNH","AMD","CRM","NFLX","GS","INTC")

SCHED_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "scheduler_settings.json")


# ══════════════════════════════════════════════════════════════════════════════
# DATA HELPERS  (all cached)
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=300)
def fetch_tape(syms: tuple, cur: str) -> list:
    try:
        raw   = yf.download(list(syms), period="2d", auto_adjust=True,
                            progress=False, threads=True)
        close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw
        out   = []
        for s in syms:
            try:
                col   = close[s]
                p     = float(col.iloc[-1])
                prev  = float(col.iloc[-2]) if len(col) >= 2 else p
                chg   = (p - prev) / prev * 100 if prev else 0.0
                label = s.replace(".NS","").replace(".BO","")
                out.append({"sym":label, "p":p, "chg":chg, "cur":cur})
            except Exception:
                pass
        return out
    except Exception:
        return []

@st.cache_data(ttl=60)
def market_status() -> dict:
    now = datetime.now(timezone.utc)
    ist = pytz.timezone("Asia/Kolkata")
    et  = pytz.timezone("America/New_York")
    ni  = now.astimezone(ist)
    ne  = now.astimezone(et)
    def m(dt): return dt.hour*60 + dt.minute
    nse  = ni.weekday()<5 and 9*60+15  <= m(ni) <= 15*60+30
    nyse = ne.weekday()<5 and 9*60+30  <= m(ne) <= 16*60
    return {
        "nse":  {"open":nse,  "time":ni.strftime("%I:%M %p IST"), "label":"NSE / BSE"},
        "nyse": {"open":nyse, "time":ne.strftime("%I:%M %p ET"),  "label":"NYSE / NASDAQ"},
    }

@st.cache_data(ttl=120)
def cached_portfolio(market=None): return get_portfolio(market=market)

@st.cache_data(ttl=120)
def cached_metrics(): return get_portfolio_metrics()

@st.cache_data(ttl=600)
def usd_inr_rate() -> float:
    """Live USD → INR rate from Yahoo Finance."""
    try:
        h = yf.Ticker("USDINR=X").history(period="1d")
        if not h.empty:
            return round(float(h["Close"].iloc[-1]), 2)
    except Exception:
        pass
    return 84.0   # fallback

def cs(m): return "₹" if m in ("INDIA","INR") else "$"

def sbadge(s):
    c={"Bullish":"b-bull","Bearish":"b-bear"}.get(s,"b-neut")
    return f'<span class="badge {c}">{s or "—"}</span>'

def cbadge(c):
    cl={"High":"b-high","Medium":"b-med","Low":"b-low"}.get(c,"b-low")
    return f'<span class="badge {cl}">{c or "—"} confidence</span>'

def load_sched():
    if os.path.exists(SCHED_FILE):
        with open(SCHED_FILE) as f: return json.load(f)
    return {"enabled":False,"day":"mon","hour":6,"minute":0,"markets":["INDIA","US"],"last_run":None}

def save_sched(cfg):
    with open(SCHED_FILE,"w") as f: json.dump(cfg,f,indent=2)

def picks_db(market=None, sector=None, size=None, limit=60):
    s=Session(); q=s.query(Pick)
    if market: q=q.filter(Pick.market==market)
    if sector: q=q.filter(Pick.sector==sector)
    if size:   q=q.filter(Pick.size==size)
    out=q.order_by(Pick.created_at.desc()).limit(limit).all()
    s.close(); return out

def sectors_db(mkt):
    s=Session()
    r=s.query(Pick.sector).filter(Pick.market==mkt).distinct().all()
    s.close(); return sorted([x[0] for x in r])

def sizes_db(mkt):
    s=Session()
    r=s.query(Pick.size).filter(Pick.market==mkt).distinct().all()
    s.close(); return sorted([x[0] for x in r])


# ══════════════════════════════════════════════════════════════════════════════
# RENDER HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def render_ticker(mode="both"):
    if mode in ("both","india"):
        items = fetch_tape(INDIA_SYMS, "₹")
        cls   = "india"
    else:
        items = fetch_tape(US_SYMS, "$")
        cls   = "us"

    if not items: return

    def chip(it):
        cc  = "t-up" if it["chg"]>=0 else "t-dn"
        arr = "▲" if it["chg"]>=0 else "▼"
        return (f'<span class="t-chip">'
                f'<span class="t-name">{it["sym"]}</span>'
                f'<span class="t-price">{it["cur"]}{it["p"]:,.2f}</span>'
                f'<span class="{cc}">{arr}{abs(it["chg"]):.2f}%</span>'
                f'</span>')

    inner = "".join(chip(i) for i in items)
    st.markdown(f'<div class="ticker-outer {cls}">'
                f'<div class="ticker-track">{inner}{inner}</div>'
                f'</div>', unsafe_allow_html=True)


def render_mbar():
    s   = market_status()
    nse = s["nse"]; nyse = s["nyse"]
    def pill(info):
        cls = "mk-open" if info["open"] else "mk-shut"
        dot = "on"      if info["open"] else "off"
        txt = "Open"    if info["open"] else "Closed"
        return (f'<span class="mkt-pill {cls}">'
                f'<span class="mk-dot {dot}"></span>'
                f'{info["label"]} &nbsp;·&nbsp; {txt} &nbsp;·&nbsp; {info["time"]}'
                f'</span>')
    st.markdown(
        f'<div class="mbar">'
        f'<div><div class="app-brand">◈ StockPicker</div>'
        f'<div class="app-sub">AI Investment Terminal</div></div>'
        f'<div>{pill(nse)}{pill(nyse)}</div>'
        f'</div>', unsafe_allow_html=True)


def render_pick_card(p, prefix=""):
    cls  = {"Bullish":"bull","Bearish":"bear"}.get(p.sentiment or "","neut")
    cur  = cs(p.currency or p.market)
    sym  = p.ticker.replace(".NS","").replace(".BO","")

    st.markdown(f"""
    <div class="pcard {cls}">
    <div style="display:flex;justify-content:space-between;align-items:flex-start">
        <div>
        <div class="pc-sym">{sym}</div>
        <div class="pc-co">{p.company[:38]}</div>
        </div>
        <div style="text-align:right">
        <div class="pc-price">{cur}{p.price_at_pick:,.2f}</div>
        <div style="margin-top:6px">
            {sbadge(p.technical_signal)}{sbadge(p.sentiment)}{cbadge(p.confidence)}
        </div>
        </div>
    </div>
    <div class="pc-meta">{p.sector} &nbsp;·&nbsp; {p.size} Cap &nbsp;·&nbsp; {p.analysis_date}</div>
    </div>""", unsafe_allow_html=True)

    c_det, c_add = st.columns([5,1])
    with c_det:
        with st.expander("Analysis details"):
            w1, w2 = st.columns(2)
            with w1:
                st.markdown("**Why Buy**", help="Reasons to invest")
                for pt in (p.why_buy or []):
                    st.markdown(f"<div style='font-size:12.5px;color:#94a3b8;margin-bottom:5px;line-height:1.5'>• {pt}</div>",
                                unsafe_allow_html=True)
            with w2:
                st.markdown("**Why Not Buy**", help="Risks to consider")
                for pt in (p.why_not_buy or []):
                    st.markdown(f"<div style='font-size:12.5px;color:#64748b;margin-bottom:5px;line-height:1.5'>• {pt}</div>",
                                unsafe_allow_html=True)
    with c_add:
        if not p.in_portfolio:
            qty = st.number_input("", 1, 10000, 10, 5,
                                  key=f"q_{prefix}_{p.id}", label_visibility="collapsed")
            if st.button("＋ Add", key=f"a_{prefix}_{p.id}", use_container_width=True):
                try:
                    add_to_portfolio(p.ticker, qty, pick_id=p.id)
                    st.cache_data.clear()
                    st.success("Added!")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
        else:
            st.markdown('<div style="text-align:center;padding:8px 0;font-size:18px">✓</div>',
                        unsafe_allow_html=True)
            st.caption("In portfolio")


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("""
    <div style="padding:24px 20px 12px">
    <div style="font-size:20px;font-weight:700;letter-spacing:-0.5px;
                background:linear-gradient(120deg,#c7d2fe,#818cf8);
                -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                font-family:'Outfit',sans-serif">
        ◈ StockPicker
    </div>
    <div style="font-size:10px;color:#334155;letter-spacing:.12em;
                text-transform:uppercase;margin-top:3px">
        AI Investment Terminal
    </div>
    </div>
    """, unsafe_allow_html=True)

    page = option_menu(
        menu_title=None,
        options=["Dashboard", "India", "US Markets", "Portfolio", "Metrics", "Settings"],
        icons=["grid-3x3-gap-fill", "currency-rupee", "currency-dollar",
               "graph-up-arrow", "bar-chart-line-fill", "gear-fill"],
        default_index=0,
        styles={
            "container":         {"background":"transparent","padding":"0 8px"},
            "menu-icon":         {"display":"none"},
            "nav-link":          {
                "font-size":"13px","color":"#64748b",
                "font-family":"'Outfit',sans-serif","padding":"9px 14px",
                "border-radius":"8px","margin":"2px 0",
                "--hover-color":"rgba(255,255,255,0.04)",
            },
            "nav-link-selected": {
                "background":"rgba(99,102,241,0.12)",
                "color":"#818cf8","font-weight":"500",
            },
            "icon":              {"font-size":"14px"},
        }
    )

    st.markdown('<hr style="border:none;border-top:1px solid rgba(255,255,255,0.05);margin:12px 0">', unsafe_allow_html=True)

    # Scheduler summary
    cfg = load_sched()
    dot_color = "#10b981" if cfg["enabled"] else "#ef4444"
    dot_label = "Active"  if cfg["enabled"] else "Off"
    st.markdown(f"""
    <div style="padding:0 12px;margin-bottom:10px">
    <div style="font-size:10px;color:#334155;text-transform:uppercase;
                letter-spacing:.1em;margin-bottom:8px">Auto Scheduler</div>
    <div style="background:rgba(255,255,255,0.025);border:1px solid rgba(255,255,255,0.06);
                border-radius:8px;padding:10px 13px;font-size:12.5px">
        <div style="display:flex;justify-content:space-between;align-items:center">
        <span style="color:#94a3b8">Schedule</span>
        <span style="display:flex;align-items:center;gap:6px;color:#94a3b8">
            <span style="width:6px;height:6px;border-radius:50%;
                        background:{dot_color};display:inline-block"></span>
            {dot_label}
        </span>
        </div>
        {'<div style="color:#6366f1;font-size:11px;margin-top:5px">Every ' + cfg["day"].title() + ' at ' + f'{cfg["hour"]:02d}:{cfg["minute"]:02d}' + '</div>' if cfg["enabled"] else ""}
    </div>
    </div>""", unsafe_allow_html=True)

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("▶ Run", use_container_width=True, key="sb_run"):
            st.session_state["quick_run"] = True
    with col_b:
        if st.button("↻ Refresh", use_container_width=True, key="sb_refresh"):
            st.cache_data.clear()
            st.rerun()

    if cfg.get("last_run"):
        st.markdown(f'<div style="padding:0 12px;font-size:11px;color:#334155;margin-top:4px">'
                    f'Last: {cfg["last_run"][:16]}</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PORTFOLIO HELPER  (defined before pages so it's available when needed)
# ══════════════════════════════════════════════════════════════════════════════

def render_ptab(market=None, pfx="all"):
    h    = cached_portfolio(market)
    rate = usd_inr_rate()

    # ── Currency toggle (only on "All" tab) ───────────────────────────────
    display_inr = True
    if pfx == "all":
        top_l, top_r = st.columns([3, 1])
        with top_r:
            tog = st.radio("", ["₹ INR", "$ USD"], horizontal=True,
                           key="curr_tog", label_visibility="collapsed")
            display_inr = (tog == "₹ INR")
        top_l.markdown(
            f'<div style="font-size:11.5px;color:#475569;padding-top:6px">'
            f'Live rate &nbsp;·&nbsp; <span style="color:#818cf8;font-family:IBM Plex Mono,monospace">'
            f'1 USD = ₹{rate:.2f}</span></div>',
            unsafe_allow_html=True)

    if not h:
        st.markdown('<div style="color:#334155;text-align:center;padding:3rem 0;font-size:14px">'
                    'No open positions</div>', unsafe_allow_html=True)
        return

    # ── Convert amounts for unified display ───────────────────────────────
    disp = []
    for x in h:
        dx = dict(x)
        if pfx == "all":
            if display_inr and dx["currency"] == "USD":
                for k in ("entry_price","current_price","invested","current_value","pnl_amount"):
                    dx[k] = dx[k] * rate
                dx["dcur"] = "₹"
            elif not display_inr and dx["currency"] == "INR":
                for k in ("entry_price","current_price","invested","current_value","pnl_amount"):
                    dx[k] = dx[k] / rate
                dx["dcur"] = "$"
            else:
                dx["dcur"] = "₹" if dx["currency"] == "INR" else "$"
        else:
            dx["dcur"] = "₹" if market == "INDIA" else "$"
        disp.append(dx)

    # ── Summary strip ──────────────────────────────────────────────────────
    inv  = sum(x["invested"]      for x in disp)
    val  = sum(x["current_value"] for x in disp)
    pnl  = val - inv
    pct  = pnl / inv * 100 if inv else 0
    pc   = "c-up" if pnl >= 0 else "c-dn"
    cur  = disp[0]["dcur"] if disp else ""

    st.markdown(f"""
    <div class="metric-strip" style="grid-template-columns:repeat(3,1fr);margin-bottom:1.2rem">
    <div class="mc">
        <div class="mc-lbl">Invested</div>
        <div class="mc-val" style="font-size:18px">{cur}{inv:,.2f}</div>
    </div>
    <div class="mc">
        <div class="mc-lbl">Current Value</div>
        <div class="mc-val" style="font-size:18px">{cur}{val:,.2f}</div>
    </div>
    <div class="mc">
        <div class="mc-lbl">Unrealised P&L</div>
        <div class="mc-val {pc}" style="font-size:18px">{cur}{pnl:+,.2f}</div>
        <div class="mc-sub {pc}">{pct:+.2f}%</div>
    </div>
    </div>""", unsafe_allow_html=True)

    # ── Portfolio table via st.dataframe ──────────────────────────────────
    rows = []
    for x in disp:
        c = x["dcur"]
        rows.append({
            "Ticker":    x["ticker"].replace(".NS","").replace(".BO",""),
            "Company":   x["company"][:24],
            "Market":    x["market"],
            "Entry":     f"{c}{x['entry_price']:,.2f}",
            "Current":   f"{c}{x['current_price']:,.2f}",
            "Qty":       int(x["quantity"]),
            "P&L %":     x["pnl_pct"],
            "P&L Amt":   f"{c}{x['pnl_amount']:+,.2f}",
            "Days Held": x["days_held"],
        })

    df = pd.DataFrame(rows)

    st.dataframe(
        df.style
        .map(lambda v: f"color: {'#10b981' if v>=0 else '#ef4444'}", subset=["P&L %"])
        .format({"P&L %": "{:+.2f}%"})
        .hide(axis="index"),
        use_container_width=True,
        hide_index=True,
    )

    # ── Close position ─────────────────────────────────────────────────────
    st.markdown('<div style="margin-top:1.2rem;margin-bottom:.4rem;font-size:10.5px;color:#475569;'
                'text-transform:uppercase;letter-spacing:.08em">Close a position</div>',
                unsafe_allow_html=True)
    opts = [f"{x['id']}  ·  {x['ticker']}  ·  {int(x['quantity'])} shares" for x in h]
    sel  = st.selectbox("", opts, key=f"sel_{pfx}", label_visibility="collapsed")
    if sel and st.button("💰 Sell at Market Price", key=f"sell_{pfx}",
                         use_container_width=True):
        pid = int(sel.split(" · ")[0].strip())
        try:
            r  = sell_position(pid)
            st.cache_data.clear()
            em = "🟢" if r["pnl_amount"] >= 0 else "🔴"
            st.success(f"{em}  {r['ticker']} sold  ·  P&L: {r['pnl_pct']:+.2f}%")
            st.rerun()
        except Exception as e:
            st.error(str(e))


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if page == "Dashboard":
    render_ticker("both")
    render_mbar()

    m   = cached_metrics()
    inv = m.get("total_invested",0) or 0
    val = m.get("current_value",0)  or 0
    pnl = m.get("unrealised_pnl",0) or 0
    pct = m.get("unrealised_pnl_pct",0) or 0
    wr  = m.get("win_rate")
    pc  = "c-up" if pnl>=0 else "c-dn"
    arr = "▲" if pnl>=0 else "▼"

    st.markdown(f"""
    <div class="metric-strip">
    <div class="mc">
        <div class="mc-lbl">Portfolio Value</div>
        <div class="mc-val">{val:,.0f}</div>
        <div class="mc-sub c-mu">Invested: {inv:,.0f}</div>
    </div>
    <div class="mc">
        <div class="mc-lbl">Unrealised P&L</div>
        <div class="mc-val {pc}">{arr} {abs(pnl):,.0f}</div>
        <div class="mc-sub {pc}">{pct:+.2f}%</div>
    </div>
    <div class="mc">
        <div class="mc-lbl">Win Rate</div>
        <div class="mc-val">{f"{wr}%" if wr else "—"}</div>
        <div class="mc-sub c-mu">{m.get('wins',0)} W &nbsp;/&nbsp; {m.get('losses',0)} L</div>
    </div>
    <div class="mc">
        <div class="mc-lbl">Positions</div>
        <div class="mc-val">{m.get('open_positions',0)}</div>
        <div class="mc-sub c-mu">{m.get('closed_positions',0)} closed</div>
    </div>
    </div>""", unsafe_allow_html=True)

    # Quick run panel
    if st.session_state.get("quick_run"):
        st.session_state.pop("quick_run")
        st.markdown('<div class="sdiv">Run Analysis</div>', unsafe_allow_html=True)
        from src.data.stock_universe import get_all_sectors, get_all_sizes
        c1,c2,c3 = st.columns(3)
        rm = c1.selectbox("Market", ["INDIA","US"], key="d_mkt")
        rs = c2.selectbox("Sector", get_all_sectors(rm), key="d_sec")
        rz = c3.selectbox("Size",   get_all_sizes(rm),   key="d_siz")
        if st.button("🚀 Launch Crew", type="primary"):
            with st.spinner(f"Running agents: {rm} · {rs} · {rz}  (2-4 min)"):
                try:
                    from src.agents.crew import run_stock_picker
                    res = run_stock_picker(rm, rs, rz)
                    if res.get("picks"):
                        save_picks(res)
                        st.cache_data.clear()
                        st.success(f"✅ {len(res['picks'])} picks saved!")
                    else:
                        st.warning("No picks returned.")
                except Exception as e:
                    st.error(str(e))

    st.markdown('<div class="sdiv">Recent Picks</div>', unsafe_allow_html=True)
    recent = picks_db(limit=6)
    if recent:
        c1, c2 = st.columns(2)
        for i, p in enumerate(recent):
            with (c1 if i%2==0 else c2):
                render_pick_card(p, "dash")
    else:
        st.markdown('<div style="color:#334155;text-align:center;padding:4rem 0;font-size:14px">'
                    'No picks yet — click ▶ Run in the sidebar</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: INDIA
# ══════════════════════════════════════════════════════════════════════════════
elif page == "India":
    render_ticker("india")
    render_mbar()
    st.markdown('<div class="sdiv">Indian Market Picks &nbsp;·&nbsp; NSE / BSE</div>',
                unsafe_allow_html=True)

    secs = sectors_db("INDIA"); szs = sizes_db("INDIA")
    if not secs:
        st.markdown('<div style="color:#334155;text-align:center;padding:4rem 0">No India picks yet.</div>',
                    unsafe_allow_html=True)
    else:
        c1,c2 = st.columns(2)
        ss = c1.selectbox("Sector", ["All"]+secs, key="in_sec")
        sz = c2.selectbox("Size",   ["All"]+szs,  key="in_siz")
        picks = picks_db("INDIA", None if ss=="All" else ss, None if sz=="All" else sz)
        st.caption(f"{len(picks)} picks · India")
        ca, cb = st.columns(2)
        for i,p in enumerate(picks):
            with (ca if i%2==0 else cb): render_pick_card(p, "in")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: US
# ══════════════════════════════════════════════════════════════════════════════
elif page == "US Markets":
    render_ticker("us")
    render_mbar()
    st.markdown('<div class="sdiv">US Market Picks &nbsp;·&nbsp; NYSE / NASDAQ</div>',
                unsafe_allow_html=True)

    secs = sectors_db("US"); szs = sizes_db("US")
    if not secs:
        st.markdown('<div style="color:#334155;text-align:center;padding:4rem 0">No US picks yet.</div>',
                    unsafe_allow_html=True)
    else:
        c1,c2 = st.columns(2)
        ss = c1.selectbox("Sector", ["All"]+secs, key="us_sec")
        sz = c2.selectbox("Size",   ["All"]+szs,  key="us_siz")
        picks = picks_db("US", None if ss=="All" else ss, None if sz=="All" else sz)
        st.caption(f"{len(picks)} picks · US")
        ca, cb = st.columns(2)
        for i,p in enumerate(picks):
            with (ca if i%2==0 else cb): render_pick_card(p, "us")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: PORTFOLIO
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Portfolio":
    render_ticker("both")
    render_mbar()
    st.markdown('<div class="sdiv">Paper Trading Portfolio</div>', unsafe_allow_html=True)

    t_in, t_us, t_all = st.tabs(["India", "US", "All"])
    with t_in:
        render_ptab(market="INDIA", pfx="india")
    with t_us:
        render_ptab(market="US", pfx="us")
    with t_all:
        render_ptab(market=None, pfx="all")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: METRICS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Metrics":
    render_ticker("both")
    render_mbar()
    st.markdown('<div class="sdiv">Performance Analytics</div>', unsafe_allow_html=True)

    m   = cached_metrics()
    bp  = m.get("best_pick");  bpp = m.get("best_pick_pct")
    wp  = m.get("worst_pick"); wpp = m.get("worst_pick_pct")
    wr  = m.get("win_rate")

    st.markdown(f"""
    <div class="metric-strip">
    <div class="mc"><div class="mc-lbl">Win Rate</div>
        <div class="mc-val">{f"{wr}%" if wr else "—"}</div>
        <div class="mc-sub c-mu">{m.get('wins',0)} W · {m.get('losses',0)} L</div></div>
    <div class="mc"><div class="mc-lbl">Open / Closed</div>
        <div class="mc-val">{m.get('open_positions',0)} / {m.get('closed_positions',0)}</div></div>
    <div class="mc"><div class="mc-lbl">Best Pick</div>
        <div class="mc-val c-up">{f"{bpp:+.1f}%" if bpp else "—"}</div>
        <div class="mc-sub c-mu">{bp or "No closed trades"}</div></div>
    <div class="mc"><div class="mc-lbl">Worst Pick</div>
        <div class="mc-val c-dn">{f"{wpp:+.1f}%" if wpp else "—"}</div>
        <div class="mc-sub c-mu">{wp or "No closed trades"}</div></div>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="sdiv">All Picks History</div>', unsafe_allow_html=True)
    s = Session()
    ap = s.query(Pick).order_by(Pick.created_at.desc()).all()
    s.close()
    if ap:
        df = pd.DataFrame([{"Date":p.analysis_date,"Ticker":p.ticker,"Company":p.company[:26],
            "Market":p.market,"Sector":p.sector,"Size":p.size,
            "Signal":p.technical_signal,"Sentiment":p.sentiment,
            "Confidence":p.confidence,
            "Price":f"{cs(p.currency)}{p.price_at_pick:,.2f}",
            "In Portfolio":"✓" if p.in_portfolio else ""} for p in ap])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No picks yet.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: SETTINGS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Settings":
    render_mbar()
    st.markdown('<div class="sdiv">Auto-Scheduler Configuration</div>', unsafe_allow_html=True)

    cfg = load_sched()
    from src.data.stock_universe import INDIAN_STOCKS, US_STOCKS, get_all_sectors, get_all_sizes

    c1,c2 = st.columns(2)
    with c1:
        st.markdown("**Schedule**")
        enabled = st.toggle("Enable auto-scheduler", cfg.get("enabled",False))
        day     = st.selectbox("Day", ["mon","tue","wed","thu","fri"],
                               index=["mon","tue","wed","thu","fri"].index(cfg.get("day","mon")))
        col_h, col_m = st.columns(2)
        hour   = col_h.number_input("Hour (24h)", 0, 23, cfg.get("hour",6))
        minute = col_m.selectbox("Minute", [0,15,30,45],
                                 index=[0,15,30,45].index(cfg.get("minute",0)))
    with c2:
        st.markdown("**Scope**")
        markets   = st.multiselect("Markets",  ["INDIA","US"],        cfg.get("markets",["INDIA","US"]))
        ind_secs  = st.multiselect("India sectors (empty=all)", list(INDIAN_STOCKS.keys()), cfg.get("india_sectors",[]))
        us_secs   = st.multiselect("US sectors (empty=all)",    list(US_STOCKS.keys()),     cfg.get("us_sectors",[]))
        sizes     = st.multiselect("Cap sizes", ["Large","Mid","Small","Mega"], cfg.get("sizes",["Large","Mid"]))

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
    mc1,mc2,mc3 = st.columns(3)
    rm = mc1.selectbox("Market", ["INDIA","US"], key="s_mkt")
    rs = mc2.selectbox("Sector", get_all_sectors(rm), key="s_sec")
    rz = mc3.selectbox("Size",   get_all_sizes(rm),   key="s_siz")
    if st.button("🚀 Run Now", use_container_width=True):
        with st.spinner(f"Agents running: {rm} · {rs} · {rz} ..."):
            try:
                from src.agents.crew import run_stock_picker
                res = run_stock_picker(rm, rs, rz)
                if res.get("picks"):
                    save_picks(res); st.cache_data.clear()
                    st.success(f"✅ {len(res['picks'])} picks saved!")
                else:
                    st.warning("No picks returned.")
            except Exception as e:
                st.error(str(e))