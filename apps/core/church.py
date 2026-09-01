"""Identité de l'organisme, partagée par tous les documents.

Le nom, l'adresse et les coordonnées étaient définis séparément dans le service
PDF finance et dans le thème des documents générés. Une seule source évite
qu'un courrier officiel et un reçu fiscal annoncent des informations
différentes.
"""

import os


def _env(name, fallback=""):
    """Valeur d'environnement en traitant une chaîne vide comme absente.

    Une plateforme de déploiement peut définir la variable à vide : le défaut de
    ``os.environ.get`` ne s'appliquerait alors pas, et les documents partiraient
    sans dénomination ni adresse.
    """

    return os.environ.get(name, '').strip() or fallback


CHURCH_INFO = {
    'name': _env('CHURCH_NAME', "Église Évangélique Baptiste de Cabassou"),
    'address': _env('CHURCH_ADDRESS', "11 lot Calimbé 2, rte de Cabassou, 97300 Cayenne"),
    'phone': _env('CHURCH_PHONE'),
    'email': _env('CHURCH_EMAIL', "contact@eglise-ebc.org"),
    'siret': _env('CHURCH_SIRET'),
    'rna': _env('CHURCH_RNA'),
}


def church_contact_line(separator=' — '):
    """Téléphone et email, sur une ligne, sans séparateur orphelin."""
    return separator.join(
        part for part in (CHURCH_INFO['phone'], CHURCH_INFO['email']) if part
    )
