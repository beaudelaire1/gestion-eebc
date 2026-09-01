# Suivi post-migration — OVH + Coolify

Dernière mise à jour : 1er septembre 2026
Contexte : migration de Render vers OVH + Coolify terminée, ressources Render supprimées.

Cette liste recense ce qui reste ouvert après la migration. Elle ne remplace pas
`PRODUCTION_CHECKLIST_COOLIFY.md`, qui décrit la recette d'un déploiement.

## 1. Continuité des données

Les sauvegardes OVH couvrent la machine. Elles ne couvrent pas les mêmes pannes qu'une
sauvegarde logique de la base :

| Panne | Sauvegarde OVH | Dump PostgreSQL |
|---|---|---|
| Disque ou VPS perdu | oui | non (si le dump est sur le VPS) |
| Suppression accidentelle de quelques enregistrements | restauration de toute la machine | restauration ciblée |
| Corruption logique détectée tardivement | selon la rétention | selon la rétention |
| Perte du compte OVH ou incident régional | non | oui si copie hors fournisseur |

Un instantané pris sur une base en fonctionnement est cohérent au niveau du crash, pas de la
transaction : PostgreSQL rejoue son journal au démarrage et s'en sort presque toujours, mais ce
n'est pas équivalent à un `pg_dump`.

- [ ] noter la nature exacte de la sauvegarde OVH utilisée : snapshot manuel ou sauvegarde
      automatisée, fréquence, rétention ;
- [ ] activer en complément la sauvegarde PostgreSQL de Coolify sur la ressource base de
      données (dump quotidien) ;
- [ ] configurer la copie vers un stockage S3 compatible, hors du VPS et si possible hors OVH ;
- [ ] **restaurer une fois** dans une base isolée et vérifier les comptages : une sauvegarde
      jamais restaurée est une hypothèse, pas une sauvegarde ;
- [ ] sortir du VPS ou supprimer `/root/render_eebc.dump` et `/root/coolify_avant_restore.dump`,
      qui contiennent les données personnelles de 205 personnes en clair.

## 2. Fonctions possiblement à l'arrêt

Le cron `eebc-daily-notifications` a disparu avec Render. Sans équivalent Coolify, les
anniversaires, rappels d'événements et alertes d'absence ne partent plus — silencieusement.

- [ ] vérifier l'existence d'une Scheduled Task Coolify `python manage.py run_notifications --all` ;
- [ ] vérifier le fuseau retenu (section 12 de `DEPLOY_COOLIFY.md`) ;
- [ ] l'exécuter une fois via *Execute Now* et contrôler les logs.

## 3. Infrastructure

- [ ] **certificat Let's Encrypt** : Cloudflare parle à l'origine sur un certificat auto-signé.
      Nuage gris → `docker restart coolify-proxy` → vérifier l'émission → nuage orange en
      **Full (strict)**. Jamais `Flexible` : boucle de redirection garantie ;
- [ ] **filtrer le port 443** sur les plages Cloudflare. Sans cela, `CF-Connecting-IP` est
      falsifiable en visant directement l'IP du VPS, et le rate limiting contournable ;
- [ ] renseigner `CHURCH_PHONE` dans Coolify : sans lui, les documents n'affichent que
      l'adresse et l'email.

## 4. Intégration continue

Les workflows GitHub échouent en quelques secondes : *account is locked due to a billing issue*.
Aucun test ne s'exécute automatiquement depuis plusieurs jours.

- [ ] régler la facturation GitHub ;
- [ ] vérifier que la suite complète passe en CI, pas seulement en local.

Les garde-fous ajoutés le 1er septembre 2026 ne protègent réellement qu'une fois la CI rétablie :
graphe de migrations sans doublon, références statiques résolvables, identité de l'organisme sur
les documents externes, séparation des canaux email et WhatsApp.

## 5. WhatsApp

La chaîne technique est validée de bout en bout (envoi réel reçu le 1er septembre 2026). Ce qui
reste ne relève pas du code — voir `docs/WHATSAPP_SETUP.md`.

- [ ] créer et faire approuver le modèle `eebc_annonce` (trois variables : nom, titre, contenu) ;
- [ ] obtenir un numéro dédié à l'église et enregistrer un moyen de paiement ;
- [ ] **collecter les numéros et le consentement** : 0 membre sur 205 possède un `whatsapp_number`.
      Ne pas recopier le champ `phone` en masse — `notify_by_whatsapp` matérialise un accord, et
      Meta sanctionne les comptes dont les destinataires signalent les messages.

Arbitrage budgétaire à poser : une conversation *Marketing* est facturée par destinataire. Pour
205 membres, une annonce diffusée se compte en dizaines d'euros. L'email reste gratuit et
illimité : garder WhatsApp pour le rare et l'urgent.

## 6. Dette technique repérée

- [ ] **chemin Twilio mort** dans `apps/communication/notification_service.py` : une seconde
      implémentation WhatsApp jamais configurée nulle part ;
- [ ] **limite de 1024 caractères** des modèles WhatsApp : une annonce longue est rejetée par
      Meta pour toute la liste. Tronquer et renvoyer vers le site ;
- [ ] **statuts de livraison ignorés** : le webhook les reçoit et les jette, donc `SMSLog`
      affiche `sent` pour un message jamais délivré ;
- [ ] **commit `b32d820`** : le nettoyage Render y a emporté une soixantaine de fichiers de
      travail en cours. À séparer si l'historique doit rester lisible.

## 7. Produit

L'option *Public* des annonces alimente désormais une section de la page d'accueil. À surveiller
au premier usage réel : c'est la seule des trois visibilités dont l'effet sort de l'application.
