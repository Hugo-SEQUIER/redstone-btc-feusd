"""
hl_spot_prices.py

Helpers to fetch Hyperliquid spot mid-prices for BASE/QUOTE by:
  1) reading spotMeta (tokens + universe)
  2) locating the pair index for (BASE, QUOTE)
  3) fetching L2 order book for assetId = 10000 + pairIndex
  4) computing mid = (bestBid + bestAsk) / 2

Docs:
- spotMeta (tokens & pairs): POST /info { "type": "spotMeta" }
- Spot asset id: assetId = 10000 + spotPairIndex
- L2 book: POST /info { "type": "l2Book", "asset": <assetId> }
"""

from __future__ import annotations
from typing import Dict, Tuple

from hyperliquid.info import Info

SPOT_ASSET_OFFSET = 10000


def _build_name_to_token_index(spot_meta: Dict) -> Dict[str, int]:
    """Map token name (case-sensitive from HL) -> token index."""
    out: Dict[str, int] = {}
    for t in spot_meta.get("tokens", []):
        name = t.get("name")
        idx = t.get("index")
        if name is not None and idx is not None:
            out[name] = idx
    return out


# add this tiny helper if you want to quickly inspect the catalog
def debug_spot_catalog(info: Info, limit: int = 10) -> None:
    sm = info.spot_meta()
    print("TOKENS:", [t.get("name") for t in sm.get("tokens", []) if t.get("name") in ["feUSD", "USDHL", "USDT0", "FEUSD"]][:limit])
    print("UNIVERSE size:", len(sm.get("universe", [])))

def get_spot_mid_any(info: Info, base: str, preferred_quotes: list[str]) -> float:
    """
    Try to get mid(base/quote) using the first available quote in preferred_quotes.
    Example: get_spot_mid_any(info, "FEUSD", ["USDT0", "USDHL"])
    """
    last_err = None
    for quote in preferred_quotes:
        try:
            return get_spot_mid(info, base, quote)
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"No available spot mid for {base} against {preferred_quotes}: {last_err}")


def list_spot_pairs_for_token(info: Info, token_name: str) -> list[tuple[str, str, int]]:
    """
    Return all spot pairs in HL Spot universe where token_name is base or quote.
    Each entry = (base_name, quote_name, pair_index).
    """
    sm = info.spot_meta()
    name_to_idx = {t["name"]: t["index"] for t in sm.get("tokens", [])}
    idx_to_name = {v: k for k, v in name_to_idx.items()}
    if token_name not in name_to_idx:
        raise RuntimeError(f"Token not in spot_meta tokens: {token_name}")

    out = []
    for u in sm.get("universe", []):
        b = u.get("baseTokenIndex")
        q = u.get("quoteTokenIndex")
        if b is None or q is None:
            continue
        bname = idx_to_name.get(b)
        qname = idx_to_name.get(q)
        if bname is None or qname is None:
            continue
        if bname == token_name or qname == token_name:
            out.append((bname, qname, int(u.get("index"))))
    return out


def find_spot_pair_index(info: Info, base: str, quote: str) -> int:
    """
    Return the universe index (pair index) for BASE/QUOTE, or raise if not found.
    """
    sm = info.spot_meta()  # {"tokens":[...], "universe":[...]}
    name_to_idx = _build_name_to_token_index(sm)
    if base not in name_to_idx or quote not in name_to_idx:
        raise RuntimeError(f"Token not in spot_meta: base={base} quote={quote}")

    base_idx = name_to_idx[base]
    quote_idx = name_to_idx[quote]

    # Each item in universe refers to a pair; typical fields include {"baseTokenIndex":..., "quoteTokenIndex":..., "index":...}
    for u in sm.get("universe", []):
        if (
            u.get("baseTokenIndex") == base_idx
            and u.get("quoteTokenIndex") == quote_idx
        ):
            pair_index = u.get("index")
            if pair_index is None:
                break
            return int(pair_index)

    raise RuntimeError(f"Spot pair not found: {base}/{quote}")


def get_spot_mid(info: Info, base: str, quote: str) -> float:
    """
    Compute mid price for BASE/QUOTE using L2 best bid/ask.
    """
    pair_index = find_spot_pair_index(info, base, quote)
    asset_id = SPOT_ASSET_OFFSET + int(pair_index)

    # Raw POST via Info wrapper:
    ob = info.post("/info", {"type": "l2Book", "asset": asset_id})
    # Expected shape: {"levels":[{"px":"...", "sz":"..."}, ...], "levels_ask":[...]} or "bids"/"asks" depending on SDK
    bids = ob.get("levels") or ob.get("bids") or []
    asks = ob.get("levels_ask") or ob.get("asks") or []

    if not bids or not asks:
        raise RuntimeError(f"No liquidity on book for {base}/{quote}")

    # Best = first level
    best_bid = float(bids[0]["px"])
    best_ask = float(asks[0]["px"])
    return (best_bid + best_ask) / 2.0


def get_fx(base: str, quote: str, info: Info) -> float:
    """
    Return FX rate: 1 BASE in QUOTE (i.e., price(BASE/QUOTE)).
    """
    return get_spot_mid(info, base, quote)


def get_stable_usd_factors(info: Info) -> Dict[str, float]:
    """
    Convenience: return approximate USD conversion for local stables by reading
    their price vs USDT0 if that pair exists, else vs USDC, else raise.
    Example output: {"feUSD": 0.9998, "USDHL": 1.0001, "USDT0": 1.0000}
    """
    results: Dict[str, float] = {}
    candidates = [("feUSD", "USDT0"), ("feUSD", "USDC"),
                  ("USDHL", "USDT0"), ("USDHL", "USDC"),
                  ("USDT0", "USDC")]

    tried = set()
    for base, quote in candidates:
        key = (base, quote)
        if key in tried:
            continue
        tried.add(key)
        try:
            px = get_spot_mid(info, base, quote)
            # Interpret QUOTE≈USD if quote in (USDT0, USDC)
            if base not in results:
                results[base] = px
        except Exception:
            continue

    if "USDT0" not in results:
        # If USDT0/USDC is available, set USDT0≈1 via that mid
        try:
            results["USDT0"] = get_spot_mid(info, "USDT0", "USDC")
        except Exception:
            pass

    if not results:
        raise RuntimeError("Could not derive any stable/USD factors from HL spot.")

    return results
