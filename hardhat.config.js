require("@nomicfoundation/hardhat-ethers");
require('dotenv').config({ path: './redstone-push.env' });

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  solidity: {
    version: "0.8.20",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200
      }
    }
  },
  networks: {
    hyperevm: {
      url: process.env.RPC_URL,
      accounts: [process.env.PRIVATE_KEY],
      chainId: parseInt(process.env.CHAIN_ID),
      gasPrice: 1000000000, // 1 gwei
      gas: parseInt(process.env.GAS_LIMIT || "2000000")
    }
  }
};
