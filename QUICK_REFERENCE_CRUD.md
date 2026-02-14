# 🎯 QUICK REFERENCE - CRUD PAR APPLICATION

**Consulter le tableau ci-dessous pour naviguer rapidement l'état CRUD de chaque app**

---

## 📱 TABLEAU INTERACTIF

### ✅ APPLICATIONS 100% COMPLÈTES

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  APPLICATION   │ MODELS │ VIEWS │ FORMS │ URLS │ TEMPLATE │
│  ─────────────────────────────────────────────────────────  │
│  accounts      │   ✅   │  ✅   │  ✅   │  ✅  │    ✅    │
│  members       │   ✅   │  ✅   │  ✅   │  ✅  │    ✅    │
│  events        │   ✅   │  ✅   │  ✅   │  ✅  │    ✅    │
│  campaigns     │   ✅   │  ✅   │  ✅   │  ✅  │    ✅    │
│  transport     │   ✅   │  ✅   │  ✅   │  ✅  │    ✅    │
│  bibleclub     │   ✅   │  ✅   │  ✅   │  ✅  │    ✅    │
│  groups        │   ✅   │  ✅   │  ✅   │  ✅  │    ✅    │
│  worship       │   ✅   │  ✅   │  ✅   │  ✅  │    ✅    │
│  departments   │   ✅   │  ✅   │  ✅   │  ✅  │    ✅    │
│  inventory     │   ✅   │  ✅   │  ✅   │  ✅  │    ✅    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 🟡 APPLICATIONS PARTIELLEMENT COMPLÈTES

```
┌─────────────────────────────────────────────────────────────┐
│  APPLICATION   │ MODELS │ VIEWS │ FORMS │ URLS │ TEMPLATE │
│  ─────────────────────────────────────────────────────────  │
│  finance       │   ✅   │  🟡   │  ✅   │  ✅  │    ✅    │
│  communication │   ✅   │  ✅   │  ❌   │  ✅  │    ✅    │
│  imports       │   ✅   │  🟡   │  ✅   │  ✅  │    ✅    │
│  public        │   🟡   │  ✅   │  ✅   │  ✅  │    ✅    │
│  core          │   ✅   │  🟡   │  🟡   │  🟡  │    ✅    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### ❌ APPLICATIONS NON-CRUD

```
┌─────────────────────────────────────────────────────────────┐
│  APPLICATION   │ TYPE / NOTES                               │
│  ─────────────────────────────────────────────────────────  │
│  dashboard     │ Hub de synthèse (lecture seule)           │
│  api           │ API REST (Serializers, pas de formulaires)│
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📍 GUIDE DE NAVIGATION

### Pour CRÉER une nouvelle ressource:

```
1. Aller dans: /[app]/create/
   Exemples:
   - /members/create/           → Créer un membre
   - /events/create/            → Créer un événement
   - /transport/drivers/create/ → Créer un chauffeur
   - /finance/transactions/create/ → Créer une transaction

2. Remplir le formulaire
   → Vérifier que apps/[app]/forms.py existe
   → Vérifier les validations

3. Soumettre → Redirection vers détail ou liste
```

### Pour VOIR/LIRE une ressource:

```
1. Aller dans le lecteur de ressource
   /[app]/
      → Liste tous
   /[app]/<id>/
      → Détail spécifique

   Exemples:
   - /members/                  → Tous les membres
   - /members/123/              → Membre #123
   - /events/calendar/          → Vue calendrier
   - /finance/dashboard/        → Tableau de bord
```

### Pour METTRE À JOUR:

```
1. Aller sur le détail: /[app]/<id>/
2. Cliquer "Éditer"
3. Aller vers: /[app]/<id>/edit/
4. Modifier les champs
5. Soumettre

⚠️  ATTENTION pour finance:
   - Les transactions sont immuables
   - Soft-delete à implémenter (voir ACTION_PLAN_DETAILLE.md)
```

### Pour SUPPRIMER:

```
1. Aller sur le détail: /[app]/<id>/
2. Cliquer "Supprimer"
3. Confirmer

⚠️  ATTENTION:
   - finance: soft-delete requis
   - imports: non applicable
```

---

## 📊 RÉSUMÉ PAR APPLICATION

### 1️⃣ ACCOUNTS (Utilisateurs)
**URL Base**: `/users/`  
**Status**: ✅ 100% COMPLET  
**CRUD**: ✅✅✅✅  
**Fichiers Clés**:
- `apps/accounts/models.py` - User model
- `apps/accounts/forms.py` - UserCreationByTeamForm
- `apps/accounts/views.py` - Toutes vues

---

### 2️⃣ MEMBERS (Membres)
**URL Base**: `/members/`  
**Status**: ✅ 100% COMPLET  
**CRUD**: ✅✅✅✅  
**Fichiers Clés**:
- `apps/members/models.py` - Member, LifeEvent, Family
- `apps/members/forms.py` - MemberForm
- `apps/members/views.py` - Toutes vues CRUD + CRM

**Opérations Spéciales**:
- `/members/families/` - Gestion familiale
- `/members/life-events/` - Événements de vie
- `/members/visits/` - Visites pastorales
- `/members/kanban/` - Tableau Kanban

---

### 3️⃣ EVENTS (Événements)
**URL Base**: `/events/`  
**Status**: ✅ 100% COMPLET  
**CRUD**: ✅✅✅✅  
**Fichiers Clés**:
- `apps/events/models.py` - Event, Category
- `apps/events/forms.py` - EventForm
- `apps/events/views.py` - Toutes vues

**Opérations Spéciales**:
- `/events/calendar/` - FullCalendar
- `/events/<id>/duplicate/` - Duplication
- `/events/categories/` - Gestion catégories

---

### 4️⃣ FINANCE (Finances)
**URL Base**: `/finance/`  
**Status**: 🟡 85% COMPLET  
**CRUD**: ✅✅🟡🟡  
**Fichiers Clés**:
- `apps/finance/models.py` - Transaction, Budget
- `apps/finance/forms.py` - TransactionForm
- `apps/finance/views.py` - Dashboard, transactions

**⚠️ PROBLÈMES**:
- ❌ DELETE sans traçabilité
- 🟡 UPDATE limité
- ℹ️ À corriger: Soft-delete (voir ACTION_PLAN_DETAILLE.md)

---

### 5️⃣ CAMPAIGNS (Collectes)
**URL Base**: `/campaigns/`  
**Status**: ✅ 100% COMPLET  
**CRUD**: ✅✅✅✅  
**Fichiers Clés**:
- `apps/campaigns/models.py` - Campaign, Donation
- `apps/campaigns/forms.py` - CampaignForm
- `apps/campaigns/views.py` - Toutes vues

---

### 6️⃣ TRANSPORT (Transport)
**URL Base**: `/transport/`  
**Status**: ✅ 100% COMPLET  
**CRUD**: ✅✅✅✅  
**Fichiers Clés**:
- `apps/transport/models.py` - Driver, Request
- `apps/transport/forms.py` - DriverProfileForm
- `apps/transport/views.py` - Toutes vues

---

### 7️⃣ IMPORTS (Import/Export)
**URL Base**: `/imports/`  
**Status**: 🟡 60% COMPLET  
**CRUD**: 🟡✅❌✅  
**Fichiers Clés**:
- `apps/imports/models.py` - ImportLog
- `apps/imports/forms.py` - ImportForm
- `apps/imports/views.py` - Import/export vues
- `apps/imports/services.py` - ExcelImportService

**⚠️ PROBLÈMES**:
- 🟡 CREATE: Upload seul (pas d'édition)
- ❌ UPDATE: Non applicable (logs immuables)
- 🟡 Validation basique (à améliorer, voir ACTION_PLAN_DETAILLE.md)

---

### 8️⃣ COMMUNICATION (Communication)
**URL Base**: `/communication/`  
**Status**: 🟡 75% COMPLET  
**CRUD**: ✅✅🟡✅  
**Fichiers Clés**:
- `apps/communication/models.py` - Notification, Announcement
- `apps/communication/forms.py` - ❌ **MANQUANT!**
- `apps/communication/views.py` - Vues sans formulaires

**🔴 PROBLÈMES CRITIQUES**:
- ❌ **forms.py N'EXISTE PAS** (créer à J1, voir ACTION_PLAN_DETAILLE.md)
- 🟡 Vues sans validation de formulaire
- 🟡 Pas de templates pour création/édition

---

### 9️⃣ BIBLECLUB (Club biblique)
**URL Base**: `/bibleclub/`  
**Status**: ✅ 100% COMPLET  
**CRUD**: ✅✅✅✅  
**Fichiers Clés**:
- `apps/bibleclub/models.py` - Class, Child, Session
- `apps/bibleclub/forms.py` - ChildForm, etc.
- `apps/bibleclub/views.py` - Toutes vues (982 lignes!)

**Opérations Spéciales**:
- `/bibleclub/sessions/<id>/attendance/` - Appel
- `/bibleclub/sessions/<id>/transport/` - Check-in transport
- Statistiques de présence

---

### 🔟 GROUPS (Groupes)
**URL Base**: `/groups/`  
**Status**: ✅ 100% COMPLET  
**CRUD**: ✅✅✅✅  
**Fichiers Clés**:
- `apps/groups/models.py` - Group, Meeting
- `apps/groups/forms.py` - GroupForm
- `apps/groups/views.py` - Toutes vues

---

### 1️⃣1️⃣ WORSHIP (Cultes)
**URL Base**: `/worship/`  
**Status**: ✅ 100% COMPLET  
**CRUD**: ✅✅✅✅  
**Fichiers Clés**:
- `apps/worship/models.py` - Service (1097 lignes!)
- `apps/worship/forms.py` - ServiceForm
- `apps/worship/views.py` - Toutes vues (831 lignes!)

**Opérations Spéciales**:
- `/worship/services/` - Ancien système
- `/worship/planning/` - Planification mensuelle
- `/worship/culte/<id>/` - Vue détail planifiée
- Assignation de rôles avec confirmation

---

### 1️⃣2️⃣ DEPARTMENTS (Départements)
**URL Base**: `/departments/`  
**Status**: ✅ 100% COMPLET  
**CRUD**: ✅✅✅✅  
**Fichiers Clés**:
- `apps/departments/models.py` - Department
- `apps/departments/forms.py` - DepartmentForm
- `apps/departments/views.py` - Toutes vues

---

### 1️⃣3️⃣ INVENTORY (Inventaire)
**URL Base**: `/inventory/`  
**Status**: ✅ 100% COMPLET  
**CRUD**: ✅✅✅✅  
**Fichiers Clés**:
- `apps/inventory/models.py` - Equipment, Category
- `apps/inventory/forms.py` - EquipmentForm
- `apps/inventory/views.py` - Toutes vues

**Opérations Spéciales**:
- `/inventory/categories/` - Gestion catégories
- Filtres par état (maintenance, cassé...)

---

### 1️⃣4️⃣ PUBLIC (Site vitrine)
**URL Base**: `/`  
**Status**: 🟡 90% COMPLET  
**CRUD**: ✅✅✅✅  
**Fichiers Clés**:
- `apps/public/models.py` - Vide (modèles dans core)
- `apps/public/forms.py` - NewsArticleForm, etc.
- `apps/public/views.py` - Views basées sur CBV

**Modèles dans**: `apps/core/models.py`

**Opérations CMS**:
- Actualités
- Pages statiques
- Témoignages
- Horaires de culte

---

### 1️⃣5️⃣ CORE (Fondations)
**URL Base**: N/A  
**Status**: 🟡 60% COMPLET  
**CRUD**: 🟡✅🟡🟡  
**Fichiers Clés**:
- `apps/core/models.py` - Site, Settings (1467 lignes!)
- `apps/core/forms.py` - Vides
- `apps/core/views.py` - Quelques vues

**⚠️ PROBLÈMES**:
- 🟡 Pas d'UI pour configuration Site
- 🟡 Settings non éditables par UI
- 🟡 Hyper-volumineux (1467 lignes)

---

### 1️⃣6️⃣ DASHBOARD (Tableau de bord)
**URL Base**: `/dashboard/`  
**Status**: ⚪ N/A  
**Type**: Synthèse (pas CRUD)  
**Fichiers Clés**:
- `apps/dashboard/views.py` - Agrégation de stats
- `apps/dashboard/urls.py` - 2 routes seulement

**Note**: N'a pas besoin de CRUD

---

### 1️⃣7️⃣ API (API REST)
**URL Base**: `/api/`  
**Status**: ✅ 100% COMPLET  
**Type**: API REST (pas CRUD web)  
**Fichiers Clés**:
- `apps/api/views.py` - ViewSets DRF
- `apps/api/serializers.py` - Serializers
- `apps/api/urls.py` - Router

**Note**: Utilise DRF Serializers, pas Django Forms

---

## 🚀 QUICK FIXES

### Communication (❌ PRIORITÉ HAUTE)
```bash
1. Créer: apps/communication/forms.py
   - AnnouncementForm
   - NotificationForm
2. Test: python manage.py test apps.communication.tests.AnnouncementFormTest
3. Deploy: git add && git commit
```

### Finance (🟡 PRIORITÉ HAUTE)
```bash
1. Modifier: apps/finance/models.py
   - Ajouter is_deleted, deleted_at, deleted_by
2. Créer migration: python manage.py makemigrations finance
3. Test soft-delete: python manage.py test apps.finance.tests.SoftDeleteTest
```

### Imports (🟡 PRIORITÉ MOYENNE)
```bash
1. Améliorer: apps/imports/services.py
   - ImportValidator class
2. Créer: apps/imports/views.py - import_preview()
3. Tester: python manage.py test apps.imports
```

### Core (🟡 PRIORITÉ MOYENNE)
```bash
1. Créer: apps/core/views.py - AdminSettingsView
2. Ajouter routes: apps/core/urls.py
3. Créer templates: templates/core/settings_form.html
```

---

## 📞 SUPPORT

**Questions?**
1. Consultez d'abord: `CRUD_STATE_ANALYSIS.md`
2. Puis: `ACTION_PLAN_DETAILLE.md`
3. Enfin: Ce fichier `QUICK_REFERENCE.md`

**Issues bloquants?**
- Communication: `forms.py` MANQUANT
- Finance: DELETE sans traçabilité
- Imports: Validation basique
- Core: Pas d'UI settings

---

**Dernière mise à jour**: 8 février 2026  
**Couverture CRUD**: 82% (cible J7: 92%)
