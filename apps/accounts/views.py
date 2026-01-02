from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy

from .forms import CustomLoginForm, UserProfileForm


class CustomLoginView(LoginView):
    """Vue de connexion personnalisée avec support 2FA."""
    form_class = CustomLoginForm
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        return reverse_lazy('dashboard:home')
    
    def form_valid(self, form):
        user = form.get_user()
        
        # Vérifier si la 2FA est activée
        if user.two_factor_enabled:
            # Stocker l'ID utilisateur en session et rediriger vers la vérification 2FA
            self.request.session['two_factor_user_id'] = user.id
            self.request.session['two_factor_next'] = self.get_success_url()
            return redirect('accounts:two_factor_verify')
        
        # Connexion normale si pas de 2FA
        messages.success(self.request, f"Bienvenue, {user.get_full_name() or user.username}!")
        return super().form_valid(form)


class CustomLogoutView(LogoutView):
    """Vue de déconnexion personnalisée."""
    next_page = 'public:home'
    
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
    
    context = {
        'form': form,
        'two_factor_enabled': request.user.two_factor_enabled,
    }
    
    return render(request, 'accounts/profile.html', context)

