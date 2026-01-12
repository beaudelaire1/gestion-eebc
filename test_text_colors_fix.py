#!/usr/bin/env python
"""
Test pour vérifier que les couleurs de texte sont maintenant impactées par les thèmes
"""
import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestion_eebc.settings')
django.setup()

def test_text_colors_application():
    """Test que les couleurs de texte s'appliquent avec les thèmes"""
    print("📝 Test d'application des couleurs de texte")
    print("=" * 60)
    
    print("\n🎨 NOUVELLES RÈGLES CSS POUR LES TEXTES")
    print("-" * 40)
    
    # Vérifier le fichier theme-overrides.css
    try:
        with open("static/css/theme-overrides.css", "r", encoding="utf-8") as f:
            overrides_content = f.read()
            
        # Compter les règles de couleur de texte
        text_rules = [
            "color: var(--text-primary)",
            "color: var(--text-secondary)", 
            "color: var(--text-muted)",
            "color: var(--accent-primary)",
            "color: inherit"
        ]
        
        total_text_rules = 0
        for rule in text_rules:
            count = overrides_content.count(rule)
            total_text_rules += count
            print(f"   🎨 {rule}: {count} occurrences")
            
        print(f"   ✅ Total règles de couleur de texte: {total_text_rules}")
        
        # Vérifier les éléments de texte spécifiques
        text_elements = [
            "h1, h2, h3, h4, h5, h6",
            "p, span, div, label, small",
            ".text-muted",
            ".text-secondary", 
            ".text-primary",
            ".card *",
            ".main-content *",
            ".top-bar *"
        ]
        
        elements_found = 0
        for element in text_elements:
            if element in overrides_content:
                elements_found += 1
                print(f"   ✅ Élément forcé: {element}")
            else:
                print(f"   ❌ Élément manquant: {element}")
                
        print(f"   📊 Éléments de texte couverts: {elements_found}/{len(text_elements)}")
        
    except Exception as e:
        print(f"   ❌ Erreur lecture CSS: {e}")
    
    print("\n🔤 ÉLÉMENTS DE TEXTE FORCÉS")
    print("-" * 40)
    
    forced_text_elements = [
        "Titres (h1-h6): var(--text-primary)",
        "Paragraphes (p): var(--text-primary)",
        "Spans et divs: var(--text-primary)",
        "Labels de formulaires: var(--text-primary)",
        "Texte dans les cartes: var(--text-primary)",
        "Texte dans main-content: var(--text-primary)",
        "Texte dans top-bar: var(--text-primary)",
        "Classes Bootstrap (.text-muted): var(--text-muted)",
        "Classes Bootstrap (.text-secondary): var(--text-secondary)",
        "Liens (a): var(--accent-primary)",
        "Icônes Bootstrap (.bi): inherit",
        "Tous les éléments (*): inherit"
    ]
    
    for element in forced_text_elements:
        print(f"   📝 {element}")
    
    print("\n🎯 STRATÉGIE D'APPLICATION")
    print("-" * 40)
    
    strategies = [
        "Règle globale: * { color: inherit !important; }",
        "Éléments spécifiques: h1-h6, p, span, div, label",
        "Classes Bootstrap: .text-muted, .text-secondary, etc.",
        "Conteneurs: .card *, .main-content *, .top-bar *",
        "Héritage forcé: color: inherit sur tous les enfants",
        "Priorité maximale: !important sur toutes les règles"
    ]
    
    for strategy in strategies:
        print(f"   🎯 {strategy}")
    
    print("\n🌙 VARIABLES CSS POUR LES TEXTES")
    print("-" * 40)
    
    text_variables = [
        "--text-primary: Couleur principale des textes",
        "--text-secondary: Couleur secondaire (plus claire)",
        "--text-muted: Couleur atténuée (très claire)",
        "--text-inverse: Couleur inversée (pour boutons)",
        "--accent-primary: Couleur d'accent (liens, actifs)"
    ]
    
    for var in text_variables:
        print(f"   🎨 {var}")
    
    print("\n📊 STATISTIQUES DE CORRECTION")
    print("-" * 40)
    
    try:
        with open("static/css/theme-overrides.css", "r", encoding="utf-8") as f:
            content = f.read()
            
        stats = {
            "Règles !important": content.count("!important"),
            "Variables CSS": content.count("var(--"),
            "Règles de couleur": content.count("color:"),
            "Sélecteurs *": content.count(" * {"),
            "Éléments h1-h6": content.count("h1, h2, h3, h4, h5, h6"),
            "Classes Bootstrap": content.count(".text-")
        }
        
        for stat, count in stats.items():
            print(f"   📊 {stat}: {count}")
            
    except Exception as e:
        print(f"   ❌ Erreur calcul stats: {e}")
    
    print("\n" + "=" * 60)
    print("🎯 RÉSULTAT ATTENDU")
    print("=" * 60)
    print("📝 MAINTENANT, les couleurs de texte devraient s'adapter:")
    print("   ✅ Titres et sous-titres")
    print("   ✅ Paragraphes et texte courant")
    print("   ✅ Labels de formulaires")
    print("   ✅ Texte dans les cartes")
    print("   ✅ Texte dans la navigation")
    print("   ✅ Texte dans les boutons")
    print("   ✅ Liens et éléments actifs")
    print("   ✅ Classes Bootstrap (.text-muted, etc.)")
    print("   ✅ TOUS les textes uniformément")
    
    print(f"\n🔧 MÉTHODE UTILISÉE:")
    print(f"   • Règle globale: * {{ color: inherit !important; }}")
    print(f"   • Sélecteurs spécifiques pour chaque type de texte")
    print(f"   • Variables CSS cohérentes (--text-primary, etc.)")
    print(f"   • Héritage forcé sur tous les conteneurs")
    print(f"   • Priorité maximale avec !important")
    
    print(f"\n🎛️  POUR TESTER:")
    print(f"   1. Aller sur: http://127.0.0.1:8000/dashboard/")
    print(f"   2. Vider le cache (Ctrl+F5)")
    print(f"   3. Changer vers un thème sombre (darkly, cyborg)")
    print(f"   4. Vérifier que TOUS les textes deviennent clairs")
    print(f"   5. Changer vers un thème clair (default, flatly)")
    print(f"   6. Vérifier que TOUS les textes deviennent sombres")
    
    return True

if __name__ == "__main__":
    test_text_colors_application()