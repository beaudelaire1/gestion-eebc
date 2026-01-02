/**
 * Service Worker pour EEBC PWA
 * 
 * Gère le cache et le mode offline
 */

const CACHE_NAME = 'eebc-cache-v1';
const OFFLINE_URL = '/offline/';

// Ressources à mettre en cache immédiatement
const PRECACHE_URLS = [
    '/',
    '/offline/',
    '/static/manifest.json',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css',
    'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css',
    'https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js',
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
        }).then(() => self.clients.claim())
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
