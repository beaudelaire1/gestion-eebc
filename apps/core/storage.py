"""Stockage des fichiers statiques en production.

``ManifestStaticFilesStorage`` lève une ``ValueError`` au rendu pour tout chemin
absent du manifeste. Cette rigueur est utile pour nos propres templates, mais
elle transforme le moindre écart d'une bibliothèque tierce en erreur 500 sur la
page entière : jazzmin appelle ``{% static 'vendor/bootswatch' %}`` sur un
répertoire, ce qui rendait toute l'administration Django inaccessible.

En mode non strict, un chemin inconnu est servi tel quel : l'asset manquant
renvoie un 404 isolé au lieu de faire tomber la page.

Nos propres références restent vérifiées hors production par
``apps/core/test_static_template_references.py``, qui échoue si un template du
projet pointe vers un fichier inexistant.
"""

from whitenoise.storage import CompressedManifestStaticFilesStorage


class ResilientManifestStaticFilesStorage(CompressedManifestStaticFilesStorage):
    """Manifeste WhiteNoise tolérant aux chemins absents."""

    manifest_strict = False
