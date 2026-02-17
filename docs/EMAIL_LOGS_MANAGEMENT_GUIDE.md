# 📧 Guide Gestion des Logs Emails - EEBC

## Vue d'ensemble

Le système de gestion des logs emails EEBC offre deux méthodes pour supprimer les vieux logs emails:
1. **Interface Web** - Interface utilisateur avec cases à cocher
2. **Commande CLI** - Gestion en ligne de commande avec options avancées

---

## 1. Interface Web de Gestion

### Accès à l'Interface

```
URL: /communication/logs/email/manage/
Permissions: Administrateur uniquement
```

### Fonctionnalités

#### 📊 Tableau de Bord Statistique
- **Total de logs** - Nombre total de logs en base
- **Envoyés** - Logs avec statut "sent"
- **Échoués** - Logs avec statut "failed"
- **En attente** - Logs avec statut "pending"

#### 🔍 Filtrage et Recherche
```
Filtrer par statut:
- Tous
- Sent (envoyés avec succès)
- Failed (échoués)
- Pending (en attente)
- Bounced (rebondis)
- Opened (ouverts)
- Clicked (cliqué)

Rechercher par:
- Email du destinataire
- Sujet du message
- Nom du destinataire
```

#### ☑️ Suppression avec Cases à Cocher

**Sélection unitaire:**
```
1. Cochez les cases individuelles à côté de chaque log
2. Le bouton "Delete" se active automatiquement
3. Un total indique le nombre sélectionné
```

**Sélection globale:**
```
1. Cochez la case "Select All" dans l'en-tête
2. Tous les logs de la page sont sélectionnés
3. Un modal de confirmation apparaît
```

#### ⏳ Pagination
```
- 50 logs par page
- Navigation: Première | Précédent | Numéros | Suivant | Dernière
- Affichage: "Showing 1-50 of 234"
```

#### 🔍 Détails des Logs
```
Cliquez sur le bouton "View" dans la colonne Actions pour:
- Voir le corps complet du message
- Vérifier les timestamps
- Consulter les messages d'erreur
- Afficher les adresses des destinataires
```

### Workflow d'Utilisation

#### Scénario 1: Supprimer tous les logs échoués

```
1. Naviguer vers /communication/logs/email/manage/
2. Sélectionner le filtre "Failed"
3. Cliquer "Select All" pour sélectionner tous les échoués
4. Cliquer "Delete"
5. Confirmer dans le modal: "Êtes-vous sûr?"
6. Les logs sont supprimés et la page se rafraîchit
```

#### Scénario 2: Supprimer les logs d'une date spécifique

```
1. Se rendre sur /communication/logs/email/manage/
2. Utiliser le champ Recherche pour filtrer
3. Sélectionner les logs spécifiques avec les cases à cocher
4. Cliquer le bouton "Delete"
5. Confirmer la suppression
```

#### Scénario 3: Recherche et suppression ciblée

```
1. Entrer une adresse email dans le champ Recherche
2. Les logs correspondants s'affichent
3. Cocher les vrais positifs
4. Cliquer Delete
5. Confirmer la suppression
```

---

## 2. Commande CLI Interactive

### Installation

La commande est automatiquement disponible dans Django:

```bash
python manage.py delete_email_logs_interactive
```

### Options Disponibles

#### Option: Filtrer par statut

```bash
python manage.py delete_email_logs_interactive --status=failed
```

Valeurs acceptées:
- `pending` - Logs en attente
- `sent` - Logs envoyés
- `failed` - Logs échoués
- `bounced` - Logs rebondis
- `opened` - Logs ouverts
- `clicked` - Logs cliqués

#### Option: Supprimer les anciens logs

```bash
python manage.py delete_email_logs_interactive --older-than-days=30
```

Supprime tous les logs créés il y a plus de 30 jours.

#### Option: Mode test (dry-run)

```bash
python manage.py delete_email_logs_interactive --dry-run
```

Affiche ce qui serait supprimé SANS effectuer la suppression.

#### Option: Sans commit Git

```bash
python manage.py delete_email_logs_interactive --no-commit
```

Supprime les logs SANS créer un commit Git de traçabilité.

### Exemples d'Utilisation

#### Exemple 1: Supprimer tous les logs échoués

```bash
python manage.py delete_email_logs_interactive --status=failed

# Affichage:
# 📧 LOGS EMAILS DISPONIBLES POUR SUPPRESSION
# ================================================================================
#   1. [05/12/2024 14:32] user1@example.com | Status: failed   | Error sending...
#   2. [04/12/2024 09:15] user2@example.com | Status: failed   | SMTP timeout...
#   3. [03/12/2024 22:41] user3@example.com | Status: failed   | Invalid email...
# ================================================================================
# Total: 3 logs (montrant 3)
# 
# 👉 Entrez les numéros à supprimer: all
# 
# ⚠️ CONFIRMATION DE SUPPRESSION
# 1. user1@example.com - Error sending... (failed)
# 2. user2@example.com - SMTP timeout... (failed)
# 3. user3@example.com - Invalid email... (failed)
# ❓ Êtes-vous sûr? (oui/non): oui
# ✅ 3 log(s) supprimé(s) avec succès!
```

#### Exemple 2: Supprimer les logs de plus de 60 jours

```bash
python manage.py delete_email_logs_interactive --older-than-days=60
```

#### Exemple 3: Mode test sur tous les logs

```bash
python manage.py delete_email_logs_interactive --dry-run

# Affichage: 🔍 Mode dry-run: aucune suppression.
```

#### Exemple 4: Sélection partielle

```bash
python manage.py delete_email_logs_interactive

# Affichage de tous les logs...
# 
# 👉 Entrez les numéros à supprimer: 1,3,5-7

# Supprime les logs #1, #3, #5, #6, #7
```

### Syntaxe de Sélection

```
Format          | Résultat
===============|=========================================
"1"             | Supprime le log #1
"1,3,5"         | Supprime logs #1, #3, #5
"1-5"           | Supprime logs #1, #2, #3, #4, #5
"1,3-5,7"       | Supprime logs #1, #3, #4, #5, #7
"all"           | Supprime TOUS les logs affichés
"quit" / "exit" | Annule l'opération
```

---

## 3. Traçabilité et Logs Audits

### Fichier de Log des Suppressions

Chaque suppression est tracée dans:
```
logs/email_deletions.log
```

Format:
```
[2024-12-05 14:32:15] Supprimés 3 logs (IDs: [123, 456, 789])
[2024-12-04 10:15:42] Supprimés 1 log (IDs: [321])
```

### Commit Git Automatique

Après chaque suppression CLI, un commit Git est créé:

```bash
git log --oneline | head -5
# abc1234 [MAINTENANCE] Suppression de 3 logs emails
# def5678 [MAINTENANCE] Suppression de 1 log emails
# ghi9012 Fix email validation
```

Pour consulter les détails:
```bash
git show abc1234

# [MAINTENANCE] Suppression de 3 logs emails
# 
# Date: 2024-12-05 14:32:15
# IDs supprimés: 123, 456, 789
# Total: 3 logs
```

---

## 4. Maintenance Automatisée

### Nettoyage Périodique

Pour nettoyer automatiquement les vieux logs, utilisez une tâche Cron:

```bash
# Crontab (supprimer les logs de plus de 90 jours chaque nuit)
0 2 * * * cd /path/to/eebc && python manage.py delete_email_logs_interactive --older-than-days=90 --no-commit
```

### Celery Beat (Alternative)

Si vous utilisez Celery Beat:

```python
# gestion_eebc/celery.py
from celery.schedules import crontab

app.conf.beat_schedule = {
    'cleanup-email-logs': {
        'task': 'apps.communication.tasks.cleanup_email_logs',
        'schedule': crontab(hour=2, minute=0),  # Chaque nuit à 2h
    },
}
```

---

## 5. Permissions et Sécurité

### Permissions Requises

| Feature | Permission | Notes |
|---------|-----------|-------|
| Visualiser logs | `admin` | Via `request.user.has_role('admin')` |
| Supprimer logs | `admin` | Confirmation requise |
| CLI Command | Serveur | Accès SSH/Terminal uniquement |

### Protections

```python
✅ Authentification requise pour l'interface web
✅ Vérification du rôle administrateur
✅ Confirmation avant suppression
✅ Modal de confirmation avec décompte
✅ Traçabilité complète via Git
✅ Logs d'audit dans logs/email_deletions.log
✅ Limitation à 100 logs affichés (CLI) pour éviter les pannes
```

---

## 6. Dépannage

### Problème: "Permission Denied" sur l'interface web

**Cause:** L'utilisateur n'a pas le rôle administrateur.

**Solution:**
```bash
# Dans Django shell
python manage.py shell
>>> from django.contrib.auth import get_user_model
>>> User = get_user_model()
>>> user = User.objects.get(username='votreuser')
>>> user.profile.role = 'admin'
>>> user.profile.save()
```

### Problème: Les cases à cocher ne réagissent pas

**Cause:** JavaScript non chargé ou erreur de console.

**Solution:**
```bash
# 1. Vérifier la console navigateur (F12)
# 2. Recharger la page (Ctrl+F5)
# 3. Vérifier que jQuery et Bootstrap JS sont chargés
```

### Problème: "Le commit Git a échoué"

**Cause:** Repository pas initialisé ou pas de changements.

**Solution:**
```bash
# Utiliser --no-commit pour ignorer le commit Git
python manage.py delete_email_logs_interactive --no-commit
```

### Problème: Logs non affichés dans l'interface

**Cause:** Pourraient être filtrés ou paginés.

**Solution:**
1. Vérifier les filtres appliqués
2. Consulter la pagination (aller à la page 1)
3. Réinitialiser les filtres avec le bouton "Reset"

---

## 7. Statistiques et Monitoring

### Vérifier le nombre de logs

```bash
python manage.py shell
>>> from apps.communication.models import EmailLog
>>> EmailLog.objects.count()
1234
>>> EmailLog.objects.filter(status='failed').count()
45
>>> EmailLog.objects.filter(status='sent').count()
1189
```

### Export CSV des logs

Pour exporter avant suppression:

```python
from apps.communication.models import EmailLog
import csv
from django.http import HttpResponse

logs = EmailLog.objects.all()

response = HttpResponse(content_type='text/csv')
response['Content-Disposition'] = 'attachment; filename="logs.csv"'

writer = csv.writer(response)
writer.writerow(['ID', 'Email', 'Sujet', 'Statut', 'Date'])

for log in logs:
    writer.writerow([
        log.id,
        log.recipient_email,
        log.subject,
        log.status,
        log.created_at.isoformat()
    ])

return response
```

---

## 8. Tests

### Exécuter les tests

```bash
python manage.py test test_email_logs_management

# Résultats:
# test_email_logs_deletion_multiple ... ok
# test_email_logs_deletion_single ... ok
# test_email_logs_filtering_by_status ... ok
# test_email_logs_page_admin_access ... ok
# test_email_logs_page_requires_admin ... ok
# test_email_logs_page_requires_login ... ok
# test_email_logs_search ... ok
# test_management_command_execution ... ok
# test_pagination ... ok
# test_email_logs_statistics ... ok
```

### Tests spécifiques

```bash
# Tester uniquement la suppression
python manage.py test test_email_logs_management.EmailLogsManagementTestCase.test_email_logs_deletion_single

# Tester uniquement la CLI
python manage.py test test_email_logs_management.EmailLogsManagementTestCase.test_management_command_execution

# Mode verbose
python manage.py test test_email_logs_management -v 2
```

---

## 9. Migration Existant

### De l'ancienne système

Si vous utilisiez `cleanup_email_logs` command précédemment:

```bash
# Ancien (toujours disponible)
python manage.py cleanup_email_logs

# Nouveau (interactif, avec validation)
python manage.py delete_email_logs_interactive

# Nouveau (interface web)
# -> /communication/logs/email/manage/
```

Les deux systèmes coexistent pour la compatibilité.

---

## 10. API Programmatique

### Utiliser dans du code Python

```python
from apps.communication.models import EmailLog
from django.utils import timezone

# Supprimer les logs de plus de 90 jours
cutoff = timezone.now() - timezone.timedelta(days=90)
deleted, _ = EmailLog.objects.filter(created_at__lt=cutoff).delete()
print(f"Supprimés {deleted} logs")

# Supprimer par statut
EmailLog.objects.filter(status='failed').delete()

# Supprimer par email
EmailLog.objects.filter(recipient_email='removed@example.com').delete()
```

---

## Résumé Rapide

| Besoin | Méthode | Commande |
|--------|--------|----------|
| Supprimer via interface web | Interface web | Accédez à `/communication/logs/email/manage/` |
| Supprimer les logs échoués | CLI | `python manage.py delete_email_logs_interactive --status=failed` |
| Supprimer les vieux logs | CLI | `python manage.py delete_email_logs_interactive --older-than-days=60` |
| Voir ce qui sera supprimé | CLI | `python manage.py delete_email_logs_interactive --dry-run` |
| Suppression auto mensuelle | Cron | Ajouter crontab avec la commande CLI |
| Voir les logs d'audit | Fichier | Consulter `logs/email_deletions.log` |

---

**Dernière mise à jour:** 05 Décembre 2024  
**Version:** 1.0  
**Statut:** ✅ Production Ready
