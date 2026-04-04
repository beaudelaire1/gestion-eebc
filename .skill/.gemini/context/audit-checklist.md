# Audit Checklist

## Sécurité
Vérifier au minimum :
- validation des entrées,
- contrôle d'accès,
- permissions et rôles,
- exposition de secrets,
- injections,
- XSS / CSRF / SSRF / IDOR selon le contexte,
- logs sensibles,
- surfaces d'attaque créées par la modification.

## Performance
Vérifier au minimum :
- requêtes inutiles,
- complexité évitable,
- surcharge front inutile,
- duplication de traitements,
- coût runtime disproportionné,
- opportunités de cache ou de simplification.

## Maintenabilité
Vérifier au minimum :
- couplage,
- nommage,
- séparation des responsabilités,
- duplication,
- clarté des interfaces,
- cohérence des modules,
- testabilité.

## Accessibilité / UX
Si l'interface est concernée, vérifier au minimum :
- structure claire,
- lisibilité,
- erreurs compréhensibles,
- navigation clavier,
- labels,
- feedback d'état,
- réduction de friction,
- hiérarchie visuelle utile.

## SEO
Si le web rendu est concerné, vérifier au minimum :
- structure sémantique,
- titres,
- métadonnées utiles,
- contenu réellement indexable,
- logique de routing si concernée,
- performance compatible avec un rendu sain.

## Delivery / Ops
Si la prod ou l'infra est concernée, vérifier au minimum :
- variables d'environnement,
- configuration différenciée,
- scripts de build,
- CI/CD impactée,
- migrations,
- compatibilité runtime,
- stratégie de rollback ou de rattrapage.