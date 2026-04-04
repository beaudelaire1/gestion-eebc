# EEBC Mobile

Application mobile Flutter connectée à la plateforme EEBC (API Django REST).

## Fonctionnalités

### Écrans publics (sans authentification)
- **Nos Églises** (`/public/sites`) - Répertoire d'églises avec adresses, horaires, contacts  
- **Carte Interactive** (`/public/map`) - Localisation GPS des églises
- **Actualités** (`/public/news`) - Articles avec images et extraits
- **Contact** (`/public/contact`) - Formulaire avec protection rate limiting
- **Je suis intéressé(e)** (`/public/interest`) - Inscription visiteur

### Fonctionnalités transversales
- **Cache local** (10 minutes) - Données persistes in SharedPreferences
- **Mode hors ligne** - Affichage des données en cache avec indicateur
- **Gestion d'erreurs robuste** - Messages clairs et options de réessai

## Pré-requis

- Flutter stable
- Android Studio (SDK + émulateur) et/ou Xcode (iOS)
- Accès réseau à l’API EEBC

## Configuration environnement

Par défaut, l’application utilise l’API de production :

- `https://eglise-ebc.org/api/v1`

Pour cibler un autre environnement, utilisez `--dart-define` :

- `--dart-define=API_BASE_URL=https://staging.example.com/api/v1`
- `--dart-define=API_TIMEOUT_SECONDS=30`

## Firebase (notifications push)

Ajouter les fichiers fournis par Firebase :

- `android/app/google-services.json`
- `ios/Runner/GoogleService-Info.plist`

## Lancement local

Depuis le dossier `eebc_mobile` :

1. `flutter pub get`
2. `flutter analyze`
3. `flutter test`
4. `flutter run -d android`

## Build production

- Android APK : `flutter build apk --release`
- Android App Bundle : `flutter build appbundle --release`

## Notes architecture

- **State Management** : Provider pour les providers d'état (providers/)
- **Caching** : LocalCacheService avec SharedPreferences (10min TTL)
- **API** : Dio HTTP client avec interceptor pour JWT refresh automatique
- **Routing** : GoRouter pour navigation déclarative
- **Validation** : FormValidator côté client + validation serveur

## Notes de robustesse

- Auth JWT (access + refresh) avec stockage sécurisé.
- Refresh token sérialisé (un seul refresh à la fois).
- Gestion des erreurs API homogène et timeouts configurables.
- Rate limiting côté serveur sur formulaires publics (3 req/10 min par IP)
- Honeypot protection sur formulaires publics

## Documentation complète

- [Fonctionnalités publiques](docs/PUBLIC_FEATURES.md) - Architecture et usage détaillé
- [API Backend](../docs/API_DOCUMENTATION.md) - Documentation des endpoints
