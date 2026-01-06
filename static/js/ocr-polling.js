/**
 * OCR Polling JavaScript
 * 
 * Gère le polling AJAX pour vérifier le statut des tâches OCR en cours.
 * Requirements: 17.2
 */

class OCRPoller {
    constructor() {
        this.pollingInterval = 3000; // 3 secondes
        this.maxPollingTime = 300000; // 5 minutes max
        this.activePolls = new Map(); // Map<receiptId, pollData>
        this.init();
    }

    init() {
        // Démarrer le polling pour tous les justificatifs en cours
        this.startPollingForExistingReceipts();
        
        // Écouter les nouveaux uploads
        this.setupUploadListeners();
    }

    startPollingForExistingReceipts() {
        // Trouver tous les éléments avec statut "en_cours"
        const processingElements = document.querySelectorAll('[data-ocr-status="en_cours"]');
        
        processingElements.forEach(element => {
            const receiptId = element.dataset.receiptId;
            if (receiptId) {
                this.startPolling(parseInt(receiptId));
            }
        });
    }

    setupUploadListeners() {
        // Écouter les soumissions de formulaire d'upload
        const uploadForms = document.querySelectorAll('form[action*="receipt-proof-upload"]');
        
        uploadForms.forEach(form => {
            form.addEventListener('submit', (e) => {
                // Le polling sera démarré après redirection vers la liste
                // avec le paramètre highlight
                const urlParams = new URLSearchParams(window.location.search);
                const highlightId = urlParams.get('highlight');
                
                if (highlightId) {
                    this.startPolling(parseInt(highlightId));
                }
            });
        });
    }

    startPolling(receiptId) {
        if (this.activePolls.has(receiptId)) {
            return; // Déjà en cours
        }

        const pollData = {
            receiptId: receiptId,
            startTime: Date.now(),
            intervalId: null,
            element: document.querySelector(`[data-receipt-id="${receiptId}"]`)
        };

        if (!pollData.element) {
            console.warn(`Element not found for receipt ${receiptId}`);
            return;
        }

        // Démarrer le polling
        pollData.intervalId = setInterval(() => {
            this.checkOCRStatus(receiptId);
        }, this.pollingInterval);

        this.activePolls.set(receiptId, pollData);

        // Arrêter après le temps maximum
        setTimeout(() => {
            this.stopPolling(receiptId);
        }, this.maxPollingTime);

        console.log(`Started OCR polling for receipt ${receiptId}`);
    }

    stopPolling(receiptId) {
        const pollData = this.activePolls.get(receiptId);
        
        if (pollData && pollData.intervalId) {
            clearInterval(pollData.intervalId);
            this.activePolls.delete(receiptId);
            console.log(`Stopped OCR polling for receipt ${receiptId}`);
        }
    }

    async checkOCRStatus(receiptId) {
        try {
            const response = await fetch(`/finance/api/receipts/${receiptId}/ocr-status/`, {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Content-Type': 'application/json',
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();

            if (data.success) {
                this.updateOCRStatus(receiptId, data);

                // Arrêter le polling si terminé ou échoué
                if (data.status === 'termine' || data.status === 'echec') {
                    this.stopPolling(receiptId);
                    
                    // Afficher une notification
                    this.showOCRNotification(receiptId, data);
                }
            } else {
                console.error(`OCR status check failed for receipt ${receiptId}:`, data.error);
            }

        } catch (error) {
            console.error(`Error checking OCR status for receipt ${receiptId}:`, error);
        }
    }

    updateOCRStatus(receiptId, data) {
        const element = document.querySelector(`[data-receipt-id="${receiptId}"]`);
        
        if (!element) {
            return;
        }

        // Mettre à jour l'attribut de statut
        element.dataset.ocrStatus = data.status;

        // Mettre à jour l'affichage du statut
        const statusElement = element.querySelector('.ocr-status');
        if (statusElement) {
            statusElement.textContent = data.status_display;
            statusElement.className = `ocr-status status-${data.status}`;
        }

        // Mettre à jour les données extraites si disponibles
        if (data.status === 'termine') {
            const amountElement = element.querySelector('.ocr-amount');
            const dateElement = element.querySelector('.ocr-date');
            const confidenceElement = element.querySelector('.ocr-confidence');

            if (amountElement && data.extracted_amount) {
                amountElement.textContent = `${data.extracted_amount}€`;
                amountElement.style.display = 'inline';
            }

            if (dateElement && data.extracted_date) {
                dateElement.textContent = data.extracted_date;
                dateElement.style.display = 'inline';
            }

            if (confidenceElement && data.confidence) {
                confidenceElement.textContent = `${data.confidence}%`;
                confidenceElement.style.display = 'inline';
            }
        }

        // Mettre à jour l'indicateur de progression
        this.updateProgressIndicator(receiptId, data.status);
    }

    updateProgressIndicator(receiptId, status) {
        const progressElement = document.querySelector(`[data-receipt-id="${receiptId}"] .ocr-progress`);
        
        if (!progressElement) {
            return;
        }

        switch (status) {
            case 'non_traite':
                progressElement.innerHTML = '<span class="badge badge-secondary">Non traité</span>';
                break;
            case 'en_cours':
                progressElement.innerHTML = `
                    <div class="d-flex align-items-center">
                        <div class="spinner-border spinner-border-sm me-2" role="status">
                            <span class="visually-hidden">Traitement en cours...</span>
                        </div>
                        <span class="text-info">Traitement en cours...</span>
                    </div>
                `;
                break;
            case 'termine':
                progressElement.innerHTML = '<span class="badge badge-success">✓ Terminé</span>';
                break;
            case 'echec':
                progressElement.innerHTML = `
                    <div class="d-flex align-items-center">
                        <span class="badge badge-danger me-2">✗ Échec</span>
                        <button class="btn btn-sm btn-outline-primary retry-ocr-btn" 
                                data-receipt-id="${receiptId}">
                            Relancer
                        </button>
                    </div>
                `;
                
                // Ajouter l'événement de relance
                const retryBtn = progressElement.querySelector('.retry-ocr-btn');
                if (retryBtn) {
                    retryBtn.addEventListener('click', () => {
                        this.retryOCR(receiptId);
                    });
                }
                break;
        }
    }

    showOCRNotification(receiptId, data) {
        let message, type;

        if (data.status === 'termine') {
            message = `OCR terminé pour le justificatif #${receiptId}`;
            if (data.extracted_amount) {
                message += ` - Montant détecté: ${data.extracted_amount}€`;
            }
            type = 'success';
        } else if (data.status === 'echec') {
            message = `OCR échoué pour le justificatif #${receiptId}`;
            type = 'error';
        }

        // Utiliser le système de toasts s'il existe, sinon alert
        if (window.showToast) {
            window.showToast(message, type);
        } else {
            // Fallback: notification native du navigateur
            if ('Notification' in window && Notification.permission === 'granted') {
                new Notification('OCR EEBC', {
                    body: message,
                    icon: '/static/icons/icon-96x96.png'
                });
            } else {
                console.log(message);
            }
        }
    }

    async retryOCR(receiptId) {
        try {
            const response = await fetch(`/finance/receipts/${receiptId}/process-ocr/`, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': this.getCSRFToken(),
                }
            });

            if (response.ok) {
                // Redémarrer le polling
                this.startPolling(receiptId);
                
                if (window.showToast) {
                    window.showToast(`OCR relancé pour le justificatif #${receiptId}`, 'info');
                }
            } else {
                throw new Error(`HTTP ${response.status}`);
            }

        } catch (error) {
            console.error(`Error retrying OCR for receipt ${receiptId}:`, error);
            
            if (window.showToast) {
                window.showToast(`Erreur lors de la relance de l'OCR`, 'error');
            }
        }
    }

    getCSRFToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    }

    // Méthode publique pour démarrer le polling manuellement
    static startPollingForReceipt(receiptId) {
        if (window.ocrPoller) {
            window.ocrPoller.startPolling(receiptId);
        }
    }

    // Méthode publique pour arrêter le polling manuellement
    static stopPollingForReceipt(receiptId) {
        if (window.ocrPoller) {
            window.ocrPoller.stopPolling(receiptId);
        }
    }
}

// Initialiser le poller quand le DOM est prêt
document.addEventListener('DOMContentLoaded', function() {
    window.ocrPoller = new OCRPoller();
    
    // Demander la permission pour les notifications
    if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
    }
});

// Exporter pour utilisation globale
window.OCRPoller = OCRPoller;