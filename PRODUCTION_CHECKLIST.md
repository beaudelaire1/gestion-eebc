# Checklist pré-production — Gestion EEBC

Cette checklist ne remplace pas les tests. Une case ne doit être cochée que si elle a été vérifiée sur l'environnement concerné.

## Configuration et sécurité

- [ ] `DJANGO_SETTINGS_MODULE=gestion_eebc.settings.prod`
- [ ] `DEBUG=False`
- [ ] `SECRET_KEY` stable, non triviale et fournie par Render
- [ ] `ALLOWED_HOSTS` contient uniquement les hôtes nécessaires
- [ ] HTTPS et HSTS vérifiés
- [ ] cookies session/CSRF sécurisés
- [ ] `TRUSTED_CLIENT_IP_HEADER=HTTP_CF_CONNECTING_IP` sur Render
- [ ] aucun `TRUSTED_PROXY_IPS=0.0.0.0/0` ou `::/0`
- [ ] CSP réellement présente dans les réponses
- [ ] CORS limité aux origines attendues
- [ ] Sentry ne collecte pas de PII par défaut

## Cache, sessions et rate limiting

- [ ] `REDIS_URL` pointe vers Render Key Value
- [ ] aucune utilisation de `LocMemCache` en production
- [ ] plusieurs workers voient le même cache
- [ ] session durable vérifiée avec le backend `cached_db`
- [ ] rate limiting vérifié avec plusieurs requêtes et plusieurs workers
- [ ] redémarrage Redis testé sans perte durable des sessions PostgreSQL

## Base de données

- [ ] `DATABASE_URL` injectée depuis Render Postgres
- [ ] `python manage.py migrate --check` ne signale rien après pre-deploy
- [ ] `python manage.py showmigrations` cohérent
- [ ] restauration PostgreSQL testée sur un environnement isolé
- [ ] stratégie de récupération Render documentée
- [ ] aucune sauvegarde de production dépend uniquement du filesystem local du service web

## Médias et fichiers statiques

- [ ] `CLOUDINARY_URL` définie
- [ ] upload d'un média réussi
- [ ] média relu après redéploiement/redémarrage
- [ ] aucun routage Django de `/media/` en production
- [ ] `collectstatic` réussit avec WhiteNoise
- [ ] fichiers statiques servis correctement avec hash/manifest

## PDF / WeasyPrint

- [ ] smoke test WeasyPrint du build réussi
- [ ] génération d'un document métier réel réussie
- [ ] rendu visuel contrôlé
- [ ] si le runtime natif Render manque de bibliothèques système, migration Docker traitée au lieu de masquer l'erreur

## Email et tâches asynchrones

- [ ] credentials Hostinger valides
- [ ] connexion SMTP 587 réussie depuis le service Render payé
- [ ] email de test réellement reçu
- [ ] `CELERY_BROKER_URL` pointe vers le même Key Value partagé
- [ ] worker Celery en état `ready`
- [ ] tâche Celery de test exécutée une fois
- [ ] absence de duplication d'envoi lors d'un retry

## Cron

- [ ] cron des notifications présent dans le Blueprint
- [ ] expression `0 10 * * *` confirmée pour 07:00 Guyane
- [ ] exécution observée dans les logs Render
- [ ] résultat métier du cron vérifié

## Build et démarrage

- [ ] `./build.sh` réussit sans `|| true` masquant une erreur critique
- [ ] `pip check` réussit
- [ ] `collectstatic` réussit
- [ ] `python manage.py check --deploy --fail-level ERROR` réussit
- [ ] le build n'exécute ni migration, ni notification, ni backup métier
- [ ] le `preDeployCommand` applique migrations + `setup_sites`
- [ ] `./start.sh` réussit
- [ ] Gunicorn reste actif sans boucle de restart
- [ ] `/healthz/ping/` répond correctement

## Versions et dépendances

- [ ] Python correspond à `.python-version`
- [ ] Django correspond à `requirements/base.txt`
- [ ] production installe `requirements/prod.txt`
- [ ] `requirements.txt` ne contient pas de snapshot concurrent
- [ ] `django-csp` utilise le format v4 `CONTENT_SECURITY_POLICY`
- [ ] aucun `django-cryptography` inutilisé/résiduel

## CI

- [ ] GitHub Actions obtient réellement un runner
- [ ] les jobs contiennent des étapes exécutées (`steps` non vide)
- [ ] tests Python 3.11 exécutés
- [ ] tests Python 3.13 exécutés
- [ ] lint exécuté
- [ ] contrôles sécurité exécutés
- [ ] `check --deploy` exécuté en CI
- [ ] aucun statut « tests passés » déduit d'un workflow qui n'a jamais démarré

## Fonctionnel critique

- [ ] page publique accessible
- [ ] login/logout
- [ ] changement de mot de passe
- [ ] 2FA pour un compte concerné
- [ ] permissions par rôles
- [ ] données membres sensibles protégées
- [ ] export sensible protégé
- [ ] événements privés non exposés
- [ ] création/lecture document ou média
- [ ] finance : parcours critique
- [ ] webhook Stripe si activé
- [ ] webhook Meta WhatsApp si activé

## Observabilité

- [ ] erreurs 5xx visibles dans les logs
- [ ] Sentry configuré si retenu
- [ ] aucune donnée sensible dans les logs
- [ ] alertes sur indisponibilité web/DB/worker définies
- [ ] suivi CPU/mémoire disponible

## Déploiement Render

- [ ] `render.yaml` relu avant sync
- [ ] branche `develop` confirmée pour web/worker/cron
- [ ] `autoDeployTrigger: commit` confirmé
- [ ] plans payants et impact de facturation explicitement acceptés avant sync
- [ ] PostgreSQL et Key Value dans la même région que les services
- [ ] secrets `sync: false` renseignés
- [ ] aucune variable manuelle du Dashboard ne contredit le Blueprint

## Verdict

Un déploiement ne peut être déclaré validé que si :

1. le build et le pre-deploy ont réellement réussi ;
2. la CI a réellement exécuté ses étapes ou une validation équivalente documentée a été réalisée ;
3. le health check est sain ;
4. les parcours critiques ont été testés ;
5. les mécanismes de persistance (PostgreSQL, Redis, Cloudinary) ont été vérifiés ;
6. les coûts Render liés à la topologie ont été acceptés.

Aucun score arbitraire de type « 10/10 » ne remplace ces preuves.
