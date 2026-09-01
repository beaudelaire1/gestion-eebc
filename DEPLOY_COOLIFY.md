# Déploiement EEBC — OVH + Coolify

Dernière mise à jour : 1er septembre 2026
Branche suivie : `develop`
Révision de recette : noter le SHA du commit déployé avant chaque validation

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
- `migrate.sh` : préflight du service one-shot `migrate` puis migrations ;
- `.env.example` : catalogue des variables ;
- `/healthz/ping/` : liveness sans dépendance externe.

`render.yaml` reste temporairement dans le dépôt uniquement comme référence de rollback pendant la migration. Il ne doit pas être utilisé comme source de vérité Coolify.

## 3. Créer PostgreSQL dans Coolify

Créer une ressource PostgreSQL dédiée dans le même projet/environnement Coolify.

Choisir une version **au moins égale** à celle de la base à reprendre : un dump ne se restaure jamais vers une version majeure antérieure. La migration de septembre 2026 a été faite en 18.6 des deux côtés.

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

Activer **Connect to Predefined Network** des deux côtés : sur la stack applicative *et* sur les ressources PostgreSQL et Redis. Une ressource base de données Coolify reste sinon isolée sur son propre réseau, et le nom d'hôte interne ne se résout pas depuis les conteneurs de l'application. Utiliser ensuite les noms/URLs internes complets fournis par Coolify pour PostgreSQL et Redis.

Ne pas résoudre ce problème en exposant PostgreSQL ou Redis publiquement.

## 6. Créer l'application Git

Dans Coolify :

1. créer une nouvelle ressource depuis le dépôt GitHub `beaudelaire1/gestion-eebc` ;
2. sélectionner la branche `develop` et noter le SHA exact utilisé pour la recette ;
3. choisir le build pack `Docker Compose` ;
4. définir `docker-compose.coolify.yml` comme emplacement du Compose ;
5. activer **Connect to Predefined Network** ;
6. charger la définition ;
7. vérifier que Coolify détecte `migrate`, `web` et `worker` ;
8. rendre public uniquement le service `web`.

Le service public écoute en interne sur le port `8000`. Selon la version de Coolify, le champ Domains attend soit `https://eglise-ebc.org:8000`, soit le seul domaine — le gestionnaire de domaines récent déduit le port depuis le `expose` du Compose. Vérifier dans les deux cas que le routeur généré fonctionne (voir l'annexe).

Saisir les domaines à la main : un copier-coller depuis un client qui transforme les URL en liens injecte du markdown dans la règle Traefik.

## 7. Variables obligatoires

Minimum de démarrage :

```text
SECRET_KEY=<secret stable >= 32 caractères>
ALLOWED_HOSTS=eglise-ebc.org,www.eglise-ebc.org
CSRF_TRUSTED_ORIGINS=https://eglise-ebc.org,https://www.eglise-ebc.org
DATABASE_URL=<URL PostgreSQL interne Coolify>
REDIS_URL=<URL Redis interne Coolify>
TRUSTED_PROXY_IPS=<CIDR réel du réseau/proxy Traefik>
MEDIA_STORAGE_BACKEND=cloudinary
CLOUDINARY_URL=cloudinary://API_KEY:API_SECRET@CLOUD_NAME
SITE_URL=https://eglise-ebc.org
SITE_NAME=EEBC
```

La configuration média fait partie du minimum de démarrage : `settings.prod` la valide à
l'import, donc une variable média absente fait échouer `migrate`, `web` et `worker` avant
toute connexion à PostgreSQL. Voir la section 8 pour l'alternative S3.

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

À chaque déploiement, le service one-shot `migrate` exécute `migrate.sh` :

1. contrôle des variables obligatoires, y compris la configuration média ;
2. attente bornée de PostgreSQL (`MIGRATE_DB_WAIT_SECONDS`, 90 s par défaut) ;
3. contrôle d'accès à Redis ;
4. `python manage.py migrate --noinput` ;
5. `python manage.py migrate --check` ;
6. `python manage.py setup_sites`, **uniquement si aucun `Site` n'existe**.

Le seed est conditionnel parce qu'il force adresse, téléphone, email et horaires avec des valeurs codées en dur : le rejouer sur une base peuplée effacerait toute modification faite depuis l'admin.

`web` et `worker` ne démarrent que si `migrate` termine avec succès.

Les migrations ne sont jamais exécutées pendant la construction de l'image Docker.

### Diagnostiquer un échec de `migrate`

Coolify lance `docker compose up -d` : le journal de déploiement n'affiche que
`service "migrate" didn't complete successfully: exit 1`, jamais la sortie du conteneur.
La cause réelle est dans les logs du conteneur, qui reste présent après l'échec :

```bash
docker logs "$(docker ps -a --filter name=migrate- --format '{{.Names}}' | head -n1)"
```

`migrate.sh` y écrit une ligne `ERREUR MIGRATION EEBC:` nommant la variable manquante ou
la dépendance injoignable.

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

## 15. Reprise des données depuis l'ancien hébergeur

### Repérer les noms réels

Coolify nomme le conteneur d'une ressource base de données d'après son **UUID**, pas d'après
« postgres ». La base applicative elle-même porte le nom `postgres`, base de maintenance par
défaut de l'image. Relever les noms avant toute commande :

```bash
docker ps -a --format '{{.Names}} {{.Status}}'
```

### Vérifier les versions

Un dump ne se restaure jamais vers une version majeure antérieure. Comparer source et cible
avant de commencer :

```bash
docker exec <CONTENEUR_PG> sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SHOW server_version"'
```

Si la source est plus récente que la cible, recréer la ressource PostgreSQL Coolify dans la
bonne version — opération indolore tant que la base cible ne contient que des données de seed,
impossible une fois les données réelles importées.

### Suspendre les écritures à la source

Avant la copie finale, suspendre le service web **et les tâches planifiées** de l'ancien
hébergeur. Un cron de notifications resté actif continue d'écrire dans la base et d'envoyer des
messages aux membres.

### Dump

Lancer `pg_dump` depuis le conteneur PostgreSQL de destination, pour que la version du client
corresponde à celle du serveur cible :

```bash
docker exec <CONTENEUR_PG> pg_dump --no-owner --no-privileges -Fc "<URL_EXTERNE_SOURCE>?sslmode=require" > /root/source.dump
```

Contrôler le contenu, pas seulement la taille du fichier :

```bash
docker exec -i <CONTENEUR_PG> pg_restore --list < /root/source.dump | grep -c "TABLE DATA"
```

### Restauration

Sauvegarder d'abord la base actuelle :

```bash
docker exec <CONTENEUR_PG> sh -c 'pg_dump --no-owner --no-privileges -Fc -U "$POSTGRES_USER" "$POSTGRES_DB"' > /root/avant_restore.dump
```

Arrêter l'application pour qu'aucune connexion ne se rouvre pendant la bascule :

```bash
docker stop <CONTENEUR_WEB> <CONTENEUR_WORKER>
```

Vider le schéma. Ne pas tenter `DROP DATABASE` : la base applicative s'appelant `postgres`, elle
est ouverte par la connexion courante et le serveur refuse.

```bash
docker exec <CONTENEUR_PG> sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "DROP SCHEMA public CASCADE" -c "CREATE SCHEMA public" -c "GRANT ALL ON SCHEMA public TO \"$POSTGRES_USER\"" -c "GRANT ALL ON SCHEMA public TO public"'
```

Restaurer :

```bash
docker exec -i <CONTENEUR_PG> sh -c 'pg_restore --no-owner --no-privileges -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < /root/source.dump
```

Redéployer ensuite depuis Coolify plutôt que de relancer les conteneurs à la main : le service
`migrate` doit rejouer son préflight sur la base restaurée.

### Vérifier

```bash
docker exec <CONTENEUR_WEB> python manage.py shell -c "from apps.members.models import Member; print(Member.objects.count())"
```

Trois points à connaître :

- **les sessions restaurées sont invalides** : elles sont signées avec le `SECRET_KEY` de
  l'ancien environnement. Les empreintes de mots de passe, elles, restent valides ;
- **les médias suivent sans action** tant que `CLOUDINARY_URL` et `MEDIA_STORAGE_BACKEND` sont
  inchangés : la base ne stocke que des chemins ;
- **les fichiers `.dump` contiennent des données personnelles.** Les sortir du serveur ou les
  supprimer une fois la vérification faite.

## 16. Bascule DNS derrière Cloudflare

Le domaine `eglise-ebc.org` est géré par Cloudflare. La bascule se fait donc dans le DNS
Cloudflare, pas chez le registrar, et deux réglages Cloudflare peuvent casser le site.

### Valider l'origine avant de toucher au DNS

Forcer la résolution vers le VPS sans rien changer publiquement :

```bash
curl -k --resolve eglise-ebc.org:443:<IP_DU_VPS> https://eglise-ebc.org/healthz/ping/
```

Le `-k` est attendu : tant que le DNS public ne pointe pas sur le serveur, Let's Encrypt ne peut
pas valider le challenge HTTP et Traefik sert un certificat auto-signé. Une réponse `200` prouve
que le routage Traefik et l'application sont corrects.

### Basculer

1. enregistrement `A` de l'apex et du `www` → IP du VPS ;
2. statut proxy sur **DNS only** (nuage gris) le temps de l'émission du certificat : le proxy
   orange fait échouer le challenge HTTP-01 ;
3. **supprimer tout enregistrement `AAAA` résiduel.** Le VPS n'ayant pas d'IPv6 configurée pour
   cette application, un `AAAA` pointant vers l'ancien hébergeur enverrait les visiteurs IPv6 au
   mauvais endroit, avec un site qui fonctionne pour les uns et pas pour les autres ;
4. vérifier la propagation :

```bash
dig +short eglise-ebc.org @1.1.1.1
```

5. déclencher l'émission du certificat, Traefik ne réessayant pas immédiatement après un échec :

```bash
docker restart coolify-proxy
```

6. vérifier le certificat réel, sans `-k` :

```bash
echo | openssl s_client -connect eglise-ebc.org:443 -servername eglise-ebc.org 2>/dev/null | openssl x509 -noout -issuer -dates
```

### Remettre le proxy Cloudflare

Passer SSL/TLS en **Full (strict)** *avant* de remettre le nuage orange.

Le mode `Flexible` provoquerait une boucle de redirection infinie : Cloudflare parlerait en HTTP
à l'origine, Django verrait `X-Forwarded-Proto: http` et renverrait une redirection vers HTTPS,
indéfiniment.

Une fois le proxy rétabli, `TRUSTED_CLIENT_IP_HEADER=HTTP_CF_CONNECTING_IP` n'est fiable que si
le VPS n'est pas joignable en direct : sans filtrage du port 443 sur les plages Cloudflare,
l'en-tête est falsifiable et le rate limiting contournable.

### Validation navigateur

Elle n'est possible qu'après l'obtention du certificat. `SECURE_HSTS_SECONDS` valant un an avec
`preload`, les navigateurs ayant déjà visité le site refusent toute exception de certificat, y
compris via le fichier `hosts`. Avant la bascule, seuls les contrôles `curl` sont exploitables.

## 17. Démantèlement de l'ancien hébergeur

Une fois la recette validée et la fenêtre de rollback écoulée :

1. supprimer les services applicatifs ;
2. supprimer **les tâches planifiées** en priorité : un cron de notifications resté actif
   enverrait des messages en double aux membres ;
3. régénérer le mot de passe de la base source ;
4. conserver un dump hors ligne avant suppression définitive de la base.

## 18. Critère de validation

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

## Annexe — diagnostics

### `service "migrate" didn't complete successfully: exit 1`

Coolify lance `docker compose up -d` : la sortie du conteneur `migrate` n'apparaît jamais dans le
journal de déploiement. Le conteneur, lui, reste présent après l'échec :

```bash
docker logs "$(docker ps -a --filter name=migrate- --format '{{.Names}}' | head -n1)"
```

`migrate.sh` y écrit une ligne `ERREUR MIGRATION EEBC:` nommant la variable manquante ou la
dépendance injoignable. Au-delà, c'est une traceback Django.

### `no available server`

Réponse du routeur attrape-tout de Coolify : aucun routeur Traefik ne correspond au domaine
demandé. Vérifier les règles réellement générées :

```bash
docker inspect -f '{{range $k,$v := .Config.Labels}}{{$k}}={{$v}}{{"\n"}}{{end}}' <CONTENEUR_WEB> | grep -i rule
```

Les labels Traefik sont figés à la **création** du conteneur : après modification des domaines,
un redéploiement est nécessaire, un simple enregistrement ne suffit pas.

Saisir les domaines **à la main** dans l'interface. Un copier-coller depuis un client qui
transforme les URL en liens injecte du markdown dans la règle, et le routeur ne correspond alors
à rien.

### `503` sur toutes les URL

Les conteneurs sont en cours de recréation, ou `migrate` a échoué : avec
`depends_on: service_completed_successfully`, `web` et `worker` ne sont jamais créés si la
migration échoue.

```bash
docker ps -a --format '{{.Names}} {{.Status}}'
```

### `400 Bad Request` sur une sonde locale

Django rejette tout `Host` absent de `ALLOWED_HOSTS`. Une sonde qui appelle `127.0.0.1` doit se
présenter avec un hôte autorisé, sinon le healthcheck reste `unhealthy` en permanence — et
Traefik écarte les conteneurs qui ne sont pas `healthy`.

### `500` sur toutes les pages, santé à `200`

`CompressedManifestStaticFilesStorage` lève une `ValueError` au rendu pour tout fichier absent du
manifeste. Les endpoints de santé ne rendant aucun template, ils continuent de répondre `200`.
Le test `apps/core/test_static_template_references.py` vérifie ce cas hors production.
