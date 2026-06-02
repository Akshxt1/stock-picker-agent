# src/data/stock_universe.py
#
# This is the master list of stocks the agents scan every week.
# Organised by: Market → Sector → Size (Large / Mid / Small / Mega)
#
# All Indian stocks use .NS (NSE) suffix — more liquid than BSE.
# US stocks use plain tickers.
#
# To add a new stock: just add its ticker to the right list below.

# ─── INDIAN STOCKS ─────────────────────────────────────────────────────────

INDIAN_STOCKS = {

    "Technology": {
        "Large": ["TCS.NS", "INFY.NS", "WIPRO.NS", "HCLTECH.NS", "TECHM.NS"],
        "Mid":   ["MPHASIS.NS", "PERSISTENT.NS", "LTTS.NS", "COFORGE.NS", "KPIT.NS"],
        "Small": ["HAPPSTMNDS.NS", "INTELLECT.NS", "TATAELXSI.NS", "TANLA.NS"],
    },

    "Banking": {
        "Large": ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "KOTAKBANK.NS", "AXISBANK.NS"],
        "Mid":   ["FEDERALBNK.NS", "IDFCFIRSTB.NS", "BANDHANBNK.NS", "RBLBANK.NS", "INDUSINDBK.NS"],
        "Small": ["DCBBANK.NS", "J&KBANK.NS", "KARSANBK.NS"],
    },

    "Pharma": {
        "Large": ["SUNPHARMA.NS", "DRREDDY.NS", "CIPLA.NS", "DIVISLAB.NS", "AUROPHARMA.NS"],
        "Mid":   ["TORNTPHARM.NS", "ALKEM.NS", "LALPATHLAB.NS", "METROPOLIS.NS", "IPCALAB.NS"],
        "Small": ["GRANULES.NS", "AJANTPHARM.NS", "NATCOPHARMA.NS", "GLAND.NS"],
    },

    "FMCG": {
        "Large": ["HINDUNILVR.NS", "ITC.NS", "NESTLEIND.NS", "BRITANNIA.NS", "DABUR.NS"],
        "Mid":   ["TATACONSUM.NS", "GODREJCP.NS", "MARICO.NS", "EMAMILTD.NS", "COLPAL.NS"],
        "Small": ["VSTIND.NS", "RADICO.NS", "BIKAJI.NS"],
    },

    "Auto": {
        "Large": ["MARUTI.NS", "TATAMOTORS.NS", "M&M.NS", "BAJAJ-AUTO.NS", "HEROMOTOCO.NS"],
        "Mid":   ["BALKRISIND.NS", "BHARATFORG.NS", "MOTHERSON.NS", "ASHOKLEY.NS", "ESCORTS.NS"],
        "Small": ["GABRIEL.NS", "SUPRAJIT.NS", "ENDURANCE.NS"],
    },

    "Energy": {
        "Large": ["RELIANCE.NS", "ONGC.NS", "BPCL.NS", "NTPC.NS", "POWERGRID.NS"],
        "Mid":   ["OIL.NS", "MGL.NS", "IGL.NS", "PETRONET.NS", "GAIL.NS"],
        "Small": ["GULFOILLUB.NS", "SOTL.NS"],
    },

    "Financial Services": {
        "Large": ["BAJFINANCE.NS", "BAJAJFINSV.NS", "HDFCLIFE.NS", "SBILIFE.NS", "ICICIPRULI.NS"],
        "Mid":   ["CHOLAFIN.NS", "MUTHOOTFIN.NS", "MANAPPURAM.NS", "LICHSGFIN.NS"],
        "Small": ["AAVAS.NS", "CREDITACC.NS", "APTUS.NS"],
    },

    "Metals": {
        "Large": ["TATASTEEL.NS", "HINDALCO.NS", "JSWSTEEL.NS", "COALINDIA.NS", "SAIL.NS"],
        "Mid":   ["NATIONALUM.NS", "NMDC.NS", "VEDL.NS", "RATNAMANI.NS"],
        "Small": ["HIMATSEIDE.NS", "SANDUMA.NS"],
    },

    "Infrastructure": {
        "Large": ["LT.NS", "ULTRACEMCO.NS", "GRASIM.NS", "ADANIENT.NS", "ADANIPORTS.NS"],
        "Mid":   ["GODREJPROP.NS", "OBEROIRLTY.NS", "PHOENIXLTD.NS", "PRESTIGE.NS"],
        "Small": ["SOBHA.NS", "KOLTEPATIL.NS", "SUNTECK.NS"],
    },

    "Telecom": {
        "Large": ["BHARTIARTL.NS", "INDUSTOWER.NS"],
        "Mid":   ["TATACOMM.NS", "RAILTEL.NS"],
        "Small": [],
    },

}


# ─── US STOCKS ─────────────────────────────────────────────────────────────

US_STOCKS = {

    "Technology": {
        "Mega":  ["AAPL", "MSFT", "NVDA", "GOOGL", "META", "AMZN"],
        "Large": ["AMD", "CRM", "ADBE", "INTC", "NOW", "PANW", "SNOW", "ORCL"],
        "Mid":   ["DDOG", "ZS", "CRWD", "GTLB", "BILL", "MDB", "NET"],
        "Small": ["IONQ", "SOUN", "BBAI", "LMND"],
    },

    "Healthcare": {
        "Mega":  ["JNJ", "UNH", "PFE", "ABBV", "LLY"],
        "Large": ["MRK", "BMY", "GILD", "REGN", "ISRG", "VRTX", "ZBH"],
        "Mid":   ["HOLX", "PODD", "ACAD", "INSP", "OMCL"],
        "Small": ["AXSM", "PRGO", "HALO"],
    },

    "Financial": {
        "Mega":  ["JPM", "BAC", "WFC", "GS", "MS", "BLK"],
        "Large": ["C", "AXP", "SCHW", "PGR", "CB", "MET"],
        "Mid":   ["ALLY", "WBS", "FNB", "BOKF", "FIBK"],
        "Small": ["NBTB", "SFNC", "HONE"],
    },

    "Consumer": {
        "Mega":  ["AMZN", "WMT", "COST", "PG", "KO", "PEP"],
        "Large": ["MCD", "SBUX", "NKE", "TGT", "TJX", "LOW"],
        "Mid":   ["WING", "TXRH", "FIVE", "BJ", "SFM"],
        "Small": ["JACK", "NAPA", "PLBY"],
    },

    "Energy": {
        "Mega":  ["XOM", "CVX"],
        "Large": ["SLB", "EOG", "MPC", "PSX", "VLO", "OXY"],
        "Mid":   ["CHRD", "MTDR", "SM", "RRC"],
        "Small": ["CIVI", "TALO"],
    },

    "Industrial": {
        "Mega":  ["GE", "CAT", "HON", "RTX", "BA"],
        "Large": ["DE", "EMR", "ETN", "PH", "ROK", "AME"],
        "Mid":   ["GNRC", "AAON", "TREX", "FWRD"],
        "Small": ["KBAL", "HAYN"],
    },

    "Telecom": {
        "Mega":  ["T", "VZ"],
        "Large": ["TMUS", "LUMN"],
        "Mid":   [],
        "Small": [],
    },

}


# ─── Helper functions ───────────────────────────────────────────────────────

def get_stocks(market: str, sector: str = None, size: str = None) -> list:
    """
    Retrieve stocks filtered by market, sector, and/or size.

    Args:
        market : "INDIA" or "US"
        sector : e.g. "Technology", "Banking", "Healthcare"
                 Pass None to get ALL sectors
        size   : "Large", "Mid", "Small", "Mega" (Mega only for US)
                 Pass None to get ALL sizes

    Returns:
        Flat list of ticker strings

    Examples:
        get_stocks("INDIA", "Technology", "Large")
        → ["TCS.NS", "INFY.NS", "WIPRO.NS", "HCLTECH.NS", "TECHM.NS"]

        get_stocks("US", "Healthcare", None)
        → all US healthcare stocks across all sizes

        get_stocks("INDIA", None, "Mid")
        → all Indian mid cap stocks across all sectors
    """
    universe = INDIAN_STOCKS if market.upper() == "INDIA" else US_STOCKS
    tickers  = []

    sectors = [sector] if sector else list(universe.keys())

    for sec in sectors:
        if sec not in universe:
            continue
        sizes = [size] if size else list(universe[sec].keys())
        for s in sizes:
            if s in universe[sec]:
                tickers.extend(universe[sec][s])

    return tickers


def get_all_sectors(market: str) -> list:
    """Returns list of all sector names for a given market."""
    universe = INDIAN_STOCKS if market.upper() == "INDIA" else US_STOCKS
    return list(universe.keys())


def get_all_sizes(market: str) -> list:
    """Returns all available size buckets for a market."""
    if market.upper() == "INDIA":
        return ["Large", "Mid", "Small"]
    return ["Mega", "Large", "Mid", "Small"]


def get_universe_summary() -> dict:
    """Prints a count of stocks across all markets, sectors, and sizes."""
    summary = {}

    for market, universe in [("INDIA", INDIAN_STOCKS), ("US", US_STOCKS)]:
        summary[market] = {}
        total = 0
        for sector, sizes in universe.items():
            count = sum(len(v) for v in sizes.values())
            summary[market][sector] = count
            total += count
        summary[market]["TOTAL"] = total

    return summary


# ─── Quick test ─────────────────────────────────────────────────────────────
# Run with: uv run src/data/stock_universe.py

if __name__ == "__main__":
    print("=" * 55)
    print("STOCK UNIVERSE SUMMARY")
    print("=" * 55)

    summary = get_universe_summary()
    for market, sectors in summary.items():
        print(f"\n  [{market}]")
        for sector, count in sectors.items():
            label = "──────" if sector == "TOTAL" else sector
            print(f"    {label:30} : {count} stocks")

    print("\n" + "=" * 55)
    print("SAMPLE QUERIES")
    print("=" * 55)

    samples = [
        ("INDIA", "Technology", "Large"),
        ("INDIA", "Banking",    "Mid"),
        ("US",    "Healthcare", "Mega"),
        ("US",    "Technology", "Small"),
    ]

    for market, sector, size in samples:
        result = get_stocks(market, sector, size)
        print(f"\n  {market} | {sector} | {size} Cap:")
        print(f"    {result}")