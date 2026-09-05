"""Account authentication enforcement middleware.

This module enforces two independent invariants for authenticated browser
sessions:
- accounts marked ``must_change_password`` cannot access the application before
  completing the required password change;
- accounts with 2FA enabled cannot keep an authenticated session unless the
  current session contains proof that the second factor was verified;
- accounts holding a privileged role cannot use the application at all until
  they have enrolled a second factor.

The MFA check is deliberately session-wide rather than tied only to the normal
login view. This prevents bypasses through Django admin or any other code path
that calls ``django.contrib.auth.login`` directly.
"""
from django.contrib.auth import SESSION_KEY, logout
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse

from apps.core.permissions import log_access_denied
from apps.core.security import is_ordinary_member

from .two_factor_policy import requires_2fa_enrollment


MFA_VERIFIED_SESSION_KEY = 'two_factor_verified_user_id'
MFA_PENDING_USER_SESSION_KEY = 'two_factor_user_id'
MFA_PENDING_NEXT_SESSION_KEY = 'two_factor_next'
MFA_ATTEMPTS_SESSION_KEY = 'two_factor_attempts'


class OrdinaryMemberAccessMiddleware:
    """Keep ordinary member sessions inside their self-service perimeter.

    The project contains legacy views that only require authentication.  This
    boundary prevents a member from reaching those management screens through
    a copied or guessed URL while those views are migrated to local RBAC.
    """

    ALLOWED_APP_VIEWS = frozenset({
        'dashboard:home',
        'accounts:profile',
        'accounts:logout',
        'accounts:first_login_password_change',
        'accounts:two_factor_setup',
        'accounts:two_factor_disable',
        'accounts:two_factor_verify',
        'accounts:two_factor_backup_codes',
        'events:list',
        'events:list_advanced',
        'events:calendar',
        'events:calendar_print',
        'events:calendar_pdf',
        'events:events_json',
        'events:detail',
        'events:upcoming',
        'communication:notifications',
        'communication:notification_detail',
        'communication:notification_mark_read',
        'communication:notifications_mark_all_read',
        'communication:notifications_count',
        'communication:announcements',
        'communication:announcement_detail',
        # Self-service transport: the views below already scope their data to
        # the signed-in requester or driver.
        'transport:requests',
        'transport:request_create',
        'transport:request_detail',
        'transport:live_status',
        'transport:pickup_location_update',
        # Submitting a testimony for moderation (never publishing one).
        'public_cms:testimony_share',
        # Document library: Document.accessible_queryset and
        # Document.can_be_accessed_by already restrict a member to public,
        # non-confidential files. Uploading, editing, sharing, categories and
        # statistics stay with the teams that own them.
        'documents:list',
        'documents:detail',
        'documents:download',
        'documents:stream',
        'documents:preview',
    })

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        if not is_ordinary_member(request.user):
            return None

        path = request.path_info
        if path.startswith('/gestion-eebc/'):
            self._deny(request, view_func)

        if not path.startswith('/app/'):
            return None

        view_name = getattr(request.resolver_match, 'view_name', '')
        if view_name not in self.ALLOWED_APP_VIEWS:
            self._deny(request, view_func)
        return None

    @staticmethod
    def _deny(request, view_func):
        view_name = getattr(request.resolver_match, 'view_name', '') or getattr(
            view_func, '__name__', ''
        )
        log_access_denied(request, ('management_role',), view_name)
        raise PermissionDenied(
            "Cet espace est réservé aux responsables autorisés de l'église."
        )


class ForcePasswordChangeMiddleware:
    """Enforce mandatory password changes and MFA for authenticated sessions."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        password_change_response = self._enforce_password_change(request)
        if password_change_response is not None:
            return password_change_response

        mfa_response = self._enforce_mfa_before_view(request)
        if mfa_response is not None:
            return mfa_response

        enrollment_response = self._enforce_2fa_enrollment(request)
        if enrollment_response is not None:
            return enrollment_response

        response = self.get_response(request)
        response = self._enforce_mfa_after_view(request, response)
        return self._enforce_2fa_enrollment_after_view(request, response)

    @staticmethod
    def _is_asset_path(path):
        return (
            path.startswith('/static/')
            or path.startswith('/media/')
            or path.startswith('/favicon.ico')
        )

    def _enforce_password_change(self, request):
        user = request.user
        if not (
            user.is_authenticated
            and hasattr(user, 'must_change_password')
            and user.must_change_password
        ):
            return None

        allowed_paths = {
            reverse('accounts:first_login_password_change'),
            reverse('accounts:logout'),
            reverse('admin:logout'),
        }
        exempt_paths = {
            reverse('accounts:login'),
            reverse('public:home'),
            reverse('admin:login'),
        }
        current_path = request.path

        if current_path in allowed_paths or self._is_asset_path(current_path):
            return self.get_response(request)

        if current_path in exempt_paths:
            logout(request)
            return self.get_response(request)

        return redirect('accounts:first_login_password_change')

    @staticmethod
    def _is_session_authenticated(request):
        """Whether the browser session itself carries the authenticated user.

        The response phase runs after DRF has resolved a bearer token, so
        ``request.user`` may be authenticated for this request only, with no
        session behind it. Both response-phase checks exist to catch sessions
        created inside a view; applying them to a stateless API call would
        turn a valid mobile request into an HTML redirect.
        """
        return bool(request.session.get(SESSION_KEY))

    @staticmethod
    def _requires_mfa(user):
        return bool(
            user.is_authenticated
            and getattr(user, 'two_factor_enabled', False)
        )

    @staticmethod
    def _has_mfa_proof(request, user):
        verified_user_id = request.session.get(MFA_VERIFIED_SESSION_KEY)
        return str(verified_user_id or '') == str(user.pk)

    @staticmethod
    def _mark_mfa_verified(request, user):
        request.session[MFA_VERIFIED_SESSION_KEY] = str(user.pk)

    @staticmethod
    def _clear_mfa_proof(request):
        request.session.pop(MFA_VERIFIED_SESSION_KEY, None)

    def _begin_mfa_challenge(self, request):
        user_id = request.user.pk
        requested_next = request.get_full_path()
        verify_path = reverse('accounts:two_factor_verify')

        # Avoid returning to the challenge itself after successful verification.
        if request.path == verify_path:
            requested_next = reverse('dashboard:home')

        # ``logout`` flushes the authenticated session. Store the pending MFA
        # state afterwards so no authenticated session survives factor one.
        logout(request)
        request.session[MFA_PENDING_USER_SESSION_KEY] = user_id
        request.session[MFA_PENDING_NEXT_SESSION_KEY] = requested_next
        request.session[MFA_ATTEMPTS_SESSION_KEY] = 0
        return redirect('accounts:two_factor_verify')

    def _enforce_mfa_before_view(self, request):
        user = request.user

        if not user.is_authenticated:
            return None

        if not self._requires_mfa(user):
            self._clear_mfa_proof(request)
            return None

        if self._has_mfa_proof(request, user):
            return None

        # Logging out must always remain possible without satisfying MFA first.
        if request.path in {reverse('accounts:logout'), reverse('admin:logout')}:
            return None

        if self._is_asset_path(request.path):
            return None

        return self._begin_mfa_challenge(request)

    def _enrollment_allowed_path(self, path):
        """Paths a privileged account may still reach before enrolling."""
        allowed = {
            reverse('accounts:two_factor_setup'),
            reverse('accounts:logout'),
            reverse('admin:logout'),
        }
        return path in allowed or self._is_asset_path(path)

    def _enforce_2fa_enrollment(self, request):
        if not requires_2fa_enrollment(request.user):
            return None

        if self._enrollment_allowed_path(request.path):
            return None

        return redirect('accounts:two_factor_setup')

    def _enforce_2fa_enrollment_after_view(self, request, response):
        """Catch privileged sessions created inside a view, such as Django admin.

        The request may have entered the middleware anonymous and been logged
        in by the view itself. Replacing the response with a redirect also
        stops the first protected page from reaching the browser.
        """
        if not self._is_session_authenticated(request):
            return response

        if not requires_2fa_enrollment(request.user):
            return response

        if self._enrollment_allowed_path(request.path):
            return response

        return redirect('accounts:two_factor_setup')

    def _enforce_mfa_after_view(self, request, response):
        """Catch sessions created inside a view before they can escape unverified.

        This is what closes alternate login paths such as Django admin. A view
        may call ``login()`` while the request entered this middleware as
        anonymous; the response-phase check still converts that session into a
        pending MFA challenge before the browser can reach a protected page.
        """
        user = request.user

        if not user.is_authenticated:
            return response

        if not self._is_session_authenticated(request):
            return response

        if not self._requires_mfa(user):
            self._clear_mfa_proof(request)
            return response

        if self._has_mfa_proof(request, user):
            return response

        current_path = request.path
        verify_path = reverse('accounts:two_factor_verify')
        setup_path = reverse('accounts:two_factor_setup')

        # A successful challenge logs the user in inside the verification view.
        # Mark the just-authenticated session before SessionMiddleware saves it.
        if current_path == verify_path and request.method == 'POST':
            self._mark_mfa_verified(request, user)
            return response

        # Enabling 2FA requires a valid TOTP in TwoFactorSetupView. If the POST
        # returned with 2FA enabled, that code is valid proof for this session.
        if current_path == setup_path and request.method == 'POST':
            self._mark_mfa_verified(request, user)
            return response

        if current_path in {reverse('accounts:logout'), reverse('admin:logout')}:
            return response

        return self._begin_mfa_challenge(request)
