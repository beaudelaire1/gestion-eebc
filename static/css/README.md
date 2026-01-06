# EEBC CSS Components Documentation

Ce document décrit toutes les classes CSS disponibles dans le système de design EEBC, organisées selon la convention BEM (Block Element Modifier).

## Table des matières

1. [Variables CSS](#variables-css)
2. [Layout Components](#layout-components)
3. [Card Components](#card-components)
4. [Avatar Components](#avatar-components)
5. [Button Components](#button-components)
6. [Table Components](#table-components)
7. [Form Components](#form-components)
8. [Badge Components](#badge-components)
9. [Progress Components](#progress-components)
10. [Alert Components](#alert-components)
11. [Image Components](#image-components)
12. [Event Components](#event-components)
13. [Stats Components](#stats-components)
14. [Calendar Components](#calendar-components)
15. [Email Components](#email-components)
16. [Utility Classes](#utility-classes)

## Variables CSS

Le système utilise des variables CSS pour maintenir la cohérence des couleurs et des espacements :

```css
:root {
    --eebc-primary: #0A36FF;
    --eebc-primary-dark: #0829CC;
    --eebc-primary-light: #3D5FFF;
    --eebc-white: #FFFFFF;
    --eebc-black: #0B0F19;
    --eebc-gray-50: #F8FAFC;
    --eebc-gray-100: #F1F5F9;
    --eebc-gray-200: #E2E8F0;
    --eebc-gray-300: #CBD5E1;
    --eebc-gray-400: #94A3B8;
    --eebc-gray-500: #64748B;
    --eebc-gray-600: #475569;
    --eebc-gray-700: #334155;
    --eebc-gray-800: #1E293B;
    --eebc-success: #10B981;
    --eebc-warning: #F59E0B;
    --eebc-danger: #EF4444;
    --eebc-info: #06B6D4;
}
```

## Layout Components

### Sidebar

**Block:** `.sidebar`
- Barre latérale de navigation principale
- Position fixe, largeur 280px

**Elements:**
- `.sidebar__brand` - En-tête de la sidebar avec logo
- `.sidebar__brand-title` - Titre principal (h4)
- `.sidebar__brand-subtitle` - Sous-titre (small)
- `.sidebar__content` - Contenu scrollable de la sidebar

**Modifiers:**
- `.sidebar--collapsed` - Sidebar rétractée (translateX(-280px))
- `.sidebar--show` - Sidebar visible sur mobile

**Exemple:**
```html
<nav class="sidebar" id="sidebar">
    <div class="sidebar__brand">
        <h4 class="sidebar__brand-title">EEBC</h4>
        <small class="sidebar__brand-subtitle">Système de Gestion</small>
    </div>
    <div class="sidebar__content">
        <!-- Navigation content -->
    </div>
</nav>
```

### Navigation

**Block:** `.nav-section`
- Section de navigation dans la sidebar

**Elements:**
- `.nav-section__title` - Titre de section (uppercase, petit)

**Block:** `.nav-link`
- Lien de navigation

**Elements:**
- `.nav-link__icon` - Icône du lien (width: 24px)

**Modifiers:**
- `.nav-link--active` - Lien actif (couleur primaire, bordure gauche)

**Exemple:**
```html
<div class="nav-section">
    <div class="nav-section__title">Principal</div>
    <nav class="nav flex-column">
        <a class="nav-link nav-link--active" href="#">
            <i class="bi bi-grid-1x2-fill nav-link__icon"></i>
            <span>Tableau de bord</span>
        </a>
    </nav>
</div>
```

### Main Content

**Block:** `.main-content`
- Zone de contenu principal
- Margin-left: 280px par défaut

**Modifiers:**
- `.main-content--expanded` - Contenu étendu (margin-left: 0)

### Top Bar

**Block:** `.top-bar`
- Barre supérieure avec navigation et utilisateur
- Position sticky

## Card Components

### Card

**Block:** `.card`
- Carte de base avec bordure arrondie et ombre

**Elements:**
- `.card__header` - En-tête de carte
- `.card__title` - Titre de carte
- `.card__body` - Corps de carte

**Exemple:**
```html
<div class="card">
    <div class="card__header">
        <h5 class="card__title">Titre de la carte</h5>
    </div>
    <div class="card__body">
        Contenu de la carte
    </div>
</div>
```

### Stat Card

**Block:** `.stat-card`
- Carte de statistique avec animation hover

**Elements:**
- `.stat-card__icon` - Icône de statistique (52x52px)
- `.stat-card__value` - Valeur numérique (grande taille, JetBrains Mono)
- `.stat-card__label` - Libellé de la statistique

**Modifiers pour l'icône:**
- `.stat-card__icon--blue` - Couleur bleue primaire
- `.stat-card__icon--green` - Couleur verte (succès)
- `.stat-card__icon--orange` - Couleur orange (warning)
- `.stat-card__icon--purple` - Couleur violette
- `.stat-card__icon--pink` - Couleur rose
- `.stat-card__icon--cyan` - Couleur cyan (info)

**Exemple:**
```html
<div class="stat-card">
    <div class="stat-card__icon stat-card__icon--blue">
        <i class="bi bi-people-fill"></i>
    </div>
    <div class="stat-card__value">150</div>
    <div class="stat-card__label">Membres actifs</div>
</div>
```

## Avatar Components

**Block:** `.avatar`
- Avatar circulaire avec initiales ou image

**Modifiers de taille:**
- `.avatar--sm` - Petit (34x34px)
- `.avatar--md` - Moyen (40x40px) - défaut
- `.avatar--lg` - Grand (50x50px)
- `.avatar--xl` - Très grand (60x60px)

**Modifiers de couleur:**
- `.avatar--primary` - Dégradé bleu primaire
- `.avatar--purple` - Dégradé violet

**Exemple:**
```html
<div class="avatar avatar--lg avatar--primary">
    JD
</div>
```

## Button Components

### Buttons

**Classes disponibles:**
- `.btn-primary` - Bouton primaire bleu avec animation
- `.btn-outline-secondary` - Bouton outline gris
- `.btn-outline-light` - Bouton outline clair
- `.user-btn` - Bouton utilisateur dans la top bar

**Exemple:**
```html
<button class="btn btn-primary">Action principale</button>
<button class="btn btn-outline-secondary">Action secondaire</button>
```

## Table Components

### Table

**Block:** `.table`
- Table de base avec styles Bootstrap étendus

**Elements:**
- `.table__header` - En-tête de colonne (th)
- `.table__cell` - Cellule de données (td)
- `.table__row` - Ligne de tableau (tr)

**Modifiers de largeur de colonne:**
- `.table__col--xs` - 50px
- `.table__col--sm` - 80px
- `.table__col--md` - 150px
- `.table__col--lg` - 200px

**Exemple:**
```html
<table class="table">
    <thead>
        <tr>
            <th class="table__header table__col--sm">ID</th>
            <th class="table__header">Nom</th>
        </tr>
    </thead>
    <tbody>
        <tr class="table__row">
            <td class="table__cell">1</td>
            <td class="table__cell">John Doe</td>
        </tr>
    </tbody>
</table>
```

## Form Components

### Input Group

**Elements:**
- `.input-group__text` - Texte d'input group avec border-radius personnalisé

**Exemple:**
```html
<div class="input-group">
    <span class="input-group-text input-group__text">
        <i class="bi bi-search"></i>
    </span>
    <input type="text" class="form-control">
</div>
```

## Badge Components

### Badge

**Block:** `.badge`
- Badge de base avec styles étendus

**Modifiers:**
- `.badge--success` - Badge vert
- `.badge--warning` - Badge orange
- `.badge--danger` - Badge rouge
- `.badge--primary` - Badge bleu
- `.badge--info` - Badge cyan

### Status Badge

**Block:** `.status-badge`
- Badge de statut spécialisé

**Modifiers:**
- `.status-badge--pending` - En attente (jaune)
- `.status-badge--confirmed` - Confirmé (vert)
- `.status-badge--completed` - Terminé (cyan)
- `.status-badge--cancelled` - Annulé (rouge)

**Exemple:**
```html
<span class="status-badge status-badge--confirmed">Confirmé</span>
```

## Image Components

### Image Card

**Classes de taille:**
- `.image-card` - Hauteur 200px par défaut
- `.image-card--sm` - Hauteur 180px
- `.image-card--lg` - Hauteur 350px
- `.image-card--xl` - Hauteur 400px

### Image Placeholder

**Block:** `.image-placeholder`
- Placeholder pour images manquantes

**Elements:**
- `.image-placeholder__icon` - Icône du placeholder
- `.image-placeholder__icon--lg` - Grande icône (4rem)

**Modifiers:**
- `.image-placeholder--primary` - Fond bleu primaire
- `.image-placeholder--secondary` - Fond gris

**Exemple:**
```html
<div class="image-placeholder image-placeholder--primary image-card--sm">
    <i class="bi bi-image image-placeholder__icon"></i>
</div>
```

## Event Components

### Event Date Badge

**Block:** `.event-date-badge`
- Badge de date pour événements

**Elements:**
- `.event-date-badge__day` - Jour (grand, gras)
- `.event-date-badge__month` - Mois (petit, uppercase)

**Exemple:**
```html
<div class="event-date-badge">
    <div class="event-date-badge__day">15</div>
    <div class="event-date-badge__month">Jan</div>
</div>
```

## Stats Components

### Stats Bar

**Block:** `.stats-bar`
- Barre de statistiques horizontale

### Mini Stat

**Block:** `.mini-stat`
- Statistique compacte avec icône

**Elements:**
- `.mini-stat__icon` - Icône de la statistique (48x48px)
- `.mini-stat__content` - Contenu textuel
- `.mini-stat__value` - Valeur numérique
- `.mini-stat__label` - Libellé de la statistique

**Modifiers pour l'icône:**
- `.mini-stat__icon--primary` - Dégradé bleu
- `.mini-stat__icon--success` - Dégradé vert
- `.mini-stat__icon--purple` - Dégradé violet
- `.mini-stat__icon--blue` - Dégradé bleu clair
- `.mini-stat__icon--pink` - Dégradé rose

**Exemple:**
```html
<div class="stats-bar">
    <div class="mini-stat">
        <div class="mini-stat__icon mini-stat__icon--primary">
            <i class="bi bi-people-fill"></i>
        </div>
        <div class="mini-stat__content">
            <div class="mini-stat__value">150</div>
            <div class="mini-stat__label">Total membres</div>
        </div>
    </div>
</div>
```

## Calendar Components

### Legend

**Block:** `.legend`
- Légende pour calendriers

**Elements:**
- `.legend-item` - Élément de légende
- `.legend-color` - Carré de couleur (16x16px)

**Modifiers pour les couleurs:**
- `.legend-color--pending` - Jaune (#ffc107)
- `.legend-color--confirmed` - Vert (#198754)
- `.legend-color--completed` - Cyan (#0dcaf0)
- `.legend-color--cancelled` - Rouge (#dc3545)

**Exemple:**
```html
<div class="legend">
    <div class="legend-item">
        <div class="legend-color legend-color--pending"></div>
        <span>En attente</span>
    </div>
</div>
```

## Email Components

### Email Container

**Block:** `.email-container`
- Conteneur principal pour emails (max-width: 600px)

### Email Header

**Block:** `.email-header`
- En-tête d'email avec bordure inférieure

### Email Content

**Block:** `.email-content`
- Zone de contenu avec fond gris clair

**Elements:**
- `.email-content__title` - Titre de section

### Email Table

**Block:** `.email-table`
- Tableau pour emails (width: 100%, border-collapse)

**Elements:**
- `.email-table__cell` - Cellule de tableau (padding: 8px 0)
- `.email-table__cell--label` - Cellule de libellé (font-weight: bold)

### Email Highlight

**Block:** `.email-highlight`
- Zone mise en évidence (fond vert clair)

**Elements:**
- `.email-highlight__title` - Titre de la zone (couleur verte)

### Email Footer

**Block:** `.email-footer`
- Pied de page d'email avec bordure supérieure

**Elements:**
- `.email-footer__text` - Texte du pied de page (petit, gris)

**Exemple:**
```html
<div class="email-container">
    <h2 class="email-header">Titre de l'email</h2>
    
    <div class="email-content">
        <h3 class="email-content__title">Section importante</h3>
        <table class="email-table">
            <tr>
                <td class="email-table__cell email-table__cell--label">Libellé:</td>
                <td class="email-table__cell">Valeur</td>
            </tr>
        </table>
    </div>
    
    <div class="email-footer">
        <p class="email-footer__text">Texte du pied de page</p>
    </div>
</div>
```

## Utility Classes

### Text

- `.text-gradient` - Texte avec dégradé bleu

### Border Radius

- `.border-radius-lg` - Border-radius 16px
- `.border-radius-xl` - Border-radius 20px

### Shadows

- `.shadow-soft` - Ombre douce (0 4px 20px rgba(11, 15, 25, 0.04))
- `.shadow-hover` - Transition d'ombre au hover
- `.shadow-hover:hover` - Ombre au hover (0 20px 40px rgba(10, 54, 255, 0.12))

### View Toggle

- `.table-view` - Vue tableau (display: none par défaut)
- `.table-view--active` - Vue tableau active (display: block)

## Responsive Design

Le système inclut des breakpoints responsive :

- **Mobile (max-width: 767.98px):**
  - Padding réduit pour top-bar, card-body, stat-card
  
- **Tablet (max-width: 991.98px):**
  - Sidebar cachée par défaut
  - `.sidebar--show` pour afficher la sidebar
  - Main content sans margin-left
  - Stats-bar en colonne

## Animations

### Keyframes disponibles

- `@keyframes fadeIn` - Animation d'apparition (opacity + translateY)

### Classes d'animation

- `.fade-in` - Applique l'animation fadeIn
- `.htmx-request` - État de chargement HTMX (opacity: 0.5, pointer-events: none)

## Conventions de nommage BEM

Le système suit strictement la convention BEM :

- **Block:** `.block-name` (kebab-case)
- **Element:** `.block-name__element-name` (kebab-case)
- **Modifier:** `.block-name--modifier-name` (kebab-case)

### Exemples de nommage correct

```css
/* Block */
.sidebar { }

/* Element */
.sidebar__brand { }
.sidebar__brand-title { }

/* Modifier */
.sidebar--collapsed { }
.nav-link--active { }

/* Element avec modifier */
.stat-card__icon--blue { }
```

## Maintenance

Pour maintenir la cohérence du système :

1. **Toujours utiliser les variables CSS** pour les couleurs et espacements
2. **Respecter la convention BEM** pour tous les nouveaux composants
3. **Éviter les styles inline** dans les templates
4. **Documenter les nouveaux composants** dans ce fichier
5. **Tester la responsivité** sur tous les breakpoints

## Support des navigateurs

Le système supporte :
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

Les variables CSS et les propriétés modernes sont utilisées, donc IE11 n'est pas supporté.