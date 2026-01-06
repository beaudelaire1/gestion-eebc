# Implementation Plan: Security Audit Fixes

## Overview

Ce plan d'implémentation couvre les corrections de sécurité critiques, le refactoring architectural, la complétion des modules CRUD et les améliorations UI/UX du projet Gestion EEBC. Les tâches sont organisées par priorité et dépendances.

## Tasks

### Phase 1: Sécurité Critique

- [x] 1. Système de permissions RBAC centralisé
  - [x] 1.1 Créer `apps/core/permissions.py` avec décorateur `@role_required`
    - Implémenter le décorateur acceptant une liste de rôles
    - Gérer la redirection avec message d'erreur
    - _Requirements: 2.1, 2.3_
  - [x] 1.2 Créer le mixin `RoleRequiredMixin` pour les CBV
    - Attribut `allowed_roles` pour définir les rôles autorisés
    - Méthode `handle_no_permission()` personnalisée
    - _Requirements: 2.2_
  - [x] 1.3 Créer la fonction utilitaire `has_role(user, *roles)`
    - Vérifier si l'utilisateur a l'un des rôles spécifiés
    - Gérer le cas superuser (accès total)
    - _Requirements: 2.4_
  - [x] 1.4 Écrire les tests unitaires pour le système RBAC
    - **Property 1: Permission Enforcement**
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4**

- [x] 2. Sécurisation des endpoints carte membres
  - [x] 2.1 Ajouter `@login_required` et `@role_required` à `members_map_view`
    - Modifier `apps/members/admin_views.py`
    - Rôles autorisés: admin, secretariat
    - _Requirements: 1.1, 1.3, 1.4_
  - [x] 2.2 Ajouter `@login_required` et `@role_required` à `members_map_data`
    - Protéger l'API JSON
    - _Requirements: 1.2_
  - [x] 2.3 Implémenter l'obfuscation GPS des coordonnées membres
    - Ajouter un décalage aléatoire de 50-100m
    - Permettre aux admins de voir les coordonnées exactes
    - _Requirements: 26.1, 26.2, 26.3_
  - [x] 2.4 Écrire les tests pour la sécurisation de la carte
    - **Property 7: GPS Obfuscation**
    - **Validates: Requirements 1.1, 1.2, 26.1**

- [x] 3. Sécurisation du flux de login
  - [x] 3.1 Créer le modèle `PasswordChangeToken` dans `apps/accounts/models.py`
    - Champs: user, token, created_at, used, expires_at
    - Méthode `is_valid()`
    - _Requirements: 5.3_
  - [x] 3.2 Créer `apps/accounts/services.py` avec `AuthenticationService`
    - Méthode `generate_password_change_token(user)`
    - Méthode `verify_password_change_token(token)`
    - Utiliser `django.core.signing` pour les tokens
    - _Requirements: 5.1, 5.3_
  - [x] 3.3 Modifier `login_view` pour utiliser le token signé
    - Supprimer le stockage du mot de passe en session
    - Utiliser le token pour le flux de changement de mot de passe
    - _Requirements: 5.1_
  - [x] 3.4 Modifier `first_login_password_change` pour utiliser le token
    - Valider le token au lieu de lire la session
    - _Requirements: 5.3_
  - [x] 3.5 Ajouter le rate limiting sur le login
    - Bloquer après 5 tentatives échouées pendant 15 minutes
    - Ajouter champs `failed_login_attempts` et `locked_until` au modèle User
    - _Requirements: 5.2_
  - [x] 3.6 Écrire les tests pour le flux de login sécurisé
    - **Property 4: Login Rate Limiting**
    - **Property 5: Secure Password Change Flow**
    - **Validates: Requirements 5.1, 5.2, 5.3**

- [x] 4. Protection des vues Finance
  - [x] 4.1 Ajouter `@role_required('admin', 'finance')` aux vues finance
    - Modifier `apps/finance/views.py`: dashboard, transaction_create, transaction_validate
    - _Requirements: 3.1, 3.2, 3.4_
  - [x] 4.2 Ajouter `@role_required` aux vues budget
    - Modifier `apps/finance/budget_views.py`
    - _Requirements: 3.4_
  - [x] 4.3 Écrire les tests de protection des vues finance
    - **Property 1: Permission Enforcement**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4**

- [-] 5. Protection des exports de données
  - [x] 5.1 Créer un mixin `ExportPermissionMixin` dans `apps/core/export_views.py`
    - Définir les permissions par type d'export
    - _Requirements: 4.1, 4.2, 4.3, 4.4_
  - [x] 5.2 Appliquer les permissions aux vues d'export existantes
    - MembersExportView: admin, secretariat
    - ChildrenExportView: admin, responsable_club
    - TransactionsExportView, BudgetsExportView: admin, finance
    - _Requirements: 4.1, 4.2, 4.3, 4.4_
  - [x] 5.3 Écrire les tests de protection des exports
    - **Property 2: Export Permission Verification**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4**

- [x] 6. Checkpoint - Vérifier la sécurité de base
  - Ensure all tests pass, ask the user if questions arise.

### Phase 2: Infrastructure

- [x] 7. Modèle AuditLog et système de logging
  - [x] 7.1 Créer le modèle `AuditLog` dans `apps/core/models.py`
    - Champs: user, action, model_name, object_id, object_repr, changes, ip_address, user_agent, timestamp
    - Index sur user, action, model_name, timestamp
    - _Requirements: 8.1_
  - [x] 7.2 Créer les signals pour le logging automatique
    - Signal post_save pour les modèles sensibles (Member, FinancialTransaction)
    - Signal post_delete
    - _Requirements: 8.3_
  - [x] 7.3 Créer le signal pour logging des connexions/déconnexions
    - Utiliser `user_logged_in` et `user_logged_out` de Django
    - _Requirements: 8.2_
  - [x] 7.4 Logger les tentatives d'accès refusées dans le décorateur RBAC
    - Créer une entrée AuditLog avec action ACCESS_DENIED
    - _Requirements: 8.4_
  - [x] 7.5 Logger les exports dans les vues d'export
    - Créer une entrée AuditLog avec action EXPORT
    - _Requirements: 4.5_
  - [x] 7.6 Enregistrer AuditLog dans l'admin Django
    - Créer `apps/core/admin.py` avec AuditLogAdmin
    - _Requirements: 8.5_
  - [x] 7.7 Écrire les tests pour l'audit logging
    - **Property 3: Audit Log Creation**
    - **Validates: Requirements 4.5, 8.2, 8.3, 8.4**

- [x] 8. Middleware de session timeout
  - [x] 8.1 Créer `SessionTimeoutMiddleware` dans `apps/core/middleware.py`
    - Vérifier le timestamp de dernière activité
    - Déconnecter si timeout dépassé
    - Exclure les URLs configurées
    - _Requirements: 6.1, 6.4_
  - [x] 8.2 Ajouter le setting `SESSION_TIMEOUT_MINUTES` dans settings
    - Valeur par défaut: 30 minutes
    - _Requirements: 6.3_
  - [x] 8.3 Ajouter le message informatif après expiration
    - Stocker un flag dans la session avant déconnexion
    - Afficher le message sur la page de login
    - _Requirements: 6.2_
  - [x] 8.4 Enregistrer le middleware dans settings
    - Ajouter à MIDDLEWARE après AuthenticationMiddleware
  - [x] 8.5 Écrire les tests pour le session timeout
    - **Property 6: Session Timeout**
    - **Validates: Requirements 6.1, 6.2, 6.4**

- [-] 9. Rate limiting middleware
  - [x] 9.1 Créer `RateLimitMiddleware` dans `apps/core/middleware.py`
    - Utiliser le cache Django pour stocker les compteurs
    - Limite par défaut: 100 requêtes/minute par utilisateur
    - _Requirements: 9.2_
  - [x] 9.2 Retourner une réponse 429 quand la limite est atteinte
    - Inclure le header Retry-After
    - _Requirements: 9.3_
  - [x] 9.3 Exclure les administrateurs des limites strictes
    - Vérifier le rôle admin avant d'appliquer la limite
    - _Requirements: 9.4_
  - [x] 9.4 Écrire les tests pour le rate limiting
    - **Property 4: Login Rate Limiting**
    - **Validates: Requirements 9.1, 9.2, 9.3, 9.4**

- [x] 10. Checkpoint - Vérifier l'infrastructure
  - Ensure all tests pass, ask the user if questions arise.

### Phase 3: Service Layer Refactoring

- [x] 11. Service Layer pour accounts
  - [x] 11.1 Compléter `apps/accounts/services.py`
    - Méthode `create_user_by_team()` (extraire de views.py)
    - Méthode `activate_user_account()`
    - Méthode `record_login_attempt()`
    - _Requirements: 7.3_
  - [x] 11.2 Refactorer `create_user_view` pour utiliser le service
    - Déléguer la logique métier au service
    - La vue ne fait que: recevoir requête → appeler service → renvoyer réponse
    - _Requirements: 7.2_
  - [x] 11.3 Écrire les tests pour AccountsService
    - Tests unitaires des méthodes du service

- [-] 12. Service Layer pour finance
  - [x] 12.1 Créer `apps/finance/services.py`
    - Classe `TransactionService` avec méthodes CRUD
    - Classe `BudgetService` avec méthodes de gestion budget
    - _Requirements: 7.4_
  - [x] 12.2 Refactorer les vues finance pour utiliser les services
    - `dashboard`, `transaction_create`, `transaction_validate`
    - _Requirements: 7.2_
  - [ ] 12.3 Écrire les tests pour FinanceService
    - Tests unitaires des méthodes du service

- [x] 13. Service Layer pour bibleclub
  - [x] 13.1 Créer `apps/bibleclub/services.py`
    - Classe `AttendanceService` pour la gestion des présences
    - _Requirements: 7.5_
  - [x] 13.2 Refactorer les vues bibleclub pour utiliser les services
    - _Requirements: 7.2_

- [x] 14. Checkpoint - Vérifier le refactoring
  - Ensure all tests pass, ask the user if questions arise.

### Phase 4: Protection des vues existantes

- [x] 15. Protection des vues Members/Pastoral
  - [x] 15.1 Ajouter `@role_required` aux vues pastorales
    - Événements de vie: admin, secretariat, encadrant
    - Visites pastorales: admin, secretariat, encadrant
    - _Requirements: 27.1, 27.2, 27.3_
  - [x] 15.2 Permettre la lecture seule de la liste des membres
    - Tous les utilisateurs authentifiés peuvent voir la liste
    - _Requirements: 27.4_

- [-] 16. Protection des vues Worship
  - [x] 16.1 Ajouter `@role_required` aux vues worship
    - Création/modification de service: admin, responsable_groupe
    - _Requirements: 28.1, 28.2, 28.4_
  - [x] 16.2 Permettre la consultation en lecture seule
    - Tous les utilisateurs authentifiés peuvent consulter
    - _Requirements: 28.3_

- [x] 17. Checkpoint - Vérifier les protections
  - Ensure all tests pass, ask the user if questions arise.

### Phase 5: Modules CRUD incomplets

- [x] 18. Complétion module Inventory
  - [x] 18.1 Créer les vues CRUD pour Inventory
    - `inventory_create`, `inventory_update`, `inventory_delete`
    - Soft delete avec is_active=False
    - _Requirements: 10.1, 10.2, 10.3_
  - [x] 18.2 Créer les templates pour Inventory
    - `inventory/create.html`, `inventory/edit.html`
    - _Requirements: 10.1, 10.2_
  - [x] 18.3 Ajouter l'historique des modifications
    - Utiliser AuditLog pour tracer les changements
    - _Requirements: 10.4_
  - [x] 18.4 Ajouter l'alerte visuelle pour mauvais état
    - Badge ou icône d'alerte dans la liste
    - _Requirements: 10.5_

- [x] 19. Complétion module Groups
  - [x] 19.1 Créer les vues CRUD pour Groups
    - `group_create`, `group_update`, `group_members_manage`
    - _Requirements: 11.1, 11.2, 11.3_
  - [x] 19.2 Créer les templates pour Groups
    - _Requirements: 11.1, 11.2_
  - [x] 19.3 Ajouter la planification de réunions
    - Modèle GroupMeeting si nécessaire
    - _Requirements: 11.4_
  - [x] 19.4 Ajouter les statistiques de présence
    - Vue avec graphiques de présence
    - _Requirements: 11.5_

- [x] 20. Complétion module Departments
  - [x] 20.1 Créer les vues CRUD pour Departments
    - `department_create`, `department_update`, `department_members`
    - _Requirements: 12.1, 12.2, 12.3_
  - [x] 20.2 Créer les templates pour Departments
    - _Requirements: 12.1, 12.2_
  - [x] 20.3 Afficher la liste des membres par département
    - _Requirements: 12.4_

- [x] 21. Complétion module Campaigns
  - [x] 21.1 Créer les vues CRUD pour Campaigns
    - `campaign_create`, `campaign_update`, `campaign_donate`
    - _Requirements: 13.1, 13.2, 13.3_
  - [x] 21.2 Créer les templates pour Campaigns
    - Inclure barre de progression vers l'objectif
    - _Requirements: 13.4_
  - [x] 21.3 Ajouter la notification de succès
    - Toast quand l'objectif est atteint
    - _Requirements: 13.5_

- [-] 22. Complétion module Transport
  - [x] 22.1 Créer les vues CRUD pour Transport
    - `driver_create`, `driver_update`, `transport_request_create`
    - _Requirements: 14.1, 14.2_
  - [x] 22.2 Créer la vue d'assignation chauffeur
    - _Requirements: 14.3_
  - [x] 22.3 Créer le calendrier des transports
    - Vue calendrier avec FullCalendar ou similaire
    - _Requirements: 14.4_
  - [x] 22.4 Ajouter la notification email de confirmation
    - _Requirements: 14.5_

- [x] 23. Complétion module Events
  - [x] 23.1 Créer les vues CRUD complètes pour Events
    - `event_create`, `event_update`, `event_cancel`, `event_duplicate`
    - _Requirements: 15.1, 15.2, 15.3, 15.4_
  - [x] 23.2 Créer le calendrier interactif des événements
    - _Requirements: 15.5_

- [x] 24. Checkpoint - Vérifier les modules CRUD
  - Ensure all tests pass, ask the user if questions arise.

### Phase 6: Fonctionnalités avancées

- [x] 25. Notifications email
  - [x] 25.1 Créer `apps/communication/services.py` pour l'envoi d'emails
    - Méthode `send_event_notification()`
    - Méthode `send_reminder()`
    - _Requirements: 16.1, 16.2_
  - [x] 25.2 Créer les templates d'emails configurables
    - Stocker dans l'admin Django
    - _Requirements: 16.4_
  - [x] 25.3 Logger tous les emails envoyés
    - Modèle EmailLog avec statut
    - _Requirements: 16.3_

- [-] 26. Traitement OCR asynchrone
  - [x] 26.1 Créer la tâche Celery pour l'OCR
    - `apps/finance/tasks.py` avec `process_ocr_task`
    - _Requirements: 17.1_
  - [x] 26.2 Modifier `receipt_proof_upload` pour créer la tâche
    - Retourner immédiatement avec statut "en cours"
    - _Requirements: 17.1_
  - [x] 26.3 Ajouter l'indicateur de progression
    - Polling AJAX ou WebSocket pour le statut
    - _Requirements: 17.2_
  - [x] 26.4 Notifier l'utilisateur à la fin du traitement
    - Toast de notification
    - _Requirements: 17.3_
  - [x] 26.5 Permettre de relancer manuellement en cas d'échec
    - Bouton "Relancer OCR"
    - _Requirements: 17.4_
  - [x] 26.6 Écrire les tests pour les tâches Celery
    - **Property 10: Celery Task Execution**
    - **Validates: Requirements 17.1, 17.2, 17.3, 17.4**

- [x] 27. Backup automatique
  - [x] 27.1 Créer la tâche Celery Beat pour le backup quotidien
    - `apps/core/tasks.py` avec `backup_database_task`
    - _Requirements: 18.1_
  - [x] 27.2 Implémenter la rotation des backups (30 derniers)
    - _Requirements: 18.2_
  - [x] 27.3 Ajouter le téléchargement depuis l'admin
    - Vue admin pour lister et télécharger les backups
    - _Requirements: 18.3_
  - [x] 27.4 Envoyer une alerte en cas d'échec
    - Email à l'admin
    - _Requirements: 18.4_

- [x] 28. Checkpoint - Vérifier les fonctionnalités avancées
  - Ensure all tests pass, ask the user if questions arise.

### Phase 7: Améliorations UI/UX

- [x] 29. Système de Toasts
  - [x] 29.1 Créer le composant Toast JavaScript
    - `static/js/toasts.js`
    - Support des types: success, error, warning, info
    - _Requirements: 19.1_
  - [x] 29.2 Créer le template partial pour les toasts
    - `templates/components/toast.html`
    - _Requirements: 19.1_
  - [x] 29.3 Intégrer avec les messages Django
    - Convertir les messages Django en toasts
    - _Requirements: 19.1_
  - [x] 29.4 Ajouter la fermeture manuelle et auto-fermeture
    - Configurable (défaut: 5 secondes)
    - _Requirements: 19.2, 19.3_
  - [x] 29.5 Gérer l'empilement des toasts
    - _Requirements: 19.4_

- [x] 30. HTMX et Skeleton Loaders
  - [x] 30.1 Ajouter HTMX au projet
    - Inclure dans base.html
    - _Requirements: 20.1_
  - [x] 30.2 Créer les skeleton loaders CSS
    - `static/css/skeletons.css`
    - _Requirements: 20.2_
  - [x] 30.3 Convertir la pagination des listes en HTMX
    - member_list, transaction_list, etc.
    - _Requirements: 20.1_
  - [x] 30.4 Ajouter les skeleton loaders pendant le chargement
    - _Requirements: 20.2_
  - [x] 30.5 Convertir les formulaires de recherche/filtrage en HTMX
    - _Requirements: 20.3_
  - [x] 30.6 Ajouter le tri des tableaux sans rechargement
    - _Requirements: 20.4_

- [x] 31. Dashboard Charts
  - [x] 31.1 Ajouter Chart.js ou ApexCharts au projet
    - _Requirements: 21.1_
  - [x] 31.2 Créer le graphique d'évolution des dons
    - Graphique en ligne sur 12 mois
    - _Requirements: 21.1_
  - [x] 31.3 Créer le graphique de répartition des dépenses
    - Camembert par catégorie
    - _Requirements: 21.2_
  - [x] 31.4 Créer le graphique de présences club biblique
    - Graphique en barres
    - _Requirements: 21.3_
  - [x] 31.5 Ajouter les filtres par période
    - _Requirements: 21.4_

- [x] 32. Refonte CSS
  - [x] 32.1 Créer `static/css/components.css`
    - Extraire les styles inline des templates
    - _Requirements: 22.1, 22.2_
  - [x] 32.2 Appliquer la convention BEM
    - Renommer les classes CSS
    - _Requirements: 22.3_
  - [x] 32.3 Documenter les classes CSS disponibles
    - Créer un fichier de documentation
    - _Requirements: 22.4_

- [x] 33. Pages d'erreur personnalisées
  - [x] 33.1 Créer `templates/errors/403.html`
    - Message explicatif et bouton retour
    - _Requirements: 23.1_
  - [x] 33.2 Créer `templates/errors/404.html`
    - Suggestions de navigation
    - _Requirements: 23.2_
  - [x] 33.3 Créer `templates/errors/500.html`
    - Message d'excuse et contact support
    - _Requirements: 23.3_
  - [x] 33.4 Configurer les handlers dans urls.py
    - handler403, handler404, handler500
    - _Requirements: 23.1, 23.2, 23.3_
  - [x] 33.5 Logger les erreurs 500 avec contexte complet
    - _Requirements: 23.4_

- [x] 34. Checkpoint - Vérifier les améliorations UI/UX
  - Ensure all tests pass, ask the user if questions arise.

### Phase 8: Tests et Validation

- [x] 35. Validation des formulaires
  - [x] 35.1 Ajouter la validation HTML5 aux formulaires
    - Attributs required, pattern, min, max
    - _Requirements: 25.1_
  - [x] 35.2 Ajouter la validation JavaScript
    - Validation en temps réel
    - _Requirements: 25.1_
  - [x] 35.3 Améliorer les messages d'erreur Django
    - Messages en français compréhensibles
    - _Requirements: 25.4_
  - [x] 35.4 Afficher les erreurs à côté des champs
    - _Requirements: 25.3_
  - [x] 35.5 Écrire les tests de validation
    - **Property 9: Form Validation Consistency**
    - **Validates: Requirements 25.1, 25.2, 25.3, 25.4**

- [x] 36. Tests automatisés prioritaires
  - [x] 36.1 Configurer pytest-django et pytest-cov
    - Fichier pytest.ini
    - _Requirements: 24.5_
  - [x] 36.2 Créer les fixtures de test dans conftest.py
    - Utilisateurs avec différents rôles
    - _Requirements: 24.1_
  - [x] 36.3 Écrire les tests unitaires pour accounts
    - Login, création user, permissions
    - _Requirements: 24.1_
  - [x] 36.4 Écrire les tests unitaires pour finance
    - Transactions, budgets
    - _Requirements: 24.2_
  - [x] 36.5 Écrire les tests d'intégration
    - Flux login → dashboard
    - _Requirements: 24.3_
  - [x] 36.6 Configurer GitHub Actions pour CI/CD
    - Exécution automatique des tests
    - _Requirements: 24.5_
  - [x] 36.7 Vérifier la couverture de code (objectif: 70%)
    - _Requirements: 24.4_

- [x] 37. Final checkpoint - Validation complète
  - Ensure all tests pass, ask the user if questions arise.
  - Vérifier que toutes les corrections de sécurité sont en place
  - Vérifier que tous les modules CRUD sont fonctionnels
  - Vérifier que l'UI/UX est cohérente

## Notes

- Toutes les tâches sont obligatoires pour une implémentation complète
- Chaque tâche référence les requirements spécifiques pour la traçabilité
- Les checkpoints permettent de valider chaque phase avant de continuer
- Les property tests valident les propriétés de correction définies dans le design
- Les tests sont intégrés à chaque phase pour garantir la qualité du code
