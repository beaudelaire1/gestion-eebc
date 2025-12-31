from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy

from .forms import CustomLoginForm, UserProfileForm


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

