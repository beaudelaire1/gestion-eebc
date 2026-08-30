"""Security primitives shared across EEBC applications.

This module deliberately contains policy decisions that must stay identical
across HTML views, APIs, exports and generated files.
"""
from __future__ import annotations

from ipaddress import ip_address, ip_network

from django.conf import settings
from django.db.models import Q
from django.utils.http import url_has_allowed_host_and_scheme


VALID_USER_ROLES = frozenset({
    'admin',
    'pasteur',
    'ancien',
    'diacre',
    'responsable_club',
    'moniteur',
    'chauffeur',
    'responsable_groupe',
    'secretariat',
    'finance',
    'encadrant',
    'membre',
})
PRIVILEGED_USER_ROLES = VALID_USER_ROLES - {'membre'}
MEMBER_SENSITIVE_ROLES = ('admin', 'secretariat', 'encadrant', 'pasteur')
# The data model does not currently distinguish a "pasteur principal" from
# other pastors. Confidential pastoral records therefore require the explicit
# pastor role (superusers retain emergency access), not a generic admin role.
PASTORAL_CONFIDENTIAL_ROLES = ('pasteur',)


def get_user_roles(user) -> set[str]:
    if not user or not getattr(user, 'is_authenticated', False):
        return set()
    if hasattr(user, 'get_roles_list'):
        return {str(role).strip() for role in user.get_roles_list() if str(role).strip()}
    raw = getattr(user, 'role', '') or ''
    return {item.strip() for item in raw.split(',') if item.strip()}


def user_has_any_role(user, *roles: str) -> bool:
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    if getattr(user, 'is_superuser', False):
        return True
    requested = {str(role).strip() for role in roles if str(role).strip()}
    return bool(get_user_roles(user).intersection(requested))


def can_view_sensitive_member_data(user) -> bool:
    return user_has_any_role(user, *MEMBER_SENSITIVE_ROLES)


def can_view_confidential_pastoral_data(user) -> bool:
    return user_has_any_role(user, *PASTORAL_CONFIDENTIAL_ROLES)


def can_assign_role(actor, role: str) -> bool:
    """Return whether ``actor`` may grant ``role`` to another account.

    Account administration is deliberately asymmetric: an administrator may
    assign any declared role; secretariat account managers may create/manage
    ordinary member accounts but may not grant any privileged role. This also
    prevents self-promotion to finance, pastor, secretariat, etc.
    """
    normalized = str(role or '').strip()
    if normalized not in VALID_USER_ROLES:
        return False
    if user_has_any_role(actor, 'admin'):
        return True
    return normalized == 'membre'


def can_manage_account(actor, target) -> bool:
    """Limit non-admin account managers to ordinary member accounts.

    Resetting the password, disabling, reactivating or editing a privileged
    account is itself a privilege-escalation path, even if its role is not
    changed. Only administrators can operate on such targets.
    """
    if user_has_any_role(actor, 'admin'):
        return True
    if not actor or not getattr(actor, 'is_authenticated', False):
        return False
    if target is None:
        return True
    if getattr(target, 'is_superuser', False):
        return False
    roles = get_user_roles(target)
    return bool(roles) and roles.isdisjoint(PRIVILEGED_USER_ROLES)


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


def _validated_single_ip(value: str) -> str | None:
    """Return a canonical IP only when the header contains exactly one address."""
    candidate = str(value or '').strip()
    if not candidate or ',' in candidate:
        return None
    try:
        return str(ip_address(candidate))
    except ValueError:
        return None


def get_trusted_client_ip(request) -> str:
    """Resolve a client IP without blindly trusting proxy-supplied headers.

    On platforms that provide a dedicated, overwrite-safe client-IP header
    (Render's Cloudflare edge uses ``CF-Connecting-IP``), production settings
    may explicitly name that WSGI ``META`` key via ``TRUSTED_CLIENT_IP_HEADER``.
    The value must contain one valid IP address.

    Otherwise, ``X-Forwarded-For`` is accepted only when ``REMOTE_ADDR``
    belongs to an explicitly configured trusted proxy/network.
    """
    remote = (request.META.get('REMOTE_ADDR') or '0.0.0.0').strip()

    trusted_header = str(
        getattr(settings, 'TRUSTED_CLIENT_IP_HEADER', '') or ''
    ).strip()
    if trusted_header:
        trusted_value = _validated_single_ip(request.META.get(trusted_header, ''))
        if trusted_value:
            return trusted_value

    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if not forwarded:
        return remote

    try:
        remote_ip = ip_address(remote)
    except ValueError:
        return remote

    trusted = _trusted_proxy_networks()
    if not any(remote_ip in network for network in trusted):
        return remote

    candidates = [part.strip() for part in forwarded.split(',') if part.strip()]
    # Walk right-to-left and return the first address which is not a trusted proxy.
    for candidate in reversed(candidates):
        try:
            candidate_ip = ip_address(candidate)
        except ValueError:
            continue
        if not any(candidate_ip in network for network in trusted):
            return str(candidate_ip)
    return candidates[0] if candidates else remote
