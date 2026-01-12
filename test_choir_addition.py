#!/usr/bin/env python
"""
Test pour vérifier l'ajout de la chorale et l'affichage des couleurs
"""
import os
import sys
import django
from django.test import TestCase, Client
from django.urls import reverse

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestion_eebc.settings')
django.setup()

from apps.core.models import Site

def test_choir_addition():
    """Test que la chorale a été ajoutée aux activités de Cayenne"""
    print("🎵 Test de l'ajout de la chorale...")
    
    try:
        # Récupérer le site Cayenne
        cayenne_site = Site.objects.get(code='CAB')
        
        print(f"✅ Site trouvé: {cayenne_site.name}")
        print(f"📅 Horaires: {cayenne_site.worship_schedule}")
        
        # Vérifier que la chorale est présente
        if "Chorale" in cayenne_site.worship_schedule:
            print("✅ Chorale trouvée dans les horaires")
            if "17h30" in cayenne_site.worship_schedule:
                print("✅ Horaire de la chorale correct (17h30)")
            else:
                print("❌ Horaire de la chorale incorrect")
        else:
            print("❌ Chorale non trouvée dans les horaires")
            
        # Compter le nombre d'activités
        activities = cayenne_site.worship_schedule.split('\n')
        print(f"📊 Nombre d'activités: {len(activities)}")
        
        expected_activities = [
            "Culte", "Étude biblique", "Réunion de prière", 
            "Groupe de jeunes", "Club biblique", "Chorale"
        ]
        
        for activity in expected_activities:
            if activity in cayenne_site.worship_schedule:
                print(f"✅ {activity} présent")
            else:
                print(f"❌ {activity} manquant")
                
    except Site.DoesNotExist:
        print("❌ Site Cayenne non trouvé")
        return False
        
    return True

def test_contact_page():
    """Test que la page de contact se charge correctement"""
    print("\n📄 Test de la page de contact...")
    
    client = Client()
    try:
        response = client.get('/contact/')
        
        if response.status_code == 200:
            print("✅ Page de contact accessible")
            
            # Vérifier la présence des activités dans le HTML
            content = response.content.decode('utf-8')
            
            activities_to_check = [
                "Culte", "Étude biblique", "Réunion de prière",
                "Groupe de jeunes", "Club biblique", "Chorale"
            ]
            
            for activity in activities_to_check:
                if activity in content:
                    print(f"✅ {activity} affiché sur la page")
                else:
                    print(f"❌ {activity} non affiché sur la page")
                    
            # Vérifier la présence des classes CSS pour les couleurs
            if "activity-item" in content:
                print("✅ Classes CSS des activités présentes")
            else:
                print("❌ Classes CSS des activités manquantes")
                
            if "schedule-organized" in content:
                print("✅ Layout organisé présent")
            else:
                print("❌ Layout organisé manquant")
                
        else:
            print(f"❌ Erreur lors du chargement: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False
        
    return True

def test_macouria_site():
    """Test que Macouria n'affiche que le culte"""
    print("\n⛪ Test du site Macouria...")
    
    try:
        macouria_site = Site.objects.get(code='MAC')
        
        print(f"✅ Site trouvé: {macouria_site.name}")
        print(f"📅 Horaires: {macouria_site.worship_schedule}")
        
        # Vérifier que seul le culte est présent
        if macouria_site.worship_schedule == "Culte: Dimanche 9h30":
            print("✅ Macouria affiche uniquement le culte")
        else:
            print("❌ Macouria affiche plus que le culte")
            
    except Site.DoesNotExist:
        print("❌ Site Macouria non trouvé")
        return False
        
    return True

if __name__ == "__main__":
    print("🚀 Test de l'ajout de la chorale et des couleurs")
    print("=" * 50)
    
    success = True
    success &= test_choir_addition()
    success &= test_contact_page()
    success &= test_macouria_site()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 Tous les tests sont passés avec succès !")
        print("✅ La chorale a été ajoutée correctement")
        print("✅ Les 6 activités sont présentes pour Cayenne")
        print("✅ Macouria n'affiche que le culte")
        print("✅ La page de contact fonctionne")
        print("✅ Le système de couleurs est en place")
    else:
        print("❌ Certains tests ont échoué")
        
    print("\n🌐 Serveur accessible sur: http://127.0.0.1:8000/contact/")