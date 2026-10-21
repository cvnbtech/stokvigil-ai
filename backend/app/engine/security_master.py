"""
StokVigil AI — Institutional Security Master Engine
Maintains an authoritative in-memory directory of all Indian equities (NSE & BSE)
bridged by their immutable depository primary key: ISIN (International Securities Identification Number).
Resolves ICICI Direct proprietary broker codes (TELCO, INFTEC, HDFBAN) and exchange tickers
deterministically with sub-millisecond O(1) latency in CPU RAM.
"""

import os
import csv
import io
import time
import logging
import urllib.request
import threading
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger("stokvigil.engine.security_master")

# Local cache paths
_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
_MASTER_CACHE_FILE = os.path.join(_DATA_DIR, "security_master_nse.csv")
_CACHE_TTL_SECONDS = 86400.0 * 3.0  # 3 days

# Global in-memory security directory
_ISIN_TO_SECURITY: Dict[str, Dict[str, Any]] = {}
_SYMBOL_TO_ISIN: Dict[str, str] = {}
_MASTER_LOCK = threading.Lock()
_MASTER_INITIALIZED = False

# Authoritative ICICI Direct Proprietary Broker Code Dictionary
# Maps 1990s legacy broker abbreviations directly to official ISIN & NSE Symbols
ICICI_PROPRIETARY_CODE_MAP: Dict[str, Dict[str, str]] = {
    "TELCO": {"isin": "INE155A01022", "symbol": "TATAMOTORS", "name": "Tata Motors Limited"},
    "TATMOT": {"isin": "INE155A01022", "symbol": "TATAMOTORS", "name": "Tata Motors Limited"},
    "TMCV": {"isin": "INE1TAE01010", "symbol": "TMCV", "name": "Tata Motors Commercial Vehicles Ltd"},
    "TMPV": {"isin": "INE155A01022", "symbol": "TATAMOTORS", "name": "Tata Motors Passenger Vehicles Ltd"},
    "INFTEC": {"isin": "INE009A01021", "symbol": "INFY", "name": "Infosys Limited"},
    "HDFBAN": {"isin": "INE040A01034", "symbol": "HDFCBANK", "name": "HDFC Bank Limited"},
    "LARTOU": {"isin": "INE018A01030", "symbol": "LT", "name": "Larsen & Toubro Limited"},
    "STABAN": {"isin": "INE062A01020", "symbol": "SBIN", "name": "State Bank of India"},
    "MARUTI": {"isin": "INE585B01010", "symbol": "MARUTI", "name": "Maruti Suzuki India Limited"},
    "RELIND": {"isin": "INE002A01018", "symbol": "RELIANCE", "name": "Reliance Industries Limited"},
    "BAJFI": {"isin": "INE296A01024", "symbol": "BAJFINANCE", "name": "Bajaj Finance Limited"},
    "BAFINS": {"isin": "INE918I01018", "symbol": "BAJAJFINSV", "name": "Bajaj Finserv Limited"},
    "AXIBAN": {"isin": "INE238A01034", "symbol": "AXISBANK", "name": "Axis Bank Limited"},
    "KOTMAH": {"isin": "INE237A01028", "symbol": "KOTAKBANK", "name": "Kotak Mahindra Bank Limited"},
    "BHAAIR": {"isin": "INE397D01024", "symbol": "BHARTIARTL", "name": "Bharti Airtel Limited"},
    "HINLEV": {"isin": "INE030A01027", "symbol": "HINDUNILVR", "name": "Hindustan Unilever Limited"},
    "ITC": {"isin": "INE154A01025", "symbol": "ITC", "name": "ITC Limited"},
    "ASIPAI": {"isin": "INE021A01026", "symbol": "ASIANPAINT", "name": "Asian Paints Limited"},
    "TITIND": {"isin": "INE280A01028", "symbol": "TITAN", "name": "Titan Company Limited"},
    "SUNPHA": {"isin": "INE044A01036", "symbol": "SUNPHARMA", "name": "Sun Pharmaceutical Industries Ltd"},
    "TATAST": {"isin": "INE081A01020", "symbol": "TATASTEEL", "name": "Tata Steel Limited"},
    "TATCON": {"isin": "INE192A01025", "symbol": "TATACONSUM", "name": "Tata Consumer Products Limited"},
    "TCS": {"isin": "INE467B01029", "symbol": "TCS", "name": "Tata Consultancy Services Limited"},
    "WIPRO": {"isin": "INE075A01022", "symbol": "WIPRO", "name": "Wipro Limited"},
    "HCLTEC": {"isin": "INE860A01027", "symbol": "HCLTECH", "name": "HCL Technologies Limited"},
    "POWGRI": {"isin": "INE752E01010", "symbol": "POWERGRID", "name": "Power Grid Corporation of India Ltd"},
    "NTPC": {"isin": "INE733E01010", "symbol": "NTPC", "name": "NTPC Limited"},
    "ONGC": {"isin": "INE213A01029", "symbol": "ONGC", "name": "Oil & Natural Gas Corporation Limited"},
    "COALIN": {"isin": "INE522F01014", "symbol": "COALINDIA", "name": "Coal India Limited"},
    "ULTRAC": {"isin": "INE481G01011", "symbol": "ULTRACEMCO", "name": "UltraTech Cement Limited"},
    "GRASIM": {"isin": "INE047A01021", "symbol": "GRASIM", "name": "Grasim Industries Limited"},
    "JSWSTE": {"isin": "INE019A01038", "symbol": "JSWSTEEL", "name": "JSW Steel Limited"},
    "ADAPOR": {"isin": "INE742F01042", "symbol": "ADANIPORTS", "name": "Adani Ports and Special Economic Zone Ltd"},
    "ADIENT": {"isin": "INE423A01024", "symbol": "ADANIENT", "name": "Adani Enterprises Limited"},
    "CIPLA": {"isin": "INE059A01026", "symbol": "CIPLA", "name": "Cipla Limited"},
    "DRREDD": {"isin": "INE089A01023", "symbol": "DRREDDY", "name": "Dr. Reddy's Laboratories Limited"},
    "DIVLAB": {"isin": "INE361B01024", "symbol": "DIVISLAB", "name": "Divi's Laboratories Limited"},
    "APOHOS": {"isin": "INE437A01024", "symbol": "APOLLOHOSP", "name": "Apollo Hospitals Enterprise Limited"},
    "EICMOT": {"isin": "INE066A01021", "symbol": "EICHERMOT", "name": "Eicher Motors Limited"},
    "BRIIND": {"isin": "INE216A01030", "symbol": "BRITANNIA", "name": "Britannia Industries Limited"},
    "BAAUTO": {"isin": "INE917I01010", "symbol": "BAJAJ-AUTO", "name": "Bajaj Auto Limited"},
    "INDUSH": {"isin": "INE095A01012", "symbol": "INDUSINDBK", "name": "IndusInd Bank Limited"},
    "NESIND": {"isin": "INE239A01016", "symbol": "NESTLEIND", "name": "Nestle India Limited"},
    "M&M": {"isin": "INE101A01026", "symbol": "M&M", "name": "Mahindra & Mahindra Limited"},
    "HDFCLF": {"isin": "INE795G01014", "symbol": "HDFCLIFE", "name": "HDFC Life Insurance Company Limited"},
    "SBILIF": {"isin": "INE123W01016", "symbol": "SBILIFE", "name": "SBI Life Insurance Company Limited"},
    "BOSCH": {"isin": "INE323A01026", "symbol": "BOSCHLTD", "name": "Bosch Limited"},
    "HERHON": {"isin": "INE158A01026", "symbol": "HEROMOTOCO", "name": "Hero MotoCorp Limited"},
    "HINDAL": {"isin": "INE038A01020", "symbol": "HINDALCO", "name": "Hindalco Industries Limited"},
    "VEDAN": {"isin": "INE205A01025", "symbol": "VEDL", "name": "Vedanta Limited"},
    "ZOMATO": {"isin": "INE758T01015", "symbol": "ZOMATO", "name": "Zomato Limited"},
    "PAYTM": {"isin": "INE982J01020", "symbol": "PAYTM", "name": "One97 Communications Limited"},
    "JIOFIN": {"isin": "INE758E01017", "symbol": "JIOFIN", "name": "Jio Financial Services Limited"},
}


def is_valid_isin(code: str) -> bool:
    """Validates 12-character Indian depository ISIN format (INE... or INF...)."""
    if not code or not isinstance(code, str):
        return False
    clean = code.strip().upper()
    return len(clean) == 12 and (clean.startswith("INE") or clean.startswith("INF") or clean.startswith("IN9"))


def _parse_csv_into_master(csv_content: str):
    """Parses official NSE EQUITY_L.csv content into global memory dictionaries."""
    global _ISIN_TO_SECURITY, _SYMBOL_TO_ISIN
    reader = csv.DictReader(io.StringIO(csv_content))
    if not reader.fieldnames:
        return

    clean_fields = [f.strip() for f in reader.fieldnames]
    reader.fieldnames = clean_fields

    isin_map: Dict[str, Dict[str, Any]] = {}
    sym_map: Dict[str, str] = {}

    for row in reader:
        sym = str(row.get("SYMBOL", "")).strip().upper()
        isin = str(row.get("ISIN NUMBER", "")).strip().upper()
        name = str(row.get("NAME OF COMPANY", "")).strip()
        series = str(row.get("SERIES", "")).strip().upper()

        if isin and is_valid_isin(isin) and sym:
            # Prefer EQ series or first occurrence
            if isin not in isin_map or series == "EQ":
                isin_map[isin] = {
                    "isin": isin,
                    "symbol": sym,
                    "company_name": name,
                    "exchange": "NSE",
                    "series": series
                }
            if sym not in sym_map or series == "EQ":
                sym_map[sym] = isin

    # Also register ICICI proprietary codes & enforce canonical primary symbols
    for icici_code, meta in ICICI_PROPRIETARY_CODE_MAP.items():
        code_upper = icici_code.upper().strip()
        isin_val = meta["isin"]
        target_sym = meta["symbol"]
        name_val = meta["name"]
        
        # Enforce the widely recognized trading ticker (e.g. TATAMOTORS instead of TMPV)
        isin_map[isin_val] = {
            "isin": isin_val,
            "symbol": target_sym,
            "company_name": name_val,
            "exchange": "NSE",
            "series": "EQ"
        }
        sym_map[code_upper] = isin_val
        sym_map[target_sym] = isin_val

    _ISIN_TO_SECURITY.update(isin_map)
    _SYMBOL_TO_ISIN.update(sym_map)
    logger.info(f"✅ Security Master loaded: {len(_ISIN_TO_SECURITY)} unique ISINs, {len(_SYMBOL_TO_ISIN)} symbol mappings in RAM.")


def init_security_master(force_refresh: bool = False) -> bool:
    """
    Initializes the in-memory Security Master.
    Loads from local disk cache if available and fresh; otherwise downloads live from NSE archives.
    Executes in < 0.05 seconds when reading from disk cache.
    """
    global _MASTER_INITIALIZED
    with _MASTER_LOCK:
        if _MASTER_INITIALIZED and not force_refresh:
            return True

        os.makedirs(_DATA_DIR, exist_ok=True)
        now = time.time()
        csv_content = ""

        # 1. Try local disk cache
        if not force_refresh and os.path.exists(_MASTER_CACHE_FILE):
            try:
                mtime = os.path.getmtime(_MASTER_CACHE_FILE)
                if (now - mtime) < _CACHE_TTL_SECONDS:
                    with open(_MASTER_CACHE_FILE, "r", encoding="utf-8", errors="ignore") as f:
                        csv_content = f.read()
                    if csv_content and len(csv_content) > 1000:
                        _parse_csv_into_master(csv_content)
                        _MASTER_INITIALIZED = True
                        return True
            except Exception as read_err:
                logger.warning(f"Error reading local security master cache: {read_err}")

        # 2. Download from official NSE archives
        url = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept": "text/csv, text/plain, */*",
        }
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                if resp.status == 200:
                    csv_content = resp.read().decode("utf-8", errors="ignore")
                    if csv_content and "ISIN NUMBER" in csv_content:
                        with open(_MASTER_CACHE_FILE, "w", encoding="utf-8") as f:
                            f.write(csv_content)
                        _parse_csv_into_master(csv_content)
                        _MASTER_INITIALIZED = True
                        return True
        except Exception as net_err:
            logger.warning(f"Note on live NSE security master download: {net_err}")

        # 3. Fallback: Parse whatever local file exists (even if stale) or ICICI map
        if os.path.exists(_MASTER_CACHE_FILE) and not _ISIN_TO_SECURITY:
            try:
                with open(_MASTER_CACHE_FILE, "r", encoding="utf-8", errors="ignore") as f:
                    csv_content = f.read()
                _parse_csv_into_master(csv_content)
                _MASTER_INITIALIZED = True
                return True
            except Exception:
                pass

        # At minimum, populate the ICICI code dictionary
        _parse_csv_into_master("")
        _MASTER_INITIALIZED = True
        return True


def ensure_initialized():
    """Ensures security master is populated before any lookup."""
    if not _MASTER_INITIALIZED:
        init_security_master()


def resolve_isin_to_symbol(isin: str) -> Optional[str]:
    """
    Returns official canonical exchange symbol for a given ISIN in <0.0001ms.
    Example: 'INE155A01022' -> 'TATAMOTORS', 'INE002A01018' -> 'RELIANCE'
    """
    if not isin:
        return None
    ensure_initialized()
    clean_isin = str(isin).strip().upper()
    sec = _ISIN_TO_SECURITY.get(clean_isin)
    return sec["symbol"] if sec else None


def resolve_symbol_to_isin(symbol: str) -> Optional[str]:
    """
    Returns official ISIN for any stock symbol or ICICI proprietary code.
    Example: 'TATAMOTORS' -> 'INE155A01022', 'TELCO' -> 'INE155A01022', 'INFTEC' -> 'INE009A01021'
    """
    if not symbol:
        return None
    ensure_initialized()
    clean = str(symbol).strip().upper().replace(".NS", "").replace(".BO", "")
    return _SYMBOL_TO_ISIN.get(clean)


def resolve_security(identifier: str, exchange: Optional[str] = None) -> Dict[str, Any]:
    """
    Universal security identifier resolver.
    Accepts ISIN, canonical ticker, .NS/.BO ticker, ICICI proprietary broker code, or 6-digit BSE scrip.
    Returns authoritative metadata dictionary:
    {
        "isin": str or None,
        "symbol": str,           # Canonical trading symbol (e.g. 'TATAMOTORS')
        "full_symbol": str,      # Exchange-suffixed ticker (e.g. 'TATAMOTORS.NS' or '500570.BO')
        "company_name": str,     # Legal corporate name
        "exchange": "NSE" | "BSE"
    }
    """
    ensure_initialized()
    raw = str(identifier or "").strip().upper()
    if not raw:
        return {"isin": None, "symbol": "", "full_symbol": "", "company_name": "", "exchange": "NSE"}

    # 1. Direct ISIN check
    if is_valid_isin(raw):
        sec = _ISIN_TO_SECURITY.get(raw)
        if sec:
            sym = sec["symbol"]
            exch = sec.get("exchange", "NSE")
            suffix = ".BO" if exch == "BSE" else ".NS"
            return {
                "isin": raw,
                "symbol": sym,
                "full_symbol": f"{sym}{suffix}",
                "company_name": sec.get("company_name", sym),
                "exchange": exch
            }
        return {
            "isin": raw,
            "symbol": raw,
            "full_symbol": f"{raw}.NS",
            "company_name": raw,
            "exchange": "NSE"
        }

    # 2. Check ICICI Proprietary Code dictionary
    clean_code = raw.replace(".NS", "").replace(".BO", "").strip()
    if clean_code in ICICI_PROPRIETARY_CODE_MAP:
        meta = ICICI_PROPRIETARY_CODE_MAP[clean_code]
        isin_val = meta["isin"]
        sym_val = meta["symbol"]
        return {
            "isin": isin_val,
            "symbol": sym_val,
            "full_symbol": f"{sym_val}.NS",
            "company_name": meta["name"],
            "exchange": "NSE"
        }

    # 3. Check official symbol lookup in Security Master
    matched_isin = _SYMBOL_TO_ISIN.get(clean_code)
    if matched_isin:
        sec = _ISIN_TO_SECURITY.get(matched_isin, {})
        sym_val = sec.get("symbol", clean_code)
        exch_val = sec.get("exchange", "NSE")
        suffix = ".BO" if exch_val == "BSE" else ".NS"
        return {
            "isin": matched_isin,
            "symbol": sym_val,
            "full_symbol": f"{sym_val}{suffix}",
            "company_name": sec.get("company_name", sym_val),
            "exchange": exch_val
        }

    # 4. BSE Scrip Code or BSE scrip resolution
    is_explicit_bse = raw.endswith(".BO") or (exchange and str(exchange).upper() == "BSE") or (clean_code.isdigit() and len(clean_code) == 6)
    if is_explicit_bse:
        bse_sym = clean_code if (clean_code.isdigit() and len(clean_code) == 6) else f"{clean_code}.BO"
        return {
            "isin": None,
            "symbol": bse_sym,
            "full_symbol": f"{clean_code}.BO",
            "company_name": clean_code,
            "exchange": "BSE"
        }

    # 5. Default fallback for standard NSE equity
    return {
        "isin": None,
        "symbol": clean_code,
        "full_symbol": f"{clean_code}.NS",
        "company_name": clean_code,
        "exchange": "NSE"
    }
