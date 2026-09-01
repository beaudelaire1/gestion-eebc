"""Un fichier statique manquant ne doit pas produire une erreur 500.

jazzmin appelle `{% static 'vendor/bootswatch' %}` sur un répertoire, absent par
nature du manifeste. En mode strict, toute page d'administration Django devenait
inaccessible.
"""

from apps.core.storage import ResilientManifestStaticFilesStorage


def test_production_manifest_is_not_strict():
    assert ResilientManifestStaticFilesStorage.manifest_strict is False


def test_unknown_static_path_is_served_as_is():
    storage = ResilientManifestStaticFilesStorage()
    storage.hashed_files = {'css/known.css': 'css/known.abc123.css'}

    assert storage.stored_name('css/known.css') == 'css/known.abc123.css'
    assert storage.stored_name('vendor/bootswatch') == 'vendor/bootswatch'
