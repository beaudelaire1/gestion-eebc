# Checklist pré-production — OVH + Coolify

Cette checklist exige des preuves observées sur l'environnement OVH/Coolify. Une configuration présente dans Git ne prouve pas qu'elle fonctionne en production.

## Build

- [ ] `Dockerfile` construit avec Python 3.13.15.
- [ ] `pip check` réussit dans le build.
- [ ] smoke test WeasyPrint réussit.
- [ ] `collectstatic` réussit avec `gestion_eebc.settings.build`.
- [ ] aucune migration n'est exécutée pendant le build.

## Configuration runtime

- [ ] `DJANGO_SETTINGS_MODULE=gestion_eebc.settings.prod`.
- [ ] `SECRET_KEY` stable et non triviale.
- [ ] `ALLOWED_HOSTS` limité aux domaines réellement servis.
- [ ] `CSRF_TRUSTED_ORIGINS` correspond aux domaines HTTPS.
- [ ] `DEBUG=False`.
- [ ] cookies session/CSRF sécurisés.
- [ ] HTTPS et HSTS vérifiés.

## Proxy Coolify / Traefik

- [ ] le service web n'a aucun port publié directement sur l'hôte.
- [ ] le domaine Coolify cible le port interne `8000`.
- [ ] `X-Forwarded-Proto` est correctement reçu par Django.
- [ ] `TRUSTED_PROXY_IPS` contient uniquement le subnet réellement utilisé par le proxy.
- [ ] aucun `0.0.0.0/0` ou `::/0` n'est configuré.
- [ ] l'IP cliente observée par le rate limiting correspond au client et non à Traefik.

## PostgreSQL

- [ ] PostgreSQL est une ressource Coolify distincte et privée.
- [ ] l'application utilise l'URL interne via `DATABASE_URL`.
- [ ] **Connect to Predefined Network** est activé si nécessaire pour joindre la base.
- [ ] le service `migrate` réussit.
- [ ] `python manage.py migrate --check` ne signale rien.
- [ ] lecture/écriture applicative vérifiée.

## Redis / Celery

- [ ] Redis est une ressource privée distincte.
- [ ] `REDIS_URL` utilise l'URL interne.
- [ ] Django cache et Celery partagent le Redis attendu.
- [ ] le worker Celery reste actif après redéploiement.
- [ ] une tâche Celery réelle est exécutée.
- [ ] rate limiting cohérent entre plusieurs workers/requêtes.

## Médias

- [ ] `MEDIA_STORAGE_BACKEND` vaut explicitement `cloudinary` ou `s3`.
- [ ] si Cloudinary : `CLOUDINARY_URL` est valide.
- [ ] si S3 : endpoint, région, bucket et credentials sont valides.
- [ ] upload puis relecture d'un média réussis.
- [ ] média encore accessible après redéploiement du web.
- [ ] migration des médias historiques validée avant changement de provider.

## Santé et disponibilité

- [ ] `/healthz/ping/` répond 200.
- [ ] `/healthz/lite/` valide PostgreSQL + Redis.
- [ ] le conteneur web reste `healthy`.
- [ ] aucune boucle de restart Gunicorn/worker.
- [ ] les 5xx sont visibles dans les logs et/ou Sentry.

## Email et notifications

- [ ] connexion Hostinger SMTP 587 réussie depuis le VPS.
- [ ] email de test réellement reçu.
- [ ] Scheduled Task Coolify `python manage.py run_notifications --all` créée.
- [ ] fuseau du serveur vérifié avant choix de l'expression cron.
- [ ] `Execute Now` réussit.
- [ ] résultat métier de la tâche vérifié.

## Sauvegardes

- [ ] sauvegarde PostgreSQL moteur configurée dans Coolify.
- [ ] copie S3 hors serveur activée.
- [ ] rétention locale définie.
- [ ] rétention distante définie.
- [ ] Backup Now crée un fichier non vide.
- [ ] restauration testée dans une base isolée.
- [ ] application testée contre la base restaurée.

## Parcours critiques

- [ ] page publique.
- [ ] login/logout.
- [ ] changement de mot de passe.
- [ ] 2FA.
- [ ] permissions par rôles.
- [ ] données membres sensibles protégées.
- [ ] finance : parcours critique.
- [ ] génération PDF métier.
- [ ] création/lecture document ou média.
- [ ] webhook Stripe si activé.
- [ ] webhook Meta si activé.

## CI / livraison Git

- [ ] GitHub Actions obtient réellement un runner (`runner_id != 0`).
- [ ] les jobs contiennent des étapes exécutées.
- [ ] tests Python 3.11 exécutés.
- [ ] tests Python 3.13 exécutés.
- [ ] sécurité/lint exécutés.
- [ ] image Docker construite par CI.
- [ ] un nouveau commit GitHub déclenche bien un redéploiement Coolify.

## Bascule

- [ ] sauvegarde finale Render réalisée.
- [ ] fenêtre d'écriture maîtrisée pendant migration finale.
- [ ] PostgreSQL transféré et contrôlé.
- [ ] médias transférés si nécessaire.
- [ ] recette Coolify validée avant changement DNS.
- [ ] DNS basculé.
- [ ] Render conservé pendant la fenêtre de rollback.

## Verdict

Le déploiement OVH/Coolify n'est **VALIDÉ** que lorsque les preuves runtime ci-dessus sont obtenues. La présence du Dockerfile, du Compose ou d'une checklist ne suffit pas à déclarer la production prête.
