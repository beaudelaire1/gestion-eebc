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
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import AllowAny
from django.core.cache import cache
import logging
import time

logger = logging.getLogger(__name__)

from apps.members.models import Member
from apps.events.models import Event, EventRegistration
from apps.worship.models import WorshipService, RoleAssignment
from apps.communication.models import Announcement
from apps.finance.models import OnlineDonation, TaxReceipt
from apps.core.models import (
    Site,
    NewsArticle,
    PublicEvent,
    ContactMessage,
    VisitorRegistration,
    SiteSettings,
    WorshipSchedule,
)

from .serializers import (
    MemberListSerializer, MemberDetailSerializer,
    EventListSerializer, EventDetailSerializer, EventRegistrationSerializer,
    WorshipServiceListSerializer, WorshipServiceDetailSerializer,
    RoleAssignmentSerializer,
    AnnouncementListSerializer, AnnouncementDetailSerializer,
    DonationListSerializer, DonationCreateSerializer, TaxReceiptSerializer,
    ProfileSerializer, DeviceTokenSerializer,
    PublicSiteSerializer, PublicNewsListSerializer, PublicNewsDetailSerializer,
    PublicEventListSerializer, PublicEventDetailSerializer,
    PublicWorshipScheduleSerializer, PublicSettingsSerializer,
    ContactMessageCreateSerializer, VisitorRegistrationCreateSerializer,
)

def _get_client_ip(request):
    """Extract client IP from request (handles proxy headers)."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


class PublicRateLimitMixin:
    """Basic rate limiting for public form endpoints."""
    rate_limit_count = 3
    rate_limit_window_seconds = 10 * 60
    rate_limit_scope = 'public-form'

    def _rate_limit_key(self, request):
        ip = _get_client_ip(request) or 'unknown'
        bucket = int(time.time()) // self.rate_limit_window_seconds
        return f"{self.rate_limit_scope}:{ip}:{bucket}"

    def allow_request(self, request):
        key = self._rate_limit_key(request)
        current = cache.get(key, 0)
        if current >= self.rate_limit_count:
            return False
        cache.set(key, current + 1, timeout=self.rate_limit_window_seconds)
        return True


def _get_visible_news_queryset():
    """Return public-visible news articles."""
    today = date.today()
    now = timezone.now()

    return NewsArticle.objects.filter(
        is_published=True,
        publish_date__lte=now
    ).filter(
        Q(display_start_date__isnull=True) | Q(display_start_date__lte=today)
    ).filter(
        Q(display_end_date__isnull=True) | Q(display_end_date__gte=today)
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
    permission_classes = [IsAuthenticatedOrReadOnly]
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
    permission_classes = [IsAuthenticatedOrReadOnly]
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
    permission_classes = [IsAuthenticatedOrReadOnly]
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
            logger.error(f"API donation session creation error: {e}", exc_info=True)
            return Response({
                'success': False,
                'error': {'message': 'Une erreur est survenue lors du traitement. Veuillez réessayer.'}
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


# =============================================================================
# BIBLECLUB VIEWSET
# =============================================================================

class BibleClubMyChildrenView(APIView):
    """
    View for parents to see their children's attendance at Bible Club.
    
    GET /api/v1/bibleclub/my-children/ - List user's children with attendance
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get children linked to the current user with their attendance records."""
        from apps.bibleclub.models import Child, Attendance, Session
        
        # Get children where the user is linked (by name match or direct reference)
        user_member = getattr(request.user, 'member_profile', None)
        if user_member:
            children_queryset = Child.objects.filter(
                Q(father_name__icontains=user_member.last_name) |
                Q(mother_name__icontains=user_member.last_name)
            ).prefetch_related('bible_class__age_group')
        else:
            children_queryset = Child.objects.none()
        
        # Build response data
        children_data = []
        
        for child in children_queryset:
            # Get recent attendance (last 10 sessions)
            recent_sessions = Session.objects.filter(
                is_cancelled=False
            ).order_by('-date')[:10]
            
            recent_attendance = []
            present_count = 0
            total_sessions = 0
            
            for session in recent_sessions:
                try:
                    attendance = Attendance.objects.get(child=child, session=session)
                    recent_attendance.append({
                        'id': attendance.id,
                        'sessionDate': session.date.isoformat(),
                        'sessionTheme': session.theme or '',
                        'status': attendance.status,
                        'notes': attendance.notes or '',
                    })
                    total_sessions += 1
                    if attendance.status in ['present', 'late']:
                        present_count += 1
                except Attendance.DoesNotExist:
                    pass
            
            # Calculate attendance rate
            attendance_rate = (present_count / total_sessions * 100) if total_sessions > 0 else 0
            
            children_data.append({
                'id': child.id,
                'firstName': child.first_name,
                'lastName': child.last_name,
                'dateOfBirth': child.date_of_birth.isoformat() if child.date_of_birth else None,
                'className': str(child.bible_class) if child.bible_class else '',
                'ageGroup': str(child.bible_class.age_group) if child.bible_class else '',
                'photo': request.build_absolute_uri(child.photo.url) if child.photo else None,
                'recentAttendance': recent_attendance,
                'attendanceRate': round(attendance_rate, 1),
            })
        
        return Response({
            'success': True,
            'data': children_data
        })


# =============================================================================
# PUBLIC WEBSITE API ENDPOINTS
# =============================================================================

class PublicSiteViewSet(viewsets.ReadOnlyModelViewSet):
    """Public list of church sites."""
    permission_classes = [AllowAny]
    serializer_class = PublicSiteSerializer
    queryset = Site.objects.filter(is_active=True)


class PublicNewsViewSet(viewsets.ReadOnlyModelViewSet):
    """Public news list and detail (by slug)."""
    permission_classes = [AllowAny]
    lookup_field = 'slug'
    filter_backends = [filters.SearchFilter]
    search_fields = ['title', 'content', 'excerpt']

    def get_queryset(self):
        return _get_visible_news_queryset().order_by('-is_featured', '-publish_date')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return PublicNewsDetailSerializer
        return PublicNewsListSerializer


class PublicEventViewSet(viewsets.ReadOnlyModelViewSet):
    """Public events list and detail (by slug)."""
    permission_classes = [AllowAny]
    lookup_field = 'slug'

    def get_queryset(self):
        return PublicEvent.objects.filter(
            is_published=True,
            start_date__gte=date.today()
        ).order_by('start_date')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return PublicEventDetailSerializer
        return PublicEventListSerializer


class PublicWorshipScheduleViewSet(viewsets.ReadOnlyModelViewSet):
    """Public worship schedules list."""
    permission_classes = [AllowAny]
    serializer_class = PublicWorshipScheduleSerializer

    def get_queryset(self):
        return WorshipSchedule.objects.filter(is_active=True).select_related('site')


class PublicSettingsView(APIView):
    """Public settings for the public site."""
    permission_classes = [AllowAny]

    def get(self, request):
        settings = SiteSettings.get_settings()
        serializer = PublicSettingsSerializer(settings, context={'request': request})
        return Response({'success': True, 'data': serializer.data})


class PublicMetaView(APIView):
    """Public metadata (choices for forms)."""
    permission_classes = [AllowAny]

    def get(self, request):
        subjects = [
            {'value': key, 'label': label}
            for key, label in ContactMessage.Subject.choices
        ]
        interests = [
            {'value': key, 'label': label}
            for key, label in VisitorRegistration.Interest.choices
        ]
        return Response({
            'success': True,
            'data': {
                'contact_subjects': subjects,
                'visitor_interests': interests,
            }
        })


class PublicContactView(PublicRateLimitMixin, APIView):
    """Public contact form submission."""
    permission_classes = [AllowAny]
    rate_limit_scope = 'public-contact'

    def post(self, request):
        if not self.allow_request(request):
            return Response({
                'success': False,
                'error': {'message': 'Trop de requetes. Reessayez plus tard.'}
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)

        serializer = ContactMessageCreateSerializer(data=request.data)
        if serializer.is_valid():
            contact = serializer.save()
            contact.ip_address = _get_client_ip(request)
            contact.save(update_fields=['ip_address'])

            return Response({
                'success': True,
                'message': 'Message envoye avec succes.'
            }, status=status.HTTP_201_CREATED)

        return Response({
            'success': False,
            'error': {
                'message': 'Donnees invalides',
                'details': serializer.errors
            }
        }, status=status.HTTP_400_BAD_REQUEST)


class PublicInterestView(PublicRateLimitMixin, APIView):
    """Public visitor registration form."""
    permission_classes = [AllowAny]
    rate_limit_scope = 'public-interest'

    def post(self, request):
        if not self.allow_request(request):
            return Response({
                'success': False,
                'error': {'message': 'Trop de requetes. Reessayez plus tard.'}
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)

        serializer = VisitorRegistrationCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Inscription enregistree. Nous vous contacterons bientot.'
            }, status=status.HTTP_201_CREATED)

        return Response({
            'success': False,
            'error': {
                'message': 'Donnees invalides',
                'details': serializer.errors
            }
        }, status=status.HTTP_400_BAD_REQUEST)

