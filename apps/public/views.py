from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import redirect

from apps.core.models import NewsArticle, PageContent, Testimony, WorshipSchedule, PublicEvent
from .forms import NewsArticleForm, PageContentForm, TestimonyForm, WorshipScheduleForm, PublicEventForm
import logging

logger = logging.getLogger(__name__)


class CMSRoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Vérifie que l'utilisateur a les droits d'administration du CMS."""
    def test_func(self):
        user = self.request.user
        return user.is_active and (user.is_superuser or user.has_any_role('admin', 'secretariat', 'pasteur', 'communication'))

# ==================== NEWS ====================
class NewsListView(CMSRoleRequiredMixin, ListView):
    model = NewsArticle
    template_name = 'public_cms/news_list.html'
    context_object_name = 'articles'
    paginate_by = 20

class NewsCreateView(CMSRoleRequiredMixin, CreateView):
    model = NewsArticle
    form_class = NewsArticleForm
    template_name = 'public_cms/news_form.html'
    success_url = reverse_lazy('public_cms:news_list')

    def form_valid(self, form):
        form.instance.author = self.request.user
        messages.success(self.request, "Article créé avec succès.")
        return super().form_valid(form)

class NewsUpdateView(CMSRoleRequiredMixin, UpdateView):
    model = NewsArticle
    form_class = NewsArticleForm
    template_name = 'public_cms/news_form.html'
    success_url = reverse_lazy('public_cms:news_list')
    
    def form_valid(self, form):
        messages.success(self.request, "Article mis à jour.")
        return super().form_valid(form)

class NewsDeleteView(CMSRoleRequiredMixin, DeleteView):
    model = NewsArticle
    template_name = 'public_cms/news_confirm_delete.html'
    success_url = reverse_lazy('public_cms:news_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Article supprimé.")
        return super().delete(request, *args, **kwargs)

# ==================== PAGES ====================
class PageListView(CMSRoleRequiredMixin, ListView):
    model = PageContent
    template_name = 'public_cms/page_list.html'
    context_object_name = 'pages'

class PageCreateView(CMSRoleRequiredMixin, CreateView):
    model = PageContent
    form_class = PageContentForm
    template_name = 'public_cms/page_form.html'
    success_url = reverse_lazy('public_cms:page_list')
    
    def form_valid(self, form):
        form.instance.author = self.request.user
        messages.success(self.request, "Page créée.")
        return super().form_valid(form)

class PageUpdateView(CMSRoleRequiredMixin, UpdateView):
    model = PageContent
    form_class = PageContentForm
    template_name = 'public_cms/page_form.html'
    success_url = reverse_lazy('public_cms:page_list')
    
    def form_valid(self, form):
        messages.success(self.request, "Page mise à jour.")
        return super().form_valid(form)

class PageDeleteView(CMSRoleRequiredMixin, DeleteView):
    model = PageContent
    template_name = 'public_cms/page_confirm_delete.html'
    success_url = reverse_lazy('public_cms:page_list')

# ==================== TESTIMONIES ====================
class TestimonyListView(CMSRoleRequiredMixin, ListView):
    model = Testimony
    template_name = 'public_cms/testimony_list.html'
    context_object_name = 'testimonies'

class TestimonyCreateView(CMSRoleRequiredMixin, CreateView):
    model = Testimony
    form_class = TestimonyForm
    template_name = 'public_cms/testimony_form.html'
    success_url = reverse_lazy('public_cms:testimony_list')
    
    def form_valid(self, form):
        messages.success(self.request, "Témoignage ajouté.")
        return super().form_valid(form)

class TestimonyUpdateView(CMSRoleRequiredMixin, UpdateView):
    model = Testimony
    form_class = TestimonyForm
    template_name = 'public_cms/testimony_form.html'
    success_url = reverse_lazy('public_cms:testimony_list')

class TestimonyDeleteView(CMSRoleRequiredMixin, DeleteView):
    model = Testimony
    template_name = 'public_cms/testimony_confirm_delete.html'
    success_url = reverse_lazy('public_cms:testimony_list')

# ==================== SCHEDULES ====================
class ScheduleListView(CMSRoleRequiredMixin, ListView):
    model = WorshipSchedule
    template_name = 'public_cms/schedule_list.html'
    context_object_name = 'schedules'

class ScheduleCreateView(CMSRoleRequiredMixin, CreateView):
    model = WorshipSchedule
    form_class = WorshipScheduleForm
    template_name = 'public_cms/schedule_form.html'
    success_url = reverse_lazy('public_cms:schedule_list')

    def form_valid(self, form):
        messages.success(self.request, "Horaire ajouté.")
        return super().form_valid(form)

class ScheduleUpdateView(CMSRoleRequiredMixin, UpdateView):
    model = WorshipSchedule
    form_class = WorshipScheduleForm
    template_name = 'public_cms/schedule_form.html'
    success_url = reverse_lazy('public_cms:schedule_list')

class ScheduleDeleteView(CMSRoleRequiredMixin, DeleteView):
    model = WorshipSchedule
    template_name = 'public_cms/schedule_confirm_delete.html'
    success_url = reverse_lazy('public_cms:schedule_list')


# ==================== PUBLIC EVENTS ====================
class PublicEventListView(CMSRoleRequiredMixin, ListView):
    model = PublicEvent
    template_name = 'public_cms/event_list.html'
    context_object_name = 'events'
    paginate_by = 20
    ordering = ['start_date']

class PublicEventCreateView(CMSRoleRequiredMixin, CreateView):
    model = PublicEvent
    form_class = PublicEventForm
    template_name = 'public_cms/event_form.html'
    success_url = reverse_lazy('public_cms:event_list')

    def form_valid(self, form):
        messages.success(self.request, "Événement créé avec succès.")
        return super().form_valid(form)

class PublicEventUpdateView(CMSRoleRequiredMixin, UpdateView):
    model = PublicEvent
    form_class = PublicEventForm
    template_name = 'public_cms/event_form.html'
    success_url = reverse_lazy('public_cms:event_list')

    def form_valid(self, form):
        messages.success(self.request, "Événement mis à jour.")
        return super().form_valid(form)

class PublicEventDeleteView(CMSRoleRequiredMixin, DeleteView):
    model = PublicEvent
    template_name = 'public_cms/event_confirm_delete.html'
    success_url = reverse_lazy('public_cms:event_list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Événement supprimé.")
        return super().delete(request, *args, **kwargs)
