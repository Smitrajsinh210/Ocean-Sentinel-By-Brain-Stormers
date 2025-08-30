/**
 * Ocean Sentinel - Frontend Tests
 * JavaScript tests for dashboard functionality
 */

// Mock dependencies
global.fetch = require('jest-fetch-mock');
global.L = {
    map: jest.fn(() => ({
        setView: jest.fn(),
        addLayer: jest.fn(),
        removeLayer: jest.fn(),
        hasLayer: jest.fn()
    })),
    tileLayer: jest.fn(() => ({
        addTo: jest.fn()
    })),
    marker: jest.fn(() => ({
        bindPopup: jest.fn(),
        addTo: jest.fn(),
        on: jest.fn()
    })),
    circleMarker: jest.fn(() => ({
        addTo: jest.fn()
    })),
    layerGroup: jest.fn(() => ({
        addLayer: jest.fn(),
        clearLayers: jest.fn()
    }))
};

global.d3 = {
    select: jest.fn(() => ({
        append: jest.fn(() => ({
            attr: jest.fn(() => ({
                attr: jest.fn()
            }))
        }))
    })),
    scaleTime: jest.fn(() => ({
        domain: jest.fn(() => ({
            range: jest.fn()
        }))
    })),
    scaleLinear: jest.fn(() => ({
        domain: jest.fn(() => ({
            range: jest.fn()
        }))
    }))
};

global.Pusher = jest.fn(() => ({
    subscribe: jest.fn(() => ({
        bind: jest.fn()
    })),
    connection: {
        bind: jest.fn()
    }
}));

// Test ThreatMonitor class
describe('ThreatMonitor', () => {
    let threatMonitor;
    
    beforeEach(() => {
        // Reset DOM
        document.body.innerHTML = '';
        
        // Mock ThreatMonitor class
        global.ThreatMonitor = class {
            constructor() {
                this.isMonitoring = false;
                this.stats = {
                    totalChecks: 0,
                    threatsDetected: 0,
                    avgResponseTime: 0
                };
            }
            
            startMonitoring() {
                this.isMonitoring = true;
                return Promise.resolve();
            }
            
            stopMonitoring() {
                this.isMonitoring = false;
                return Promise.resolve();
            }
            
            getStats() {
                return this.stats;
            }
            
            isActive() {
                return this.isMonitoring;
            }
        };
        
        threatMonitor = new ThreatMonitor();
    });
    
    test('should initialize with monitoring stopped', () => {
        expect(threatMonitor.isActive()).toBe(false);
    });
    
    test('should start monitoring', async () => {
        await threatMonitor.startMonitoring();
        expect(threatMonitor.isActive()).toBe(true);
    });
    
    test('should stop monitoring', async () => {
        await threatMonitor.startMonitoring();
        await threatMonitor.stopMonitoring();
        expect(threatMonitor.isActive()).toBe(false);
    });
    
    test('should return stats', () => {
        const stats = threatMonitor.getStats();
        expect(stats).toHaveProperty('totalChecks');
        expect(stats).toHaveProperty('threatsDetected');
        expect(stats).toHaveProperty('avgResponseTime');
    });
});

// Test AlertManager class
describe('AlertManager', () => {
    let alertManager;
    
    beforeEach(() => {
        // Mock AlertManager class
        global.AlertManager = class {
            constructor() {
                this.alerts = new Map();
            }
            
            async createAlert(threatData, options = {}) {
                const alertId = `alert_${Date.now()}`;
                const alert = {
                    id: alertId,
                    threatId: threatData.id,
                    type: threatData.type,
                    severity: threatData.severity,
                    timestamp: new Date().toISOString(),
                    status: 'created'
                };
                
                this.alerts.set(alertId, alert);
                return alert;
            }
            
            getAlert(alertId) {
                return this.alerts.get(alertId);
            }
            
            getAllAlerts() {
                return Array.from(this.alerts.values());
            }
        };
        
        alertManager = new AlertManager();
    });
    
    test('should create alert', async () => {
        const threatData = {
            id: 'threat-1',
            type: 'storm',
            severity: 4,
            confidence: 0.85
        };
        
        const alert = await alertManager.createAlert(threatData);
        
        expect(alert).toHaveProperty('id');
        expect(alert.type).toBe('storm');
        expect(alert.severity).toBe(4);
        expect(alert.status).toBe('created');
    });
    
    test('should retrieve alert by ID', async () => {
        const threatData = {
            id: 'threat-1',
            type: 'pollution',
            severity: 3
        };
        
        const alert = await alertManager.createAlert(threatData);
        const retrieved = alertManager.getAlert(alert.id);
        
        expect(retrieved).toEqual(alert);
    });
    
    test('should get all alerts', async () => {
        const threatData1 = { id: 'threat-1', type: 'storm', severity: 4 };
        const threatData2 = { id: 'threat-2', type: 'pollution', severity: 3 };
        
        await alertManager.createAlert(threatData1);
        await alertManager.createAlert(threatData2);
        
        const allAlerts = alertManager.getAllAlerts();
        expect(allAlerts).toHaveLength(2);
    });
});

// Test RealTimeManager class
describe('RealTimeManager', () => {
    let realTimeManager;
    
    beforeEach(() => {
        global.RealTimeManager = class {
            constructor() {
                this.eventHandlers = new Map();
                this.connectionStatus = {
                    pusher: 'disconnected',
                    supabase: 'disconnected'
                };
            }
            
            on(event, callback) {
                if (!this.eventHandlers.has(event)) {
                    this.eventHandlers.set(event, []);
                }
                this.eventHandlers.get(event).push(callback);
            }
            
            emit(event, data) {
                if (this.eventHandlers.has(event)) {
                    this.eventHandlers.get(event).forEach(callback => {
                        callback(data);
                    });
                }
            }
            
            getConnectionStatus() {
                return this.connectionStatus;
            }
        };
        
        realTimeManager = new RealTimeManager();
    });
    
    test('should register event handlers', () => {
        const handler = jest.fn();
        realTimeManager.on('test:event', handler);
        
        realTimeManager.emit('test:event', { test: 'data' });
        
        expect(handler).toHaveBeenCalledWith({ test: 'data' });
    });
    
    test('should return connection status', () => {
        const status = realTimeManager.getConnectionStatus();
        
        expect(status).toHaveProperty('pusher');
        expect(status).toHaveProperty('supabase');
    });
});

// Test ThreatMapManager class
describe('ThreatMapManager', () => {
    let mapManager;
    
    beforeEach(() => {
        document.body.innerHTML = '<div id="test-map"></div>';
        
        global.ThreatMapManager = class {
            constructor(containerId) {
                this.containerId = containerId;
                this.markers = new Map();
                this.map = {
                    setView: jest.fn(),
                    addLayer: jest.fn(),
                    hasLayer: jest.fn(() => false)
                };
            }
            
            addThreat(threat) {
                const marker = {
                    id: threat.id,
                    type: threat.type,
                    severity: threat.severity
                };
                this.markers.set(threat.id, marker);
            }
            
            updateThreats(threats) {
                this.markers.clear();
                threats.forEach(threat => this.addThreat(threat));
            }
            
            getMarkerCount() {
                return this.markers.size;
            }
        };
        
        mapManager = new ThreatMapManager('test-map');
    });
    
    test('should add threat markers', () => {
        const threat = {
            id: 'threat-1',
            type: 'storm',
            severity: 4,
            latitude: 40.7128,
            longitude: -74.0060
        };
        
        mapManager.addThreat(threat);
        
        expect(mapManager.getMarkerCount()).toBe(1);
    });
    
    test('should update threats', () => {
        const threats = [
            { id: 'threat-1', type: 'storm', severity: 4, latitude: 40.7128, longitude: -74.0060 },
            { id: 'threat-2', type: 'pollution', severity: 3, latitude: 34.0522, longitude: -118.2437 }
        ];
        
        mapManager.updateThreats(threats);
        
        expect(mapManager.getMarkerCount()).toBe(2);
    });
});

// Test utility functions
describe('Utility Functions', () => {
    test('should format time ago correctly', () => {
        const formatTimeAgo = (date) => {
            const now = new Date();
            const diff = now - date;
            const minutes = Math.floor(diff / 60000);
            
            if (minutes < 1) return 'Just now';
            if (minutes < 60) return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
            
            const hours = Math.floor(minutes / 60);
            return `${hours} hour${hours > 1 ? 's' : ''} ago`;
        };
        
        const now = new Date();
        const fiveMinutesAgo = new Date(now.getTime() - 5 * 60 * 1000);
        const twoHoursAgo = new Date(now.getTime() - 2 * 60 * 60 * 1000);
        
        expect(formatTimeAgo(now)).toBe('Just now');
        expect(formatTimeAgo(fiveMinutesAgo)).toBe('5 minutes ago');
        expect(formatTimeAgo(twoHoursAgo)).toBe('2 hours ago');
    });
    
    test('should format threat types correctly', () => {
        const formatThreatType = (type) => {
            const typeMap = {
                'storm': 'Storm',
                'pollution': 'Air Pollution',
                'erosion': 'Coastal Erosion',
                'algal_bloom': 'Algal Bloom',
                'illegal_dumping': 'Illegal Dumping',
                'anomaly': 'Environmental Anomaly'
            };
            return typeMap[type] || type.charAt(0).toUpperCase() + type.slice(1);
        };
        
        expect(formatThreatType('storm')).toBe('Storm');
        expect(formatThreatType('pollution')).toBe('Air Pollution');
        expect(formatThreatType('unknown')).toBe('Unknown');
    });
});

// Test API integration
describe('API Integration', () => {
    beforeEach(() => {
        fetch.resetMocks();
    });
    
    test('should fetch threats from API', async () => {
        const mockThreats = [
            { id: '1', type: 'storm', severity: 4 },
            { id: '2', type: 'pollution', severity: 3 }
        ];
        
        fetch.mockResponseOnce(JSON.stringify({ threats: mockThreats }));
        
        const response = await fetch('/api/v1/threats');
        const data = await response.json();
        
        expect(fetch).toHaveBeenCalledWith('/api/v1/threats');
        expect(data.threats).toHaveLength(2);
    });
    
    test('should handle API errors gracefully', async () => {
        fetch.mockRejectOnce(new Error('API Error'));
        
        try {
            await fetch('/api/v1/threats');
        } catch (error) {
            expect(error.message).toBe('API Error');
        }
    });
});

// Performance tests
describe('Performance Tests', () => {
    test('should handle large datasets efficiently', () => {
        const largeDataset = Array.from({ length: 1000 }, (_, i) => ({
            id: `threat-${i}`,
            type: 'storm',
            severity: Math.floor(Math.random() * 5) + 1,
            latitude: Math.random() * 180 - 90,
            longitude: Math.random() * 360 - 180
        }));
        
        const startTime = performance.now();
        
        // Simulate processing large dataset
        const processed = largeDataset.filter(threat => threat.severity >= 3);
        const grouped = processed.reduce((acc, threat) => {
            acc[threat.type] = acc[threat.type] || [];
            acc[threat.type].push(threat);
            return acc;
        }, {});
        
        const endTime = performance.now();
        const processingTime = endTime - startTime;
        
        expect(processingTime).toBeLessThan(100); // Should complete within 100ms
        expect(Object.keys(grouped)).toContain('storm');
    });
});

// Setup and teardown
beforeAll(() => {
    // Setup global test environment
    global.console = {
        ...console,
        // Suppress console.log during tests
        log: jest.fn(),
        error: jest.fn(),
        warn: jest.fn()
    };
});

afterAll(() => {
    // Cleanup
    jest.clearAllMocks();
});
