/**
 * Ocean Sentinel - Service Worker
 * Handles push notifications and offline functionality
 */

const CACHE_NAME = 'ocean-sentinel-v1';
const STATIC_CACHE_URLS = [
    '/',
    '/css/dashboard.css',
    '/css/charts.css',
    '/css/responsive.css',
    '/js/dashboard.js',
    '/js/real_time.js',
    '/js/blockchain.js',
    '/js/charts.js',
    '/js/maps.js',
    '/js/alerts.js',
    '/js/threat_monitor.js',
    '/assets/favicon.ico',
    '/assets/apple-touch-icon.png'
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
    console.log('Service Worker: Installing...');
    
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                console.log('Service Worker: Caching static assets');
                return cache.addAll(STATIC_CACHE_URLS);
            })
            .then(() => {
                console.log('Service Worker: Installation complete');
                return self.skipWaiting();
            })
            .catch((error) => {
                console.error('Service Worker: Installation failed', error);
            })
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
    console.log('Service Worker: Activating...');
    
    event.waitUntil(
        caches.keys()
            .then((cacheNames) => {
                return Promise.all(
                    cacheNames
                        .filter((cacheName) => cacheName !== CACHE_NAME)
                        .map((cacheName) => {
                            console.log('Service Worker: Deleting old cache', cacheName);
                            return caches.delete(cacheName);
                        })
                );
            })
            .then(() => {
                console.log('Service Worker: Activation complete');
                return self.clients.claim();
            })
    );
});

// Fetch event - serve from cache, fallback to network
self.addEventListener('fetch', (event) => {
    // Skip non-GET requests
    if (event.request.method !== 'GET') {
        return;
    }
    
    // Skip API requests (let them go to network)
    if (event.request.url.includes('/api/')) {
        return;
    }
    
    event.respondWith(
        caches.match(event.request)
            .then((cachedResponse) => {
                // Return cached version if available
                if (cachedResponse) {
                    return cachedResponse;
                }
                
                // Fetch from network
                return fetch(event.request)
                    .then((response) => {
                        // Don't cache non-successful responses
                        if (!response || response.status !== 200 || response.type !== 'basic') {
                            return response;
                        }
                        
                        // Clone response for caching
                        const responseToCache = response.clone();
                        
                        caches.open(CACHE_NAME)
                            .then((cache) => {
                                cache.put(event.request, responseToCache);
                            });
                        
                        return response;
                    });
            })
            .catch(() => {
                // Fallback for offline scenarios
                if (event.request.destination === 'document') {
                    return caches.match('/');
                }
            })
    );
});

// Push event - handle push notifications
self.addEventListener('push', (event) => {
    console.log('Service Worker: Push notification received');
    
    let notificationData = {
        title: 'Ocean Sentinel Alert',
        body: 'New threat detected',
        icon: '/assets/icon-192x192.png',
        badge: '/assets/badge-72x72.png',
        tag: 'ocean-sentinel-alert',
        requireInteraction: false,
        data: {}
    };
    
    // Parse push data if available
    if (event.data) {
        try {
            const pushData = event.data.json();
            notificationData = {
                ...notificationData,
                ...pushData
            };
        } catch (error) {
            console.error('Service Worker: Error parsing push data', error);
        }
    }
    
    // Determine if notification should require interaction based on severity
    if (notificationData.data && notificationData.data.severity >= 4) {
        notificationData.requireInteraction = true;
    }
    
    event.waitUntil(
        self.registration.showNotification(notificationData.title, notificationData)
    );
});

// Notification click event
self.addEventListener('notificationclick', (event) => {
    console.log('Service Worker: Notification clicked');
    
    event.notification.close();
    
    const urlToOpen = event.notification.data?.url || '/';
    
    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true })
            .then((clientList) => {
                // Check if there's already a window/tab open
                for (const client of clientList) {
                    if (client.url === urlToOpen && 'focus' in client) {
                        return client.focus();
                    }
                }
                
                // Open new window/tab
                if (clients.openWindow) {
                    return clients.openWindow(urlToOpen);
                }
            })
    );
});

// Background sync for offline actions
self.addEventListener('sync', (event) => {
    console.log('Service Worker: Background sync triggered', event.tag);
    
    if (event.tag === 'threat-data-sync') {
        event.waitUntil(syncThreatData());
    }
});

// Sync threat data when online
async function syncThreatData() {
    try {
        // Get pending threat data from IndexedDB or cache
        const pendingData = await getPendingThreatData();
        
        if (pendingData.length > 0) {
            console.log(`Service Worker: Syncing ${pendingData.length} pending threat records`);
            
            // Send to API
            for (const data of pendingData) {
                try {
                    const response = await fetch('/api/v1/threats', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(data)
                    });
                    
                    if (response.ok) {
                        await removePendingThreatData(data.id);
                        console.log('Service Worker: Synced threat data', data.id);
                    }
                } catch (error) {
                    console.error('Service Worker: Failed to sync threat data', error);
                }
            }
        }
    } catch (error) {
        console.error('Service Worker: Background sync failed', error);
    }
}

// Helper functions for IndexedDB operations
async function getPendingThreatData() {
    // Simplified - in production, use IndexedDB
    return [];
}

async function removePendingThreatData(id) {
    // Simplified - in production, remove from IndexedDB
    console.log('Service Worker: Removed synced data', id);
}

// Message event - handle messages from main thread
self.addEventListener('message', (event) => {
    console.log('Service Worker: Message received', event.data);
    
    if (event.data && event.data.type) {
        switch (event.data.type) {
            case 'SKIP_WAITING':
                self.skipWaiting();
                break;
            case 'GET_VERSION':
                event.ports[0].postMessage({ version: CACHE_NAME });
                break;
            case 'CLEAR_CACHE':
                clearAllCaches();
                break;
            default:
                console.log('Service Worker: Unknown message type', event.data.type);
        }
    }
});

// Clear all caches
async function clearAllCaches() {
    try {
        const cacheNames = await caches.keys();
        await Promise.all(
            cacheNames.map(cacheName => caches.delete(cacheName))
        );
        console.log('Service Worker: All caches cleared');
    } catch (error) {
        console.error('Service Worker: Failed to clear caches', error);
    }
}
