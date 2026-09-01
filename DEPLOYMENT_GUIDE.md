# Guide de déploiement EEBC

## Cible en cours : OVH + Coolify

La procédure de migration et de production cible est maintenant décrite dans :

- `DEPLOY_COOLIFY.md` : runbook OVH/Coolify ;
- `PRODUCTION_CHECKLIST_COOLIFY.md` : preuves exigées avant validation ;
- `Dockerfile` : image de production reproductible ;
- `docker-compose.coolify.yml` : services applicatifs Coolify ;
- `.python-version` : runtime Python ;
- `requirements/prod.txt` : dépendances Python ;
- `gestion_eebc/settings/prod.py` : invariants runtime ;
- `start.sh` : démarrage Gunicorn.

La branche suivie par Coolify est `develop`. Pour chaque recette, noter le SHA exact déployé afin que les preuves et un éventuel rollback restent reproductibles.

## Historique

La production a été migrée depuis Render vers OVH + Coolify le 1er septembre 2026,
et les ressources Render ont été supprimées. Il n'existe plus de plateforme de
repli : les sauvegardes PostgreSQL sont le seul filet de sécurité.
