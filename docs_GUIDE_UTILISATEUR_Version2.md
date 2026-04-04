# Guide Utilisateur – Gestion EEBC  
**Version 2.0 – 2026-02-14**  
*Application de gestion pour l’Église Évangélique Baptiste de Cabassou*  

---

> **Convention captures d’écran**  
> Stocker les images dans `docs/images/`  
> Exemple : `docs/images/01-login.png`

---

## Table des matières

1. [Introduction](#1-introduction)  
2. [Accès & Connexion](#2-accès--connexion)  
3. [Navigation & Interface](#3-navigation--interface)  
4. [Module Membres](#4-module-membres)  
5. [Module CRM Pastoral](#5-module-crm-pastoral)  
6. [Module Club Biblique](#6-module-club-biblique)  
7. [Module Cultes (Worship)](#7-module-cultes-worship)  
8. [Module Finance](#8-module-finance)  
9. [Module Événements](#9-module-événements)  
10. [Module Groupes](#10-module-groupes)  
11. [Module Départements](#11-module-départements)  
12. [Module Transport](#12-module-transport)  
13. [Module Inventaire](#13-module-inventaire)  
14. [Module Communication](#14-module-communication)  
15. [Rôles & Permissions](#15-rôles--permissions)  
16. [FAQ & Dépannage](#16-faq--dépannage)  
17. [Annexes](#17-annexes)

---

# 1. Introduction

## 1.1 Présentation
Gestion EEBC est un système complet de gestion d’église : membres, cultes, finances, événements, communication, transport et inventaire.

### 📸 Capture d’écran  
`docs/images/01-dashboard.png`

---

# 2. Accès & Connexion

## 2.1 Accès
- Public : https://gestion-eebc.onrender.com  
- Local : http://localhost:8000

## 2.2 Connexion
1. Accéder à la page de connexion  
2. Renseigner identifiant + mot de passe  
3. Cliquer **Se connecter**

### 📸 Capture d’écran  
`docs/images/02-login.png`

---

# 3. Navigation & Interface

## 3.1 Structure
- Barre supérieure  
- Menu latéral  
- Zone centrale  

### 📸 Capture d’écran  
`docs/images/03-layout.png`

## 3.2 Mode nuit
Activer l’icône 🌙 dans la barre supérieure.

### 📸 Capture d’écran  
`docs/images/04-darkmode.png`

---

# 4. Module Membres

## 4.1 Créer un membre
1. Menu **Membres**  
2. **Nouveau**  
3. Remplir identité, contact, situation  
4. Enregistrer  

### 📸 Capture d’écran  
`docs/images/05-member-create.png`

## 4.2 Modifier une fiche
1. Ouvrir membre  
2. Cliquer **Modifier**  
3. Sauvegarder  

### 📸 Capture d’écran  
`docs/images/06-member-edit.png`

## 4.3 Gérer les familles
1. Ouvrir membre  
2. Section **Famille**  
3. Choisir rôle  

### 📸 Capture d’écran  
`docs/images/07-family.png`

## 4.4 Préférences de notifications
1. Ouvrir membre  
2. Section **Préférences**  
3. Cocher Email / SMS / WhatsApp  

### 📸 Capture d’écran  
`docs/images/08-member-notifications.png`

---

# 5. Module CRM Pastoral

## 5.1 Ajouter un événement de vie
1. Aller sur un membre  
2. Section **Événements de vie**  
3. **Ajouter**  
4. Choisir type + priorité  

### 📸 Capture d’écran  
`docs/images/09-life-event.png`

## 5.2 Programmer une visite pastorale
1. Ouvrir **Visites pastorales**  
2. Cliquer **Nouvelle visite**  
3. Choisir type, date, membre  
4. Enregistrer  

### 📸 Capture d’écran  
`docs/images/10-pastoral-visit.png`

## 5.3 Alertes automatiques
Vérifier la liste d’alertes générées pour les visites en retard.

### 📸 Capture d’écran  
`docs/images/11-pastoral-alerts.png`

---

# 6. Module Club Biblique

## 6.1 Tranches d’âge
1. Menu **Club Biblique**  
2. Ouvrir **Tranches d’âge**  
3. Ajouter ou modifier  

### 📸 Capture d’écran  
`docs/images/12-age-groups.png`

## 6.2 Classes
1. Ouvrir **Classes**  
2. Cliquer **Nouvelle classe**  
3. Définir tranche, salle, moniteur  

### 📸 Capture d’écran  
`docs/images/13-class-create.png`

## 6.3 Enfants
1. Ouvrir **Enfants**  
2. Ajouter identité + parents  
3. Assigner à une classe  

### 📸 Capture d’écran  
`docs/images/14-child-create.png`

## 6.4 Sessions
1. Ouvrir **Sessions**  
2. Nouvelle session  
3. Définir date + thème  

### 📸 Capture d’écran  
`docs/images/15-session.png`

## 6.5 Présences
1. Ouvrir session  
2. Cocher présent/absent  
3. Enregistrer  

### 📸 Capture d’écran  
`docs/images/16-attendance.png`

## 6.6 Transport enfants
1. Ouvrir un enfant  
2. Section **Transport**  
3. Affecter chauffeur  

### 📸 Capture d’écran  
`docs/images/17-child-transport.png`

---

# 7. Module Cultes (Worship)

## 7.1 Créer un culte
1. Menu **Cultes**  
2. **Nouveau**  
3. Choisir type + thème  
4. Enregistrer  

### 📸 Capture d’écran  
`docs/images/18-worship-create.png`

## 7.2 Rôles & assignations
1. Ouvrir culte  
2. Ajouter rôles  
3. Assigner membres  

### 📸 Capture d’écran  
`docs/images/19-worship-roles.png`

## 7.3 Planning mensuel
1. Menu **Planning mensuel**  
2. Choisir mois + site  
3. Assigner rôles  
4. Publier  

### 📸 Capture d’écran  
`docs/images/20-monthly-schedule.png`

## 7.4 Confirmation par token
1. Membre reçoit email  
2. Clique lien  
3. Accepte ou refuse  

### 📸 Capture d’écran  
`docs/images/21-role-token.png`

---

# 8. Module Finance

## 8.1 Transaction
1. Menu **Finance**  
2. **Nouvelle transaction**  
3. Type + montant + méthode  
4. Valider  

### 📸 Capture d’écran  
`docs/images/22-finance-transaction.png`

## 8.2 Catégories
1. Ouvrir **Catégories**  
2. Créer / modifier  

### 📸 Capture d’écran  
`docs/images/23-finance-category.png`

## 8.3 Justificatifs (OCR)
1. Ouvrir transaction  
2. Ajouter justificatif  
3. Vérifier extraction  

### 📸 Capture d’écran  
`docs/images/24-ocr.png`

## 8.4 Dons en ligne (Stripe)
1. Ouvrir page de dons  
2. Choisir montant  
3. Paiement Stripe  

### 📸 Capture d’écran  
`docs/images/25-online-donation.png`

## 8.5 Reçus fiscaux
1. Menu **Reçus fiscaux**  
2. Générer reçu  
3. Envoyer au donateur  

### 📸 Capture d’écran  
`docs/images/26-tax-receipt.png`

## 8.6 Budgets
1. Menu **Budgets**  
2. Nouveau budget  
3. Ajouter lignes  
4. Soumettre / approuver  

### 📸 Capture d’écran  
`docs/images/27-budget.png`

---

# 9. Module Événements

## 9.1 Créer événement
1. Menu **Événements**  
2. **Nouveau**  
3. Définir titre + date + lieu  

### 📸 Capture d’écran  
`docs/images/28-event-create.png`

## 9.2 Récurrence & visibilité
1. Choisir récurrence  
2. Définir visibilité  

### 📸 Capture d’écran  
`docs/images/29-event-visibility.png`

## 9.3 Inscriptions
1. Ouvrir événement  
2. Section **Inscriptions**  
3. Ajouter membre  

### 📸 Capture d’écran  
`docs/images/30-event-registration.png`

---

# 10. Module Groupes

## 10.1 Créer groupe
1. Menu **Groupes**  
2. **Nouveau**  
3. Ajouter membres  

### 📸 Capture d’écran  
`docs/images/31-group-create.png`

## 10.2 Réunions
1. Ouvrir groupe  
2. Ajouter réunion  

### 📸 Capture d’écran  
`docs/images/32-group-meeting.png`

---

# 11. Module Départements

## 11.1 Créer département
1. Menu **Départements**  
2. **Nouveau**  
3. Définir responsables  

### 📸 Capture d’écran  
`docs/images/33-department-create.png`

---

# 12. Module Transport

## 12.1 Chauffeurs
1. Menu **Transport**  
2. Ajouter chauffeur  

### 📸 Capture d’écran  
`docs/images/34-driver.png`

## 12.2 Demande transport
1. Menu **Demandes**  
2. Nouvelle demande  
3. Assigner chauffeur  

### 📸 Capture d’écran  
`docs/images/35-transport-request.png`

---

# 13. Module Inventaire

## 13.1 Catégories
Créer / modifier catégories.

### 📸 Capture d’écran  
`docs/images/36-inventory-category.png`

## 13.2 Équipements
1. Nouveau matériel  
2. Quantité + état  
3. Enregistrer  

### 📸 Capture d’écran  
`docs/images/37-equipment.png`

---

# 14. Module Communication

## 14.1 Emails
1. Ouvrir **Email logs**  
2. Consulter statuts  

### 📸 Capture d’écran  
`docs/images/38-email-log.png`

## 14.2 SMS
1. Ouvrir **SMS logs**  
2. Vérifier envois  

### 📸 Capture d’écran  
`docs/images/39-sms-log.png`

## 14.3 Annonces
1. Nouvelle annonce  
2. Choisir visibilité + priorité  

### 📸 Capture d’écran  
`docs/images/40-announcement.png`

## 14.4 Templates d’emails
1. Menu **Templates**  
2. Créer ou éditer  

### 📸 Capture d’écran  
`docs/images/41-email-template.png`

---

# 15. Rôles & Permissions

| Rôle | Permissions |
|------|-------------|
| Administrateur | Accès complet |
| Pasteur | Membres, CRM, Cultes |
| Secrétaire | Membres, Événements |
| Trésorier | Finance |
| Moniteur | Club Biblique |
| Responsable groupe | Son groupe |

---

# 16. FAQ & Dépannage

**Mot de passe oublié** → utiliser “Mot de passe oublié”  
**Erreur de sauvegarde** → vérifier champs obligatoires  
**Accès refusé** → vérifier rôle et permissions  

---

# 17. Annexes

- Support : contact@eglise-ebc.org  
- Site : https://eglise-ebc.org  

---

*© 2026 – Gestion EEBC*