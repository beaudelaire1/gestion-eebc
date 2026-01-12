# API REST - EEBC Gestion

Documentation complète de l'API REST pour l'application mobile EEBC.

**Base URL:** `https://eglise-ebc.org/api/v1/`

---

## Authentification

Toutes les requêtes (sauf login) nécessitent un token JWT dans le header:
```
Authorization: Bearer <access_token>
```

### POST /auth/login/

Authentification et obtention des tokens JWT.

**Request Body:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "user": {
      "id": 1,
      "username": "john.doe",
      "email": "john@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "role": "member",
      "phone": "+594694123456",
      "photo": "/media/users/photos/john.jpg",
      "member_id": 42
    },
    "must_change_password": false
  }
}
```

**Response (401) - Compte verrouillé:**
```json
{
  "success": false,
  "error": {
    "code": 401,
    "message": "Compte verrouillé. Réessayez dans 15 minutes.",
    "locked": true,
    "remaining_minutes": 15
  }
}
```

### POST /auth/refresh/

Rafraîchir le token d'accès.

**Request Body:**
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Response (200):**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### POST /auth/logout/

Déconnexion et invalidation du token.

**Request Body:**
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Déconnexion réussie"
}
```

### PUT /auth/password/

Changer le mot de passe.

**Request Body:**
```json
{
  "old_password": "string",
  "new_password": "string",
  "confirm_password": "string"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Mot de passe modifié avec succès",
  "data": {
    "access": "new_access_token",
    "refresh": "new_refresh_token"
  }
}
```

---

## Profil Utilisateur

### GET /profile/

Obtenir le profil de l'utilisateur connecté.

**Response (200):**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "username": "john.doe",
    "email": "john@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "role": "member",
    "phone": "+594694123456",
    "photo": "/media/users/photos/john.jpg",
    "member": {
      "id": 42,
      "member_id": "EEBC-CAB-0042",
      "first_name": "John",
      "last_name": "Doe",
      "email": "john@example.com",
      "phone": "+594694123456",
      "is_baptized": true,
      "status": "actif",
      "site": {
        "id": 1,
        "code": "CAB",
        "name": "Cabassou"
      }
    }
  }
}
```

### PUT /profile/

Mettre à jour le profil.

**Request Body:**
```json
{
  "email": "newemail@example.com",
  "phone": "+594694999999",
  "first_name": "John",
  "last_name": "Doe"
}
```

---

## Membres (Annuaire)

### GET /members/

Liste des membres actifs.

**Query Parameters:**
- `search`: Recherche par nom, email ou téléphone
- `site`: Filtrer par ID de site
- `page`: Numéro de page
- `ordering`: Tri (`last_name`, `first_name`, `-last_name`, `-first_name`)

**Response (200):**
```json
{
  "count": 150,
  "next": "/api/v1/members/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "member_id": "EEBC-CAB-0001",
      "first_name": "Jean",
      "last_name": "Dupont",
      "email": "jean@example.com",
      "phone": "+594694123456",
      "photo": "/media/members/photos/jean.jpg",
      "status": "actif",
      "site": {
        "id": 1,
        "code": "CAB",
        "name": "Cabassou"
      }
    }
  ]
}
```

### GET /members/{id}/

Détail d'un membre.

**Response (200):**
```json
{
  "id": 1,
  "member_id": "EEBC-CAB-0001",
  "first_name": "Jean",
  "last_name": "Dupont",
  "full_name": "Jean Dupont",
  "email": "jean@example.com",
  "phone": "+594694123456",
  "whatsapp_number": "+594694123456",
  "photo": "/media/members/photos/jean.jpg",
  "date_of_birth": "1985-03-15",
  "age": 40,
  "gender": "M",
  "marital_status": "marie",
  "address": "123 Rue Example",
  "city": "Cayenne",
  "postal_code": "97300",
  "is_baptized": true,
  "baptism_date": "2010-06-20",
  "status": "actif",
  "family": {
    "id": 5,
    "name": "Famille Dupont",
    "members": [
      {"id": 2, "first_name": "Marie", "last_name": "Dupont", "relationship": "SPOUSE"}
    ]
  },
  "site": {
    "id": 1,
    "code": "CAB",
    "name": "Cabassou"
  }
}
```

---

## Événements

### GET /events/

Liste des événements à venir.

**Query Parameters:**
- `search`: Recherche par titre ou description
- `start_date`: Date de début (YYYY-MM-DD)
- `end_date`: Date de fin (YYYY-MM-DD)
- `site`: Filtrer par ID de site
- `page`: Numéro de page

**Response (200):**
```json
{
  "count": 25,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "title": "Culte dominical",
      "description": "Culte du dimanche matin",
      "start_date": "2026-01-12",
      "start_time": "09:30:00",
      "end_date": null,
      "end_time": "12:00:00",
      "location": "Temple de Cabassou",
      "all_day": false,
      "is_cancelled": false,
      "color": "#0d6efd",
      "site": {"id": 1, "code": "CAB", "name": "Cabassou"},
      "is_user_registered": false,
      "current_participants": 45
    }
  ]
}
```

### GET /events/{id}/

Détail d'un événement.

### GET /events/my_registrations/

Liste des événements auxquels l'utilisateur est inscrit.

### POST /events/{id}/register/

S'inscrire à un événement.

**Request Body (optionnel):**
```json
{
  "notes": "Je viendrai avec 2 personnes"
}
```

**Response (201):**
```json
{
  "success": true,
  "message": "Inscription réussie",
  "data": {
    "id": 123,
    "event": 1,
    "user": 42,
    "registered_at": "2026-01-08T10:30:00Z",
    "notes": "Je viendrai avec 2 personnes"
  }
}
```

### DELETE /events/{id}/register/

Se désinscrire d'un événement.

---

## Cultes (Worship)

### GET /worship/services/

Liste des services de culte.

**Query Parameters:**
- `site`: Filtrer par ID de site

**Response (200):**
```json
{
  "count": 10,
  "results": [
    {
      "id": 1,
      "date": "2026-01-12",
      "start_time": "09:30:00",
      "service_type": "culte_dominical",
      "theme": "La foi qui déplace les montagnes",
      "is_confirmed": true,
      "site": {"id": 1, "code": "CAB", "name": "Cabassou"},
      "user_assignments": [
        {
          "id": 5,
          "role": "choriste",
          "role_display": "Choriste",
          "member": {"id": 42, "first_name": "John", "last_name": "Doe"},
          "status": "confirme",
          "is_current_user": true
        }
      ]
    }
  ]
}
```

### GET /worship/services/{id}/

Détail d'un service avec tous les rôles assignés.

### GET /worship/services/my_assignments/

Services où l'utilisateur a des assignations.

### GET /worship/services/history/

Historique des services (3 derniers mois).

### POST /worship/confirm/

Confirmer ou décliner une assignation.

**Request Body:**
```json
{
  "assignment_id": 123,
  "action": "confirm"
}
```

ou pour décliner:
```json
{
  "assignment_id": 123,
  "action": "decline",
  "decline_reason": "Je serai absent ce jour-là"
}
```

---

## Annonces

### GET /announcements/

Liste des annonces actives (épinglées en premier).

**Query Parameters:**
- `search`: Recherche par titre ou contenu

**Response (200):**
```json
{
  "count": 5,
  "results": [
    {
      "id": 1,
      "title": "Assemblée générale",
      "excerpt": "L'assemblée générale annuelle aura lieu...",
      "is_pinned": true,
      "priority": "high",
      "start_date": "2026-01-05T00:00:00Z",
      "author": "Pasteur Martin",
      "is_read": false
    }
  ]
}
```

### GET /announcements/{id}/

Détail d'une annonce.

### POST /announcements/{id}/mark_read/

Marquer une annonce comme lue.

---

## Dons

### GET /donations/

Historique des dons de l'utilisateur.

**Response (200):**
```json
{
  "count": 12,
  "results": [
    {
      "id": 1,
      "amount": "50.00",
      "donation_type": "dime",
      "donation_type_display": "Dîme",
      "status": "completed",
      "status_display": "Complété",
      "is_recurring": false,
      "created_at": "2026-01-01T10:00:00Z"
    }
  ]
}
```

### POST /donations/

Créer une session de paiement Stripe.

**Request Body:**
```json
{
  "amount": 50.00,
  "donation_type": "dime",
  "is_recurring": false
}
```

Pour un don récurrent:
```json
{
  "amount": 100.00,
  "donation_type": "don",
  "is_recurring": true,
  "recurring_interval": "month"
}
```

**Response (201):**
```json
{
  "success": true,
  "message": "Session de paiement créée",
  "data": {
    "checkout_url": "https://checkout.stripe.com/...",
    "session_id": "cs_test_..."
  }
}
```

### GET /donations/receipts/

Liste des reçus fiscaux disponibles.

**Response (200):**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "receipt_number": "RF-2025-0001",
      "fiscal_year": 2025,
      "total_amount": "1200.00",
      "status": "issued",
      "issue_date": "2026-01-15",
      "pdf_file": "/media/finance/tax_receipts/2025/RF-2025-0001.pdf"
    }
  ]
}
```

---

## Notifications Push

### POST /notifications/register/

Enregistrer un token d'appareil pour les notifications push.

**Request Body:**
```json
{
  "token": "ExponentPushToken[xxxxxx]",
  "platform": "ios",
  "device_name": "iPhone de John"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Appareil enregistré"
}
```

### DELETE /notifications/register/

Désenregistrer un appareil.

**Request Body:**
```json
{
  "token": "ExponentPushToken[xxxxxx]"
}
```

---

## Codes d'erreur

| Code | Description |
|------|-------------|
| 400 | Requête invalide |
| 401 | Non authentifié |
| 403 | Accès refusé |
| 404 | Ressource non trouvée |
| 429 | Trop de requêtes |
| 500 | Erreur serveur |

## Format des réponses d'erreur

```json
{
  "success": false,
  "error": {
    "code": 400,
    "message": "Requête invalide",
    "details": {
      "field_name": ["Message d'erreur"]
    }
  }
}
```
