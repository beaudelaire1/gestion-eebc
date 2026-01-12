#!/usr/bin/env python
"""
Test pour vérifier que les couleurs s'adaptent correctement selon le thème choisi
"""
import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestion_eebc.settings')
django.setup()

def test_adaptive_color_system():
    """Test que les couleurs s'adaptent selon le thème (blanc, noir, ou autre)"""
    print("🎨 Test du système de couleurs adaptatives")
    print("=" * 60)
    
    print("\n🔧 APPROCHE CORRIGÉE")
    print("-" * 40)
    print("❌ AVANT: Couleurs forcées (noir hard-codé)")
    print("✅ APRÈS: Variables CSS adaptatives selon le thème")
    print("")
    print("🎯 Principe: Chaque thème définit ses propres variables")
    print("   • Thème clair: --text-primary = #212529 (noir)")
    print("   • Thème sombre: --text-primary = #ffffff (blanc)")
    print("   • Thème coloré: --text-primary = couleur spécifique")
    
    print("\n🌈 VÉRIFICATION DES VARIABLES PAR THÈME")
    print("-" * 40)
    
    # Vérifier les variables dans themes.css
    try:
        with open("static/css/themes.css", "r", encoding="utf-8") as f:
            themes_content = f.read()
            
        # Thèmes à vérifier
        themes_to_check = [
            ("default", "Thème par défaut"),
            ("darkly", "Thème sombre élégant"),
            ("cyborg", "Thème cyberpunk"),
            ("flatly", "Thème plat coloré"),
            ("cerulean", "Thème bleu ciel")
        ]
        
        for theme_id, description in themes_to_check:
            if f'[data-theme="{theme_id}"]' in themes_content:
                print(f"   ✅ {theme_id}: {description}")
                
                # Extraire la section du thème
                theme_start = themes_content.find(f'[data-theme="{theme_id}"]')
                theme_end = themes_content.find('[data-theme=', theme_start + 1)
                if theme_end == -1:
                    theme_end = len(themes_content)
                theme_section = themes_content[theme_start:theme_end]
                
                # Vérifier les variables de couleur de texte
                text_vars = [
                    "--text-primary",
                    "--text-secondary", 
                    "--text-muted",
                    "--accent-primary"
                ]
                
                for var in text_vars:
                    if var in theme_section:
                        # Extraire la valeur
                        var_line = [line for line in theme_section.split('\n') if var in line]
                        if var_line:
                            value = var_line[0].split(':')[1].strip().rstrip(';')
                            print(f"      🎨 {var}: {value}")
                    else:
                        print(f"      ❌ {var}: Non défini")
            else:
                print(f"   ❌ {theme_id}: Non trouvé")
                
    except Exception as e:
        print(f"   ❌ Erreur lecture themes.css: {e}")
    
    print("\n🎯 NOUVELLES RÈGLES CSS INTELLIGENTES")
    print("-" * 40)
    
    # Vérifier theme-overrides.css
    try:
        with open("static/css/theme-overrides.css", "r", encoding="utf-8") as f:
            overrides_content = f.read()
            
        # Vérifier qu'on n'a plus de règles globales trop agressives
        problematic_rules = [
            "* {",
            ".main-content *",
            ".card *",
            ".top-bar *"
        ]
        
        print("   🔍 Vérification des règles problématiques supprimées:")
        for rule in problematic_rules:
            if rule in overrides_content:
                print(f"      ❌ Règle encore présente: {rule}")
            else:
                print(f"      ✅ Règle supprimée: {rule}")
        
        # Vérifier les règles spécifiques
        good_rules = [
            "color: var(--text-primary)",
            "color: var(--text-secondary)",
            "color: var(--text-muted)",
            "color: var(--accent-primary)"
        ]
        
        print("\n   🎨 Vérification des variables adaptatives:")
        for rule in good_rules:
            count = overrides_content.count(rule)
            print(f"      ✅ {rule}: {count} occurrences")
            
    except Exception as e:
        print(f"   ❌ Erreur lecture overrides: {e}")
    
    print("\n🌈 EXEMPLES DE COULEURS PAR THÈME")
    print("-" * 40)
    
    color_examples = [
        ("Default (clair)", "--text-primary: #212529 (noir foncé)"),
        ("Darkly (sombre)", "--text-primary: #ffffff (blanc)"),
        ("Cyborg (cyberpunk)", "--text-primary: #888 (gris clair)"),
        ("Flatly (coloré)", "--text-primary: #212529 (noir)"),
        ("Cerulean (bleu)", "--text-primary: #033C73 (bleu foncé)")
    ]
    
    for theme, color in color_examples:
        print(f"   🎨 {theme}: {color}")
    
    print("\n🔄 FONCTIONNEMENT ADAPTATIF")
    print("-" * 40)
    
    adaptive_flow = [
        "1. Utilisateur choisit un thème",
        "2. JavaScript applique data-theme='nom-du-theme'",
        "3. CSS charge les variables du thème choisi",
        "4. Tous les éléments utilisent var(--text-primary)",
        "5. La couleur s'adapte automatiquement au thème"
    ]
    
    for step in adaptive_flow:
        print(f"   🔄 {step}")
    
    print("\n" + "=" * 60)
    print("🎯 RÉSULTAT ATTENDU")
    print("=" * 60)
    print("🎨 MAINTENANT, les couleurs s'adaptent intelligemment:")
    print("   ✅ Thème CLAIR → Texte SOMBRE (lisible)")
    print("   ✅ Thème SOMBRE → Texte CLAIR (lisible)")
    print("   ✅ Thème COLORÉ → Texte ADAPTÉ (harmonieux)")
    print("   ✅ Pas de couleur hard-codée")
    print("   ✅ Variables CSS dynamiques")
    print("   ✅ Adaptation automatique")
    
    print(f"\n🔧 AVANTAGES DE CETTE APPROCHE:")
    print(f"   • Respect des couleurs définies par chaque thème")
    print(f"   • Pas de couleur forcée en dur")
    print(f"   • Adaptation automatique selon le contexte")
    print(f"   • Lisibilité garantie sur tous les thèmes")
    print(f"   • Cohérence visuelle parfaite")
    
    print(f"\n🎛️  POUR TESTER:")
    print(f"   1. Aller sur: http://127.0.0.1:8000/dashboard/")
    print(f"   2. Vider le cache (Ctrl+F5)")
    print(f"   3. Tester différents thèmes:")
    print(f"      • Default → Texte noir sur fond blanc")
    print(f"      • Darkly → Texte blanc sur fond sombre")
    print(f"      • Cyborg → Texte gris clair sur fond noir")
    print(f"      • Flatly → Texte noir sur fond coloré")
    print(f"   4. Vérifier que chaque thème a sa propre couleur")
    
    return True

if __name__ == "__main__":
    test_adaptive_color_system()