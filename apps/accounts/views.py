from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseRedirect
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.urls import reverse
from urllib.parse import urlencode
from .forms import UserCreationByTeamForm, FirstLoginPasswordChangeForm
from .services import AuthenticationService, AccountsService

User = get_user_model()


def login_view(request):
    """Vue de connexion personnalisée avec rate limiting et tokens sécurisés."""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if username and password:
            # Utiliser le service d'authentification avec rate limiting
            user, error_message = AuthenticationService.authenticate_user(
                username=username,
                password=password,
                request=request
            )
            
            if user is not None:
                # Vérifier si l'utilisateur doit changer son mot de passe
                if user.must_change_password:
                    # Générer un token sécurisé au lieu de stocker le mot de passe en session
                    token = AuthenticationService.generate_password_change_token(user)
                    # Rediriger vers le changement de mot de passe avec le token
                    url = reverse('accounts:first_login_password_change')
                    return HttpResponseRedirect(f'{url}?token={token}')
                
                # Connexion normale
                login(request, user)
                next_url = request.GET.get('next', 'dashboard:home')
                return redirect(next_url)
            else:
                messages.error(request, error_message)
    
    return render(request, 'accounts/login.html')


def first_login_password_change(request):
    """Changement de mot de passe obligatoire à la première connexion.
    
    Utilise un token sécurisé signé au lieu de stocker le mot de passe en session.
    """
    # Récupérer le token depuis l'URL
    token = request.GET.get('token') or request.POST.get('token')
    
    if not token:
        messages.error(request, 'Token manquant. Veuillez vous reconnecter.')
        return redirect('accounts:login')
    
    # Vérifier le token (sans le consommer pour le GET)
    user = AuthenticationService.verify_password_change_token(token)
    
    if not user:
        messages.error(request, 'Token invalide ou expiré. Veuillez vous reconnecter.')
        return redirect('accounts:login')
    
    # Vérifier que l'utilisateur doit encore changer son mot de passe
    if not user.must_change_password:
        messages.info(request, 'Votre mot de passe a déjà été changé.')
        return redirect('accounts:login')
    
    if request.method == 'POST':
        form = FirstLoginPasswordChangeForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data['new_password1']
            
            # Consommer le token (le marquer comme utilisé)
            verified_user = AuthenticationService.consume_password_change_token(token)
            
            if not verified_user:
                messages.error(request, 'Token invalide ou expiré. Veuillez vous reconnecter.')
                return redirect('accounts:login')
            
            # Activer le compte avec le nouveau mot de passe via le service
            result = AccountsService.activate_user_account(verified_user, new_password)
            
            if result.success:
                # Connecter l'utilisateur avec le nouveau mot de passe
                authenticated_user = authenticate(
                    request,
                    username=verified_user.username,
                    password=new_password
                )
                if authenticated_user:
                    login(request, authenticated_user)
                    messages.success(request, 'Votre mot de passe a été changé avec succès. Bienvenue !')
                    return redirect('dashboard:home')
                else:
                    messages.error(request, 'Erreur lors de la connexion automatique.')
                    return redirect('accounts:login')
            else:
                messages.error(request, result.error or 'Erreur lors du changement de mot de passe.')
    else:
        form = FirstLoginPasswordChangeForm()
    
    return render(request, 'accounts/first_login_password_change.html', {
        'form': form,
        'user': user,
        'token': token  # Passer le token au template pour le formulaire POST
    })


@login_required
def create_user_view(request):
    """Vue pour créer un nouvel utilisateur (réservée à l'équipe).
    
    Délègue la logique métier au service AccountsService.
    La vue ne fait que: recevoir requête → appeler service → renvoyer réponse.
    """
    # Vérifier les permissions
    if not (request.user.is_admin or request.user.role in ['admin', 'secretariat']):
        messages.error(request, 'Vous n\'avez pas les permissions pour créer des utilisateurs.')
        return redirect('dashboard:home')
    
    if request.method == 'POST':
        form = UserCreationByTeamForm(request.POST)
        if form.is_valid():
            # Déléguer la création au service
            result = AccountsService.create_user_by_team(
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                email=form.cleaned_data['email'],
                role=form.cleaned_data['role'],
                phone=form.cleaned_data.get('phone', ''),
                created_by=request.user
            )
            
            if result.success:
                user = result.data['user']
                messages.success(
                    request, 
                    f'Utilisateur {user.get_full_name()} créé avec succès. '
                    f'Un email d\'invitation a été envoyé à {user.email}.'
                )
                return redirect('accounts:create_user')
            else:
                messages.error(request, result.error or 'Erreur lors de la création de l\'utilisateur.')
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
    """Renvoyer l'email d'invitation à un utilisateur.
    
    Délègue la logique métier au service AccountsService.
    """
    if not (request.user.is_admin or request.user.role in ['admin', 'secretariat']):
        return JsonResponse({'success': False, 'error': 'Permissions insuffisantes'})
    
    user = get_object_or_404(User, id=user_id)
    
    # Déléguer au service
    result = AccountsService.resend_invitation(user, request.user)
    
    if result.success:
        return JsonResponse({'success': True, 'message': 'Email d\'invitation renvoyé'})
    else:
        return JsonResponse({'success': False, 'error': result.error})


@login_required
@require_http_methods(["POST"])
def reset_user_password(request, user_id):
    """Réinitialiser le mot de passe d'un utilisateur actif.
    
    Délègue la logique métier au service AccountsService.
    """
    if not (request.user.is_admin or request.user.role in ['admin', 'secretariat']):
        return JsonResponse({'success': False, 'error': 'Permissions insuffisantes'})
    
    user = get_object_or_404(User, id=user_id)
    
    # Déléguer au service
    result = AccountsService.reset_user_password(user, request.user)
    
    if result.success:
        return JsonResponse({'success': True, 'message': 'Mot de passe réinitialisé et email envoyé'})
    else:
        return JsonResponse({'success': False, 'error': result.error})


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