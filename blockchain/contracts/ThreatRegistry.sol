// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title Threat Registry Contract
 * @dev Smart contract for registering and managing environmental threats
 * @notice This contract maintains an immutable registry of detected threats
 */
contract ThreatRegistry {
    // Enums
    enum ThreatType { STORM, POLLUTION, EROSION, ALGAL_BLOOM, ILLEGAL_DUMPING, ANOMALY }
    enum ThreatStatus { ACTIVE, RESOLVED, INVESTIGATING, FALSE_POSITIVE }
    
    // Structs
    struct Threat {
        uint256 id;
        ThreatType threatType;
        uint8 severity; // 1-5 scale
        uint256 confidence; // Stored as percentage (0-100)
        int256 latitude; // Stored as fixed-point (multiply by 1e6)
        int256 longitude; // Stored as fixed-point (multiply by 1e6)
        string description;
        address reporter;
        uint256 timestamp;
        ThreatStatus status;
        bytes32 dataHash; // Hash of supporting data
        uint256 affectedPopulation;
        bool verified;
        address verifier;
        uint256 verificationTimestamp;
    }
    
    // Events
    event ThreatRegistered(
        uint256 indexed threatId,
        ThreatType indexed threatType,
        uint8 severity,
        address indexed reporter,
        uint256 timestamp
    );
    
    event ThreatStatusUpdated(
        uint256 indexed threatId,
        ThreatStatus oldStatus,
        ThreatStatus newStatus,
        address indexed updater,
        uint256 timestamp
    );
    
    event ThreatVerified(
        uint256 indexed threatId,
        address indexed verifier,
        uint256 timestamp,
        bool verified
    );
    
    // State variables
    address public owner;
    uint256 public nextThreatId;
    uint256 public totalThreats;
    
    // Mappings
    mapping(uint256 => Threat) public threats;
    mapping(address => bool) public authorizedReporters;
    mapping(address => bool) public authorizedVerifiers;
    mapping(ThreatType => uint256) public threatTypeCount;
    mapping(ThreatStatus => uint256) public threatStatusCount;
    
    // Arrays for iteration
    uint256[] public activeThreatIds;
    uint256[] public allThreatIds;
    
    // Constants
    uint256 public constant MAX_SEVERITY = 5;
    uint256 public constant MAX_CONFIDENCE = 100;
    int256 public constant COORDINATE_PRECISION = 1e6;
    
    // Modifiers
    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this function");
        _;
    }
    
    modifier onlyAuthorizedReporter() {
        require(authorizedReporters[msg.sender] || msg.sender == owner, 
                "Not authorized to report threats");
        _;
    }
    
    modifier onlyAuthorizedVerifier() {
        require(authorizedVerifiers[msg.sender] || msg.sender == owner, 
                "Not authorized to verify threats");
        _;
    }
    
    modifier threatExists(uint256 _threatId) {
        require(_threatId < nextThreatId, "Threat does not exist");
        _;
    }
    
    modifier validSeverity(uint8 _severity) {
        require(_severity >= 1 && _severity <= MAX_SEVERITY, "Invalid severity level");
        _;
    }
    
    modifier validConfidence(uint256 _confidence) {
        require(_confidence <= MAX_CONFIDENCE, "Invalid confidence level");
        _;
    }
    
    // Constructor
    constructor() {
        owner = msg.sender;
        authorizedReporters[msg.sender] = true;
        authorizedVerifiers[msg.sender] = true;
        nextThreatId = 1;
        totalThreats = 0;
    }
    
    /**
     * @dev Register a new environmental threat
     * @param _threatType Type of threat
     * @param _severity Severity level (1-5)
     * @param _confidence Confidence percentage (0-100)
     * @param _latitude Latitude * 1e6
     * @param _longitude Longitude * 1e6
     * @param _description Description of the threat
     * @param _dataHash Hash of supporting environmental data
     * @param _affectedPopulation Estimated affected population
     * @return threatId ID of the registered threat
     */
    function registerThreat(
        ThreatType _threatType,
        uint8 _severity,
        uint256 _confidence,
        int256 _latitude,
        int256 _longitude,
        string memory _description,
        bytes32 _dataHash,
        uint256 _affectedPopulation
    ) 
        external 
        onlyAuthorizedReporter 
        validSeverity(_severity)
        validConfidence(_confidence)
        returns (uint256 threatId) 
    {
        require(bytes(_description).length > 0, "Description cannot be empty");
        require(_dataHash != bytes32(0), "Data hash cannot be empty");
        
        threatId = nextThreatId;
        nextThreatId++;
        
        // Create new threat
        threats[threatId] = Threat({
            id: threatId,
            threatType: _threatType,
            severity: _severity,
            confidence: _confidence,
            latitude: _latitude,
            longitude: _longitude,
            description: _description,
            reporter: msg.sender,
            timestamp: block.timestamp,
            status: ThreatStatus.ACTIVE,
            dataHash: _dataHash,
            affectedPopulation: _affectedPopulation,
            verified: false,
            verifier: address(0),
            verificationTimestamp: 0
        });
        
        // Update tracking arrays and counters
        activeThreatIds.push(threatId);
        allThreatIds.push(threatId);
        totalThreats++;
        threatTypeCount[_threatType]++;
        threatStatusCount[ThreatStatus.ACTIVE]++;
        
        emit ThreatRegistered(threatId, _threatType, _severity, msg.sender, block.timestamp);
        
        return threatId;
    }
    
    /**
     * @dev Update threat status
     * @param _threatId ID of the threat
     * @param _newStatus New status
     */
    function updateThreatStatus(uint256 _threatId, ThreatStatus _newStatus) 
        external 
        onlyAuthorizedReporter 
        threatExists(_threatId) 
    {
        Threat storage threat = threats[_threatId];
        ThreatStatus oldStatus = threat.status;
        require(oldStatus != _newStatus, "Status is already set to this value");
        
        threat.status = _newStatus;
        
        // Update status counters
        threatStatusCount[oldStatus]--;
        threatStatusCount[_newStatus]++;
        
        // Update active threats array
        if (oldStatus == ThreatStatus.ACTIVE && _newStatus != ThreatStatus.ACTIVE) {
            _removeFromActiveThreatIds(_threatId);
        } else if (oldStatus != ThreatStatus.ACTIVE && _newStatus == ThreatStatus.ACTIVE) {
            activeThreatIds.push(_threatId);
        }
        
        emit ThreatStatusUpdated(_threatId, oldStatus, _newStatus, msg.sender, block.timestamp);
    }
    
    /**
     * @dev Verify a threat
     * @param _threatId ID of the threat to verify
     * @param _isVerified Whether the threat is verified as legitimate
     */
    function verifyThreat(uint256 _threatId, bool _isVerified) 
        external 
        onlyAuthorizedVerifier 
        threatExists(_threatId) 
    {
        Threat storage threat = threats[_threatId];
        require(!threat.verified, "Threat already verified");
        
        threat.verified = true;
        threat.verifier = msg.sender;
        threat.verificationTimestamp = block.timestamp;
        
        // If marked as false positive, update status
        if (!_isVerified && threat.status == ThreatStatus.ACTIVE) {
            updateThreatStatus(_threatId, ThreatStatus.FALSE_POSITIVE);
        }
        
        emit ThreatVerified(_threatId, msg.sender, block.timestamp, _isVerified);
    }
    
    /**
     * @dev Get threat by ID
     * @param _threatId ID of the threat
     * @return Threat data
     */
    function getThreat(uint256 _threatId) 
        external 
        view 
        threatExists(_threatId) 
        returns (Threat memory) 
    {
        return threats[_threatId];
    }
    
    /**
     * @dev Get active threats with pagination
     * @param _offset Starting offset
     * @param _limit Maximum number of threats to return
     * @return threatIds Array of active threat IDs
     */
    function getActiveThreats(uint256 _offset, uint256 _limit) 
        external 
        view 
        returns (uint256[] memory threatIds) 
    {
        require(_limit > 0 && _limit <= 100, "Limit must be between 1 and 100");
        
        if (activeThreatIds.length == 0 || _offset >= activeThreatIds.length) {
            return new uint256[](0);
        }
        
        uint256 returnSize = activeThreatIds.length - _offset;
        if (returnSize > _limit) {
            returnSize = _limit;
        }
        
        threatIds = new uint256[](returnSize);
        for (uint256 i = 0; i < returnSize; i++) {
            threatIds[i] = activeThreatIds[_offset + i];
        }
        
        return threatIds;
    }
    
    /**
     * @dev Get threats by type with pagination
     * @param _threatType Type of threats to retrieve
     * @param _offset Starting offset
     * @param _limit Maximum number of threats to return
     * @return threatIds Array of threat IDs of specified type
     */
    function getThreatsByType(ThreatType _threatType, uint256 _offset, uint256 _limit) 
        external 
        view 
        returns (uint256[] memory threatIds) 
    {
        require(_limit > 0 && _limit <= 100, "Limit must be between 1 and 100");
        
        // Count matching threats
        uint256 matchCount = 0;
        for (uint256 i = 0; i < allThreatIds.length; i++) {
            if (threats[allThreatIds[i]].threatType == _threatType) {
                matchCount++;
            }
        }
        
        if (matchCount == 0 || _offset >= matchCount) {
            return new uint256[](0);
        }
        
        uint256 returnSize = matchCount - _offset;
        if (returnSize > _limit) {
            returnSize = _limit;
        }
        
        threatIds = new uint256[](returnSize);
        uint256 currentIndex = 0;
        uint256 matchIndex = 0;
        
        for (uint256 i = 0; i < allThreatIds.length && currentIndex < returnSize; i++) {
            if (threats[allThreatIds[i]].threatType == _threatType) {
                if (matchIndex >= _offset) {
                    threatIds[currentIndex] = allThreatIds[i];
                    currentIndex++;
                }
                matchIndex++;
            }
        }
        
        return threatIds;
    }
    
    /**
     * @dev Get threats by severity level
     * @param _minSeverity Minimum severity level
     * @param _offset Starting offset
     * @param _limit Maximum number of threats to return
     * @return threatIds Array of threat IDs with severity >= _minSeverity
     */
    function getThreatsBySeverity(uint8 _minSeverity, uint256 _offset, uint256 _limit) 
        external 
        view 
        validSeverity(_minSeverity)
        returns (uint256[] memory threatIds) 
    {
        require(_limit > 0 && _limit <= 100, "Limit must be between 1 and 100");
        
        // Count matching threats
        uint256 matchCount = 0;
        for (uint256 i = 0; i < allThreatIds.length; i++) {
            if (threats[allThreatIds[i]].severity >= _minSeverity) {
                matchCount++;
            }
        }
        
        if (matchCount == 0 || _offset >= matchCount) {
            return new uint256[](0);
        }
        
        uint256 returnSize = matchCount - _offset;
        if (returnSize > _limit) {
            returnSize = _limit;
        }
        
        threatIds = new uint256[](returnSize);
        uint256 currentIndex = 0;
        uint256 matchIndex = 0;
        
        for (uint256 i = 0; i < allThreatIds.length && currentIndex < returnSize; i++) {
            if (threats[allThreatIds[i]].severity >= _minSeverity) {
                if (matchIndex >= _offset) {
                    threatIds[currentIndex] = allThreatIds[i];
                    currentIndex++;
                }
                matchIndex++;
            }
        }
        
        return threatIds;
    }
    
    /**
     * @dev Get contract statistics
     * @return totalCount Total number of threats
     * @return activeCount Number of active threats
     * @return resolvedCount Number of resolved threats
     * @return verifiedCount Number of verified threats
     */
    function getRegistryStats() 
        external 
        view 
        returns (
            uint256 totalCount,
            uint256 activeCount,
            uint256 resolvedCount,
            uint256 verifiedCount
        ) 
    {
        totalCount = totalThreats;
        activeCount = threatStatusCount[ThreatStatus.ACTIVE];
        resolvedCount = threatStatusCount[ThreatStatus.RESOLVED];
        
        // Count verified threats
        verifiedCount = 0;
        for (uint256 i = 0; i < allThreatIds.length; i++) {
            if (threats[allThreatIds[i]].verified) {
                verifiedCount++;
            }
        }
        
        return (totalCount, activeCount, resolvedCount, verifiedCount);
    }
    
    /**
     * @dev Internal function to remove threat ID from active threats array
     * @param _threatId ID to remove
     */
    function _removeFromActiveThreatIds(uint256 _threatId) internal {
        for (uint256 i = 0; i < activeThreatIds.length; i++) {
            if (activeThreatIds[i] == _threatId) {
                // Move last element to this position and pop
                activeThreatIds[i] = activeThreatIds[activeThreatIds.length - 1];
                activeThreatIds.pop();
                break;
            }
        }
    }
    
    /**
     * @dev Add authorized reporter
     * @param _reporter Address to authorize
     */
    function addAuthorizedReporter(address _reporter) external onlyOwner {
        require(_reporter != address(0), "Invalid reporter address");
        authorizedReporters[_reporter] = true;
    }
    
    /**
     * @dev Remove authorized reporter
     * @param _reporter Address to remove
     */
    function removeAuthorizedReporter(address _reporter) external onlyOwner {
        require(_reporter != owner, "Cannot remove owner from reporters");
        authorizedReporters[_reporter] = false;
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
     * @dev Transfer ownership
     * @param _newOwner New owner address
     */
    function transferOwnership(address _newOwner) external onlyOwner {
        require(_newOwner != address(0), "Invalid new owner address");
        require(_newOwner != owner, "New owner cannot be current owner");
        
        authorizedReporters[_newOwner] = true;
        authorizedVerifiers[_newOwner] = true;
        
        owner = _newOwner;
    }
    
    /**
     * @dev Get contract version
     * @return Version string
     */
    function getVersion() external pure returns (string memory) {
        return "Threat Registry Contract v1.0.0";
    }
}
