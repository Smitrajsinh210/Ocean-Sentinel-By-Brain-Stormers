/**
 * Ocean Sentinel - Blockchain Integration
 * Web3 and Starton blockchain verification client
 */

class BlockchainClient {
    constructor() {
        this.config = {
            startonApiKey: window.STARTON_API_KEY,
            contractAddress: window.CONTRACT_ADDRESS,
            network: window.BLOCKCHAIN_NETWORK || 'mumbai',
            startonBaseUrl: 'https://api.starton.io/v3'
        };
        
        this.cache = new Map();
        this.verificationQueue = [];
        this.isProcessingQueue = false;
        
        this.init();
    }
    
    async init() {
        console.log('⛓️ Initializing blockchain client...');
        
        // Verify configuration
        if (!this.config.startonApiKey || !this.config.contractAddress) {
            console.warn('⚠️ Blockchain configuration incomplete');
            return;
        }
        
        try {
            // Test connection to Starton API
            await this.testConnection();
            
            // Start processing verification queue
            this.startQueueProcessor();
            
            console.log('✅ Blockchain client initialized');
            
        } catch (error) {
            console.error('❌ Blockchain client initialization failed:', error);
        }
    }
    
    async testConnection() {
        const response = await fetch(`${this.config.startonBaseUrl}/smart-contract`, {
            headers: {
                'x-api-key': this.config.startonApiKey,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`Starton API connection failed: ${response.status}`);
        }
        
        console.log('✅ Starton API connection verified');
    }
    
    async verifyDataIntegrity(dataHash, showUI = true) {
        try {
            if (showUI) {
                this.showVerificationSpinner(dataHash);
            }
            
            // Check cache first
            const cacheKey = `verify_${dataHash}`;
            if (this.cache.has(cacheKey)) {
                const result = this.cache.get(cacheKey);
                if (showUI) {
                    this.showVerificationResult(dataHash, result);
                }
                return result;
            }
            
            // Call smart contract verification function
            const result = await this.callSmartContractRead(
                'verifyDataIntegrity',
                [dataHash]
            );
            
            const verificationResult = {
                verified: result?.verified || false,
                timestamp: result?.timestamp || null,
                blockNumber: result?.blockNumber || null,
                transactionHash: result?.transactionHash || null,
                source: result?.source || null
            };
            
            // Cache result
            this.cache.set(cacheKey, verificationResult);
            
            if (showUI) {
                this.showVerificationResult(dataHash, verificationResult);
            }
            
            return verificationResult;
            
        } catch (error) {
            console.error('Blockchain verification failed:', error);
            
            if (showUI) {
                this.showVerificationError(dataHash, error);
            }
            
            return { verified: false, error: error.message };
        }
    }
    
    async getAuditTrail(startDate, endDate, dataType = null) {
        try {
            const events = await this.getContractEvents('DataLogged', {
                fromBlock: 'earliest',
                toBlock: 'latest',
                limit: 1000
            });
            
            // Filter events by date range and type
            let filteredEvents = events.filter(event => {
                const eventDate = new Date(event.timestamp);
                return eventDate >= new Date(startDate) && eventDate <= new Date(endDate);
            });
            
            if (dataType) {
                filteredEvents = filteredEvents.filter(event => 
                    event.args?.dataType === dataType
                );
            }
            
            return filteredEvents.map(event => ({
                transactionHash: event.transactionHash,
                blockNumber: event.blockNumber,
                timestamp: event.timestamp,
                dataHash: event.args?.dataHash,
                source: event.args?.source,
                dataType: event.args?.dataType
            }));
            
        } catch (error) {
            console.error('Failed to get audit trail:', error);
            return [];
        }
    }
    
    async callSmartContractRead(functionName, params = []) {
        const url = `${this.config.startonBaseUrl}/smart-contract/${this.config.network}/${this.config.contractAddress}/read`;
        
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'x-api-key': this.config.startonApiKey,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                functionName,
                params
            })
        });
        
        if (!response.ok) {
            throw new Error(`Smart contract read failed: ${response.status}`);
        }
        
        return await response.json();
    }
    
    async getContractEvents(eventName, options = {}) {
        const url = `${this.config.startonBaseUrl}/smart-contract/${this.config.network}/${this.config.contractAddress}/events`;
        
        const queryParams = new URLSearchParams({
            eventName,
            ...options
        });
        
        const response = await fetch(`${url}?${queryParams}`, {
            headers: {
                'x-api-key': this.config.startonApiKey,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`Get contract events failed: ${response.status}`);
        }
        
        const data = await response.json();
        return data.items || [];
    }
    
    async getBulkVerificationStatus(dataHashes) {
        const results = [];
        
        for (const hash of dataHashes) {
            try {
                const result = await this.verifyDataIntegrity(hash, false);
                results.push({ hash, ...result });
            } catch (error) {
                results.push({ hash, verified: false, error: error.message });
            }
        }
        
        return results;
    }
    
    queueVerification(dataHash) {
        if (!this.verificationQueue.includes(dataHash)) {
            this.verificationQueue.push(dataHash);
        }
    }
    
    startQueueProcessor() {
        if (this.isProcessingQueue) return;
        
        this.isProcessingQueue = true;
        
        const processQueue = async () => {
            while (this.verificationQueue.length > 0) {
                const dataHash = this.verificationQueue.shift();
                try {
                    await this.verifyDataIntegrity(dataHash, false);
                    // Small delay to avoid rate limiting
                    await new Promise(resolve => setTimeout(resolve, 100));
                } catch (error) {
                    console.error(`Queue verification failed for ${dataHash}:`, error);
                }
            }
            
            // Check again after 30 seconds
            setTimeout(() => {
                if (this.verificationQueue.length > 0) {
                    processQueue();
                }
            }, 30000);
        };
        
        processQueue();
    }
    
    showVerificationSpinner(dataHash) {
        const shortHash = dataHash.substring(0, 8) + '...';
        
        // Create or update verification status element
        let statusElement = document.getElementById(`verification-${dataHash}`);
        if (!statusElement) {
            statusElement = document.createElement('div');
            statusElement.id = `verification-${dataHash}`;
            statusElement.className = 'blockchain-verification-status';
        }
        
        statusElement.innerHTML = `
            <div class="verification-item verifying">
                <span class="verification-icon">⏳</span>
                <span class="verification-text">Verifying ${shortHash}</span>
                <div class="verification-spinner"></div>
            </div>
        `;
        
        // Append to verification container or create one
        let container = document.getElementById('blockchain-verifications');
        if (!container) {
            container = document.createElement('div');
            container.id = 'blockchain-verifications';
            container.className = 'blockchain-verifications-container';
            document.body.appendChild(container);
        }
        
        container.appendChild(statusElement);
    }
    
    showVerificationResult(dataHash, result) {
        const shortHash = dataHash.substring(0, 8) + '...';
        const statusElement = document.getElementById(`verification-${dataHash}`);
        
        if (!statusElement) return;
        
        const isVerified = result.verified;
        const iconClass = isVerified ? 'verified' : 'unverified';
        const icon = isVerified ? '✅' : '❌';
        const status = isVerified ? 'Verified' : 'Not Found';
        
        statusElement.innerHTML = `
            <div class="verification-item ${iconClass}">
                <span class="verification-icon">${icon}</span>
                <span class="verification-text">${status}: ${shortHash}</span>
                ${isVerified ? `
                    <div class="verification-details">
                        <small>Block: ${result.blockNumber || 'N/A'}</small>
                        <small>Time: ${result.timestamp ? new Date(result.timestamp).toLocaleString() : 'N/A'}</small>
                    </div>
                ` : ''}
            </div>
        `;
        
        // Auto-remove after 5 seconds if verified, 10 seconds if not
        setTimeout(() => {
            if (statusElement.parentElement) {
                statusElement.remove();
            }
        }, isVerified ? 5000 : 10000);
    }
    
    showVerificationError(dataHash, error) {
        const shortHash = dataHash.substring(0, 8) + '...';
        const statusElement = document.getElementById(`verification-${dataHash}`);
        
        if (!statusElement) return;
        
        statusElement.innerHTML = `
            <div class="verification-item error">
                <span class="verification-icon">⚠️</span>
                <span class="verification-text">Error: ${shortHash}</span>
                <div class="verification-details">
                    <small>${error.message || 'Verification failed'}</small>
                </div>
            </div>
        `;
        
        // Auto-remove after 10 seconds
        setTimeout(() => {
            if (statusElement.parentElement) {
                statusElement.remove();
            }
        }, 10000);
    }
    
    async generateBlockchainReport(startDate, endDate) {
        try {
            const auditTrail = await this.getAuditTrail(startDate, endDate);
            
            const report = {
                period: { startDate, endDate },
                totalTransactions: auditTrail.length,
                dataTypes: {},
                sources: {},
                dailyStats: {},
                integrityScore: 100 // All blockchain data is verified by definition
            };
            
            // Analyze audit trail
            auditTrail.forEach(event => {
                // Count by data type
                const dataType = event.dataType || 'unknown';
                report.dataTypes[dataType] = (report.dataTypes[dataType] || 0) + 1;
                
                // Count by source
                const source = event.source || 'unknown';
                report.sources[source] = (report.sources[source] || 0) + 1;
                
                // Daily statistics
                const date = new Date(event.timestamp).toDateString();
                report.dailyStats[date] = (report.dailyStats[date] || 0) + 1;
            });
            
            return report;
            
        } catch (error) {
            console.error('Failed to generate blockchain report:', error);
            return null;
        }
    }
    
    createBlockchainWidget(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        const widget = document.createElement('div');
        widget.className = 'blockchain-widget';
        widget.innerHTML = `
            <div class="widget-header">
                <h3>🔗 Blockchain Integrity</h3>
                <span class="network-badge">${this.config.network}</span>
            </div>
            <div class="widget-content">
                <div class="integrity-status">
                    <div class="status-item">
                        <span class="status-label">Network:</span>
                        <span class="status-value network-status">Connected</span>
                    </div>
                    <div class="status-item">
                        <span class="status-label">Contract:</span>
                        <span class="status-value contract-address">${this.config.contractAddress.substring(0, 10)}...</span>
                    </div>
                    <div class="status-item">
                        <span class="status-label">Verified Records:</span>
                        <span class="status-value verified-count">Loading...</span>
                    </div>
                </div>
                <div class="widget-actions">
                    <button onclick="blockchainClient.showAuditTrail()">View Audit Trail</button>
                    <button onclick="blockchainClient.verifyCurrentData()">Verify Data</button>
                </div>
            </div>
        `;
        
        container.appendChild(widget);
        
        // Update verified count
        this.updateVerifiedCount();
    }
    
    async updateVerifiedCount() {
        try {
            const events = await this.getContractEvents('DataLogged', {
                fromBlock: 'latest-100',
                limit: 100
            });
            
            const countElement = document.querySelector('.verified-count');
            if (countElement) {
                countElement.textContent = events.length.toString();
            }
            
        } catch (error) {
            console.error('Failed to update verified count:', error);
        }
    }
    
    async showAuditTrail() {
        const endDate = new Date();
        const startDate = new Date(endDate.getTime() - 7 * 24 * 60 * 60 * 1000); // 7 days ago
        
        const auditTrail = await this.getAuditTrail(startDate, endDate);
        
        // Create modal with audit trail
        const modal = document.createElement('div');
        modal.className = 'blockchain-modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h2>Blockchain Audit Trail</h2>
                    <button class="close-modal" onclick="this.parentElement.parentElement.parentElement.remove()">×</button>
                </div>
                <div class="modal-body">
                    <div class="audit-summary">
                        <p><strong>Period:</strong> ${startDate.toDateString()} - ${endDate.toDateString()}</p>
                        <p><strong>Total Transactions:</strong> ${auditTrail.length}</p>
                    </div>
                    <div class="audit-table">
                        <table>
                            <thead>
                                <tr>
                                    <th>Time</th>
                                    <th>Data Hash</th>
                                    <th>Source</th>
                                    <th>Transaction</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${auditTrail.slice(0, 50).map(event => `
                                    <tr>
                                        <td>${new Date(event.timestamp).toLocaleString()}</td>
                                        <td>${event.dataHash?.substring(0, 10)}...</td>
                                        <td>${event.source}</td>
                                        <td>
                                            <a href="https://mumbai.polygonscan.com/tx/${event.transactionHash}" 
                                               target="_blank">${event.transactionHash?.substring(0, 10)}...</a>
                                        </td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
    }
    
    async verifyCurrentData() {
        if (window.dashboard?.state?.environmentalData) {
            const dataHash = window.dashboard.state.environmentalData.data_hash;
            if (dataHash) {
                await this.verifyDataIntegrity(dataHash, true);
            }
        }
    }
    
    cleanup() {
        console.log('🧹 Cleaning up blockchain client...');
        this.cache.clear();
        this.verificationQueue = [];
        this.isProcessingQueue = false;
    }
}

// Global blockchain client instance
window.blockchainClient = new BlockchainClient();

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.blockchainClient) {
        window.blockchainClient.cleanup();
    }
});
