# EEBC Mobile App

Application mobile cross-platform pour l'Église Évangélique Baptiste de Cabassou (EEBC).

## Technologies

- **React Native** avec **Expo** (SDK 50)
- **TypeScript** (strict mode)
- **React Navigation** pour la navigation
- **Zustand** pour la gestion d'état
- **Axios** pour les requêtes HTTP
- **Expo SecureStore** pour le stockage sécurisé
- **Expo Notifications** pour les notifications push

## Structure du projet

```
eebc-mobile/
├── src/
│   ├── components/     # Composants UI réutilisables
│   ├── screens/        # Écrans de l'application
│   ├── services/       # Services (API, Auth, Storage, etc.)
│   ├── stores/         # Stores Zustand
│   ├── hooks/          # Hooks React personnalisés
│   ├── types/          # Définitions TypeScript
│   └── constants/      # Constantes de l'application
├── assets/             # Images, icônes, fonts
├── App.tsx             # Point d'entrée
└── app.json            # Configuration Expo
```

## Installation

```bash
# Installer les dépendances
npm install

# Démarrer le serveur de développement
npm start

# Lancer sur iOS
npm run ios

# Lancer sur Android
npm run android
```

## Scripts disponibles

- `npm start` - Démarre le serveur Expo
- `npm run android` - Lance sur Android
- `npm run ios` - Lance sur iOS
- `npm run web` - Lance sur navigateur web
- `npm run lint` - Vérifie le code avec ESLint
- `npm run lint:fix` - Corrige les erreurs ESLint
- `npm run format` - Formate le code avec Prettier
- `npm test` - Lance les tests

## Configuration

L'application se connecte à l'API Django backend. Configurez l'URL de l'API dans `src/constants/index.ts`.

## Licence

Propriétaire - EEBC
