/**
 * Ocean Sentinel - Interactive Maps
 * Leaflet.js map components for threat visualization
 */

class ThreatMapManager {
    constructor(containerId, options = {}) {
        this.containerId = containerId;
        this.map = null;
        this.layers = new Map();
        this.markers = new Map();
        this.heatmaps = new Map();
        this.currentData = [];
        
        this.options = {
            center: [39.8283, -98.5795], // Center of US
            zoom: 4,
            minZoom: 2,
            maxZoom: 18,
            ...options
        };
        
        this.threatIcons = new Map();
        this.init();
    }
    
    async init() {
        try {
            console.log('🗺️ Initializing threat map...');
            
            await this.createMap();
            this.createThreatIcons();
            this.setupLayers();
            this.setupControls();
            this.setupEventHandlers();
            
            console.log('✅ Threat map initialized');
            
        } catch (error) {
            console.error('❌ Failed to initialize threat map:', error);
        }
    }
    
    async createMap() {
        const container = document.getElementById(this.containerId);
        if (!container) {
            throw new Error(`Map container not found: ${this.containerId}`);
        }
        
        // Initialize Leaflet map
        this.map = L.map(this.containerId, {
            center: this.options.center,
            zoom: this.options.zoom,
            minZoom: this.options.minZoom,
            maxZoom: this.options.maxZoom,
            zoomControl: false // We'll add custom controls
        });
        
        // Add base tile layer
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 19
        }).addTo(this.map);
        
        // Add satellite layer as option
        const satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
            attribution: 'Tiles © Esri'
        });
        
        // Base layers control
        const baseLayers = {
            "OpenStreetMap": this.map._layers[Object.keys(this.map._layers)[0]],
            "Satellite": satelliteLayer
        };
        
        this.layerControl = L.control.layers(baseLayers, {}, {
            position: 'topright'
        }).addTo(this.map);
    }
    
    createThreatIcons() {
        const iconOptions = {
            iconSize: [32, 32],
            iconAnchor: [16, 32],
            popupAnchor: [0, -32]
        };
        
        // Create icons for different threat types and severities
        const threatTypes = ['storm', 'pollution', 'erosion', 'algal_bloom', 'illegal_dumping', 'anomaly'];
        const colors = {
            'storm': '#ff6b6b',
            'pollution': '#4ecdc4', 
            'erosion': '#45b7d1',
            'algal_bloom': '#96ceb4',
            'illegal_dumping': '#ffeaa7',
            'anomaly': '#dda0dd'
        };
        
        threatTypes.forEach(type => {
            for (let severity = 1; severity <= 5; severity++) {
                const color = colors[type];
                const size = 20 + (severity * 4); // Size based on severity
                
                const iconHtml = `
                    <div style="
                        width: ${size}px;
                        height: ${size}px;
                        border-radius: 50%;
                        background: ${color};
                        border: 2px solid white;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.3);
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        color: white;
                        font-weight: bold;
                        font-size: ${Math.max(10, size/3)}px;
                    ">
                        ${severity}
                    </div>
                `;
                
                this.threatIcons.set(`${type}_${severity}`, L.divIcon({
                    html: iconHtml,
                    className: 'threat-marker',
                    iconSize: [size, size],
                    iconAnchor: [size/2, size/2]
                }));
            }
        });
    }
    
    setupLayers() {
        // Create layer groups for different threat types
        const threatTypes = ['storm', 'pollution', 'erosion', 'algal_bloom', 'illegal_dumping', 'anomaly'];
        
        threatTypes.forEach(type => {
            const layer = L.layerGroup();
            this.layers.set(type, layer);
            this.layerControl.addOverlay(layer, this.formatThreatType(type));
            layer.addTo(this.map);
        });
        
        // Create heatmap layer
        this.heatmapLayer = L.layerGroup();
        this.layers.set('heatmap', this.heatmapLayer);
        this.layerControl.addOverlay(this.heatmapLayer, 'Threat Density');
        
        // Create cluster layer for high-density areas
        this.clusterLayer = L.markerClusterGroup({
            maxClusterRadius: 50,
            iconCreateFunction: (cluster) => {
                const count = cluster.getChildCount();
                const maxSeverity = Math.max(...cluster.getAllChildMarkers().map(m => m.options.severity || 1));
                
                return L.divIcon({
                    html: `<div class="cluster-icon severity-${maxSeverity}">${count}</div>`,
                    className: 'threat-cluster',
                    iconSize: [40, 40]
                });
            }
        });
        
        this.layers.set('cluster', this.clusterLayer);
        this.layerControl.addOverlay(this.clusterLayer, 'Clustered View');
    }
    
    setupControls() {
        // Add custom zoom control
        L.control.zoom({
            position: 'topleft'
        }).addTo(this.map);
        
        // Add scale control
        L.control.scale({
            position: 'bottomleft'
        }).addTo(this.map);
        
        // Add custom control panel
        const controlPanel = L.control({ position: 'topright' });
        controlPanel.onAdd = () => {
            const div = L.DomUtil.create('div', 'map-control-panel');
            div.innerHTML = `
                <div class="control-group">
                    <button id="refresh-threats" class="map-btn" title="Refresh Threats">
                        🔄
                    </button>
                    <button id="center-map" class="map-btn" title="Reset View">
                        🎯
                    </button>
                    <button id="toggle-heatmap" class="map-btn" title="Toggle Heatmap">
                        🔥
                    </button>
                    <button id="toggle-cluster" class="map-btn" title="Toggle Clustering">
                        📍
                    </button>
                </div>
                <div class="severity-legend">
                    <h4>Severity</h4>
                    <div class="legend-item"><span class="legend-color severity-1"></span> Minor</div>
                    <div class="legend-item"><span class="legend-color severity-2"></span> Moderate</div>
                    <div class="legend-item"><span class="legend-color severity-3"></span> Significant</div>
                    <div class="legend-item"><span class="legend-color severity-4"></span> Dangerous</div>
                    <div class="legend-item"><span class="legend-color severity-5"></span> Extreme</div>
                </div>
            `;
            
            // Prevent map interactions when clicking controls
            L.DomEvent.disableClickPropagation(div);
            
            return div;
        };
        
        controlPanel.addTo(this.map);
        
        // Setup control event handlers
        this.setupControlHandlers();
    }
    
    setupControlHandlers() {
        document.getElementById('refresh-threats')?.addEventListener('click', () => {
            this.refreshThreats();
        });
        
        document.getElementById('center-map')?.addEventListener('click', () => {
            this.map.setView(this.options.center, this.options.zoom);
        });
        
        document.getElementById('toggle-heatmap')?.addEventListener('click', (e) => {
            this.toggleHeatmap();
            e.target.classList.toggle('active');
        });
        
        document.getElementById('toggle-cluster')?.addEventListener('click', (e) => {
            this.toggleClustering();
            e.target.classList.toggle('active');
        });
    }
    
    setupEventHandlers() {
        // Map click handler
        this.map.on('click', (e) => {
            const { lat, lng } = e.latlng;
            this.emit('mapClick', { latitude: lat, longitude: lng });
        });
        
        // Zoom change handler
        this.map.on('zoomend', () => {
            this.updateDisplayBasedOnZoom();
        });
        
        // Move end handler
        this.map.on('moveend', () => {
            this.emit('mapMoved', {
                center: this.map.getCenter(),
                zoom: this.map.getZoom(),
                bounds: this.map.getBounds()
            });
        });
    }
    
    addThreat(threat) {
        try {
            const { id, type, severity, latitude, longitude, confidence, description, timestamp } = threat;
            
            // Get appropriate icon
            const iconKey = `${type}_${severity}`;
            const icon = this.threatIcons.get(iconKey);
            
            if (!icon) {
                console.warn(`No icon found for threat type: ${type}, severity: ${severity}`);
                return;
            }
            
            // Create marker
            const marker = L.marker([latitude, longitude], { 
                icon,
                severity,
                threatType: type,
                threatId: id
            });
            
            // Create popup content
            const popupContent = this.createThreatPopup(threat);
            marker.bindPopup(popupContent, {
                maxWidth: 300,
                className: 'threat-popup'
            });
            
            // Add click handler
            marker.on('click', () => {
                this.emit('threatClick', threat);
            });
            
            // Add to appropriate layer
            const layer = this.layers.get(type);
            if (layer) {
                layer.addLayer(marker);
            }
            
            // Add to cluster layer
            this.clusterLayer.addLayer(marker);
            
            // Store marker reference
            this.markers.set(id, marker);
            
            console.log(`📍 Added ${type} threat marker at ${latitude}, ${longitude}`);
            
        } catch (error) {
            console.error('Error adding threat to map:', error);
        }
    }
    
    createThreatPopup(threat) {
        const timeAgo = this.formatTimeAgo(new Date(threat.timestamp));
        const severityLabel = ['', 'Minor', 'Moderate', 'Significant', 'Dangerous', 'Extreme'][threat.severity];
        
        return `
            <div class="threat-popup-content">
                <div class="popup-header">
                    <h3>${this.formatThreatType(threat.type)} Threat</h3>
                    <span class="severity-badge severity-${threat.severity}">${severityLabel}</span>
                </div>
                <div class="popup-body">
                    <p class="threat-description">${threat.description}</p>
                    <div class="threat-meta">
                        <div class="meta-item">
                            <span class="meta-label">Confidence:</span>
                            <span class="meta-value">${Math.round(threat.confidence * 100)}%</span>
                        </div>
                        <div class="meta-item">
                            <span class="meta-label">Detected:</span>
                            <span class="meta-value">${timeAgo}</span>
                        </div>
                        ${threat.affected_population ? `
                            <div class="meta-item">
                                <span class="meta-label">Affected:</span>
                                <span class="meta-value">${threat.affected_population.toLocaleString()} people</span>
                            </div>
                        ` : ''}
                    </div>
                </div>
                <div class="popup-actions">
                    <button onclick="window.dashboard?.viewThreatDetails('${threat.id}')" class="btn btn-primary btn-sm">
                        View Details
                    </button>
                    ${!threat.verified ? `
                        <button onclick="window.dashboard?.verifyThreat('${threat.id}')" class="btn btn-secondary btn-sm">
                            Verify
                        </button>
                    ` : ''}
                </div>
            </div>
        `;
    }
    
    updateThreats(threats) {
        // Clear existing markers
        this.clearAllMarkers();
        
        // Add new threats
        threats.forEach(threat => {
            this.addThreat(threat);
        });
        
        // Update heatmap if enabled
        this.updateHeatmap(threats);
        
        // Fit map to threats if there are any
        if (threats.length > 0) {
            this.fitToThreats(threats);
        }
        
        this.currentData = threats;
        console.log(`🗺️ Updated map with ${threats.length} threats`);
    }
    
    clearAllMarkers() {
        // Clear individual layers
        this.layers.forEach(layer => {
            if (layer !== this.heatmapLayer && layer !== this.clusterLayer) {
                layer.clearLayers();
            }
        });
        
        // Clear cluster layer
        this.clusterLayer.clearLayers();
        
        // Clear marker references
        this.markers.clear();
    }
    
    updateHeatmap(threats) {
        // Clear existing heatmap
        this.heatmapLayer.clearLayers();
        
        if (threats.length === 0) return;
        
        // Prepare heatmap data
        const heatData = threats.map(threat => [
            threat.latitude,
            threat.longitude,
            threat.severity * threat.confidence // Weight by severity and confidence
        ]);
        
        // Create heatmap
        const heatmapOptions = {
            radius: 25,
            blur: 15,
            maxZoom: 17,
            gradient: {
                0.0: 'blue',
                0.5: 'lime',
                0.7: 'yellow',
                0.9: 'orange',
                1.0: 'red'
            }
        };
        
        const heatLayer = L.heatLayer(heatData, heatmapOptions);
        this.heatmapLayer.addLayer(heatLayer);
        
        console.log('🔥 Updated threat heatmap');
    }
    
    fitToThreats(threats) {
        if (threats.length === 0) return;
        
        const group = new L.featureGroup(
            threats.map(threat => 
                L.marker([threat.latitude, threat.longitude])
            )
        );
        
        this.map.fitBounds(group.getBounds(), {
            padding: [20, 20]
        });
    }
    
    toggleHeatmap() {
        if (this.map.hasLayer(this.heatmapLayer)) {
            this.map.removeLayer(this.heatmapLayer);
        } else {
            this.map.addLayer(this.heatmapLayer);
        }
    }
    
    toggleClustering() {
        const hasCluster = this.map.hasLayer(this.clusterLayer);
        
        if (hasCluster) {
            // Remove cluster layer and show individual layers
            this.map.removeLayer(this.clusterLayer);
            this.layers.forEach((layer, type) => {
                if (type !== 'heatmap' && type !== 'cluster') {
                    this.map.addLayer(layer);
                }
            });
        } else {
            // Remove individual layers and show cluster
            this.layers.forEach((layer, type) => {
                if (type !== 'heatmap' && type !== 'cluster') {
                    this.map.removeLayer(layer);
                }
            });
            this.map.addLayer(this.clusterLayer);
        }
    }
    
    updateDisplayBasedOnZoom() {
        const zoom = this.map.getZoom();
        
        // Auto-enable clustering at lower zoom levels
        if (zoom < 6 && !this.map.hasLayer(this.clusterLayer)) {
            this.toggleClustering();
            document.getElementById('toggle-cluster')?.classList.add('active');
        }
    }
    
    refreshThreats() {
        this.emit('refreshRequested');
        
        // Show loading indicator
        const refreshBtn = document.getElementById('refresh-threats');
        if (refreshBtn) {
            refreshBtn.innerHTML = '⏳';
            refreshBtn.disabled = true;
            
            setTimeout(() => {
                refreshBtn.innerHTML = '🔄';
                refreshBtn.disabled = false;
            }, 2000);
        }
    }
    
    setUserLocation(latitude, longitude, accuracy = 1000) {
        // Remove existing user location
        if (this.userLocationMarker) {
            this.map.removeLayer(this.userLocationMarker);
        }
        
        if (this.userLocationCircle) {
            this.map.removeLayer(this.userLocationCircle);
        }
        
        // Add user location marker
        this.userLocationMarker = L.marker([latitude, longitude], {
            icon: L.divIcon({
                html: '<div class="user-location-marker">📍</div>',
                className: 'user-location',
                iconSize: [20, 20],
                iconAnchor: [10, 10]
            })
        }).addTo(this.map);
        
        // Add accuracy circle
        this.userLocationCircle = L.circle([latitude, longitude], {
            radius: accuracy,
            color: '#4285f4',
            fillColor: '#4285f4',
            fillOpacity: 0.1,
            weight: 2
        }).addTo(this.map);
        
        this.userLocationMarker.bindPopup('Your Location');
    }
    
    // Utility methods
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
    
    formatTimeAgo(date) {
        const now = new Date();
        const diff = now - date;
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);
        
        if (days > 0) return `${days} day${days > 1 ? 's' : ''} ago`;
        if (hours > 0) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
        if (minutes > 0) return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
        return 'Just now';
    }
    
    // Event emitter
    emit(event, data) {
        document.dispatchEvent(new CustomEvent(`map:${event}`, { detail: data }));
    }
    
    // Cleanup
    destroy() {
        if (this.map) {
            this.map.remove();
            this.map = null;
        }
        this.layers.clear();
        this.markers.clear();
        this.heatmaps.clear();
        console.log('🗺️ Threat map destroyed');
    }
}

// Export for global use
window.ThreatMapManager = ThreatMapManager;
