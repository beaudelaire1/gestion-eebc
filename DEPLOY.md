# Déploiement EEBC — Render

Dernière mise à jour : 30 août 2026  
Branche déployée : `develop`  
Source de vérité infrastructure : `render.yaml`

## 1. Principe

Le déploiement de production ne doit pas être reconstruit manuellement depuis des réglages dispersés dans le Dashboard Render.

`render.yaml` décrit :

- le service web Django ;
- le worker Celery ;
- Render Key Value utilisé comme Redis partagé ;
- PostgreSQL ;
- le cron quotidien de notifications ;
- la branche `develop` ;
- le build, le pre-deploy et le démarrage ;
- les références entre services.

Toute modification d'architecture Render doit d'abord être faite dans `render.yaml`, revue, puis synchronisée avec le Blueprint.

> Attention : le Blueprint actuel utilise des ressources Render payantes. Une synchronisation peut donc modifier la facturation du workspace. Vérifier les changements proposés par Render avant de confirmer le sync.

## 2. Versions de production

- Python : version définie dans `.python-version`.
- Django : version définie dans `requirements/base.txt`.
- Dépendances de production : `requirements/prod.txt`.
- `requirements.txt` est uniquement un point d'entrée de compatibilité vers `requirements/prod.txt`.

Ne pas réintroduire `runtime.txt`, une seconde version de Django ou un autre fichier de dépendances de production concurrent.

## 3. Variables obligatoires

Le Blueprint génère ou référence automatiquement :

- `SECRET_KEY` ;
- `DATABASE_URL` ;
- `REDIS_URL` ;
- `CELERY_BROKER_URL` ;
- `DJANGO_SETTINGS_MODULE` ;
- `TRUSTED_CLIENT_IP_HEADER` ;
- `ALLOWED_HOSTS` ;
- `SITE_URL` ;
- `SITE_NAME`.

Les secrets marqués `sync: false` doivent être renseignés dans Render avant un déploiement utilisable.

Minimum pour le démarrage de production :

```text
CLOUDINARY_URL
HOSTINGER_EMAIL_HOST_USER
HOSTINGER_EMAIL_HOST_PASSWORD
```

Selon les fonctionnalités activées :

```text
HOSTINGER_API_KEY
SENTRY_DSN
STRIPE_PUBLIC_KEY
STRIPE_SECRET_KEY
STRIPE_WEBHOOK_SECRET
META_WHATSAPP_ACCESS_TOKEN
META_WHATSAPP_PHONE_NUMBER_ID
META_WHATSAPP_VERIFY_TOKEN
META_WHATSAPP_APP_SECRET
TURNSTILE_SITE_KEY
TURNSTILE_SECRET_KEY
```

Ne jamais stocker les vraies valeurs dans Git.

## 4. Invariants de sécurité

La production refuse volontairement de démarrer si un invariant critique manque.

### Cache partagé

`REDIS_URL` est obligatoire. `LocMemCache` est interdit en production parce que les compteurs de sécurité et le rate limiting doivent être communs à tous les workers Gunicorn.

### IP client

Sur Render :

```text
TRUSTED_CLIENT_IP_HEADER=HTTP_CF_CONNECTING_IP
```

Hors Render, utiliser `TRUSTED_PROXY_IPS` avec les CIDR réels du reverse proxy.

Ne jamais utiliser :

```text
TRUSTED_PROXY_IPS=0.0.0.0/0
TRUSTED_PROXY_IPS=::/0
```

### Médias

`CLOUDINARY_URL` est obligatoire avec `gestion_eebc.settings.prod`.

Le filesystem local Render est éphémère. Les médias utilisateurs ne doivent donc pas être servis depuis `MEDIA_ROOT` en production.

### SECRET_KEY

La production exige une clé stable. Aucun fallback aléatoire n'est généré au démarrage.

## 5. Pipeline de déploiement

### Build

Render exécute :

```bash
./build.sh
```

Le build :

1. installe `requirements/prod.txt` ;
2. exécute `pip check` ;
3. effectue un smoke test WeasyPrint ;
4. exécute `collectstatic` ;
5. exécute `python manage.py check --deploy --fail-level ERROR`.

Le build ne doit jamais :

- lancer une migration ;
- créer/modifier des données métier ;
- envoyer des notifications ;
- créer une sauvegarde locale de production.

### Pre-deploy

Après un build réussi et avant le démarrage du nouveau service :

```bash
python manage.py migrate --noinput && python manage.py setup_sites
```

### Start

Render exécute :

```bash
./start.sh
```

`start.sh` vérifie Django sans masquer les erreurs puis lance Gunicorn.

## 6. Redis / sessions / Celery

Render Key Value est la source Redis partagée pour :

- le cache Django ;
- le rate limiting ;
- le cache des sessions ;
- le broker Celery ;
- le backend de résultats Celery.

Les sessions utilisent `cached_db` : PostgreSQL reste la source durable, Redis accélère l'accès.

Le Key Value du Blueprint est persistant. Ne pas le remplacer par un cache local par worker.

## 7. PostgreSQL

La production utilise le PostgreSQL défini par le Blueprint et injecte sa `connectionString` dans `DATABASE_URL`.

Les migrations passent exclusivement par le `preDeployCommand` Render ou par une intervention manuelle contrôlée. Elles ne doivent pas être exécutées pendant le build.

La commande historique `backup_db` écrit un fichier local et ne constitue donc pas une stratégie de sauvegarde durable sur Render. Pour la production Render, utiliser les mécanismes de sauvegarde/récupération du PostgreSQL géré et tester régulièrement une restauration.

## 8. Emails

Le backend Hostinger utilise SMTP sur le port 587.

Le service web/worker de production doit donc utiliser un plan Render qui autorise cette sortie réseau. Un service web Render Free ne peut pas envoyer vers les ports SMTP 25, 465 ou 587.

Vérifications après déploiement :

- credentials Hostinger présents ;
- worker Celery actif ;
- un email de test réellement reçu ;
- absence d'erreur SMTP dans les logs.

## 9. Cron

Render évalue les expressions cron en UTC.

Le cron des notifications est :

```text
0 10 * * *
```

soit 07:00 en Guyane (`America/Cayenne`, UTC-3).

Ne pas remplacer par `0 7 * * *` si l'objectif reste 07:00 heure de Guyane.

## 10. Vérification après déploiement

### Logs

Vérifier séparément :

- build web ;
- pre-deploy ;
- démarrage Gunicorn ;
- worker Celery ;
- cron ;
- Sentry si configuré.

### Health check

Le Blueprint utilise :

```text
/healthz/ping/
```

Le service n'est considéré sain qu'après réponse correcte de cet endpoint et absence de redémarrages en boucle.

### Contrôles applicatifs minimum

- page publique ;
- authentification ;
- session après plusieurs requêtes ;
- rate limiting ;
- lecture/écriture PostgreSQL ;
- upload puis relecture d'un média Cloudinary ;
- génération PDF ;
- envoi email ;
- exécution d'une tâche Celery ;
- webhook Stripe/Meta uniquement si les intégrations sont activées.

## 11. Rollback

Un rollback de code et un rollback de schéma sont deux opérations différentes.

Avant de revenir à un commit antérieur :

1. vérifier si le déploiement a appliqué une migration ;
2. vérifier si cette migration est réversible ;
3. restaurer la base si nécessaire ;
4. seulement ensuite redéployer le commit stable.

Ne jamais faire un `git revert` automatique sur un incident impliquant une migration destructive sans analyser la base.

## 12. GitHub Actions

La CI doit exécuter les tests sur Python 3.11 et 3.13 et les contrôles de sécurité sur Python 3.13.

Un workflow marqué `failure` n'est pas forcément un échec applicatif. Vérifier que le job a réellement obtenu un runner et exécuté des étapes. Un job avec `runner_id: 0` et `steps: []` correspond à un problème d'exécution GitHub Actions en amont des tests.

Ne jamais annoncer « tests passés » ou « production ready » sans exécution effective des commandes.

## 13. Si WeasyPrint échoue sur Render

Le build contient un smoke test PDF volontairement bloquant.

Si les bibliothèques système nécessaires à WeasyPrint ne sont pas disponibles sur le runtime Python natif Render, ne pas masquer l'erreur et ne pas ajouter un `apt-get ... || true`.

La solution propre est de passer le service concerné sur un runtime Docker avec les dépendances système versionnées dans un `Dockerfile`, puis de tester le rendu PDF dans l'image.
