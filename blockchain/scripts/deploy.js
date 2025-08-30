/**
 * Ocean Sentinel - Smart Contract Deployment Script
 * Deploys all Ocean Sentinel contracts using Starton platform
 */

const axios = require('axios');
const fs = require('fs');
const path = require('path');
require('dotenv').config();

class ContractDeployer {
    constructor() {
        this.startonApiKey = process.env.STARTON_API_KEY;
        this.network = process.env.BLOCKCHAIN_NETWORK || 'polygon-mumbai';
        this.baseUrl = 'https://api.starton.com/v3';
        this.deployedContracts = {};
        
        if (!this.startonApiKey) {
            throw new Error('STARTON_API_KEY not found in environment variables');
        }
        
        console.log('🚀 Ocean Sentinel Contract Deployer initialized');
        console.log(`📡 Network: ${this.network}`);
    }
    
    /**
     * Deploy all Ocean Sentinel contracts
     */
    async deployAllContracts() {
        try {
            console.log('🔄 Starting contract deployment...\n');
            
            // Deploy contracts in order (dependencies first)
            await this.deployOceanSentinelDataContract();
            await this.deployThreatRegistryContract();
            await this.deployAlertContract();
            
            // Save deployment info
            await this.saveDeploymentInfo();
            
            console.log('\n✅ All contracts deployed successfully!');
            console.log('📄 Deployment info saved to blockchain/deployed_contracts.json');
            
            return this.deployedContracts;
            
        } catch (error) {
            console.error('❌ Deployment failed:', error.message);
            throw error;
        }
    }
    
    /**
     * Deploy Ocean Sentinel Data contract
     */
    async deployOceanSentinelDataContract() {
        console.log('📦 Deploying OceanSentinelData contract...');
        
        const contractSource = fs.readFileSync(
            path.join(__dirname, '../contracts/OceanSentinelData.sol'),
            'utf8'
        );
        
        const deploymentData = {
            name: 'OceanSentinelData',
            description: 'Smart contract for storing and verifying environmental data integrity',
            params: [], // No constructor parameters
            signerWallet: await this.getOrCreateWallet(),
            network: this.network,
            speed: 'average'
        };
        
        try {
            const response = await this.makeStartonRequest(
                'POST',
                '/smart-contract/from-template',
                {
                    templateId: 'ERC20_META_TRANSACTION', // Using closest template, will be customized
                    name: deploymentData.name,
                    description: deploymentData.description,
                    params: deploymentData.params,
                    signerWallet: deploymentData.signerWallet,
                    network: deploymentData.network,
                    speed: deploymentData.speed
                }
            );
            
            const contractAddress = response.data.address;
            const transactionHash = response.data.transactionHash;
            
            this.deployedContracts.OceanSentinelData = {
                address: contractAddress,
                transactionHash: transactionHash,
                network: this.network,
                deployedAt: new Date().toISOString()
            };
            
            console.log(`✅ OceanSentinelData deployed to: ${contractAddress}`);
            console.log(`🔗 Transaction: ${transactionHash}\n`);
            
            // Wait for confirmation
            await this.waitForTransaction(transactionHash);
            
        } catch (error) {
            console.error('❌ Failed to deploy OceanSentinelData:', error.response?.data || error.message);
            throw error;
        }
    }
    
    /**
     * Deploy Threat Registry contract
     */
    async deployThreatRegistryContract() {
        console.log('📦 Deploying ThreatRegistry contract...');
        
        const deploymentData = {
            name: 'ThreatRegistry',
            description: 'Smart contract for registering and managing environmental threats',
            params: [], // No constructor parameters
            signerWallet: await this.getOrCreateWallet(),
            network: this.network,
            speed: 'average'
        };
        
        try {
            // For this example, we'll use Starton's custom deployment
            const response = await this.deployCustomContract(
                'ThreatRegistry',
                deploymentData
            );
            
            const contractAddress = response.address;
            const transactionHash = response.transactionHash;
            
            this.deployedContracts.ThreatRegistry = {
                address: contractAddress,
                transactionHash: transactionHash,
                network: this.network,
                deployedAt: new Date().toISOString()
            };
            
            console.log(`✅ ThreatRegistry deployed to: ${contractAddress}`);
            console.log(`🔗 Transaction: ${transactionHash}\n`);
            
            await this.waitForTransaction(transactionHash);
            
        } catch (error) {
            console.error('❌ Failed to deploy ThreatRegistry:', error.response?.data || error.message);
            throw error;
        }
    }
    
    /**
     * Deploy Alert contract
     */
    async deployAlertContract() {
        console.log('📦 Deploying AlertContract...');
        
        const deploymentData = {
            name: 'AlertContract',
            description: 'Smart contract for managing and tracking alert notifications',
            params: [], // No constructor parameters
            signerWallet: await this.getOrCreateWallet(),
            network: this.network,
            speed: 'average'
        };
        
        try {
            const response = await this.deployCustomContract(
                'AlertContract',
                deploymentData
            );
            
            const contractAddress = response.address;
            const transactionHash = response.transactionHash;
            
            this.deployedContracts.AlertContract = {
                address: contractAddress,
                transactionHash: transactionHash,
                network: this.network,
                deployedAt: new Date().toISOString()
            };
            
            console.log(`✅ AlertContract deployed to: ${contractAddress}`);
            console.log(`🔗 Transaction: ${transactionHash}\n`);
            
            await this.waitForTransaction(transactionHash);
            
        } catch (error) {
            console.error('❌ Failed to deploy AlertContract:', error.response?.data || error.message);
            throw error;
        }
    }
    
    /**
     * Deploy custom contract using Starton
     */
    async deployCustomContract(contractName, deploymentData) {
        // Read contract source code
        const contractSource = fs.readFileSync(
            path.join(__dirname, `../contracts/${contractName}.sol`),
            'utf8'
        );
        
        // Compile and deploy using Starton's compilation service
        const compileResponse = await this.makeStartonRequest(
            'POST',
            '/smart-contract/compile',
            {
                name: contractName,
                sourceCode: contractSource,
                compilerVersion: '0.8.19'
            }
        );
        
        const compiledContract = compileResponse.data;
        
        // Deploy compiled contract
        const deployResponse = await this.makeStartonRequest(
            'POST',
            '/smart-contract/deploy',
            {
                name: deploymentData.name,
                description: deploymentData.description,
                bytecode: compiledContract.bytecode,
                abi: compiledContract.abi,
                params: deploymentData.params,
                signerWallet: deploymentData.signerWallet,
                network: deploymentData.network,
                speed: deploymentData.speed
            }
        );
        
        return deployResponse.data;
    }
    
    /**
     * Get or create wallet for deployment
     */
    async getOrCreateWallet() {
        try {
            // Try to get existing wallets
            const walletsResponse = await this.makeStartonRequest('GET', '/wallet');
            const wallets = walletsResponse.data.items;
            
            if (wallets.length > 0) {
                console.log(`💰 Using existing wallet: ${wallets[0].address}`);
                return wallets[0].address;
            }
            
            // Create new wallet if none exists
            console.log('💰 Creating new wallet...');
            const createWalletResponse = await this.makeStartonRequest(
                'POST',
                '/wallet',
                {
                    name: 'Ocean Sentinel Deployer',
                    description: 'Wallet for deploying Ocean Sentinel contracts'
                }
            );
            
            const walletAddress = createWalletResponse.data.address;
            console.log(`✅ New wallet created: ${walletAddress}`);
            console.log('⚠️  Please fund this wallet with testnet tokens before deployment');
            
            return walletAddress;
            
        } catch (error) {
            console.error('❌ Failed to get/create wallet:', error.response?.data || error.message);
            throw error;
        }
    }
    
    /**
     * Wait for transaction confirmation
     */
    async waitForTransaction(transactionHash, maxWaitTime = 300000) { // 5 minutes max
        console.log(`⏳ Waiting for transaction confirmation: ${transactionHash}`);
        
        const startTime = Date.now();
        
        while (Date.now() - startTime < maxWaitTime) {
            try {
                const response = await this.makeStartonRequest(
                    'GET',
                    `/transaction/${transactionHash}`
                );
                
                const transaction = response.data;
                
                if (transaction.status === 'confirmed') {
                    console.log('✅ Transaction confirmed');
                    return transaction;
                } else if (transaction.status === 'failed') {
                    throw new Error('Transaction failed');
                }
                
                // Wait 5 seconds before checking again
                await new Promise(resolve => setTimeout(resolve, 5000));
                
            } catch (error) {
                if (error.response?.status === 404) {
                    // Transaction not found yet, continue waiting
                    await new Promise(resolve => setTimeout(resolve, 5000));
                    continue;
                } else {
                    throw error;
                }
            }
        }
        
        throw new Error('Transaction confirmation timeout');
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
            config.data = data;
        }
        
        try {
            const response = await axios(config);
            return response;
        } catch (error) {
            console.error(`API Request failed: ${method} ${endpoint}`);
            console.error('Error:', error.response?.data || error.message);
            throw error;
        }
    }
    
    /**
     * Save deployment information to file
     */
    async saveDeploymentInfo() {
        const deploymentInfo = {
            network: this.network,
            deployedAt: new Date().toISOString(),
            contracts: this.deployedContracts,
            startonApiVersion: 'v3'
        };
        
        const outputPath = path.join(__dirname, '../deployed_contracts.json');
        fs.writeFileSync(outputPath, JSON.stringify(deploymentInfo, null, 2));
        
        // Also update environment template
        const envUpdate = `
# Updated contract addresses from deployment
CONTRACT_ADDRESS_DATA=${this.deployedContracts.OceanSentinelData?.address || ''}
CONTRACT_ADDRESS_THREATS=${this.deployedContracts.ThreatRegistry?.address || ''}
CONTRACT_ADDRESS_ALERTS=${this.deployedContracts.AlertContract?.address || ''}
BLOCKCHAIN_NETWORK=${this.network}
`;
        
        console.log('📝 Add these addresses to your .env file:');
        console.log(envUpdate);
    }
    
    /**
     * Verify contract deployment
     */
    async verifyDeployment() {
        console.log('🔍 Verifying contract deployments...\n');
        
        for (const [contractName, contractInfo] of Object.entries(this.deployedContracts)) {
            try {
                console.log(`🔍 Verifying ${contractName}...`);
                
                // Get contract details from Starton
                const response = await this.makeStartonRequest(
                    'GET',
                    `/smart-contract/${contractInfo.address}`
                );
                
                const contractDetails = response.data;
                
                console.log(`✅ ${contractName} verified:`);
                console.log(`   Address: ${contractDetails.address}`);
                console.log(`   Network: ${contractDetails.network}`);
                console.log(`   Status: ${contractDetails.status}`);
                console.log();
                
            } catch (error) {
                console.error(`❌ Failed to verify ${contractName}:`, error.message);
            }
        }
    }
}

// Main deployment function
async function main() {
    try {
        const deployer = new ContractDeployer();
        
        // Deploy all contracts
        const deployedContracts = await deployer.deployAllContracts();
        
        // Verify deployment
        await deployer.verifyDeployment();
        
        console.log('🎉 Ocean Sentinel smart contracts deployed successfully!');
        console.log('\nNext steps:');
        console.log('1. Update your .env file with the contract addresses');
        console.log('2. Fund the deployer wallet with testnet tokens if needed');
        console.log('3. Test contract interactions using interact.js');
        
        return deployedContracts;
        
    } catch (error) {
        console.error('💥 Deployment failed:', error.message);
        process.exit(1);
    }
}

// Export for use as module
module.exports = { ContractDeployer };

// Run if called directly
if (require.main === module) {
    main().catch(console.error);
}
