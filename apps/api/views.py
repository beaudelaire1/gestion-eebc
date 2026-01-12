"""
API Views for EEBC Mobile App.
"""
from datetime import date, timedelta
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, status, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend

from apps.members.models import Member
from apps.events.models import Event, EventRegistration
from apps.worship.models import WorshipService, RoleAssignment
from apps.communication.models import Announcement
from apps.finance.models import OnlineDonation, TaxReceipt

from .serializers import (
    MemberListSerializer, MemberDetailSerializer,
    EventListSerializer, EventDetailSerializer, EventRegistrationSerializer,
    WorshipServiceListSerializer, WorshipServiceDetailSerializer,
    RoleAssignmentSerializer,
    AnnouncementListSerializer, AnnouncementDetailSerializer,
    DonationListSerializer, DonationCreateSerializer, TaxReceiptSerializer,
    ProfileSerializer, DeviceTokenSerializer,
)


# =============================================================================
# MEMBER VIEWSET
# =============================================================================

class MemberViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing members (directory).
    
    GET /api/v1/members/ - List active members
    GET /api/v1/members/{id}/ - Member detail
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['first_name', 'last_name', 'email', 'phone']
    ordering_fields = ['last_name', 'first_name']
    ordering = ['last_name', 'first_name']
    
    def get_queryset(self):
        """Return active members only, respecting privacy settings."""
        queryset = Member.objects.filter(status='actif').select_related('site', 'family')
        
        # Filter by site if specified
        site_id = self.request.query_params.get('site')
        if site_id:
            queryset = queryset.filter(site_id=site_id)
        
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return MemberDetailSerializer
        return MemberListSerializer


# =============================================================================
# EVENT VIEWSET
# =============================================================================

class EventViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing events.
    
    GET /api/v1/events/ - List upcoming events
    GET /api/v1/events/{id}/ - Event detail
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description', 'location']
    ordering_fields = ['start_date', 'start_time']
    ordering = ['start_date', 'start_time']
    
    def get_queryset(self):
        """Return upcoming events."""
        queryset = Event.objects.filter(
            is_cancelled=False,
            start_date__gte=date.today()
        ).select_related('site', 'category')
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(start_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(start_date__lte=end_date)
        
        # Filter by site
        site_id = self.request.query_params.get('site')
        if site_id:
            queryset = queryset.filter(Q(site_id=site_id) | Q(site__isnull=True))
        
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return EventDetailSerializer
        return EventListSerializer
    
    @action(detail=False, methods=['get'])
    def my_registrations(self, request):
        """Get events the user is registered for."""
        registrations = EventRegistration.objects.filter(
            user=request.user,
            event__start_date__gte=date.today()
        ).select_related('event')
        
        events = [reg.event for reg in registrations]
        serializer = EventListSerializer(events, many=True, context={'request': request})
        
        return Response({
            'success': True,
            'data': serializer.data
        })


class EventRegistrationView(APIView):
    """
    View for registering/unregistering for an event.
    
    POST /api/v1/events/{id}/register/ - Register for event
    DELETE /api/v1/events/{id}/register/ - Unregister from event
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        """Register for an event."""
        event = get_object_or_404(Event, pk=pk)
        
        if event.is_cancelled:
            return Response({
                'success': False,
                'error': {'message': 'Cet événement est annulé'}
            }, status=status.HTTP_400_BAD_REQUEST)
        
        registration, created = EventRegistration.objects.get_or_create(
            event=event,
            user=request.user,
            defaults={'notes': request.data.get('notes', '')}
        )
        
        if not created:
            return Response({
                'success': False,
                'error': {'message': 'Vous êtes déjà inscrit à cet événement'}
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'success': True,
            'message': 'Inscription réussie',
            'data': EventRegistrationSerializer(registration).data
        }, status=status.HTTP_201_CREATED)
    
    def delete(self, request, pk):
        """Unregister from an event."""
        event = get_object_or_404(Event, pk=pk)
        
        try:
            registration = EventRegistration.objects.get(event=event, user=request.user)
            registration.delete()
            return Response({
                'success': True,
                'message': 'Désinscription réussie'
            })
        except EventRegistration.DoesNotExist:
            return Response({
                'success': False,
                'error': {'message': 'Vous n\'êtes pas inscrit à cet événement'}
            }, status=status.HTTP_400_BAD_REQUEST)


# =============================================================================
# WORSHIP VIEWSET
# =============================================================================

class WorshipServiceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing worship services.
    
    GET /api/v1/worship/services/ - List upcoming services
    GET /api/v1/worship/services/{id}/ - Service detail
    """
    permission_classes = [IsAuthenticated]
    ordering = ['-event__start_date']
    
    def get_queryset(self):
        """Return upcoming worship services."""
        queryset = WorshipService.objects.filter(
            event__start_date__gte=date.today() - timedelta(days=7)
        ).select_related('event', 'event__site').prefetch_related('roles', 'roles__member')
        
        # Filter by site
        site_id = self.request.query_params.get('site')
        if site_id:
            queryset = queryset.filter(event__site_id=site_id)
        
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return WorshipServiceDetailSerializer
        return WorshipServiceListSerializer
    
    @action(detail=False, methods=['get'])
    def my_assignments(self, request):
        """Get services where the user has assignments."""
        if not hasattr(request.user, 'member_profile') or not request.user.member_profile:
            return Response({
                'success': True,
                'data': []
            })
        
        member = request.user.member_profile
        services = WorshipService.objects.filter(
            roles__member=member,
            event__start_date__gte=date.today()
        ).distinct().select_related('event', 'event__site')
        
        serializer = WorshipServiceListSerializer(
            services, many=True, context={'request': request}
        )
        
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def history(self, request):
        """Get past services (last 3 months)."""
        three_months_ago = date.today() - timedelta(days=90)
        
        queryset = WorshipService.objects.filter(
            event__start_date__gte=three_months_ago,
            event__start_date__lt=date.today()
        ).select_related('event', 'event__site')
        
        serializer = WorshipServiceListSerializer(
            queryset, many=True, context={'request': request}
        )
        
        return Response({
            'success': True,
            'data': serializer.data
        })


class WorshipConfirmationView(APIView):
    """
    View for confirming/declining worship assignments.
    
    POST /api/v1/worship/confirm/ - Confirm or decline assignment
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Confirm or decline a role assignment."""
        assignment_id = request.data.get('assignment_id')
        action = request.data.get('action')  # 'confirm' or 'decline'
        decline_reason = request.data.get('decline_reason', '')
        
        if not assignment_id or action not in ['confirm', 'decline']:
            return Response({
                'success': False,
                'error': {'message': 'Paramètres invalides'}
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Try RoleAssignment first (new system)
        try:
            assignment = RoleAssignment.objects.get(pk=assignment_id)
            
            # Verify the assignment belongs to the user
            if not hasattr(request.user, 'member_profile') or \
               assignment.member_id != request.user.member_profile.id:
                return Response({
                    'success': False,
                    'error': {'message': 'Cette assignation ne vous appartient pas'}
                }, status=status.HTTP_403_FORBIDDEN)
            
            if action == 'confirm':
                assignment.status = RoleAssignment.Status.ACCEPTED
            else:
                assignment.status = RoleAssignment.Status.DECLINED
                assignment.decline_reason = decline_reason
            
            assignment.responded_at = timezone.now()
            assignment.save()
            
            return Response({
                'success': True,
                'message': 'Réponse enregistrée',
                'data': RoleAssignmentSerializer(assignment).data
            })
            
        except RoleAssignment.DoesNotExist:
            return Response({
                'success': False,
                'error': {'message': 'Assignation non trouvée'}
            }, status=status.HTTP_404_NOT_FOUND)


# =============================================================================
# ANNOUNCEMENT VIEWSET
# =============================================================================

class AnnouncementViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing announcements.
    
    GET /api/v1/announcements/ - List current announcements
    GET /api/v1/announcements/{id}/ - Announcement detail
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['title', 'content']
    
    def get_queryset(self):
        """Return current announcements, pinned first."""
        from django.utils import timezone
        now = timezone.now()
        
        return Announcement.objects.filter(
            is_active=True,
            start_date__lte=now
        ).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=now)
        ).order_by('-is_pinned', '-start_date')
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return AnnouncementDetailSerializer
        return AnnouncementListSerializer
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark an announcement as read."""
        from .models import AnnouncementReadStatus
        
        announcement = self.get_object()
        
        AnnouncementReadStatus.objects.get_or_create(
            user=request.user,
            announcement=announcement
        )
        
        return Response({
            'success': True,
            'message': 'Marqué comme lu'
        })


# =============================================================================
# DONATION VIEWSET
# =============================================================================

class DonationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for donations.
    
    GET /api/v1/donations/ - List user's donations
    POST /api/v1/donations/ - Create a new donation
    GET /api/v1/donations/receipts/ - List tax receipts
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return donations for the current user."""
        return OnlineDonation.objects.filter(
            Q(donor_email=self.request.user.email) |
            Q(member__user=self.request.user)
        ).order_by('-created_at')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return DonationCreateSerializer
        return DonationListSerializer
    
    def create(self, request, *args, **kwargs):
        """Create a Stripe checkout session for donation."""
        from apps.finance.stripe_service import stripe_service
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        # Check if Stripe is configured
        if not stripe_service.is_configured:
            return Response({
                'success': False,
                'error': {'message': 'Le système de paiement n\'est pas configuré'}
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        try:
            # Get member ID if user has a member profile
            member_id = None
            if hasattr(request.user, 'member_profile') and request.user.member_profile:
                member_id = request.user.member_profile.id
            
            # Create Stripe session
            if data.get('is_recurring'):
                result = stripe_service.create_recurring_donation(
                    amount=data['amount'],
                    donation_type=data['donation_type'],
                    interval=data.get('recurring_interval', 'month'),
                    donor_email=request.user.email,
                    member_id=member_id,
                )
            else:
                result = stripe_service.create_donation_session(
                    amount=data['amount'],
                    donation_type=data['donation_type'],
                    donor_email=request.user.email,
                    donor_name=request.user.get_full_name(),
                    member_id=member_id,
                )
            
            return Response({
                'success': True,
                'message': 'Session de paiement créée',
                'data': {
                    'checkout_url': result['url'],
                    'session_id': result['session_id']
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': {'message': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def receipts(self, request):
        """Get tax receipts for the user."""
        if hasattr(request.user, 'member_profile') and request.user.member_profile:
            receipts = TaxReceipt.objects.filter(
                member=request.user.member_profile,
                status__in=['issued', 'sent']
            )
        else:
            receipts = TaxReceipt.objects.filter(
                donor_email=request.user.email,
                status__in=['issued', 'sent']
            )
        
        serializer = TaxReceiptSerializer(receipts, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        })


# =============================================================================
# PROFILE VIEW
# =============================================================================

class ProfileView(APIView):
    """
    View for user profile.
    
    GET /api/v1/profile/ - Get user profile
    PUT /api/v1/profile/ - Update user profile
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get user profile."""
        serializer = ProfileSerializer(request.user)
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    def put(self, request):
        """Update user profile."""
        serializer = ProfileSerializer(request.user, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            
            # Also update member profile if exists
            if hasattr(request.user, 'member_profile') and request.user.member_profile:
                member = request.user.member_profile
                if 'phone' in request.data:
                    member.phone = request.data['phone']
                if 'email' in request.data:
                    member.email = request.data['email']
                member.save()
            
            return Response({
                'success': True,
                'message': 'Profil mis à jour',
                'data': serializer.data
            })
        
        return Response({
            'success': False,
            'error': {
                'message': 'Données invalides',
                'details': serializer.errors
            }
        }, status=status.HTTP_400_BAD_REQUEST)


# =============================================================================
# DEVICE REGISTRATION VIEW
# =============================================================================

class RegisterDeviceView(APIView):
    """
    View for registering device tokens for push notifications.
    
    POST /api/v1/notifications/register/ - Register device token
    DELETE /api/v1/notifications/register/ - Unregister device token
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Register a device token."""
        from .models import DeviceToken
        
        serializer = DeviceTokenSerializer(data=request.data)
        
        if serializer.is_valid():
            data = serializer.validated_data
            
            # Create or update the device token
            device_token, created = DeviceToken.objects.update_or_create(
                user=request.user,
                token=data['token'],
                defaults={
                    'platform': data['platform'],
                    'device_name': data.get('device_name', ''),
                    'is_active': True,
                }
            )
            
            return Response({
                'success': True,
                'message': 'Appareil enregistré' if created else 'Appareil mis à jour'
            })
        
        return Response({
            'success': False,
            'error': {
                'message': 'Données invalides',
                'details': serializer.errors
            }
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request):
        """Unregister a device token."""
        from .models import DeviceToken
        
        token = request.data.get('token')
        if not token:
            return Response({
                'success': False,
                'error': {'message': 'Token requis'}
            }, status=status.HTTP_400_BAD_REQUEST)
        
        DeviceToken.objects.filter(user=request.user, token=token).update(is_active=False)
        
        return Response({
            'success': True,
            'message': 'Appareil désenregistré'
        })
