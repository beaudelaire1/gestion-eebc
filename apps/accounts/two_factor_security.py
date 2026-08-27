"""Security policy and cryptographic helpers for EEBC two-factor auth."""

import base64
import hashlib
import json
import os

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction

ENCRYPTED_PREFIX = "enc:v1:"
MAX_MFA_ATTEMPTS = 5
MFA_LOCK_SECONDS = 10 * 60
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


def _mfa_attempts_key(user_id):
    return f"eebc:2fa:attempts:{user_id}"


def _mfa_lock_key(user_id):
    return f"eebc:2fa:lock:{user_id}"


def is_mfa_locked(user_id):
    return bool(cache.get(_mfa_lock_key(user_id)))


def record_mfa_failure(user_id):
    """Atomically register a failed MFA attempt and return (locked, remaining)."""
    attempts_key = _mfa_attempts_key(user_id)
    if cache.add(attempts_key, 1, MFA_LOCK_SECONDS):
        attempts = 1
    else:
        try:
            attempts = cache.incr(attempts_key)
        except ValueError:
            cache.add(attempts_key, 1, MFA_LOCK_SECONDS)
            attempts = int(cache.get(attempts_key, 1))

    if attempts >= MAX_MFA_ATTEMPTS:
        cache.set(_mfa_lock_key(user_id), True, MFA_LOCK_SECONDS)
        return True, 0
    return False, MAX_MFA_ATTEMPTS - attempts


def clear_mfa_failures(user_id):
    cache.delete_many([_mfa_attempts_key(user_id), _mfa_lock_key(user_id)])


def verify_second_factor(user, code):
    """Verify TOTP or atomically consume a single-use backup code."""
    from .two_factor import hash_backup_code, verify_totp

    if not user.two_factor_enabled or not code:
        return False

    secret = user.get_two_factor_secret()
    if verify_totp(secret, code):
        return True

    hashed_input = hash_backup_code(code.upper().replace(" ", ""))
    user_model = type(user)
    with transaction.atomic():
        locked_user = user_model.objects.select_for_update().get(pk=user.pk)
        try:
            backup_codes = json.loads(locked_user.two_factor_backup_codes or "[]")
        except (TypeError, ValueError):
            backup_codes = []

        if hashed_input not in backup_codes:
            return False

        backup_codes.remove(hashed_input)
        locked_user.two_factor_backup_codes = json.dumps(backup_codes)
        locked_user.save(update_fields=["two_factor_backup_codes"])
        user.two_factor_backup_codes = locked_user.two_factor_backup_codes
        return True


def _fernet_key():
    """Build a stable Fernet key from the dedicated application secret."""
    configured = getattr(settings, "TWO_FACTOR_ENCRYPTION_KEY", "")
    raw_key = str(configured or os.environ.get("TWO_FACTOR_ENCRYPTION_KEY", "")).strip()
    if not raw_key:
        if not settings.DEBUG:
            raise ImproperlyConfigured(
                "TWO_FACTOR_ENCRYPTION_KEY is required in production to protect TOTP secrets."
            )
        raw_key = settings.SECRET_KEY
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
