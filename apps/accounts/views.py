from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from .user_creation import create_user_by_team, activate_user_account
from .forms import UserCreationByTeamForm, FirstLoginPasswordChangeForm

User = get_user_model()


def login_view(request):
    """Vue de connexion personnalisée."""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if username and password:
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                # Vérifier si l'utilisateur doit changer son mot de passe
                if user.must_change_password:
                    # Ne pas connecter l'utilisateur, rediriger vers le changement de mot de passe
                    request.session['first_login_user_id'] = user.id
                    request.session['temp_username'] = username
                    request.session['temp_password'] = password
                    return redirect('accounts:first_login_password_change')
                
                # Connexion normale
                login(request, user)
                next_url = request.GET.get('next', 'dashboard:home')
                return redirect(next_url)
            else:
                messages.error(request, 'Nom d\'utilisateur ou mot de passe incorrect.')
    
    return render(request, 'accounts/login.html')


def first_login_password_change(request):
    """Changement de mot de passe obligatoire à la première connexion."""
    user_id = request.session.get('first_login_user_id')
    temp_username = request.session.get('temp_username')
    temp_password = request.session.get('temp_password')
    
    if not user_id or not temp_username or not temp_password:
        messages.error(request, 'Session expirée. Veuillez vous reconnecter.')
        return redirect('accounts:login')
    
    user = get_object_or_404(User, id=user_id)
    
    # Vérifier que l'utilisateur doit encore changer son mot de passe
    if not user.must_change_password:
        messages.info(request, 'Votre mot de passe a déjà été changé.')
        return redirect('accounts:login')
    
    if request.method == 'POST':
        form = FirstLoginPasswordChangeForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data['new_password1']
            
            # Vérifier que le nouveau mot de passe est différent de l'ancien
            if temp_password == new_password:
                form.add_error('new_password1', 'Le nouveau mot de passe doit être différent de l\'ancien.')
            else:
                # Activer le compte avec le nouveau mot de passe
                if activate_user_account(user, new_password):
                    # Marquer que l'utilisateur n'a plus besoin de changer son mot de passe
                    user.must_change_password = False
                    user.save()
                    
                    # Nettoyer la session
                    del request.session['first_login_user_id']
                    del request.session['temp_username']
                    del request.session['temp_password']
                    
                    # Connecter l'utilisateur avec le nouveau mot de passe
                    user = authenticate(request, username=temp_username, password=new_password)
                    if user:
                        login(request, user)
                        messages.success(request, 'Votre mot de passe a été changé avec succès. Bienvenue !')
                        return redirect('dashboard:home')
                    else:
                        messages.error(request, 'Erreur lors de la connexion automatique.')
                        return redirect('accounts:login')
                else:
                    messages.error(request, 'Erreur lors du changement de mot de passe.')
    else:
        form = FirstLoginPasswordChangeForm()
    
    return render(request, 'accounts/first_login_password_change.html', {
        'form': form,
        'user': user
    })


@login_required
def create_user_view(request):
    """Vue pour créer un nouvel utilisateur (réservée à l'équipe)."""
    # Vérifier les permissions
    if not (request.user.is_admin or request.user.role in ['admin', 'secretariat']):
        messages.error(request, 'Vous n\'avez pas les permissions pour créer des utilisateurs.')
        return redirect('dashboard:home')
    
    if request.method == 'POST':
        form = UserCreationByTeamForm(request.POST)
        if form.is_valid():
            # Créer l'utilisateur
            user, username, password = create_user_by_team(
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                email=form.cleaned_data['email'],
                role=form.cleaned_data['role'],
                phone=form.cleaned_data.get('phone', ''),
                created_by=request.user
            )
            
            if user:
                messages.success(
                    request, 
                    f'Utilisateur {user.get_full_name()} créé avec succès. '
                    f'Un email d\'invitation a été envoyé à {user.email}.'
                )
                return redirect('accounts:create_user')
            else:
                messages.error(request, 'Erreur lors de la création de l\'utilisateur.')
    else:
        form = UserCreationByTeamForm()
    
    return render(request, 'accounts/create_user.html', {
        'form': form
    })


@login_required
def user_list_view(request):
    """Liste des utilisateurs (pour l'équipe)."""
    if not (request.user.is_admin or request.user.role in ['admin', 'secretariat']):
        messages.error(request, 'Vous n\'avez pas les permissions pour voir cette page.')
        return redirect('dashboard:home')
    
    users = User.objects.all().order_by('last_name', 'first_name')
    
    return render(request, 'accounts/user_list.html', {
        'users': users
    })


@login_required
@require_http_methods(["POST"])
def resend_invitation(request, user_id):
    """Renvoyer l'email d'invitation à un utilisateur."""
    if not (request.user.is_admin or request.user.role in ['admin', 'secretariat']):
        return JsonResponse({'success': False, 'error': 'Permissions insuffisantes'})
    
    user = get_object_or_404(User, id=user_id)
    
    # Vérifier que l'utilisateur n'a pas encore activé son compte
    if not user.must_change_password:
        return JsonResponse({'success': False, 'error': 'L\'utilisateur a déjà activé son compte'})
    
    # Générer un nouveau mot de passe temporaire
    from .user_creation import generate_password, send_invitation_email
    new_password = generate_password()
    
    # Mettre à jour le mot de passe temporaire
    user.set_password(new_password)
    user.must_change_password = True  # S'assurer que le changement est requis
    user.save()
    
    # Renvoyer l'email
    if send_invitation_email(user, user.username, new_password, request.user):
        return JsonResponse({'success': True, 'message': 'Email d\'invitation renvoyé'})
    else:
        return JsonResponse({'success': False, 'error': 'Erreur lors de l\'envoi de l\'email'})


@login_required
@require_http_methods(["POST"])
def reset_user_password(request, user_id):
    """Réinitialiser le mot de passe d'un utilisateur actif."""
    if not (request.user.is_admin or request.user.role in ['admin', 'secretariat']):
        return JsonResponse({'success': False, 'error': 'Permissions insuffisantes'})
    
    user = get_object_or_404(User, id=user_id)
    
    # Vérifier que l'utilisateur a un compte actif
    if user.must_change_password:
        return JsonResponse({'success': False, 'error': 'L\'utilisateur doit d\'abord changer son mot de passe'})
    
    # Générer un nouveau mot de passe temporaire
    from .user_creation import generate_password, send_password_reset_email
    new_password = generate_password()
    
    # Réinitialiser le mot de passe et forcer le changement
    user.set_password(new_password)
    user.must_change_password = True  # Forcer le changement à la prochaine connexion
    user.save()
    
    # Envoyer l'email de réinitialisation
    if send_password_reset_email(user, user.username, new_password, request.user):
        return JsonResponse({'success': True, 'message': 'Mot de passe réinitialisé et email envoyé'})
    else:
        return JsonResponse({'success': False, 'error': 'Erreur lors de l\'envoi de l\'email'})


def logout_view(request):
    """Vue de déconnexion."""
    if request.method == 'POST':
        # Déconnexion sécurisée via formulaire
        logout(request)
        messages.success(request, 'Vous avez été déconnecté avec succès.')
        return redirect('public:home')
    else:
        # Accès direct via GET - rediriger vers une page de confirmation
        return render(request, 'accounts/logout_confirm.html')


@login_required
def profile_view(request):
    """Vue du profil utilisateur."""
    if request.method == 'POST':
        # Mise à jour du profil
        user = request.user
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        user.phone = request.POST.get('phone', '')
        user.save()
        
        messages.success(request, 'Profil mis à jour avec succès.')
        return redirect('accounts:profile')
    
    return render(request, 'accounts/profile.html')