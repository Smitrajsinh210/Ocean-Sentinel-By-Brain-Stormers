// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title Alert Contract
 * @dev Smart contract for managing and tracking alert notifications
 * @notice This contract maintains records of all alerts sent for threats
 */
contract AlertContract {
    // Enums
    enum AlertStatus { PENDING, SENT, DELIVERED, FAILED }
    enum AlertChannel { WEB, EMAIL, SMS, PUSH }
    
    // Structs
    struct Alert {
        uint256 id;
        uint256 threatId;
        string message;
        uint8 severity;
        AlertChannel[] channels;
        string[] recipients;
        address sender;
        uint256 timestamp;
        AlertStatus status;
        uint256 deliveryTimestamp;
        string failureReason;
        bool isEmergency;
    }
    
    struct AlertStats {
        uint256 totalAlerts;
        uint256 successfulAlerts;
        uint256 failedAlerts;
        uint256 averageDeliveryTime;
        uint256 emergencyAlerts;
    }
    
    // Events
    event AlertCreated(
        uint256 indexed alertId,
        uint256 indexed threatId,
        uint8 severity,
        address indexed sender,
        uint256 timestamp,
        bool isEmergency
    );
    
    event AlertStatusUpdated(
        uint256 indexed alertId,
        AlertStatus oldStatus,
        AlertStatus newStatus,
        uint256 timestamp
    );
    
    event AlertDelivered(
        uint256 indexed alertId,
        uint256 deliveryTime,
        uint256 timestamp
    );
    
    event EmergencyAlert(
        uint256 indexed alertId,
        uint256 indexed threatId,
        uint8 severity,
        uint256 timestamp
    );
    
    // State variables
    address public owner;
    uint256 public nextAlertId;
    uint256 public totalAlerts;
    uint256 public emergencyThreshold; // Severity level for emergency alerts
    
    // Mappings
    mapping(uint256 => Alert) public alerts;
    mapping(address => bool) public authorizedSenders;
    mapping(uint256 => uint256[]) public threatAlerts; // threatId => alertIds
    mapping(AlertStatus => uint256) public statusCount;
    
    // Arrays for iteration
    uint256[] public allAlertIds;
    uint256[] public emergencyAlertIds;
    uint256[] public recentAlertIds; // Last 1000 alerts
    
    // Constants
    uint256 public constant MAX_RECIPIENTS = 1000;
    uint256 public constant MAX_MESSAGE_LENGTH = 1000;
    uint256 public constant RECENT_ALERTS_LIMIT = 1000;
    
    // Modifiers
    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this function");
        _;
    }
    
    modifier onlyAuthorizedSender() {
        require(authorizedSenders[msg.sender] || msg.sender == owner, 
                "Not authorized to send alerts");
        _;
    }
    
    modifier alertExists(uint256 _alertId) {
        require(_alertId < nextAlertId, "Alert does not exist");
        _;
    }
    
    modifier validSeverity(uint8 _severity) {
        require(_severity >= 1 && _severity <= 5, "Invalid severity level");
        _;
    }
    
    // Constructor
    constructor() {
        owner = msg.sender;
        authorizedSenders[msg.sender] = true;
        nextAlertId = 1;
        totalAlerts = 0;
        emergencyThreshold = 4; // Severity 4 and 5 are emergencies
    }
    
    /**
     * @dev Create a new alert
     * @param _threatId Associated threat ID
     * @param _message Alert message
     * @param _severity Alert severity (1-5)
     * @param _channels Array of alert channels
     * @param _recipients Array of recipient identifiers
     * @return alertId ID of the created alert
     */
    function createAlert(
        uint256 _threatId,
        string memory _message,
        uint8 _severity,
        AlertChannel[] memory _channels,
        string[] memory _recipients
    ) 
        external 
        onlyAuthorizedSender 
        validSeverity(_severity)
        returns (uint256 alertId) 
    {
        require(bytes(_message).length > 0 && bytes(_message).length <= MAX_MESSAGE_LENGTH, 
                "Invalid message length");
        require(_channels.length > 0, "At least one channel required");
        require(_recipients.length > 0 && _recipients.length <= MAX_RECIPIENTS, 
                "Invalid number of recipients");
        
        alertId = nextAlertId;
        nextAlertId++;
        
        bool isEmergency = _severity >= emergencyThreshold;
        
        // Create new alert
        alerts[alertId] = Alert({
            id: alertId,
            threatId: _threatId,
            message: _message,
            severity: _severity,
            channels: _channels,
            recipients: _recipients,
            sender: msg.sender,
            timestamp: block.timestamp,
            status: AlertStatus.PENDING,
            deliveryTimestamp: 0,
            failureReason: "",
            isEmergency: isEmergency
        });
        
        // Update tracking arrays and counters
        allAlertIds.push(alertId);
        threatAlerts[_threatId].push(alertId);
        
        // Add to recent alerts (maintain size limit)
        recentAlertIds.push(alertId);
        if (recentAlertIds.length > RECENT_ALERTS_LIMIT) {
            // Remove oldest alert from recent list
            for (uint256 i = 0; i < recentAlertIds.length - 1; i++) {
                recentAlertIds[i] = recentAlertIds[i + 1];
            }
            recentAlertIds.pop();
        }
        
        if (isEmergency) {
            emergencyAlertIds.push(alertId);
            emit EmergencyAlert(alertId, _threatId, _severity, block.timestamp);
        }
        
        totalAlerts++;
        statusCount[AlertStatus.PENDING]++;
        
        emit AlertCreated(alertId, _threatId, _severity, msg.sender, block.timestamp, isEmergency);
        
        return alertId;
    }
    
    /**
     * @dev Update alert status
     * @param _alertId ID of the alert
     * @param _newStatus New status
     * @param _failureReason Reason for failure (if applicable)
     */
    function updateAlertStatus(
        uint256 _alertId, 
        AlertStatus _newStatus,
        string memory _failureReason
    ) 
        external 
        onlyAuthorizedSender 
        alertExists(_alertId) 
    {
        Alert storage alert = alerts[_alertId];
        AlertStatus oldStatus = alert.status;
        require(oldStatus != _newStatus, "Status is already set to this value");
        
        alert.status = _newStatus;
        
        // Set failure reason if status is FAILED
        if (_newStatus == AlertStatus.FAILED) {
            alert.failureReason = _failureReason;
        }
        
        // Set delivery timestamp if delivered
        if (_newStatus == AlertStatus.DELIVERED) {
            alert.deliveryTimestamp = block.timestamp;
            uint256 deliveryTime = block.timestamp - alert.timestamp;
            emit AlertDelivered(_alertId, deliveryTime, block.timestamp);
        }
        
        // Update status counters
        statusCount[oldStatus]--;
        statusCount[_newStatus]++;
        
        emit AlertStatusUpdated(_alertId, oldStatus, _newStatus, block.timestamp);
    }
    
    /**
     * @dev Get alert by ID
     * @param _alertId ID of the alert
     * @return Alert data
     */
    function getAlert(uint256 _alertId) 
        external 
        view 
        alertExists(_alertId) 
        returns (Alert memory) 
    {
        return alerts[_alertId];
    }
    
    /**
     * @dev Get alerts for a specific threat
     * @param _threatId Threat ID
     * @return alertIds Array of alert IDs for the threat
     */
    function getAlertsForThreat(uint256 _threatId) 
        external 
        view 
        returns (uint256[] memory alertIds) 
    {
        return threatAlerts[_threatId];
    }
    
    /**
     * @dev Get recent alerts with pagination
     * @param _offset Starting offset
     * @param _limit Maximum number of alerts to return
     * @return alertIds Array of recent alert IDs
     */
    function getRecentAlerts(uint256 _offset, uint256 _limit) 
        external 
        view 
        returns (uint256[] memory alertIds) 
    {
        require(_limit > 0 && _limit <= 100, "Limit must be between 1 and 100");
        
        if (recentAlertIds.length == 0 || _offset >= recentAlertIds.length) {
            return new uint256[](0);
        }
        
        uint256 returnSize = recentAlertIds.length - _offset;
        if (returnSize > _limit) {
            returnSize = _limit;
        }
        
        alertIds = new uint256[](returnSize);
        
        // Return in reverse order (most recent first)
        for (uint256 i = 0; i < returnSize; i++) {
            alertIds[i] = recentAlertIds[recentAlertIds.length - 1 - _offset - i];
        }
        
        return alertIds;
    }
    
    /**
     * @dev Get emergency alerts with pagination
     * @param _offset Starting offset
     * @param _limit Maximum number of alerts to return
     * @return alertIds Array of emergency alert IDs
     */
    function getEmergencyAlerts(uint256 _offset, uint256 _limit) 
        external 
        view 
        returns (uint256[] memory alertIds) 
    {
        require(_limit > 0 && _limit <= 100, "Limit must be between 1 and 100");
        
        if (emergencyAlertIds.length == 0 || _offset >= emergencyAlertIds.length) {
            return new uint256[](0);
        }
        
        uint256 returnSize = emergencyAlertIds.length - _offset;
        if (returnSize > _limit) {
            returnSize = _limit;
        }
        
        alertIds = new uint256[](returnSize);
        
        // Return in reverse order (most recent first)
        for (uint256 i = 0; i < returnSize; i++) {
            alertIds[i] = emergencyAlertIds[emergencyAlertIds.length - 1 - _offset - i];
        }
        
        return alertIds;
    }
    
    /**
     * @dev Get alerts by status with pagination
     * @param _status Alert status to filter by
     * @param _offset Starting offset
     * @param _limit Maximum number of alerts to return
     * @return alertIds Array of alert IDs with specified status
     */
    function getAlertsByStatus(AlertStatus _status, uint256 _offset, uint256 _limit) 
        external 
        view 
        returns (uint256[] memory alertIds) 
    {
        require(_limit > 0 && _limit <= 100, "Limit must be between 1 and 100");
        
        // Count matching alerts
        uint256 matchCount = 0;
        for (uint256 i = 0; i < allAlertIds.length; i++) {
            if (alerts[allAlertIds[i]].status == _status) {
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
        
        alertIds = new uint256[](returnSize);
        uint256 currentIndex = 0;
        uint256 matchIndex = 0;
        
        // Return in reverse order (most recent first)
        for (int256 i = int256(allAlertIds.length) - 1; i >= 0 && currentIndex < returnSize; i--) {
            if (alerts[allAlertIds[uint256(i)]].status == _status) {
                if (matchIndex >= _offset) {
                    alertIds[currentIndex] = allAlertIds[uint256(i)];
                    currentIndex++;
                }
                matchIndex++;
            }
        }
        
        return alertIds;
    }
    
    /**
     * @dev Get alert statistics
     * @return stats AlertStats struct with comprehensive statistics
     */
    function getAlertStats() external view returns (AlertStats memory stats) {
        stats.totalAlerts = totalAlerts;
        stats.successfulAlerts = statusCount[AlertStatus.DELIVERED];
        stats.failedAlerts = statusCount[AlertStatus.FAILED];
        stats.emergencyAlerts = emergencyAlertIds.length;
        
        // Calculate average delivery time
        uint256 totalDeliveryTime = 0;
        uint256 deliveredCount = 0;
        
        for (uint256 i = 0; i < allAlertIds.length; i++) {
            Alert storage alert = alerts[allAlertIds[i]];
            if (alert.status == AlertStatus.DELIVERED && alert.deliveryTimestamp > alert.timestamp) {
                totalDeliveryTime += (alert.deliveryTimestamp - alert.timestamp);
                deliveredCount++;
            }
        }
        
        if (deliveredCount > 0) {
            stats.averageDeliveryTime = totalDeliveryTime / deliveredCount;
        } else {
            stats.averageDeliveryTime = 0;
        }
        
        return stats;
    }
    
    /**
     * @dev Set emergency threshold
     * @param _threshold New emergency threshold (severity level)
     */
    function setEmergencyThreshold(uint8 _threshold) 
        external 
        onlyOwner 
        validSeverity(_threshold) 
    {
        emergencyThreshold = _threshold;
    }
    
    /**
     * @dev Add authorized sender
     * @param _sender Address to authorize
     */
    function addAuthorizedSender(address _sender) external onlyOwner {
        require(_sender != address(0), "Invalid sender address");
        authorizedSenders[_sender] = true;
    }
    
    /**
     * @dev Remove authorized sender
     * @param _sender Address to remove
     */
    function removeAuthorizedSender(address _sender) external onlyOwner {
        require(_sender != owner, "Cannot remove owner from senders");
        authorizedSenders[_sender] = false;
    }
    
    /**
     * @dev Transfer ownership
     * @param _newOwner New owner address
     */
    function transferOwnership(address _newOwner) external onlyOwner {
        require(_newOwner != address(0), "Invalid new owner address");
        require(_newOwner != owner, "New owner cannot be current owner");
        
        authorizedSenders[_newOwner] = true;
        owner = _newOwner;
    }
    
    /**
     * @dev Get contract version
     * @return Version string
     */
    function getVersion() external pure returns (string memory) {
        return "Alert Contract v1.0.0";
    }
}
