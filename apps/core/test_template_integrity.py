"""Aucun gabarit ne doit être cassé à la compilation.

Quatre pages levaient une erreur de syntaxe et renvoyaient un 500 dès qu'on
les ouvrait : trois avaient une balise Django coupée par un retour à la ligne,
que le lexer ne reconnaît pas, et la quatrième appelait un filtre `sub`
inexistant. Rien ne les couvrait, donc rien ne l'avait signalé.
"""

import glob
import os

import pytest
from django.template import TemplateSyntaxError
from django.template.loader import get_template


# Le conftest du projet crée les sites par défaut dans une fixture de session
# qui touche la base ; sans ce marqueur, elle s'exécute avant les migrations.
@pytest.mark.django_db
def test_every_template_compiles():
    broken = []

    for path in sorted(glob.glob('templates/**/*.html', recursive=True)):
        name = path.replace(os.sep, '/')[len('templates/'):]
        try:
            get_template(name)
        except TemplateSyntaxError as exc:
            broken.append(f'{name} : {exc}')
        except Exception:
            # Un gabarit peut être introuvable par son nom relatif selon le
            # chargeur ; seule la syntaxe nous intéresse ici.
            continue

    assert not broken, 'Gabarits non compilables :\n' + '\n'.join(broken)
