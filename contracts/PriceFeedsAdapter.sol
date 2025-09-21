// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title Simple PriceFeedsAdapter
 * @dev A minimal adapter contract for storing and retrieving price feeds
 */
contract PriceFeedsAdapter {
    address public admin;
    
    mapping(bytes32 => uint256) public priceFeeds;
    mapping(bytes32 => uint256) public timestamps;
    
    event PriceFeedUpdated(bytes32 indexed dataFeedId, uint256 value, uint256 timestamp);
    
    modifier onlyAdmin() {
        require(msg.sender == admin, "Only admin");
        _;
    }
    
    constructor(address _admin) {
        admin = _admin;
    }
    
    /**
     * @dev Update multiple price feeds at once
     */
    function updateDataFeeds(bytes32[] calldata dataFeedIds, uint256[] calldata values) external onlyAdmin {
        require(dataFeedIds.length == values.length, "Length mismatch");
        
        for (uint256 i = 0; i < dataFeedIds.length; i++) {
            priceFeeds[dataFeedIds[i]] = values[i];
            timestamps[dataFeedIds[i]] = block.timestamp;
            emit PriceFeedUpdated(dataFeedIds[i], values[i], block.timestamp);
        }
    }
    
    /**
     * @dev Get the latest value for a data feed
     */
    function getValueForDataFeed(bytes32 dataFeedId) external view returns (uint256) {
        return priceFeeds[dataFeedId];
    }
    
    /**
     * @dev Get timestamp for a data feed
     */
    function getTimestampForDataFeed(bytes32 dataFeedId) external view returns (uint256) {
        return timestamps[dataFeedId];
    }
}
