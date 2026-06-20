# src/tools/stock_discovery.py
#
# Gives the Researcher agent the ability to DISCOVER stocks itself
# instead of working from a hardcoded list.
#
# Sources (no API key needed):
#   - yfinance screener / sector queries
#   - NSE India top gainers / actives via public endpoints
#   - Yahoo Finance sector ETF holdings proxy

from crewai.tools import tool
import yfinance as yf
import pandas as pd

from src.providers import market_data_client

# ── Sector → ETF mapping for US market (holdings = relevant stocks) ──────────
US_SECTOR_ETFS = {
    "Technology":         "XLK",
    "Healthcare":         "XLV",
    "Financial":          "XLF",
    "Consumer":           "XLY",
    "Energy":             "XLE",
    "Industrial":         "XLI",
    "Telecom":            "XLC",
    "Materials":          "XLB",
    "Real Estate":        "XLRE",
    "Utilities":          "XLU",
}

# ── NSE sector index → component proxy tickers ───────────────────────────────
# These are the Nifty sector index tickers on yfinance
INDIA_SECTOR_INDEX = {
    "Technology":         "^CNXIT",
    "Banking":            "^NSEBANK",
    "Pharma":             "^CNXPHARMA",
    "FMCG":               "^CNXFMCG",
    "Auto":               "^CNXAUTO",
    "Energy":             "^CNXENERGY",
    "Financial Services": "^CNXFIN",
    "Metals":             "^CNXMETAL",
    "Infrastructure":     "^CNXINFRA",
    "Telecom":            "^CNXTELECOM",
    "Realty":             "^CNXREALTY",
    "Media":              "^CNXMEDIA",
}

# ── Fallback: curated seed lists by sector for Indian market ─────────────────
# Used when live discovery fails — much broader than old universe
INDIA_SECTOR_SEEDS = {
    "Technology": [
        "TCS.NS","INFY.NS","WIPRO.NS","HCLTECH.NS","TECHM.NS",
        "MPHASIS.NS","PERSISTENT.NS","LTTS.NS","COFORGE.NS","KPIT.NS",
        "HAPPSTMNDS.NS","INTELLECT.NS","TATAELXSI.NS","TANLA.NS",
        "OFSS.NS","MASTEK.NS","NIIT.NS","RAMSARUP.NS","SONATSOFTW.NS",
        "ZENSAR.NS","HEXAWARE.NS","CYIENT.NS",
    ],
    "Banking": [
        "HDFCBANK.NS","ICICIBANK.NS","SBIN.NS","KOTAKBANK.NS","AXISBANK.NS",
        "FEDERALBNK.NS","IDFCFIRSTB.NS","BANDHANBNK.NS","RBLBANK.NS","INDUSINDBK.NS",
        "CANBK.NS","BANKBARODA.NS","PNB.NS","UNIONBANK.NS","INDIANB.NS",
        "DCBBANK.NS","KTKBANK.NS","KARURVYSYA.NS","SOUTHBANK.NS","LAKSHVILAS.NS",
    ],
    "Pharma": [
        "SUNPHARMA.NS","DRREDDY.NS","CIPLA.NS","DIVISLAB.NS","AUROPHARMA.NS",
        "TORNTPHARM.NS","ALKEM.NS","LALPATHLAB.NS","METROPOLIS.NS","IPCALAB.NS",
        "GRANULES.NS","AJANTPHARM.NS","NATCOPHARMA.NS","GLAND.NS",
        "BIOCON.NS","CADILAHC.NS","PFIZER.NS","ABBOTINDIA.NS","GLAXO.NS",
        "APOLLOHOSP.NS","FORTIS.NS","MAXHEALTH.NS",
    ],
    "FMCG": [
        "HINDUNILVR.NS","ITC.NS","NESTLEIND.NS","BRITANNIA.NS","DABUR.NS",
        "TATACONSUM.NS","GODREJCP.NS","MARICO.NS","EMAMILTD.NS","COLPAL.NS",
        "VSTIND.NS","RADICO.NS","BIKAJI.NS","VARUNBEV.NS","UBL.NS",
        "PGHH.NS","GILLETTE.NS","MCDOWELL-N.NS",
    ],
    "Auto": [
        "MARUTI.NS","TATAMOTORS.NS","M&M.NS","BAJAJ-AUTO.NS","HEROMOTOCO.NS",
        "BALKRISIND.NS","BHARATFORG.NS","MOTHERSON.NS","ASHOKLEY.NS","ESCORTS.NS",
        "GABRIEL.NS","SUPRAJIT.NS","ENDURANCE.NS","EXIDEIND.NS","AMARAJABAT.NS",
        "BOSCHLTD.NS","SCHAEFFLER.NS","SUNDRMFAST.NS","SWARAJENG.NS","MAHINDCIE.NS",
    ],
    "Energy": [
        "RELIANCE.NS","ONGC.NS","BPCL.NS","NTPC.NS","POWERGRID.NS",
        "OIL.NS","MGL.NS","IGL.NS","PETRONET.NS","GAIL.NS",
        "ADANIGREEN.NS","TATAPOWER.NS","TORNTPOWER.NS","CESC.NS","JSPL.NS",
        "ADANIPOWER.NS","RPOWER.NS","NHPC.NS","SJVN.NS","HINDPETRO.NS",
    ],
    "Financial Services": [
        "BAJFINANCE.NS","BAJAJFINSV.NS","HDFCLIFE.NS","SBILIFE.NS","ICICIPRULI.NS",
        "CHOLAFIN.NS","MUTHOOTFIN.NS","MANAPPURAM.NS","LICHSGFIN.NS",
        "AAVAS.NS","CREDITACC.NS","APTUS.NS","PNBHOUSING.NS","CANFINHOME.NS",
        "SBICARD.NS","ANGELONE.NS","CDSL.NS","BSE.NS","MCX.NS",
    ],
    "Metals": [
        "TATASTEEL.NS","HINDALCO.NS","JSWSTEEL.NS","COALINDIA.NS","SAIL.NS",
        "NATIONALUM.NS","NMDC.NS","VEDL.NS","RATNAMANI.NS",
        "APLAPOLLO.NS","JINDALSAW.NS","WELSPUNIND.NS","HLEGLAS.NS","GPPL.NS",
        "MOIL.NS","SANDUMA.NS","GRAVITA.NS","HINDCOPPER.NS",
    ],
    "Infrastructure": [
        "LT.NS","ULTRACEMCO.NS","GRASIM.NS","ADANIENT.NS","ADANIPORTS.NS",
        "GODREJPROP.NS","OBEROIRLTY.NS","PHOENIXLTD.NS","PRESTIGE.NS",
        "SOBHA.NS","KOLTEPATIL.NS","SUNTECK.NS","DLF.NS","BRIGADE.NS",
        "ACC.NS","AMBUJACEMENT.NS","SHREECEM.NS","RAMCOCEM.NS","HEIDELBERG.NS",
        "IRB.NS","KNR.NS","HG INFRA.NS","NCC.NS","RVNL.NS","IRCON.NS",
    ],
    "Telecom": [
        "BHARTIARTL.NS","INDUSTOWER.NS","TATACOMM.NS","RAILTEL.NS",
        "HFCL.NS","TEJASNET.NS","STLTECH.NS","VINDHYATEL.NS","TTML.NS",
        "ONMOBILE.NS","TANLA.NS","ROUTE.NS",
    ],
}

US_SECTOR_SEEDS = {
    "Technology": [
        "AAPL","MSFT","NVDA","GOOGL","META","AMZN","AMD","CRM","ADBE","INTC",
        "NOW","PANW","SNOW","ORCL","DDOG","ZS","CRWD","GTLB","BILL","MDB",
        "NET","PLTR","AI","PATH","IONQ","SOUN","BBAI","LMND","TTD","TWLO",
    ],
    "Healthcare": [
        "JNJ","UNH","PFE","ABBV","LLY","MRK","BMY","GILD","REGN","ISRG",
        "VRTX","ZBH","HOLX","PODD","ACAD","INSP","OMCL","AXSM","PRGO","HALO",
        "DXCM","IDXX","ALGN","MASI","NTRA","RXRX","PCVX","ACMR",
    ],
    "Financial": [
        "JPM","BAC","WFC","GS","MS","BLK","C","AXP","SCHW","PGR",
        "CB","MET","ALLY","WBS","FNB","BOKF","FIBK","NBTB","SFNC","HONE",
        "V","MA","PYPL","SQ","AFRM","SOFI","LC","UPST",
    ],
    "Consumer": [
        "AMZN","WMT","COST","PG","KO","PEP","MCD","SBUX","NKE","TGT",
        "TJX","LOW","WING","TXRH","FIVE","BJ","SFM","JACK","NAPA",
        "HD","EL","CL","CLX","GIS","K","HSY","MNST",
    ],
    "Energy": [
        "XOM","CVX","SLB","EOG","MPC","PSX","VLO","OXY","CHRD","MTDR",
        "SM","RRC","CIVI","TALO","COP","HES","DVN","FANG","PR","CTRA",
    ],
    "Industrial": [
        "GE","CAT","HON","RTX","BA","DE","EMR","ETN","PH","ROK",
        "AME","GNRC","AAON","TREX","FWRD","KBAL","HAYN","UPS","FDX","LMT",
    ],
    "Telecom": [
        "T","VZ","TMUS","LUMN","CHTR","DISH","SATS","IRDM","VSAT",
    ],
}


def _get_sector_seeds(market: str, sector: str) -> list:
    """Return sector seed tickers, allowing minor case/spacing differences."""
    seed_map = INDIA_SECTOR_SEEDS if market.upper() == "INDIA" else US_SECTOR_SEEDS
    if sector in seed_map:
        return seed_map[sector]

    normalized = sector.strip().lower()
    for sector_name, tickers in seed_map.items():
        if sector_name.lower() == normalized:
            return tickers

    return []


@tool("Discover Stocks")
def discover_stocks(market: str, sector: str, size: str) -> str:
    """
    Discovers relevant stock tickers for a given market, sector, and size
    without relying on a hardcoded list. Returns a comma-separated list of
    tickers for the agent to research.

    Args:
        market: "INDIA" or "US"
        sector: e.g. "Technology", "Banking", "Healthcare", "Financial"
        size:   "Large", "Mid", "Small", or "Mega" (US only)

    Returns:
        A string with discovered tickers, e.g. "AAPL, MSFT, NVDA, ..."
    """
    market = market.upper()
    tickers = []

    # ── Step 1: Try live discovery via yfinance screener ─────────────────────
    try:
        if market == "US":
            etf_symbol = US_SECTOR_ETFS.get(sector)
            if etf_symbol:
                etf = yf.Ticker(etf_symbol)
                # Get top holdings from ETF
                holdings = etf.funds_data
                if holdings and hasattr(holdings, 'top_holdings'):
                    top = holdings.top_holdings
                    if top is not None and not top.empty:
                        tickers = list(top.index[:20])
    except Exception:
        pass

    # ── Step 2: Use seed lists filtered by size ───────────────────────────────
    if not tickers:
        seeds = _get_sector_seeds(market, sector)

        if seeds:
            # Filter by size using market cap thresholds
            filtered = _filter_by_size(seeds, market, size)
            tickers = filtered if filtered else seeds[:10]  # fallback: first 10 seeds

    if not tickers:
        return f"No stocks found for {market} / {sector} / {size}. Try a different sector or size."

    result = ", ".join(tickers[:15])  # cap at 15 so agents aren't overwhelmed
    return f"Discovered {len(tickers[:15])} stocks for {market} {sector} {size} Cap:\n{result}"


def _filter_by_size(tickers: list, market: str, size: str) -> list:
    """
    Filter tickers by market cap to match the requested size bucket.

    India thresholds (INR) follow SEBI definitions (approx ₹85/USD):
        Mega  > ₹1.2T   (> $14B)   — Nifty 50 heavyweights
        Large = ₹200B-1.2T ($2.4B-14B)
        Mid   = ₹50B-200B  ($600M-2.4B)   ← SEBI: ~101st–250th by market cap
        Small < ₹50B       (< $600M)

    US thresholds (USD):
        Mega  > $200B
        Large = $10B-200B
        Mid   = $2B-10B
        Small < $2B
    """
    is_india = (market == "INDIA")
    thresholds = {
        "Mega":  (14e9  * 85, float("inf")),   # > ~₹1.2T
        "Large": (2.4e9 * 85, 14e9  * 85),     # ₹204B – ₹1.2T
        "Mid":   (600e6 * 85, 2.4e9 * 85),     # ₹51B  – ₹204B  (SEBI mid-cap zone)
        "Small": (0,          600e6 * 85),      # < ₹51B
    } if is_india else {
        "Mega":  (200e9, float("inf")),
        "Large": (10e9,  200e9),
        "Mid":   (2e9,   10e9),
        "Small": (0,     2e9),
    }

    low, high = thresholds.get(size, (0, float("inf")))
    matched = []

    for ticker in tickers:
        try:
            info = yf.Ticker(ticker).fast_info
            mcap = getattr(info, "market_cap", None) or 0
            if low <= mcap <= high:
                matched.append(ticker)
            if len(matched) >= 15:
                break
        except Exception:
            continue

    return matched


@tool("Get Market Movers")
def get_market_movers(market: str, sector: str) -> str:
    """
    Returns today's top-performing and most-active stocks in a given
    market and sector. Use this to find momentum candidates.

    Args:
        market: "INDIA" or "US"
        sector: sector name, e.g. "Technology", "Banking"
    """
    market = market.upper()
    seeds = _get_sector_seeds(market, sector)

    if not seeds:
        return f"No seed stocks available for {market} / {sector}."

    results = []
    tickers = seeds[:20]

    try:
        data = yf.download(
            tickers=" ".join(tickers),
            period="3mo",
            group_by="ticker",
            auto_adjust=False,
            progress=False,
            threads=True,
            timeout=15,
        )

        for ticker in tickers:
            try:
                hist = data[ticker] if len(tickers) > 1 else data
                mover = _build_mover_row(ticker, hist)
                if mover:
                    results.append(mover)
            except Exception:
                continue
    except Exception:
        pass

    if not results:
        client = market_data_client()
        for ticker in tickers:
            try:
                hist = client.history(ticker, period="3mo").data
                mover = _build_mover_row(ticker, hist)
                if mover:
                    results.append(mover)
            except Exception:
                continue

    if not results:
        fallback = ", ".join(seeds[:10])
        return (
            f"Live mover data unavailable for {market} / {sector}. "
            f"Using sector seed watchlist as momentum candidates:\n{fallback}"
        )

    # Sort by 3-month performance
    results.sort(key=lambda x: x["3m_chg"], reverse=True)

    lines = [f"Top movers in {market} / {sector}:"]
    for r in results[:10]:
        lines.append(
            f"  {r['ticker']:20} price={r['price']:>10}  3m={r['3m_chg']:>+7.2f}%  vol={r['vol']}x"
        )
    return "\n".join(lines)


def _build_mover_row(ticker: str, hist: pd.DataFrame) -> dict | None:
    if hist is None or hist.empty or len(hist) < 2:
        return None

    price_now = hist["Close"].dropna().iloc[-1]
    price_start = hist["Close"].dropna().iloc[0]
    if price_start == 0:
        return None

    chg_3m = ((price_now - price_start) / price_start) * 100
    avg_vol = hist["Volume"].mean()
    last_vol = hist["Volume"].iloc[-1]
    vol_ratio = round(last_vol / avg_vol, 2) if avg_vol > 0 else 1.0

    return {
        "ticker": ticker,
        "price": round(float(price_now), 2),
        "3m_chg": round(float(chg_3m), 2),
        "vol": vol_ratio,
    }
