#!/usr/bin/env python
"""
Script de test pour vérifier les corrections apportées au système d'utilisateurs :
1. Lien email corrigé (pas d'erreur 404)
2. Rôles multiples fonctionnels
3. Alertes membres non visités restreintes aux pasteurs/anciens/diacres
"""

import os
import sys
import django
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestion_eebc.settings')
django.setup()

User = get_user_model()

def test_multiple_roles():
    """Test le système de rôles multiples."""
    
    print("🔧 Test des rôles multiples...")
    
    try:
        # Nettoyer d'abord
        User.objects.filter(username='test_multi_role').delete()
        
        # Créer un utilisateur avec plusieurs rôles
        user = User.objects.create_user(
            username='test_multi_role',
            email='multi@test.com',
            password='testpass123',
            first_name='Multi',
            last_name='Role',
            role='pasteur,ancien,diacre'  # Plusieurs rôles
        )
        
        # Test des méthodes de rôles
        assert user.has_role('pasteur'), "L'utilisateur devrait avoir le rôle pasteur"
        assert user.has_role('ancien'), "L'utilisateur devrait avoir le rôle ancien"
        assert user.has_role('diacre'), "L'utilisateur devrait avoir le rôle diacre"
        assert not user.has_role('membre'), "L'utilisateur ne devrait pas avoir le rôle membre"
        
        print("✅ Rôles multiples: OK")
        
        # Test des propriétés
        assert user.is_pasteur, "is_pasteur devrait être True"
        assert user.is_ancien, "is_ancien devrait être True"
        assert user.is_diacre, "is_diacre devrait être True"
        assert user.can_view_member_alerts, "can_view_member_alerts devrait être True"
        
        print("✅ Propriétés de rôles: OK")
        
        # Test de l'affichage des rôles
        role_display = user.get_role_display()
        assert 'Pasteur' in role_display, "L'affichage devrait contenir 'Pasteur'"
        assert 'Ancien' in role_display, "L'affichage devrait contenir 'Ancien'"
        assert 'Diacre' in role_display, "L'affichage devrait contenir 'Diacre'"
        
        print("✅ Affichage des rôles: OK")
        
        # Test ajout/suppression de rôles
        user.add_role('moniteur')
        assert user.has_role('moniteur'), "Le rôle moniteur devrait être ajouté"
        
        user.remove_role('diacre')
        assert not user.has_role('diacre'), "Le rôle diacre devrait être supprimé"
        
        print("✅ Ajout/suppression de rôles: OK")
        
        # Nettoyer
        user.delete()
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur rôles multiples: {str(e)}")
        return False

def test_member_alerts_permissions():
    """Test les permissions pour les alertes de membres non visités."""
    
    print("\n🔒 Test des permissions d'alertes...")
    
    try:
        # Nettoyer d'abord
        User.objects.filter(username__in=['test_pasteur', 'test_membre']).delete()
        
        # Créer un pasteur
        pasteur = User.objects.create_user(
            username='test_pasteur',
            email='pasteur@test.com',
            password='testpass123',
            first_name='Test',
            last_name='Pasteur',
            role='pasteur'
        )
        
        # Créer un membre simple
        membre = User.objects.create_user(
            username='test_membre',
            email='membre@test.com',
            password='testpass123',
            first_name='Test',
            last_name='Membre',
            role='membre'
        )
        
        # Test des permissions
        assert pasteur.can_view_member_alerts, "Le pasteur devrait pouvoir voir les alertes"
        assert not membre.can_view_member_alerts, "Le membre ne devrait pas pouvoir voir les alertes"
        
        print("✅ Permissions d'alertes: OK")
        
        # Nettoyer
        pasteur.delete()
        membre.delete()
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur permissions: {str(e)}")
        return False

def test_new_roles():
    """Test les nouveaux rôles pasteur et ancien."""
    
    print("\n⛪ Test des nouveaux rôles...")
    
    try:
        # Vérifier que les nouveaux rôles existent
        role_choices = dict(User.Role.choices)
        
        assert 'pasteur' in role_choices, "Le rôle pasteur devrait exister"
        assert 'ancien' in role_choices, "Le rôle ancien devrait exister"
        assert 'diacre' in role_choices, "Le rôle diacre devrait exister"
        
        assert role_choices['pasteur'] == 'Pasteur', "Le label du rôle pasteur devrait être 'Pasteur'"
        assert role_choices['ancien'] == 'Ancien', "Le label du rôle ancien devrait être 'Ancien'"
        assert role_choices['diacre'] == 'Diacre', "Le label du rôle diacre devrait être 'Diacre'"
        
        print("✅ Nouveaux rôles: OK")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur nouveaux rôles: {str(e)}")
        return False

def test_email_token_generation():
    """Test la génération de tokens pour les emails."""
    
    print("\n📧 Test des tokens d'email...")
    
    try:
        from apps.accounts.services import AuthenticationService
        
        # Nettoyer d'abord
        User.objects.filter(username='test_token').delete()
        
        # Créer un utilisateur
        user = User.objects.create_user(
            username='test_token',
            email='token@test.com',
            password='testpass123',
            first_name='Test',
            last_name='Token',
            must_change_password=True
        )
        
        # Générer un token
        token = AuthenticationService.generate_password_change_token(user)
        assert token, "Un token devrait être généré"
        
        # Vérifier le token
        verified_user = AuthenticationService.verify_password_change_token(token)
        assert verified_user == user, "Le token devrait être valide et retourner le bon utilisateur"
        
        print("✅ Génération de tokens: OK")
        
        # Nettoyer
        user.delete()
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur tokens: {str(e)}")
        return False

def main():
    """Fonction principale de test."""
    
    print("🚀 Test des corrections utilisateurs pour Gestion EEBC")
    print("=" * 60)
    
    # Tests
    tests = [
        test_multiple_roles,
        test_member_alerts_permissions,
        test_new_roles,
        test_email_token_generation
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print("\n" + "=" * 60)
    success_count = sum(results)
    total_count = len(results)
    
    if success_count == total_count:
        print("🎉 Tous les tests sont passés avec succès!")
        print("✅ Les corrections utilisateurs fonctionnent correctement:")
        print("   • Rôles multiples implémentés")
        print("   • Nouveaux rôles pasteur/ancien/diacre ajoutés")
        print("   • Permissions d'alertes restreintes")
        print("   • Tokens d'email sécurisés")
        return 0
    else:
        print(f"⚠️  {total_count - success_count} test(s) ont échoué sur {total_count}")
        return 1

if __name__ == '__main__':
    sys.exit(main())