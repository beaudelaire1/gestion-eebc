/**
 * EEBC Theme Manager
 * Gère les différents modes de thème du dashboard
 */

class ThemeManager {
    constructor() {
        this.themes = [
            // Thèmes clairs
            { id: 'default', name: 'Default', icon: 'bi-circle', description: 'Thème Bootstrap standard' },
            { id: 'cerulean', name: 'Cerulean', icon: 'bi-water', description: 'Thème bleu ciel apaisant' },
            { id: 'cosmo', name: 'Cosmo', icon: 'bi-stars', description: 'Thème moderne et épuré' },
            { id: 'flatly', name: 'Flatly', icon: 'bi-square', description: 'Design plat et coloré' },
            { id: 'journal', name: 'Journal', icon: 'bi-journal-text', description: 'Style journal élégant' },
            { id: 'litera', name: 'Litera', icon: 'bi-book', description: 'Thème littéraire classique' },
            { id: 'lumen', name: 'Lumen', icon: 'bi-lightbulb', description: 'Thème lumineux et clair' },
            { id: 'lux', name: 'Lux', icon: 'bi-gem', description: 'Thème luxueux et raffiné' },
            { id: 'materia', name: 'Materia', icon: 'bi-layers', description: 'Material Design Google' },
            { id: 'minty', name: 'Minty', icon: 'bi-flower1', description: 'Thème menthe fraîche' },
            { id: 'pulse', name: 'Pulse', icon: 'bi-heart-pulse', description: 'Thème violet dynamique' },
            { id: 'sandstone', name: 'Sandstone', icon: 'bi-mountain', description: 'Thème terre et nature' },
            { id: 'simplex', name: 'Simplex', icon: 'bi-dash-circle', description: 'Simplicité et efficacité' },
            { id: 'sketchy', name: 'Sketchy', icon: 'bi-pencil', description: 'Style dessiné à la main' },
            { id: 'spacelab', name: 'Spacelab', icon: 'bi-rocket', description: 'Thème spatial futuriste' },
            { id: 'united', name: 'United', icon: 'bi-flag', description: 'Thème orange Ubuntu' },
            { id: 'yeti', name: 'Yeti', icon: 'bi-snow', description: 'Thème bleu glacier' },
            
            // Thèmes sombres
            { id: 'darkly', name: 'Darkly', icon: 'bi-moon', description: 'Bootstrap sombre élégant' },
            { id: 'cyborg', name: 'Cyborg', icon: 'bi-robot', description: 'Thème cyberpunk futuriste' },
            { id: 'slate', name: 'Slate', icon: 'bi-tablet', description: 'Ardoise moderne et sobre' },
            { id: 'solar', name: 'Solar', icon: 'bi-sun', description: 'Thème solarisé contrasté' },
            { id: 'superhero', name: 'Superhero', icon: 'bi-lightning-charge', description: 'Thème super-héros sombre' }
        ];
        
        this.currentTheme = this.getStoredTheme() || this.getSystemTheme();
        this.init();
    }

    init() {
        this.applyTheme(this.currentTheme);
        this.createThemeSelector();
        this.bindEvents();
        this.updateChartColors();
    }

    getStoredTheme() {
        return localStorage.getItem('eebc-theme');
    }

    getSystemTheme() {
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }

    applyTheme(themeId) {
        document.documentElement.setAttribute('data-theme', themeId);
        this.currentTheme = themeId;
        localStorage.setItem('eebc-theme', themeId);
        
        // Mettre à jour l'icône du bouton principal
        this.updateThemeButton();
        
        // Déclencher un événement personnalisé pour les composants qui en ont besoin
        window.dispatchEvent(new CustomEvent('themeChanged', { 
            detail: { theme: themeId } 
        }));
        
        // Mettre à jour les couleurs des graphiques
        setTimeout(() => this.updateChartColors(), 100);
    }

    updateThemeButton() {
        const themeButton = document.getElementById('themeToggle');
        const currentThemeData = this.themes.find(t => t.id === this.currentTheme);
        
        if (themeButton && currentThemeData) {
            const icon = themeButton.querySelector('i');
            if (icon) {
                // Supprimer toutes les classes d'icônes existantes
                icon.className = icon.className.replace(/bi-[a-z-]+/g, '');
                icon.classList.add(currentThemeData.icon);
            }
            
            // Mettre à jour le tooltip
            themeButton.setAttribute('title', `Thème actuel: ${currentThemeData.name}`);
        }
    }

    createThemeSelector() {
        const existingSelector = document.getElementById('themeSelector');
        if (existingSelector) {
            existingSelector.remove();
        }

        const selector = document.createElement('div');
        selector.id = 'themeSelector';
        selector.className = 'theme-selector';
        selector.innerHTML = `
            <div class="theme-selector__content">
                <div class="theme-selector__header">
                    <h6 class="theme-selector__title">
                        <i class="bi bi-palette me-2"></i>
                        Choisir un thème
                    </h6>
                    <button class="theme-selector__close" onclick="themeManager.hideThemeSelector()">
                        <i class="bi bi-x"></i>
                    </button>
                </div>
                <div class="theme-selector__grid">
                    ${this.themes.map(theme => `
                        <div class="theme-option ${theme.id === this.currentTheme ? 'theme-option--active' : ''}" 
                             data-theme="${theme.id}"
                             onclick="themeManager.selectTheme('${theme.id}')">
                            <div class="theme-option__preview" data-preview-theme="${theme.id}">
                                <div class="theme-option__preview-header"></div>
                                <div class="theme-option__preview-content">
                                    <div class="theme-option__preview-card"></div>
                                    <div class="theme-option__preview-card"></div>
                                </div>
                            </div>
                            <div class="theme-option__info">
                                <div class="theme-option__name">
                                    <i class="bi ${theme.icon} me-2"></i>
                                    ${theme.name}
                                </div>
                                <div class="theme-option__description">${theme.description}</div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;

        document.body.appendChild(selector);
    }

    showThemeSelector() {
        const selector = document.getElementById('themeSelector');
        if (selector) {
            selector.classList.add('theme-selector--visible');
            document.body.classList.add('theme-selector-open');
        }
    }

    hideThemeSelector() {
        const selector = document.getElementById('themeSelector');
        if (selector) {
            selector.classList.remove('theme-selector--visible');
            document.body.classList.remove('theme-selector-open');
        }
    }

    selectTheme(themeId) {
        // Mettre à jour l'état actif
        document.querySelectorAll('.theme-option').forEach(option => {
            option.classList.remove('theme-option--active');
        });
        
        const selectedOption = document.querySelector(`[data-theme="${themeId}"]`);
        if (selectedOption) {
            selectedOption.classList.add('theme-option--active');
        }

        // Appliquer le thème
        this.applyTheme(themeId);

        // Fermer le sélecteur après un délai
        setTimeout(() => {
            this.hideThemeSelector();
        }, 500);

        // Afficher une notification
        this.showThemeNotification(themeId);
    }

    showThemeNotification(themeId) {
        const themeData = this.themes.find(t => t.id === themeId);
        if (!themeData) return;

        // Supprimer les notifications existantes
        document.querySelectorAll('.theme-notification').forEach(n => n.remove());

        const notification = document.createElement('div');
        notification.className = 'theme-notification';
        notification.innerHTML = `
            <div class="theme-notification__content">
                <i class="bi ${themeData.icon} me-2"></i>
                Thème "${themeData.name}" appliqué
            </div>
        `;

        document.body.appendChild(notification);

        // Animation d'entrée
        setTimeout(() => {
            notification.classList.add('theme-notification--visible');
        }, 10);

        // Suppression automatique
        setTimeout(() => {
            notification.classList.remove('theme-notification--visible');
            setTimeout(() => notification.remove(), 300);
        }, 2000);
    }

    bindEvents() {
        // Écouter les changements de préférence système
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            if (!this.getStoredTheme()) {
                this.applyTheme(e.matches ? 'dark' : 'light');
            }
        });

        // Fermer le sélecteur en cliquant à l'extérieur
        document.addEventListener('click', (e) => {
            const selector = document.getElementById('themeSelector');
            const themeButton = document.getElementById('themeToggle');
            
            if (selector && selector.classList.contains('theme-selector--visible')) {
                if (!selector.contains(e.target) && !themeButton.contains(e.target)) {
                    this.hideThemeSelector();
                }
            }
        });

        // Raccourci clavier pour ouvrir le sélecteur de thème
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.shiftKey && e.key === 'T') {
                e.preventDefault();
                this.showThemeSelector();
            }
        });
    }

    updateChartColors() {
        // Mettre à jour les couleurs des graphiques Chart.js
        if (window.Chart && window.Chart.instances) {
            const computedStyle = getComputedStyle(document.documentElement);
            const primaryColor = computedStyle.getPropertyValue('--accent-primary').trim();
            const successColor = computedStyle.getPropertyValue('--accent-success').trim();
            const warningColor = computedStyle.getPropertyValue('--accent-warning').trim();
            const dangerColor = computedStyle.getPropertyValue('--accent-danger').trim();
            const textColor = computedStyle.getPropertyValue('--text-primary').trim();

            Object.values(window.Chart.instances).forEach(chart => {
                if (chart && chart.data) {
                    // Mettre à jour les couleurs des datasets
                    chart.data.datasets.forEach(dataset => {
                        if (dataset.backgroundColor) {
                            if (Array.isArray(dataset.backgroundColor)) {
                                dataset.backgroundColor = [primaryColor, successColor, warningColor, dangerColor];
                            } else {
                                dataset.backgroundColor = primaryColor;
                            }
                        }
                        if (dataset.borderColor) {
                            dataset.borderColor = primaryColor;
                        }
                    });

                    // Mettre à jour les couleurs des axes
                    if (chart.options.scales) {
                        Object.values(chart.options.scales).forEach(scale => {
                            if (scale.ticks) {
                                scale.ticks.color = textColor;
                            }
                            if (scale.grid) {
                                scale.grid.color = computedStyle.getPropertyValue('--border-color').trim();
                            }
                        });
                    }

                    chart.update();
                }
            });
        }
    }

    // Méthode pour obtenir les couleurs du thème actuel
    getThemeColors() {
        const computedStyle = getComputedStyle(document.documentElement);
        return {
            primary: computedStyle.getPropertyValue('--accent-primary').trim(),
            success: computedStyle.getPropertyValue('--accent-success').trim(),
            warning: computedStyle.getPropertyValue('--accent-warning').trim(),
            danger: computedStyle.getPropertyValue('--accent-danger').trim(),
            info: computedStyle.getPropertyValue('--accent-info').trim(),
            background: computedStyle.getPropertyValue('--bg-primary').trim(),
            text: computedStyle.getPropertyValue('--text-primary').trim()
        };
    }
}

// Initialiser le gestionnaire de thème
let themeManager;
document.addEventListener('DOMContentLoaded', () => {
    themeManager = new ThemeManager();
});

// Fonction globale pour basculer le sélecteur de thème
function toggleThemeSelector() {
    if (themeManager) {
        const selector = document.getElementById('themeSelector');
        if (selector && selector.classList.contains('theme-selector--visible')) {
            themeManager.hideThemeSelector();
        } else {
            themeManager.showThemeSelector();
        }
    }
}