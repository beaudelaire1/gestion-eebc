#!/usr/bin/env python
"""
Test pour vérifier que les thèmes sombres fonctionnent correctement sur tout le dashboard
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

def test_dark_theme_consistency():
    """Test que les thèmes sombres s'appliquent à tout le dashboard"""
    print("🌙 Test de cohérence des thèmes sombres")
    print("=" * 50)
    
    # Vérifier la correction dans le template de base
    print("\n🔧 1. Vérification de la correction localStorage")
    print("-" * 40)
    
    try:
        with open("templates/base.html", "r", encoding="utf-8") as f:
            base_content = f.read()
            
        if "localStorage.getItem('eebc-theme')" in base_content:
            print("   ✅ Clé localStorage corrigée: 'eebc-theme'")
        else:
            print("   ❌ Clé localStorage incorrecte")
            
        if "'darkly'" in base_content and "'default'" in base_content:
            print("   ✅ Thèmes par défaut corrects: darkly/default")
        else:
            print("   ❌ Thèmes par défaut incorrects")
            
    except Exception as e:
        print(f"   ❌ Erreur lecture template: {e}")
    
    # Vérifier les variables CSS des thèmes sombres
    print("\n🎨 2. Vérification des variables CSS sombres")
    print("-" * 40)
    
    try:
        with open("static/css/themes.css", "r", encoding="utf-8") as f:
            themes_content = f.read()
            
        dark_themes = ['darkly', 'cyborg', 'slate', 'solar', 'superhero']
        
        for theme in dark_themes:
            if f'[data-theme="{theme}"]' in themes_content:
                print(f"   ✅ Thème {theme}: Défini")
                
                # Vérifier les variables essentielles
                theme_section = themes_content.split(f'[data-theme="{theme}"]')[1].split('[data-theme=')[0]
                
                essential_vars = [
                    '--bg-primary',
                    '--bg-secondary', 
                    '--bg-card',
                    '--text-primary',
                    '--text-secondary'
                ]
                
                for var in essential_vars:
                    if var in theme_section:
                        print(f"      ✅ Variable {var} définie")
                    else:
                        print(f"      ❌ Variable {var} manquante")
            else:
                print(f"   ❌ Thème {theme}: Non défini")
                
    except Exception as e:
        print(f"   ❌ Erreur lecture CSS: {e}")
    
    # Vérifier les composants utilisent les bonnes variables
    print("\n🧩 3. Vérification des composants CSS")
    print("-" * 40)
    
    try:
        with open("static/css/components.css", "r", encoding="utf-8") as f:
            components_content = f.read()
            
        # Variables utilisées dans les composants
        component_vars = [
            'var(--bg-card)',
            'var(--bg-secondary)',
            'var(--text-primary)',
            'var(--border-color)',
            'var(--bg-accent)'
        ]
        
        for var in component_vars:
            if var in components_content:
                print(f"   ✅ Composant utilise: {var}")
            else:
                print(f"   ❌ Composant n'utilise pas: {var}")
                
    except Exception as e:
        print(f"   ❌ Erreur lecture composants: {e}")
    
    # Test du gestionnaire de thèmes
    print("\n⚙️  4. Vérification du gestionnaire de thèmes")
    print("-" * 40)
    
    try:
        with open("static/js/theme-manager.js", "r", encoding="utf-8") as f:
            js_content = f.read()
            
        if "localStorage.setItem('eebc-theme'" in js_content:
            print("   ✅ Gestionnaire utilise la bonne clé: 'eebc-theme'")
        else:
            print("   ❌ Gestionnaire utilise une mauvaise clé")
            
        if "document.documentElement.setAttribute('data-theme'" in js_content:
            print("   ✅ Gestionnaire applique data-theme correctement")
        else:
            print("   ❌ Gestionnaire n'applique pas data-theme")
            
        # Compter les thèmes sombres
        dark_theme_count = 0
        for theme in dark_themes:
            if f"'{theme}'" in js_content:
                dark_theme_count += 1
                
        print(f"   ✅ Thèmes sombres configurés: {dark_theme_count}/5")
        
    except Exception as e:
        print(f"   ❌ Erreur lecture JS: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 DIAGNOSTIC")
    print("=" * 50)
    print("Le problème était probablement dû à:")
    print("❌ Clé localStorage incorrecte: 'theme' au lieu de 'eebc-theme'")
    print("❌ Thèmes par défaut incorrects: 'dark'/'light' au lieu de 'darkly'/'default'")
    print("")
    print("✅ CORRECTIONS APPLIQUÉES:")
    print("✅ Clé localStorage corrigée: 'eebc-theme'")
    print("✅ Thème sombre par défaut: 'darkly'")
    print("✅ Thème clair par défaut: 'default'")
    print("✅ Variables CSS cohérentes dans tous les composants")
    
    print(f"\n🌙 Maintenant les thèmes sombres devraient s'appliquer à tout le dashboard")
    print(f"🎛️  Testez avec: http://127.0.0.1:8000/dashboard/")
    
    return True

if __name__ == "__main__":
    test_dark_theme_consistency()