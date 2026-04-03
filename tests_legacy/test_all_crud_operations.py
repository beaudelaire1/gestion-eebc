#!/usr/bin/env python
"""
Script de test pour vérifier que tous les CRUD fonctionnent correctement
dans l'interface admin Django avec Jazzmin.
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

def test_admin_access():
    """Test l'accès aux différentes sections de l'admin."""
    
    print("🔍 Test des accès admin CRUD...")
    
    # Créer un client de test
    client = Client()
    
    # Créer un superuser pour les tests (ou utiliser un existant)
    try:
        admin_user = User.objects.get(username='test_admin')
        admin_user.delete()  # Supprimer s'il existe déjà
    except User.DoesNotExist:
        pass
    
    admin_user = User.objects.create_superuser(
        username='test_admin',
        email='admin@test.com',
        password='testpass123'
    )
    
    # Se connecter
    client.login(username='test_admin', password='testpass123')
    
    # Liste des apps et modèles à tester
    admin_urls_to_test = [
        # Core
        ('admin:core_site_changelist', 'Sites'),
        ('admin:core_city_changelist', 'Villes'),
        ('admin:core_family_changelist', 'Familles'),
        
        # Accounts
        ('admin:accounts_user_changelist', 'Utilisateurs'),
        
        # Members
        ('admin:members_member_changelist', 'Membres'),
        ('admin:members_lifeevent_changelist', 'Événements de vie'),
        
        # Bible Club
        ('admin:bibleclub_agegroup_changelist', 'Tranches d\'âge'),
        ('admin:bibleclub_child_changelist', 'Enfants'),
        ('admin:bibleclub_session_changelist', 'Sessions'),
        
        # Events
        ('admin:events_event_changelist', 'Événements'),
        ('admin:events_eventcategory_changelist', 'Catégories d\'événements'),
        
        # Finance
        ('admin:finance_financialtransaction_changelist', 'Transactions financières'),
        ('admin:finance_financecategory_changelist', 'Catégories financières'),
        
        # Groups
        ('admin:groups_group_changelist', 'Groupes'),
        ('admin:groups_groupmeeting_changelist', 'Réunions de groupe'),
        
        # Transport
        ('admin:transport_driverprofile_changelist', 'Profils chauffeur'),
        ('admin:transport_transportrequest_changelist', 'Demandes de transport'),
        
        # Inventory
        ('admin:inventory_equipment_changelist', 'Équipements'),
        ('admin:inventory_category_changelist', 'Catégories d\'équipement'),
        
        # Communication
        ('admin:communication_notification_changelist', 'Notifications'),
        ('admin:communication_emaillog_changelist', 'Logs email'),
        
        # Worship
        ('admin:worship_worshipservice_changelist', 'Services de culte'),
        ('admin:worship_servicerole_changelist', 'Rôles de service'),
    ]
    
    success_count = 0
    error_count = 0
    
    for url_name, description in admin_urls_to_test:
        try:
            url = reverse(url_name)
            response = client.get(url)
            
            if response.status_code == 200:
                print(f"✅ {description}: OK")
                success_count += 1
            else:
                print(f"❌ {description}: Erreur {response.status_code}")
                error_count += 1
                
        except Exception as e:
            print(f"❌ {description}: Exception - {str(e)}")
            error_count += 1
    
    print(f"\n📊 Résultats:")
    print(f"✅ Succès: {success_count}")
    print(f"❌ Erreurs: {error_count}")
    print(f"📈 Taux de réussite: {(success_count/(success_count+error_count)*100):.1f}%")
    
    # Nettoyer
    admin_user.delete()
    
    return error_count == 0

def test_crud_operations():
    """Test les opérations CRUD de base."""
    
    print("\n🔧 Test des opérations CRUD...")
    
    try:
        # Nettoyer d'abord si l'utilisateur existe
        try:
            existing_user = User.objects.get(username='test_user')
            existing_user.delete()
        except User.DoesNotExist:
            pass
        
        # Test création utilisateur
        user = User.objects.create_user(
            username='test_user',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        print("✅ Création utilisateur: OK")
        
        # Test lecture
        retrieved_user = User.objects.get(username='test_user')
        assert retrieved_user.email == 'test@example.com'
        print("✅ Lecture utilisateur: OK")
        
        # Test mise à jour
        retrieved_user.first_name = 'Updated'
        retrieved_user.save()
        updated_user = User.objects.get(username='test_user')
        assert updated_user.first_name == 'Updated'
        print("✅ Mise à jour utilisateur: OK")
        
        # Test suppression
        user_id = updated_user.id
        updated_user.delete()
        assert not User.objects.filter(id=user_id).exists()
        print("✅ Suppression utilisateur: OK")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur CRUD: {str(e)}")
        return False

def main():
    """Fonction principale de test."""
    
    print("🚀 Démarrage des tests CRUD pour Gestion EEBC")
    print("=" * 50)
    
    # Test accès admin
    admin_success = test_admin_access()
    
    # Test opérations CRUD
    crud_success = test_crud_operations()
    
    print("\n" + "=" * 50)
    if admin_success and crud_success:
        print("🎉 Tous les tests sont passés avec succès!")
        print("✅ L'interface admin et les CRUD fonctionnent correctement.")
        return 0
    else:
        print("⚠️  Certains tests ont échoué.")
        print("❌ Vérifiez les erreurs ci-dessus.")
        return 1

if __name__ == '__main__':
    sys.exit(main())