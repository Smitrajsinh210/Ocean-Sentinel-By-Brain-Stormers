// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title Ocean Sentinel Data Contract
 * @dev Smart contract for storing and verifying environmental data integrity
 * @notice This contract ensures immutable logging of environmental sensor readings
 */
contract OceanSentinelData {
    // Events
    event DataLogged(
        bytes32 indexed dataHash,
        address indexed logger,
        uint256 timestamp,
        string dataSource,
        string dataType
    );
    
    event DataVerified(
        bytes32 indexed dataHash,
        address indexed verifier,
        uint256 timestamp,
        bool isValid
    );
    
    // Structs
    struct EnvironmentalData {
        bytes32 dataHash;
        address logger;
        uint256 timestamp;
        string dataSource;
        string dataType;
        bool isVerified;
        address verifier;
        uint256 verificationTimestamp;
    }
    
    // State variables
    address public owner;
    uint256 public totalRecords;
    
    // Mappings
    mapping(bytes32 => EnvironmentalData) public environmentalRecords;
    mapping(address => bool) public authorizedLoggers;
    mapping(address => bool) public authorizedVerifiers;
    mapping(string => uint256) public sourceRecordCount;
    
    // Arrays for iteration
    bytes32[] public allDataHashes;
    
    // Modifiers
    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this function");
        _;
    }
    
    modifier onlyAuthorizedLogger() {
        require(authorizedLoggers[msg.sender] || msg.sender == owner, 
                "Not authorized to log data");
        _;
    }
    
    modifier onlyAuthorizedVerifier() {
        require(authorizedVerifiers[msg.sender] || msg.sender == owner, 
                "Not authorized to verify data");
        _;
    }
    
    modifier dataExists(bytes32 _dataHash) {
        require(environmentalRecords[_dataHash].timestamp != 0, 
                "Data record does not exist");
        _;
    }
    
    // Constructor
    constructor() {
        owner = msg.sender;
        authorizedLoggers[msg.sender] = true;
        authorizedVerifiers[msg.sender] = true;
        totalRecords = 0;
    }
    
    /**
     * @dev Log environmental data hash to blockchain
     * @param _dataHash Hash of the environmental data
     * @param _dataSource Source of the data (e.g., "weather_api", "sensor_network")
     * @param _dataType Type of data (e.g., "temperature", "air_quality")
     */
    function logEnvironmentalData(
        bytes32 _dataHash,
        string memory _dataSource,
        string memory _dataType
    ) external onlyAuthorizedLogger {
        require(_dataHash != bytes32(0), "Data hash cannot be empty");
        require(bytes(_dataSource).length > 0, "Data source cannot be empty");
        require(bytes(_dataType).length > 0, "Data type cannot be empty");
        require(environmentalRecords[_dataHash].timestamp == 0, 
                "Data already exists");
        
        // Create new environmental data record
        environmentalRecords[_dataHash] = EnvironmentalData({
            dataHash: _dataHash,
            logger: msg.sender,
            timestamp: block.timestamp,
            dataSource: _dataSource,
            dataType: _dataType,
            isVerified: false,
            verifier: address(0),
            verificationTimestamp: 0
        });
        
        // Add to arrays for iteration
        allDataHashes.push(_dataHash);
        
        // Update counters
        totalRecords++;
        sourceRecordCount[_dataSource]++;
        
        // Emit event
        emit DataLogged(_dataHash, msg.sender, block.timestamp, _dataSource, _dataType);
    }
    
    /**
     * @dev Verify the integrity of logged environmental data
     * @param _dataHash Hash of the data to verify
     * @param _isValid Whether the data is valid
     */
    function verifyDataIntegrity(
        bytes32 _dataHash,
        bool _isValid
    ) external onlyAuthorizedVerifier dataExists(_dataHash) {
        require(!environmentalRecords[_dataHash].isVerified, 
                "Data already verified");
        
        environmentalRecords[_dataHash].isVerified = true;
        environmentalRecords[_dataHash].verifier = msg.sender;
        environmentalRecords[_dataHash].verificationTimestamp = block.timestamp;
        
        emit DataVerified(_dataHash, msg.sender, block.timestamp, _isValid);
    }
    
    /**
     * @dev Get environmental data record by hash
     * @param _dataHash Hash of the data record
     * @return Environmental data record
     */
    function getEnvironmentalData(bytes32 _dataHash) 
        external 
        view 
        dataExists(_dataHash) 
        returns (EnvironmentalData memory) 
    {
        return environmentalRecords[_dataHash];
    }
    
    /**
     * @dev Check if data hash exists and is verified
     * @param _dataHash Hash to check
     * @return exists Whether the data exists
     * @return verified Whether the data is verified
     */
    function checkDataStatus(bytes32 _dataHash) 
        external 
        view 
        returns (bool exists, bool verified) 
    {
        exists = environmentalRecords[_dataHash].timestamp != 0;
        verified = environmentalRecords[_dataHash].isVerified;
        return (exists, verified);
    }
    
    /**
     * @dev Get data records by source with pagination
     * @param _dataSource Data source to filter by
     * @param _offset Starting offset
     * @param _limit Maximum number of records to return
     * @return hashes Array of data hashes
     */
    function getDataBySource(
        string memory _dataSource,
        uint256 _offset,
        uint256 _limit
    ) external view returns (bytes32[] memory hashes) {
        require(_limit > 0 && _limit <= 100, "Limit must be between 1 and 100");
        
        // Count matching records
        uint256 matchCount = 0;
        for (uint256 i = 0; i < allDataHashes.length; i++) {
            if (keccak256(bytes(environmentalRecords[allDataHashes[i]].dataSource)) == 
                keccak256(bytes(_dataSource))) {
                matchCount++;
            }
        }
        
        if (matchCount == 0 || _offset >= matchCount) {
            return new bytes32[](0);
        }
        
        // Calculate actual return size
        uint256 returnSize = matchCount - _offset;
        if (returnSize > _limit) {
            returnSize = _limit;
        }
        
        // Fill return array
        hashes = new bytes32[](returnSize);
        uint256 currentIndex = 0;
        uint256 matchIndex = 0;
        
        for (uint256 i = 0; i < allDataHashes.length && currentIndex < returnSize; i++) {
            if (keccak256(bytes(environmentalRecords[allDataHashes[i]].dataSource)) == 
                keccak256(bytes(_dataSource))) {
                if (matchIndex >= _offset) {
                    hashes[currentIndex] = allDataHashes[i];
                    currentIndex++;
                }
                matchIndex++;
            }
        }
        
        return hashes;
    }
    
    /**
     * @dev Get recent data records with pagination
     * @param _offset Starting offset
     * @param _limit Maximum number of records to return
     * @return hashes Array of data hashes (most recent first)
     */
    function getRecentData(uint256 _offset, uint256 _limit) 
        external 
        view 
        returns (bytes32[] memory hashes) 
    {
        require(_limit > 0 && _limit <= 100, "Limit must be between 1 and 100");
        
        if (allDataHashes.length == 0 || _offset >= allDataHashes.length) {
            return new bytes32[](0);
        }
        
        uint256 returnSize = allDataHashes.length - _offset;
        if (returnSize > _limit) {
            returnSize = _limit;
        }
        
        hashes = new bytes32[](returnSize);
        
        // Return in reverse order (most recent first)
        for (uint256 i = 0; i < returnSize; i++) {
            hashes[i] = allDataHashes[allDataHashes.length - 1 - _offset - i];
        }
        
        return hashes;
    }
    
    /**
     * @dev Add authorized logger
     * @param _logger Address to authorize
     */
    function addAuthorizedLogger(address _logger) external onlyOwner {
        require(_logger != address(0), "Invalid logger address");
        authorizedLoggers[_logger] = true;
    }
    
    /**
     * @dev Remove authorized logger
     * @param _logger Address to remove
     */
    function removeAuthorizedLogger(address _logger) external onlyOwner {
        require(_logger != owner, "Cannot remove owner from loggers");
        authorizedLoggers[_logger] = false;
    }
    
    /**
     * @dev Add authorized verifier
     * @param _verifier Address to authorize
     */
    function addAuthorizedVerifier(address _verifier) external onlyOwner {
        require(_verifier != address(0), "Invalid verifier address");
        authorizedVerifiers[_verifier] = true;
    }
    
    /**
     * @dev Remove authorized verifier
     * @param _verifier Address to remove
     */
    function removeAuthorizedVerifier(address _verifier) external onlyOwner {
        require(_verifier != owner, "Cannot remove owner from verifiers");
        authorizedVerifiers[_verifier] = false;
    }
    
    /**
     * @dev Get contract statistics
     * @return totalCount Total number of records
     * @return verifiedCount Number of verified records
     * @return uniqueSources Number of unique data sources
     */
    function getContractStats() 
        external 
        view 
        returns (uint256 totalCount, uint256 verifiedCount, uint256 uniqueSources) 
    {
        totalCount = totalRecords;
        
        // Count verified records
        verifiedCount = 0;
        for (uint256 i = 0; i < allDataHashes.length; i++) {
            if (environmentalRecords[allDataHashes[i]].isVerified) {
                verifiedCount++;
            }
        }
        
        // This is a simplified count - in production you'd want to track this more efficiently
        uniqueSources = 0; // Would need additional logic to count unique sources
        
        return (totalCount, verifiedCount, uniqueSources);
    }
    
    /**
     * @dev Emergency function to transfer ownership
     * @param _newOwner New owner address
     */
    function transferOwnership(address _newOwner) external onlyOwner {
        require(_newOwner != address(0), "Invalid new owner address");
        require(_newOwner != owner, "New owner cannot be current owner");
        
        // Remove current owner from authorized lists
        authorizedLoggers[owner] = false;
        authorizedVerifiers[owner] = false;
        
        // Add new owner to authorized lists
        authorizedLoggers[_newOwner] = true;
        authorizedVerifiers[_newOwner] = true;
        
        // Transfer ownership
        owner = _newOwner;
    }
    
    /**
     * @dev Get contract version
     * @return Version string
     */
    function getVersion() external pure returns (string memory) {
        return "Ocean Sentinel Data Contract v1.0.0";
    }
}
