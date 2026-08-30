# Déploiement rapide EEBC — Render

Ce guide est un aide-mémoire. Le runbook complet reste `DEPLOY.md` et l'infrastructure reste définie dans `render.yaml`.

## Avant de synchroniser Render

1. Vérifier que le Blueprint cible bien `develop`.
2. Examiner les changements de plans proposés par Render : la topologie actuelle utilise des ressources payantes et peut modifier la facturation.
3. Renseigner les secrets `sync: false`, en particulier :

```text
CLOUDINARY_URL
HOSTINGER_EMAIL_HOST_USER
HOSTINGER_EMAIL_HOST_PASSWORD
```

Puis les secrets Stripe, Meta, Turnstile et Sentry si ces intégrations sont utilisées.

## Déployer

Le déploiement doit venir d'un commit sur `develop` :

```bash
git checkout develop
git pull origin develop
git push origin develop
```

Pour un Blueprint existant, vérifier/synchroniser le Blueprint dans Render afin que les modifications de `render.yaml` soient réellement appliquées.

Ne pas remplacer la configuration par des réglages manuels divergents dans le Dashboard.

## Ce que Render doit exécuter

Build :

```bash
./build.sh
```

Pre-deploy :

```bash
python manage.py migrate --noinput && python manage.py setup_sites
```

Start :

```bash
./start.sh
```

Health check :

```text
/healthz/ping/
```

## Validation minimale

Après le déploiement :

- le service web reste stable sans boucle de redémarrage ;
- `healthz/ping` répond correctement ;
- PostgreSQL est accessible ;
- Redis est accessible et partagé ;
- une connexion utilisateur conserve sa session ;
- un upload média est relu depuis Cloudinary ;
- un PDF est généré ;
- un email Hostinger est réellement reçu ;
- le worker Celery est actif ;
- les logs ne contiennent pas d'`ImproperlyConfigured`.

## Si le déploiement échoue

Lire la première exception réelle du build/pre-deploy/start. Ne pas la contourner avec `|| true`, un cache local, un secret généré au démarrage ou un fallback de stockage éphémère.

Pour la procédure de diagnostic et de rollback, utiliser `DEPLOY.md`.
