/**
 * Toast Notification System
 * 
 * Système simple de notifications toast pour EEBC.
 * Requirements: 17.3, 19.1
 */

class ToastManager {
    constructor() {
        this.container = null;
        this.toasts = new Map();
        this.defaultDuration = 5000; // 5 secondes
        this.init();
    }

    init() {
        // Créer le conteneur de toasts s'il n'existe pas
        this.createContainer();
    }

    createContainer() {
        // Vérifier si le conteneur existe déjà
        this.container = document.getElementById('toast-container');
        
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.id = 'toast-container';
            this.container.className = 'toast-container position-fixed top-0 end-0 p-3';
            this.container.style.zIndex = '9999';
            document.body.appendChild(this.container);
        }
    }

    show(message, type = 'info', duration = null) {
        const toastId = this.generateId();
        const toast = this.createToast(toastId, message, type);
        
        // Ajouter au conteneur
        this.container.appendChild(toast);
        this.toasts.set(toastId, toast);

        // Animer l'apparition
        setTimeout(() => {
            toast.classList.add('show');
        }, 100);

        // Auto-fermeture
        const closeDuration = duration || this.defaultDuration;
        if (closeDuration > 0) {
            setTimeout(() => {
                this.hide(toastId);
            }, closeDuration);
        }

        return toastId;
    }

    createToast(id, message, type) {
        const toast = document.createElement('div');
        toast.id = `toast-${id}`;
        toast.className = `toast align-items-center text-bg-${this.getBootstrapClass(type)} border-0`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');

        const icon = this.getIcon(type);
        
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body d-flex align-items-center">
                    ${icon ? `<i class="${icon} me-2"></i>` : ''}
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" 
                        data-bs-dismiss="toast" aria-label="Close"
                        onclick="window.toastManager.hide('${id}')"></button>
            </div>
        `;

        return toast;
    }

    hide(toastId) {
        const toast = this.toasts.get(toastId);
        
        if (toast) {
            toast.classList.remove('show');
            
            // Supprimer après l'animation
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
                this.toasts.delete(toastId);
            }, 300);
        }
    }

    hideAll() {
        this.toasts.forEach((toast, id) => {
            this.hide(id);
        });
    }

    getBootstrapClass(type) {
        const classes = {
            'success': 'success',
            'error': 'danger',
            'warning': 'warning',
            'info': 'info',
            'primary': 'primary',
            'secondary': 'secondary'
        };
        
        return classes[type] || 'info';
    }

    getIcon(type) {
        const icons = {
            'success': 'bi bi-check-circle-fill',
            'error': 'bi bi-exclamation-triangle-fill',
            'warning': 'bi bi-exclamation-triangle-fill',
            'info': 'bi bi-info-circle-fill',
            'primary': 'bi bi-info-circle-fill',
            'secondary': 'bi bi-info-circle-fill'
        };
        
        return icons[type] || null;
    }

    generateId() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2);
    }

    // Méthodes de convenance
    success(message, duration = null) {
        return this.show(message, 'success', duration);
    }

    error(message, duration = null) {
        return this.show(message, 'error', duration);
    }

    warning(message, duration = null) {
        return this.show(message, 'warning', duration);
    }

    info(message, duration = null) {
        return this.show(message, 'info', duration);
    }
}

// Initialiser le gestionnaire de toasts
document.addEventListener('DOMContentLoaded', function() {
    window.toastManager = new ToastManager();
    
    // Fonction globale pour compatibilité
    window.showToast = function(message, type = 'info', duration = null) {
        return window.toastManager.show(message, type, duration);
    };
    
    // Fonctions de convenance globales
    window.showSuccess = function(message, duration = null) {
        return window.toastManager.success(message, duration);
    };
    
    window.showError = function(message, duration = null) {
        return window.toastManager.error(message, duration);
    };
    
    window.showWarning = function(message, duration = null) {
        return window.toastManager.warning(message, duration);
    };
    
    window.showInfo = function(message, duration = null) {
        return window.toastManager.info(message, duration);
    };
});

// Intégration avec les messages Django
document.addEventListener('DOMContentLoaded', function() {
    // Convertir les messages Django en toasts
    const djangoMessages = document.querySelectorAll('.django-messages .alert');
    
    djangoMessages.forEach(function(alert) {
        let type = 'info';
        
        if (alert.classList.contains('alert-success')) {
            type = 'success';
        } else if (alert.classList.contains('alert-danger')) {
            type = 'error';
        } else if (alert.classList.contains('alert-warning')) {
            type = 'warning';
        } else if (alert.classList.contains('alert-info')) {
            type = 'info';
        }
        
        const message = alert.textContent.trim();
        
        if (message && window.toastManager) {
            window.toastManager.show(message, type);
        }
        
        // Cacher le message Django original
        alert.style.display = 'none';
    });
});

// CSS pour les toasts (injecté dynamiquement)
const toastCSS = `
.toast-container {
    max-width: 400px;
}

.toast {
    opacity: 0;
    transform: translateX(100%);
    transition: all 0.3s ease-in-out;
}

.toast.show {
    opacity: 1;
    transform: translateX(0);
}

.toast-body {
    font-size: 0.9rem;
}

.toast .btn-close {
    font-size: 0.8rem;
}

/* Styles pour les différents types */
.toast.text-bg-success {
    background-color: #198754 !important;
    color: white !important;
}

.toast.text-bg-danger {
    background-color: #dc3545 !important;
    color: white !important;
}

.toast.text-bg-warning {
    background-color: #fd7e14 !important;
    color: white !important;
}

.toast.text-bg-info {
    background-color: #0dcaf0 !important;
    color: white !important;
}

/* Animation d'empilement */
.toast-container .toast + .toast {
    margin-top: 0.5rem;
}
`;

// Injecter le CSS
const style = document.createElement('style');
style.textContent = toastCSS;
document.head.appendChild(style);