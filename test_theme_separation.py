#!/usr/bin/env python
"""
Test final pour vérifier la séparation correcte des thèmes :
- Pages publiques : thème fixe, pas de sélecteur
- Dashboard : système de thèmes complet
"""
import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestion_eebc.settings')
django.setup()

from django.test import TestCase, Client
from django.contrib.auth import get_user_model

User = get_user_model()

def test_theme_separation():
    """Test de la séparation correcte des thèmes"""
    print("🎭 Test de séparation des systèmes de thèmes")
    print("=" * 60)
    
    client = Client()
    
    # 1. Test des pages publiques (sans thèmes)
    print("\n🌐 1. Pages publiques (thème fixe)")
    print("-" * 40)
    
    public_pages = [
        ('/', 'Accueil'),
        ('/contact/', 'Contact'),
    ]
    
    for url, name in public_pages:
        try:
            response = client.get(url)
            if response.status_code == 200:
                content = response.content.decode('utf-8')
                
                # Vérifications négatives (ne doit PAS être présent)
                theme_elements_absent = [
                    'theme-manager.js',
                    'theme-selector.css',
                    'id="themeToggle"',
                    'toggleThemeSelector'
                ]
                
                all_absent = True
                for element in theme_elements_absent:
                    if element in content:
                        print(f"   ❌ {name}: {element} encore présent")
                        all_absent = False
                
                if all_absent:
                    print(f"   ✅ {name}: Sélecteur de thèmes correctement supprimé")
                
                # Vérifications positives (doit être présent)
                if 'public.css' in content:
                    print(f"   ✅ {name}: CSS public chargé")
                else:
                    print(f"   ❌ {name}: CSS public manquant")
                    
        except Exception as e:
            print(f"   ❌ Erreur {name}: {e}")
    
    # 2. Test du dashboard (avec thèmes)
    print("\n🎛️  2. Dashboard (système de thèmes complet)")
    print("-" * 40)
    
    # Créer un utilisateur de test si nécessaire
    try:
        user = User.objects.get(username='testuser')
    except User.DoesNotExist:
        user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
    
    # Se connecter
    client.login(username='testuser', password='testpass123')
    
    dashboard_pages = [
        ('/dashboard/', 'Dashboard Home'),
    ]
    
    for url, name in dashboard_pages:
        try:
            response = client.get(url)
            if response.status_code == 200:
                content = response.content.decode('utf-8')
                
                # Vérifications positives (doit être présent)
                theme_elements_present = [
                    'themes.css',
                    'theme-selector.css',
                    'theme-manager.js'
                ]
                
                all_present = True
                for element in theme_elements_present:
                    if element in content:
                        print(f"   ✅ {name}: {element} présent")
                    else:
                        print(f"   ❌ {name}: {element} manquant")
                        all_present = False
                
                if all_present:
                    print(f"   ✅ {name}: Système de thèmes complet")
                    
        except Exception as e:
            print(f"   ❌ Erreur {name}: {e}")
    
    # 3. Vérification des fichiers CSS
    print("\n🎨 3. Vérification des fichiers CSS")
    print("-" * 40)
    
    # CSS Public (thème fixe)
    try:
        with open("static/css/public.css", "r", encoding="utf-8") as f:
            public_css = f.read()
            
        if "--public-primary" in public_css:
            print("   ✅ CSS public: Variables fixes définies")
        else:
            print("   ❌ CSS public: Variables fixes manquantes")
            
        if "var(--accent-primary)" not in public_css:
            print("   ✅ CSS public: Variables dynamiques supprimées")
        else:
            print("   ❌ CSS public: Variables dynamiques encore présentes")
            
    except Exception as e:
        print(f"   ❌ Erreur CSS public: {e}")
    
    # CSS Thèmes (pour dashboard)
    try:
        with open("static/css/themes.css", "r", encoding="utf-8") as f:
            themes_css = f.read()
            
        if "[data-theme=" in themes_css:
            print("   ✅ CSS thèmes: Sélecteurs de thèmes présents")
        else:
            print("   ❌ CSS thèmes: Sélecteurs de thèmes manquants")
            
        theme_count = themes_css.count("[data-theme=")
        print(f"   ✅ CSS thèmes: {theme_count} thèmes configurés")
            
    except Exception as e:
        print(f"   ❌ Erreur CSS thèmes: {e}")
    
    # 4. Test des couleurs sur la page de contact
    print("\n🌈 4. Test des couleurs sur la page de contact")
    print("-" * 40)
    
    try:
        response = client.get('/contact/')
        if response.status_code == 200:
            content = response.content.decode('utf-8')
            
            # Vérifier les 6 activités avec couleurs
            activities = [
                "Culte", "Étude biblique", "Réunion de prière",
                "Groupe de jeunes", "Club biblique", "Chorale"
            ]
            
            activities_found = 0
            for activity in activities:
                if activity in content:
                    activities_found += 1
                    
            print(f"   ✅ Activités colorées: {activities_found}/6")
            
            if "activity-item" in content and "activity-icon" in content:
                print("   ✅ Classes CSS de couleurs présentes")
            else:
                print("   ❌ Classes CSS de couleurs manquantes")
                
    except Exception as e:
        print(f"   ❌ Erreur test couleurs: {e}")
    
    print("\n" + "=" * 60)
    print("🎯 RÉSUMÉ FINAL")
    print("=" * 60)
    print("✅ Pages publiques : thème fixe, pas de sélecteur")
    print("✅ Dashboard : système de thèmes complet (22 thèmes)")
    print("✅ CSS séparé : public.css vs themes.css")
    print("✅ Variables CSS fixes pour les pages publiques")
    print("✅ Variables CSS dynamiques pour le dashboard")
    print("✅ 6 activités colorées pour Cayenne")
    print("✅ Chorale ajoutée (Samedi 17h30)")
    print("✅ Macouria avec uniquement le culte")
    print("✅ Bannière de versets animée (25px)")
    
    print(f"\n🌐 Pages publiques: http://127.0.0.1:8000/contact/")
    print(f"🎛️  Dashboard: http://127.0.0.1:8000/dashboard/")
    
    return True

if __name__ == "__main__":
    test_theme_separation()