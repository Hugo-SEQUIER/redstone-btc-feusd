import json
import time
import uuid
from typing import Dict, Any, List, Tuple, Optional
import requests

REDSTONE_PRICE_ENDPOINTS: List[str] = [
    "https://api.redstone.finance/prices",                 # facade
    "https://oracle-gateway-1.a.redstone.finance/prices",  # gateway #1
    "https://oracle-gateway-2.a.redstone.finance/prices",  # gateway #2
    # You can add more mirrors here if needed
]

def _http_get_json(url: str, params: Dict[str, str], timeout: float) -> Tuple[int, Any, Dict[str, str]]:
    """HTTP GET with headers; returns (status_code, parsed_json_or_text, resp_headers)."""
    headers = {
        "Accept": "application/json,text/plain,*/*",
        "User-Agent": "hl-hip3-deploy/1.0 (+redstone-test)",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
    resp = requests.get(url, params=params, headers=headers, timeout=timeout)
    try:
        return resp.status_code, resp.json(), dict(resp.headers or {})
    except Exception:
        return resp.status_code, resp.text, dict(resp.headers or {})

def _normalize_rs_payload(data: Any) -> List[Dict[str, Any]]:
    """
    Accept list | dict | stringified JSON and normalize to a list of price objects:
      [{"symbol": "BTC", "value": 65000.0, "timestamp": 1726..., "provider": "..."}]
    """
    # If the gateway returned text, try to parse it as JSON
    if isinstance(data, str):
        txt = data.strip()
        if (txt.startswith("{") and txt.endswith("}")) or (txt.startswith("[") and txt.endswith("]")):
            try:
                data = json.loads(txt)
            except Exception:
                pass  # keep as str

    # Case 1: already the expected list
    if isinstance(data, list):
        return data

    # Case 2: some gateways return a dict keyed by symbol
    # Example: {"BTC": {"value": 65000, "timestamp": ..., "provider": "redstone"}, ...}
    if isinstance(data, dict):
        out = []
        for sym, obj in data.items():
            if isinstance(obj, dict) and "value" in obj:
                out.append({
                    "symbol": sym,
                    "value": obj.get("value"),
                    "timestamp": obj.get("timestamp"),
                    "provider": obj.get("provider", "redstone"),
                })
        if out:
            return out

    # Anything else -> not usable
    raise RuntimeError(f"Unexpected RedStone payload type: {type(data)}")

def _try_redstone_endpoint(endpoint: str, symbols: List[str], timeout: float) -> Dict[str, Dict[str, Any]]:
    """
    Try a single RedStone endpoint with multiple query shapes:
      1) symbols=BTC,ETH (batch)
      2) symbol=BTC      (per-symbol fallback)
    Returns {SYMBOL: {value, timestamp, provider}}.
    """
    wanted = [s.strip().upper() for s in symbols if s.strip()]
    if not wanted:
        return {}

    # 1) Batch query: symbols=BTC,ETH
    # Add a tiny cache-buster param in case of stale edges
    params = {"symbols": ",".join(wanted), "_": uuid.uuid4().hex}
    status, data, _ = _http_get_json(endpoint, params, timeout)
    if status == 200:
        try:
            normalized = _normalize_rs_payload(data)
            out: Dict[str, Dict[str, Any]] = {}
            for item in normalized:
                try:
                    sym = str(item["symbol"]).upper()
                    val = float(item["value"])
                    ts = item.get("timestamp")
                    provider = str(item.get("provider", "redstone"))
                    out[sym] = {"value": val, "timestamp": ts, "provider": provider}
                except Exception:
                    continue
            if out:
                return out
        except Exception:
            # fall through to per-symbol tries
            pass

    # 2) Per-symbol fallback: some gateways only accept 'symbol'
    out: Dict[str, Dict[str, Any]] = {}
    for sym in wanted:
        params = {"symbol": sym, "_": uuid.uuid4().hex}
        status, data, _ = _http_get_json(endpoint, params, timeout)
        if status != 200:
            continue
        try:
            normalized = _normalize_rs_payload(data)
        except Exception:
            continue
        # pick the first matching entry for that symbol
        for item in normalized:
            try:
                if str(item.get("symbol", "")).upper() != sym:
                    continue
                val = float(item["value"])
                ts = item.get("timestamp")
                provider = str(item.get("provider", "redstone"))
                out[sym] = {"value": val, "timestamp": ts, "provider": provider}
                break
            except Exception:
                continue

    if out:
        return out

    raise RuntimeError(f"No usable data from {endpoint}")

def fetch_redstone_prices(
    symbols: List[str],
    *,
    endpoints: Optional[List[str]] = None,
    timeout_secs: float = 4.0,
    retries: int = 4,
    retry_base_delay: float = 0.5,
) -> Dict[str, Dict[str, Any]]:
    """
    Fetch latest RedStone prices with endpoint + query-shape fallbacks and exponential backoff.
    Returns {SYMBOL: {value, timestamp, provider}}.
    """
    eps = endpoints or REDSTONE_PRICE_ENDPOINTS
    attempt = 0
    last_err: Optional[Exception] = None

    while attempt < retries:
        for ep in eps:
            try:
                result = _try_redstone_endpoint(ep, symbols, timeout_secs)
                if result:
                    return result
                last_err = RuntimeError(f"No data from {ep}")
            except Exception as e:
                last_err = e
        attempt += 1
        time.sleep(retry_base_delay * (2 ** (attempt - 1)))

    raise RuntimeError(f"Failed to fetch RedStone prices after {retries} attempts: {last_err}")
