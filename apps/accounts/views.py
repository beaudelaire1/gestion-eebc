from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView
from django.db.models import Q

from .forms import CustomLoginForm, UserProfileForm, UserCreateForm
from .models import User


class CustomLoginView(LoginView):
    """Vue de connexion personnalisée."""
    form_class = CustomLoginForm
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        return reverse_lazy('dashboard:home')
    
    def form_valid(self, form):
        messages.success(self.request, f"Bienvenue, {form.get_user().get_full_name() or form.get_user().username}!")
        return super().form_valid(form)


class CustomLogoutView(LogoutView):
    """Vue de déconnexion personnalisée."""
    next_page = 'accounts:login'
    
    def dispatch(self, request, *args, **kwargs):
        messages.info(request, "Vous avez été déconnecté avec succès.")
        return super().dispatch(request, *args, **kwargs)


@login_required
def profile_view(request):
    """Vue du profil utilisateur."""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profil mis à jour avec succès!")
            return redirect('accounts:profile')
    else:
        form = UserProfileForm(instance=request.user)
    
    return render(request, 'accounts/profile.html', {'form': form})


class UserCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """Vue de création d'utilisateur."""
    model = User
    form_class = UserCreateForm
    template_name = 'accounts/user_create.html'
    success_url = reverse_lazy('accounts:user_list')
    
    def test_func(self):
        """Seuls les staff/admin peuvent créer des utilisateurs."""
        return self.request.user.is_staff or self.request.user.is_superuser
    
    def form_valid(self, form):
        messages.success(
            self.request, 
            f"L'utilisateur {form.instance.username} a été créé avec succès!"
        )
        return super().form_valid(form)


class UserListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Vue liste des utilisateurs."""
    model = User
    template_name = 'accounts/user_list.html'
    context_object_name = 'users'
    paginate_by = 25
    
    def test_func(self):
        """Seuls les staff/admin peuvent voir la liste des utilisateurs."""
        return self.request.user.is_staff or self.request.user.is_superuser
    
    def get_queryset(self):
        queryset = User.objects.all().order_by('last_name', 'first_name')
        
        # Recherche
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        return context

