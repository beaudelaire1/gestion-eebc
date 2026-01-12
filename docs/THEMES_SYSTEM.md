# Système de Thèmes EEBC

## Vue d'ensemble

Le système de gestion EEBC dispose maintenant d'un système de thèmes avancé avec 7 modes différents pour personnaliser l'apparence de l'interface utilisateur.

## Thèmes Disponibles

### 1. **Light** (Clair)
- **Description** : Thème clair classique
- **Icône** : `bi-sun`
- **Couleurs** : Blanc, bleu (#0A36FF), tons de gris clairs
- **Usage** : Idéal pour un usage en journée et un environnement bien éclairé

### 2. **Darky** (Sombre)
- **Description** : Thème sombre élégant
- **Icône** : `bi-moon`
- **Couleurs** : Tons sombres, bleu (#3b82f6), contrastes élevés
- **Usage** : Parfait pour réduire la fatigue oculaire en environnement peu éclairé

### 3. **Flatty** (Plat)
- **Description** : Design plat et minimaliste
- **Icône** : `bi-square`
- **Couleurs** : Couleurs plates, pas d'ombres, bordures nettes
- **Usage** : Interface épurée et moderne, focus sur le contenu

### 4. **Neony** (Néon)
- **Description** : Thème néon futuriste
- **Icône** : `bi-lightning`
- **Couleurs** : Fond noir, accents néon verts (#00ff88), effets lumineux
- **Usage** : Style cyberpunk pour une expérience visuelle unique

### 5. **Oceany** (Océan)
- **Description** : Thème océan apaisant
- **Icône** : `bi-water`
- **Couleurs** : Bleus océan (#0077be), tons aquatiques
- **Usage** : Ambiance calme et professionnelle

### 6. **Sunsety** (Coucher de soleil)
- **Description** : Thème coucher de soleil
- **Icône** : `bi-sunset`
- **Couleurs** : Oranges chauds (#ff6b35), tons dorés
- **Usage** : Atmosphère chaleureuse et accueillante

### 7. **Foresty** (Forêt)
- **Description** : Thème forêt naturel
- **Icône** : `bi-tree`
- **Couleurs** : Verts naturels (#228b22), tons terreux
- **Usage** : Ambiance naturelle et apaisante

## Utilisation

### Changer de Thème

1. **Via l'interface** : Cliquez sur l'icône de thème dans la barre supérieure
2. **Raccourci clavier** : `Ctrl + Shift + T`
3. **Sélection** : Choisissez parmi les 7 thèmes disponibles avec aperçu

### Persistance

- Le thème sélectionné est automatiquement sauvegardé dans le localStorage
- Le thème est restauré à chaque visite
- Détection automatique de la préférence système (clair/sombre) si aucun thème n'est défini

## Architecture Technique

### Fichiers CSS

- `static/css/themes.css` : Définitions des variables CSS pour tous les thèmes
- `static/css/theme-selector.css` : Styles du sélecteur de thème
- `static/css/components.css` : Composants utilisant les variables de thème

### JavaScript

- `static/js/theme-manager.js` : Gestionnaire principal des thèmes
- Classe `ThemeManager` pour la gestion complète du système

### Variables CSS

Chaque thème définit un ensemble de variables CSS :

```css
:root, [data-theme="light"] {
    --bg-primary: #ffffff;
    --bg-secondary: #f8fafc;
    --text-primary: #0B0F19;
    --accent-primary: #0A36FF;
    /* ... autres variables */
}
```

### Intégration avec Chart.js

Le système met automatiquement à jour les couleurs des graphiques Chart.js lors du changement de thème.

## Personnalisation

### Ajouter un Nouveau Thème

1. **Définir les variables CSS** dans `themes.css` :
```css
[data-theme="montheme"] {
    --bg-primary: #couleur;
    /* ... autres variables */
}
```

2. **Ajouter le thème** dans `theme-manager.js` :
```javascript
{ id: 'montheme', name: 'Mon Thème', icon: 'bi-icon', description: 'Description' }
```

3. **Ajouter les styles de prévisualisation** dans `theme-selector.css`

### Variables Disponibles

- **Arrière-plans** : `--bg-primary`, `--bg-secondary`, `--bg-card`, `--bg-hover`
- **Textes** : `--text-primary`, `--text-secondary`, `--text-muted`, `--text-inverse`
- **Bordures** : `--border-color`, `--border-light`, `--border-strong`
- **Accents** : `--accent-primary`, `--accent-success`, `--accent-warning`, `--accent-danger`, `--accent-info`
- **Ombres** : `--shadow-sm`, `--shadow-md`, `--shadow-lg`, `--shadow-xl`

## Accessibilité

- Transitions respectueuses de `prefers-reduced-motion`
- Contrastes de couleurs optimisés pour chaque thème
- Navigation au clavier supportée
- Focus visible sur tous les éléments interactifs

## Compatibilité

- Navigateurs modernes supportant les variables CSS
- Fallback automatique vers le thème clair si les variables CSS ne sont pas supportées
- Compatible avec tous les composants existants du système EEBC

## Raccourcis Clavier

- `Ctrl + Shift + T` : Ouvrir/fermer le sélecteur de thème
- `Échap` : Fermer le sélecteur de thème (si ouvert)

## Notifications

Le système affiche des notifications lors :
- Du changement de thème
- De la première visite (notification de bienvenue)
- D'erreurs de chargement de thème

## Performance

- Chargement asynchrone des thèmes
- Transitions CSS optimisées
- Mise en cache des préférences utilisateur
- Pas de rechargement de page nécessaire