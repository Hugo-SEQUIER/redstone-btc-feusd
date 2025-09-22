# app.py
from fastapi import FastAPI
from src.compute.stable_fx import resolve_stable_usd_factor
from src.prices.redstone_prices import fetch_redstone_prices
from hyperliquid.info import Info
from src.hip3.hip3_config import API_URL, EVM_ADDR
import time

app = FastAPI()

@app.get("/health")
def health():
    """Health check endpoint for Docker"""
    return {"status": "healthy", "timestamp": time.time()}

@app.get("/price/btc-feusd")
def btc_feusd():
    rs = fetch_redstone_prices(["BTC", "USDT0", "USDC"])
    btc_usd = float(rs["BTC"]["value"])
    fx = resolve_stable_usd_factor(Info(API_URL, skip_ws=True), "FEUSD", evm_addresses=EVM_ADDR, evm_usd_reference="USDC")
    value = btc_usd / fx
    return {"id": "BTC-FEUSD", "value": value, "timestamp": time.time()}
