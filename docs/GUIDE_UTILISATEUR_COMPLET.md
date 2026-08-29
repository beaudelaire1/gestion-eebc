# Guide Utilisateur Complet – Gestion EEBC

Version: 2026-02-14  
Public: Équipe pastorale, secrétariat, responsables de ministères, trésorerie, communication, administration

---

## 1) Objectif de l’application

Gestion EEBC centralise la gestion de l’église dans une interface unique:

- Membres et familles
- Suivi pastoral (événements de vie, visites)
- Club biblique (classes, enfants, sessions, présences)
- Cultes et planification
- Événements et calendrier
- Groupes et départements
- Finance (transactions, budgets, reçus)
- Inventaire
- Transport
- Communication (annonces, notifications, emails)
- CMS public (contenu du site)

---

## 2) Accès et connexion

### URL principales

- Interface interne: `/app/`
- Administration Django/Jazzmin: `/admin/`
- Site public: `/`

### Connexion

1. Ouvrir la page de connexion.
2. Saisir identifiant + mot de passe.
3. Valider le CAPTCHA si demandé.
4. Cliquer sur **Se connecter**.

### Sécurité

- Verrouillage temporaire après tentatives échouées répétées.
- Expiration de session en cas d’inactivité.
- 2FA disponible selon configuration de compte.

---

## 3) Navigation générale

L’interface interne est organisée par menu latéral:

- **Principal**: tableau de bord, calendrier, accès site public
- **Club Biblique**: vue d’ensemble, enfants, classes, sessions
- **Vie d’Église**: cultes, planning, finance, budgets, campagnes
- **Gestion**: membres, familles, visites, groupes, départements
- **Ressources**: transport, inventaire
- **Communication**: notifications, annonces, historiques

Bonnes pratiques de navigation:

- Utiliser les boutons **Retour à la liste** sur les pages détail.
- Préférer les actions depuis l’interface `/app/` (et non `/admin/`) pour les opérations quotidiennes.

---

## 4) Tableau de bord (`/app/`)

Le dashboard affiche les blocs clés:

- Statistiques globales
- Dernière session club biblique
- Campagnes actives
- Trésorerie du mois
- Prochain culte
- Suivi pastoral

### Alertes pastorales

- Les membres non visités renvoient vers une page interne de suivi (`/app/members/visits/needed/`).

---

## 5) Module Membres

### Liste (`/app/members/`)

Fonctions:

- Recherche par nom, email, téléphone
- Filtres par statut
- Tri et pagination
- Accès création/édition/suppression selon rôle

### Détail membre (`/app/members/<id>/`)

- Informations personnelles et ecclésiales
- Actions rapides: modifier, supprimer
- Bouton **Retour à la liste**

### Création / modification

- Vérifier l’exactitude des coordonnées
- Compléter site, statut, informations de contact
- Sauvegarder et contrôler la fiche

### Suppression

- Passer par l’écran de confirmation
- Utiliser **Annuler** ou **Retour à la liste** si nécessaire

---

## 6) Familles

### Pages principales

- Liste: `/app/members/families/`
- Détail: `/app/members/families/<id>/`
- Création / édition / ajout membre

### Usage recommandé

- Créer d’abord la famille
- Associer les membres avec le bon rôle familial
- Vérifier adresse/téléphone communs

---

## 7) Suivi pastoral

### Événements de vie

- Liste: `/app/members/life-events/`
- Création: `/app/members/life-events/create/`
- Détail + marquage visité/annoncé

### Visites pastorales

- Liste: `/app/members/visits/`
- À visiter: `/app/members/visits/needed/`
- Création: `/app/members/visits/create/`

### Flux conseillé

1. Créer l’événement de vie.
2. Planifier la visite.
3. Mettre à jour le statut (planifié → effectué).
4. Ajouter un résumé de visite et actions de suivi.

---

## 8) Club Biblique

### Classes

- Liste: `/app/bibleclub/classes/`
- Détail: `/app/bibleclub/classes/<id>/`
- CRUD complet classes

La page détail classe contient:

- Capacité et occupation
- Moniteurs assignés
- Enfants inscrits
- Bouton **Retour à la liste**

### Enfants

- Liste: `/app/bibleclub/children/`
- Détail, création, édition, suppression

### Sessions et présences

- Sessions: `/app/bibleclub/sessions/`
- Création session
- Feuille d’appel par classe
- Mise à jour des statuts de présence

---

## 9) Inventaire

### Équipements

- Liste: `/app/inventory/`
- Détail: `/app/inventory/<id>/`
- CRUD complet équipements

La page détail équipement inclut:

- Informations générales et achat
- Historique des modifications
- Actions rapides
- Bouton **Retour à la liste** (en haut et en bas)

### Catégories

- Liste et CRUD des catégories

---

## 10) Finance

### Fonctionnalités clés

- Tableau de bord finance
- Transactions (création, validation, suivi)
- Budgets (cycle de vie, approbation, suivi)
- Reçus fiscaux

### Bonnes pratiques

- Valider les transactions avec justificatifs
- Utiliser les statuts cohérents (en attente/validé)
- Vérifier les exports avant diffusion

---

## 11) Cultes (Worship)

- Gestion des services de culte
- Affectation des rôles
- Suivi des confirmations
- Planning mensuel

Procédure type:

1. Créer/mettre à jour le service.
2. Assigner les rôles.
3. Vérifier les confirmations.
4. Suivre les rôles non confirmés depuis le dashboard.

---

## 12) Événements

- Calendrier
- Détail événement
- Création, édition, annulation
- Catégories d’événements

Conseil:

- Toujours contrôler date, heure, lieu, visibilité avant publication.

---

## 13) Groupes et Départements

### Groupes

- Liste, détail, création, édition, suppression
- Réunions de groupe
- Dashboard groupes

### Départements

- Gestion des départements
- Responsables et rattachements

---

## 14) Transport

Fonctions principales:

- Chauffeurs
- Demandes de transport
- Suivi des trajets liés aux activités

---

## 15) Communication

- Notifications utilisateur
- Annonces
- Journaux email/SMS

Bonnes pratiques:

- Segmenter les destinataires
- Relire les annonces avant envoi
- Suivre les logs en cas d’échec

---

## 16) CMS / Site public

- Gestion articles/actualités/pages/témoignages/horaires
- Contrôle de publication depuis l’interface interne

---

## 17) Rôles et permissions (résumé)

Exemples de rôles métier:

- admin
- secretariat
- finance
- pasteur / ancien / diacre
- responsable_club
- responsable_groupe
- communication

Important:

- Certaines actions CRUD sont limitées par rôle.
- En cas d’accès refusé, vérifier le rôle du compte utilisateur.

---

## 18) Dépannage rapide

### Problèmes fréquents

- **Je ne vois pas un bouton CRUD**: vérifier le rôle utilisateur.
- **Lien vers admin au lieu de dashboard**: privilégier les pages `/app/...`.
- **Données non visibles**: vérifier filtres actifs et pagination.
- **Thème admin absent**: vérifier activation Jazzmin dans les settings.

### Vérifications techniques (équipe support)

- `manage.py check`
- Contrôle des URLs nommées
- Contrôle des templates avec liens cassés

---

## 19) Routines recommandées

### Quotidien

- Consulter dashboard
- Traiter notifications
- Suivre visites et sessions

### Hebdomadaire

- Mettre à jour événements et cultes
- Contrôler budgets/transactions
- Vérifier inventaire sensible

### Mensuel

- Export et archivage des rapports
- Revue des comptes inactifs
- Nettoyage des données obsolètes

---

## 20) Support

En cas de blocage fonctionnel:

1. Capturer l’URL et une capture d’écran.
2. Décrire l’action attendue et le résultat observé.
3. Transmettre au support technique avec le rôle utilisateur concerné.

---

## Annexe A – Raccourcis d’URL utiles

- Dashboard: `/app/`
- Membres: `/app/members/`
- Membres à visiter: `/app/members/visits/needed/`
- Classes club biblique: `/app/bibleclub/classes/`
- Inventaire: `/app/inventory/`
- Admin Jazzmin: `/admin/`

---

## Annexe B – Historique de ce guide

- 2026-02-14: édition complète Markdown + export DOCX

---

## 21) Procédures détaillées (SOP)

### 21.1 Intégrer un nouveau membre (de bout en bout)

1. Ouvrir `/app/members/` puis **Créer**.
2. Saisir identité, coordonnées, site, statut initial.
3. Vérifier l’unicité email/téléphone (éviter doublons).
4. Enregistrer, puis ouvrir la fiche détail.
5. Compléter les champs pastoraux (baptême, date d’arrivée, notes utiles).
6. Si nécessaire, rattacher à une famille (`/app/members/families/`).
7. Programmer un premier suivi pastoral (visite ou événement de vie).

Contrôles qualité:

- Fiche sans champs critiques manquants (nom, statut, site, contact).
- Rôle/accès utilisateur correspondant au besoin réel.
- Données sensibles uniquement dans les espaces prévus.

### 21.2 Traiter un événement de vie

1. Créer l’événement via `/app/members/life-events/create/`.
2. Marquer “nécessite visite” si besoin.
3. Planifier la visite via `/app/members/visits/create/`.
4. Réaliser la visite et passer le statut en **effectué**.
5. Renseigner compte-rendu, actions de suivi, confidentialité.
6. (Optionnel) Marquer l’annonce dominicale si applicable.

### 21.3 Organiser une session Club Biblique

1. Vérifier les classes (`/app/bibleclub/classes/`) et leurs effectifs.
2. Créer la session (`/app/bibleclub/sessions/create/`).
3. Prendre l’appel par classe.
4. Corriger les statuts (présent, absent, retard).
5. Vérifier les enfants nécessitant transport.
6. Contrôler le résumé de session (taux de présence).

### 21.4 Traiter une transaction financière

1. Créer la transaction dans `/app/finance/`.
2. Associer catégorie correcte et justificatif.
3. Vérifier montant, date, site et type (don/dépense).
4. Passer en statut validé après contrôle.
5. Vérifier impact sur dashboard finance et budgets.

### 21.5 Gérer un équipement inventaire

1. Créer ou ouvrir un équipement (`/app/inventory/`).
2. Renseigner état, quantité, emplacement, responsable.
3. Ajouter les informations d’achat si disponibles.
4. Mettre à jour à chaque mouvement majeur.
5. Contrôler l’historique des modifications en détail.

---

## 22) Matrice de rôles (opérationnelle)

> Cette matrice est un cadre métier. Les permissions réelles dépendent de la configuration du projet.

| Module | admin | secretariat | pasteur/ancien/diacre | finance | responsable_club | communication |
|---|---:|---:|---:|---:|---:|---:|
| Membres (CRUD) | ✅ | ✅ | 👁️ | ❌ | ❌ | ❌ |
| Familles | ✅ | ✅ | 👁️ | ❌ | ❌ | ❌ |
| Suivi pastoral | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Club Biblique | ✅ | 👁️ | 👁️ | ❌ | ✅ | ❌ |
| Finance | ✅ | 👁️ | ❌ | ✅ | ❌ | ❌ |
| Événements | ✅ | ✅ | 👁️ | ❌ | ❌ | ❌ |
| Inventaire | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Communication | ✅ | ✅ | 👁️ | ❌ | ❌ | ✅ |
| CMS Public | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ |

Légende: ✅ = gérer, 👁️ = consultation, ❌ = non autorisé

---

## 23) Checklists prêtes à l’emploi

### 23.1 Checklist ouverture de semaine

- Vérifier alertes dashboard (visites, rôles non confirmés, campagnes).
- Vérifier événements des 14 prochains jours.
- Vérifier sessions club biblique à venir.
- Vérifier actions financières en attente.
- Vérifier notifications critiques non lues.

### 23.2 Checklist fin de semaine

- Clôturer les visites pastorales effectuées.
- Compléter les événements de vie ouverts.
- Contrôler les absences répétées au club biblique.
- Réconcilier transactions validées + justificatifs.
- Exporter les synthèses nécessaires.

### 23.3 Checklist qualité des données

- Éviter doublons membres (email/téléphone).
- Contrôler statuts incohérents (actif/inactif).
- Vérifier familles sans chef de famille.
- Vérifier équipements sans responsable.
- Vérifier événements sans lieu/heure.

---

## 24) Guide express par profil

### 24.1 Secrétariat (routine)

- Matin: membres/familles, nouvelles inscriptions.
- Midi: annonces/événements de la semaine.
- Soir: vérification visites planifiées et rappels.

### 24.2 Pasteur / anciens / diacres

- Ouvrir `/app/` puis bloc suivi pastoral.
- Traiter `/app/members/visits/needed/`.
- Mettre à jour les comptes-rendus de visites.

### 24.3 Trésorerie

- Vérifier transactions en attente.
- Valider avec justificatifs.
- Contrôler budget et écarts.

### 24.4 Responsable Club Biblique

- Vérifier classes/effectifs.
- Préparer session + appel.
- Suivre présences et retards.

---

## 25) Navigation sans friction (anti-perte)

Principes:

- Depuis une fiche détail, toujours revenir via **Retour à la liste**.
- Éviter d’ouvrir le back-office admin pour les opérations quotidiennes.
- Utiliser le menu latéral plutôt que l’historique navigateur quand possible.

Points déjà sécurisés:

- Fiche membre: retour liste présent.
- Détail classe biblique: retour liste présent.
- Détail équipement inventaire: retour liste présent (haut et bas).

---

## 26) Dépannage avancé (support interne)

### 26.1 Symptôme: bouton/action manquant

Causes probables:

- Rôle insuffisant
- Statut utilisateur inactif
- Contexte d’objet non compatible (ex: élément supprimé)

Actions:

1. Vérifier le rôle réel du compte.
2. Vérifier l’état actif du compte.
3. Vérifier l’URL et les paramètres.

### 26.2 Symptôme: lien renvoie vers admin

Actions:

1. Remplacer vers route interne `/app/...`.
2. Vérifier le nom d’URL Django (`reverse`/`url`).
3. Tester navigation depuis dashboard.

### 26.3 Symptôme: texte de template affiché brut (`{{ ... }}`)

Cause fréquente:

- Expression template cassée ou mal fermée.

Actions:

1. Contrôler la syntaxe du template.
2. Vérifier que les expressions sont bien formées.
3. Recharger la page et confirmer rendu HTML final.

---

## 27) Gouvernance et sécurité des données

Règles:

- Ne pas exporter des données sensibles sans besoin métier.
- Limiter les comptes admin aux personnes autorisées.
- Utiliser des mots de passe robustes et uniques.
- Activer la 2FA pour les rôles sensibles.
- Nettoyer périodiquement les comptes inactifs.

Conservation recommandée:

- Logs opérationnels: conservation selon politique interne.
- Exports: archivage structuré avec date + version.

---

## 28) Plan de formation (suggestion)

### Jour 1 (2h)

- Connexion, navigation, dashboard
- CRUD membres/familles

### Jour 2 (2h)

- Suivi pastoral
- Club biblique

### Jour 3 (2h)

- Finance et inventaire
- Communication et CMS

Évaluation:

- Chaque utilisateur exécute 3 scénarios complets sans assistance.

---

## 29) Annexes techniques utiles

### 29.1 Commandes de vérification (équipe technique)

- `python manage.py check`
- Audit URL/templates si besoin

### 29.2 Convention interne de tickets

Pour chaque incident:

- URL complète
- Profil utilisateur
- Étapes de reproduction
- Résultat attendu / résultat observé
- Capture écran + horodatage

---

## 30) Conclusion

Ce guide est la référence opérationnelle pour utiliser Gestion EEBC en production.

Objectif final:

- Opérations quotidiennes fluides
- Données fiables
- Navigation 100% orientée dashboard
- Réduction des erreurs et du support réactif

