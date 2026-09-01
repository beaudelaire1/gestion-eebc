"""Chaque {% static %} littéral d'un template doit désigner un fichier réel.

En production, ``CompressedManifestStaticFilesStorage`` lève une ``ValueError``
au rendu dès qu'un template référence un fichier absent du manifeste. Le
déploiement Coolify a rendu la panne visible :

    ValueError: Missing staticfiles manifest entry for 'img/og-image.png'

Une simple erreur de chemin suffit donc à renvoyer un 500 sur toutes les pages
héritant du template fautif, sans qu'aucun test fonctionnel ne le signale.
"""

import re
from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles import finders
from django.test import SimpleTestCase


# {% static 'chemin' %} / {% static "chemin" %}. Les appels dont l'argument est
# une variable ne sont pas vérifiables statiquement et sont ignorés.
STATIC_TAG_RE = re.compile(r"""\{%\s*static\s+(?P<quote>['"])(?P<path>[^'"]+)(?P=quote)""")


def _template_dirs():
    dirs = []
    for engine in settings.TEMPLATES:
        dirs.extend(Path(directory) for directory in engine.get('DIRS', []))
    dirs.append(Path(settings.BASE_DIR) / 'apps')
    return [directory for directory in dirs if directory.is_dir()]


class StaticTemplateReferenceTests(SimpleTestCase):
    def test_every_literal_static_reference_resolves(self):
        base_dir = Path(settings.BASE_DIR)
        missing = []

        for directory in _template_dirs():
            for template in directory.rglob('*.html'):
                content = template.read_text(encoding='utf-8', errors='ignore')
                for match in STATIC_TAG_RE.finditer(content):
                    path = match.group('path')

                    # Un chemin construit par interpolation n'est pas vérifiable.
                    if '{{' in path or '{%' in path:
                        continue

                    if finders.find(path) is None:
                        try:
                            location = template.relative_to(base_dir)
                        except ValueError:
                            location = template
                        missing.append(f'{location} -> {path}')

        self.assertFalse(
            missing,
            'Fichiers statiques référencés mais introuvables '
            '(500 garanti en production) :\n  - ' + '\n  - '.join(sorted(set(missing))),
        )
