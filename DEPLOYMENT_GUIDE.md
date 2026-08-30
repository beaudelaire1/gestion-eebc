# Guide de déploiement EEBC

Ce document historique a été retiré comme procédure opérationnelle : il décrivait une ancienne livraison ponctuelle et contenait des instructions désormais incompatibles avec l'architecture de production.

La procédure de référence est maintenant :

- `DEPLOY.md` pour le runbook complet ;
- `render.yaml` pour l'infrastructure Render ;
- `.python-version` pour le runtime Python ;
- `requirements/prod.txt` pour les dépendances de production ;
- `build.sh` pour le build ;
- `start.sh` pour le démarrage.

Branche actuellement ciblée par le Blueprint : `develop`.

Ne pas reprendre les anciennes instructions qui demandaient un déploiement manuel depuis `main`, un cache local, des migrations pendant le build ou un statut « production ready » sans tests réellement exécutés.
