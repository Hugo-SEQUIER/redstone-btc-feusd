"""
hip3_config.py

Central configuration for oracle updates.
Edit ONE place, both scripts read from here.
"""

from hyperliquid.utils import constants

# ---- Network ----
API_URL = constants.TESTNET_API_URL   # or constants.TESTNET_API_URL

EVM_ADDR = {
    "FEUSD": "0x88102bea0bbad5f301f6e9e4dacdf979",
}