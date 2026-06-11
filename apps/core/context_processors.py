"""Context processors globaux de l'application."""

from apps.core.utils.user_codes import format_user_public_code


def operator_code(request):
    """Injecte `operator_code` dans tous les templates rendus avec un `request`.

    Garantit que les templates PDF (et autres) peuvent afficher
    `{{ operator_code }}` sans qu'aucune vue n'ait à le câbler manuellement.
    Retourne toujours une valeur (code système si utilisateur anonyme).
    """
    return {'operator_code': format_user_public_code(getattr(request, 'user', None))}
