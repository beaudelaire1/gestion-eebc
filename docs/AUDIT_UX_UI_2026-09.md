# Audit UX/UI — EEBC Gestion

Date : 2026-09-01  
Branche auditée : `develop`  
Périmètre : site public (`templates/public*`, `apps/core` site vitrine) et application interne `/app` (`templates/base.html`, dashboard, composants partagés).

## 1. Compréhension du besoin

L’objectif est d’améliorer l’expérience publique et l’application interne sans changer la stack (Django 5.2, Bootstrap 5, HTMX, Alpine.js) et sans introduire React. Les corrections doivent rester compatibles avec les rôles métier, les formulaires existants et les contraintes de production Coolify.

## 2. Normes et règles retenues

- **Accessibilité** : WCAG 2.2 niveau AA et référentiel RGAA 4.1.2 pour les points critiques : landmarks, lien d’évitement, focus visible, contrastes, navigation clavier, `prefers-reduced-motion`, messages d’erreur et zones tactiles.
- **Framework CSS** : Bootstrap 5.3, avec des tokens CSS centralisés (`--bg-*`, `--text-*`, `--accent-*`) et une limitation stricte des `!important`.
- **Architecture front** : conventions BEM déjà présentes, HTMX en amélioration progressive, templates Django comme source de vérité HTML.
- **Performance perçue** : éviter les animations globales coûteuses, préserver le LCP des pages publiques, limiter les scripts inline et mutualiser les correctifs dans `static/css/eebc-ux.css`.
- **Confidentialité** : consentement cookie sobre, sans traceur tiers, conforme à une approche CNIL “cookies strictement nécessaires”.
- **Cible minimale** : mobile 360 px, desktop 1440 px, navigation clavier complète sur les éléments interactifs critiques.

## 3. Constats priorisés

### Critique / fort impact

1. **L’application `/app` n’avait pas de lien d’évitement ni de cible principale focusable.**  
   `templates/base.html` rendait `<main class="main-content">` sans `id`, alors que la navigation latérale est longue. Impact : navigation clavier et lecteurs d’écran pénalisés.

2. **Deux systèmes de toasts coexistaient.**  
   `templates/base.html` incluait `components/toast_container.html` **et** `static/js/toasts.js`; le composant convertissait tous les `.alert`, y compris des erreurs de formulaire, ce qui pouvait masquer des retours de validation importants.

3. **Le sélecteur de thème utilisait des `div` cliquables.**  
   Les options de thème étaient accessibles à la souris mais pas nativement au clavier ni avec un état `aria-pressed`.

4. **Le carrousel public utilisait des puces `div` cliquables.**  
   Les points de navigation n’étaient pas des boutons et ne portaient ni nom accessible ni état courant.

### Majeur

5. **Styles inline massifs dans les templates.**  
   Analyse statique : 949 occurrences de `style=`, réparties ainsi : 489 dans les templates d'e-mails (le CSS inline y est **requis** par les clients de messagerie : ne pas convertir), ~36 dans les documents print/PDF (rendus autonomes WeasyPrint), 82 valeurs dynamiques (`{{ ... }}`) et ~330 statiques dans les pages web. Ce sont ces ~330 qui fragmentent la charte et compliquent les thèmes sombres.

6. **Règles CSS trop globales.**  
   `components.css` applique `*` pour la police et `themes.css` impose une transition sur tous les éléments. La couche d’application des thèmes utilise ensuite de nombreux `!important`, ce qui rend les contrastes difficiles à garantir sur les 23 thèmes.

7. **Hiérarchie de titres à risque sur l’accueil public.**  
   Quand le carrousel est actif, chaque slide rend un `h1`; une page peut donc exposer plusieurs titres principaux.

8. **Recherche globale absente sur mobile.**  
   La recherche du top bar est masquée en `d-none d-md-block`, sans point d’entrée équivalent sur petit écran.

### Moyen / amélioration continue

9. **État du sidebar mobile insuffisamment synchronisé.**  
   L’overlay restait `aria-hidden="true"` en permanence et le sidebar n’était pas masqué proprement lorsqu’il était fermé sur mobile.

10. **Liens externes nouveaux onglets pas tous sécurisés.**  
    Analyse statique : 44 `target="_blank"`, dont 28 sans `rel="noopener noreferrer"` détecté par le script local.

11. **Composants de données sans sémantique suffisante.**  
    Les barres de progression du dashboard et l’anneau de présence n’exposaient pas explicitement leur valeur aux technologies d’assistance.

## 4. Corrections appliquées

- Ajout d’une couche mutualisée `static/css/eebc-ux.css` : lien d’évitement, focus visible homogène, `prefers-reduced-motion`, zones tactiles 44 px, correctifs boutons de carrousel et sélecteur de thème.
- `templates/base.html` : skip-link, `main#main-content`, navigation latérale nommée, recherche globale labellisée, bouton thème en `aria-haspopup="dialog"`, suppression de l’ancien conteneur de toasts dupliqué, synchronisation `aria-hidden` du sidebar mobile.
- `static/js/theme-manager.js` + `static/css/theme-selector.css` : options de thème converties en boutons, `aria-pressed`, dialogue nommé, focus initial et restitution du focus, fermeture clavier/extérieur plus robuste.
- `templates/public/base.html` : skip-link centralisé en CSS, bandeau cookies en région nommée avec `aria-live`.
- `templates/public/home.html` : carrousel déclaré comme région `carrousel`, puces transformées en boutons avec `aria-label` et `aria-current`, slides masquées via `aria-hidden`.
- `templates/dashboard/home.html` : navigation de section nommée, `aria-current`, progression des campagnes en `role="progressbar"`, anneau de présence avec `<title>`, lien externe de don sécurisé.

### Sortie du CSS inline (gabarits partagés)

- `static/css/eebc-ux.css` : ajout d'une section d'utilitaires (`nav-link--sub`, `icon-sm/xs/xxs`, `text-donation`, `app-search`, `dropdown-item-btn`, `bg-gradient-*`, `bg-soft-*`, `stat-subbreakdown`, `event-color-dot`, bandeau `.cookie-banner` BEM, `#scrollTopBtn`).
- `templates/base.html` : **25 attributs `style` → 0**. Suppression de styles redondants avec `components.css` (marque sidebar), sous-liens de navigation et bouton de déconnexion classés, bandeau cookies unifié avec le site public (même markup BEM, `role="region"`, `aria-live`, consentement valable 6 mois façon CNIL, `type="button"` sur les boutons).
- `templates/public/base.html` : **10 attributs `style` → 0**. Bandeau cookies classé, bouton retour-en-haut déplacé en CSS.
- `templates/dashboard/home.html` : **20 attributs `style` → 6**, tous légitimes : 4 propriétés personnalisées `--card-accent` (pattern recommandé), la couleur d'événement migrée en `--event-color`, la largeur dynamique de la barre de progression. Suppression de 3 fonds d'icônes redondants (déjà couverts par `--card-accent` hérité).
- Règle durable documentée : statique récurrent → classe utilitaire ; valeur dynamique → propriété personnalisée inline ; e-mail → inline conservé.

## 5. Validations effectuées

- Téléchargement de la branche `develop` et analyse statique de 364 templates.
- Compteurs avant correction : 950 styles inline, 83 `onclick`, 60 images (aucune sans `alt` détectée), 35 boutons sans `type`, 156 tables, 44 liens `target="_blank"`.
- Vérification des points d’entrée : site public via `apps/core/urls.py`, application interne sous `/app` via `gestion_eebc/urls.py`.
- Contrôles locaux : `git diff --check`, vérification des marqueurs critiques et `node --check` sur le JavaScript modifié.
- Vérification de redondance avant suppression (ex. marque sidebar déjà forcée en blanc par `components.css`, fonds d'icônes déjà couverts par `--card-accent`) et parité de cascade vérifiée contre `themes.css` (aucun override `!important` sur les éléments convertis).

## 6. Risques restants et prochaines étapes

- **Refactor CSS nécessaire** : réduire progressivement les `!important` de la couche thème et étendre la sortie du CSS inline aux ~275 occurrences statiques restantes, hors gabarits partagés (pages métier), en suivant la règle ci-dessus. Les 489 occurrences des e-mails et les documents print/PDF ne sont **pas** à convertir.
- **Titres du carrousel** : décider si seule la première slide active porte le `h1`, ou passer les slides en `h2` avec un `h1` fixe masqué visuellement.
- **Recherche mobile** : ajouter un bouton recherche dans le top bar mobile ou une page `/app/search/` dédiée.
- **Tests à brancher** : ajouter un contrôle automatisé d’accessibilité (axe-core ou pa11y) sur `/`, `/contact/`, `/inscription/`, `/app/` et une page formulaire avec erreurs.
- **Mesure terrain** : valider les contrastes des 23 thèmes avec un rapport de contraste automatisé avant de promouvoir les thèmes sombres comme choix par défaut.
