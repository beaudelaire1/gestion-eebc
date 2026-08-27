"""Authentication enforcement for password changes and two-factor verification."""

from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import logout
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse


class ForcePasswordChangeMiddleware:
    """Enforce password rotation and MFA before sensitive application access."""

    WEB_PROTECTED_PREFIXES = ('/app/', '/gestion-eebc/')
    API_PREFIX = '/api/v1/'

    def __init__(self, get_response):
        self.get_response = get_response

    @staticmethod
    def _is_asset(path):
        return path.startswith(('/static/', '/media/', '/favicon.ico'))

    def _password_change_redirect(self, user):
        from .services import AuthenticationService

        token = AuthenticationService.generate_password_change_token(user)
        url = reverse('accounts:first_login_password_change')
        return redirect(f"{url}?{urlencode({'token': token})}")

    def _enforce_api_token_mfa(self, request):
        if not request.path.startswith(self.API_PREFIX):
            return None

        authorization = request.META.get('HTTP_AUTHORIZATION', '')
        if not authorization.startswith('Bearer '):
            return None

        from rest_framework_simplejwt.exceptions import TokenError
        from rest_framework_simplejwt.tokens import AccessToken

        from .models import User
        from .two_factor_security import needs_two_factor_verification, requires_two_factor

        raw_token = authorization.split(' ', 1)[1].strip()
        try:
            token = AccessToken(raw_token)
        except TokenError:
            return None

        user_id = token.get('user_id')
        if not user_id:
            return JsonResponse(
                {'success': False, 'error': {'code': 401, 'message': 'Jeton invalide.'}},
                status=401,
            )

        user = User.objects.filter(pk=user_id, is_active=True).first()
        if not user:
            return JsonResponse(
                {'success': False, 'error': {'code': 401, 'message': 'Compte indisponible.'}},
                status=401,
            )

        if token.get('password_change_only'):
            if request.path not in {'/api/v1/auth/password/', '/api/v1/auth/logout/'}:
                return JsonResponse(
                    {
                        'success': False,
                        'error': {
                            'code': 403,
                            'message': 'Le mot de passe doit être modifié avant tout autre accès.',
                            'must_change_password': True,
                        },
                    },
                    status=403,
                )
            return None

        if requires_two_factor(user) and not user.two_factor_enabled:
            return JsonResponse(
                {
                    'success': False,
                    'error': {
                        'code': 403,
                        'message': 'La double authentification doit être configurée.',
                        'two_factor_setup_required': True,
                    },
                },
                status=403,
            )

        if needs_two_factor_verification(user) and token.get('mfa') is not True:
            return JsonResponse(
                {
                    'success': False,
                    'error': {
                        'code': 401,
                        'message': 'Une nouvelle authentification avec 2FA est requise.',
                        'two_factor_required': True,
                    },
                },
                status=401,
            )
        return None

    def _enforce_web_mfa(self, request):
        if not request.user.is_authenticated:
            return None
        if not request.path.startswith(self.WEB_PROTECTED_PREFIXES):
            return None

        from .two_factor_security import needs_two_factor_verification, requires_two_factor

        setup_path = reverse('accounts:two_factor_setup')
        verify_path = reverse('accounts:two_factor_verify')
        login_path = reverse('accounts:login')
        logout_path = reverse('accounts:logout')
        user = request.user

        if request.path in {verify_path, login_path, logout_path}:
            return None

        # L'écran de configuration est exempté uniquement pendant le premier enrôlement.
        # Une fois la 2FA active, il requiert lui aussi une session ayant passé le MFA.
        if request.path == setup_path and not user.two_factor_enabled:
            return None

        if requires_two_factor(user) and not user.two_factor_enabled:
            request.session['two_factor_next'] = request.get_full_path()
            return redirect('accounts:two_factor_setup')

        if needs_two_factor_verification(user):
            verified_user_id = request.session.get('two_factor_verified_user_id')
            if verified_user_id != user.pk:
                request.session['two_factor_user_id'] = user.pk
                request.session['two_factor_next'] = request.get_full_path()
                return redirect('accounts:two_factor_verify')
        return None

    def __call__(self, request):
        current_path = request.path
        if self._is_asset(current_path):
            return self.get_response(request)

        enforce_mfa = getattr(settings, 'TWO_FACTOR_ENFORCEMENT_ENABLED', True)
        if enforce_mfa:
            api_response = self._enforce_api_token_mfa(request)
            if api_response is not None:
                return api_response

        if (
            request.user.is_authenticated
            and getattr(request.user, 'must_change_password', False)
        ):
            first_login_path = reverse('accounts:first_login_password_change')
            logout_path = reverse('accounts:logout')
            login_path = reverse('accounts:login')

            if current_path == first_login_path:
                return self.get_response(request)
            if current_path in {login_path, logout_path}:
                logout(request)
                return self.get_response(request)
            return self._password_change_redirect(request.user)

        if enforce_mfa:
            mfa_response = self._enforce_web_mfa(request)
            if mfa_response is not None:
                return mfa_response

        return self.get_response(request)
