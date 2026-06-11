# src/ui/stock_detail.py
# Full Groww/INDMoney-style stock detail page
# Tabs: AI Analysis | Technicals | News | Events

import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime


# ── Cached data fetchers ──────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def _chart_data(ticker: str, period: str) -> pd.DataFrame:
    return yf.Ticker(ticker).history(period=period)

@st.cache_data(ttl=600)
def _stock_info(ticker: str) -> dict:
    try:    return yf.Ticker(ticker).info or {}
    except: return {}

@st.cache_data(ttl=300)
def _news(ticker: str) -> list:
    try:
        raw  = yf.Ticker(ticker).news or []
        out  = []
        for item in raw[:12]:
            c = item.get("content", {})
            title   = c.get("title")   or item.get("title","")
            summary = c.get("summary") or ""
            source  = (c.get("provider",{}).get("displayName") or item.get("publisher",""))
            date    = c.get("pubDate") or item.get("providerPublishTime","")
            url     = (c.get("canonicalUrl",{}).get("url") or item.get("link",""))
            if title:
                out.append({"title":title,"summary":summary,
                             "source":source,"date":date,"url":url})
        return out
    except Exception: return []

@st.cache_data(ttl=3600)
def _events(ticker: str) -> dict:
    ev = {}
    try:
        stock = yf.Ticker(ticker)
        try:
            cal = stock.calendar
            if cal: ev["calendar"] = cal
        except Exception: pass
        try:
            div = stock.dividends
            if not div.empty:
                ev["last_div"] = {"date": str(div.index[-1].date()),
                                   "amount": round(float(div.iloc[-1]),4)}
        except Exception: pass
        try:
            ed = stock.earnings_dates
            if ed is not None and not ed.empty:
                ev["earnings"] = ed.head(5).reset_index()
        except Exception: pass
    except Exception: pass
    return ev

MONTHS = ["","Jan","Feb","Mar","Apr","May","Jun",
          "Jul","Aug","Sep","Oct","Nov","Dec"]

def _fmt_date(d) -> str:
    try:
        if isinstance(d,(int,float)):
            return datetime.fromtimestamp(d).strftime("%d %b %Y")
        s = str(d)
        return s[:10] if len(s)>=10 else s
    except Exception: return str(d)


# ── Signal summary bar (Groww-style) ─────────────────────────────────────────

def _signal_bar(bear:int, neut:int, bull:int):
    total = bear + neut + bull
    if total == 0: return
    pos   = (bull + 0.5*neut) / total * 100
    label = "Bullish" if pos>55 else "Bearish" if pos<45 else "Neutral"
    color = "#10b981" if pos>55 else "#ef4444" if pos<45 else "#f59e0b"
    bp    = bear/total*100; np_=neut/total*100
    st.markdown(f"""
    <div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);
                border-radius:12px;padding:16px 18px;margin-bottom:16px">
      <div style="font-size:12px;color:#64748b;margin-bottom:4px">Based on technicals, this stock is</div>
      <div style="font-size:20px;font-weight:700;color:{color};margin-bottom:14px">{label}</div>
      <div style="position:relative;height:8px;border-radius:4px;overflow:visible;
                  background:linear-gradient(90deg,#ef4444 {bp}%,#f59e0b {bp}% {bp+np_}%,#10b981 {bp+np_}%);
                  margin-bottom:20px">
        <div style="position:absolute;top:-5px;left:calc({pos}% - 6px);
                    width:0;height:0;border-left:6px solid transparent;
                    border-right:6px solid transparent;border-top:9px solid #e2e8f0"></div>
      </div>
      <div style="display:flex;justify-content:space-between;font-size:12px">
        <div style="display:flex;align-items:center;gap:5px">
          <span style="width:9px;height:9px;background:#ef4444;border-radius:2px;display:inline-block"></span>
          <span style="color:#64748b">Bearish</span> <b style="color:#ef4444">{bear}</b>
        </div>
        <div style="display:flex;align-items:center;gap:5px">
          <span style="width:9px;height:9px;background:#f59e0b;border-radius:2px;display:inline-block"></span>
          <span style="color:#64748b">Neutral</span> <b style="color:#f59e0b">{neut}</b>
        </div>
        <div style="display:flex;align-items:center;gap:5px">
          <span style="width:9px;height:9px;background:#10b981;border-radius:2px;display:inline-block"></span>
          <span style="color:#64748b">Bullish</span> <b style="color:#10b981">{bull}</b>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)


# ── Main detail page ──────────────────────────────────────────────────────────

def show_stock_detail(ticker: str, pick=None):
    """
    Full stock detail page.
    ticker: e.g. "WIPRO.NS" or "AAPL"
    pick  : Pick ORM object (optional) for AI analysis tab
    """
    # Back button
    if st.button("← Back to picks", key="detail_back"):
        st.session_state.pop("selected_stock", None)
        st.session_state.pop("selected_pick_id", None)
        st.rerun()

    info   = _stock_info(ticker)
    sym    = ticker.replace(".NS","").replace(".BO","")
    name   = info.get("longName", sym)
    is_ind = ticker.endswith(".NS") or ticker.endswith(".BO")
    cur    = "₹" if is_ind else "$"
    exch   = "NSE" if ticker.endswith(".NS") else "BSE" if ticker.endswith(".BO") else "NYSE/NASDAQ"

    # Live price
    try:
        h1    = _chart_data(ticker, "2d")
        price = round(float(h1["Close"].iloc[-1]),2)  if not h1.empty else 0
        prev  = round(float(h1["Close"].iloc[-2]),2)  if len(h1)>=2  else price
        chg   = round(price-prev, 2)
        pct   = round((chg/prev)*100, 2) if prev else 0
    except Exception:
        price=chg=pct=0

    cc  = "#10b981" if pct>=0 else "#ef4444"
    arr = "▲" if pct>=0 else "▼"

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="margin-bottom:18px">
      <div style="font-size:12px;color:#475569;margin-bottom:4px">{sym} &nbsp;·&nbsp; {exch}</div>
      <div style="font-size:17px;font-weight:600;color:#e2e8f0;margin-bottom:6px">{name}</div>
      <div style="display:flex;align-items:baseline;gap:12px">
        <span style="font-family:'IBM Plex Mono',monospace;font-size:30px;font-weight:700;color:#e2e8f0">
          {cur}{price:,.2f}
        </span>
        <span style="font-size:14px;font-weight:500;color:{cc}">
          {arr} {cur}{abs(chg):.2f} ({pct:+.2f}%)
        </span>
      </div>
    </div>""", unsafe_allow_html=True)

    # ── Price chart ───────────────────────────────────────────────────────────
    PERIODS = {"1D":"1d","1W":"5d","1M":"1mo","3M":"3mo","6M":"6mo","1Y":"1y","All":"5y"}
    sel = st.radio("", list(PERIODS.keys()), horizontal=True, index=2,
                   label_visibility="collapsed", key="chart_per")
    try:
        cd = _chart_data(ticker, PERIODS[sel])
        if not cd.empty:
            sp = float(cd["Close"].iloc[0]); ep = float(cd["Close"].iloc[-1])
            lc = "#10b981" if ep>=sp else "#ef4444"
            fc = "rgba(16,185,129,0.07)" if ep>=sp else "rgba(239,68,68,0.07)"
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=cd.index, y=cd["Close"], mode="lines",
                fill="tozeroy",
                line=dict(color=lc,width=2), fillcolor=fc,
                hovertemplate=f"{cur}%{{y:,.2f}}<extra></extra>",
            ))
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=0,r=0,t=4,b=0), height=210,
                xaxis=dict(showgrid=False,color="#475569",tickfont=dict(size=10,color="#475569")),
                yaxis=dict(showgrid=True,gridcolor="rgba(255,255,255,0.04)",
                           color="#475569",tickfont=dict(size=10)),
                hovermode="x unified",
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
    except Exception: st.caption("Chart unavailable")

    # ── Quick stats ───────────────────────────────────────────────────────────
    h52  = info.get("fiftyTwoWeekHigh")
    l52  = info.get("fiftyTwoWeekLow")
    vol  = info.get("volume")
    mc   = info.get("marketCap")
    pe   = info.get("trailingPE")
    roe  = info.get("returnOnEquity")

    stats = []
    if h52:  stats.append(("52W High",  f"{cur}{h52:,.2f}"))
    if l52:  stats.append(("52W Low",   f"{cur}{l52:,.2f}"))
    if vol:  stats.append(("Volume",    f"{vol/1e6:.1f}M" if vol>1e6 else f"{vol:,}"))
    if mc:   stats.append(("Mkt Cap",   f"{cur}{mc/1e9:.1f}B" if mc>1e9 else f"{cur}{mc/1e6:.0f}M"))
    if pe:   stats.append(("P/E",       f"{pe:.1f}x"))
    if roe:  stats.append(("ROE",       f"{roe*100:.1f}%"))

    if stats:
        cols = st.columns(len(stats))
        for col,(lbl,val) in zip(cols,stats):
            col.metric(lbl,val)

    st.markdown('<hr style="border:none;border-top:1px solid rgba(255,255,255,0.05);margin:16px 0">',
                unsafe_allow_html=True)

    # ── Tabs ──────────────────────────────────────────────────────────────────
    t_ai, t_tech, t_news, t_ev = st.tabs(
        ["🤖 AI Analysis", "📊 Technicals", "📰 News", "📅 Events"])

    # ─ AI Analysis ─────────────────────────────────────────────────────────
    with t_ai:
        if pick and (pick.why_buy or pick.why_not_buy):
            # Signal badges row
            sig_color = lambda s: "#10b981" if s=="Bullish" else "#ef4444" if s=="Bearish" else "#f59e0b"
            sig_bg    = lambda s: "rgba(16,185,129,.12)" if s=="Bullish" else "rgba(239,68,68,.12)" if s=="Bearish" else "rgba(245,158,11,.12)"
            st.markdown(f"""
            <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:18px">
              <span style="padding:5px 14px;border-radius:6px;font-size:12px;font-weight:600;
                background:{sig_bg(pick.technical_signal)};color:{sig_color(pick.technical_signal)}">
                Technical: {pick.technical_signal or '—'}
              </span>
              <span style="padding:5px 14px;border-radius:6px;font-size:12px;font-weight:600;
                background:{sig_bg(pick.sentiment)};color:{sig_color(pick.sentiment)}">
                Sentiment: {pick.sentiment or '—'}
              </span>
              <span style="padding:5px 14px;border-radius:6px;font-size:12px;font-weight:600;
                background:rgba(99,102,241,.12);color:#818cf8">
                {pick.confidence or '—'} Confidence
              </span>
            </div>""", unsafe_allow_html=True)

            if pick.why_buy:
                st.markdown('<div style="font-size:13px;font-weight:600;color:#10b981;margin-bottom:10px">✅ Why Buy</div>',
                            unsafe_allow_html=True)
                for pt in pick.why_buy:
                    st.markdown(f"""
                    <div style="font-size:13px;color:#94a3b8;margin-bottom:8px;padding:12px 14px;
                                background:rgba(16,185,129,0.05);border-left:2px solid #10b981;
                                border-radius:0 8px 8px 0;line-height:1.5">• {pt}</div>""",
                                unsafe_allow_html=True)

            if pick.why_not_buy:
                st.markdown('<div style="font-size:13px;font-weight:600;color:#ef4444;margin:20px 0 10px">⚠️ Why Not Buy</div>',
                            unsafe_allow_html=True)
                for pt in pick.why_not_buy:
                    st.markdown(f"""
                    <div style="font-size:13px;color:#64748b;margin-bottom:8px;padding:12px 14px;
                                background:rgba(239,68,68,0.05);border-left:2px solid #ef4444;
                                border-radius:0 8px 8px 0;line-height:1.5">• {pt}</div>""",
                                unsafe_allow_html=True)
        else:
            st.markdown('<div style="color:#334155;text-align:center;padding:3rem 0;font-size:14px">'
                        'No AI analysis yet.<br>Go back and run a crew analysis first.</div>',
                        unsafe_allow_html=True)

    # ─ Technicals ──────────────────────────────────────────────────────────
    with t_tech:
        try:
            from src.tools.technical_indicators import get_technical_indicators
            tech = get_technical_indicators.func(ticker)
            if "error" in tech:
                st.warning(tech["error"])
            else:
                rsi   = tech.get("rsi",50) or 50
                macd  = tech.get("macd_signal_label","") or ""
                ema   = tech.get("ema_trend","") or ""
                bb    = tech.get("bb_signal","") or ""

                bull = sum([rsi>55, "Bullish" in macd, "Bullish" in ema,
                            any(x in bb.lower() for x in ("upper","bull"))])
                bear = sum([rsi<45, "Bearish" in macd, "Bearish" in ema,
                            any(x in bb.lower() for x in ("lower","bear"))])
                neut = 4 - bull - bear
                _signal_bar(bear, neut, bull)

                def vc(v):
                    if not v: return "#64748b"
                    vl = v.lower()
                    if any(x in vl for x in ("bull","strong","above","oversold","recover")): return "#10b981"
                    if any(x in vl for x in ("bear","weak","below","overbought","sell")):   return "#ef4444"
                    return "#f59e0b"

                rows = [
                    ("RSI (14)",        str(tech.get("rsi","—")),           tech.get("rsi_signal","—")),
                    ("MACD (12,26,9)",  str(tech.get("macd","—")),           tech.get("macd_signal_label","—")),
                    ("Bollinger Bands", f"Mid {tech.get('bb_mid','—')}",     tech.get("bb_signal","—")),
                    ("EMA 20 / 50",     f"{tech.get('ema_20','—')} / {tech.get('ema_50','—')}", tech.get("ema_trend","—")),
                    ("ATR (vol)",       str(tech.get("atr","—")),            "Volatility measure"),
                    ("Overall",         f"Score {tech.get('technical_score','—')}/4", tech.get("overall_signal","—")),
                ]
                tbody = ""
                for lbl,val,verdict in rows:
                    tbody += f"""
                    <tr>
                      <td style="padding:12px 16px;color:#94a3b8;font-size:13px;
                                 border-bottom:1px solid rgba(255,255,255,0.04)">{lbl}</td>
                      <td style="padding:12px 16px;font-family:'IBM Plex Mono',monospace;
                                 font-size:13px;color:#cbd5e1;
                                 border-bottom:1px solid rgba(255,255,255,0.04)">{val}</td>
                      <td style="padding:12px 16px;font-size:13px;font-weight:500;color:{vc(verdict)};
                                 border-bottom:1px solid rgba(255,255,255,0.04)">{verdict}</td>
                    </tr>"""

                st.markdown(f"""
                <table style="width:100%;border-collapse:collapse;
                              background:rgba(255,255,255,0.02);
                              border:1px solid rgba(255,255,255,0.06);
                              border-radius:10px;overflow:hidden">
                  <thead><tr>
                    <th style="padding:10px 16px;text-align:left;font-size:10.5px;color:#475569;
                               text-transform:uppercase;letter-spacing:.07em;
                               background:rgba(255,255,255,0.02);
                               border-bottom:1px solid rgba(255,255,255,0.06)">Indicator</th>
                    <th style="padding:10px 16px;text-align:left;font-size:10.5px;color:#475569;
                               text-transform:uppercase;letter-spacing:.07em;
                               background:rgba(255,255,255,0.02);
                               border-bottom:1px solid rgba(255,255,255,0.06)">Value</th>
                    <th style="padding:10px 16px;text-align:left;font-size:10.5px;color:#475569;
                               text-transform:uppercase;letter-spacing:.07em;
                               background:rgba(255,255,255,0.02);
                               border-bottom:1px solid rgba(255,255,255,0.06)">Verdict</th>
                  </tr></thead>
                  <tbody>{tbody}</tbody>
                </table>""", unsafe_allow_html=True)

                st.markdown('<div style="font-size:10.5px;color:#334155;text-transform:uppercase;letter-spacing:.1em;margin:1.4rem 0 .8rem;padding-bottom:8px;border-bottom:1px solid rgba(255,255,255,0.04)">Key Levels</div>',
                            unsafe_allow_html=True)
                c1,c2,c3,c4,c5,c6 = st.columns(6)
                c1.metric("Price",    f"{cur}{tech.get('current_price','—')}")
                c2.metric("EMA 20",   f"{cur}{tech.get('ema_20','—')}")
                c3.metric("EMA 50",   f"{cur}{tech.get('ema_50','—')}")
                c4.metric("BB Upper", f"{cur}{tech.get('bb_upper','—')}")
                c5.metric("BB Mid",   f"{cur}{tech.get('bb_mid','—')}")
                c6.metric("BB Lower", f"{cur}{tech.get('bb_lower','—')}")
        except Exception as e:
            st.error(f"Technicals unavailable: {e}")

    # ─ News ────────────────────────────────────────────────────────────────
    with t_news:
        items = _news(ticker)
        if items:
            for item in items:
                title   = item.get("title","")
                source  = item.get("source","")
                date    = _fmt_date(item.get("date",""))
                url     = item.get("url","")
                summary = item.get("summary","")
                st.markdown(f"""
                <div style="padding:14px 0;border-bottom:1px solid rgba(255,255,255,0.05)">
                  <div style="font-size:11px;color:#475569;margin-bottom:6px">
                    {source} &nbsp;·&nbsp; {date}
                  </div>
                  <div style="font-size:14px;font-weight:500;color:#e2e8f0;
                              line-height:1.4;margin-bottom:6px">{title}</div>
                  {f'<div style="font-size:12.5px;color:#64748b;line-height:1.5">{summary[:200]}{"…" if len(summary)>200 else ""}</div>' if summary else ""}
                  {f'<a href="{url}" target="_blank" style="font-size:12px;color:#818cf8;text-decoration:none;margin-top:4px;display:inline-block">Read more →</a>' if url else ""}
                </div>""", unsafe_allow_html=True)
        else:
            st.markdown('<div style="color:#334155;text-align:center;padding:3rem 0;font-size:14px">No recent news available</div>',
                        unsafe_allow_html=True)

    # ─ Events ──────────────────────────────────────────────────────────────
    with t_ev:
        ev = _events(ticker)
        has_content = False

        # Next earnings from calendar
        cal = ev.get("calendar")
        if cal:
            try:
                ed = None
                if isinstance(cal, dict):
                    v = cal.get("Earnings Date") or cal.get("earnings_date")
                    if v:
                        ed = str(v[0])[:10] if isinstance(v,list) else str(v)[:10]
                if ed and len(ed)>=7:
                    mon = int(ed[5:7]); day = ed[8:10]
                    st.markdown('<div style="font-size:10.5px;color:#334155;text-transform:uppercase;letter-spacing:.1em;margin-bottom:12px">Upcoming Earnings</div>',
                                unsafe_allow_html=True)
                    st.markdown(f"""
                    <div style="background:rgba(99,102,241,0.08);border:1px solid rgba(99,102,241,0.2);
                                border-radius:10px;padding:14px 16px;margin-bottom:14px;
                                display:flex;align-items:center;gap:14px">
                      <div style="width:50px;height:50px;background:rgba(99,102,241,0.15);
                                  border-radius:8px;display:flex;flex-direction:column;
                                  align-items:center;justify-content:center;flex-shrink:0">
                        <span style="font-size:20px;font-weight:700;color:#818cf8;line-height:1">{day}</span>
                        <span style="font-size:10px;color:#6366f1;text-transform:uppercase">{MONTHS[mon]}</span>
                      </div>
                      <div>
                        <div style="font-size:14px;font-weight:500;color:#e2e8f0">Quarterly Result</div>
                        <div style="font-size:12px;color:#64748b;margin-top:2px">Release date</div>
                      </div>
                    </div>""", unsafe_allow_html=True)
                    has_content = True
            except Exception: pass

        # Earnings history
        earnings = ev.get("earnings")
        if earnings is not None and not earnings.empty:
            st.markdown('<div style="font-size:10.5px;color:#334155;text-transform:uppercase;letter-spacing:.1em;margin:12px 0 10px">Earnings History</div>',
                        unsafe_allow_html=True)
            try:
                df = earnings.copy()
                df.columns = [str(c) for c in df.columns]
                st.dataframe(df, use_container_width=True, hide_index=True)
                has_content = True
            except Exception: pass

        # Last dividend
        div = ev.get("last_div")
        if div:
            st.markdown('<div style="font-size:10.5px;color:#334155;text-transform:uppercase;letter-spacing:.1em;margin:12px 0 10px">Last Dividend</div>',
                        unsafe_allow_html=True)
            st.markdown(f"""
            <div style="background:rgba(16,185,129,0.05);border:1px solid rgba(16,185,129,0.15);
                        border-radius:10px;padding:14px 16px;
                        display:flex;justify-content:space-between;align-items:center">
              <div>
                <div style="font-size:14px;font-weight:500;color:#e2e8f0">Dividend</div>
                <div style="font-size:12px;color:#64748b;margin-top:2px">{div['date']}</div>
              </div>
              <div style="font-family:'IBM Plex Mono',monospace;font-size:20px;
                          font-weight:700;color:#10b981">
                {cur}{div['amount']:.4f}
              </div>
            </div>""", unsafe_allow_html=True)
            has_content = True

        if not has_content:
            st.markdown('<div style="color:#334155;text-align:center;padding:3rem 0;font-size:14px">No upcoming events found</div>',
                        unsafe_allow_html=True)
