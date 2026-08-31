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

La recette de migration doit être faite depuis `coolify-migration`. Après validation et merge, la branche suivie par Coolify doit devenir `develop`.

## Render

`render.yaml`, `DEPLOY.md` et `PRODUCTION_CHECKLIST.md` décrivent l'infrastructure Render existante. Ils sont conservés temporairement pour permettre un rollback pendant la migration. Ils ne sont plus la source de vérité de la cible OVH/Coolify.

Ne pas supprimer l'environnement Render avant :

1. validation des parcours critiques sur Coolify ;
2. migration complète des données ;
3. validation du stockage média ;
4. sauvegarde PostgreSQL et test de restauration ;
5. validation du worker Celery et de la tâche planifiée ;
6. bascule DNS réussie ;
7. expiration de la fenêtre de rollback décidée.
