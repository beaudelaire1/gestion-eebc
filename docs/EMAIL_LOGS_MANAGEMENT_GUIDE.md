<div align="center">

# 📧 Guide Complet - Gestion des Logs Emails EEBC

## Système de Gestion des Logs Emails - Production v1.0

[![Status](https://img.shields.io/badge/Status-Production%20Ready-green?style=flat-square)]()
[![Version](https://img.shields.io/badge/Version-1.0-blue?style=flat-square)]()
[![Updated](https://img.shields.io/badge/Updated-Feb%202026-informational?style=flat-square)]()

</div>

---

## 📚 Table des Matières Rapide

| Section | Description | Accès rapide |
|---------|-------------|-------------|
| **Interface Web** | Gestion visuelle avec cases à cocher | [Voir →](#interface-web) |
| **Commande CLI** | Gestion en ligne de commande | [Voir →](#commande-cli) |
| **Cas d'Usage** | Exemples pratiques du quotidien | [Voir →](#cas-dusage-pratiques) |
| **Dépannage** | Résolution des problèmes | [Voir →](#dépannage) |
| **FAQ** | Questions fréquentes | [Voir →](#faq) |

---

## 🎯 Vue d'Ensemble

<div style="background:#e8f4f8; padding:20px; border-radius:8px; border-left:5px solid #0078d4;">

Le système de gestion des logs emails EEBC offre **deux méthodes complémentaires** pour supprimer et auditer les logs emails:

### 🌐 Interface Web
Pour les utilisateurs qui préfèrent une **gestion visuelle**:
- ✅ Filtrage et recherche intuitifs
- ✅ Cases à cocher pour sélection
- ✅ Pagination de 50 logs par page
- ✅ Statistiques en temps réel
- ✅ Détails complets des logs en modals
- ✅ Confirmation avant suppression

### 🖥️ Commande CLI
Pour les administrateurs et **automatisation**:
- ✅ Sélection flexible (numéros, ranges)
- ✅ Options avancées (filtres, dry-run)
- ✅ Commits Git automatiques
- ✅ Idéale pour scripts/cron
- ✅ Mode simulation disponible
- ✅ Audit trail complet

</div>

---

# 🌐 Interface Web

## Accès et Connexion

<div style="background:#f5f5f5; padding:15px; border-radius:6px;">

### URL d'Accès
```
https://votresite.com/communication/logs/email/manage/
```

### Prérequis
- ✅ Connexion avec compte administrateur
- ✅ Rôle `admin` activé
- ✅ Navigateur moderne (Chrome, Firefox, Safari, Edge)

### 🔐 Sécurité
- Authentification requise
- Vérification du rôle admin
- Confirmation avant suppression
- Audit trail complète

</div>

---

## 📊 Tableau de Bord Statistique

<div style="background:#fff9e6; padding:20px; border-radius:8px; border-left:4px solid #ffc107;">

### Vue d'Ensemble Rapide

La première section affiche **4 cartes d'information** mises à jour en temps réel:

#### Cartes Statistiques

| Carte | Icône | Couleur | Affiche |
|-------|-------|---------|---------|
| **Total** | 📬 | Bleu | Nombre total de logs en base |
| **Sent** | ✅ | Vert | Emails envoyés avec succès |
| **Failed** | ❌ | Rouge | Emails en erreur |
| **Pending** | ⏳ | Orange | Emails en attente d'envoi |

### Exemple d'Affichage
```
┌─────────────────────────────────────────────────────────┐
│              📊 TABLEAU DE BORD STATISTIQUE              │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ 📬 TOTAL     │  │ ✅ SENT      │  │ ❌ FAILED    │ │
│  │ LOGS         │  │ LOGS         │  │ LOGS         │ │
│  │              │  │              │  │              │ │
│  │   1,254      │  │   1,189      │  │      45      │ │
│  │              │  │              │  │              │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│                                                         │
│  ┌──────────────┐                                       │
│  │ ⏳ PENDING   │                                       │
│  │ LOGS         │                                       │
│  │              │                                       │
│  │      20      │                                       │
│  │              │                                       │
│  └──────────────┘                                       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**💡 Conseil**: Ces statistiques se mettent à jour automatiquement. Rafraîchissez la page pour voir les dernières données.

</div>

---

## 🔍 Panneau de Recherche et Filtrage

<div style="background:#f0f7ff; padding:20px; border-radius:8px; border-left:4px solid #0056b3;">

### Recherche Textuelle

```
┌─────────────────────────────────────────────────────┐
│ 🔎 Rechercher par email, sujet ou destinataire...   │
│                                                     │
│ [________________________________] [Reset]         │
└─────────────────────────────────────────────────────┘
```

**Recherche dans:**
- 📧 **Email du destinataire** (john@company.com)
- 📝 **Sujet du message** (Welcome, Reset password, Newsletter)
- 👤 **Nom du destinataire** (John Doe, Marie Martin)

**Exemples de Recherches:**
```
"john@company.com"          → Tous les logs pour cet email
"reset password"            → Tous les logs avec ce sujet
"marie"                     → Tous les logs pour Jean Marie
```

### Filtre par Statut

```
┌──────────────────────────────┐
│ Filtrer par Statut    ▼      │
├──────────────────────────────┤
│ ✅ Tous les statuts          │
│ ✓  Sent (Envoyés)            │
│ ✗  Failed (Échoués)          │
│ ⏳ Pending (En attente)      │
│ 🔙 Bounced (Rebondis)        │
│ 👁️  Opened (Ouverts)        │
│ 🔗 Clicked (Cliqués)         │
└──────────────────────────────┘
```

### 🎨 Guide Couleur des Statuts

| Statut | Badge | Signification | Action |
|--------|-------|---------------|--------|
| **SENT** | ✅ Vert | Email envoyé avec succès | Archivable |
| **FAILED** | ❌ Rouge | Erreur lors de l'envoi | À investiguer |
| **PENDING** | ⏳ Orange | En attente de traitement | à surveiller |
| **BOUNCED** | 🔙 Rose | Email rejeté | À nettoyer |
| **OPENED** | 👁️  Bleu | Destinataire a ouvert | Engagement confirmé |
| **CLICKED** | 🔗 Violet | Lien cliqué dans email | Conversion |

</div>

---

## 📋 Tableau Principal des Logs

<div style="background:#fff3cd; padding:20px; border-radius:8px; border-left:4px solid #ff9800;">

### Structure du Tableau

```
┌──────────────────────────────────────────────────────────────────┐
│  Sélection | Email      | Sujet      | Statut | Date/Heure | .. │
├──────────────────────────────────────────────────────────────────┤
│     ☑      │ u1@ex.com  │ Welcome    │ ✅SENT │ 17/02 14:32│ View│
│     ☑      │ u2@ex.com  │ Reset pwd  │ ❌FAIL │ 17/02 10:15│ View│
│     ☑      │ u3@ex.com  │ Newsletter │ ⏳PEND │ 17/02 09:45│ View│
│     ☐      │ u4@ex.com  │ Confirm    │ ✅SENT │ 16/02 22:10│ View│
│     ☐      │ u5@ex.com  │ Invoice    │ 👁️OPEN│ 16/02 18:45│ View│
│            │            │            │        │             │    │
├────────────┴────────────┴────────────┴────────┴─────────────┴────┤
│ ☑ Select All          🗑️ Delete (3 sélectionnés)  Montrant 1-50 │
└────────────────────────────────────────────────────────────────────┘
```

### Colonnes Expliquées

| Colonne | Types | Actions Disponibles |
|---------|-------|-------------------|
| **☑** | Checkbox | Cocher/décocher individuellement |
| **Email** | Texte | Copie au survol |
| **Sujet** | Texte | Affiche tronqué à 50 caractères |
| **Statut** | Badge | Filtrable par couleur |
| **Date** | DateTime | Format: DD/MM/YYYY HH:MM |
| **Actions** | Boutons | 👁️ Voir | 🗑️ Supprimer |

### Comportement du Tableau

- **Hover (survol)**: La ligne s'illumine légèrement
- **Tri**: Cliquez sur l'en-tête pour trier (si activé)
- **Pagination**: 50 logs par page (défilement bas pour navigation)
- **Recherche**: Filtre dynamique lors de la saisie

</div>

---

## ☑️ Sélection et Suppression

<div style="background:#f0f0f0; padding:20px; border-radius:8px; border-left:4px solid #666;">

### Sélection Unitaire

**Étapes:**
```
1. Cochez la case ☑️ à côté du log à supprimer
   ↓
2. Le bouton [🗑️ Delete] s'active automatiquement
   ↓
3. Le message affiche "1 selected"
   ↓
4. Cliquez le bouton Delete
   ↓
5. Confirmez dans la modal "Êtes-vous sûr?"
   ↓
6. Le log est supprimé et la page se rafraîchit
```

### Sélection Groupée

**Étapes:**
```
1. Cochez la case ☑️ "Select All" dans l'en-tête
   ↓
2. TOUTES les cases de la page se cochent
   ↓
3. Le message affiche "50 selected" (tous les logs de la page)
   ↓
4. Cliquez [🗑️ Delete]
   ↓
5. Modal affiche la liste des logs à supprimer
   ↓
6. Confirmez: "Êtes-vous sûr? Cette action est IRRÉVERSIBLE"
   ↓
7. Tous les logs sélectionnés sont supprimés
```

### Modal de Confirmation

```
┌─────────────────────────────────────────┐
│ ⚠️ CONFIRMATION DE SUPPRESSION          │
├─────────────────────────────────────────┤
│                                         │
│ Vous avez sélectionné 3 logs:          │
│                                         │
│ 1. user1@example.com - Welcome (SENT)  │
│ 2. user2@example.com - Reset pwd (FAIL)│
│ 3. user3@example.com - Newsletter (...)│
│                                         │
│ ⚠️ Cette action est IRRÉVERSIBLE        │
│                                         │
│ Êtes-vous sûr de continuer?             │
│                                         │
│ [❌ Annuler]     [✅ Confirmer Suppression] │
│                                         │
└─────────────────────────────────────────┘
```

### États du Bouton Delete

| État | Couleur | Raison |
|------|---------|--------|
| **Activé** | 🟢 Vert | 1+ logs sélectionnés |
| **Désactivé** | 🔘 Gris | 0 logs sélectionnés |
| **Loading** | 🔄 Jaune | Suppression en cours |
| **Succès** | ✅ Vert | Suppression réussie |

**💡 Conseil**: Utilisez "Select All" seulement si vous êtes sûr. Le bouton vous demande TOUJOURS confirmation.

</div>

---

## 🔍 Modal de Détails des Logs

<div style="background:#e8f5e9; padding:20px; border-radius:8px; border-left:4px solid #4caf50;">

### Affichage des Détails

Cliquez sur le bouton **👁️ View** pour voir tous les détails d'un log:

```
┌──────────────────────────────────────────────┐
│ 👁️ DÉTAILS DU LOG #12345                    │
├──────────────────────────────────────────────┤
│                                              │
│ Email Destinataire                           │
│ ├─ À: john.doe@example.com                  │
│ └─ Nom: John Doe                             │
│                                              │
│ Sujet du Message                             │
│ └─ Welcome to Our Platform!                 │
│                                              │
│ Contenu de l'Email                           │
│ ├─ Dear John,                                │
│ ├─ Welcome to EEBC Platform...              │
│ ├─ [Long contenu du message...]             │
│ └─ Best regards, The Team                    │
│                                              │
│ Métadonnées                                  │
│ ├─ Statut: ✅ SENT                          │
│ ├─ Créé: 17/02/2026 14:32:15                │
│ ├─ Envoyé: 17/02/2026 14:32:18              │
│ └─ ID du Log: 12345                          │
│                                              │
│ Messages d'Erreur (si applicable)            │
│ └─ Aucune erreur                             │
│                                              │
│              [Fermer]                        │
│                                              │
└──────────────────────────────────────────────┘
```

### Informations Disponibles

- 📧 **Email & Destinataire**: Adresse complète et nom
- 📝 **Sujet**: Titre du message
- 📄 **Corps**: Contenu complet du message
- 🕐 **Timestamps**: Création, envoi, réception
- ⚠️ **Erreurs**: Messages d'erreur détaillés
- 🔍 **ID**: Identifiant technique du log

</div>

---

## 📄 Pagination

<div style="background:#f8f8f8; padding:20px; border-radius:8px; border-left:4px solid #999;">

### Contrôles de Navigation

```
Montrant 1-50 de 1254 logs

« Première  ◄ Précédent  1  [2]  3  4  5 ... 25  Suivant ►  Dernière »

Aller à la page: [___]  [Go]   Total pages: 25
```

### Navigation Rapide

| Bouton | Action |
|--------|--------|
| **« Première** | Aller à la page 1 |
| **◄ Précédent** | Page précédente |
| **[Numéro]** | Aller à cette page |
| **Suivant ►** | Page suivante |
| **Dernière »** | Aller à la dernière page |

### Affichage par Page

L'interface affiche **50 logs par page**. 

**Pour briser les records:**
- Page 1: 1-50
- Page 2: 51-100
- Page 3: 101-150
- ...
- Page 25: 1201-1250

**💡 Conseil**: Utilisez la recherche pour filtrer rapidement plutôt que de naviguer page par page.

</div>

---

# 🖥️ Commande CLI

## Guide d'Installation et Utilisation

<div style="background:#f5f5f5; padding:20px; border-radius:8px; border-left:4px solid #555;">

### Accès à la Commande

La commande est automatiquement disponible dans Django:

```bash
python manage.py delete_email_logs_interactive
```

### Prérequis

- ✅ Accès SSH/Terminal au serveur
- ✅ Environnement Python configuré
- ✅ Permissions pour exécuter Django

</div>

---

## 🎯 Options Disponibles

<div style="background:#f0f0f0; padding:20px; border-radius:8px;">

### Option 1: Filtrer par Statut

```bash
python manage.py delete_email_logs_interactive --status=failed
```

**Valeurs acceptées:**
- `all` - Tous les statuts (par défaut)
- `pending` - Logs en attente
- `sent` - Logs envoyés
- `failed` - Logs échoués ❌
- `bounced` - Logs rebondis 🔙
- `opened` - Logs ouverts 👁️
- `clicked` - Logs cliqués 🔗

---

### Option 2: Supprimer les Logs Anciens

```bash
python manage.py delete_email_logs_interactive --older-than-days=30
```

Supprime **uniquement** les logs créés il y a plus de 30 jours.

**Exemples:**
```bash
# Supprimer les logs de plus de 60 jours
python manage.py delete_email_logs_interactive --older-than-days=60

# Supprimer les logs de plus d'un an
python manage.py delete_email_logs_interactive --older-than-days=365
```

---

### Option 3: Mode Test (Dry-Run)

```bash
python manage.py delete_email_logs_interactive --dry-run
```

**Affiche ce qui SERAIT supprimé SANS effectuer la suppression.**

Parfait pour:
- Tester avant de réellement supprimer
- Vérifier les filtres
- Voir le nombre de logs affected

---

### Option 4: Éviter le Commit Git

```bash
python manage.py delete_email_logs_interactive --no-commit
```

Supprime les logs **SANS** créer un commit Git automatique.

Utile for:
- Scripts automatisés
- Quand Git n'est pas disponible
- Suppressions batch

</div>

---

## 📝 Exemples Pratiques

<div style="background:#f9f9f9; padding:20px; border-radius:8px; border-left:4px solid #0078d4;">

### Exemple 1: Supprimer Tous les Logs Échoués

```bash
$ python manage.py delete_email_logs_interactive --status=failed

📧 LOGS EMAILS DISPONIBLES POUR SUPPRESSION
================================================================================
  1. [05/02/2026 14:32] user1@example.com | Status: failed | Error: SMTP timeout
  2. [04/02/2026 09:15] user2@example.com | Status: failed | Error: Invalid email
  3. [03/02/2026 22:41] user3@example.com | Status: failed | Error: Max retries
================================================================================
Total: 3 logs (montrant 3)

📝 SÉLECTION DES LOGS À SUPPRIMER
👉 Entrez les numéros à supprimer: all

⚠️ CONFIRMATION DE SUPPRESSION
================================================================================
1. user1@example.com - Error: SMTP timeout (failed)
2. user2@example.com - Error: Invalid email (failed)
3. user3@example.com - Error: Max retries (failed)

Total: 3 log(s) à supprimer
⚠️ Cette action est IRRÉVERSIBLE.

❓ Êtes-vous sûr? (oui/non): oui

✅ 3 log(s) supprimé(s) avec succès!
================================================================================

📊 Logs restants: 1251
   • Total avant: 1254
   • Supprimés: 3
   • Restants: 1251

✅ Commit Git créé: 3 logs suppressions tracées

✨ Opération terminée!
```

---

### Exemple 2: Nettoyer les Vieux Logs (60+ jours)

```bash
$ python manage.py delete_email_logs_interactive --older-than-days=60

📧 LOGS EMAILS DISPONIBLES POUR SUPPRESSION
================================================================================
  1. [15/12/2025 08:20] archive@test.com | Status: sent | Welcome
  2. [10/12/2025 14:45] olduser@test.com | Status: sent | Newsletter
  3. [05/12/2025 10:30] legacy@test.com | Status: failed | Reset
  ... (showing 50 of 124 old logs)

👉 Entrez les numéros à supprimer: 1-20

⚠️ CONFIRMATION
20 log(s) à supprimer

❓ Êtes-vous sûr? (oui/non): oui

✅ 20 log(s) supprimé(s)
📊 Restants: 1234

✨ Opération terminée!
```

---

### Exemple 3: Mode Test (Dry-Run)

```bash
$ python manage.py delete_email_logs_interactive --dry-run

📧 LOGS EMAILS DISPONIBLES POUR SUPPRESSION
================================================================================
  1. [17/02/2026 14:32] user1@example.com | Status: sent | Welcome
  2. [17/02/2026 10:15] user2@example.com | Status: failed | Reset
  ... (100 logs affichés)

🔍 Mode dry-run: aucune suppression effectuée.

✨ Fin du test!
```

</div>

---

## 🎯 Syntaxe de Sélection

<div style="background:#fff3e0; padding:20px; border-radius:8px; border-left:4px solid #ff9800;">

### Formats Acceptés

| Format | Exemple | Résultat |
|--------|---------|----------|
| **Single** | `1` | Supprime le log #1 |
| **Multiple** | `1,3,5` | Supprime logs #1, #3, #5 |
| **Range** | `1-5` | Supprime logs #1 à #5 |
| **Mix** | `1,3-5,7` | Supprime #1, #3, #4, #5, #7 |
| **All** | `all` | Supprime TOUS les logs affichés |
| **Cancel** | `quit` ou `exit` | Annule l'opération |

### Exemples Concrets

```bash
# Supprimer seulement le 1er log
👉 Entrez: 1

# Supprimer les logs 1, 3, 5
👉 Entrez: 1,3,5

# Supprimer les logs de 1 à 10
👉 Entrez: 1-10

# Supprimer un mix
👉 Entrez: 1,3-5,8

# Supprimer tous
👉 Entrez: all

# Annuler
👉 Entrez: quit
```

</div>

---

# 🎓 Cas d'Usage Pratiques

<div style="background:#e3f2fd; padding:20px; border-radius:8px; border-left:4px solid #1976d2;">

## Cas 1: Je Veux Voir mes Logs

**Besoin:** Consulter l'historique des emails envoyés

**Solution Web:**
1. Accédez à `/communication/logs/email/manage/`
2. Les logs s'affichent immédiatement
3. Naviguez avec les contrôles de pagination
4. Utilisez le filtrage si besoin

---

## Cas 2: Je Veux Supprimer un Email Spécifique

**Besoin:** Supprimer le log d'un email envoyé par erreur

**Solution Web:**
1. Cherchez l'email avec [🔎 Rechercher]
2. Cochez sa case ☑️
3. Cliquez [🗑️ Delete]
4. Confirmez la suppression

---

## Cas 3: Je Veux Nettoyer les Erreurs

**Besoin:** Supprimer tous les emails échoués

**Solution Web:**
```
1. Sélectionnez Status = "Failed"
2. Cliquez "Select All"
3. Cliquez Delete
4. Confirmez
```

**Solution CLI:**
```bash
python manage.py delete_email_logs_interactive --status=failed
→ Tapez: all
→ Confirmez: oui
```

---

## Cas 4: Je Veux Automatiser le Nettoyage

**Besoin:** Supprimer les vieux logs automatiquement chaque mois

**Solution Cron:**
```bash
# Ajouter au crontab
crontab -e

# Ajouter cette ligne (exécute le 1er du mois à 2h)
0 2 1 * * cd /path/to/eebc && python manage.py delete_email_logs_interactive --older-than-days=90 --no-commit
```

**Solution Celery:**
```python
# apps/communication/tasks.py
@periodic_task(run_every=crontab(hour=2, minute=0, day_of_month=1))
def cleanup_old_logs():
    cutoff = timezone.now() - timedelta(days=90)
    deleted, _ = EmailLog.objects.filter(created_at__lt=cutoff).delete()
```

---

## Cas 5: Je Veux Tester Avant de Supprimer

**Besoin:** Vérifier ce qui serait supprimé sans risque

**Solution CLI:**
```bash
python manage.py delete_email_logs_interactive --older-than-days=30 --dry-run

# Affiche les logs de plus de 30 jours SANS les supprimer
```

</div>

---

# 🛠️ Dépannage

<div style="background:#ffebee; padding:20px; border-radius:8px; border-left:4px solid #c62828;">

## ❓ Je ne peux pas accéder à la page

**Problème:** Error 403 ou redirection vers connexion

**Causes possibles:**
1. ❌ Vous n'êtes pas connecté
2. ❌ Vous n'avez pas le rôle administrateur

**Solutions:**
```bash
# Vérifier votre statut dans Django shell
python manage.py shell

>>> from django.contrib.auth import get_user_model
>>> User = get_user_model()
>>> user = User.objects.get(username='votreusername')
>>> user.profile.role
'admin'  # Doit dire 'admin'

# Si ce n'est pas 'admin', le configurer:
>>> user.profile.role = 'admin'
>>> user.profile.save()
```

---

## ❓ Le tableau n'affiche rien

**Problème:** Les logs ne s'affichent pas

**Causes possibles:**
1. ❌ Filtres trop restrictifs appliqués
2. ❌ Aucun log n'existe en base

**Solutions:**
```
1. Cliquez le bouton [Reset] pour réinitialiser les filtres
2. Allez à la page 1 avec « Première »
3. Rafraîchissez la page (Ctrl+F5)
```

---

## ❓ Le bouton Delete ne s'active pas

**Problème:** Le bouton reste grisé même avec sélections

**Cause:** Aucun log n'est réellement sélectionné

**Solution:**
```
1. Vérifiez que les cases ☑️ sont cochées (devraient être ✓)
2. Cliquez manuellement les cases
3. Vérifiez que le texte "X selected" s'affiche
```

---

## ❓ La suppression a échoué

**Problème:** Les logs n'ont pas été supprimés

**Raisons:**
1. ❌ Confirmation annulée
2. ❌ Erreur de permission
3. ❌ Erreur database

**Solutions:**
```bash
# Vérifier les logs d'erreur
tail -f logs/django.log

# Vérifier la connection database
python manage.py dbshell
```

---

## ❓ La commande CLI échoue

**Problème:** `python manage.py delete_email_logs_interactive` ne fonctionne pas

**Cause:** Fichier commande manquant ou mal placé

**Solution:**
```bash
# Vérifier que le fichier existe
ls -la apps/communication/management/commands/delete_email_logs_interactive.py

# Vérifier la syntaxe Python
python -m py_compile apps/communication/management/commands/delete_email_logs_interactive.py

# Si erreur, réinstaller la commande
```

---

## ❓ Le commit Git échoue

**Problème:** "Commit Git échoué" en message

**Cause:** Git n'est pas disponible ou erreur de configuration

**Solution:**
```bash
# Utiliser --no-commit pour ignorer le commit Git
python manage.py delete_email_logs_interactive --no-commit

# Ou vérifier la configuration Git
git status
git config --list
```

</div>

---

# ❓ FAQ

<div style="background:#f5f5f5; padding:20px; border-radius:8px;">

## Questions Fréquentes

### Q: Puis-je récupérer un log supprimé?
**A:** Non, la suppression est **définitive et irréversible**. Une fois supprimé, le log est perdu. Utilisez TOUJOURS --dry-run pour vérifier avant.

---

### Q: Combien de logs puis-je supprimer à la fois?
**A:** Illimité! L'interface CLI limite l'affichage à 100 pour la performance, mais vous pouvez supprimer tous les logs sélectionnés.

---

### Q: Quelle est la meilleure pratique pour le nettoyage?
**A:** Nettoyer régulièrement:
- ✅ Variables par jour: Les logs FAILED
- ✅ Variables par mois: Les log de plus de 90 jours
- ✅ Variables par trimestre: Audit complet

---

### Q: Les logs sont-ils sécurisés?
**A:** Oui! Tous les accès sont loggés:
- ✅ Audit trail dans `logs/email_deletions.log`
- ✅ Commit Git avec timestamp
- ✅ IP/User tracé

---

### Q: Puis-je restaurer de la sauvegarde?
**A:** Si vous avez une sauvegarde database avant la suppression:
```bash
# Restaurer depuis sauvegarde
pg_restore --dbname=eebc backup.sql
```

---

### Q: Comment monitorer les suppressions?
**A:** Consulter les logs:
```bash
# Voir les suppressions récentes
tail -f logs/email_deletions.log

# Voir les commits Git
git log --oneline | grep MAINTENANCE

# Compter les logs supprimés
grep "Supprimés" logs/email_deletions.log | wc -l
```

---

### Q: La suppression affecte-t-elle les emails?
**A:** Non! Seuls les **logs** sont supprimés. Les emails réels ont déjà été envoyés aux destinataires. C'est juste l'historique qu'on nettoie.

---

### Q: Puis-je exporter les logs avant suppression?
**A:** Oui! Faites une sauvegarde database avant:
```bash
pg_dump -U user eebc_db > backup_$(date +%Y%m%d).sql
```

---

### Q: Quel rôle j'ai besoin?
**A:** `admin` uniquement. Pas d'autres rôles ne peuvent accéder à cette interface.

</div>

---

## 📚 Documentation Complémentaire

| Document | Contenu |
|----------|---------|
| [EMAIL_LOGS_IMPLEMENTATION_SUMMARY.md](./EMAIL_LOGS_IMPLEMENTATION_SUMMARY.md) | Détails techniques et architecture |
| [API Programmatique](#api-programmatique) | Utiliser dans du code Python |
| [Tests](#tests-automatisés) | Exécuter la suite de tests |

---

## 📞 Support

Pour des problèmes ou questions:
- 📧 Email: support@eebc.fr
- 💬 Issues: GitHub Issues
- 📱 Chat: Slack #technical-support

---

<div align="center">

**Dernière mise à jour:** 17 Février 2026  
**Version:** 1.0  
**Statut:** ✅ Production Ready

[⬆ Retour au Sommet](#-guide-complet---gestion-des-logs-emails-eebc)

</div>
