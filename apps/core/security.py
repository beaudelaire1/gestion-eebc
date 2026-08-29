"""Security primitives shared across EEBC applications.

This module deliberately contains policy decisions that must stay identical
across HTML views, APIs, exports and generated files.
"""
from __future__ import annotations

from ipaddress import ip_address, ip_network

from django.conf import settings
from django.db.models import Q
from django.utils.http import url_has_allowed_host_and_scheme


MEMBER_SENSITIVE_ROLES = ('admin', 'secretariat', 'encadrant')
PASTORAL_CONFIDENTIAL_ROLES = ('admin', 'pasteur')


def user_has_any_role(user, *roles: str) -> bool:
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    if getattr(user, 'is_superuser', False):
        return True
    if hasattr(user, 'has_any_role'):
        return user.has_any_role(*roles)
    raw = getattr(user, 'role', '') or ''
    user_roles = {item.strip() for item in raw.split(',') if item.strip()}
    return bool(user_roles.intersection(roles)) or 'admin' in user_roles


def can_view_sensitive_member_data(user) -> bool:
    return user_has_any_role(user, *MEMBER_SENSITIVE_ROLES)


def can_view_confidential_pastoral_data(user) -> bool:
    return user_has_any_role(user, *PASTORAL_CONFIDENTIAL_ROLES)


def can_assign_role(actor, role: str) -> bool:
    """Only administrators may grant the administrator role."""
    if role != 'admin':
        return bool(actor and getattr(actor, 'is_authenticated', False))
    return user_has_any_role(actor, 'admin')


def can_manage_account(actor, target) -> bool:
    """Non-admin account managers may never mutate an administrator account."""
    if user_has_any_role(actor, 'admin'):
        return True
    if not actor or not getattr(actor, 'is_authenticated', False):
        return False
    if target is None:
        return True
    return not (getattr(target, 'is_superuser', False) or user_has_any_role(target, 'admin'))


def event_visibility_q(user):
    """Return the only Event rows the supplied actor is allowed to observe."""
    if user and getattr(user, 'is_authenticated', False):
        if user_has_any_role(user, 'admin'):
            return Q()
        return Q(visibility='public') | Q(visibility='members') | Q(
            visibility='private', organizers=user
        )
    return Q(visibility='public')


def safe_next_url(request, candidate: str | None, fallback: str) -> str:
    if candidate and url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate
    return fallback


def revoke_user_refresh_tokens(user) -> int:
    """Blacklist all known refresh/sliding JWTs for a user.

    Deleting OutstandingToken rows does not revoke an already issued token.
    Persisting BlacklistedToken rows does.
    """
    if not user or not getattr(user, 'pk', None):
        return 0
    try:
        from rest_framework_simplejwt.token_blacklist.models import (
            BlacklistedToken,
            OutstandingToken,
        )
    except Exception:
        return 0

    count = 0
    for token in OutstandingToken.objects.filter(user=user).iterator():
        _, created = BlacklistedToken.objects.get_or_create(token=token)
        if created:
            count += 1
    return count


def _trusted_proxy_networks():
    values = getattr(settings, 'TRUSTED_PROXY_IPS', []) or []
    networks = []
    for value in values:
        try:
            networks.append(ip_network(str(value).strip(), strict=False))
        except ValueError:
            continue
    return networks


def get_trusted_client_ip(request) -> str:
    """Resolve a client IP without blindly trusting X-Forwarded-For.

    X-Forwarded-For is accepted only when REMOTE_ADDR belongs to an explicitly
    configured trusted proxy/network. Otherwise REMOTE_ADDR is authoritative.
    """
    remote = (request.META.get('REMOTE_ADDR') or '0.0.0.0').strip()
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if not forwarded:
        return remote

    try:
        remote_ip = ip_address(remote)
    except ValueError:
        return remote

    if not any(remote_ip in network for network in _trusted_proxy_networks()):
        return remote

    candidates = [part.strip() for part in forwarded.split(',') if part.strip()]
    # Walk right-to-left and return the first address which is not a trusted proxy.
    trusted = _trusted_proxy_networks()
    for candidate in reversed(candidates):
        try:
            candidate_ip = ip_address(candidate)
        except ValueError:
            continue
        if not any(candidate_ip in network for network in trusted):
            return candidate
    return candidates[0] if candidates else remote
