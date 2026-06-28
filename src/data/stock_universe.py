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


# ─── Display name mapping ───────────────────────────────────────────────────
# Used by the search endpoint to match company names as well as tickers.

TICKER_NAMES: dict[str, str] = {
    # ── India – Technology ──────────────────────────────────────────────────
    "TCS.NS":        "Tata Consultancy Services",
    "INFY.NS":       "Infosys",
    "WIPRO.NS":      "Wipro",
    "HCLTECH.NS":    "HCL Technologies",
    "TECHM.NS":      "Tech Mahindra",
    "MPHASIS.NS":    "Mphasis",
    "PERSISTENT.NS": "Persistent Systems",
    "LTTS.NS":       "L&T Technology Services",
    "COFORGE.NS":    "Coforge",
    "KPIT.NS":       "KPIT Technologies",
    "HAPPSTMNDS.NS": "Happiest Minds Technologies",
    "INTELLECT.NS":  "Intellect Design Arena",
    "TATAELXSI.NS":  "Tata Elxsi",
    "TANLA.NS":      "Tanla Platforms",
    # ── India – Banking ─────────────────────────────────────────────────────
    "HDFCBANK.NS":   "HDFC Bank",
    "ICICIBANK.NS":  "ICICI Bank",
    "SBIN.NS":       "State Bank of India",
    "KOTAKBANK.NS":  "Kotak Mahindra Bank",
    "AXISBANK.NS":   "Axis Bank",
    "FEDERALBNK.NS": "Federal Bank",
    "IDFCFIRSTB.NS": "IDFC First Bank",
    "BANDHANBNK.NS": "Bandhan Bank",
    "RBLBANK.NS":    "RBL Bank",
    "INDUSINDBK.NS": "IndusInd Bank",
    "DCBBANK.NS":    "DCB Bank",
    "J&KBANK.NS":    "Jammu & Kashmir Bank",
    "KARSANBK.NS":   "Karur Vysya Bank",
    # ── India – Pharma ──────────────────────────────────────────────────────
    "SUNPHARMA.NS":  "Sun Pharmaceutical",
    "DRREDDY.NS":    "Dr. Reddy's Laboratories",
    "CIPLA.NS":      "Cipla",
    "DIVISLAB.NS":   "Divi's Laboratories",
    "AUROPHARMA.NS": "Aurobindo Pharma",
    "TORNTPHARM.NS": "Torrent Pharmaceuticals",
    "ALKEM.NS":      "Alkem Laboratories",
    "LALPATHLAB.NS": "Dr Lal Pathlabs",
    "METROPOLIS.NS": "Metropolis Healthcare",
    "IPCALAB.NS":    "IPCA Laboratories",
    "GRANULES.NS":   "Granules India",
    "AJANTPHARM.NS": "Ajanta Pharma",
    "NATCOPHARMA.NS":"Natco Pharma",
    "GLAND.NS":      "Gland Pharma",
    # ── India – FMCG ────────────────────────────────────────────────────────
    "HINDUNILVR.NS": "Hindustan Unilever",
    "ITC.NS":        "ITC",
    "NESTLEIND.NS":  "Nestle India",
    "BRITANNIA.NS":  "Britannia Industries",
    "DABUR.NS":      "Dabur India",
    "TATACONSUM.NS": "Tata Consumer Products",
    "GODREJCP.NS":   "Godrej Consumer Products",
    "MARICO.NS":     "Marico",
    "EMAMILTD.NS":   "Emami",
    "COLPAL.NS":     "Colgate-Palmolive India",
    "VSTIND.NS":     "VST Industries",
    "RADICO.NS":     "Radico Khaitan",
    "BIKAJI.NS":     "Bikaji Foods",
    # ── India – Auto ────────────────────────────────────────────────────────
    "MARUTI.NS":     "Maruti Suzuki",
    "TATAMOTORS.NS": "Tata Motors",
    "M&M.NS":        "Mahindra & Mahindra",
    "BAJAJ-AUTO.NS": "Bajaj Auto",
    "HEROMOTOCO.NS": "Hero MotoCorp",
    "BALKRISIND.NS": "Balkrishna Industries",
    "BHARATFORG.NS": "Bharat Forge",
    "MOTHERSON.NS":  "Samvardhana Motherson",
    "ASHOKLEY.NS":   "Ashok Leyland",
    "ESCORTS.NS":    "Escorts Kubota",
    "GABRIEL.NS":    "Gabriel India",
    "SUPRAJIT.NS":   "Suprajit Engineering",
    "ENDURANCE.NS":  "Endurance Technologies",
    # ── India – Energy ──────────────────────────────────────────────────────
    "RELIANCE.NS":   "Reliance Industries",
    "ONGC.NS":       "Oil and Natural Gas Corporation",
    "BPCL.NS":       "Bharat Petroleum",
    "NTPC.NS":       "NTPC",
    "POWERGRID.NS":  "Power Grid Corporation",
    "OIL.NS":        "Oil India",
    "MGL.NS":        "Mahanagar Gas",
    "IGL.NS":        "Indraprastha Gas",
    "PETRONET.NS":   "Petronet LNG",
    "GAIL.NS":       "GAIL India",
    "GULFOILLUB.NS": "Gulf Oil Lubricants",
    "SOTL.NS":       "Savita Oil Technologies",
    # ── India – Financial Services ──────────────────────────────────────────
    "BAJFINANCE.NS": "Bajaj Finance",
    "BAJAJFINSV.NS": "Bajaj Finserv",
    "HDFCLIFE.NS":   "HDFC Life Insurance",
    "SBILIFE.NS":    "SBI Life Insurance",
    "ICICIPRULI.NS": "ICICI Prudential Life Insurance",
    "CHOLAFIN.NS":   "Cholamandalam Investment",
    "MUTHOOTFIN.NS": "Muthoot Finance",
    "MANAPPURAM.NS": "Manappuram Finance",
    "LICHSGFIN.NS":  "LIC Housing Finance",
    "AAVAS.NS":      "Aavas Financiers",
    "CREDITACC.NS":  "Credit Access Grameen",
    "APTUS.NS":      "Aptus Value Housing Finance",
    # ── India – Metals ──────────────────────────────────────────────────────
    "TATASTEEL.NS":  "Tata Steel",
    "HINDALCO.NS":   "Hindalco Industries",
    "JSWSTEEL.NS":   "JSW Steel",
    "COALINDIA.NS":  "Coal India",
    "SAIL.NS":       "Steel Authority of India",
    "NATIONALUM.NS": "National Aluminium Company",
    "NMDC.NS":       "NMDC",
    "VEDL.NS":       "Vedanta",
    "RATNAMANI.NS":  "Ratnamani Metals & Tubes",
    "HIMATSEIDE.NS": "Himatsingka Seide",
    "SANDUMA.NS":    "Sandur Manganese & Iron Ores",
    # ── India – Infrastructure / Realty ─────────────────────────────────────
    "LT.NS":         "Larsen & Toubro",
    "ULTRACEMCO.NS": "UltraTech Cement",
    "GRASIM.NS":     "Grasim Industries",
    "ADANIENT.NS":   "Adani Enterprises",
    "ADANIPORTS.NS": "Adani Ports",
    "GODREJPROP.NS": "Godrej Properties",
    "OBEROIRLTY.NS": "Oberoi Realty",
    "PHOENIXLTD.NS": "Phoenix Mills",
    "PRESTIGE.NS":   "Prestige Estates",
    "SOBHA.NS":      "Sobha",
    "KOLTEPATIL.NS": "Kolte-Patil Developers",
    "SUNTECK.NS":    "Sunteck Realty",
    # ── India – Telecom ─────────────────────────────────────────────────────
    "BHARTIARTL.NS": "Bharti Airtel",
    "INDUSTOWER.NS": "Indus Towers",
    "TATACOMM.NS":   "Tata Communications",
    "RAILTEL.NS":    "RailTel Corporation",
    # ── US – Technology ─────────────────────────────────────────────────────
    "AAPL":  "Apple",
    "MSFT":  "Microsoft",
    "NVDA":  "NVIDIA",
    "GOOGL": "Alphabet (Google)",
    "META":  "Meta Platforms",
    "AMZN":  "Amazon",
    "AMD":   "Advanced Micro Devices",
    "CRM":   "Salesforce",
    "ADBE":  "Adobe",
    "INTC":  "Intel",
    "NOW":   "ServiceNow",
    "PANW":  "Palo Alto Networks",
    "SNOW":  "Snowflake",
    "ORCL":  "Oracle",
    "DDOG":  "Datadog",
    "ZS":    "Zscaler",
    "CRWD":  "CrowdStrike",
    "GTLB":  "GitLab",
    "BILL":  "Bill.com",
    "MDB":   "MongoDB",
    "NET":   "Cloudflare",
    "IONQ":  "IonQ",
    "SOUN":  "SoundHound AI",
    "BBAI":  "BigBear.ai",
    "LMND":  "Lemonade",
    # ── US – Healthcare ─────────────────────────────────────────────────────
    "JNJ":  "Johnson & Johnson",
    "UNH":  "UnitedHealth Group",
    "PFE":  "Pfizer",
    "ABBV": "AbbVie",
    "LLY":  "Eli Lilly",
    "MRK":  "Merck",
    "BMY":  "Bristol-Myers Squibb",
    "GILD": "Gilead Sciences",
    "REGN": "Regeneron Pharmaceuticals",
    "ISRG": "Intuitive Surgical",
    "VRTX": "Vertex Pharmaceuticals",
    "ZBH":  "Zimmer Biomet",
    "HOLX": "Hologic",
    "PODD": "Insulet Corporation",
    "ACAD": "Acadia Pharmaceuticals",
    "INSP": "Inspire Medical Systems",
    "OMCL": "Omnicell",
    "AXSM": "Axsome Therapeutics",
    "PRGO": "Perrigo",
    "HALO": "Halozyme Therapeutics",
    # ── US – Financial ───────────────────────────────────────────────────────
    "JPM":  "JPMorgan Chase",
    "BAC":  "Bank of America",
    "WFC":  "Wells Fargo",
    "GS":   "Goldman Sachs",
    "MS":   "Morgan Stanley",
    "BLK":  "BlackRock",
    "C":    "Citigroup",
    "AXP":  "American Express",
    "SCHW": "Charles Schwab",
    "PGR":  "Progressive Corporation",
    "CB":   "Chubb",
    "MET":  "MetLife",
    "ALLY": "Ally Financial",
    "WBS":  "Webster Financial",
    "FNB":  "F.N.B. Corporation",
    "BOKF": "BOK Financial",
    "FIBK": "First Interstate BancSystem",
    "NBTB": "NBT Bancorp",
    "SFNC": "Simmons First National",
    "HONE": "Harleysville National",
    # ── US – Consumer ───────────────────────────────────────────────────────
    "WMT":  "Walmart",
    "COST": "Costco",
    "PG":   "Procter & Gamble",
    "KO":   "Coca-Cola",
    "PEP":  "PepsiCo",
    "MCD":  "McDonald's",
    "SBUX": "Starbucks",
    "NKE":  "Nike",
    "TGT":  "Target",
    "TJX":  "TJX Companies",
    "LOW":  "Lowe's",
    "WING": "Wingstop",
    "TXRH": "Texas Roadhouse",
    "FIVE": "Five Below",
    "BJ":   "BJ's Wholesale Club",
    "SFM":  "Sprouts Farmers Market",
    "JACK": "Jack in the Box",
    "NAPA": "Duckhorn Portfolio",
    "PLBY": "PLBY Group",
    # ── US – Energy ─────────────────────────────────────────────────────────
    "XOM":  "ExxonMobil",
    "CVX":  "Chevron",
    "SLB":  "SLB (Schlumberger)",
    "EOG":  "EOG Resources",
    "MPC":  "Marathon Petroleum",
    "PSX":  "Phillips 66",
    "VLO":  "Valero Energy",
    "OXY":  "Occidental Petroleum",
    "CHRD": "Chord Energy",
    "MTDR": "Matador Resources",
    "SM":   "SM Energy",
    "RRC":  "Range Resources",
    "CIVI": "Civitas Resources",
    "TALO": "Talos Energy",
    # ── US – Industrial ─────────────────────────────────────────────────────
    "GE":   "GE Aerospace",
    "CAT":  "Caterpillar",
    "HON":  "Honeywell",
    "RTX":  "RTX Corporation",
    "BA":   "Boeing",
    "DE":   "Deere & Company",
    "EMR":  "Emerson Electric",
    "ETN":  "Eaton Corporation",
    "PH":   "Parker Hannifin",
    "ROK":  "Rockwell Automation",
    "AME":  "AMETEK",
    "GNRC": "Generac Holdings",
    "AAON": "AAON",
    "TREX": "Trex Company",
    "FWRD": "Forward Air",
    "KBAL": "Kimball International",
    "HAYN": "Haynes International",
    # ── US – Telecom ────────────────────────────────────────────────────────
    "T":    "AT&T",
    "VZ":   "Verizon",
    "TMUS": "T-Mobile US",
    "LUMN": "Lumen Technologies",
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
    """Returns all available size buckets for a market.

    India follows SEBI's official classification — Large (top 100), Mid
    (101–250), Small (251+). There is no 'Mega' tier in India.
    US uses the informal Mega/Large/Mid/Small convention.
    """
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