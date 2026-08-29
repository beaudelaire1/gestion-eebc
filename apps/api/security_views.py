"""Secure API variants for resources with object-level confidentiality."""
from datetime import date, timedelta

from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.security import can_view_sensitive_member_data, event_visibility_q
from apps.events.models import Event, EventRegistration
from apps.members.models import Member
from apps.worship.models import WorshipService

from . import views as legacy_views
from .serializers import EventListSerializer, WorshipServiceListSerializer


def _visible_event_ids(user):
    return Event.objects.filter(event_visibility_q(user)).values_list('pk', flat=True)


class SafeMemberDirectorySerializer(serializers.ModelSerializer):
    """Non-sensitive member identity fields for the ordinary mobile directory."""

    class Meta:
        model = Member
        fields = ('id', 'member_id', 'first_name', 'last_name', 'photo', 'site')
        read_only_fields = fields


class SecureMemberViewSet(legacy_views.MemberViewSet):
    """Keep a useful directory while reserving personal details for staff."""
    permission_classes = [IsAuthenticated]
    # Never allow phone/email as a search oracle for ordinary API consumers.
    search_fields = ['first_name', 'last_name']

    def get_serializer_class(self):
        if can_view_sensitive_member_data(self.request.user):
            return super().get_serializer_class()
        return SafeMemberDirectorySerializer


class SecureEventViewSet(legacy_views.EventViewSet):
    """Make Event.visibility an executable policy, including list endpoints."""

    def get_queryset(self):
        return super().get_queryset().filter(event_visibility_q(self.request.user)).distinct()

    @action(detail=False, methods=['get'])
    def my_registrations(self, request):
        registrations = EventRegistration.objects.filter(
            user=request.user,
            event__start_date__gte=date.today(),
            event_id__in=_visible_event_ids(request.user),
        ).select_related('event')
        serializer = EventListSerializer(
            [registration.event for registration in registrations],
            many=True,
            context={'request': request},
        )
        return Response({'success': True, 'data': serializer.data})


class SecureEventRegistrationView(legacy_views.EventRegistrationView):
    def _visible_event(self, request, pk):
        return get_object_or_404(
            Event.objects.filter(event_visibility_q(request.user)).distinct(),
            pk=pk,
        )

    def post(self, request, pk):
        self._visible_event(request, pk)
        return super().post(request, pk)

    def delete(self, request, pk):
        self._visible_event(request, pk)
        return super().delete(request, pk)


class SecureWorshipServiceViewSet(legacy_views.WorshipServiceViewSet):
    """A worship service must not leak an Event hidden by Event.visibility."""

    def get_queryset(self):
        queryset = WorshipService.objects.filter(
            event__start_date__gte=date.today() - timedelta(days=7),
            event_id__in=_visible_event_ids(self.request.user),
        ).select_related('event', 'event__site').prefetch_related('roles', 'roles__member')
        site_id = self.request.query_params.get('site')
        if site_id:
            queryset = queryset.filter(event__site_id=site_id)
        return queryset.distinct()

    @action(detail=False, methods=['get'])
    def history(self, request):
        three_months_ago = date.today() - timedelta(days=90)
        queryset = WorshipService.objects.filter(
            event__start_date__gte=three_months_ago,
            event__start_date__lt=date.today(),
            event_id__in=_visible_event_ids(request.user),
        ).select_related('event', 'event__site').distinct()
        serializer = WorshipServiceListSerializer(
            queryset, many=True, context={'request': request}
        )
        return Response({'success': True, 'data': serializer.data})
