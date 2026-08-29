"""Authentication views for the mobile API.

A password match is not considered a fully authenticated session when the
account requires an initial password change or MFA.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core import signing
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.services import AuthenticationService
from apps.core.security import revoke_user_refresh_tokens
from .serializers import UserSerializer

User = get_user_model()
PASSWORD_CHANGE_SALT = 'api-initial-password-change-v1'
PASSWORD_CHANGE_MAX_AGE = 15 * 60


def _issue_tokens(user):
    refresh = RefreshToken.for_user(user)
    refresh['username'] = user.username
    refresh['role'] = user.role
    refresh['must_change_password'] = user.must_change_password
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': UserSerializer(user).data,
        'must_change_password': user.must_change_password,
    }


def _password_change_challenge(user):
    return signing.dumps(
        {'user_id': user.pk, 'password_hash': user.password},
        salt=PASSWORD_CHANGE_SALT,
        compress=True,
    )


class CustomTokenObtainPairView(APIView):
    """Secure login endpoint: password -> mandatory change -> MFA -> tokens."""
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        username = str(request.data.get('username') or '').strip()
        password = request.data.get('password') or ''
        if not username or not password:
            return Response({
                'success': False,
                'error': {'code': 400, 'message': 'Identifiants requis'},
            }, status=status.HTTP_400_BAD_REQUEST)

        user, error_message = AuthenticationService.authenticate_user(
            username=username,
            password=password,
            request=request,
        )
        if user is None:
            return Response({
                'success': False,
                'error': {'code': 401, 'message': error_message or 'Identifiants invalides'},
            }, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            return Response({
                'success': False,
                'error': {'code': 403, 'message': 'Compte désactivé'},
            }, status=status.HTTP_403_FORBIDDEN)

        if user.must_change_password:
            # Never mint a normal access/refresh token for a temporary password.
            return Response({
                'success': False,
                'error': {
                    'code': 'password_change_required',
                    'message': 'Le mot de passe temporaire doit être remplacé avant connexion.',
                },
                'data': {
                    'password_change_required': True,
                    'password_change_challenge': _password_change_challenge(user),
                },
            }, status=status.HTTP_403_FORBIDDEN)

        if user.two_factor_enabled:
            code = str(request.data.get('two_factor_code') or '').strip()
            if not code:
                return Response({
                    'success': False,
                    'error': {
                        'code': 'mfa_required',
                        'message': 'Un code de double authentification est requis.',
                    },
                    'data': {'mfa_required': True},
                }, status=428)
            if not user.verify_two_factor_code(code):
                return Response({
                    'success': False,
                    'error': {'code': 'mfa_invalid', 'message': 'Code de double authentification invalide.'},
                }, status=status.HTTP_401_UNAUTHORIZED)

        return Response({'success': True, 'data': _issue_tokens(user)})


class InitialPasswordChangeView(APIView):
    """Replace a temporary password using a short-lived, password-bound challenge."""
    permission_classes = [AllowAny]

    def post(self, request):
        challenge = request.data.get('challenge') or ''
        new_password = request.data.get('new_password') or ''
        confirm_password = request.data.get('confirm_password') or ''
        if not challenge or not new_password or new_password != confirm_password:
            return Response({
                'success': False,
                'error': {'code': 400, 'message': 'Challenge ou confirmation de mot de passe invalide.'},
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            payload = signing.loads(
                challenge,
                salt=PASSWORD_CHANGE_SALT,
                max_age=PASSWORD_CHANGE_MAX_AGE,
            )
            user = User.objects.get(pk=payload.get('user_id'), is_active=True)
        except (signing.BadSignature, signing.SignatureExpired, User.DoesNotExist):
            return Response({
                'success': False,
                'error': {'code': 401, 'message': 'Challenge expiré ou invalide.'},
            }, status=status.HTTP_401_UNAUTHORIZED)

        if payload.get('password_hash') != user.password or not user.must_change_password:
            return Response({
                'success': False,
                'error': {'code': 401, 'message': 'Challenge déjà utilisé ou invalide.'},
            }, status=status.HTTP_401_UNAUTHORIZED)

        try:
            validate_password(new_password, user=user)
        except DjangoValidationError as exc:
            return Response({
                'success': False,
                'error': {'code': 400, 'message': 'Mot de passe insuffisant.', 'details': exc.messages},
            }, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.must_change_password = False
        user.save(update_fields=['password', 'must_change_password'])
        revoke_user_refresh_tokens(user)

        # MFA accounts must authenticate again with password + TOTP. No token is minted here.
        if user.two_factor_enabled:
            return Response({
                'success': True,
                'message': 'Mot de passe modifié. Double authentification requise pour terminer la connexion.',
                'data': {'mfa_required': True},
            })

        return Response({
            'success': True,
            'message': 'Mot de passe modifié avec succès.',
            'data': _issue_tokens(user),
        })


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({'success': True, 'message': 'Déconnexion réussie'})
        try:
            RefreshToken(refresh_token).blacklist()
        except Exception:
            return Response({
                'success': False,
                'error': {'code': 400, 'message': 'Token invalide'},
            }, status=status.HTTP_400_BAD_REQUEST)
        return Response({'success': True, 'message': 'Déconnexion réussie'})


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        user = request.user
        old_password = request.data.get('old_password') or ''
        new_password = request.data.get('new_password') or ''
        confirm_password = request.data.get('confirm_password') or ''

        if not user.check_password(old_password):
            return Response({
                'success': False,
                'error': {'code': 400, 'message': 'Mot de passe actuel incorrect.'},
            }, status=status.HTTP_400_BAD_REQUEST)
        if not new_password or new_password != confirm_password:
            return Response({
                'success': False,
                'error': {'code': 400, 'message': 'Les nouveaux mots de passe ne correspondent pas.'},
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            validate_password(new_password, user=user)
        except DjangoValidationError as exc:
            return Response({
                'success': False,
                'error': {'code': 400, 'message': 'Mot de passe insuffisant.', 'details': exc.messages},
            }, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.must_change_password = False
        user.save(update_fields=['password', 'must_change_password'])
        revoke_user_refresh_tokens(user)

        # New tokens are created only after all old refresh tokens were blacklisted.
        return Response({
            'success': True,
            'message': 'Mot de passe modifié avec succès',
            'data': _issue_tokens(user),
        })
