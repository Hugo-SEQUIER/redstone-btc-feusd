#!/usr/bin/env python3
"""
Read BTC-FEUSD price from the deployed contract on HyperEVM testnet
"""

import time
from datetime import datetime
from web3 import Web3
from eth_utils import keccak

# Contract configuration
CONTRACT_ADDRESS = "0x492f4913E411691807c53b178c1E36F4144E9889"
RPC_URL = "https://evmrpc-jp.hyperpc.app/adae36120cb94b9984f348314cdca711"
CHAIN_ID = 998

# Contract ABI for the functions we need
CONTRACT_ABI = [
    {
        "inputs": [{"internalType": "bytes32", "name": "dataFeedId", "type": "bytes32"}],
        "name": "getValueForDataFeed",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "bytes32", "name": "dataFeedId", "type": "bytes32"}],
        "name": "getTimestampForDataFeed",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "admin",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    }
]

def get_data_feed_id(symbol: str) -> bytes:
    """Generate data feed ID for a symbol (keccak256 hash)"""
    return keccak(text=symbol)

def read_contract_price(symbol: str = "BTC-FEUSD") -> dict:
    """
    Read price data from the HyperEVM testnet contract
    
    Returns:
        dict: {
            'symbol': str,
            'price': float,
            'raw_price': int,
            'timestamp': int,
            'last_update': datetime,
            'age_seconds': int,
            'age_minutes': int,
            'contract': str,
            'network': str
        }
    """
    try:
        # Connect to HyperEVM testnet
        print(f"🔗 Connecting to HyperEVM testnet...")
        w3 = Web3(Web3.HTTPProvider(RPC_URL))
        
        if not w3.is_connected():
            raise Exception("Failed to connect to HyperEVM testnet")
        
        print(f"✅ Connected to chain ID: {w3.eth.chain_id}")
        
        # Load contract
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(CONTRACT_ADDRESS),
            abi=CONTRACT_ABI
        )
        
        # Generate data feed ID
        data_feed_id = get_data_feed_id(symbol)
        print(f"📋 Data Feed ID for {symbol}: {data_feed_id.hex()}")
        
        # Read price and timestamp
        print(f"📊 Reading price data...")
        raw_price = contract.functions.getValueForDataFeed(data_feed_id).call()
        timestamp = contract.functions.getTimestampForDataFeed(data_feed_id).call()
        
        # Convert raw price (scaled by 10^8) to decimal
        price_decimal = raw_price / 1e8
        
        # Calculate age
        last_update = datetime.fromtimestamp(timestamp)
        current_time = datetime.now()
        age_seconds = int((current_time - last_update).total_seconds())
        age_minutes = age_seconds // 60
        
        result = {
            'symbol': symbol,
            'price': price_decimal,
            'raw_price': raw_price,
            'timestamp': timestamp,
            'last_update': last_update,
            'age_seconds': age_seconds,
            'age_minutes': age_minutes,
            'contract': CONTRACT_ADDRESS,
            'network': f'HyperEVM Testnet (Chain ID: {CHAIN_ID})',
            'data_feed_id': data_feed_id.hex()
        }
        
        return result
        
    except Exception as e:
        print(f"❌ Error reading contract: {e}")
        raise

def check_contract_admin() -> str:
    """Check who is the admin of the contract"""
    try:
        w3 = Web3(Web3.HTTPProvider(RPC_URL))
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(CONTRACT_ADDRESS),
            abi=CONTRACT_ABI
        )
        admin = contract.functions.admin().call()
        return admin
    except Exception as e:
        print(f"❌ Error reading admin: {e}")
        return None

def format_price_output(data: dict):
    """Pretty print the price data"""
    print("\n" + "="*60)
    print(f"🎯 {data['symbol']} PRICE DATA")
    print("="*60)
    print(f"💰 Price: {data['price']:,.6f} FEUSD per BTC")
    print(f"🔢 Raw Price: {data['raw_price']:,} (scaled by 10^8)")
    print(f"⏰ Last Updated: {data['last_update'].strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📅 Age: {data['age_minutes']} minutes ({data['age_seconds']} seconds)")
    print(f"⛓️ Network: {data['network']}")
    print(f"📍 Contract: {data['contract']}")
    print(f"🆔 Data Feed ID: {data['data_feed_id']}")
    
    # Status indicators
    if data['age_minutes'] < 10:
        print("🟢 Status: Fresh (< 10 minutes)")
    elif data['age_minutes'] < 30:
        print("🟡 Status: Recent (< 30 minutes)")
    else:
        print("🔴 Status: Stale (> 30 minutes)")
    
    print("="*60)

def main():
    """Main function"""
    print("🔍 Reading BTC-FEUSD price from HyperEVM testnet contract...")
    
    try:
        # Check contract admin
        admin = check_contract_admin()
        if admin:
            print(f"👤 Contract Admin: {admin}")
        
        # Read price data
        price_data = read_contract_price("BTC-FEUSD")
        
        # Display results
        format_price_output(price_data)
        
        # Return data for programmatic use
        return price_data
        
    except Exception as e:
        print(f"❌ Failed to read price: {e}")
        return None

if __name__ == "__main__":
    result = main()
    
    # Example of using the data programmatically
    if result:
        print(f"\n💡 You can use this price in your code:")
        print(f"   BTC-FEUSD price: {result['price']}")
        print(f"   Last update: {result['age_minutes']} minutes ago")
