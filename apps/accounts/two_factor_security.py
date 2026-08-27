"""Security policy and cryptographic helpers for EEBC two-factor auth."""

import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

ENCRYPTED_PREFIX = "enc:v1:"
DEFAULT_REQUIRED_ROLES = {
    "admin",
    "pasteur",
    "ancien",
    "diacre",
    "responsable_club",
    "moniteur",
    "chauffeur",
    "responsable_groupe",
    "secretariat",
    "finance",
    "encadrant",
}


def required_two_factor_roles():
    configured = getattr(settings, "TWO_FACTOR_REQUIRED_ROLES", None)
    if configured:
        if isinstance(configured, str):
            return {role.strip() for role in configured.split(",") if role.strip()}
        return set(configured)
    return DEFAULT_REQUIRED_ROLES


def requires_two_factor(user):
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser or user.is_staff:
        return True
    roles = set(user.get_roles_list()) if hasattr(user, "get_roles_list") else set()
    return bool(roles & required_two_factor_roles())


def needs_two_factor_verification(user):
    return requires_two_factor(user) or bool(getattr(user, "two_factor_enabled", False))


def _fernet_key():
    """Build a stable Fernet key from the dedicated application secret."""
    configured = getattr(settings, "TWO_FACTOR_ENCRYPTION_KEY", "")
    raw_key = str(configured or os.environ.get("TWO_FACTOR_ENCRYPTION_KEY", "")).strip()
    if not raw_key:
        if not settings.DEBUG:
            raise ImproperlyConfigured(
                "TWO_FACTOR_ENCRYPTION_KEY is required in production to protect TOTP secrets."
            )
        raw_key = settings.SECRET_KEY  # development fallback only
    digest = hashlib.sha256(raw_key.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def _fernet():
    return Fernet(_fernet_key())


def is_encrypted_secret(value):
    return bool(value and value.startswith(ENCRYPTED_PREFIX))


def encrypt_totp_secret(secret):
    if not secret:
        return ""
    if is_encrypted_secret(secret):
        return secret
    token = _fernet().encrypt(secret.encode("utf-8")).decode("ascii")
    return f"{ENCRYPTED_PREFIX}{token}"


def decrypt_totp_secret(value):
    if not value:
        return ""
    if not is_encrypted_secret(value):
        return value
    token = value[len(ENCRYPTED_PREFIX) :]
    try:
        return _fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise ImproperlyConfigured(
            "Unable to decrypt a TOTP secret. Check TWO_FACTOR_ENCRYPTION_KEY."
        ) from exc
