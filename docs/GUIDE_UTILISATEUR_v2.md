# Guide Utilisateur — Gestion EEBC

**Église Évangélique Baptiste de Cabassou**
Version 2.0 | Avril 2026

---

## Table des matières

1. [Accès et connexion](#1-accès-et-connexion)
2. [Dashboard](#2-dashboard)
3. [Membres](#3-membres)
4. [Club Biblique](#4-club-biblique)
5. [Cultes (Worship)](#5-cultes)
6. [Finance](#6-finance)
7. [Dons en ligne (Stripe)](#7-dons-en-ligne)
8. [Événements](#8-événements)
9. [Groupes et Départements](#9-groupes-et-départements)
10. [Transport](#10-transport)
11. [Inventaire](#11-inventaire)
12. [Communication et Notifications](#12-communication)
13. [Documents](#13-documents)
14. [Module Jeunesse](#14-module-jeunesse)
15. [Campagnes de dons](#15-campagnes)
16. [Import/Export](#16-import-export)
17. [Site public (CMS)](#17-site-public)
18. [Administration](#18-administration)

---

## 1. Accès et connexion

- URL du site public : `https://eglise-ebc.org`
- URL du dashboard : `https://eglise-ebc.org/app/`
- URL de l'admin Django : `https://eglise-ebc.org/gestion-eebc/`

### Rôles utilisateurs
| Rôle | Accès |
|------|-------|
| Admin | Tout |
| Secrétariat | Membres, événements, communication |
| Finance | Transactions, budgets, rapports, dons en ligne |
| Pasteur | Membres, visites pastorales, cultes |
| Moniteur | Club biblique de sa classe |
| Membre | Son profil, événements publics |

---

## 2. Dashboard

Le tableau de bord (`/app/`) affiche :
- Statistiques clés (membres actifs, enfants, groupes, événements)
- Finances du mois (recettes, dépenses, solde)
- Alertes (campagnes critiques, rôles non confirmés, visites nécessaires)
- Événements à venir
- Annonces actives
- Notifications non lues

### Recherche globale
La barre de recherche en haut du dashboard permet de chercher dans :
- Membres (nom, email, téléphone, ID membre)
- Événements (titre, lieu)
- Transactions (référence, description)
- Enfants (nom)
- Groupes (nom)

---

## 3. Membres

### Gestion des membres (`/app/members/`)
- Liste avec filtres (site, statut, ville, baptisé)
- Création/modification avec formulaire complet
- Identifiant unique auto-généré : `EEBC-CAB-XXXX` ou `EEBC-MAC-XXXX`
- Photo de profil
- Email et date de baptême optionnels
- Carte GPS des membres (`/gestion-eebc/members/map/`)

### Suivi pastoral (CRM)
- Événements de vie (naissance, décès, hospitalisation, mariage, baptême)
- Visites pastorales (planifiées, effectuées, à faire)
- Notifications automatiques aux pasteurs pour les événements critiques

### Notifications automatiques
- Nouveau membre → admins et secrétariat notifiés
- Événement de vie → pasteurs notifiés
- Membre non visité depuis 6 mois → alerte hebdomadaire

---

## 4. Club Biblique

### Gestion (`/app/bibleclub/`)
- Classes par tranche d'âge
- Enfants avec contacts parents (père et mère)
- Moniteurs (principal et assistants)
- Sessions avec prise de présence

### Notifications automatiques
- Enfant absent → parents notifiés par email
- 3+ absences consécutives → alerte parents + moniteur principal
- Session terminée → rapport envoyé aux responsables

---

## 5. Cultes

### Planification (`/app/worship/`)
- Planning mensuel par site
- Assignation des rôles (prédicateur, dirigeant, sonorisation, accueil, etc.)
- Confirmation/déclin par les membres assignés
- Notifications automatiques aux membres assignés
- Alerte si rôles non confirmés à J-3

---

## 6. Finance

### Transactions (`/app/finance/transactions/`)
- CRUD complet avec 6 types : Don, Dîme, Offrande, Dépense, Remboursement, Transfert
- 6 méthodes de paiement : Espèces, Chèque, Virement, Carte, Mobile, Autre
- Validation par un responsable (workflow en_attente → validé)
- Soft-delete avec audit trail
- Export Excel

### Dons en ligne (`/app/finance/online-donations/`)
- Liste complète des dons Stripe avec filtres
- Stats (total reçu, nombre de dons)
- Lien vers la transaction associée

### Récapitulatif par membre (`/app/finance/member-summary/`)
- Tableau annuel : Dîmes, Dons, Offrandes par membre
- Détail mensuel par membre
- Export PDF individuel (pour reçus fiscaux)

### Rapports (`/app/finance/reports/`)
- Filtres par année, mois, site
- KPIs : recettes, dépenses, solde
- Répartition par type et méthode de paiement
- Évolution mensuelle
- Export PDF

### Budgets (`/app/finance/budgets/`)
- Création par groupe/département
- Soumission et approbation ligne par ligne
- Suivi d'utilisation
- Export Excel et impression

### Prévisionnel (`/app/finance/forecasts/`)
- Scénarios (optimiste, réaliste, pessimiste)
- Lignes mensuelles recettes/dépenses
- Export Excel

### Reçus fiscaux (`/app/finance/tax-receipts/`)
- Génération PDF individuelle
- Génération en masse (bulk)
- Envoi par email (individuel ou bulk)

### Notifications automatiques
- Don en ligne reçu → équipe finance notifiée
- Dépense en attente de validation → responsables finance notifiés
- Transaction importante (>500€ dépense, >1000€ don) → admins notifiés

---

## 7. Dons en ligne (Stripe)

### Page de don (`https://eglise-ebc.org/don/`)
- Checkout personnalisé avec branding EEBC
- Types : Don, Dîme, Offrande
- Montants prédéfinis ou libre
- Don récurrent (mensuel)
- Captcha Cloudflare Turnstile
- Paiement sécurisé via Stripe

### Après le paiement
- Page de succès avec récapitulatif
- Email HTML professionnel avec reçu PDF en pièce jointe
- Transaction automatiquement créée dans la comptabilité
- Équipe finance notifiée

### Configuration Stripe
Variables d'environnement requises sur Render :
- `STRIPE_PUBLIC_KEY` : clé publique (pk_live_...)
- `STRIPE_SECRET_KEY` : clé secrète (sk_live_...)
- `STRIPE_WEBHOOK_SECRET` : secret du webhook (whsec_...)

Webhook URL : `https://eglise-ebc.org/webhooks/stripe/`

---

## 8. Événements

### Gestion (`/app/events/`)
- CRUD avec catégories, récurrence, visibilité
- Portée des notifications : organisateur, groupe, département, membres, tous
- Rappel automatique X jours avant (configurable par événement)
- Synchronisation automatique avec le site public si visibilité = public

### Notifications automatiques
- Nouvel événement → admins notifiés
- Rappel J-X → destinataires selon la portée
- Événement annulé → email aux destinataires

---

## 9. Groupes et Départements

### Groupes (`/app/groups/`)
- Groupes de maison avec membres
- Réunions avec génération automatique
- Statistiques de participation

### Départements (`/app/departments/`)
- Liste des départements avec responsable
- Membres assignés

---

## 10. Transport (`/app/transport/`)
- Chauffeurs avec profil
- Demandes de transport (création, assignation)
- Calendrier des transports
- Pointage des chauffeurs pour le club biblique

---

## 11. Inventaire (`/app/inventory/`)
- Équipements par catégorie
- CRUD complet

---

## 12. Communication

### Emails
- Backend Hostinger SMTP
- Templates HTML professionnels avec branding EEBC
- Logs de tous les emails envoyés
- Désabonnement par type de notification

### Notifications in-app
- Cloche de notifications dans le dashboard
- Types : info, warning, success, error
- Marquer comme lu

### Annonces
- Création avec priorité et visibilité
- Épinglage en haut du dashboard
- Dates de début/fin

### SMS et WhatsApp (si Twilio configuré)
- Envoi via le service de notification multicanal
- Logs des SMS envoyés

---

## 13. Documents (`/app/documents/`)
- Upload de fichiers (PDF, images, etc.)
- Catégories
- Partage par lien sécurisé (token UUID)
- Génération de documents (éditeur intégré)
- Aperçu et téléchargement

---

## 14. Module Jeunesse (`/app/young/`)
- Groupes de jeunes
- Membres jeunes avec inscription
- Activités/événements
- Prise de présence
- Impression fiche d'inscription

---

## 15. Campagnes de dons (`/app/campaigns/`)
- Objectif financier avec suivi de progression
- Dons nominatifs ou anonymes
- Reçu PDF par don
- Lien de partage sécurisé pour dons en ligne

---

## 16. Import/Export (`/app/imports/`)
- Hub central d'import/export
- Import Excel (membres, enfants, transactions)
- Templates téléchargeables
- Export : membres, enfants, jeunes, groupes, inventaire, transport, communication

---

## 17. Site public (CMS)

### Pages publiques
- Accueil avec carousel/hero animé et histoires bibliques
- Nos Églises (carte interactive)
- Événements publics
- Actualités
- Contact (formulaire avec Turnstile)
- Inscription visiteur
- Page de don en ligne

### Gestion CMS (`/app/cms/`)
- Articles d'actualité
- Pages statiques
- Témoignages
- Horaires des cultes
- Sliders du carousel

### Visiteurs
- Inscription via le site public → notification aux admins
- Suivi dans l'admin (contacté, converti en membre)
- Action admin "Convertir en membre" en un clic

---

## 18. Administration

### Sauvegardes
- Backup automatique à chaque déploiement
- Commande manuelle : `python manage.py backup_db`
- Rotation automatique (30 dernières conservées)
- Alerte email en cas d'échec

### Monitoring
- Health check : `https://eglise-ebc.org/health/`
- Vérifie : base de données, cache, Stripe, email, espace disque
- Sentry pour le suivi des erreurs (configurer `SENTRY_DSN`)

### Notifications planifiées (sans Celery)
- Commande : `python manage.py run_notifications --all`
- Exécutée à chaque déploiement
- Pour exécution quotidienne : configurer un Cron Job Render à 7h

### Nettoyage des dons de test
```bash
python manage.py cleanup_test_donations --dry-run  # Prévisualisation
python manage.py cleanup_test_donations --yes       # Suppression
```

### Variables d'environnement requises (Render)
| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Clé secrète Django |
| `DATABASE_URL` | URL PostgreSQL |
| `ALLOWED_HOSTS` | Domaines autorisés |
| `EMAIL_BACKEND` | `hostinger` ou `smtp` |
| `HOSTINGER_EMAIL_HOST_USER` | Email Hostinger |
| `HOSTINGER_EMAIL_HOST_PASSWORD` | Mot de passe email |
| `STRIPE_PUBLIC_KEY` | Clé publique Stripe |
| `STRIPE_SECRET_KEY` | Clé secrète Stripe |
| `STRIPE_WEBHOOK_SECRET` | Secret webhook Stripe |
| `TURNSTILE_SITE_KEY` | Clé Cloudflare Turnstile |
| `TURNSTILE_SECRET_KEY` | Secret Turnstile |
| `SENTRY_DSN` | DSN Sentry (monitoring) |
