/**
 * Ocean Sentinel - Main Dashboard JavaScript
 * Core dashboard functionality for Bubble.io integration
 */

class OceanSentinelDashboard {
    constructor() {
        this.config = {
            apiBaseUrl: window.OCEAN_SENTINEL_API_URL || 'https://your-api.vercel.app/api/v1',
            pusherKey: window.PUSHER_KEY,
            pusherCluster: window.PUSHER_CLUSTER || 'us2',
            supabaseUrl: window.SUPABASE_URL,
            supabaseAnonKey: window.SUPABASE_ANON_KEY
        };
        
        this.state = {
            currentUser: null,
            authToken: null,
            threats: [],
            alerts: [],
            environmentalData: null,
            selectedThreat: null,
            filters: {
                threatType: 'all',
                severity: 'all',
                timeRange: '24h',
                resolved: false
            }
        };
        
        this.components = {
            threatMap: null,
            charts: {},
            pusher: null,
            supabase: null
        };
        
        this.eventHandlers = new Map();
        this.updateIntervals = new Map();
        
        this.init();
    }
    
    async init() {
        try {
            console.log('🌊 Initializing Ocean Sentinel Dashboard...');
            
            // Initialize external services
            await this.initializeServices();
            
            // Setup authentication
            await this.initializeAuth();
            
            // Initialize components
            await this.initializeComponents();
            
            // Setup event listeners
            this.setupEventListeners();
            
            // Load initial data
            await this.loadInitialData();
            
            // Setup real-time updates
            this.setupRealTimeUpdates();
            
            // Start monitoring
            this.startPeriodicUpdates();
            
            console.log('✅ Dashboard initialized successfully');
            
        } catch (error) {
            console.error('❌ Dashboard initialization failed:', error);
            this.showError('Failed to initialize dashboard');
        }
    }
    
    async initializeServices() {
        // Initialize Pusher for real-time updates
        if (this.config.pusherKey) {
            this.components.pusher = new Pusher(this.config.pusherKey, {
                cluster: this.config.pusherCluster,
                encrypted: true
            });
        }
        
        // Initialize Supabase client
        if (this.config.supabaseUrl && this.config.supabaseAnonKey) {
            this.components.supabase = supabase.createClient(
                this.config.supabaseUrl, 
                this.config.supabaseAnonKey
            );
        }
    }
    
    async initializeAuth() {
        // Check for existing authentication
        const token = localStorage.getItem('ocean_sentinel_token');
        if (token) {
            this.state.authToken = token;
            try {
                const user = await this.verifyToken(token);
                this.state.currentUser = user;
                this.updateUIForAuthenticatedUser();
            } catch (error) {
                console.warn('Token verification failed:', error);
                this.logout();
            }
        }
    }
    
    async initializeComponents() {
        // Initialize map component
        if (typeof L !== 'undefined') {
            await this.initializeMap();
        }
        
        // Initialize chart components
        if (typeof d3 !== 'undefined') {
            await this.initializeCharts();
        }
        
        // Initialize data tables
        this.initializeDataTables();
        
        // Initialize UI components
        this.initializeUIComponents();
    }
    
    async initializeMap() {
        const mapContainer = document.getElementById('threat-map');
        if (!mapContainer) return;
        
        this.components.threatMap = L.map('threat-map').setView([39.8283, -98.5795], 4);
        
        // Add tile layer
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(this.components.threatMap);
        
        // Add threat layers
        this.components.threatLayers = {
            storms: L.layerGroup().addTo(this.components.threatMap),
            pollution: L.layerGroup().addTo(this.components.threatMap),
            erosion: L.layerGroup().addTo(this.components.threatMap),
            other: L.layerGroup().addTo(this.components.threatMap)
        };
        
        // Add layer control
        const layerControl = L.control.layers({}, {
            'Storm Threats': this.components.threatLayers.storms,
            'Pollution': this.components.threatLayers.pollution,
            'Coastal Erosion': this.components.threatLayers.erosion,
            'Other Threats': this.components.threatLayers.other
        }).addTo(this.components.threatMap);
    }
    
    async initializeCharts() {
        // Initialize threat timeline chart
        this.components.charts.timeline = new ThreatTimeline('#threat-timeline-chart');
        
        // Initialize severity distribution chart
        this.components.charts.severity = new SeverityChart('#severity-distribution-chart');
        
        // Initialize environmental metrics chart
        this.components.charts.environmental = new EnvironmentalChart('#environmental-metrics-chart');
        
        // Initialize alert performance chart
        this.components.charts.alerts = new AlertPerformanceChart('#alert-performance-chart');
    }
    
    initializeDataTables() {
        // Initialize threats table
        const threatsTable = document.getElementById('threats-table');
        if (threatsTable && typeof DataTable !== 'undefined') {
            this.components.threatsTable = new DataTable('#threats-table', {
                columns: [
                    { data: 'type', title: 'Type' },
                    { data: 'severity', title: 'Severity' },
                    { data: 'confidence', title: 'Confidence' },
                    { data: 'location', title: 'Location' },
                    { data: 'timestamp', title: 'Detected' },
                    { data: 'actions', title: 'Actions' }
                ],
                order: [[4, 'desc']],
                pageLength: 25
            });
        }
    }
    
    initializeUIComponents() {
        // Initialize filter controls
        this.setupFilterControls();
        
        // Initialize notification system
        this.setupNotificationSystem();
        
        // Initialize modals and overlays
        this.setupModals();
        
        // Initialize keyboard shortcuts
        this.setupKeyboardShortcuts();
    }
    
    setupEventListeners() {
        // API response handlers
        this.eventHandlers.set('apiError', this.handleApiError.bind(this));
        this.eventHandlers.set('dataUpdate', this.handleDataUpdate.bind(this));
        
        // UI event handlers
        document.addEventListener('click', this.handleGlobalClick.bind(this));
        document.addEventListener('keyup', this.handleGlobalKeyup.bind(this));
        
        // Window events
        window.addEventListener('resize', this.handleWindowResize.bind(this));
        window.addEventListener('beforeunload', this.handleBeforeUnload.bind(this));
        
        // Custom events
        document.addEventListener('threatSelected', this.handleThreatSelection.bind(this));
        document.addEventListener('filterChanged', this.handleFilterChange.bind(this));
    }
    
    async loadInitialData() {
        console.log('📊 Loading initial dashboard data...');
        
        try {
            // Load threats
            await this.loadThreats();
            
            // Load recent alerts
            await this.loadAlerts();
            
            // Load environmental data
            await this.loadEnvironmentalData();
            
            // Load dashboard analytics
            await this.loadAnalytics();
            
            // Update UI with loaded data
            this.updateDashboard();
            
        } catch (error) {
            console.error('Error loading initial data:', error);
            this.showError('Failed to load dashboard data');
        }
    }
    
    async loadThreats() {
        try {
            const response = await this.apiCall('/threats', {
                hours_back: this.getHoursFromTimeRange(this.state.filters.timeRange),
                resolved: this.state.filters.resolved,
                limit: 100
            });
            
            this.state.threats = response || [];
            console.log(`📍 Loaded ${this.state.threats.length} threats`);
            
        } catch (error) {
            console.error('Error loading threats:', error);
            this.state.threats = [];
        }
    }
    
    async loadAlerts() {
        try {
            const response = await this.apiCall('/alerts', {
                hours_back: 24,
                limit: 50
            });
            
            this.state.alerts = response || [];
            console.log(`🚨 Loaded ${this.state.alerts.length} alerts`);
            
        } catch (error) {
            console.error('Error loading alerts:', error);
            this.state.alerts = [];
        }
    }
    
    async loadEnvironmentalData() {
        try {
            const response = await this.apiCall('/data/latest');
            this.state.environmentalData = response?.data || null;
            console.log('🌡️ Loaded environmental data');
            
        } catch (error) {
            console.error('Error loading environmental data:', error);
            this.state.environmentalData = null;
        }
    }
    
    async loadAnalytics() {
        try {
            const response = await this.apiCall('/analytics/dashboard');
            this.state.analytics = response || {};
            console.log('📈 Loaded dashboard analytics');
            
        } catch (error) {
            console.error('Error loading analytics:', error);
            this.state.analytics = {};
        }
    }
    
    setupRealTimeUpdates() {
        if (!this.components.pusher) return;
        
        // Subscribe to threat alerts
        const alertsChannel = this.components.pusher.subscribe('threat-alerts');
        alertsChannel.bind('new-threat', (data) => {
            this.handleNewThreat(data);
        });
        
        // Subscribe to system updates
        const updatesChannel = this.components.pusher.subscribe('dashboard-updates');
        updatesChannel.bind('data-update', (data) => {
            this.handleDataUpdate(data);
        });
        
        // Subscribe to location-specific updates if user has preferences
        if (this.state.currentUser?.preferences?.geographic_focus) {
            const location = this.state.currentUser.preferences.geographic_focus;
            const locationChannel = `location-${Math.round(location.lat)}_${Math.round(location.lon)}`;
            
            const localChannel = this.components.pusher.subscribe(locationChannel);
            localChannel.bind('local-threat', (data) => {
                this.handleLocalThreat(data);
            });
        }
    }
    
    startPeriodicUpdates() {
        // Update threats every 5 minutes
        this.updateIntervals.set('threats', setInterval(() => {
            this.loadThreats().then(() => this.updateThreatsDisplay());
        }, 5 * 60 * 1000));
        
        // Update environmental data every 10 minutes
        this.updateIntervals.set('environmental', setInterval(() => {
            this.loadEnvironmentalData().then(() => this.updateEnvironmentalDisplay());
        }, 10 * 60 * 1000));
        
        // Update analytics every 15 minutes
        this.updateIntervals.set('analytics', setInterval(() => {
            this.loadAnalytics().then(() => this.updateAnalyticsDisplay());
        }, 15 * 60 * 1000));
    }
    
    updateDashboard() {
        this.updateThreatsDisplay();
        this.updateAlertsDisplay();
        this.updateEnvironmentalDisplay();
        this.updateAnalyticsDisplay();
        this.updateMapDisplay();
    }
    
    updateThreatsDisplay() {
        // Update threats table
        if (this.components.threatsTable) {
            const tableData = this.state.threats.map(threat => ({
                type: this.formatThreatType(threat.type),
                severity: this.formatSeverity(threat.severity),
                confidence: `${Math.round(threat.confidence * 100)}%`,
                location: this.formatCoordinates(threat.latitude, threat.longitude),
                timestamp: this.formatTimestamp(threat.timestamp),
                actions: this.generateThreatActions(threat)
            }));
            
            this.components.threatsTable.clear().rows.add(tableData).draw();
        }
        
        // Update threat statistics
        this.updateThreatStatistics();
        
        // Update charts
        if (this.components.charts.timeline) {
            this.components.charts.timeline.updateData(this.state.threats);
        }
        
        if (this.components.charts.severity) {
            this.components.charts.severity.updateData(this.state.threats);
        }
    }
    
    updateMapDisplay() {
        if (!this.components.threatMap) return;
        
        // Clear existing markers
        Object.values(this.components.threatLayers).forEach(layer => {
            layer.clearLayers();
        });
        
        // Add threat markers
        this.state.threats.forEach(threat => {
            const marker = this.createThreatMarker(threat);
            const layerKey = this.getThreatLayerKey(threat.type);
            
            if (this.components.threatLayers[layerKey]) {
                this.components.threatLayers[layerKey].addLayer(marker);
            }
        });
        
        // Fit map to threat bounds if threats exist
        if (this.state.threats.length > 0) {
            const group = new L.featureGroup(
                Object.values(this.components.threatLayers)
                    .map(layer => layer.getLayers())
                    .flat()
            );
            
            if (group.getLayers().length > 0) {
                this.components.threatMap.fitBounds(group.getBounds(), { padding: [20, 20] });
            }
        }
    }
    
    createThreatMarker(threat) {
        const icon = this.getThreatIcon(threat.type, threat.severity);
        const marker = L.marker([threat.latitude, threat.longitude], { icon });
        
        const popupContent = `
            <div class="threat-popup">
                <h4>${this.formatThreatType(threat.type)} Threat</h4>
                <p><strong>Severity:</strong> ${threat.severity}/5</p>
                <p><strong>Confidence:</strong> ${Math.round(threat.confidence * 100)}%</p>
                <p><strong>Description:</strong> ${threat.description}</p>
                <p><strong>Detected:</strong> ${this.formatTimestamp(threat.timestamp)}</p>
                <div class="threat-actions">
                    <button onclick="dashboard.viewThreatDetails('${threat.id}')">View Details</button>
                    ${threat.verified ? '' : '<button onclick="dashboard.verifyThreat(\'' + threat.id + '\')">Verify</button>'}
                </div>
            </div>
        `;
        
        marker.bindPopup(popupContent);
        marker.on('click', () => this.selectThreat(threat));
        
        return marker;
    }
    
    // API communication methods
    async apiCall(endpoint, params = {}, options = {}) {
        const url = new URL(this.config.apiBaseUrl + endpoint);
        
        // Add query parameters
        Object.keys(params).forEach(key => {
            if (params[key] !== undefined && params[key] !== null) {
                url.searchParams.append(key, params[key]);
            }
        });
        
        const fetchOptions = {
            method: options.method || 'GET',
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        };
        
        // Add authentication header if available
        if (this.state.authToken) {
            fetchOptions.headers['Authorization'] = `Bearer ${this.state.authToken}`;
        }
        
        // Add body for POST/PUT requests
        if (options.body) {
            fetchOptions.body = JSON.stringify(options.body);
        }
        
        try {
            const response = await fetch(url.toString(), fetchOptions);
            
            if (!response.ok) {
                throw new Error(`API call failed: ${response.status} ${response.statusText}`);
            }
            
            return await response.json();
            
        } catch (error) {
            console.error('API call error:', error);
            this.eventHandlers.get('apiError')?.(error);
            throw error;
        }
    }
    
    // Event handlers
    handleNewThreat(threatData) {
        console.log('🚨 New threat received:', threatData);
        
        // Add to threats array
        this.state.threats.unshift(threatData.threat);
        
        // Update displays
        this.updateThreatsDisplay();
        this.updateMapDisplay();
        
        // Show notification
        this.showNotification(`New ${threatData.threat.type} threat detected`, 'warning');
        
        // Play alert sound if enabled
        if (this.state.currentUser?.preferences?.sound_alerts) {
            this.playAlertSound(threatData.threat.severity);
        }
    }
    
    handleDataUpdate(updateData) {
        console.log('📊 Data update received:', updateData);
        
        if (updateData.type === 'environmental') {
            this.loadEnvironmentalData().then(() => this.updateEnvironmentalDisplay());
        } else if (updateData.type === 'analytics') {
            this.loadAnalytics().then(() => this.updateAnalyticsDisplay());
        }
    }
    
    handleThreatSelection(event) {
        const threat = event.detail.threat;
        this.state.selectedThreat = threat;
        this.showThreatDetails(threat);
    }
    
    handleFilterChange(event) {
        const { filterType, value } = event.detail;
        this.state.filters[filterType] = value;
        
        // Reload data with new filters
        this.loadThreats().then(() => this.updateDashboard());
    }
    
    // Utility methods
    selectThreat(threat) {
        this.state.selectedThreat = threat;
        document.dispatchEvent(new CustomEvent('threatSelected', { 
            detail: { threat } 
        }));
    }
    
    formatThreatType(type) {
        const typeMap = {
            'storm': 'Storm',
            'pollution': 'Air Pollution',
            'erosion': 'Coastal Erosion',
            'algal_bloom': 'Algal Bloom',
            'illegal_dumping': 'Illegal Dumping',
            'anomaly': 'Environmental Anomaly'
        };
        return typeMap[type] || type.charAt(0).toUpperCase() + type.slice(1);
    }
    
    formatSeverity(severity) {
        const severityLabels = ['', 'Minor', 'Moderate', 'Significant', 'Dangerous', 'Extreme'];
        return `${severityLabels[severity]} (${severity}/5)`;
    }
    
    formatTimestamp(timestamp) {
        return new Date(timestamp).toLocaleString();
    }
    
    formatCoordinates(lat, lon) {
        return `${lat.toFixed(4)}, ${lon.toFixed(4)}`;
    }
    
    getHoursFromTimeRange(timeRange) {
        const rangeMap = {
            '1h': 1, '6h': 6, '12h': 12, '24h': 24,
            '48h': 48, '7d': 168, '30d': 720
        };
        return rangeMap[timeRange] || 24;
    }
    
    showNotification(message, type = 'info') {
        // Implementation would depend on your notification system
        console.log(`Notification (${type}):`, message);
    }
    
    showError(message) {
        this.showNotification(message, 'error');
    }
    
    cleanup() {
        // Clear intervals
        this.updateIntervals.forEach(interval => clearInterval(interval));
        this.updateIntervals.clear();
        
        // Unsubscribe from Pusher channels
        if (this.components.pusher) {
            this.components.pusher.disconnect();
        }
        
        // Clean up map
        if (this.components.threatMap) {
            this.components.threatMap.remove();
        }
        
        console.log('🧹 Dashboard cleaned up');
    }
}

// Global dashboard instance
let dashboard;

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    dashboard = new OceanSentinelDashboard();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (dashboard) {
        dashboard.cleanup();
    }
});
