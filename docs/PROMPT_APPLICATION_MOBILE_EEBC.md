# Prompt — Création de l'Application Mobile EEBC (Flutter)

## Contexte du projet

Tu es un développeur Flutter expert. Tu dois créer l'application mobile **EEBC** (Église Évangélique Baptiste de Cabassou) en **Flutter/Dart**. Cette application est le compagnon mobile d'un système de gestion d'église basé sur **Django REST Framework**. L'API backend est déjà entièrement fonctionnelle et déployée à l'adresse `https://eglise-ebc.org/api/v1/`.

L'église gère **2 sites** : **Cabassou** (principal) et **Macouria**. Chaque donnée (membres, événements, cultes) peut être filtrée par site.

---

## Stack technique imposée

- **Framework** : Flutter 3.x (Dart SDK ^3.5.4)
- **State Management** : Provider 6.x
- **Navigation** : GoRouter 13.x
- **HTTP** : Dio 5.x (avec intercepteur JWT)
- **Stockage sécurisé** : flutter_secure_storage 9.x
- **UI** : Material 3, Google Fonts (Poppins), cached_network_image, flutter_svg, flutter_spinkit
- **Notifications** : Firebase Core + Firebase Messaging + flutter_local_notifications
- **Autres** : intl (i18n/dates), url_launcher, shared_preferences

---

## Architecture cible

```text
lib/
├── main.dart
├── config/
│   ├── app_config.dart          # URLs API, constantes, timeouts
│   ├── routes.dart              # GoRouter avec toutes les routes
│   └── theme.dart               # Thèmes clair/sombre Material 3
├── models/
│   ├── user.dart                # Modèle User (auth + profil)
│   ├── member.dart              # Modèle Member
│   ├── event.dart               # Modèle Event + EventRegistration
│   ├── worship_service.dart     # Modèle WorshipService + RoleAssignment
│   ├── announcement.dart        # Modèle Announcement
│   ├── donation.dart            # Modèle OnlineDonation + TaxReceipt
│   ├── bible_club.dart          # Modèle Child + Attendance
│   └── notification.dart        # Modèle Notification
├── providers/
│   ├── auth_provider.dart       # État d'authentification global
│   ├── members_provider.dart
│   ├── events_provider.dart
│   ├── worship_provider.dart
│   ├── announcements_provider.dart
│   ├── donations_provider.dart
│   ├── bible_club_provider.dart
│   ├── notifications_provider.dart
│   └── theme_provider.dart      # Gestion thème clair/sombre
├── services/
│   ├── api_service.dart         # Client Dio avec intercepteur JWT auto-refresh
│   ├── auth_service.dart        # Login, logout, refresh, stockage tokens
│   ├── notification_service.dart # Firebase Messaging + local notifications
│   └── storage_service.dart     # Abstraction stockage local
├── screens/
│   ├── splash_screen.dart
│   ├── login_screen.dart
│   ├── change_password_screen.dart
│   ├── home/
│   │   └── home_screen.dart     # Dashboard principal
│   ├── members/
│   │   ├── members_list_screen.dart
│   │   └── member_detail_screen.dart
│   ├── events/
│   │   ├── events_list_screen.dart
│   │   └── event_detail_screen.dart
│   ├── worship/
│   │   ├── worship_list_screen.dart
│   │   └── worship_detail_screen.dart
│   ├── announcements/
│   │   ├── announcements_list_screen.dart
│   │   └── announcement_detail_screen.dart
│   ├── donations/
│   │   ├── donations_screen.dart
│   │   ├── donation_form_screen.dart
│   │   └── receipts_screen.dart
│   ├── bible_club/
│   │   └── bible_club_screen.dart
│   ├── profile/
│   │   ├── profile_screen.dart
│   │   └── settings_screen.dart
│   └── notifications/
│       └── notifications_screen.dart
├── widgets/
│   ├── common/
│   │   ├── app_scaffold.dart     # Scaffold avec BottomNavBar
│   │   ├── loading_indicator.dart
│   │   ├── error_widget.dart
│   │   ├── empty_state_widget.dart
│   │   ├── search_bar.dart
│   │   ├── badge_widget.dart
│   │   └── avatar_widget.dart
│   ├── cards/
│   │   ├── member_card.dart
│   │   ├── event_card.dart
│   │   ├── worship_card.dart
│   │   ├── announcement_card.dart
│   │   └── donation_card.dart
│   └── forms/
│       ├── custom_text_field.dart
│       └── custom_button.dart
└── utils/
    ├── date_helpers.dart
    ├── validators.dart
    ├── constants.dart
    └── extensions.dart
```

---

## Endpoints API disponibles

### Authentification (JWT)
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/auth/login/` | Login → retourne `{access, refresh, user: {id, username, email, first_name, last_name, role, must_change_password}}` |
| POST | `/auth/refresh/` | Body: `{refresh}` → retourne `{access}` |
| POST | `/auth/logout/` | Body: `{refresh}` → blacklist le token |
| PUT | `/auth/password/` | Body: `{old_password, new_password}` |

### Profil
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET/PUT | `/profile/` | Profil utilisateur avec infos membre liées |

### Membres (Annuaire)
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/members/` | Liste paginée, params: `?search=&site=&ordering=&page=` |
| GET | `/members/{id}/` | Détail membre complet |

### Événements
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/events/` | Événements à venir, params: `?search=&site=&start_date=&end_date=` |
| GET | `/events/{id}/` | Détail événement |
| GET | `/events/my_registrations/` | Mes inscriptions |
| POST | `/events/{id}/register/` | S'inscrire |
| DELETE | `/events/{id}/register/` | Se désinscrire |

### Cultes (Worship)
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/worship/services/` | Liste des services, params: `?site=` |
| GET | `/worship/services/{id}/` | Détail avec rôles/assignations |
| GET | `/worship/services/my_assignments/` | Mes assignations |
| GET | `/worship/services/history/` | Historique (3 derniers mois) |
| POST | `/worship/confirm/` | Body: `{assignment_id, action: "confirm"|"decline"}` |

### Annonces
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/announcements/` | Annonces actives (épinglées en premier) |
| GET | `/announcements/{id}/` | Détail |
| POST | `/announcements/{id}/mark_read/` | Marquer comme lue |

### Dons
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/donations/` | Historique des dons du membre |
| POST | `/donations/` | Créer un don Stripe : `{amount, donation_type, donor_name, donor_email, is_recurring?, recurring_interval?}` |
| GET | `/donations/receipts/` | Reçus fiscaux PDF |

### Club Biblique
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/bibleclub/my-children/` | Enfants du parent connecté avec historique de présences |

### Notifications Push
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/notifications/register/` | Body: `{token, device_type: "android"|"ios"}` |
| DELETE | `/notifications/register/` | Désenregistrer l'appareil |

---

## Modèles de données Dart à créer

### User
```dart
class User {
  final int id;
  final String username;
  final String email;
  final String firstName;
  final String lastName;
  final String role;         // "admin,pasteur" (multi-rôle, séparé par virgules)
  final String? phone;
  final String? photo;
  final bool mustChangePassword;
  
  factory User.fromJson(Map<String, dynamic> json);
  Map<String, dynamic> toJson();
}
```

### Member
```dart
class Member {
  final int id;
  final String memberId;      // Format "EEBC-CAB-0001"
  final String firstName;
  final String lastName;
  final String? email;
  final String? phone;
  final String? whatsappNumber;
  final String? photo;
  final DateTime? dateOfBirth;
  final String? gender;        // "M" ou "F"
  final String? maritalStatus;
  final String? address;
  final String? city;
  final bool isBaptized;
  final DateTime? baptismDate;
  final String status;          // actif, inactif, visiteur, transféré
  final int? siteId;
  final String? siteName;
  
  factory Member.fromJson(Map<String, dynamic> json);
}
```

### Event
```dart
class Event {
  final int id;
  final String title;
  final String? description;
  final DateTime startDate;
  final String? startTime;
  final DateTime? endDate;
  final String? endTime;
  final String? location;
  final String? address;
  final bool allDay;
  final bool isCancelled;
  final String? color;
  final String visibility;     // "PUBLIC" ou "PRIVATE"
  final String? categoryName;
  final bool isRegistered;     // pour l'utilisateur courant
  final int registrationCount;
  
  factory Event.fromJson(Map<String, dynamic> json);
}
```

### WorshipService
```dart
class WorshipService {
  final int id;
  final String serviceType;
  final String? theme;
  final String? bibleText;
  final String? sermonTitle;
  final bool isConfirmed;
  final DateTime date;
  final String? startTime;
  final String? endTime;
  final List<RoleAssignment> roles;
  
  factory WorshipService.fromJson(Map<String, dynamic> json);
}

class RoleAssignment {
  final int id;
  final String roleName;
  final String? assigneeName;
  final String status;         // pending, confirmed, declined
  
  factory RoleAssignment.fromJson(Map<String, dynamic> json);
}
```

### Announcement
```dart
class Announcement {
  final int id;
  final String title;
  final String content;
  final bool isPinned;
  final String priority;       // high, medium, low
  final bool isRead;
  final DateTime createdAt;
  final String? authorName;
  
  factory Announcement.fromJson(Map<String, dynamic> json);
}
```

### OnlineDonation
```dart
class OnlineDonation {
  final int id;
  final double amount;
  final String donationType;   // dime, don, offrande
  final String status;
  final bool isRecurring;
  final String? recurringInterval;
  final DateTime createdAt;
  
  factory OnlineDonation.fromJson(Map<String, dynamic> json);
}
```

---

## Design System & Thème

### Couleurs
- **Primary** : `#3498db` (bleu)
- **Secondary** : `#2ecc71` (vert)
- **Accent** : `#9b59b6` (violet)
- **Danger** : `#e74c3c` (rouge)
- **Warning** : `#f39c12` (orange)
- **Info** : `#00bcd4` (cyan)
- **Background clair** : `#f5f5f5`
- **Background sombre** : `#121212`

### Typographie
- Police : **Poppins** (Google Fonts)
- Titres : Bold 600-700
- Corps : Regular 400
- Labels : Medium 500

### Composants UI
- **Cards** : coins arrondis 12px, elevation 2, padding 16px
- **Boutons** : coins arrondis 8px, height 48px
- **Bottom Navigation Bar** : 5 onglets (Accueil, Annuaire, Événements, Cultes, Profil)
- **AppBar** : fond primary, icône notification avec badge compteur
- Pull-to-refresh sur toutes les listes
- Shimmer loading (skeleton) pendant le chargement
- Animations de transition entre écrans

---

## Fonctionnalités à implémenter (par priorité)

### P0 — Critique
1. **Authentification complète**
   - Écran login avec validation (username + mot de passe)
   - Stockage sécurisé des tokens JWT (access + refresh)
   - Auto-refresh du token via intercepteur Dio (si 401 → refresh → retry)
   - Déconnexion avec blacklist du token
   - Redirection automatique vers login si non authentifié
   - Écran de changement de mot de passe (si `must_change_password == true`, forcer le changement)

2. **Navigation principale**
   - Bottom Navigation Bar avec 5 onglets
   - Splash screen avec logo EEBC et animation
   - Deep linking via GoRouter

3. **Dashboard (Home)**
   - Carte de bienvenue personnalisée ("Bonjour, [Prénom]")
   - Compteur d'annonces non lues
   - Prochains événements (3 max)
   - Prochains cultes (2 max)
   - Raccourcis rapides vers chaque section

### P1 — Important
4. **Annuaire des membres**
   - Liste paginée avec scroll infini
   - Recherche par nom/prénom en temps réel
   - Filtre par site (Cabassou / Macouria)
   - Carte membre avec avatar (photo ou initiales), nom, téléphone
   - Écran détail membre : photo, infos, boutons appeler/WhatsApp/email (via url_launcher)

5. **Événements**
   - Liste avec cards visuelles (date, lieu, couleur catégorie)
   - Filtres : site, plage de dates
   - Écran détail : description complète, lieu, carte, bouton inscription
   - Bouton s'inscrire / se désinscrire
   - Section "Mes inscriptions" dans le profil

6. **Cultes (Worship)**
   - Liste des prochains services
   - Détail : thème, texte biblique, titre sermon, rôles assignés
   - Section "Mes assignations" avec possibilité de confirmer / décliner
   - Historique des cultes passés

7. **Annonces**
   - Liste avec distinction visuelle (épinglées en haut, badge priorité)
   - Détail en page complète (pas en dialog)
   - Marquer comme lue automatiquement à l'ouverture
   - Badge compteur non-lues dans la BottomNav et AppBar

### P2 — Secondaire
8. **Dons / Finance**
   - Formulaire de don : montant, type (dîme/don/offrande), nom, email
   - Option don récurrent (mensuel/hebdomadaire)
   - Intégration Stripe via WebView (l'API retourne une `checkout_url`)
   - Historique des dons
   - Téléchargement des reçus fiscaux (PDF via url_launcher)

9. **Club Biblique**
   - Liste des enfants du parent connecté
   - Historique de présences par enfant
   - Statistiques de présence

10. **Notifications Push**
    - Initialisation Firebase Messaging au démarrage
    - Enregistrement du token FCM auprès du backend
    - Gestion des notifications en foreground (local notification)
    - Navigation vers l'écran concerné au tap sur notification
    - Écran liste des notifications

11. **Profil & Paramètres**
    - Affichage profil complet avec possibilité d'édition
    - Changement de mot de passe
    - Paramètres : thème (clair/sombre/système), langue, préférences de notification
    - Informations de l'app (version, à propos)
    - Déconnexion

---

## Gestion des erreurs

Le backend retourne les erreurs au format :

```json
{
  "success": false,
  "error": {
    "code": "AUTHENTICATION_FAILED",
    "message": "Identifiants invalides",
    "details": {}
  }
}
```

L'app doit :
- Afficher des messages d'erreur user-friendly en français
- Gérer la perte de connexion réseau (afficher un écran offline avec bouton "Réessayer")
- Gérer les timeouts (30 secondes par défaut)
- En cas de 401, tenter un refresh token puis retry automatique
- Logger les erreurs pour le debug

---

## Gestion de l'état (Provider)

Chaque `Provider` doit :
- Exposer un état de chargement (`isLoading`)
- Exposer les données (`items`, `selectedItem`)
- Exposer les erreurs (`errorMessage`)
- Implémenter `fetchAll()`, `fetchById(id)` et les actions spécifiques
- Appeler `notifyListeners()` pour mettre à jour l'UI
- Gérer le cache local (SharedPreferences pour les données non sensibles)

---

## Contraintes techniques

1. **Pas de données mockées** — tout doit venir de l'API
2. **Responsive** — supporter téléphones et tablettes
3. **Accessibilité** — Semantics sur les éléments importants
4. **Performance** — lazy loading des images, pagination scroll infini
5. **Sécurité** — tokens dans flutter_secure_storage, jamais en clair
6. **Offline** — cache des dernières données chargées, indication mode hors-ligne
7. **Internationalisation** — textes en français par défaut, architecture prête pour l'anglais
8. **Code propre** — chaque fichier < 300 lignes, documentation des classes publiques

---

## Livrables attendus

1. Tous les fichiers Dart dans l'architecture définie ci-dessus
2. Configuration Firebase (fichiers android/ios à mettre en place)
3. Assets : placeholder pour le logo EEBC, icônes de navigation
4. Tests unitaires pour les services (api_service, auth_service)
5. Tests widget pour les écrans principaux
6. README.md mis à jour avec instructions de build et configuration

---

*Commence par implémenter les modèles Dart, puis les services (API + Auth avec intercepteur Dio), puis les providers, les widgets réutilisables, et enfin les écrans en commençant par P0 → P1 → P2.*
