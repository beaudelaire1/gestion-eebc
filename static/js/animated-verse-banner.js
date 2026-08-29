/**
 * Bande de verset animée avec texte défilant
 * Sélection aléatoire de versets bibliques
 */

class AnimatedVerseBanner {
    constructor() {
        this.verses = [
            {
                text: "Car Dieu a tant aimé le monde qu'il a donné son Fils unique, afin que quiconque croit en lui ne périsse point, mais qu'il ait la vie éternelle.",
                reference: "Jean 3:16"
            },
            {
                text: "Je puis tout par celui qui me fortifie.",
                reference: "Philippiens 4:13"
            },
            {
                text: "L'Éternel est mon berger: je ne manquerai de rien.",
                reference: "Psaume 23:1"
            },
            {
                text: "Confie-toi en l'Éternel de tout ton cœur, et ne t'appuie pas sur ta sagesse.",
                reference: "Proverbes 3:5"
            },
            {
                text: "Car mes pensées ne sont pas vos pensées, et vos voies ne sont pas mes voies, dit l'Éternel.",
                reference: "Ésaïe 55:8"
            },
            {
                text: "Venez à moi, vous tous qui êtes fatigués et chargés, et je vous donnerai du repos.",
                reference: "Matthieu 11:28"
            },
            {
                text: "Cherchez premièrement le royaume et la justice de Dieu; et toutes ces choses vous seront données par-dessus.",
                reference: "Matthieu 6:33"
            },
            {
                text: "Car là où deux ou trois sont assemblés en mon nom, je suis au milieu d'eux.",
                reference: "Matthieu 18:20"
            },
            {
                text: "L'amour de Dieu a été versé dans nos cœurs par le Saint-Esprit qui nous a été donné.",
                reference: "Romains 5:5"
            },
            {
                text: "Celui qui demeure sous l'abri du Très-Haut repose à l'ombre du Tout-Puissant.",
                reference: "Psaume 91:1"
            },
            {
                text: "Réjouissez-vous toujours dans le Seigneur; je le répète, réjouissez-vous.",
                reference: "Philippiens 4:4"
            },
            {
                text: "Car c'est par la grâce que vous êtes sauvés, par le moyen de la foi.",
                reference: "Éphésiens 2:8"
            },
            {
                text: "Que votre cœur ne se trouble point. Croyez en Dieu, et croyez en moi.",
                reference: "Jean 14:1"
            },
            {
                text: "Il n'y a donc maintenant aucune condamnation pour ceux qui sont en Jésus-Christ.",
                reference: "Romains 8:1"
            },
            {
                text: "Voici, je me tiens à la porte, et je frappe. Si quelqu'un entend ma voix et ouvre la porte, j'entrerai chez lui.",
                reference: "Apocalypse 3:20"
            }
        ];
        
        this.currentVerse = null;
        this.bannerElement = null;
        this.init();
    }

    init() {
        this.selectRandomVerse();
        this.createBanner();
        this.startAnimation();
    }

    selectRandomVerse() {
        const randomIndex = Math.floor(Math.random() * this.verses.length);
        this.currentVerse = this.verses[randomIndex];
    }

    createBanner() {
        // Chercher la bannière existante dans le HTML
        this.bannerElement = document.querySelector('.animated-verse-banner');
        
        if (!this.bannerElement) {
            // Si aucune bannière n'existe, en créer une (fallback)
            this.bannerElement = document.createElement('div');
            this.bannerElement.className = 'animated-verse-banner';
            
            // Insérer au début du premier formulaire trouvé
            const form = document.querySelector('form[method="post"]');
            if (form) {
                form.parentNode.insertBefore(this.bannerElement, form);
            }
        }
        
        // Mettre à jour le contenu de la bannière existante avec le texte défilant
        this.updateBannerContent();
    }
    
    updateBannerContent() {
        if (!this.bannerElement) return;
        
        const fullText = `${this.currentVerse.text} — ${this.currentVerse.reference}`;
        
        this.bannerElement.innerHTML = `
            <div class="verse-scroll-container">
                <div class="verse-scroll-text">${fullText}</div>
            </div>
        `;
    }

    startAnimation() {
        const scrollText = this.bannerElement.querySelector('.verse-scroll-text');
        if (scrollText) {
            // Calculer la largeur du texte pour l'animation
            const textWidth = scrollText.scrollWidth;
            const containerWidth = this.bannerElement.offsetWidth;
            
            // Définir la durée de l'animation basée sur la longueur du texte
            const duration = Math.max(15, textWidth / 50); // Minimum 15s, ajusté selon la longueur
            
            scrollText.style.animationDuration = `${duration}s`;
            scrollText.classList.add('scrolling');
        }
    }

    // Changer de verset (peut être appelé périodiquement)
    changeVerse() {
        this.selectRandomVerse();
        this.updateBannerContent();
        
        // Redémarrer l'animation
        const scrollText = this.bannerElement.querySelector('.verse-scroll-text');
        if (scrollText) {
            scrollText.classList.remove('scrolling');
            setTimeout(() => {
                this.startAnimation();
            }, 100);
        }
    }

    // Méthode pour changer de verset périodiquement
    startPeriodicChange(intervalMinutes = 2) {
        setInterval(() => {
            this.changeVerse();
        }, intervalMinutes * 60 * 1000);
    }
}

// Initialiser la bannière quand le DOM est chargé
document.addEventListener('DOMContentLoaded', function() {
    // Vérifier s'il y a une bannière de verset sur la page
    if (document.querySelector('.animated-verse-banner')) {
        const verseBanner = new AnimatedVerseBanner();
        
        // Changer de verset toutes les 2 minutes
        verseBanner.startPeriodicChange(2);
        
        // Exposer globalement pour les tests
        window.verseBanner = verseBanner;
    }
});

// Fonction pour changer manuellement de verset (pour les tests)
function changeVerse() {
    if (window.verseBanner) {
        window.verseBanner.changeVerse();
    }
}