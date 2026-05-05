/**
 * Service Worker pour EEBC PWA
 * 
 * Gère le cache et le mode offline
 */

const CACHE_NAME = 'eebc-cache-v5';
const OFFLINE_URL = '/offline/';

// Ressources à mettre en cache immédiatement
const PRECACHE_URLS = [
    '/',
    '/offline/',
    '/static/manifest.json',
    '/static/vendor/bootstrap/bootstrap.min.css',
    '/static/vendor/bootstrap/bootstrap.bundle.min.js',
    '/static/vendor/bootstrap-icons/bootstrap-icons.css',
    '/static/css/public.css',
    '/static/css/luxe-design.css',
    '/static/css/animated-verse-banner.css',
];

// Installation du Service Worker
self.addEventListener('install', event => {
    console.log('[SW] Installation...');
    
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('[SW] Mise en cache des ressources');
                return cache.addAll(PRECACHE_URLS);
            })
            .then(() => self.skipWaiting())
    );
});

// Activation du Service Worker
self.addEventListener('activate', event => {
    console.log('[SW] Activation...');
    
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames
                    .filter(cacheName => cacheName !== CACHE_NAME)
                    .map(cacheName => {
                        console.log('[SW] Suppression ancien cache:', cacheName);
                        return caches.delete(cacheName);
                    })
            );
        })
        .then(() => self.clients.claim())
        .then(() => self.clients.matchAll({ type: 'window', includeUncontrolled: true }))
        .then(clients => {
            return Promise.all(clients.map(client => {
                const clientUrl = new URL(client.url);
                if (clientUrl.pathname.startsWith('/admin/') ||
                    clientUrl.pathname.startsWith('/app/') ||
                    clientUrl.pathname.includes('/api/')) {
                    return Promise.resolve();
                }
                return client.navigate(client.url);
            }));
        })
    );
});

// Interception des requêtes
self.addEventListener('fetch', event => {
    // Ignorer les requêtes non-GET
    if (event.request.method !== 'GET') {
        return;
    }
    
    // Ignorer les requêtes vers l'admin et l'API
    const url = new URL(event.request.url);
    if (url.pathname.startsWith('/admin/') || 
        url.pathname.startsWith('/app/') ||
        url.pathname.includes('/api/')) {
        return;
    }

    if (event.request.headers.get('accept')?.includes('text/html')) {
        event.respondWith(
            fetch(event.request)
                .then(response => {
                    if (response && response.status === 200 && response.type === 'basic') {
                        const responseToCache = response.clone();
                        caches.open(CACHE_NAME).then(cache => {
                            cache.put(event.request, responseToCache);
                        });
                    }
                    return response;
                })
                .catch(() => caches.match(event.request).then(cachedResponse => {
                    return cachedResponse || caches.match(OFFLINE_URL);
                }))
        );
        return;
    }
    
    event.respondWith(
        caches.match(event.request)
            .then(cachedResponse => {
                if (cachedResponse) {
                    // Retourner depuis le cache
                    return cachedResponse;
                }
                
                // Sinon, faire la requête réseau
                return fetch(event.request)
                    .then(response => {
                        // Ne pas mettre en cache les réponses non valides
                        if (!response || response.status !== 200 || response.type !== 'basic') {
                            return response;
                        }
                        
                        // Cloner la réponse pour le cache
                        const responseToCache = response.clone();
                        
                        // Mettre en cache les pages HTML et ressources statiques
                        if (event.request.url.includes('/static/') ||
                            event.request.headers.get('accept').includes('text/html')) {
                            caches.open(CACHE_NAME)
                                .then(cache => {
                                    cache.put(event.request, responseToCache);
                                });
                        }
                        
                        return response;
                    })
                    .catch(() => {
                        // En cas d'erreur réseau, afficher la page offline
                        if (event.request.headers.get('accept').includes('text/html')) {
                            return caches.match(OFFLINE_URL);
                        }
                    });
            })
    );
});

// Gestion des notifications push (préparé pour futur)
self.addEventListener('push', event => {
    console.log('[SW] Notification push reçue');
    
    const options = {
        body: event.data ? event.data.text() : 'Nouvelle notification EEBC',
        icon: '/static/icons/icon-192x192.png',
        badge: '/static/icons/icon-72x72.png',
        vibrate: [100, 50, 100],
        data: {
            dateOfArrival: Date.now(),
            primaryKey: 1
        },
        actions: [
            {action: 'explore', title: 'Voir'},
            {action: 'close', title: 'Fermer'},
        ]
    };
    
    event.waitUntil(
        self.registration.showNotification('EEBC', options)
    );
});

// Clic sur notification
self.addEventListener('notificationclick', event => {
    console.log('[SW] Clic sur notification');
    
    event.notification.close();
    
    if (event.action === 'explore') {
        event.waitUntil(
            clients.openWindow('/')
        );
    }
});

// Synchronisation en arrière-plan (préparé pour futur)
self.addEventListener('sync', event => {
    console.log('[SW] Sync event:', event.tag);
    
    if (event.tag === 'sync-data') {
        event.waitUntil(syncData());
    }
});

async function syncData() {
    // Synchroniser les données en attente
    console.log('[SW] Synchronisation des données...');
}
