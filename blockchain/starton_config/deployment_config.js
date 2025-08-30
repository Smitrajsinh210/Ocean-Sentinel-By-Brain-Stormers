/**
 * Ocean Sentinel - Starton Deployment Configuration
 * Specific deployment configuration for Starton blockchain platform
 */

const StartonDeploymentConfig = {
    // Starton Platform Configuration
    starton: {
        api: {
            base_url: 'https://api.starton.com/v3',
            api_key: process.env.STARTON_API_KEY,
            timeout: 30000,
            max_retries: 3,
            retry_delay: 2000
        },
        
        // Starton Wallet Configuration
        wallet: {
            create_if_missing: true,
            wallet_name: 'Ocean Sentinel Deployer',
            wallet_description: 'Primary deployment wallet for Ocean Sentinel contracts',
            backup_phrase_required: false,
            auto_fund_testnet: false,
            minimum_balance_check: true
        },
        
        // Starton Smart Contract Deployment
        smart_contracts: {
            compilation_service: true,
            automatic_verification: true,
            save_artifacts: true,
            generate_typescript_types: false
        }
    },
    
    // Network Configuration for Starton
    networks: {
        'polygon-mumbai': {
            starton_network_id: 'polygon-mumbai',
            display_name: 'Polygon Mumbai Testnet',
            chain_id: 80001,
            native_currency: 'MATIC',
            block_explorer: 'https://mumbai.polygonscan.com',
            rpc_endpoint: 'https://rpc-mumbai.maticvigil.com',
            is_testnet: true,
            
            // Starton-specific gas configuration
            gas_configuration: {
                gas_price_strategy: 'average', // slow, average, fast, fastest
                gas_limit_multiplier: 1.2,
                max_gas_price: '30000000000', // 30 Gwei
                min_gas_price: '1000000000',  // 1 Gwei
                priority_fee: 'auto'
            },
            
            // Required balance for deployment
            required_balance: {
                amount: '0.1',
                currency: 'MATIC',
                check_before_deployment: true
            },
            
            // Starton webhook configuration
            webhooks: {
                enabled: true,
                base_url: process.env.WEBHOOK_BASE_URL || 'https://your-api.vercel.app',
                authentication: {
                    method: 'bearer',
                    token: process.env.STARTON_WEBHOOK_TOKEN
                }
            }
        },
        
        'ethereum-goerli': {
            starton_network_id: 'ethereum-goerli',
            display_name: 'Ethereum Goerli Testnet',
            chain_id: 5,
            native_currency: 'ETH',
            block_explorer: 'https://goerli.etherscan.io',
            rpc_endpoint: process.env.GOERLI_RPC_URL || 'https://goerli.infura.io/v3/',
            is_testnet: true,
            
            gas_configuration: {
                gas_price_strategy: 'average',
                gas_limit_multiplier: 1.3,
                max_gas_price: '50000000000', // 50 Gwei
                min_gas_price: '1000000000',  // 1 Gwei
                priority_fee: 'auto'
            },
            
            required_balance: {
                amount: '0.05',
                currency: 'ETH',
                check_before_deployment: true
            },
            
            webhooks: {
                enabled: true,
                base_url: process.env.WEBHOOK_BASE_URL || 'https://your-api.vercel.app',
                authentication: {
                    method: 'bearer',
                    token: process.env.STARTON_WEBHOOK_TOKEN
                }
            }
        }
    },
    
    // Contract Deployment Sequence
    deployment_sequence: [
        {
            contract_name: 'OceanSentinelData',
            order: 1,
            starton_config: {
                template_id: 'custom_data_storage',
                constructor_params: [],
                gas_limit: 3000000,
                gas_price_strategy: 'average',
                
                // Post-deployment initialization calls
                initialization_calls: [
                    {
                        function_name: 'addAuthorizedLogger',
                        params: ['{{DEPLOYER_ADDRESS}}'],
                        gas_limit: 100000,
                        required: true,
                        description: 'Add deployer as authorized logger'
                    },
                    {
                        function_name: 'addAuthorizedVerifier', 
                        params: ['{{DEPLOYER_ADDRESS}}'],
                        gas_limit: 100000,
                        required: true,
                        description: 'Add deployer as authorized verifier'
                    }
                ],
                
                // Event monitoring setup
                event_monitoring: {
                    events: ['DataLogged', 'DataVerified'],
                    webhook_url: '{{WEBHOOK_BASE_URL}}/starton/ocean-sentinel-data',
                    notification_channels: ['webhook', 'email']
                }
            }
        },
        
        {
            contract_name: 'ThreatRegistry',
            order: 2,
            depends_on: ['OceanSentinelData'],
            starton_config: {
                template_id: 'custom_threat_registry',
                constructor_params: [],
                gas_limit: 4000000,
                gas_price_strategy: 'average',
                
                initialization_calls: [
                    {
                        function_name: 'addAuthorizedReporter',
                        params: ['{{DEPLOYER_ADDRESS}}'],
                        gas_limit: 100000,
                        required: true,
                        description: 'Add deployer as authorized threat reporter'
                    },
                    {
                        function_name: 'addAuthorizedVerifier',
                        params: ['{{DEPLOYER_ADDRESS}}'],
                        gas_limit: 100000,
                        required: true,
                        description: 'Add deployer as authorized threat verifier'
                    }
                ],
                
                event_monitoring: {
                    events: ['ThreatRegistered', 'ThreatStatusUpdated', 'ThreatVerified'],
                    webhook_url: '{{WEBHOOK_BASE_URL}}/starton/threat-registry',
                    notification_channels: ['webhook', 'email', 'sms']
                }
            }
        },
        
        {
            contract_name: 'AlertContract',
            order: 3,
            depends_on: ['ThreatRegistry'],
            starton_config: {
                template_id: 'custom_alert_system',
                constructor_params: [],
                gas_limit: 2500000,
                gas_price_strategy: 'fast', // Alerts need faster deployment
                
                initialization_calls: [
                    {
                        function_name: 'addAuthorizedSender',
                        params: ['{{DEPLOYER_ADDRESS}}'],
                        gas_limit: 100000,
                        required: true,
                        description: 'Add deployer as authorized alert sender'
                    },
                    {
                        function_name: 'setEmergencyThreshold',
                        params: [4], // Severity 4 and above are emergencies
                        gas_limit: 80000,
                        required: true,
                        description: 'Set emergency alert threshold'
                    }
                ],
                
                event_monitoring: {
                    events: ['AlertCreated', 'AlertStatusUpdated', 'AlertDelivered', 'EmergencyAlert'],
                    webhook_url: '{{WEBHOOK_BASE_URL}}/starton/alert-contract',
                    notification_channels: ['webhook', 'email', 'sms', 'push']
                }
            }
        }
    ],
    
    // Starton-specific deployment strategies
    deployment_strategies: {
        development: {
            network: 'polygon-mumbai',
            gas_price_strategy: 'slow',
            confirmation_blocks: 1,
            enable_monitoring: false,
            save_deployment_artifacts: true,
            auto_verify_contracts: false,
            webhook_notifications: false
        },
        
        staging: {
            network: 'polygon-mumbai',
            gas_price_strategy: 'average',
            confirmation_blocks: 2,
            enable_monitoring: true,
            save_deployment_artifacts: true,
            auto_verify_contracts: true,
            webhook_notifications: true
        },
        
        production: {
            network: 'polygon-mumbai', // Will be mainnet when ready
            gas_price_strategy: 'fast',
            confirmation_blocks: 5,
            enable_monitoring: true,
            save_deployment_artifacts: true,
            auto_verify_contracts: true,
            webhook_notifications: true,
            require_manual_approval: true
        }
    },
    
    // Starton Webhook Configuration
    webhook_config: {
        enabled: process.env.ENABLE_STARTON_WEBHOOKS === 'true',
        base_url: process.env.WEBHOOK_BASE_URL,
        authentication: {
            type: 'bearer',
            token: process.env.STARTON_WEBHOOK_TOKEN
        },
        
        // Webhook endpoints for each contract event
        endpoints: {
            // Ocean Sentinel Data Contract
            'DataLogged': {
                url: '/api/webhooks/starton/data-logged',
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Ocean-Sentinel-Event': 'DataLogged'
                }
            },
            'DataVerified': {
                url: '/api/webhooks/starton/data-verified',
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Ocean-Sentinel-Event': 'DataVerified'
                }
            },
            
            // Threat Registry Contract
            'ThreatRegistered': {
                url: '/api/webhooks/starton/threat-registered',
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Ocean-Sentinel-Event': 'ThreatRegistered'
                },
                priority: 'high'
            },
            'ThreatStatusUpdated': {
                url: '/api/webhooks/starton/threat-status-updated',
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Ocean-Sentinel-Event': 'ThreatStatusUpdated'
                }
            },
            'ThreatVerified': {
                url: '/api/webhooks/starton/threat-verified',
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Ocean-Sentinel-Event': 'ThreatVerified'
                }
            },
            
            // Alert Contract
            'AlertCreated': {
                url: '/api/webhooks/starton/alert-created',
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Ocean-Sentinel-Event': 'AlertCreated'
                },
                priority: 'critical'
            },
            'AlertStatusUpdated': {
                url: '/api/webhooks/starton/alert-status-updated',
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Ocean-Sentinel-Event': 'AlertStatusUpdated'
                }
            },
            'AlertDelivered': {
                url: '/api/webhooks/starton/alert-delivered',
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Ocean-Sentinel-Event': 'AlertDelivered'
                }
            },
            'EmergencyAlert': {
                url: '/api/webhooks/starton/emergency-alert',
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Ocean-Sentinel-Event': 'EmergencyAlert'
                },
                priority: 'critical'
            }
        },
        
        // Webhook retry configuration
        retry_config: {
            max_retries: 3,
            initial_delay: 1000, // 1 second
            exponential_backoff: true,
            max_delay: 30000 // 30 seconds
        }
    },
    
    // Starton Monitoring and Alerts
    monitoring: {
        enabled: true,
        starton_dashboard_integration: true,
        
        // Performance metrics
        metrics: {
            deployment_time: true,
            gas_usage: true,
            transaction_success_rate: true,
            event_frequency: true,
            webhook_delivery_rate: true
        },
        
        // Alert conditions
        alerts: {
            deployment_failure: {
                enabled: true,
                notification_channels: ['email', 'webhook']
            },
            high_gas_usage: {
                enabled: true,
                threshold: 5000000, // 5M gas
                notification_channels: ['email']
            },
            webhook_failure: {
                enabled: true,
                threshold: 3, // 3 consecutive failures
                notification_channels: ['email', 'sms']
            },
            contract_interaction_failure: {
                enabled: true,
                threshold: 5, // 5 failures in 1 hour
                window: 3600, // 1 hour
                notification_channels: ['email', 'webhook']
            }
        }
    },
    
    // Environment-specific overrides for Starton
    environments: {
        development: {
            starton: {
                wallet: {
                    auto_fund_testnet: true
                }
            },
            webhook_config: {
                enabled: false
            },
            monitoring: {
                enabled: false
            }
        },
        
        production: {
            starton: {
                smart_contracts: {
                    automatic_verification: true,
                    generate_typescript_types: true
                }
            },
            webhook_config: {
                enabled: true,
                retry_config: {
                    max_retries: 5,
                    max_delay: 60000 // 1 minute
                }
            },
            monitoring: {
                enabled: true,
                starton_dashboard_integration: true
            }
        }
    },
    
    // Integration Configuration
    integration: {
        // Backend API integration
        backend_integration: {
            update_env_file: true,
            env_file_path: '../backend/.env',
            contract_address_prefix: 'CONTRACT_ADDRESS_',
            abi_output_path: '../backend/app/abis/'
        },
        
        // Frontend integration
        frontend_integration: {
            generate_typescript_types: true,
            types_output_path: '../frontend/types/contracts.ts',
            abi_output_path: '../frontend/src/abis/',
            update_config_file: true,
            config_file_path: '../frontend/src/config/contracts.ts'
        }
    },
    
    // Security Configuration for Starton
    security: {
        // Access control
        access_control: {
            multi_sig_deployment: false, // Set to true for production
            deployer_key_rotation: false,
            api_key_rotation_days: 90
        },
        
        // Contract security
        contract_security: {
            enable_pause_functionality: false,
            enable_upgrade_functionality: false,
            audit_required: process.env.NODE_ENV === 'production',
            formal_verification: false
        },
        
        // API security
        api_security: {
            rate_limiting: true,
            ip_whitelisting: false,
            webhook_signature_verification: true
        }
    }
};

// Helper Functions for Starton Configuration
const StartonHelpers = {
    /**
     * Get current deployment strategy
     */
    getCurrentStrategy() {
        const env = process.env.NODE_ENV || 'development';
        return StartonDeploymentConfig.deployment_strategies[env] || 
               StartonDeploymentConfig.deployment_strategies.development;
    },
    
    /**
     * Get network configuration for Starton
     */
    getNetworkConfig(networkName) {
        const strategy = this.getCurrentStrategy();
        const network = networkName || strategy.network;
        return StartonDeploymentConfig.networks[network];
    },
    
    /**
     * Get contracts in deployment order
     */
    getDeploymentSequence() {
        return StartonDeploymentConfig.deployment_sequence.sort((a, b) => a.order - b.order);
    },
    
    /**
     * Replace template variables in configuration
     */
    replaceTemplateVariables(config, variables) {
        const configStr = JSON.stringify(config);
        let replacedStr = configStr;
        
        Object.entries(variables).forEach(([key, value]) => {
            const regex = new RegExp(`{{${key}}}`, 'g');
            replacedStr = replacedStr.replace(regex, value);
        });
        
        return JSON.parse(replacedStr);
    },
    
    /**
     * Validate Starton configuration
     */
    validateConfig() {
        const errors = [];
        
        // Check required environment variables
        if (!process.env.STARTON_API_KEY) {
            errors.push('STARTON_API_KEY environment variable is required');
        }
        
        if (StartonDeploymentConfig.webhook_config.enabled) {
            if (!process.env.WEBHOOK_BASE_URL) {
                errors.push('WEBHOOK_BASE_URL required when webhooks are enabled');
            }
            if (!process.env.STARTON_WEBHOOK_TOKEN) {
                errors.push('STARTON_WEBHOOK_TOKEN required when webhooks are enabled');
            }
        }
        
        // Validate deployment sequence
        const sequence = this.getDeploymentSequence();
        const orders = sequence.map(s => s.order);
        const uniqueOrders = [...new Set(orders)];
        if (orders.length !== uniqueOrders.length) {
            errors.push('Duplicate deployment order numbers found');
        }
        
        return errors;
    },
    
    /**
     * Generate Starton deployment summary
     */
    generateDeploymentSummary(deploymentResults) {
        return {
            platform: 'Starton',
            timestamp: new Date().toISOString(),
            network: this.getCurrentStrategy().network,
            contracts: deploymentResults.contracts || {},
            total_gas_used: Object.values(deploymentResults.contracts || {})
                .reduce((sum, contract) => sum + (contract.gasUsed || 0), 0),
            webhook_endpoints: Object.keys(StartonDeploymentConfig.webhook_config.endpoints).length,
            monitoring_enabled: StartonDeploymentConfig.monitoring.enabled,
            security_features: {
                multi_sig: StartonDeploymentConfig.security.access_control.multi_sig_deployment,
                audit_required: StartonDeploymentConfig.security.contract_security.audit_required,
                webhook_verification: StartonDeploymentConfig.security.api_security.webhook_signature_verification
            }
        };
    }
};

// Export configuration and helpers
module.exports = {
    ...StartonDeploymentConfig,
    helpers: StartonHelpers
};

// Validate configuration on load
if (require.main === module) {
    const errors = StartonHelpers.validateConfig();
    if (errors.length > 0) {
        console.error('❌ Starton deployment configuration validation errors:');
        errors.forEach(error => console.error(`   - ${error}`));
        process.exit(1);
    } else {
        console.log('✅ Starton deployment configuration is valid');
        
        // Show configuration summary
        const strategy = StartonHelpers.getCurrentStrategy();
        console.log('\n🚀 Starton Deployment Configuration Summary:');
        console.log(`   Platform: Starton v3`);
        console.log(`   Network: ${strategy.network}`);
        console.log(`   Strategy: ${process.env.NODE_ENV || 'development'}`);
        console.log(`   Contracts: ${StartonDeploymentConfig.deployment_sequence.length}`);
        console.log(`   Webhooks: ${StartonDeploymentConfig.webhook_config.enabled ? 'Enabled' : 'Disabled'}`);
        console.log(`   Monitoring: ${StartonDeploymentConfig.monitoring.enabled ? 'Enabled' : 'Disabled'}`);
    }
}
