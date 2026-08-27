"""MFA-aware authentication endpoints for the EEBC mobile API."""

from django.urls import reverse
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts.models import User
from apps.accounts.services import AuthenticationService
from apps.accounts.two_factor_security import (
    clear_mfa_failures,
    is_mfa_locked,
    needs_two_factor_verification,
    record_mfa_failure,
    requires_two_factor,
    verify_second_factor,
)

from .serializers import ChangePasswordSerializer, UserSerializer


def _issue_tokens(user, *, mfa_verified=False, password_change_only=False):
    refresh = RefreshToken.for_user(user)
    refresh['username'] = user.username
    refresh['role'] = user.role
    refresh['must_change_password'] = user.must_change_password
    refresh['mfa'] = bool(mfa_verified)
    refresh['password_change_only'] = bool(password_change_only)
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
    }


def _setup_url(request):
    path = reverse('accounts:two_factor_setup')
    return request.build_absolute_uri(path)


def _verify_mfa_with_rate_limit(user, code):
    if is_mfa_locked(user.pk):
        return False, 'locked', 0

    if verify_second_factor(user, code):
        clear_mfa_failures(user.pk)
        return True, None, 0

    locked, remaining = record_mfa_failure(user.pk)
    return False, 'locked' if locked else 'invalid', remaining


class SecureTokenObtainPairView(APIView):
    """Issue JWTs only after password and, when applicable, TOTP verification."""

    permission_classes = [AllowAny]

    def post(self, request):
        username = str(request.data.get('username', '')).strip()
        password = str(request.data.get('password', ''))
        otp = str(request.data.get('otp', '')).strip()

        if not username or not password:
            return Response(
                {
                    'success': False,
                    'error': {'code': 400, 'message': 'Identifiant et mot de passe requis.'},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user, error_message = AuthenticationService.authenticate_user(
            username=username,
            password=password,
            request=request,
        )
        if user is None:
            return Response(
                {
                    'success': False,
                    'error': {
                        'code': 401,
                        'message': error_message or 'Identifiants invalides.',
                    },
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        mfa_verified = False
        if user.two_factor_enabled:
            if not otp:
                return Response(
                    {
                        'success': False,
                        'error': {
                            'code': 401,
                            'message': 'Code de double authentification requis.',
                            'two_factor_required': True,
                        },
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            valid, reason, remaining = _verify_mfa_with_rate_limit(user, otp)
            if not valid:
                response_code = 429 if reason == 'locked' else 401
                message = (
                    'Trop de codes invalides. Réessayez dans 10 minutes.'
                    if reason == 'locked'
                    else f'Code invalide. {remaining} tentative(s) restante(s).'
                )
                return Response(
                    {
                        'success': False,
                        'error': {
                            'code': response_code,
                            'message': message,
                            'two_factor_required': True,
                        },
                    },
                    status=response_code,
                )
            mfa_verified = True

        if user.must_change_password:
            tokens = _issue_tokens(
                user,
                mfa_verified=mfa_verified,
                password_change_only=True,
            )
            return Response(
                {
                    'success': True,
                    'data': {
                        **tokens,
                        'user': UserSerializer(user, context={'request': request}).data,
                        'must_change_password': True,
                        'password_change_only': True,
                    },
                }
            )

        if requires_two_factor(user) and not user.two_factor_enabled:
            return Response(
                {
                    'success': False,
                    'error': {
                        'code': 403,
                        'message': 'La double authentification doit être configurée avant l’accès mobile.',
                        'two_factor_setup_required': True,
                        'setup_url': _setup_url(request),
                    },
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if needs_two_factor_verification(user) and not mfa_verified:
            return Response(
                {
                    'success': False,
                    'error': {
                        'code': 401,
                        'message': 'Code de double authentification requis.',
                        'two_factor_required': True,
                    },
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        tokens = _issue_tokens(user, mfa_verified=mfa_verified)
        return Response(
            {
                'success': True,
                'data': {
                    **tokens,
                    'user': UserSerializer(user, context={'request': request}).data,
                    'must_change_password': False,
                    'two_factor_verified': mfa_verified,
                },
            }
        )


class SecureTokenRefreshView(TokenRefreshView):
    """Reject refresh tokens created before MFA enforcement or without MFA proof."""

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        raw_refresh = request.data.get('refresh')
        if not raw_refresh:
            return Response({'detail': 'Refresh token requis.'}, status=400)

        try:
            token = RefreshToken(raw_refresh)
        except TokenError:
            return Response({'detail': 'Refresh token invalide.'}, status=401)

        if token.get('password_change_only'):
            return Response(
                {
                    'detail': 'Le mot de passe doit être modifié avant de renouveler la session.',
                    'must_change_password': True,
                },
                status=403,
            )

        user_id = token.get('user_id')
        user = User.objects.filter(pk=user_id, is_active=True).first()
        if not user:
            return Response({'detail': 'Compte indisponible.'}, status=401)

        if requires_two_factor(user) and not user.two_factor_enabled:
            return Response(
                {
                    'detail': 'Configuration 2FA requise.',
                    'two_factor_setup_required': True,
                    'setup_url': _setup_url(request),
                },
                status=403,
            )

        if needs_two_factor_verification(user) and token.get('mfa') is not True:
            return Response(
                {
                    'detail': 'Réauthentification avec 2FA requise.',
                    'two_factor_required': True,
                },
                status=401,
            )
        return super().post(request, *args, **kwargs)


class SecureChangePasswordView(APIView):
    """Rotate password, revoke old refresh tokens, then enforce the current MFA policy."""

    permission_classes = [IsAuthenticated]

    def put(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(
                {
                    'success': False,
                    'error': {
                        'code': 400,
                        'message': 'Données invalides',
                        'details': serializer.errors,
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.must_change_password = False
        user.save(update_fields=['password', 'must_change_password'])

        for outstanding in OutstandingToken.objects.filter(user=user):
            BlacklistedToken.objects.get_or_create(token=outstanding)

        if requires_two_factor(user) and not user.two_factor_enabled:
            return Response(
                {
                    'success': True,
                    'message': 'Mot de passe modifié. Configurez maintenant la double authentification.',
                    'data': {
                        'two_factor_setup_required': True,
                        'setup_url': _setup_url(request),
                    },
                }
            )

        mfa_verified = bool(getattr(request.auth, 'get', lambda *_: False)('mfa', False))
        if needs_two_factor_verification(user) and not mfa_verified:
            return Response(
                {
                    'success': True,
                    'message': 'Mot de passe modifié. Une nouvelle connexion avec 2FA est requise.',
                    'data': {'two_factor_required': True},
                }
            )

        tokens = _issue_tokens(user, mfa_verified=mfa_verified)
        return Response(
            {
                'success': True,
                'message': 'Mot de passe modifié avec succès',
                'data': tokens,
            }
        )
