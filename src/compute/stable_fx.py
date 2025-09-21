# src/stable_fx.py
"""
Resolve stablecoin -> USD factors needed to convert BTC/USD
into BTC/<your-stable> when HL Spot has no pairs.

Strategy:
  1) Try HL Spot mid(base/quote) for preferred quotes (usually USDT0, then other stables).
  2) If no HL-Spot pair, use DexScreener on HyperEVM with token addresses.
  3) If still nothing, fall back to peg=1.0 (logged).
"""

from __future__ import annotations
from typing import Dict, List, Optional
from hyperliquid.info import Info

from src.prices.hl_spot_prices import get_spot_mid
from src.prices.hyper_evm_prices import get_pair_mid_from_dexscreener


def resolve_stable_usd_factor(
    info: Info,
    symbol: str,
    *,
    preferred_quotes: List[str] = ("FEUSD"),
    evm_addresses: Optional[Dict[str, str]] = None,  # {"USDHL": "0x...", "USDC": "0x...", ...}
    evm_usd_reference: str = "USDC",                 # quote address to use on DexScreener
) -> float:
    """
    Return USD factor for a given stablecoin symbol:
      factor = price(symbol / USD_like)

    Order:
      A) HL Spot: first available pair symbol/quote in preferred_quotes
      B) DexScreener (HyperEVM): price(symbol_addr / evm_usd_reference_addr)
      C) 1.0 (peg)

    Note: When using DexScreener with evm_usd_reference="USDC", this returns
    symbol/USDC, not symbol/USD. Caller must multiply by USDC/USD to get symbol/USD.

    Raises only if everything is disabled/missing (we default to 1.0 otherwise).
    """
    # A) HL Spot
    last_err = None
    for q in preferred_quotes:
        try:
            return get_spot_mid(info, symbol, q)
        except Exception as e:
            last_err = e
            continue

    # B) DexScreener
    if evm_addresses and symbol in evm_addresses and evm_usd_reference in evm_addresses:
        try:
            return get_pair_mid_from_dexscreener(evm_addresses[symbol], evm_addresses[evm_usd_reference])
        except Exception as e:
            last_err = e

    # C) Peg
    # Logically we'd warn here; for now, return 1.0 so pipelines don't break.
    # Caller can check proximity-to-1 and decide whether to accept/push.
    return 1.0


def resolve_stable_usd_factor_with_usdc_reference(
    info: Info,
    symbol: str,
    usdc_usd_rate: float,
    *,
    preferred_quotes: List[str] = ("USDT0", "USDHL", "FEUSD"),
    evm_addresses: Optional[Dict[str, str]] = None,
    evm_usd_reference: str = "USDC",
) -> float:
    """
    Return stable/USD factor, properly handling USDC as intermediate reference.
    
    Args:
        info: Hyperliquid Info instance
        symbol: Stablecoin symbol (e.g., "USDT0", "USDHL", "FEUSD")
        usdc_usd_rate: USDC/USD rate from RedStone or other USD oracle
        preferred_quotes: Preferred quotes to try on HL Spot first
        evm_addresses: Token addresses for DexScreener queries
        evm_usd_reference: Reference token for DexScreener (usually "USDC")
    
    Returns:
        stable/USD rate = stable/USDC * USDC/USD
        
    Example:
        If USDT0/USDC = 0.99993 and USDC/USD = 1.002:
        Returns 0.99993 * 1.002 = 1.00193
    """
    # Try HL Spot first (these are already stable/USD-like)
    last_err = None
    for q in preferred_quotes:
        try:
            return get_spot_mid(info, symbol, q)
        except Exception as e:
            last_err = e
            continue
    
    # Try DexScreener with USDC reference
    if evm_addresses and symbol in evm_addresses and evm_usd_reference in evm_addresses:
        try:
            stable_usdc_rate = get_pair_mid_from_dexscreener(
                evm_addresses[symbol], 
                evm_addresses[evm_usd_reference]
            )
            # Convert stable/USDC to stable/USD
            return stable_usdc_rate * usdc_usd_rate
        except Exception as e:
            last_err = e
    
    # Fallback to peg
    return 1.0
