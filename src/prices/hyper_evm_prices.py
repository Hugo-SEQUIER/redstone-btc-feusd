# src/hyper_evm_prices.py
"""
Fetch mid-prices on HyperEVM via DexScreener.

get_pair_mid_from_dexscreener(tokenA_addr, tokenB_addr) returns
price(tokenA/tokenB) = how many B per 1 A, using the best available pool.
"""

from __future__ import annotations
from typing import Dict, Any, List
import requests


DEXSCREENER_BASE = "https://api.dexscreener.com/latest/dex/tokens"


def _load_pairs_for_token(token_addr: str, timeout: float = 5.0) -> List[Dict[str, Any]]:
    url = f"{DEXSCREENER_BASE}/{token_addr}"
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    return data.get("pairs", []) or []


def get_pair_mid_from_dexscreener(tokenA: str, tokenB: str, timeout: float = 5.0) -> float:
    """
    Returns mid price for tokenA/tokenB on HyperEVM using DexScreener.

    - tokenA, tokenB: checksummed addresses (strings)
    - We prefer pools that explicitly quote price for the right orientation.
    - Otherwise we pick the highest-liquidity pool and use its 'price' field.

    Raises RuntimeError if no suitable pool is found.
    """
    pairs = _load_pairs_for_token(tokenA, timeout=timeout)
    tB = tokenB.lower()

    best_liq = -1.0
    best_price = None

    for p in pairs:
        base = (p.get("baseToken") or {}).get("address", "").lower()
        quote = (p.get("quoteToken") or {}).get("address", "").lower()
        if not base or not quote:
            continue

        price_str = p.get("priceNative") or p.get("price")  # both are common
        try:
            liq_usd = float((p.get("liquidity") or {}).get("usd", 0.0))
        except Exception:
            liq_usd = 0.0

        # Exact orientation
        if base == tokenA.lower() and quote == tB and price_str:
            try:
                return float(price_str)
            except Exception:
                pass

        # Inverted orientation
        if base == tB and quote == tokenA.lower() and price_str:
            try:
                v = float(price_str)
                if v != 0.0:
                    return 1.0 / v
            except Exception:
                pass

        # Keep best-liquidity fallback
        if liq_usd > best_liq and price_str:
            best_liq = liq_usd
            best_price = price_str

    if best_price is not None:
        try:
            return float(best_price)
        except Exception:
            pass

    raise RuntimeError(f"No suitable DexScreener pool for {tokenA} vs {tokenB}")
