# Implementation Plan: EEBC Mobile App

## Overview

Plan d'implémentation pour l'application mobile EEBC en React Native avec Expo. Le développement est divisé en phases : setup, API Django, services mobiles, écrans, et tests.

## Phase 1: Setup et Configuration

- [x] 1. Initialiser le projet React Native avec Expo
  - [x] 1.1 Créer le projet avec `npx create-expo-app eebc-mobile --template blank-typescript`
    - Configurer TypeScript strict mode
    - _Requirements: Setup_
  - [x] 1.2 Installer les dépendances principales
    - React Navigation, Zustand, Axios, Expo SecureStore, Expo Notifications
    - _Requirements: Setup_
  - [x] 1.3 Configurer la structure de dossiers
    - src/screens, src/components, src/services, src/stores, src/hooks, src/types
    - _Requirements: Setup_
  - [x] 1.4 Configurer ESLint et Prettier
    - _Requirements: Setup_

## Phase 2: API Django (Backend)

- [x] 2. Créer l'API REST Django
  - [x] 2.1 Installer Django REST Framework et SimpleJWT
    - Ajouter à requirements.txt et INSTALLED_APPS
    - _Requirements: 1.2_
  - [x] 2.2 Configurer l'authentification JWT
    - Settings JWT, URLs pour login/refresh/logout
    - _Requirements: 1.2, 1.4_
  - [x] 2.3 Créer les serializers pour les modèles existants
    - MemberSerializer, EventSerializer, WorshipServiceSerializer, AnnouncementSerializer
    - _Requirements: 3.1, 4.1, 5.1, 6.1_
  - [x] 2.4 Créer les ViewSets et URLs API
    - /api/v1/members/, /api/v1/events/, /api/v1/worship/, /api/v1/announcements/
    - _Requirements: 3.1, 4.1, 5.1, 6.1_
  - [x] 2.5 Implémenter les endpoints d'authentification
    - Login, refresh, logout, change password
    - _Requirements: 1.1, 1.2, 1.4, 1.5_
  - [x] 2.6 Implémenter l'endpoint de profil utilisateur
    - GET/PUT /api/v1/profile/
    - _Requirements: 10.1, 10.2, 10.7_
  - [x] 2.7 Implémenter les endpoints de donation
    - GET/POST /api/v1/donations/, intégration Stripe
    - _Requirements: 7.1, 7.2, 7.3_
  - [x] 2.8 Implémenter l'endpoint d'enregistrement device token
    - POST /api/v1/notifications/register/
    - _Requirements: 8.2_

- [x] 3. Checkpoint - Tester l'API Django
  - Tester tous les endpoints avec Postman/curl
  - Vérifier l'authentification JWT fonctionne

## Phase 3: Services Mobile

- [x] 4. Implémenter les services de base
  - [x] 4.1 Créer ApiService avec Axios
    - Configuration baseURL, timeout, interceptors
    - Gestion automatique du token dans les headers
    - _Requirements: 1.3_
  - [x] 4.2 Écrire les tests pour ApiService
    - Tester interceptors et gestion d'erreurs
    - _Requirements: 1.3_
  - [x] 4.3 Créer StorageService
    - Wrapper pour SecureStore (tokens) et AsyncStorage (cache)
    - _Requirements: 1.3, 9.1_
  - [x] 4.4 Écrire property test pour StorageService
    - **Property 1: JWT Token Lifecycle**
    - **Validates: Requirements 1.3, 1.6**
  - [x] 4.5 Créer AuthService
    - Login, logout, refresh, changePassword, biometric
    - _Requirements: 1.1, 1.2, 1.4, 1.5, 1.6, 1.7_
  - [x] 4.6 Écrire property test pour AuthService
    - **Property 2: Token Auto-Refresh**
    - **Property 3: Password Change Redirect**
    - **Validates: Requirements 1.4, 1.5**

- [x] 5. Implémenter les services avancés
  - [x] 5.1 Créer NotificationService
    - Permission, register device, handlers
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_
  - [x] 5.2 Créer SyncService
    - Queue management, sync operations, connectivity
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_
  - [x] 5.3 Écrire property test pour SyncService
    - **Property 11: Offline Data Availability**
    - **Property 12: Offline Action Queuing**
    - **Validates: Requirements 9.1, 9.2, 9.3, 9.4**

## Phase 4: State Management

- [x] 6. Créer les stores Zustand
  - [x] 6.1 Créer authStore
    - user, tokens, isAuthenticated, login/logout actions
    - _Requirements: 1.1, 1.6_
  - [x] 6.2 Créer membersStore
    - list, searchQuery, filteredMembers, cache
    - _Requirements: 3.1, 3.2_
  - [x] 6.3 Écrire property test pour member filtering
    - **Property 7: Member Search Filtering**
    - **Validates: Requirements 3.2**
  - [x] 6.4 Créer eventsStore
    - events, selectedDate, registrations
    - _Requirements: 4.1, 4.2, 4.4, 4.5_
  - [x] 6.5 Écrire property test pour event filtering
    - **Property 6: Event Date Filtering**
    - **Validates: Requirements 4.2**
  - [x] 6.6 Créer worshipStore
    - services, assignments, confirmations
    - _Requirements: 5.1, 5.2, 5.4_
  - [x] 6.7 Créer announcementsStore
    - list, unreadCount, readStatus
    - _Requirements: 6.1, 6.2, 6.4, 6.5_
  - [x] 6.8 Écrire property test pour announcement sorting
    - **Property 9: Announcement Sorting**
    - **Property 10: Read Status Tracking**
    - **Validates: Requirements 6.2, 6.4, 6.5**

- [x] 7. Checkpoint - Tester les stores
  - Vérifier que tous les stores fonctionnent correctement
  - Tester la persistance et le cache

## Phase 5: Navigation et Écrans

- [x] 8. Configurer la navigation
  - [x] 8.1 Créer RootNavigator avec Auth/Main stacks
    - Gestion de l'état d'authentification
    - _Requirements: 1.1_
  - [x] 8.2 Créer AuthStack (Login, ChangePassword)
    - _Requirements: 1.1, 1.5_
  - [x] 8.3 Créer MainTabNavigator
    - Dashboard, Members, Events, Worship, More
    - _Requirements: 2.1_
  - [x] 8.4 Créer MoreStack
    - Announcements, Giving, Profile, Settings
    - _Requirements: 6.1, 7.1, 10.1_

- [x] 9. Implémenter les écrans d'authentification
  - [x] 9.1 Créer LoginScreen
    - Formulaire login, validation, biometric option
    - _Requirements: 1.1, 1.7, 1.8_
  - [x] 9.2 Écrire property test pour login lockout
    - **Property 4: Account Lockout**
    - **Validates: Requirements 1.8**
  - [x] 9.3 Créer ChangePasswordScreen
    - Formulaire changement mot de passe
    - _Requirements: 1.5, 10.3_

- [-] 10. Implémenter le Dashboard
  - [x] 10.1 Créer DashboardScreen
    - Widgets selon rôle, événements, annonces, assignments
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_
  - [ ] 10.2 Écrire property test pour role-based widgets
    - **Property 5: Role-Based Dashboard**
    - **Validates: Requirements 2.1, 2.6**

- [x] 11. Implémenter le module Membres
  - [x] 11.1 Créer MembersListScreen
    - Liste avec recherche, pull-to-refresh
    - _Requirements: 3.1, 3.2, 3.8_
  - [x] 11.2 Créer MemberDetailScreen
    - Profil complet, actions contact
    - _Requirements: 3.3, 3.4, 3.5, 3.6, 3.7_
  - [x] 11.3 Écrire property test pour authorization
    - **Property 8: Authorization Enforcement**
    - **Validates: Requirements 3.7**

- [x] 12. Implémenter le module Événements
  - [x] 12.1 Créer EventsScreen avec calendrier
    - Vue calendrier, sélection date
    - _Requirements: 4.1, 4.2_
  - [x] 12.2 Créer EventDetailScreen
    - Détails, inscription, badge registered
    - _Requirements: 4.3, 4.4, 4.5, 4.8_
  - [x] 12.3 Implémenter les rappels d'événements
    - Notifications locales 24h avant
    - _Requirements: 4.6_

- [x] 13. Implémenter le module Culte
  - [x] 13.1 Créer WorshipScreen
    - Liste services, mes assignments
    - _Requirements: 5.1, 5.2, 5.7_
  - [x] 13.2 Créer ServiceDetailScreen
    - Roster complet, songs, confirmation
    - _Requirements: 5.3, 5.4, 5.5_

- [ ] 14. Implémenter le module Annonces
  - [ ] 14.1 Créer AnnouncementsScreen
    - Liste triée, pinned en haut
    - _Requirements: 6.1, 6.2, 6.5_
  - [ ] 14.2 Créer AnnouncementDetailScreen
    - Contenu complet, mark as read, share
    - _Requirements: 6.3, 6.4, 6.6_

- [ ] 15. Implémenter le module Dons
  - [ ] 15.1 Créer GivingScreen
    - Options de don, historique
    - _Requirements: 7.1, 7.4_
  - [ ] 15.2 Créer DonationFormScreen
    - Formulaire avec Stripe
    - _Requirements: 7.2, 7.3, 7.6, 7.7_
  - [ ] 15.3 Écrire property test pour donation persistence
    - **Property 13: Donation Persistence**
    - **Validates: Requirements 7.3, 7.4**
  - [ ] 15.4 Implémenter téléchargement reçus fiscaux
    - _Requirements: 7.5_

- [ ] 16. Implémenter le module Profil
  - [ ] 16.1 Créer ProfileScreen
    - Affichage et édition profil
    - _Requirements: 10.1, 10.2_
  - [ ] 16.2 Écrire property test pour profile update
    - **Property 14: Profile Update Persistence**
    - **Validates: Requirements 10.2, 10.7**
  - [ ] 16.3 Créer SettingsScreen
    - Notifications, dark mode, version
    - _Requirements: 10.4, 10.5, 10.6_

- [ ] 17. Checkpoint - Test des écrans
  - Vérifier la navigation complète
  - Tester le mode offline

## Phase 6: Notifications Push

- [-] 18. Configurer Firebase Cloud Messaging
  - [x] 18.1 Créer projet Firebase et configurer
    - google-services.json, GoogleService-Info.plist
    - _Requirements: 8.1_
  - [x] 18.2 Implémenter l'enregistrement du device token
    - _Requirements: 8.2_
  - [-] 18.3 Implémenter les handlers de notification
    - Foreground, background, tap
    - _Requirements: 8.3, 8.5_
  - [ ] 18.4 Écrire property test pour deep linking
    - **Property 15: Notification Deep Linking**
    - **Validates: Requirements 8.5**
  - [ ] 18.5 Implémenter les préférences de notification
    - _Requirements: 8.4_
  - [ ] 18.6 Implémenter le badge count
    - _Requirements: 8.6_

## Phase 7: Finalisation

- [ ] 19. UI/UX Polish
  - [ ] 19.1 Implémenter le dark mode
    - _Requirements: 10.5_
  - [ ] 19.2 Ajouter les animations et transitions
    - _Requirements: UX_
  - [ ] 19.3 Optimiser les performances
    - Lazy loading, image caching
    - _Requirements: Performance_
  - [ ] 19.4 Ajouter l'accessibilité
    - Labels, contraste, taille texte
    - _Requirements: Accessibility_

- [ ] 20. Tests E2E
  - [ ] 20.1 Configurer Detox
    - _Requirements: Testing_
  - [ ] 20.2 Écrire tests E2E pour les flux principaux
    - Login, navigation, actions principales
    - _Requirements: Testing_

- [ ] 21. Préparation déploiement
  - [ ] 21.1 Configurer les builds de production
    - iOS et Android
    - _Requirements: Deployment_
  - [ ] 21.2 Créer les assets (icône, splash screen)
    - _Requirements: Deployment_
  - [ ] 21.3 Préparer les fiches App Store et Play Store
    - _Requirements: Deployment_
  - [ ] 21.4 Soumettre pour review
    - _Requirements: Deployment_

- [ ] 22. Checkpoint final
  - Vérifier que tous les tests passent
  - Valider le déploiement sur les stores

## Notes

- Toutes les tâches sont obligatoires, y compris les tests property-based
- Chaque phase doit être validée avant de passer à la suivante
- L'API Django (Phase 2) doit être complète avant de commencer les écrans
- Les property tests utilisent fast-check pour React Native
