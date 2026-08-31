# Déploiement EEBC — OVH + Coolify

Dernière mise à jour : 31 août 2026  
Branche de migration : `coolify-migration`  
Branche cible après validation : `develop`

## 1. Architecture cible

La production est composée de ressources indépendantes :

- application Git Coolify basée sur `docker-compose.coolify.yml` ;
- service `web` Django/Gunicorn ;
- service `worker` Celery ;
- service one-shot `migrate` exécuté avant `web` et `worker` ;
- PostgreSQL géré comme ressource Database Coolify ;
- Redis géré comme ressource séparée Coolify ;
- médias sur Cloudinary ou stockage S3 compatible ;
- tâche planifiée Coolify pour `run_notifications` ;
- sauvegardes PostgreSQL Coolify avec copie S3 hors serveur.

PostgreSQL et Redis ne sont volontairement pas inclus dans le Compose applicatif : un redéploiement du code ne doit pas recréer ou coupler le cycle de vie des données au cycle de vie de l'application.

## 2. Fichiers de référence

- `Dockerfile` : image Python 3.13.15 + dépendances système WeasyPrint ;
- `docker-compose.coolify.yml` : web, worker et migration ;
- `gestion_eebc/settings/prod.py` : invariants de production ;
- `start.sh` : préflight Django puis Gunicorn ;
- `.env.example` : catalogue des variables ;
- `/healthz/ping/` : liveness sans dépendance externe.

`render.yaml` reste temporairement dans le dépôt uniquement comme référence de rollback pendant la migration. Il ne doit pas être utilisé comme source de vérité Coolify.

## 3. Créer PostgreSQL dans Coolify

Créer une ressource PostgreSQL dédiée dans le même projet/environnement Coolify. PostgreSQL 17 convient à la migration actuelle.

Après démarrage :

1. vérifier que la base est `healthy` ;
2. récupérer l'URL interne PostgreSQL ;
3. l'enregistrer dans l'application sous `DATABASE_URL` ;
4. ne pas exposer PostgreSQL publiquement sauf besoin d'administration explicitement contrôlé.

Exemple de forme attendue :

```text
postgresql://USER:PASSWORD@HOST_INTERNE:5432/eebc
```

## 4. Créer Redis dans Coolify

Créer une ressource Redis dédiée, privée, dans le même environnement.

Renseigner son URL interne dans :

```text
REDIS_URL
```

Le Compose réutilise automatiquement cette URL comme broker et backend Celery.

## 5. Réseau entre ressources Coolify

Une application Docker Compose et des ressources PostgreSQL/Redis créées séparément ne partagent pas automatiquement le même réseau applicatif.

Activer **Connect to Predefined Network** pour la stack applicative afin qu'elle puisse joindre les ressources internes Coolify. Utiliser ensuite les noms/URLs internes complets fournis par Coolify pour PostgreSQL et Redis.

Ne pas résoudre ce problème en exposant PostgreSQL ou Redis publiquement.

## 6. Créer l'application Git

Dans Coolify :

1. créer une nouvelle ressource depuis le dépôt GitHub `beaudelaire1/gestion-eebc` ;
2. sélectionner temporairement la branche `coolify-migration` pour la recette ;
3. choisir le build pack `Docker Compose` ;
4. définir `docker-compose.coolify.yml` comme emplacement du Compose ;
5. activer **Connect to Predefined Network** ;
6. charger la définition ;
7. vérifier que Coolify détecte `migrate`, `web` et `worker` ;
8. rendre public uniquement le service `web`.

Le service public écoute en interne sur le port `8000`. Dans le champ Domains du service web, cibler le port interne, par exemple :

```text
https://eglise-ebc.org:8000
```

Ajouter `www.eglise-ebc.org` uniquement si ce nom doit également être servi par cette application.

## 7. Variables obligatoires

Minimum de démarrage :

```text
SECRET_KEY=<secret stable >= 32 caractères>
ALLOWED_HOSTS=eglise-ebc.org,www.eglise-ebc.org
CSRF_TRUSTED_ORIGINS=https://eglise-ebc.org,https://www.eglise-ebc.org
DATABASE_URL=<URL PostgreSQL interne Coolify>
REDIS_URL=<URL Redis interne Coolify>
TRUSTED_PROXY_IPS=<CIDR réel du réseau/proxy Traefik>
SITE_URL=https://eglise-ebc.org
SITE_NAME=EEBC
```

Ne jamais utiliser :

```text
TRUSTED_PROXY_IPS=0.0.0.0/0
TRUSTED_PROXY_IPS=::/0
```

Pour identifier le subnet réellement utilisé par le proxy Docker/Coolify, inspecter les réseaux Docker du serveur OVH puis renseigner uniquement le réseau nécessaire. Ne pas recopier un CIDR d'exemple sans le vérifier sur le serveur.

`GUNICORN_FORWARDED_ALLOW_IPS=*` est acceptable dans cette architecture parce que le port 8000 n'est pas publié sur l'hôte : Gunicorn n'est accessible que depuis le réseau Docker/proxy. La confiance dans l'adresse IP cliente reste, elle, contrôlée séparément par `TRUSTED_PROXY_IPS` dans Django.

## 8. Stockage média

### Option A — conserver Cloudinary

```text
MEDIA_STORAGE_BACKEND=cloudinary
CLOUDINARY_URL=cloudinary://API_KEY:API_SECRET@CLOUD_NAME
```

Cette option minimise le changement pendant la migration d'hébergeur.

### Option B — OVH Object Storage / S3 compatible

```text
MEDIA_STORAGE_BACKEND=s3
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_STORAGE_BUCKET_NAME=...
AWS_S3_ENDPOINT_URL=https://...
AWS_S3_REGION_NAME=...
AWS_S3_ADDRESSING_STYLE=path
AWS_LOCATION=media
```

`AWS_S3_CUSTOM_DOMAIN` est facultatif.

Le backend S3 utilise des URLs signées par défaut et n'écrase pas un fichier existant portant le même nom.

Avant de basculer de Cloudinary vers S3, migrer les médias existants et vérifier les URLs utilisées par les documents déjà enregistrés. Ne pas changer simplement la variable de backend si des fichiers historiques existent uniquement sur Cloudinary.

## 9. Email et intégrations

Configurer au minimum si l'envoi email est utilisé :

```text
EMAIL_BACKEND=hostinger
HOSTINGER_EMAIL_HOST=smtp.hostinger.com
HOSTINGER_EMAIL_PORT=587
HOSTINGER_EMAIL_USE_TLS=True
HOSTINGER_EMAIL_HOST_USER=...
HOSTINGER_EMAIL_HOST_PASSWORD=...
DEFAULT_FROM_EMAIL=EEBC <contact@eglise-ebc.org>
```

Ajouter ensuite les secrets Stripe, Meta WhatsApp, Turnstile et Sentry uniquement pour les fonctions réellement activées.

## 10. Migrations

À chaque déploiement, le service one-shot `migrate` exécute :

```bash
python manage.py migrate --noinput
python manage.py migrate --check
python manage.py setup_sites
```

`web` et `worker` ne démarrent que si `migrate` termine avec succès.

Les migrations ne sont jamais exécutées pendant la construction de l'image Docker.

## 11. Fichiers statiques et PDF

Le `Dockerfile` :

1. installe `requirements/prod.txt` ;
2. exécute `pip check` ;
3. installe les bibliothèques système Pango/Harfbuzz nécessaires à WeasyPrint ;
4. génère un PDF de contrôle ;
5. exécute le contrôle Django avec `settings.build` ;
6. exécute `collectstatic` avec `settings.build`.

Une erreur WeasyPrint ou `collectstatic` doit donc faire échouer le build.

## 12. Tâche quotidienne de notifications

Ne pas lancer Celery Beat pendant la première migration : le fichier `gestion_eebc/celery.py` contient d'autres tâches historiques, dont des tâches de backup local qui n'ont pas encore été validées pour la nouvelle infrastructure.

Créer dans Coolify une Scheduled Task ciblant le conteneur `web` :

```text
Commande : python manage.py run_notifications --all
```

Si le serveur OVH/Coolify reste en UTC :

```text
0 10 * * *
```

correspond à 07:00 en Guyane.

Si le serveur est explicitement configuré en `America/Cayenne`, utiliser :

```text
0 7 * * *
```

Vérifier le timezone réel du serveur avant d'enregistrer la tâche, puis utiliser `Execute Now` une première fois pour vérifier la commande.

## 13. Sauvegardes PostgreSQL

Utiliser les sauvegardes moteur PostgreSQL de Coolify, pas une archive du volume Docker et pas la commande historique `backup_db` comme unique sauvegarde.

Configuration minimale recommandée :

- dump PostgreSQL quotidien ;
- rétention locale courte ;
- copie vers un stockage S3 compatible hors du VPS ;
- rétention distante supérieure à la rétention locale ;
- test de restauration dans une base isolée avant validation de production.

Une sauvegarde réussie sans test de restauration ne constitue pas une preuve de récupérabilité.

## 14. Vérifications avant bascule DNS

Le déploiement de recette doit valider au minimum :

```text
/healthz/ping/            -> 200
/healthz/lite/            -> DB + Redis sains
```

Puis vérifier :

- page publique ;
- login/logout ;
- session sur plusieurs requêtes ;
- permissions et 2FA ;
- lecture/écriture PostgreSQL ;
- Redis/rate limiting ;
- upload puis relecture d'un média ;
- génération PDF réelle ;
- envoi email réel ;
- exécution d'une tâche Celery ;
- `run_notifications --all` via Scheduled Task ;
- Stripe/Meta uniquement si les intégrations sont activées ;
- redémarrage du web sans perte de données ;
- sauvegarde PostgreSQL puis restauration isolée.

## 15. Bascule

Ne modifier le DNS de `eglise-ebc.org` qu'après validation de recette.

Ordre recommandé :

1. réduire temporairement le TTL DNS si nécessaire ;
2. sauvegarder la base source ;
3. arrêter les écritures sur l'ancien environnement pendant la copie finale ;
4. restaurer/importer PostgreSQL sur Coolify ;
5. migrer les médias si le backend change ;
6. lancer les contrôles de cohérence ;
7. basculer le DNS ;
8. surveiller logs, healthchecks, emails et worker ;
9. conserver Render disponible pendant la fenêtre de rollback définie.

## 16. Critère de validation

OVH + Coolify est déclaré prêt uniquement lorsque :

1. l'image Docker se construit ;
2. `migrate` réussit ;
3. `web` reste healthy ;
4. le worker Celery reste actif ;
5. les parcours critiques sont vérifiés ;
6. le stockage média persiste ;
7. une sauvegarde PostgreSQL est créée et restaurée avec succès ;
8. la tâche quotidienne est exécutée au bon fuseau ;
9. le déploiement depuis GitHub fonctionne après un nouveau commit.
