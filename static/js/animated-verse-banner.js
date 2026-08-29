/**
 * Bande de verset biblique — version accessible
 * ---------------------------------------------
 * - Texte affiché intégralement dès le chargement (lisible par les lecteurs d'écran)
 * - Rotation douce en fondu toutes les 30 secondes (pas de défilement type "marquee")
 * - Désactivée si l'utilisateur préfère un mouvement réduit (prefers-reduced-motion)
 * - Pas d'aria-live : le changement automatique ne doit pas interrompre la lecture
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

        this.rotationIntervalMs = 30000; // 30 s entre chaque verset
        this.fadeDurationMs = 400;
        this.timer = null;
        this.bannerElement = null;
        this.reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        this.init();
    }

    init() {
        this.bannerElement = document.querySelector('.animated-verse-banner');
        if (!this.bannerElement) return;

        // Conteneur texte : simple paragraphe, pas de zone défilante
        this.bannerElement.innerHTML = '<p class="verse-banner-text"></p>';
        this.textEl = this.bannerElement.querySelector('.verse-banner-text');

        this.showVerse(this.randomVerse(), false);

        // Rotation automatique seulement si le mouvement est accepté
        if (!this.reducedMotion) {
            this.startRotation();
            // Pause quand l'onglet est masqué (économie + stabilité)
            document.addEventListener('visibilitychange', () => {
                if (document.hidden) {
                    this.stopRotation();
                } else {
                    this.startRotation();
                }
            });
        }
    }

    randomVerse() {
        return this.verses[Math.floor(Math.random() * this.verses.length)];
    }

    formatVerse(verse) {
        return `\u00AB\u00A0${verse.text}\u00A0\u00BB — ${verse.reference}`;
    }

    showVerse(verse, withFade = true) {
        if (!this.textEl) return;
        if (!withFade || this.reducedMotion) {
            this.textEl.textContent = this.formatVerse(verse);
            return;
        }
        // Fondu sortant puis entrant
        this.textEl.classList.add('verse-banner-text--hidden');
        window.setTimeout(() => {
            this.textEl.textContent = this.formatVerse(verse);
            this.textEl.classList.remove('verse-banner-text--hidden');
        }, this.fadeDurationMs);
    }

    startRotation() {
        this.stopRotation();
        this.timer = window.setInterval(() => this.showVerse(this.randomVerse()), this.rotationIntervalMs);
    }

    stopRotation() {
        if (this.timer) {
            window.clearInterval(this.timer);
            this.timer = null;
        }
    }

    // Compatibilité ascendante : changeVerse() était exposée pour les tests
    changeVerse() {
        this.showVerse(this.randomVerse());
    }

    startPeriodicChange() {
        // Ancienne API (minutes) — déléguée à la rotation standard
        this.startRotation();
    }
}

// Initialisation
document.addEventListener('DOMContentLoaded', function () {
    if (document.querySelector('.animated-verse-banner')) {
        window.verseBanner = new AnimatedVerseBanner();
    }
});

// Fonction utilitaire conservée pour les tests existants
function changeVerse() {
    if (window.verseBanner) {
        window.verseBanner.changeVerse();
    }
}
