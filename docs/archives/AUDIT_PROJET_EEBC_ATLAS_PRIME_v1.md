# Audit Report

## 1. Lecture strategique
- Objet de l'audit : etablir un etat des lieux technique exploitable du projet EEBC en suivant le cadre ATLAS PRIME.
- Perimetre : configuration Django, routage, architecture des applications, securite applicative, API mobile, strategie de test et pipeline de livraison.
- Niveau de risque : moyen avec plusieurs points importants et un point critique sur la securite effectivement appliquee.
- Point de vigilance dominant : ecart entre les mecanismes declares, les validations executees et les garanties reellement actives.

## 2. Contexte observe
- Stack identifiee : Django 4.2, HTMX, Django REST Framework, Jazzmin, WeasyPrint, Celery optionnel, WhiteNoise, PostgreSQL en production et SQLite en developpement/test. Voir [requirements/base.txt](requirements/base.txt), [gestion_eebc/settings/base.py](gestion_eebc/settings/base.py), [gestion_eebc/settings/prod.py](gestion_eebc/settings/prod.py).
- Points d'entree lus : [manage.py](manage.py), [gestion_eebc/urls.py](gestion_eebc/urls.py), [gestion_eebc/settings/base.py](gestion_eebc/settings/base.py), [gestion_eebc/settings/dev.py](gestion_eebc/settings/dev.py), [gestion_eebc/settings/prod.py](gestion_eebc/settings/prod.py), [gestion_eebc/settings/test.py](gestion_eebc/settings/test.py).
- Conventions observees : decoupage modulaire sous [apps](apps), separation public/app/api dans [gestion_eebc/urls.py](gestion_eebc/urls.py), forte presence de documentation racine et de tests a la racine du depot.
- Deploiement observe : Render via [render.yaml](render.yaml), scripts [build.sh](build.sh) et [start.sh](start.sh), CI GitHub Actions via [.github/workflows/tests.yml](.github/workflows/tests.yml), [.github/workflows/code-quality.yml](.github/workflows/code-quality.yml) et [.github/workflows/deploy.yml](.github/workflows/deploy.yml).
- Hypotheses eventuelles : les integrations Stripe, Twilio, Hostinger et Sentry ne sont actives qu'en fonction des variables d'environnement de production.

## 3. Points forts reels
- Architecture modulaire lisible. Le projet isole bien les domaines metier sous [apps](apps) et garde un routage global clair dans [gestion_eebc/urls.py](gestion_eebc/urls.py).
- Separation des environnements propre. La configuration est decoupee entre base, developpement, production et test dans [gestion_eebc/settings](gestion_eebc/settings), ce qui facilite l'exploitation.
- Reflexes securite deja presents. Le projet integre un utilisateur personnalise avec roles et 2FA dans [apps/accounts/models.py](apps/accounts/models.py), un middleware de timeout et un rate limiting dans [apps/core/middleware.py](apps/core/middleware.py), ainsi qu'une API JWT dans [apps/api/auth_views.py](apps/api/auth_views.py).
- Parcours applicatifs bien distincts. Le site public, l'application interne et l'API mobile sont separes dans [gestion_eebc/urls.py](gestion_eebc/urls.py), ce qui reduit le couplage de navigation.
- Base de delivery existante. Le projet dispose de checks de sante dans [apps/core/health.py](apps/core/health.py), d'un blueprint Render dans [render.yaml](render.yaml) et de workflows CI/CD deja poses dans [.github/workflows](.github/workflows).
- Presence de vrais tests applicatifs sur certaines zones. Les modules [apps/api/tests.py](apps/api/tests.py) et [apps/members/tests.py](apps/members/tests.py) montrent une base de tests plus structurée.

## 4. Problemes identifies
### Critiques
- Probleme : les politiques CSP et Permissions Policy semblent declarees mais non appliquees reellement.
- Impact : faux sentiment de protection sur le front public et l'application interne, avec risque que certaines defenses attendues n'existent pas en production.
- Cause probable : des reglages CSP et Permissions Policy sont declares dans [gestion_eebc/settings/base.py#L158](gestion_eebc/settings/base.py#L158) et [gestion_eebc/settings/base.py#L185](gestion_eebc/settings/base.py#L185), mais aucune dependance type django-csp n'est declaree dans [requirements/base.txt](requirements/base.txt) et aucun middleware CSP n'a ete verifie dans la pile.
- Correction prioritaire : soit brancher une implementation reelle des headers de securite, soit retirer les reglages inertes pour eviter l'ambiguite, puis valider les en-tetes HTTP en environnement de staging.

### Importants
- Probleme : la strategie de tests automatisee n'est pas completement coherente avec la production.
- Impact : des regressions liees a PostgreSQL peuvent passer inaperçues, alors que la production est configuree pour Postgres.
- Cause probable : la CI provisionne un service Postgres dans [.github/workflows/tests.yml#L14](.github/workflows/tests.yml#L14) et exporte une DATABASE_URL dans [.github/workflows/tests.yml#L63](.github/workflows/tests.yml#L63), mais les tests utilisent SQLite memoire dans [gestion_eebc/settings/test.py#L16](gestion_eebc/settings/test.py#L16).
- Correction recommandee : aligner la configuration de test CI sur PostgreSQL pour au moins un job, ou supprimer le service inutile si le choix SQLite est assume.

- Probleme : la base de tests melange tests pytest et scripts de validation ad hoc.
- Impact : lisibilite reduite, automatisation plus fragile, et risque de surestimer la couverture reelle.
- Cause probable : coexistence de vrais tests dans [apps/api/tests.py#L38](apps/api/tests.py#L38) et [apps/members/tests.py#L10](apps/members/tests.py#L10) avec des scripts orientes shell ou console comme [test_bug_fixes.py#L4](test_bug_fixes.py#L4), [test_bug_fixes.py#L15](test_bug_fixes.py#L15) et [test_all_crud_operations.py#L190](test_all_crud_operations.py#L190).
- Correction recommandee : separer strictement les scripts de verification manuelle des tests collectes par pytest, et normaliser la suite dans apps ou un dossier tests dedie.

- Probleme : certaines fonctionnalites finance ont encore des placeholders ou une chaine de livraison incomplete.
- Impact : risque de non-conformite documentaire et d'experience degradee sur les recus fiscaux et les notifications associees.
- Cause probable : identifiants administratifs placeholder dans [apps/finance/pdf_service.py#L33](apps/finance/pdf_service.py#L33) et [apps/finance/pdf_service.py#L34](apps/finance/pdf_service.py#L34), envoi de recu sans piece jointe dans [apps/finance/models.py#L793](apps/finance/models.py#L793).
- Correction recommandee : externaliser les identifiants legaux en configuration metier, joindre effectivement le PDF au message, puis valider le parcours de bout en bout.

- Probleme : le pipeline de build tolere explicitement un echec de construction Docker.
- Impact : la CI peut afficher un resultat vert alors qu'une etape de build est invalide ou inexistante.
- Cause probable : la commande de build est suffixee par un contournement dans [.github/workflows/tests.yml#L140](.github/workflows/tests.yml#L140), alors qu'aucun Dockerfile n'a ete trouve a la racine du depot.
- Correction recommandee : soit retirer cette etape si Docker n'est pas une cible de livraison, soit fournir un Dockerfile et rendre l'etape bloquante.

### Mineurs
- Probleme : le depot contient une volumetrie documentaire tres elevee avec plusieurs syntheses de corrections et de livrables.
- Impact : onboarding plus diffus, difficultes a identifier la source de verite documentaire.
- Correction possible : consolider la documentation principale autour d'un index unique et de quelques documents de reference stables.

- Probleme : l'environnement Python local configure n'inclut pas les dependances de developpement attendues.
- Impact : verification locale incomplete sans preparation supplementaire.
- Cause probable : [requirements/dev.txt#L16](requirements/dev.txt#L16) declare pytest mais le smoke test local n'a pas pu s'executer car le venv courant ne contient pas pytest.
- Correction possible : documenter une commande d'installation standard pour le mode developpement et verifier l'etat du venv avant execution des tests.

- Probleme : les notifications push sont annoncees mais non implementees.
- Impact : fonctionnalite partielle cote communication mobile.
- Cause probable : placeholder explicite dans [apps/communication/notification_service.py#L233](apps/communication/notification_service.py#L233).
- Correction possible : soit implementer le canal push, soit le retirer du discours produit et de la surface fonctionnelle exposee.

## 5. Analyse transversale
### Securite
- Point fort : timeout de session, rate limiting, roles et 2FA sont presents dans [apps/core/middleware.py](apps/core/middleware.py) et [apps/accounts/models.py](apps/accounts/models.py).
- Point faible : une partie des headers de securite semble declarative plutot qu'operationnelle, et Django signale logiquement dans le check de deploiement que [gestion_eebc/settings/prod.py#L30](gestion_eebc/settings/prod.py#L30) laisse SECURE_SSL_REDIRECT a False. Dans ce cas precis, le commentaire de [gestion_eebc/settings/prod.py#L28](gestion_eebc/settings/prod.py#L28) montre toutefois une decision consciente liee a Render.

### Performance
- Point fort : cache, health checks et separation des parcours existent. Voir [apps/core/health.py](apps/core/health.py) et [gestion_eebc/settings/prod.py](gestion_eebc/settings/prod.py).
- Point faible : le projet reste sur rendu serveur classique avec beaucoup de surface HTML et de nombreuses apps, ce qui augmente le risque de duplication de logique et de vues lourdes a mesure que le perimetre grossit.

### Maintenabilite
- Point fort : le decoupage par domaines metier est lisible et la convention apps reste globalement stable.
- Point faible : coexistence de nombreuses vues specialisees, de scripts de validation ad hoc et d'une documentation tres dispersée, ce qui complique la source de verite.

### Accessibilite / UX
- Point fort : la separation site public / backoffice / mobile laisse de la place pour adapter les parcours selon les usages.
- Limite : l'audit n'a pas inclus de revue front exhaustive ni d'analyse DOM/ARIA sur les templates, donc la conclusion UX/accessibilite reste partielle.

### Delivery / Ops
- Point fort : presence conjointe de Render, WhiteNoise, health checks, logs console et workflows GitHub Actions.
- Point faible : les controles de build ne sont pas entierement credibles tant qu'une partie reste non bloquante ou alignee sur un artefact absent.

## 6. Priorisation recommandee
1. Rendre effectives et verifiables les protections de securite HTTP annoncees, puis valider les headers en staging.
2. Aligner la strategie de tests sur la realite de production en separant scripts manuels et tests pytest, et en faisant tourner au moins un job Postgres reel.
3. Finaliser les parcours finance sensibles, en particulier les recus fiscaux PDF et leur envoi complet, avant de qualifier ces fonctions comme stabilisees.

## 7. Livraison
- Resume executable : EEBC est un projet Django modulaire deja avance, avec un vrai socle applicatif, une couverture fonctionnelle large et des bases de securite/delivery solides. Le projet n'est pas desorganise, mais il souffre de quelques ecarts entre ce qui est declare et ce qui est effectivement garanti, surtout sur la securite front et la fiabilite de la validation continue.
- Risques residuels : absence de verification complete de la suite de tests locale dans l'environnement courant, pas de revue exhaustive template par template, pas de validation dynamique des headers HTTP en staging.
- Etape suivante recommandee : traiter les 3 priorites ci-dessus, puis executer un audit de verification cible apres corrections sur securite, CI et flux finance.