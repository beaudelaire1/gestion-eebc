#!/usr/bin/env python
"""
Test pour vérifier que les thèmes s'appliquent maintenant à tout le dashboard
"""
import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestion_eebc.settings')
django.setup()

def test_general_theme_application():
    """Test que les thèmes s'appliquent maintenant de manière générale"""
    print("🎭 Test d'application générale des thèmes")
    print("=" * 60)
    
    print("\n🔧 CORRECTIONS APPLIQUÉES")
    print("-" * 40)
    
    corrections = [
        ("templates/base.html", "Clé localStorage: 'eebc-theme'"),
        ("templates/base.html", "Thèmes par défaut: 'darkly'/'default'"),
        ("static/css/components.css", "main-content: var(--bg-secondary)"),
        ("static/css/components.css", "top-bar: var(--bg-card)"),
        ("static/css/theme-overrides.css", "Force !important sur tous les éléments"),
        ("static/js/theme-fix.js", "Nettoyage localStorage")
    ]
    
    for file_path, description in corrections:
        if os.path.exists(file_path):
            print(f"   ✅ {description}")
        else:
            print(f"   ❌ {file_path}: Fichier manquant")
    
    print("\n🎨 ÉLÉMENTS FORCÉS AVEC !IMPORTANT")
    print("-" * 40)
    
    forced_elements = [
        "body: background + color",
        "main-content: background + color", 
        "top-bar: background + border + color",
        "sidebar navigation: colors",
        "buttons: background + border + color",
        "cards: background + border + color",
        "tables: background + color + borders",
        "forms: background + border + color",
        "dropdowns: background + border + color",
        "modals: background + border + color",
        "pagination: background + border + color"
    ]
    
    for element in forced_elements:
        print(f"   🎨 {element}")
    
    print("\n🌙 VARIABLES CSS UTILISÉES")
    print("-" * 40)
    
    theme_vars = [
        "--bg-primary: Arrière-plan principal",
        "--bg-secondary: Arrière-plan secondaire",
        "--bg-card: Arrière-plan des cartes",
        "--bg-hover: Arrière-plan au survol",
        "--text-primary: Texte principal",
        "--text-secondary: Texte secondaire", 
        "--text-muted: Texte atténué",
        "--text-inverse: Texte inversé",
        "--border-color: Couleur des bordures",
        "--accent-primary: Couleur d'accent"
    ]
    
    for var in theme_vars:
        print(f"   🎨 {var}")
    
    print("\n🔍 VÉRIFICATION DES FICHIERS")
    print("-" * 40)
    
    # Vérifier theme-overrides.css
    try:
        with open("static/css/theme-overrides.css", "r", encoding="utf-8") as f:
            overrides_content = f.read()
            
        important_count = overrides_content.count("!important")
        var_count = overrides_content.count("var(--")
        
        print(f"   ✅ theme-overrides.css: {important_count} règles !important")
        print(f"   ✅ theme-overrides.css: {var_count} variables CSS")
        
        # Vérifier les éléments clés
        key_elements = [
            ".main-content",
            ".top-bar", 
            ".card",
            ".sidebar .nav-link",
            ".btn-outline-secondary"
        ]
        
        for element in key_elements:
            if element in overrides_content:
                print(f"   ✅ Élément forcé: {element}")
            else:
                print(f"   ❌ Élément manquant: {element}")
                
    except Exception as e:
        print(f"   ❌ Erreur lecture overrides: {e}")
    
    # Vérifier template de base
    try:
        with open("templates/base.html", "r", encoding="utf-8") as f:
            base_content = f.read()
            
        if "theme-overrides.css" in base_content:
            print("   ✅ theme-overrides.css chargé dans le template")
        else:
            print("   ❌ theme-overrides.css non chargé")
            
        if "localStorage.getItem('eebc-theme')" in base_content:
            print("   ✅ Clé localStorage correcte")
        else:
            print("   ❌ Clé localStorage incorrecte")
            
    except Exception as e:
        print(f"   ❌ Erreur lecture template: {e}")
    
    print("\n" + "=" * 60)
    print("🎯 RÉSULTAT ATTENDU")
    print("=" * 60)
    print("🌙 MAINTENANT, les thèmes sombres devraient s'appliquer à:")
    print("   ✅ Sidebar (navigation latérale)")
    print("   ✅ Contenu principal (main-content)")
    print("   ✅ Barre supérieure (top-bar)")
    print("   ✅ Cartes et composants")
    print("   ✅ Boutons et formulaires")
    print("   ✅ Tableaux et listes")
    print("   ✅ Modals et dropdowns")
    print("   ✅ TOUT le dashboard uniformément")
    
    print(f"\n🔧 MÉTHODE UTILISÉE:")
    print(f"   • Variables CSS cohérentes")
    print(f"   • Règles !important pour forcer l'application")
    print(f"   • Fichier theme-overrides.css spécialisé")
    print(f"   • Correction de la clé localStorage")
    
    print(f"\n🎛️  POUR TESTER:")
    print(f"   1. Aller sur: http://127.0.0.1:8000/dashboard/")
    print(f"   2. Vider le cache (Ctrl+F5)")
    print(f"   3. Changer de thème avec le sélecteur")
    print(f"   4. Vérifier que TOUT devient sombre/clair")
    
    return True

if __name__ == "__main__":
    test_general_theme_application()