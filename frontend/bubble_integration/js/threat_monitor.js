/**
 * Ocean Sentinel - Threat Monitor
 * Real-time threat monitoring and detection system
 */

class ThreatMonitor {
    constructor() {
        this.isMonitoring = false;
        this.monitoringInterval = null;
        this.detectionModels = new Map();
        this.thresholds = {
            storm: { severity: 3, confidence: 0.7 },
            pollution: { severity: 2, confidence: 0.6 },
            erosion: { severity: 2, confidence: 0.5 },
            algal_bloom: { severity: 3, confidence: 0.8 },
            illegal_dumping: { severity: 1, confidence: 0.9 },
            anomaly: { severity: 2, confidence: 0.6 }
        };
        
        this.config = {
            monitoringInterval: 30000, // 30 seconds
            apiTimeout: 15000,
            maxRetries: 3,
            batchSize: 10
        };
        
        this.stats = {
            totalChecks: 0,
            threatsDetected: 0,
            falsePositives: 0,
            avgResponseTime: 0,
            lastCheck: null
        };
        
        this.init();
    }
    
    async init() {
        console.log('🔍 Initializing Threat Monitor...');
        
        try {
            await this.loadDetectionModels();
            this.setupEventListeners();
            console.log('✅ Threat Monitor initialized');
        } catch (error) {
            console.error('❌ Failed to initialize Threat Monitor:', error);
        }
    }
    
    async loadDetectionModels() {
        console.log('🤖 Loading AI detection models...');
        
        try {
            // Load TensorFlow.js models for client-side prediction
            const modelUrls = {
                storm: '/models/storm_detection.json',
                pollution: '/models/pollution_detection.json',
                erosion: '/models/erosion_detection.json'
            };
            
            for (const [type, url] of Object.entries(modelUrls)) {
                try {
                    const model = await tf.loadLayersModel(url);
                    this.detectionModels.set(type, model);
                    console.log(`✅ Loaded ${type} detection model`);
                } catch (error) {
                    console.warn(`⚠️ Failed to load ${type} model:`, error);
                }
            }
            
            console.log(`🤖 Loaded ${this.detectionModels.size} AI models`);
            
        } catch (error) {
            console.error('Failed to load detection models:', error);
        }
    }
    
    setupEventListeners() {
        // Listen for manual monitoring toggle
        document.addEventListener('toggleMonitoring', (event) => {
            if (event.detail.enabled) {
                this.startMonitoring();
            } else {
                this.stopMonitoring();
            }
        });
        
        // Listen for threshold updates
        document.addEventListener('updateThresholds', (event) => {
            this.updateThresholds(event.detail.thresholds);
        });
        
        // Listen for real-time data updates
        if (window.realTimeManager) {
            window.realTimeManager.on('environmental:updated', (data) => {
                this.processEnvironmentalData(data);
            });
        }
    }
    
    startMonitoring() {
        if (this.isMonitoring) {
            console.warn('⚠️ Monitoring already active');
            return;
        }
        
        console.log('🔍 Starting threat monitoring...');
        this.isMonitoring = true;
        
        // Start periodic monitoring
        this.monitoringInterval = setInterval(() => {
            this.performThreatCheck();
        }, this.config.monitoringInterval);
        
        // Perform initial check
        this.performThreatCheck();
        
        // Update UI
        this.updateMonitoringUI(true);
        
        console.log('✅ Threat monitoring started');
    }
    
    stopMonitoring() {
        if (!this.isMonitoring) {
            console.warn('⚠️ Monitoring not active');
            return;
        }
        
        console.log('🛑 Stopping threat monitoring...');
        this.isMonitoring = false;
        
        if (this.monitoringInterval) {
            clearInterval(this.monitoringInterval);
            this.monitoringInterval = null;
        }
        
        // Update UI
        this.updateMonitoringUI(false);
        
        console.log('✅ Threat monitoring stopped');
    }
    
    async performThreatCheck() {
        const checkStart = Date.now();
        
        try {
            console.log('🔍 Performing threat detection check...');
            
            // Fetch latest environmental data
            const environmentalData = await this.fetchEnvironmentalData();
            
            if (!environmentalData) {
                console.warn('⚠️ No environmental data available');
                return;
            }
            
            // Run AI-powered threat detection
            const detectedThreats = await this.runThreatDetection(environmentalData);
            
            // Process detected threats
            if (detectedThreats.length > 0) {
                await this.processThreatDetections(detectedThreats);
            }
            
            // Update statistics
            this.updateStats(checkStart, detectedThreats.length);
            
            console.log(`✅ Threat check completed - ${detectedThreats.length} threats detected`);
            
        } catch (error) {
            console.error('❌ Threat check failed:', error);
            this.handleMonitoringError(error);
        }
    }
    
    async fetchEnvironmentalData() {
        try {
            const response = await fetch('/api/v1/data/latest', {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${window.dashboard?.state?.authToken}`,
                    'Content-Type': 'application/json'
                },
                timeout: this.config.apiTimeout
            });
            
            if (!response.ok) {
                throw new Error(`API error: ${response.status}`);
            }
            
            const data = await response.json();
            return data.data;
            
        } catch (error) {
            console.error('Failed to fetch environmental data:', error);
            return null;
        }
    }
    
    async runThreatDetection(environmentalData) {
        const threats = [];
        
        try {
            // Run server-side AI detection
            const serverThreats = await this.runServerDetection(environmentalData);
            threats.push(...serverThreats);
            
            // Run client-side AI detection if models are available
            if (this.detectionModels.size > 0) {
                const clientThreats = await this.runClientDetection(environmentalData);
                threats.push(...clientThreats);
            }
            
            // Remove duplicates and apply thresholds
            return this.filterAndValidateThreats(threats);
            
        } catch (error) {
            console.error('Threat detection failed:', error);
            return [];
        }
    }
    
    async runServerDetection(environmentalData) {
        try {
            const response = await fetch('/api/v1/threats/detect', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${window.dashboard?.state?.authToken}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ data: environmentalData }),
                timeout: this.config.apiTimeout
            });
            
            if (!response.ok) {
                throw new Error(`Detection API error: ${response.status}`);
            }
            
            const result = await response.json();
            return result.threats || [];
            
        } catch (error) {
            console.error('Server-side detection failed:', error);
            return [];
        }
    }
    
    async runClientDetection(environmentalData) {
        const threats = [];
        
        try {
            // Prepare input tensors
            const inputTensor = this.prepareInputTensor(environmentalData);
            
            // Run predictions for each available model
            for (const [type, model] of this.detectionModels.entries()) {
                try {
                    const prediction = model.predict(inputTensor);
                    const predictionData = await prediction.data();
                    
                    // Convert prediction to threat object
                    const threat = this.predictionToThreat(type, predictionData[0], environmentalData);
                    
                    if (threat) {
                        threats.push(threat);
                    }
                    
                    // Clean up tensors
                    prediction.dispose();
                    
                } catch (error) {
                    console.error(`Client-side ${type} detection failed:`, error);
                }
            }
            
            // Clean up input tensor
            inputTensor.dispose();
            
            return threats;
            
        } catch (error) {
            console.error('Client-side detection failed:', error);
            return [];
        }
    }
    
    prepareInputTensor(environmentalData) {
        // Convert environmental data to tensor format
        const features = [];
        
        // Weather features
        if (environmentalData.weather) {
            features.push(
                environmentalData.weather.temperature || 0,
                environmentalData.weather.humidity || 0,
                environmentalData.weather.pressure || 0,
                environmentalData.weather.wind_speed || 0,
                environmentalData.weather.precipitation || 0
            );
        } else {
            features.push(0, 0, 0, 0, 0);
        }
        
        // Air quality features
        if (environmentalData.air_quality) {
            features.push(
                environmentalData.air_quality.pm2_5 || 0,
                environmentalData.air_quality.pm10 || 0,
                environmentalData.air_quality.no2 || 0,
                environmentalData.air_quality.aqi || 0
            );
        } else {
            features.push(0, 0, 0, 0);
        }
        
        // Ocean features
        if (environmentalData.ocean) {
            features.push(
                environmentalData.ocean.water_level || 0,
                environmentalData.ocean.wave_height || 0,
                environmentalData.ocean.temperature || 0
            );
        } else {
            features.push(0, 0, 0);
        }
        
        // Normalize features (simple min-max scaling)
        const normalizedFeatures = this.normalizeFeatures(features);
        
        return tf.tensor2d([normalizedFeatures]);
    }
    
    normalizeFeatures(features) {
        // Simple feature normalization (you'd want more sophisticated normalization in production)
        return features.map((value, index) => {
            const scales = [50, 100, 1020, 30, 50, 100, 200, 100, 100, 5, 3, 25]; // Example scales
            return Math.max(-1, Math.min(1, value / (scales[index] || 100)));
        });
    }
    
    predictionToThreat(type, confidence, environmentalData) {
        const threshold = this.thresholds[type];
        
        if (confidence < threshold.confidence) {
            return null;
        }
        
        const severity = Math.ceil(confidence * 5);
        
        if (severity < threshold.severity) {
            return null;
        }
        
        return {
            id: `client_${type}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
            type,
            severity,
            confidence,
            source: 'client_ai',
            timestamp: new Date().toISOString(),
            description: this.generateThreatDescription(type, severity, confidence, environmentalData),
            latitude: environmentalData.location?.latitude || 0,
            longitude: environmentalData.location?.longitude || 0,
            data_sources: ['client_detection']
        };
    }
    
    generateThreatDescription(type, severity, confidence, data) {
        const severityLabels = ['', 'Minor', 'Moderate', 'Significant', 'Dangerous', 'Extreme'];
        const severityLabel = severityLabels[severity];
        
        const descriptions = {
            storm: `${severityLabel} storm conditions detected with ${Math.round(confidence * 100)}% confidence. Weather patterns indicate potential severe weather development.`,
            pollution: `${severityLabel} air pollution levels detected. Air quality monitoring shows elevated pollutant concentrations.`,
            erosion: `${severityLabel} coastal erosion risk identified. Environmental conditions suggest increased shoreline vulnerability.`,
            algal_bloom: `${severityLabel} algal bloom conditions detected. Water quality parameters indicate potential harmful algal growth.`,
            illegal_dumping: `Potential illegal dumping activity detected with high confidence. Environmental monitoring suggests unauthorized waste disposal.`,
            anomaly: `${severityLabel} environmental anomaly detected. Unusual patterns identified in monitoring data.`
        };
        
        return descriptions[type] || `${severityLabel} ${type} threat detected.`;
    }
    
    filterAndValidateThreats(threats) {
        // Remove duplicates based on type and location
        const uniqueThreats = new Map();
        
        threats.forEach(threat => {
            const key = `${threat.type}_${Math.round(threat.latitude * 100)}_${Math.round(threat.longitude * 100)}`;
            
            if (!uniqueThreats.has(key) || uniqueThreats.get(key).confidence < threat.confidence) {
                uniqueThreats.set(key, threat);
            }
        });
        
        // Apply severity and confidence thresholds
        return Array.from(uniqueThreats.values()).filter(threat => {
            const threshold = this.thresholds[threat.type];
            return threat.severity >= threshold.severity && threat.confidence >= threshold.confidence;
        });
    }
    
    async processThreatDetections(threats) {
        console.log(`🚨 Processing ${threats.length} threat detections...`);
        
        for (const threat of threats) {
            try {
                // Store threat in database
                await this.storeThreat(threat);
                
                // Create and send alerts
                if (window.alertManager) {
                    await window.alertManager.createAlert(threat, {
                        channels: ['web', 'push'],
                        createdBy: 'threat_monitor'
                    });
                }
                
                // Update dashboard
                if (window.dashboard) {
                    window.dashboard.handleNewThreat({ threat });
                }
                
                // Log detection
                console.log(`🚨 Threat detected: ${threat.type} (severity ${threat.severity})`);
                
            } catch (error) {
                console.error(`Failed to process threat ${threat.id}:`, error);
            }
        }
    }
    
    async storeThreat(threat) {
        try {
            const response = await fetch('/api/v1/threats', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${window.dashboard?.state?.authToken}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(threat)
            });
            
            if (!response.ok) {
                throw new Error(`Failed to store threat: ${response.status}`);
            }
            
            const result = await response.json();
            threat.id = result.id; // Update with server-assigned ID
            
        } catch (error) {
            console.error('Failed to store threat:', error);
            throw error;
        }
    }
    
    processEnvironmentalData(data) {
        if (this.isMonitoring) {
            // Trigger immediate threat check if new environmental data arrives
            setTimeout(() => {
                this.performThreatCheck();
            }, 1000);
        }
    }
    
    updateThresholds(newThresholds) {
        this.thresholds = { ...this.thresholds, ...newThresholds };
        console.log('🎚️ Threat thresholds updated:', this.thresholds);
    }
    
    updateStats(checkStart, threatsFound) {
        const checkDuration = Date.now() - checkStart;
        
        this.stats.totalChecks++;
        this.stats.threatsDetected += threatsFound;
        this.stats.lastCheck = new Date().toISOString();
        
        // Update rolling average response time
        if (this.stats.totalChecks === 1) {
            this.stats.avgResponseTime = checkDuration;
        } else {
            this.stats.avgResponseTime = (this.stats.avgResponseTime + checkDuration) / 2;
        }
    }
    
    updateMonitoringUI(isActive) {
        // Update monitoring status indicator
        const statusElement = document.getElementById('monitoring-status');
        if (statusElement) {
            statusElement.className = isActive ? 'status-active' : 'status-inactive';
            statusElement.textContent = isActive ? 'Monitoring Active' : 'Monitoring Inactive';
        }
        
        // Update monitoring toggle button
        const toggleButton = document.getElementById('toggle-monitoring');
        if (toggleButton) {
            toggleButton.textContent = isActive ? 'Stop Monitoring' : 'Start Monitoring';
            toggleButton.className = isActive ? 'btn btn-danger' : 'btn btn-success';
        }
        
        // Dispatch status change event
        document.dispatchEvent(new CustomEvent('monitoringStatusChanged', {
            detail: { active: isActive, stats: this.stats }
        }));
    }
    
    handleMonitoringError(error) {
        console.error('Monitoring error:', error);
        
        // Show error notification
        if (window.alertManager) {
            window.alertManager.showToast(`Monitoring error: ${error.message}`, 'error');
        }
        
        // Emit error event
        document.dispatchEvent(new CustomEvent('monitoringError', {
            detail: { error: error.message }
        }));
    }
    
    // Public API methods
    getStats() {
        return { ...this.stats };
    }
    
    getThresholds() {
        return { ...this.thresholds };
    }
    
    isActive() {
        return this.isMonitoring;
    }
    
    cleanup() {
        console.log('🧹 Cleaning up Threat Monitor...');
        
        this.stopMonitoring();
        
        // Dispose of TensorFlow models
        this.detectionModels.forEach(model => {
            try {
                model.dispose();
            } catch (error) {
                console.warn('Error disposing model:', error);
            }
        });
        
        this.detectionModels.clear();
    }
}

// Global threat monitor instance
window.threatMonitor = new ThreatMonitor();

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.threatMonitor) {
        window.threatMonitor.cleanup();
    }
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ThreatMonitor;
}
