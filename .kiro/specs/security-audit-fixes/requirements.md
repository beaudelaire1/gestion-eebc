# Requirements Document

## Introduction

Ce document spécifie les corrections de sécurité, les améliorations de permissions, le refactoring architectural et les fonctionnalités manquantes identifiées lors de l'audit du projet Gestion EEBC. L'objectif est de transformer ce projet en une application de niveau entreprise, sécurisée, maintenable et complète.

## Glossaire

- **RBAC**: Role-Based Access Control - Contrôle d'accès basé sur les rôles
- **Décorateur**: Fonction Python qui modifie le comportement d'une autre fonction
- **Middleware**: Composant qui intercepte les requêtes/réponses Django
- **CRUD**: Create, Read, Update, Delete - Opérations de base sur les données
- **Rate_Limiting**: Limitation du nombre de requêtes par période de temps
- **Service_Layer**: Couche de services séparant la logique métier des vues
- **Audit_Log**: Journal d'audit traçant les actions utilisateurs
- **OCR**: Optical Character Recognition - Reconnaissance optique de caractères
- **HTMX**: Bibliothèque JavaScript pour interactions AJAX déclaratives
- **Skeleton_Loader**: Animation de chargement simulant la structure du contenu
- **Toast**: Notification flottante temporaire

---

## SECTION A: CORRECTIONS DE SÉCURITÉ CRITIQUES

### Requirement 1: Sécurisation des endpoints carte membres

**User Story:** En tant qu'administrateur, je veux que la carte des membres soit protégée par authentification, afin que les données de localisation des membres ne soient pas exposées publiquement.

#### Acceptance Criteria

1. WHEN un utilisateur non authentifié accède à `/admin/members/map/` THEN THE System SHALL rediriger vers la page de connexion
2. WHEN un utilisateur non authentifié accède à `/admin/members/map/data/` THEN THE System SHALL retourner une erreur 401 ou rediriger vers login
3. WHEN un utilisateur authentifié avec rôle admin ou secretariat accède à la carte THEN THE System SHALL afficher la carte des membres
4. WHEN un utilisateur authentifié sans rôle approprié accède à la carte THEN THE System SHALL afficher un message d'erreur de permission

### Requirement 2: Système de permissions par rôle (RBAC)

**User Story:** En tant que développeur, je veux un système centralisé de contrôle d'accès par rôle, afin de protéger les vues sensibles de manière cohérente.

#### Acceptance Criteria

1. THE System SHALL fournir un décorateur `@role_required(*roles)` réutilisable dans `apps/core/permissions.py`
2. THE System SHALL fournir un mixin `RoleRequiredMixin` pour les vues basées sur classes
3. WHEN un utilisateur sans le rôle requis accède à une vue protégée THEN THE System SHALL afficher un message d'erreur et rediriger vers le dashboard
4. THE System SHALL définir les rôles suivants avec leurs permissions:
   - `admin`: Accès total
   - `secretariat`: Gestion membres, utilisateurs
   - `finance`: Gestion finances, budgets, transactions
   - `responsable_club`: Gestion club biblique
   - `moniteur`: Accès limité club biblique (sa classe)
   - `responsable_groupe`: Gestion de son groupe
   - `encadrant`: Accès données pastorales
   - `membre`: Accès lecture seule limité

### Requirement 3: Protection des vues Finance

**User Story:** En tant que trésorier, je veux que seuls les utilisateurs autorisés puissent accéder aux données financières, afin de protéger les informations sensibles.

#### Acceptance Criteria

1. WHEN un utilisateur sans rôle finance/admin accède au dashboard finance THEN THE System SHALL refuser l'accès
2. WHEN un utilisateur sans rôle finance/admin tente de créer une transaction THEN THE System SHALL refuser l'accès
3. WHEN un utilisateur sans rôle finance/admin tente d'exporter des données financières THEN THE System SHALL refuser l'accès
4. THE System SHALL permettre aux rôles `admin` et `finance` d'accéder à toutes les fonctionnalités finance

### Requirement 4: Protection des exports de données

**User Story:** En tant qu'administrateur, je veux que les exports de données soient protégés par des permissions appropriées, afin d'éviter les fuites de données.

#### Acceptance Criteria

1. WHEN un utilisateur tente d'exporter des membres THEN THE System SHALL vérifier qu'il a le rôle admin ou secretariat
2. WHEN un utilisateur tente d'exporter des enfants du club THEN THE System SHALL vérifier qu'il a le rôle admin ou responsable_club
3. WHEN un utilisateur tente d'exporter des transactions THEN THE System SHALL vérifier qu'il a le rôle admin ou finance
4. WHEN un utilisateur tente d'exporter des budgets THEN THE System SHALL vérifier qu'il a le rôle admin ou finance
5. THE System SHALL logger toutes les tentatives d'export (réussies ou non)

### Requirement 5: Sécurisation du flux de login

**User Story:** En tant qu'utilisateur, je veux que le processus de connexion soit sécurisé, afin de protéger mon compte contre les attaques.

#### Acceptance Criteria

1. THE System SHALL NE PAS stocker le mot de passe temporaire en clair dans la session
2. WHEN un utilisateur échoue 5 tentatives de connexion THEN THE System SHALL bloquer temporairement le compte (15 minutes)
3. THE System SHALL utiliser un token sécurisé signé pour le flux de changement de mot de passe initial
4. WHEN un utilisateur se connecte depuis un nouvel appareil THEN THE System SHALL enregistrer l'événement dans les logs

### Requirement 6: Middleware de timeout de session

**User Story:** En tant qu'administrateur sécurité, je veux que les sessions inactives expirent automatiquement, afin de réduire les risques de détournement de session.

#### Acceptance Criteria

1. THE System SHALL déconnecter automatiquement un utilisateur après 30 minutes d'inactivité
2. WHEN une session expire THEN THE System SHALL afficher un message informatif à la reconnexion
3. THE System SHALL permettre de configurer la durée de timeout via les settings
4. THE System SHALL exclure certaines URLs du reset de timeout (API heartbeat)

---

## SECTION B: REFACTORING ARCHITECTURAL

### Requirement 7: Service Layer - Extraction logique métier

**User Story:** En tant que développeur, je veux que la logique métier soit séparée des vues, afin d'améliorer la testabilité et la maintenabilité du code.

#### Acceptance Criteria

1. THE System SHALL créer un fichier `services.py` dans chaque app contenant de la logique métier
2. WHEN une vue effectue une opération métier complexe THEN THE System SHALL déléguer à un service
3. THE System SHALL extraire la logique de création d'utilisateur de `accounts/views.py` vers `accounts/services.py`
4. THE System SHALL extraire la logique de transactions de `finance/views.py` vers `finance/services.py`
5. THE System SHALL extraire la logique de présences de `bibleclub/views.py` vers `bibleclub/services.py`

### Requirement 8: Audit Logging centralisé

**User Story:** En tant qu'administrateur, je veux un journal d'audit des actions sensibles, afin de tracer les modifications importantes.

#### Acceptance Criteria

1. THE System SHALL créer un modèle `AuditLog` dans `apps/core/models.py` avec: user, action, model, object_id, changes, ip_address, timestamp
2. THE System SHALL logger toutes les connexions/déconnexions via signals
3. THE System SHALL logger toutes les modifications de données sensibles (membres, finances) via signals
4. THE System SHALL logger toutes les tentatives d'accès refusées
5. THE System SHALL permettre de consulter les logs via l'interface admin Django
6. THE System SHALL conserver les logs pendant 1 an minimum

### Requirement 9: Rate limiting

**User Story:** En tant qu'administrateur système, je veux limiter le nombre de requêtes par utilisateur, afin de protéger l'application contre les abus.

#### Acceptance Criteria

1. THE System SHALL limiter les tentatives de login à 5 par minute par IP
2. THE System SHALL limiter les requêtes API à 100 par minute par utilisateur
3. WHEN la limite est atteinte THEN THE System SHALL retourner une erreur 429
4. THE System SHALL exclure les administrateurs des limites strictes

---

## SECTION C: MODULES INCOMPLETS

### Requirement 10: Complétion module Inventory (CRUD)

**User Story:** En tant que gestionnaire, je veux pouvoir gérer l'inventaire complet des équipements, afin de suivre le matériel de l'église.

#### Acceptance Criteria

1. THE System SHALL permettre de créer un nouvel équipement avec nom, catégorie, état, responsable, localisation
2. THE System SHALL permettre de modifier un équipement existant
3. THE System SHALL permettre de supprimer un équipement (soft delete avec is_active=False)
4. THE System SHALL afficher l'historique des modifications d'un équipement
5. WHEN un équipement est en mauvais état THEN THE System SHALL afficher une alerte visuelle

### Requirement 11: Complétion module Groups (CRUD)

**User Story:** En tant que responsable de groupe, je veux pouvoir gérer mon groupe de maison, afin d'organiser les réunions et suivre les membres.

#### Acceptance Criteria

1. THE System SHALL permettre de créer un nouveau groupe avec nom, type, responsable, lieu de réunion
2. THE System SHALL permettre de modifier les informations d'un groupe
3. THE System SHALL permettre d'ajouter/retirer des membres d'un groupe
4. THE System SHALL permettre de planifier des réunions de groupe
5. THE System SHALL afficher les statistiques de présence du groupe

### Requirement 12: Complétion module Departments (CRUD)

**User Story:** En tant qu'administrateur, je veux pouvoir gérer les départements de l'église, afin d'organiser les ministères.

#### Acceptance Criteria

1. THE System SHALL permettre de créer un nouveau département avec nom, description, responsable
2. THE System SHALL permettre de modifier un département existant
3. THE System SHALL permettre d'assigner des membres à un département
4. THE System SHALL afficher la liste des membres par département

### Requirement 13: Complétion module Campaigns (CRUD)

**User Story:** En tant que trésorier, je veux pouvoir gérer les campagnes de collecte, afin de suivre les objectifs financiers.

#### Acceptance Criteria

1. THE System SHALL permettre de créer une nouvelle campagne avec nom, objectif, dates début/fin
2. THE System SHALL permettre de modifier une campagne existante
3. THE System SHALL permettre d'enregistrer des dons pour une campagne
4. THE System SHALL afficher la progression en temps réel vers l'objectif (barre de progression)
5. WHEN une campagne atteint son objectif THEN THE System SHALL afficher une notification de succès

### Requirement 14: Complétion module Transport (CRUD)

**User Story:** En tant que coordinateur transport, je veux pouvoir gérer les chauffeurs et les demandes de transport, afin d'organiser les déplacements.

#### Acceptance Criteria

1. THE System SHALL permettre de créer/modifier un profil chauffeur avec véhicule et disponibilités
2. THE System SHALL permettre de créer une demande de transport avec date, heure, lieu, passagers
3. THE System SHALL permettre d'assigner un chauffeur à une demande
4. THE System SHALL afficher le planning des transports sous forme de calendrier
5. WHEN un transport est confirmé THEN THE System SHALL notifier le demandeur par email

---

## SECTION D: FONCTIONNALITÉS AVANCÉES

### Requirement 15: Events CRUD complet

**User Story:** En tant qu'organisateur, je veux pouvoir gérer complètement les événements, afin de planifier les activités de l'église.

#### Acceptance Criteria

1. THE System SHALL permettre de créer un événement avec titre, description, dates, lieu, catégorie
2. THE System SHALL permettre de modifier un événement existant
3. THE System SHALL permettre d'annuler un événement (avec notification aux inscrits)
4. THE System SHALL permettre de dupliquer un événement existant
5. THE System SHALL afficher les événements dans un calendrier interactif

### Requirement 16: Notifications email/SMS

**User Story:** En tant qu'administrateur, je veux pouvoir envoyer des notifications aux membres, afin de les informer des événements importants.

#### Acceptance Criteria

1. THE System SHALL permettre d'envoyer des emails de notification pour les événements
2. THE System SHALL permettre d'envoyer des rappels automatiques avant les événements
3. THE System SHALL logger tous les emails envoyés avec leur statut
4. THE System SHALL permettre de configurer les templates d'emails via l'admin

### Requirement 17: Traitement OCR asynchrone

**User Story:** En tant que trésorier, je veux que le traitement OCR des justificatifs soit asynchrone, afin de ne pas bloquer l'interface utilisateur.

#### Acceptance Criteria

1. WHEN un justificatif est uploadé THEN THE System SHALL créer une tâche Celery pour le traitement OCR
2. THE System SHALL afficher un indicateur de progression pendant le traitement
3. WHEN le traitement OCR est terminé THEN THE System SHALL notifier l'utilisateur
4. IF le traitement OCR échoue THEN THE System SHALL permettre de relancer manuellement

### Requirement 18: Backup automatique

**User Story:** En tant qu'administrateur système, je veux des sauvegardes automatiques de la base de données, afin de prévenir la perte de données.

#### Acceptance Criteria

1. THE System SHALL effectuer une sauvegarde quotidienne de la base de données via Celery Beat
2. THE System SHALL conserver les 30 dernières sauvegardes
3. THE System SHALL permettre de télécharger une sauvegarde depuis l'admin
4. THE System SHALL envoyer une alerte si une sauvegarde échoue

---

## SECTION E: AMÉLIORATIONS UI/UX

### Requirement 19: Système de Toasts (notifications flottantes)

**User Story:** En tant qu'utilisateur, je veux des notifications visuelles élégantes, afin d'être informé du résultat de mes actions.

#### Acceptance Criteria

1. THE System SHALL afficher des toasts pour les messages de succès, erreur, warning, info
2. THE System SHALL permettre de fermer manuellement un toast
3. THE System SHALL auto-fermer les toasts après 5 secondes (configurable)
4. THE System SHALL empiler les toasts multiples sans chevauchement

### Requirement 20: HTMX et Skeleton Loaders

**User Story:** En tant qu'utilisateur, je veux une interface réactive sans rechargement de page, afin d'avoir une meilleure expérience utilisateur.

#### Acceptance Criteria

1. THE System SHALL utiliser HTMX pour la pagination des listes sans rechargement
2. THE System SHALL afficher des skeleton loaders pendant le chargement des données
3. THE System SHALL utiliser HTMX pour les formulaires de recherche/filtrage
4. THE System SHALL permettre le tri des tableaux sans rechargement de page

### Requirement 21: Dashboard Charts

**User Story:** En tant qu'administrateur, je veux des graphiques sur le dashboard, afin de visualiser les statistiques clés.

#### Acceptance Criteria

1. THE System SHALL afficher un graphique d'évolution des dons (ligne) sur le dashboard finance
2. THE System SHALL afficher un graphique de répartition des dépenses par catégorie (camembert)
3. THE System SHALL afficher un graphique de présences au club biblique (barres)
4. THE System SHALL permettre de filtrer les graphiques par période

### Requirement 22: Refonte CSS - Extraction styles inline

**User Story:** En tant que développeur, je veux que les styles CSS soient centralisés, afin de faciliter la maintenance et la cohérence visuelle.

#### Acceptance Criteria

1. THE System SHALL extraire tous les styles inline des templates vers des fichiers CSS
2. THE System SHALL créer un fichier `static/css/components.css` pour les composants réutilisables
3. THE System SHALL utiliser des classes CSS cohérentes basées sur une convention de nommage (BEM)
4. THE System SHALL documenter les classes CSS disponibles

### Requirement 23: Pages d'erreur personnalisées

**User Story:** En tant qu'utilisateur, je veux des pages d'erreur informatives et cohérentes, afin de comprendre ce qui s'est passé.

#### Acceptance Criteria

1. THE System SHALL afficher une page 403 personnalisée avec message explicatif
2. THE System SHALL afficher une page 404 personnalisée avec suggestions de navigation
3. THE System SHALL afficher une page 500 personnalisée avec message d'excuse et contact support
4. THE System SHALL logger les erreurs 500 avec contexte complet

---

## SECTION F: QUALITÉ ET TESTS

### Requirement 24: Tests automatisés prioritaires

**User Story:** En tant que développeur, je veux des tests automatisés pour les modules critiques, afin de garantir la stabilité du code.

#### Acceptance Criteria

1. THE System SHALL avoir des tests unitaires pour le module accounts (login, création user, permissions)
2. THE System SHALL avoir des tests unitaires pour le module finance (transactions, budgets)
3. THE System SHALL avoir des tests d'intégration pour les flux critiques (login → dashboard)
4. THE System SHALL avoir une couverture de code minimale de 70% pour accounts et finance
5. THE System SHALL exécuter les tests automatiquement via CI/CD

### Requirement 25: Validation des formulaires

**User Story:** En tant qu'utilisateur, je veux des messages d'erreur clairs sur les formulaires, afin de corriger facilement mes saisies.

#### Acceptance Criteria

1. THE System SHALL valider les formulaires côté client (HTML5 + JavaScript)
2. THE System SHALL valider les formulaires côté serveur (Django forms)
3. THE System SHALL afficher les erreurs de validation à côté des champs concernés
4. THE System SHALL utiliser des messages d'erreur en français compréhensibles

### Requirement 26: Obfuscation des données sensibles sur la carte

**User Story:** En tant qu'administrateur, je veux que les coordonnées GPS des membres soient légèrement décalées, afin de protéger leur vie privée.

#### Acceptance Criteria

1. WHEN la carte affiche un membre THEN THE System SHALL ajouter un décalage aléatoire de 50-100m aux coordonnées
2. THE System SHALL afficher un cercle de zone plutôt qu'un point précis
3. THE System SHALL permettre aux admins de voir les coordonnées exactes si nécessaire
4. THE System SHALL documenter cette fonctionnalité de protection de la vie privée

---

## SECTION G: PROTECTION DES VUES EXISTANTES

### Requirement 27: Protection des vues Members/Pastoral

**User Story:** En tant que pasteur, je veux que les données pastorales soient accessibles uniquement au personnel autorisé, afin de respecter la confidentialité.

#### Acceptance Criteria

1. WHEN un utilisateur sans rôle pastoral accède aux événements de vie THEN THE System SHALL refuser l'accès
2. WHEN un utilisateur sans rôle pastoral accède aux visites pastorales THEN THE System SHALL refuser l'accès
3. THE System SHALL permettre aux rôles `admin`, `secretariat` et `encadrant` d'accéder aux données pastorales
4. THE System SHALL permettre à tous les utilisateurs authentifiés de voir la liste des membres (lecture seule)

### Requirement 28: Protection des vues Worship

**User Story:** En tant que responsable de culte, je veux que seuls les utilisateurs autorisés puissent gérer les plannings de culte, afin d'éviter les modifications non autorisées.

#### Acceptance Criteria

1. WHEN un utilisateur sans rôle worship accède à la création de service THEN THE System SHALL refuser l'accès
2. WHEN un utilisateur sans rôle worship tente de modifier un planning THEN THE System SHALL refuser l'accès
3. THE System SHALL permettre à tous les utilisateurs authentifiés de consulter les services (lecture seule)
4. THE System SHALL permettre aux rôles `admin` et `responsable_groupe` de gérer les cultes

