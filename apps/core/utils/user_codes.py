"""Helpers pour afficher un identifiant utilisateur non sensible."""


SYSTEM_OPERATOR_CODE = 'SYS-000000'


def format_user_public_code(user, *, system_code=SYSTEM_OPERATOR_CODE):
    """Retourne un code court stable pour tracer l'utilisateur sur un document."""
    if not user or not getattr(user, 'is_authenticated', False) or not getattr(user, 'pk', None):
        return system_code

    try:
        user_id = int(user.pk)
    except (TypeError, ValueError):
        normalized_id = str(user.pk).replace('-', '').upper()
        return f"USR-{normalized_id[:12]}"

    return f"USR-{user_id:06d}"