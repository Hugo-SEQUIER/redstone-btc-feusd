// Deploy RedStone PriceFeedsAdapter Contract to HyperEVM Testnet
// Usage: node deploy-adapter.js

const hre = require("hardhat");
const { ethers } = require('ethers');
require('dotenv').config({ path: './redstone-push.env' });

async function deployAdapter() {
  try {
    console.log('🚀 Deploying RedStone PriceFeedsAdapter to HyperEVM Testnet...');
    
    // Setup provider and get signer
    const [deployer] = await hre.ethers.getSigners();
    
    console.log(`📝 Deploying from address: ${deployer.address}`);
    console.log(`🌐 Network: ${process.env.CHAIN_NAME} (Chain ID: ${process.env.CHAIN_ID})`);
    
    // Check balance
    const balance = await deployer.provider.getBalance(deployer.address);
    console.log(`💰 Balance: ${hre.ethers.formatEther(balance)} ETH`);
    
    if (balance === 0n) {
      throw new Error('❌ Insufficient balance. Please fund your wallet with HyperEVM testnet tokens.');
    }
    
    // Get contract factory
    const PriceFeedsAdapter = await hre.ethers.getContractFactory("PriceFeedsAdapter");
    
    // Deploy contract
    console.log('⏳ Deploying contract...');
    const adapter = await PriceFeedsAdapter.deploy(deployer.address, {
      gasLimit: parseInt(process.env.GAS_LIMIT || '500000')
    });
    
    console.log(`📋 Transaction hash: ${adapter.deploymentTransaction().hash}`);
    
    // Wait for deployment
    await adapter.waitForDeployment();
    const contractAddress = await adapter.getAddress();
    
    console.log('✅ Contract deployed successfully!');
    console.log(`📍 Contract address: ${contractAddress}`);
    console.log(`🔧 Admin address: ${deployer.address}`);
    
    // Set up the BTC-FEUSD data feed
    const btcFeusdDataFeedId = hre.ethers.keccak256(hre.ethers.toUtf8Bytes("BTC-FEUSD"));
    console.log('\n⚙️ Setting up BTC-FEUSD data feed...');
    
    const tx = await adapter.setDataFeedSymbol(btcFeusdDataFeedId, "BTC-FEUSD");
    await tx.wait();
    
    console.log(`✅ BTC-FEUSD data feed configured`);
    console.log(`📊 Data Feed ID: ${btcFeusdDataFeedId}`);
    
    // Update the environment file with the contract address
    console.log('\n📝 Please update your redstone-push.env file with:');
    console.log(`ADAPTER_CONTRACT_ADDRESS=${contractAddress}`);
    
    // Show verification command
    console.log('\n🔍 To verify the contract (optional):');
    console.log(`npx hardhat verify --network hyperevm ${contractAddress} "${deployer.address}"`);
    
    return contractAddress;
    
  } catch (error) {
    console.error('❌ Deployment failed:', error.message);
    if (error.reason) {
      console.error('Reason:', error.reason);
    }
    process.exit(1);
  }
}

if (require.main === module) {
  deployAdapter();
}

module.exports = { deployAdapter };
