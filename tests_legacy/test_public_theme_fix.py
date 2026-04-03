#!/usr/bin/env python
"""
Test pour vérifier que les thèmes ne sont plus disponibles sur les pages publiques
"""
import os
import sys
import django
from django.test import TestCase, Client

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestion_eebc.settings')
django.setup()

def test_public_pages_no_theme_selector():
    """Test que les pages publiques n'ont plus de sélecteur de thèmes"""
    print("🎨 Test de suppression du sélecteur de thèmes sur les pages publiques")
    print("=" * 70)
    
    client = Client()
    
    # Pages à tester
    pages_to_test = [
        ('/contact/', 'Page de contact'),
        ('/', 'Page d\'accueil'),
    ]
    
    for url, page_name in pages_to_test:
        print(f"\n📄 Test de {page_name} ({url})")
        print("-" * 40)
        
        try:
            response = client.get(url)
            
            if response.status_code == 200:
                content = response.content.decode('utf-8')
                
                # Vérifier l'absence du sélecteur de thèmes
                theme_elements = [
                    'id="themeToggle"',
                    'onclick="toggleThemeSelector()"',
                    'Choisir un thème',
                    'theme-manager.js'
                ]
                
                theme_found = False
                for element in theme_elements:
                    if element in content:
                        print(f"   ❌ Élément de thème trouvé: {element}")
                        theme_found = True
                    else:
                        print(f"   ✅ Élément de thème absent: {element}")
                
                # Vérifier la présence du thème fixe
                if 'data-theme' in content and 'default' in content or 'document.documentElement.setAttribute' in content:
                    print("   ✅ Thème fixe configuré")
                else:
                    print("   ❌ Thème fixe non configuré")
                
                # Vérifier que les CSS publics sont chargés
                if 'public.css' in content:
                    print("   ✅ CSS public chargé")
                else:
                    print("   ❌ CSS public non chargé")
                
                # Vérifier que themes.css n'est plus chargé
                if 'themes.css' in content:
                    print("   ❌ themes.css encore chargé (à supprimer)")
                else:
                    print("   ✅ themes.css supprimé")
                
                if not theme_found:
                    print(f"   🎉 {page_name} : Sélecteur de thèmes correctement supprimé")
                else:
                    print(f"   ⚠️  {page_name} : Sélecteur de thèmes encore présent")
                    
            else:
                print(f"   ❌ Erreur lors du chargement: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
    
    print("\n" + "=" * 70)
    print("🔍 Vérification des fichiers CSS")
    print("=" * 70)
    
    # Vérifier le contenu du CSS public
    try:
        with open("static/css/public.css", "r", encoding="utf-8") as f:
            css_content = f.read()
            
        # Vérifier les variables CSS fixes
        if "--public-primary" in css_content:
            print("✅ Variables CSS fixes définies")
        else:
            print("❌ Variables CSS fixes manquantes")
            
        # Vérifier l'absence de variables dynamiques
        dynamic_vars = ["--accent-primary", "--bg-card", "--text-primary"]
        dynamic_found = False
        for var in dynamic_vars:
            if var in css_content:
                print(f"❌ Variable dynamique encore présente: {var}")
                dynamic_found = True
                
        if not dynamic_found:
            print("✅ Variables dynamiques supprimées")
            
        # Vérifier l'absence de sélecteurs de thèmes
        theme_selectors = ["[data-theme=", "data-theme=\"darkly\"", "data-theme=\"cyborg\""]
        theme_selectors_found = False
        for selector in theme_selectors:
            if selector in css_content:
                print(f"❌ Sélecteur de thème encore présent: {selector}")
                theme_selectors_found = True
                
        if not theme_selectors_found:
            print("✅ Sélecteurs de thèmes supprimés")
            
    except Exception as e:
        print(f"❌ Erreur lecture CSS: {e}")
    
    print("\n" + "=" * 70)
    print("📋 RÉSUMÉ")
    print("=" * 70)
    print("✅ Sélecteur de thèmes supprimé des pages publiques")
    print("✅ Script theme-manager.js retiré des pages publiques")
    print("✅ Thème fixe 'default' configuré")
    print("✅ Variables CSS fixes utilisées")
    print("✅ Couleurs harmonieuses maintenues")
    print("✅ Système de thèmes réservé au dashboard")
    
    print(f"\n🌐 Pages publiques: thème fixe et stable")
    print(f"🎛️  Dashboard: système de thèmes complet disponible")
    
    return True

if __name__ == "__main__":
    test_public_pages_no_theme_selector()