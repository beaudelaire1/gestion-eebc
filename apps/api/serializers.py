"""
Serializers for the EEBC Mobile API.
"""
from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.members.models import Member
from apps.events.models import Event, EventRegistration
from apps.worship.models import WorshipService, ServiceRole, ScheduledService, RoleAssignment
from apps.communication.models import Announcement
from apps.finance.models import FinancialTransaction, OnlineDonation, TaxReceipt
from apps.core.models import Site, Family

User = get_user_model()


# =============================================================================
# AUTHENTICATION SERIALIZERS
# =============================================================================

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom token serializer that includes user info and handles lockout.
    """
    
    def validate(self, attrs):
        # Check if user exists and is locked
        username = attrs.get('username')
        try:
            user = User.objects.get(username=username)
            if user.is_locked():
                remaining = (user.locked_until - timezone.now()).seconds // 60
                raise serializers.ValidationError({
                    'detail': f'Compte verrouillé. Réessayez dans {remaining} minutes.',
                    'locked': True,
                    'remaining_minutes': remaining
                })
        except User.DoesNotExist:
            pass
        
        try:
            data = super().validate(attrs)
        except Exception as e:
            # Record failed attempt
            try:
                user = User.objects.get(username=username)
                user.record_failed_attempt(
                    lockout_minutes=getattr(settings, 'API_LOCKOUT_DURATION_MINUTES', 15),
                    max_attempts=getattr(settings, 'API_MAX_LOGIN_ATTEMPTS', 5)
                )
            except User.DoesNotExist:
                pass
            raise
        
        # Reset failed attempts on successful login
        user = self.user
        user.reset_failed_attempts()
        
        # Add custom claims
        data['user'] = UserSerializer(user).data
        data['must_change_password'] = user.must_change_password
        
        return data
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Add custom claims
        token['username'] = user.username
        token['role'] = user.role
        token['must_change_password'] = user.must_change_password
        
        return token


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change."""
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, min_length=8)
    confirm_password = serializers.CharField(required=True, write_only=True)
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Mot de passe actuel incorrect')
        return value
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({
                'confirm_password': 'Les mots de passe ne correspondent pas'
            })
        return attrs


# =============================================================================
# USER & PROFILE SERIALIZERS
# =============================================================================

class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model."""
    member_id = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'phone', 'photo', 'member_id'
        ]
        read_only_fields = ['id', 'username', 'role']
    
    def get_member_id(self, obj):
        if hasattr(obj, 'member_profile') and obj.member_profile:
            return obj.member_profile.id
        return None


class ProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile with member info."""
    member = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'phone', 'photo', 'member'
        ]
        read_only_fields = ['id', 'username', 'role']
    
    def get_member(self, obj):
        if hasattr(obj, 'member_profile') and obj.member_profile:
            return MemberDetailSerializer(obj.member_profile).data
        return None


# =============================================================================
# SITE SERIALIZER
# =============================================================================

class SiteSerializer(serializers.ModelSerializer):
    """Serializer for Site model."""
    
    class Meta:
        model = Site
        fields = ['id', 'code', 'name', 'address', 'city', 'phone', 'email']


# =============================================================================
# MEMBER SERIALIZERS
# =============================================================================

class FamilyMemberSerializer(serializers.ModelSerializer):
    """Serializer for family member summary."""
    relationship = serializers.CharField(source='family_role')
    
    class Meta:
        model = Member
        fields = ['id', 'first_name', 'last_name', 'relationship']


class FamilyInfoSerializer(serializers.ModelSerializer):
    """Serializer for family info."""
    members = serializers.SerializerMethodField()
    
    class Meta:
        model = Family
        fields = ['id', 'name', 'members']
    
    def get_members(self, obj):
        members = obj.members.exclude(id=self.context.get('exclude_member_id'))
        return FamilyMemberSerializer(members, many=True).data


class MemberListSerializer(serializers.ModelSerializer):
    """Serializer for member list view."""
    site = SiteSerializer(read_only=True)
    
    class Meta:
        model = Member
        fields = [
            'id', 'member_id', 'first_name', 'last_name', 'email',
            'phone', 'photo', 'status', 'site'
        ]


class MemberDetailSerializer(serializers.ModelSerializer):
    """Serializer for member detail view."""
    site = SiteSerializer(read_only=True)
    family = serializers.SerializerMethodField()
    age = serializers.ReadOnlyField()
    full_name = serializers.ReadOnlyField()
    
    class Meta:
        model = Member
        fields = [
            'id', 'member_id', 'first_name', 'last_name', 'full_name',
            'email', 'phone', 'whatsapp_number', 'photo',
            'date_of_birth', 'age', 'gender', 'marital_status',
            'address', 'city', 'postal_code',
            'is_baptized', 'baptism_date', 'status',
            'family', 'site'
        ]
    
    def get_family(self, obj):
        if obj.family:
            return FamilyInfoSerializer(
                obj.family,
                context={'exclude_member_id': obj.id}
            ).data
        return None


# =============================================================================
# EVENT SERIALIZERS
# =============================================================================

class EventListSerializer(serializers.ModelSerializer):
    """Serializer for event list view."""
    site = SiteSerializer(read_only=True)
    is_user_registered = serializers.SerializerMethodField()
    current_participants = serializers.SerializerMethodField()
    
    class Meta:
        model = Event
        fields = [
            'id', 'title', 'description', 'start_date', 'start_time',
            'end_date', 'end_time', 'location', 'all_day',
            'is_cancelled', 'color', 'site', 'is_user_registered',
            'current_participants'
        ]
    
    def get_is_user_registered(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.registrations.filter(user=request.user).exists()
        return False
    
    def get_current_participants(self, obj):
        return obj.registrations.count()


class EventDetailSerializer(EventListSerializer):
    """Serializer for event detail view."""
    allows_registration = serializers.SerializerMethodField()
    max_participants = serializers.SerializerMethodField()
    
    class Meta(EventListSerializer.Meta):
        fields = EventListSerializer.Meta.fields + [
            'address', 'allows_registration', 'max_participants'
        ]
    
    def get_allows_registration(self, obj):
        return obj.visibility != Event.Visibility.PRIVATE
    
    def get_max_participants(self, obj):
        return None  # No max by default


class EventRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for event registration."""
    
    class Meta:
        model = EventRegistration
        fields = ['id', 'event', 'user', 'registered_at', 'notes']
        read_only_fields = ['id', 'user', 'registered_at']


# =============================================================================
# WORSHIP SERIALIZERS
# =============================================================================

class MemberSummarySerializer(serializers.ModelSerializer):
    """Brief member info for assignments."""
    
    class Meta:
        model = Member
        fields = ['id', 'first_name', 'last_name', 'photo']


class ServiceRoleSerializer(serializers.ModelSerializer):
    """Serializer for service role."""
    member = MemberSummarySerializer(read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    is_current_user = serializers.SerializerMethodField()
    
    class Meta:
        model = ServiceRole
        fields = [
            'id', 'role', 'role_display', 'member', 'status',
            'is_current_user', 'notes'
        ]
    
    def get_is_current_user(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            if hasattr(request.user, 'member_profile') and request.user.member_profile:
                return obj.member_id == request.user.member_profile.id
        return False


class WorshipServiceListSerializer(serializers.ModelSerializer):
    """Serializer for worship service list."""
    date = serializers.DateField(source='event.start_date')
    start_time = serializers.TimeField(source='event.start_time')
    site = SiteSerializer(source='event.site', read_only=True)
    user_assignments = serializers.SerializerMethodField()
    
    class Meta:
        model = WorshipService
        fields = [
            'id', 'date', 'start_time', 'service_type', 'theme',
            'is_confirmed', 'site', 'user_assignments'
        ]
    
    def get_user_assignments(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            if hasattr(request.user, 'member_profile') and request.user.member_profile:
                roles = obj.roles.filter(member=request.user.member_profile)
                return ServiceRoleSerializer(roles, many=True, context=self.context).data
        return []


class WorshipServiceDetailSerializer(WorshipServiceListSerializer):
    """Serializer for worship service detail."""
    assignments = ServiceRoleSerializer(source='roles', many=True, read_only=True)
    
    class Meta(WorshipServiceListSerializer.Meta):
        fields = WorshipServiceListSerializer.Meta.fields + [
            'bible_text', 'sermon_title', 'assignments'
        ]


class RoleAssignmentSerializer(serializers.ModelSerializer):
    """Serializer for role assignment confirmation."""
    service_date = serializers.DateField(source='scheduled_service.date', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    
    class Meta:
        model = RoleAssignment
        fields = [
            'id', 'role', 'role_display', 'status', 'service_date',
            'decline_reason', 'suggested_replacement'
        ]
        read_only_fields = ['id', 'role', 'service_date']


# =============================================================================
# ANNOUNCEMENT SERIALIZERS
# =============================================================================

class AnnouncementListSerializer(serializers.ModelSerializer):
    """Serializer for announcement list."""
    excerpt = serializers.SerializerMethodField()
    author = serializers.CharField(source='created_by.get_full_name', read_only=True)
    is_read = serializers.SerializerMethodField()
    
    class Meta:
        model = Announcement
        fields = [
            'id', 'title', 'excerpt', 'is_pinned', 'priority',
            'start_date', 'author', 'is_read'
        ]
    
    def get_excerpt(self, obj):
        return obj.content[:200] + '...' if len(obj.content) > 200 else obj.content
    
    def get_is_read(self, obj):
        from .models import AnnouncementReadStatus
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return AnnouncementReadStatus.objects.filter(
                user=request.user,
                announcement=obj
            ).exists()
        return False


class AnnouncementDetailSerializer(serializers.ModelSerializer):
    """Serializer for announcement detail."""
    author = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = Announcement
        fields = [
            'id', 'title', 'content', 'is_pinned', 'priority',
            'start_date', 'end_date', 'author', 'created_at'
        ]


# =============================================================================
# DONATION SERIALIZERS
# =============================================================================

class DonationListSerializer(serializers.ModelSerializer):
    """Serializer for donation list."""
    donation_type_display = serializers.CharField(
        source='get_donation_type_display', read_only=True
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = OnlineDonation
        fields = [
            'id', 'amount', 'donation_type', 'donation_type_display',
            'status', 'status_display', 'is_recurring', 'created_at'
        ]


class DonationCreateSerializer(serializers.Serializer):
    """Serializer for creating a donation."""
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=1)
    donation_type = serializers.ChoiceField(choices=OnlineDonation.DonationType.choices)
    is_recurring = serializers.BooleanField(default=False)
    recurring_interval = serializers.ChoiceField(
        choices=[('month', 'Mensuel'), ('year', 'Annuel')],
        required=False
    )
    
    def validate(self, attrs):
        if attrs.get('is_recurring') and not attrs.get('recurring_interval'):
            raise serializers.ValidationError({
                'recurring_interval': 'Requis pour les dons récurrents'
            })
        return attrs


class TaxReceiptSerializer(serializers.ModelSerializer):
    """Serializer for tax receipts."""
    
    class Meta:
        model = TaxReceipt
        fields = [
            'id', 'receipt_number', 'fiscal_year', 'total_amount',
            'status', 'issue_date', 'pdf_file'
        ]


# =============================================================================
# DEVICE TOKEN SERIALIZER
# =============================================================================

class DeviceTokenSerializer(serializers.Serializer):
    """Serializer for device token registration."""
    token = serializers.CharField(required=True)
    platform = serializers.ChoiceField(choices=['ios', 'android'], required=True)
    device_name = serializers.CharField(required=False, allow_blank=True)
