"""Authentication throttling without attacker-triggered global account lockout."""
from __future__ import annotations

import hashlib
from datetime import timedelta

from django.contrib.auth import authenticate
from django.core.cache import cache
from django.utils import timezone

from apps.core.security import get_trusted_client_ip
from .models import User

WINDOW_SECONDS = 15 * 60
MAX_ACCOUNT_IP_FAILURES = 8
MAX_IP_FAILURES = 30
TELEMETRY_FAILURE_THRESHOLD = 5
MAX_MFA_FAILURES = 8
MFA_REPLAY_WINDOW_SECONDS = 120


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode('utf-8', errors='ignore')).hexdigest()[:24]


def _counter_key(prefix: str, value: str) -> str:
    return f'auth-security:{prefix}:{_digest(value)}'


def _get_count(key: str) -> int:
    try:
        return int(cache.get(key, 0) or 0)
    except (TypeError, ValueError):
        return 0


def _increment(key: str) -> int:
    if cache.add(key, 1, timeout=WINDOW_SECONDS):
        return 1
    try:
        return int(cache.incr(key))
    except (ValueError, TypeError):
        current = _get_count(key) + 1
        cache.set(key, current, timeout=WINDOW_SECONDS)
        return current


def _mfa_failure_key(user, request) -> str:
    ip = get_trusted_client_ip(request) if request is not None else 'unknown'
    return _counter_key('mfa-user-ip', f'{user.pk}|{ip}')


def _mfa_replay_key(user, code: str) -> str:
    return _counter_key('mfa-used-code', f'{user.pk}|{str(code).strip()}')


def verify_mfa_challenge(user, code: str, request=None) -> tuple[bool, str]:
    """Verify MFA with shared throttling and short replay protection.

    Successful password authentication does not reset this counter, so an
    attacker who already knows a password cannot obtain unlimited TOTP guesses
    by repeatedly restarting the login flow.
    """
    code = str(code or '').strip()
    if not code:
        return False, 'Code de double authentification requis.'

    failure_key = _mfa_failure_key(user, request)
    if _get_count(failure_key) >= MAX_MFA_FAILURES:
        return False, 'Trop de tentatives de double authentification. Réessayez plus tard.'

    replay_key = _mfa_replay_key(user, code)
    if cache.get(replay_key):
        _increment(failure_key)
        return False, 'Code de double authentification déjà utilisé.'

    if not user.verify_two_factor_code(code):
        _increment(failure_key)
        return False, 'Code de double authentification invalide.'

    cache.delete(failure_key)
    cache.set(replay_key, True, timeout=MFA_REPLAY_WINDOW_SECONDS)
    return True, ''


def secure_authenticate_user(cls, username: str, password: str, request=None):
    """Drop-in classmethod for AuthenticationService.authenticate_user.

    Effective throttling is scoped to source IP + account. The legacy
    ``failed_login_attempts``/``locked_until`` fields are retained as operator
    telemetry for automated abuse, but automated failures do not globally block
    a legitimate login from another source.

    A future ``locked_until`` with zero failed attempts is treated as an
    explicit/manual account lock and remains globally effective.
    """
    username = (username or '').strip()
    ip = get_trusted_client_ip(request) if request is not None else 'unknown'
    ip_key = _counter_key('ip', ip)
    identity_key = _counter_key('account-ip', f'{username.lower()}|{ip}')

    if (
        _get_count(ip_key) >= MAX_IP_FAILURES
        or _get_count(identity_key) >= MAX_ACCOUNT_IP_FAILURES
    ):
        return None, 'Trop de tentatives depuis cette connexion. Réessayez plus tard.'

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        _increment(ip_key)
        _increment(identity_key)
        return None, 'Nom d’utilisateur ou mot de passe incorrect.'

    # Preserve the ability for an administrator/operator to explicitly lock an
    # account without allowing anonymous failed attempts to create that lock.
    if (
        user.locked_until
        and timezone.now() < user.locked_until
        and user.failed_login_attempts == 0
    ):
        return None, 'Compte temporairement verrouillé.'

    authenticated_user = authenticate(
        request=request,
        username=username,
        password=password,
    )
    if authenticated_user is None:
        _increment(ip_key)
        scoped_failures = _increment(identity_key)

        # Compatibility/telemetry only. This state is not consulted for
        # automated lockout because failed_login_attempts > 0.
        user.failed_login_attempts = min(scoped_failures, MAX_ACCOUNT_IP_FAILURES)
        if scoped_failures >= TELEMETRY_FAILURE_THRESHOLD:
            user.locked_until = timezone.now() + timedelta(seconds=WINDOW_SECONDS)
        user.save(update_fields=['failed_login_attempts', 'locked_until'])
        return None, 'Nom d’utilisateur ou mot de passe incorrect.'

    cache.delete(identity_key)
    if user.failed_login_attempts or user.locked_until:
        user.failed_login_attempts = 0
        user.locked_until = None
        user.save(update_fields=['failed_login_attempts', 'locked_until'])

    if request is not None:
        user.last_login_ip = ip
        user.save(update_fields=['last_login_ip'])

    return authenticated_user, ''
