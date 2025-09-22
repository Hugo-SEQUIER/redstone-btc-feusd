// RedStone Push Relayer for HyperEVM Testnet
// This script periodically pushes price data to the deployed adapter contract

const { ethers } = require('ethers');
const axios = require('axios');
require('dotenv').config({ path: './redstone-push.env' });

class RedStonePushRelayer {
  constructor() {
    this.provider = new ethers.JsonRpcProvider(process.env.RPC_URL);
    this.wallet = new ethers.Wallet(process.env.PRIVATE_KEY, this.provider);
    this.contractAddress = process.env.ADAPTER_CONTRACT_ADDRESS;
    this.dataFeeds = JSON.parse(process.env.DATA_FEEDS || '["BTC-FEUSD"]');
    this.updateInterval = parseInt(process.env.UPDATE_PRICE_INTERVAL || '300000');
    this.checkInterval = parseInt(process.env.RELAYER_ITERATION_INTERVAL || '30000');
    this.minDeviation = parseFloat(process.env.MIN_DEVIATION_PERCENTAGE || '0.5');
    this.updateConditions = JSON.parse(process.env.UPDATE_CONDITIONS || '["time","value-deviation"]');
    
    // Contract ABI for the adapter
    this.contractABI = [
      {
        "inputs": [
          {"internalType": "bytes32[]", "name": "dataFeedIds", "type": "bytes32[]"},
          {"internalType": "uint256[]", "name": "values", "type": "uint256[]"}
        ],
        "name": "updateDataFeeds",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
      },
      {
        "inputs": [{"internalType": "bytes32", "name": "dataFeedId", "type": "bytes32"}],
        "name": "getValueForDataFeed",
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
    ];
    
    this.contract = new ethers.Contract(this.contractAddress, this.contractABI, this.wallet);
    this.lastUpdateTime = {};
    this.lastValues = {};
    
    console.log('🔧 RedStone Push Relayer initialized');
    console.log(`📍 Contract: ${this.contractAddress}`);
    console.log(`⏰ Update interval: ${this.updateInterval}ms`);
    console.log(`📊 Min deviation: ${this.minDeviation}%`);
    console.log(`🎯 Data feeds: ${this.dataFeeds.join(', ')}`);
  }

  // Convert symbol to bytes32 data feed ID
  symbolToDataFeedId(symbol) {
    return ethers.keccak256(ethers.toUtf8Bytes(symbol));
  }

  // Fetch price from your price service
  async fetchPrice(symbol) {
    try {
      const response = await axios.get(`http://python-price-service:8060/price/btc-feusd`, {
        timeout: 30000
      });
      
      if (response.data && response.data.value) {
        // Convert to fixed point (multiply by 10^8 for 8 decimal places)
        const scaledValue = Math.round(response.data.value * 1e8);
        return {
          symbol,
          value: scaledValue,
          timestamp: response.data.timestamp || Date.now() / 1000
        };
      }
      
      throw new Error('Invalid price data format');
    } catch (error) {
      console.error(`❌ Failed to fetch price for ${symbol}:`, error.message);
      return null;
    }
  }

  // Check if update is needed based on conditions
  shouldUpdate(symbol, newPrice) {
    const now = Date.now();
    const lastUpdate = this.lastUpdateTime[symbol] || 0;
    const lastValue = this.lastValues[symbol] || 0;
    
    // Check time condition
    if (this.updateConditions.includes('time')) {
      if (now - lastUpdate >= this.updateInterval) {
        console.log(`⏰ Time-based update triggered for ${symbol}`);
        return true;
      }
    }
    
    // Check value deviation condition
    if (this.updateConditions.includes('value-deviation') && lastValue > 0) {
      const deviation = Math.abs((newPrice - lastValue) / lastValue) * 100;
      if (deviation >= this.minDeviation) {
        console.log(`📈 Deviation-based update triggered for ${symbol}: ${deviation.toFixed(2)}%`);
        return true;
      }
    }
    
    return false;
  }

  // Update prices on-chain
  async updatePrices(priceData) {
    try {
      const dataFeedIds = [];
      const values = [];
      
      for (const data of priceData) {
        dataFeedIds.push(this.symbolToDataFeedId(data.symbol));
        values.push(BigInt(data.value));
      }
      
      console.log(`🚀 Updating prices on-chain...`);
      console.log(`📊 Data:`, priceData.map(d => `${d.symbol}: ${d.value / 1e8}`));
      
      const tx = await this.contract.updateDataFeeds(dataFeedIds, values, {
        gasLimit: parseInt(process.env.GAS_LIMIT || '500000')
      });
      
      console.log(`📋 Transaction submitted: ${tx.hash}`);
      const receipt = await tx.wait();
      console.log(`✅ Transaction confirmed in block: ${receipt.blockNumber}`);
      
      // Update tracking
      for (const data of priceData) {
        this.lastUpdateTime[data.symbol] = Date.now();
        this.lastValues[data.symbol] = data.value;
      }
      
      return true;
    } catch (error) {
      console.error(`❌ Failed to update prices:`, error.message);
      return false;
    }
  }

  // Main relayer loop
  async run() {
    console.log('🔄 Starting relayer loop...');
    
    while (true) {
      try {
        const pricesToUpdate = [];
        
        // Fetch prices for all data feeds
        for (const symbol of this.dataFeeds) {
          const priceData = await this.fetchPrice(symbol);
          
          if (priceData && this.shouldUpdate(symbol, priceData.value)) {
            pricesToUpdate.push(priceData);
          }
        }
        
        // Update prices if needed
        if (pricesToUpdate.length > 0) {
          await this.updatePrices(pricesToUpdate);
        } else {
          console.log('💤 No updates needed');
        }
        
      } catch (error) {
        console.error('❌ Relayer loop error:', error.message);
      }
      
      // Wait before next iteration
      await new Promise(resolve => setTimeout(resolve, this.checkInterval));
    }
  }

  // Graceful shutdown
  async shutdown() {
    console.log('🛑 Shutting down relayer...');
    process.exit(0);
  }
}

// Handle shutdown signals
process.on('SIGINT', async () => {
  console.log('\n⚡ Received SIGINT');
  process.exit(0);
});

process.on('SIGTERM', async () => {
  console.log('\n⚡ Received SIGTERM');
  process.exit(0);
});

// Start the relayer
async function main() {
  try {
    const relayer = new RedStonePushRelayer();
    await relayer.run();
  } catch (error) {
    console.error('❌ Failed to start relayer:', error.message);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = { RedStonePushRelayer };
