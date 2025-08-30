/**
 * Ocean Sentinel - Contract Interaction Script
 * Test and interact with deployed Ocean Sentinel contracts
 */

const axios = require('axios');
const crypto = require('crypto');
require('dotenv').config();

class ContractInteractor {
    constructor() {
        this.startonApiKey = process.env.STARTON_API_KEY;
        this.network = process.env.BLOCKCHAIN_NETWORK || 'polygon-mumbai';
        this.baseUrl = 'https://api.starton.com/v3';
        
        // Contract addresses (should be set after deployment)
        this.contracts = {
            OceanSentinelData: process.env.CONTRACT_ADDRESS_DATA,
            ThreatRegistry: process.env.CONTRACT_ADDRESS_THREATS,
            AlertContract: process.env.CONTRACT_ADDRESS_ALERTS
        };
        
        if (!this.startonApiKey) {
            throw new Error('STARTON_API_KEY not found in environment variables');
        }
        
        console.log('🔗 Ocean Sentinel Contract Interactor initialized');
        console.log(`📡 Network: ${this.network}`);
    }
    
    /**
     * Test all contract interactions
     */
    async testAllContracts() {
        try {
            console.log('🧪 Starting contract interaction tests...\n');
            
            // Test Ocean Sentinel Data Contract
            await this.testOceanSentinelDataContract();
            
            // Test Threat Registry Contract
            await this.testThreatRegistryContract();
            
            // Test Alert Contract
            await this.testAlertContract();
            
            console.log('\n✅ All contract tests completed successfully!');
            
        } catch (error) {
            console.error('❌ Contract testing failed:', error.message);
            throw error;
        }
    }
    
    /**
     * Test Ocean Sentinel Data contract
     */
    async testOceanSentinelDataContract() {
        console.log('📊 Testing OceanSentinelData contract...');
        
        const contractAddress = this.contracts.OceanSentinelData;
        if (!contractAddress) {
            console.error('❌ OceanSentinelData contract address not found');
            return;
        }
        
        try {
            // Test 1: Log environmental data
            console.log('📝 Test 1: Logging environmental data...');
            
            const testData = {
                temperature: 25.5,
                humidity: 68,
                pressure: 1013.25,
                timestamp: Date.now()
            };
            
            const dataHash = crypto.createHash('sha256')
                .update(JSON.stringify(testData))
                .digest('hex');
            
            const logDataResponse = await this.callContractFunction(
                contractAddress,
                'logEnvironmentalData',
                [
                    `0x${dataHash}`,
                    'weather_api',
                    'temperature_humidity'
                ]
            );
            
            console.log(`✅ Data logged successfully. TX: ${logDataResponse.transactionHash}`);
            
            // Test 2: Verify data integrity
            console.log('🔍 Test 2: Verifying data integrity...');
            
            const verifyResponse = await this.callContractFunction(
                contractAddress,
                'verifyDataIntegrity',
                [
                    `0x${dataHash}`,
                    true
                ]
            );
            
            console.log(`✅ Data verified successfully. TX: ${verifyResponse.transactionHash}`);
            
            // Test 3: Get environmental data
            console.log('📖 Test 3: Reading environmental data...');
            
            const readResponse = await this.readContractFunction(
                contractAddress,
                'getEnvironmentalData',
                [`0x${dataHash}`]
            );
            
            console.log('✅ Data read successfully:', readResponse);
            
            // Test 4: Get contract stats
            console.log('📈 Test 4: Getting contract statistics...');
            
            const statsResponse = await this.readContractFunction(
                contractAddress,
                'getContractStats',
                []
            );
            
            console.log('✅ Contract stats:', statsResponse);
            console.log();
            
        } catch (error) {
            console.error('❌ OceanSentinelData test failed:', error.message);
        }
    }
    
    /**
     * Test Threat Registry contract
     */
    async testThreatRegistryContract() {
        console.log('🚨 Testing ThreatRegistry contract...');
        
        const contractAddress = this.contracts.ThreatRegistry;
        if (!contractAddress) {
            console.error('❌ ThreatRegistry contract address not found');
            return;
        }
        
        try {
            // Test 1: Register a threat
            console.log('📝 Test 1: Registering a threat...');
            
            const testDataHash = crypto.createHash('sha256')
                .update(JSON.stringify({ test: 'threat data' }))
                .digest('hex');
            
            const registerResponse = await this.callContractFunction(
                contractAddress,
                'registerThreat',
                [
                    0, // ThreatType.STORM
                    4, // Severity
                    85, // Confidence (85%)
                    40712800, // Latitude * 1e6 (40.7128)
                    -74006000, // Longitude * 1e6 (-74.0060)
                    'Severe storm conditions detected in NYC area',
                    `0x${testDataHash}`,
                    1000000 // Affected population
                ]
            );
            
            console.log(`✅ Threat registered successfully. TX: ${registerResponse.transactionHash}`);
            
            // Extract threat ID from transaction receipt
            const threatId = 1; // Assuming this is the first threat
            
            // Test 2: Update threat status
            console.log('🔄 Test 2: Updating threat status...');
            
            const updateResponse = await this.callContractFunction(
                contractAddress,
                'updateThreatStatus',
                [
                    threatId,
                    2 // ThreatStatus.INVESTIGATING
                ]
            );
            
            console.log(`✅ Threat status updated. TX: ${updateResponse.transactionHash}`);
            
            // Test 3: Verify threat
            console.log('✅ Test 3: Verifying threat...');
            
            const verifyResponse = await this.callContractFunction(
                contractAddress,
                'verifyThreat',
                [
                    threatId,
                    true
                ]
            );
            
            console.log(`✅ Threat verified. TX: ${verifyResponse.transactionHash}`);
            
            // Test 4: Get threat details
            console.log('📖 Test 4: Reading threat details...');
            
            const threatResponse = await this.readContractFunction(
                contractAddress,
                'getThreat',
                [threatId]
            );
            
            console.log('✅ Threat details:', threatResponse);
            
            // Test 5: Get registry statistics
            console.log('📈 Test 5: Getting registry statistics...');
            
            const statsResponse = await this.readContractFunction(
                contractAddress,
                'getRegistryStats',
                []
            );
            
            console.log('✅ Registry stats:', statsResponse);
            console.log();
            
        } catch (error) {
            console.error('❌ ThreatRegistry test failed:', error.message);
        }
    }
    
    /**
     * Test Alert contract
     */
    async testAlertContract() {
        console.log('📢 Testing AlertContract...');
        
        const contractAddress = this.contracts.AlertContract;
        if (!contractAddress) {
            console.error('❌ AlertContract address not found');
            return;
        }
        
        try {
            // Test 1: Create an alert
            console.log('📝 Test 1: Creating an alert...');
            
            const createResponse = await this.callContractFunction(
                contractAddress,
                'createAlert',
                [
                    1, // Threat ID
                    'URGENT: Severe storm approaching NYC area. Seek shelter immediately.',
                    4, // Severity
                    [0, 1, 2], // Channels: WEB, EMAIL, SMS
                    ['user1@example.com', 'user2@example.com', '+1234567890']
                ]
            );
            
            console.log(`✅ Alert created successfully. TX: ${createResponse.transactionHash}`);
            
            const alertId = 1; // Assuming this is the first alert
            
            // Test 2: Update alert status
            console.log('🔄 Test 2: Updating alert status...');
            
            const updateResponse = await this.callContractFunction(
                contractAddress,
                'updateAlertStatus',
                [
                    alertId,
                    1, // AlertStatus.SENT
                    '' // No failure reason
                ]
            );
            
            console.log(`✅ Alert status updated. TX: ${updateResponse.transactionHash}`);
            
            // Test 3: Mark as delivered
            console.log('📨 Test 3: Marking alert as delivered...');
            
            const deliveredResponse = await this.callContractFunction(
                contractAddress,
                'updateAlertStatus',
                [
                    alertId,
                    2, // AlertStatus.DELIVERED
                    ''
                ]
            );
            
            console.log(`✅ Alert marked as delivered. TX: ${deliveredResponse.transactionHash}`);
            
            // Test 4: Get alert details
            console.log('📖 Test 4: Reading alert details...');
            
            const alertResponse = await this.readContractFunction(
                contractAddress,
                'getAlert',
                [alertId]
            );
            
            console.log('✅ Alert details:', alertResponse);
            
            // Test 5: Get alert statistics
            console.log('📈 Test 5: Getting alert statistics...');
            
            const statsResponse = await this.readContractFunction(
                contractAddress,
                'getAlertStats',
                []
            );
            
            console.log('✅ Alert stats:', statsResponse);
            console.log();
            
        } catch (error) {
            console.error('❌ AlertContract test failed:', error.message);
        }
    }
    
    /**
     * Call a contract function (write operation)
     */
    async callContractFunction(contractAddress, functionName, params = []) {
        try {
            const response = await this.makeStartonRequest(
                'POST',
                `/smart-contract/${this.network}/${contractAddress}/call`,
                {
                    functionName: functionName,
                    params: params,
                    speed: 'average'
                }
            );
            
            return response.data;
            
        } catch (error) {
            console.error(`Failed to call ${functionName}:`, error.response?.data || error.message);
            throw error;
        }
    }
    
    /**
     * Read from a contract function (read-only operation)
     */
    async readContractFunction(contractAddress, functionName, params = []) {
        try {
            const response = await this.makeStartonRequest(
                'POST',
                `/smart-contract/${this.network}/${contractAddress}/read`,
                {
                    functionName: functionName,
                    params: params
                }
            );
            
            return response.data.response;
            
        } catch (error) {
            console.error(`Failed to read ${functionName}:`, error.response?.data || error.message);
            throw error;
        }
    }
    
    /**
     * Get contract events
     */
    async getContractEvents(contractAddress, eventName = null, fromBlock = 'latest') {
        try {
            const endpoint = `/smart-contract/${this.network}/${contractAddress}/event`;
            const params = {
                fromBlock: fromBlock
            };
            
            if (eventName) {
                params.eventName = eventName;
            }
            
            const response = await this.makeStartonRequest('GET', endpoint, params);
            return response.data;
            
        } catch (error) {
            console.error('Failed to get contract events:', error.response?.data || error.message);
            throw error;
        }
    }
    
    /**
     * Make API request to Starton
     */
    async makeStartonRequest(method, endpoint, data = null) {
        const config = {
            method: method.toLowerCase(),
            url: `${this.baseUrl}${endpoint}`,
            headers: {
                'x-api-key': this.startonApiKey,
                'Content-Type': 'application/json'
            }
        };
        
        if (data) {
            if (method.toLowerCase() === 'get') {
                config.params = data;
            } else {
                config.data = data;
            }
        }
        
        try {
            const response = await axios(config);
            return response;
        } catch (error) {
            console.error(`API Request failed: ${method} ${endpoint}`);
            throw error;
        }
    }
    
    /**
     * Monitor contract events in real-time
     */
    async monitorEvents(contractAddress, eventName = null) {
        console.log(`👀 Monitoring events for contract: ${contractAddress}`);
        if (eventName) {
            console.log(`🎯 Filtering for event: ${eventName}`);
        }
        
        let lastBlock = 'latest';
        
        setInterval(async () => {
            try {
                const events = await this.getContractEvents(contractAddress, eventName, lastBlock);
                
                if (events.length > 0) {
                    console.log(`📡 New events detected: ${events.length}`);
                    events.forEach(event => {
                        console.log(`📋 Event: ${event.name}`, event.data);
                    });
                    
                    // Update last block
                    lastBlock = Math.max(...events.map(e => e.blockNumber)) + 1;
                }
                
            } catch (error) {
                console.error('Event monitoring error:', error.message);
            }
        }, 10000); // Check every 10 seconds
    }
    
    /**
     * Simulate a complete threat detection workflow
     */
    async simulateWorkflow() {
        console.log('🎭 Simulating complete threat detection workflow...\n');
        
        try {
            // Step 1: Log environmental data
            console.log('1️⃣ Logging environmental data...');
            const environmentalData = {
                temperature: 32.5,
                humidity: 85,
                windSpeed: 45,
                pressure: 995.2,
                timestamp: Date.now()
            };
            
            const dataHash = crypto.createHash('sha256')
                .update(JSON.stringify(environmentalData))
                .digest('hex');
            
            await this.callContractFunction(
                this.contracts.OceanSentinelData,
                'logEnvironmentalData',
                [`0x${dataHash}`, 'weather_station', 'severe_weather']
            );
            
            // Step 2: AI detects threat and registers it
            console.log('2️⃣ AI detects threat and registers it...');
            await this.callContractFunction(
                this.contracts.ThreatRegistry,
                'registerThreat',
                [
                    0, // STORM
                    5, // Extreme severity
                    92, // High confidence
                    25761700, // Miami latitude
                    -80191800, // Miami longitude
                    'Extreme hurricane conditions detected approaching Miami',
                    `0x${dataHash}`,
                    2500000 // 2.5M affected population
                ]
            );
            
            // Step 3: Create emergency alert
            console.log('3️⃣ Creating emergency alert...');
            await this.callContractFunction(
                this.contracts.AlertContract,
                'createAlert',
                [
                    2, // Threat ID
                    'EMERGENCY: Category 5 hurricane approaching Miami. Evacuate immediately!',
                    5, // Maximum severity
                    [0, 1, 2, 3], // All channels
                    ['emergency@miami.gov', 'alerts@noaa.gov', '+1-888-WEATHER']
                ]
            );
            
            // Step 4: Verify data integrity
            console.log('4️⃣ Verifying data integrity...');
            await this.callContractFunction(
                this.contracts.OceanSentinelData,
                'verifyDataIntegrity',
                [`0x${dataHash}`, true]
            );
            
            // Step 5: Verify threat
            console.log('5️⃣ Human verification of threat...');
            await this.callContractFunction(
                this.contracts.ThreatRegistry,
                'verifyThreat',
                [2, true]
            );
            
            // Step 6: Update alert status
            console.log('6️⃣ Updating alert delivery status...');
            await this.callContractFunction(
                this.contracts.AlertContract,
                'updateAlertStatus',
                [2, 2, ''] // Delivered
            );
            
            console.log('✅ Complete workflow simulation successful!\n');
            
        } catch (error) {
            console.error('❌ Workflow simulation failed:', error.message);
            throw error;
        }
    }
}

// CLI interface
async function main() {
    const args = process.argv.slice(2);
    const command = args[0];
    
    const interactor = new ContractInteractor();
    
    try {
        switch (command) {
            case 'test':
                await interactor.testAllContracts();
                break;
                
            case 'workflow':
                await interactor.simulateWorkflow();
                break;
                
            case 'monitor':
                const contractAddress = args[1];
                const eventName = args[2];
                if (!contractAddress) {
                    console.error('Usage: node interact.js monitor <contract_address> [event_name]');
                    process.exit(1);
                }
                await interactor.monitorEvents(contractAddress, eventName);
                break;
                
            case 'data':
                await interactor.testOceanSentinelDataContract();
                break;
                
            case 'threats':
                await interactor.testThreatRegistryContract();
                break;
                
            case 'alerts':
                await interactor.testAlertContract();
                break;
                
            default:
                console.log('Ocean Sentinel Contract Interactor');
                console.log('Usage: node interact.js <command>');
                console.log('');
                console.log('Commands:');
                console.log('  test      - Run all contract tests');
                console.log('  workflow  - Simulate complete threat detection workflow');
                console.log('  monitor   - Monitor contract events');
                console.log('  data      - Test Ocean Sentinel Data contract');
                console.log('  threats   - Test Threat Registry contract');
                console.log('  alerts    - Test Alert contract');
                break;
        }
        
    } catch (error) {
        console.error('💥 Command failed:', error.message);
        process.exit(1);
    }
}

// Export for use as module
module.exports = { ContractInteractor };

// Run if called directly
if (require.main === module) {
    main().catch(console.error);
}
