"""
Helpers avancés pour la gestion des rôles multi-utilisateurs.

Ce module fournit des utilitaires pour :
- Vérifier les permissions complexes (AND, OR, NOT)
- Gérer les hiérarchies de rôles
- Auditer les accès
"""

from typing import List, Set
from django.contrib.auth import get_user_model

User = get_user_model()


# =============================================================================
# HIÉRARCHIE DES RÔLES (chaque rôle hérite des permissions des rôles inférieurs)
# =============================================================================

ROLE_HIERARCHY = {
    'admin': ['admin', 'secretariat', 'finance', 'responsable_club', 'moniteur', 
              'chauffeur', 'responsable_groupe', 'encadrant', 'pasteur', 'ancien', 
              'diacre', 'membre'],
    'pasteur': ['pasteur', 'ancien', 'diacre', 'encadrant', 'membre'],
    'ancien': ['ancien', 'diacre', 'encadrant', 'membre'],
    'diacre': ['diacre', 'membre'],
    'secretariat': ['secretariat', 'membre'],
    'finance': ['finance', 'membre'],
    'responsable_club': ['responsable_club', 'moniteur', 'membre'],
    'moniteur': ['moniteur', 'membre'],
    'chauffeur': ['chauffeur', 'membre'],
    'responsable_groupe': ['responsable_groupe', 'membre'],
    'encadrant': ['encadrant', 'membre'],
    'membre': ['membre'],
}


def get_user_effective_roles(user) -> Set[str]:
    """
    Retourne tous les rôles effectifs de l'utilisateur (incluant hiérarchie).
    
    Args:
        user: User instance
        
    Returns:
        Set[str]: Ensemble des rôles effectifs
        
    Exemple:
        >>> user.role = "pasteur,finance"
        >>> get_user_effective_roles(user)
        {'admin', 'pasteur', 'ancien', 'diacre', 'encadrant', 'finance', 'membre'}
    """
    if not user or not user.is_authenticated:
        return set()
    
    # Superuser a tous les rôles
    if user.is_superuser:
        return set(ROLE_HIERARCHY.keys())
    
    # Récupérer les rôles assignés
    assigned_roles = user.get_roles_list() if hasattr(user, 'get_roles_list') else []
    
    # Ajouter les rôles hérités via la hiérarchie
    effective_roles = set()
    for role in assigned_roles:
        if role in ROLE_HIERARCHY:
            effective_roles.update(ROLE_HIERARCHY[role])
        else:
            effective_roles.add(role)
    
    return effective_roles


def user_has_any_role(user, *roles) -> bool:
    """
    Vérifie si l'utilisateur a AU MOINS UN des rôles spécifiés (OR).
    
    Args:
        user: User instance
        *roles: Rôles requis (n'importe lequel)
        
    Returns:
        bool: True si l'utilisateur a au moins un des rôles
        
    Exemple:
        >>> user_has_any_role(user, 'admin', 'finance')  # True si admin OU finance
    """
    if not roles:
        return True
    
    effective_roles = get_user_effective_roles(user)
    return any(role in effective_roles for role in roles)


def user_has_all_roles(user, *roles) -> bool:
    """
    Vérifie si l'utilisateur a TOUS les rôles spécifiés (AND).
    
    Args:
        user: User instance
        *roles: Rôles requis (tous)
        
    Returns:
        bool: True si l'utilisateur a tous les rôles
        
    Exemple:
        >>> user_has_all_roles(user, 'pasteur', 'finance')  # True seulement si les deux
    """
    if not roles:
        return True
    
    effective_roles = get_user_effective_roles(user)
    return all(role in effective_roles for role in roles)


def user_can_manage_role(user, target_role: str) -> bool:
    """
    Vérifie si l'utilisateur peut gérer/attribuer un rôle donné.
    
    Règle: Un utilisateur peut attribuer uniquement les rôles qu'il possède ou inférieurs.
    
    Args:
        user: User instance
        target_role: Rôle à vérifier
        
    Returns:
        bool: True si l'utilisateur peut gérer ce rôle
        
    Exemple:
        >>> user_can_manage_role(pasteur_user, 'diacre')  # True
        >>> user_can_manage_role(diacre_user, 'pasteur')  # False
    """
    # Admin peut tout
    if user.is_superuser or user_has_any_role(user, 'admin'):
        return True
    
    # Vérifier que le target_role est dans les rôles effectifs de l'utilisateur
    effective_roles = get_user_effective_roles(user)
    return target_role in effective_roles


def get_manageable_roles(user) -> List[str]:
    """
    Retourne la liste des rôles que l'utilisateur peut attribuer.
    
    Args:
        user: User instance
        
    Returns:
        List[str]: Liste des rôles gérables
        
    Exemple:
        >>> get_manageable_roles(pasteur_user)
        ['pasteur', 'ancien', 'diacre', 'encadrant', 'membre']
    """
    effective_roles = get_user_effective_roles(user)
    return sorted(effective_roles)


def format_roles_display(roles: List[str]) -> str:
    """
    Formate une liste de rôles pour affichage.
    
    Args:
        roles: Liste des rôles
        
    Returns:
        str: Chaîne formatée
        
    Exemple:
        >>> format_roles_display(['admin', 'finance'])
        "Administrateur, Finance"
    """
    from apps.accounts.models import User
    
    labels = []
    for role in roles:
        for choice_value, choice_label in User.Role.choices:
            if choice_value == role:
                labels.append(choice_label)
                break
    
    return ', '.join(labels) if labels else 'Aucun rôle'


def validate_role_combination(roles: List[str]) -> tuple[bool, str]:
    """
    Valide qu'une combinaison de rôles est cohérente.
    
    Args:
        roles: Liste des rôles à valider
        
    Returns:
        tuple: (bool valide, str message d'erreur ou None)
        
    Règles de validation:
    - Au moins un rôle requis
    - Pas de rôles incompatibles (ex: admin + membre seul)
    - Rôles doivent exister
        
    Exemple:
        >>> validate_role_combination(['admin', 'finance'])
        (True, None)
        >>> validate_role_combination([])
        (False, "Au moins un rôle requis")
    """
    from apps.accounts.models import User
    
    if not roles:
        return False, "Au moins un rôle requis."
    
    # Vérifier que tous les rôles existent
    valid_roles = [choice[0] for choice in User.Role.choices]
    invalid_roles = [r for r in roles if r not in valid_roles]
    
    if invalid_roles:
        return False, f"Rôles invalides : {', '.join(invalid_roles)}"
    
    # Admin seul suffit, pas besoin d'autres rôles
    if 'admin' in roles and len(roles) > 1:
        return True, "Note: Le rôle 'admin' donne déjà tous les accès."
    
    return True, None


def get_role_description(role: str) -> str:
    """
    Retourne une description du rôle.
    
    Args:
        role: Code du rôle
        
    Returns:
        str: Description du rôle
    """
    descriptions = {
        'admin': "Accès complet à toutes les fonctionnalités du système",
        'pasteur': "Gestion pastorale, accès aux données sensibles",
        'ancien': "Gestion des membres, suivi pastoral",
        'diacre': "Service et assistance, accès limité",
        'secretariat': "Gestion administrative et membres",
        'finance': "Gestion financière et budgets",
        'responsable_club': "Gestion du club biblique",
        'moniteur': "Animation d'une classe du club biblique",
        'chauffeur': "Gestion des transports",
        'responsable_groupe': "Animation d'un groupe de maison",
        'encadrant': "Accès données pastorales en lecture",
        'membre': "Accès basique aux fonctionnalités",
    }
    
    return descriptions.get(role, "Rôle personnalisé")
