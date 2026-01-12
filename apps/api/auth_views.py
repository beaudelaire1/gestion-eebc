"""
Authentication views for the mobile API.
"""
from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken

from .serializers import (
    CustomTokenObtainPairSerializer,
    ChangePasswordSerializer,
)


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom token obtain view that handles account lockout and must_change_password flag.
    """
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            # Handle different error detail formats
            error_message = 'Identifiants invalides'
            if hasattr(e, 'detail'):
                detail = e.detail
                if isinstance(detail, dict):
                    error_message = str(detail.get('detail', error_message))
                elif isinstance(detail, (list, tuple)) and len(detail) > 0:
                    error_message = str(detail[0])
                else:
                    error_message = str(detail)
            
            return Response({
                'success': False,
                'error': {
                    'code': 401,
                    'message': error_message,
                }
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        return Response({
            'success': True,
            'data': serializer.validated_data
        })


class LogoutView(APIView):
    """
    Logout view that blacklists the refresh token.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            return Response({
                'success': True,
                'message': 'Déconnexion réussie'
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': {
                    'code': 400,
                    'message': 'Token invalide'
                }
            }, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(APIView):
    """
    View for changing user password.
    """
    permission_classes = [IsAuthenticated]
    
    def put(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.must_change_password = False
            user.save()
            
            # Blacklist all existing tokens for this user
            OutstandingToken.objects.filter(user=user).delete()
            
            # Generate new tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'success': True,
                'message': 'Mot de passe modifié avec succès',
                'data': {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                }
            })
        
        return Response({
            'success': False,
            'error': {
                'code': 400,
                'message': 'Données invalides',
                'details': serializer.errors
            }
        }, status=status.HTTP_400_BAD_REQUEST)
