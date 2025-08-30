/**
 * Ocean Sentinel - Real-time Data Management
 * Pusher and Supabase real-time integration
 */

class RealTimeManager {
    constructor() {
        this.pusher = null;
        this.supabase = null;
        this.channels = new Map();
        this.subscriptions = new Map();
        
        this.config = {
            pusherKey: window.PUSHER_KEY,
            pusherCluster: window.PUSHER_CLUSTER || 'us2',
            supabaseUrl: window.SUPABASE_URL,
            supabaseAnonKey: window.SUPABASE_ANON_KEY,
            reconnectAttempts: 5,
            reconnectDelay: 1000
        };
        
        this.eventHandlers = new Map();
        this.connectionStatus = {
            pusher: 'disconnected',
            supabase: 'disconnected'
        };
        
        this.init();
    }
    
    async init() {
        try {
            console.log('🔄 Initializing real-time connections...');
            
            await this.initializePusher();
            await this.initializeSupabase();
            
            this.setupConnectionMonitoring();
            this.setupDefaultChannels();
            
            console.log('✅ Real-time connections established');
            
        } catch (error) {
            console.error('❌ Failed to initialize real-time connections:', error);
        }
    }
    
    async initializePusher() {
        if (!this.config.pusherKey) {
            console.warn('⚠️ Pusher key not configured');
            return;
        }
        
        this.pusher = new Pusher(this.config.pusherKey, {
            cluster: this.config.pusherCluster,
            encrypted: true,
            enabledTransports: ['ws', 'wss'],
            disabledTransports: ['xhr_polling', 'xhr_streaming']
        });
        
        this.pusher.connection.bind('connected', () => {
            this.connectionStatus.pusher = 'connected';
            console.log('✅ Pusher connected');
            this.emit('pusher:connected');
        });
        
        this.pusher.connection.bind('disconnected', () => {
            this.connectionStatus.pusher = 'disconnected';
            console.log('⚠️ Pusher disconnected');
            this.emit('pusher:disconnected');
        });
        
        this.pusher.connection.bind('error', (error) => {
            console.error('❌ Pusher connection error:', error);
            this.emit('pusher:error', error);
        });
    }
    
    async initializeSupabase() {
        if (!this.config.supabaseUrl || !this.config.supabaseAnonKey) {
            console.warn('⚠️ Supabase credentials not configured');
            return;
        }
        
        this.supabase = supabase.createClient(
            this.config.supabaseUrl,
            this.config.supabaseAnonKey
        );
        
        // Test connection
        try {
            const { data, error } = await this.supabase
                .from('threats')
                .select('count', { count: 'exact', head: true });
            
            if (!error) {
                this.connectionStatus.supabase = 'connected';
                console.log('✅ Supabase connected');
                this.emit('supabase:connected');
            }
        } catch (error) {
            console.error('❌ Supabase connection error:', error);
            this.emit('supabase:error', error);
        }
    }
    
    setupConnectionMonitoring() {
        // Monitor connection health
        setInterval(() => {
            this.checkConnectionHealth();
        }, 30000); // Check every 30 seconds
        
        // Handle page visibility changes
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) {
                this.reconnectAll();
            }
        });
        
        // Handle online/offline events
        window.addEventListener('online', () => {
            console.log('📶 Network online - reconnecting...');
            this.reconnectAll();
        });
        
        window.addEventListener('offline', () => {
            console.log('📵 Network offline');
            this.emit('network:offline');
        });
    }
    
    setupDefaultChannels() {
        // Subscribe to global threat alerts
        this.subscribeToThreatAlerts();
        
        // Subscribe to system updates
        this.subscribeToSystemUpdates();
        
        // Subscribe to environmental data updates
        this.subscribeToEnvironmentalUpdates();
        
        // Setup Supabase real-time subscriptions
        this.setupSupabaseSubscriptions();
    }
    
    subscribeToThreatAlerts() {
        if (!this.pusher) return;
        
        const channel = this.pusher.subscribe('threat-alerts');
        this.channels.set('threat-alerts', channel);
        
        channel.bind('new-threat', (data) => {
            console.log('🚨 New threat alert received:', data);
            this.emit('threat:new', data);
            this.handleThreatAlert(data);
        });
        
        channel.bind('threat-updated', (data) => {
            console.log('📝 Threat updated:', data);
            this.emit('threat:updated', data);
        });
        
        channel.bind('threat-resolved', (data) => {
            console.log('✅ Threat resolved:', data);
            this.emit('threat:resolved', data);
        });
    }
    
    subscribeToSystemUpdates() {
        if (!this.pusher) return;
        
        const channel = this.pusher.subscribe('system-updates');
        this.channels.set('system-updates', channel);
        
        channel.bind('data-collection-complete', (data) => {
            console.log('📊 Data collection completed:', data);
            this.emit('data:collected', data);
        });
        
        channel.bind('system-maintenance', (data) => {
            console.log('🔧 System maintenance notification:', data);
            this.emit('system:maintenance', data);
        });
        
        channel.bind('alert-sent', (data) => {
            console.log('📤 Alert sent notification:', data);
            this.emit('alert:sent', data);
        });
    }
    
    subscribeToEnvironmentalUpdates() {
        if (!this.pusher) return;
        
        const channel = this.pusher.subscribe('environmental-updates');
        this.channels.set('environmental-updates', channel);
        
        channel.bind('data-update', (data) => {
            console.log('🌡️ Environmental data updated:', data);
            this.emit('environmental:updated', data);
        });
        
        channel.bind('anomaly-detected', (data) => {
            console.log('⚠️ Environmental anomaly detected:', data);
            this.emit('environmental:anomaly', data);
        });
    }
    
    setupSupabaseSubscriptions() {
        if (!this.supabase) return;
        
        // Subscribe to threats table changes
        const threatsSubscription = this.supabase
            .channel('threats-changes')
            .on('postgres_changes', 
                { event: '*', schema: 'public', table: 'threats' },
                (payload) => {
                    console.log('🔄 Threats table changed:', payload);
                    this.handleSupabaseChange('threats', payload);
                }
            )
            .subscribe();
        
        this.subscriptions.set('threats', threatsSubscription);
        
        // Subscribe to alerts table changes
        const alertsSubscription = this.supabase
            .channel('alerts-changes')
            .on('postgres_changes',
                { event: '*', schema: 'public', table: 'alert_notifications' },
                (payload) => {
                    console.log('🔄 Alerts table changed:', payload);
                    this.handleSupabaseChange('alerts', payload);
                }
            )
            .subscribe();
        
        this.subscriptions.set('alerts', alertsSubscription);
        
        // Subscribe to environmental data changes
        const environmentalSubscription = this.supabase
            .channel('environmental-changes')
            .on('postgres_changes',
                { event: 'INSERT', schema: 'public', table: 'environmental_data_summary' },
                (payload) => {
                    console.log('🔄 Environmental data updated:', payload);
                    this.handleSupabaseChange('environmental', payload);
                }
            )
            .subscribe();
        
        this.subscriptions.set('environmental', environmentalSubscription);
    }
    
    subscribeToLocationUpdates(latitude, longitude, radius = 50) {
        if (!this.pusher) return null;
        
        const locationKey = `${Math.round(latitude)}_${Math.round(longitude)}`;
        const channelName = `location-${locationKey}`;
        
        if (this.channels.has(channelName)) {
            return this.channels.get(channelName);
        }
        
        const channel = this.pusher.subscribe(channelName);
        this.channels.set(channelName, channel);
        
        channel.bind('local-threat', (data) => {
            console.log(`📍 Local threat near ${locationKey}:`, data);
            this.emit('threat:local', { ...data, location: { latitude, longitude } });
        });
        
        channel.bind('local-alert', (data) => {
            console.log(`🚨 Local alert near ${locationKey}:`, data);
            this.emit('alert:local', { ...data, location: { latitude, longitude } });
        });
        
        return channel;
    }
    
    handleThreatAlert(data) {
        const threat = data.threat;
        
        // Check if threat is high severity
        if (threat.severity >= 4) {
            // Show critical alert notification
            this.showCriticalAlert(threat);
            
            // Play alert sound if enabled
            this.playAlertSound(threat.severity);
            
            // Send browser notification if permitted
            this.sendBrowserNotification(threat);
        }
        
        // Update any active dashboards
        if (window.dashboard) {
            window.dashboard.handleNewThreat(data);
        }
    }
    
    handleSupabaseChange(table, payload) {
        const { eventType, new: newRecord, old: oldRecord } = payload;
        
        switch (table) {
            case 'threats':
                if (eventType === 'INSERT') {
                    this.emit('threat:created', newRecord);
                } else if (eventType === 'UPDATE') {
                    this.emit('threat:updated', { old: oldRecord, new: newRecord });
                } else if (eventType === 'DELETE') {
                    this.emit('threat:deleted', oldRecord);
                }
                break;
                
            case 'alerts':
                if (eventType === 'INSERT') {
                    this.emit('alert:created', newRecord);
                } else if (eventType === 'UPDATE') {
                    this.emit('alert:updated', { old: oldRecord, new: newRecord });
                }
                break;
                
            case 'environmental':
                if (eventType === 'INSERT') {
                    this.emit('environmental:new', newRecord);
                }
                break;
        }
    }
    
    showCriticalAlert(threat) {
        // Create critical alert overlay
        const alertOverlay = document.createElement('div');
        alertOverlay.className = 'critical-alert-overlay';
        alertOverlay.innerHTML = `
            <div class="critical-alert">
                <div class="alert-header">
                    <h2>🚨 CRITICAL THREAT ALERT</h2>
                    <button class="close-alert" onclick="this.parentElement.parentElement.parentElement.remove()">×</button>
                </div>
                <div class="alert-content">
                    <h3>${threat.type.toUpperCase()} THREAT DETECTED</h3>
                    <p><strong>Severity:</strong> ${threat.severity}/5 (${['', 'Minor', 'Moderate', 'Significant', 'Dangerous', 'Extreme'][threat.severity]})</p>
                    <p><strong>Confidence:</strong> ${Math.round(threat.confidence * 100)}%</p>
                    <p><strong>Location:</strong> ${threat.latitude?.toFixed(4)}, ${threat.longitude?.toFixed(4)}</p>
                    <p><strong>Description:</strong> ${threat.description}</p>
                    <p><strong>Recommendation:</strong> ${threat.recommendation || 'Follow local emergency guidelines'}</p>
                </div>
                <div class="alert-actions">
                    <button onclick="window.dashboard?.viewThreatDetails('${threat.id}')">View Details</button>
                    <button onclick="this.parentElement.parentElement.parentElement.remove()">Dismiss</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(alertOverlay);
        
        // Auto-remove after 30 seconds
        setTimeout(() => {
            if (alertOverlay.parentElement) {
                alertOverlay.remove();
            }
        }, 30000);
    }
    
    playAlertSound(severity) {
        try {
            // Create audio context if not exists
            if (!this.audioContext) {
                this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            }
            
            // Generate alert tone based on severity
            const frequency = 440 + (severity * 110); // Higher frequency for higher severity
            const duration = 0.5 + (severity * 0.2); // Longer duration for higher severity
            
            const oscillator = this.audioContext.createOscillator();
            const gainNode = this.audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(this.audioContext.destination);
            
            oscillator.frequency.value = frequency;
            oscillator.type = 'sine';
            
            gainNode.gain.setValueAtTime(0, this.audioContext.currentTime);
            gainNode.gain.linearRampToValueAtTime(0.3, this.audioContext.currentTime + 0.1);
            gainNode.gain.linearRampToValueAtTime(0, this.audioContext.currentTime + duration);
            
            oscillator.start(this.audioContext.currentTime);
            oscillator.stop(this.audioContext.currentTime + duration);
            
        } catch (error) {
            console.warn('Could not play alert sound:', error);
        }
    }
    
    async sendBrowserNotification(threat) {
        if (!('Notification' in window)) return;
        
        if (Notification.permission === 'granted') {
            new Notification(`${threat.type.toUpperCase()} Threat Alert`, {
                body: `Severity ${threat.severity}/5 - ${threat.description}`,
                icon: '/assets/ocean-sentinel-icon.png',
                badge: '/assets/threat-badge.png',
                tag: `threat-${threat.id}`,
                requireInteraction: threat.severity >= 4
            });
        } else if (Notification.permission !== 'denied') {
            const permission = await Notification.requestPermission();
            if (permission === 'granted') {
                this.sendBrowserNotification(threat);
            }
        }
    }
    
    checkConnectionHealth() {
        // Check Pusher connection
        if (this.pusher && this.pusher.connection.state !== 'connected') {
            console.warn('⚠️ Pusher connection unhealthy, attempting reconnect...');
            this.reconnectPusher();
        }
        
        // Check Supabase connection with a simple query
        if (this.supabase) {
            this.supabase
                .from('threats')
                .select('count', { count: 'exact', head: true })
                .then(({ error }) => {
                    if (error) {
                        console.warn('⚠️ Supabase connection unhealthy:', error);
                        this.emit('supabase:error', error);
                    }
                });
        }
    }
    
    async reconnectAll() {
        console.log('🔄 Reconnecting all real-time services...');
        
        try {
            await this.reconnectPusher();
            await this.reconnectSupabase();
        } catch (error) {
            console.error('❌ Reconnection failed:', error);
        }
    }
    
    async reconnectPusher() {
        if (!this.pusher) return;
        
        try {
            if (this.pusher.connection.state !== 'connected') {
                this.pusher.connect();
            }
        } catch (error) {
            console.error('❌ Pusher reconnection failed:', error);
        }
    }
    
    async reconnectSupabase() {
        if (!this.supabase) return;
        
        try {
            // Recreate Supabase client
            this.supabase = supabase.createClient(
                this.config.supabaseUrl,
                this.config.supabaseAnonKey
            );
            
            // Reestablish subscriptions
            this.subscriptions.forEach((subscription, key) => {
                subscription.unsubscribe();
            });
            this.subscriptions.clear();
            
            this.setupSupabaseSubscriptions();
            
        } catch (error) {
            console.error('❌ Supabase reconnection failed:', error);
        }
    }
    
    // Event emitter methods
    on(event, callback) {
        if (!this.eventHandlers.has(event)) {
            this.eventHandlers.set(event, []);
        }
        this.eventHandlers.get(event).push(callback);
    }
    
    off(event, callback) {
        if (this.eventHandlers.has(event)) {
            const handlers = this.eventHandlers.get(event);
            const index = handlers.indexOf(callback);
            if (index > -1) {
                handlers.splice(index, 1);
            }
        }
    }
    
    emit(event, data = null) {
        if (this.eventHandlers.has(event)) {
            this.eventHandlers.get(event).forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`Error in event handler for ${event}:`, error);
                }
            });
        }
    }
    
    getConnectionStatus() {
        return {
            pusher: this.connectionStatus.pusher,
            supabase: this.connectionStatus.supabase,
            overall: this.connectionStatus.pusher === 'connected' && 
                    this.connectionStatus.supabase === 'connected' ? 'connected' : 'degraded'
        };
    }
    
    cleanup() {
        console.log('🧹 Cleaning up real-time connections...');
        
        // Disconnect Pusher
        if (this.pusher) {
            this.channels.forEach(channel => {
                this.pusher.unsubscribe(channel.name);
            });
            this.pusher.disconnect();
        }
        
        // Unsubscribe from Supabase channels
        this.subscriptions.forEach(subscription => {
            subscription.unsubscribe();
        });
        
        // Clear event handlers
        this.eventHandlers.clear();
        this.channels.clear();
        this.subscriptions.clear();
    }
}

// Global real-time manager instance
window.realTimeManager = new RealTimeManager();

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.realTimeManager) {
        window.realTimeManager.cleanup();
    }
});
