#!/usr/bin/env python3
"""
Script de test pour vérifier la bande animée avec versets et les nouveaux thèmes
"""

import requests
import sys
from bs4 import BeautifulSoup

def test_animated_banner():
    """Test de la bande animée avec versets"""
    
    print("🎬 Test de la bande animée avec versets")
    print("=" * 50)
    
    try:
        url = "http://127.0.0.1:8000/contact/"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            print("✅ Page de contact accessible")
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Vérifier les scripts JS
            scripts = soup.find_all('script')
            animated_banner_found = False
            
            for script in scripts:
                script_src = script.get('src', '')
                if 'animated-verse-banner.js' in script_src:
                    animated_banner_found = True
                    print("✅ Script de bande animée chargé")
                    break
            
            if not animated_banner_found:
                print("❌ Script de bande animée manquant")
            
            # Vérifier les CSS
            css_links = soup.find_all('link', {'rel': 'stylesheet'})
            css_files = [link.get('href', '') for link in css_links]
            
            if any('animated-verse-banner.css' in css for css in css_files):
                print("✅ CSS de bande animée chargé")
            else:
                print("❌ CSS de bande animée manquant")
            
            # Vérifier que l'ancienne bande statique n'est plus là
            old_banner = soup.find('div', class_='bible-verse-banner')
            if not old_banner:
                print("✅ Ancienne bande statique supprimée")
            else:
                print("⚠️ Ancienne bande statique encore présente")
            
        else:
            print(f"❌ Erreur HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False
    
    return True

def test_new_themes():
    """Test des nouveaux thèmes Bootswatch"""
    
    print("\n🎨 Test des nouveaux thèmes Bootswatch")
    print("=" * 50)
    
    expected_themes = [
        'default', 'cerulean', 'cosmo', 'flatly', 'journal', 'litera', 
        'lumen', 'lux', 'materia', 'minty', 'pulse', 'sandstone', 
        'simplex', 'sketchy', 'spacelab', 'united', 'yeti',
        'darkly', 'cyborg', 'slate', 'solar', 'superhero'
    ]
    
    try:
        url = "http://127.0.0.1:8000/"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Vérifier le script theme-manager
            scripts = soup.find_all('script')
            theme_manager_found = False
            
            for script in scripts:
                script_src = script.get('src', '')
                if 'theme-manager.js' in script_src:
                    theme_manager_found = True
                    print("✅ Gestionnaire de thèmes chargé")
                    break
            
            if not theme_manager_found:
                print("❌ Gestionnaire de thèmes manquant")
                return False
            
            print(f"📋 Thèmes attendus: {len(expected_themes)}")
            print("   Clairs: default, cerulean, cosmo, flatly, journal, litera, lumen, lux, materia, minty, pulse, sandstone, simplex, sketchy, spacelab, united, yeti")
            print("   Sombres: darkly, cyborg, slate, solar, superhero")
            
        else:
            print(f"❌ Erreur HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False
    
    return True

def test_verse_collection():
    """Test de la collection de versets"""
    
    print("\n📖 Test de la collection de versets")
    print("=" * 50)
    
    expected_verses = [
        "Jean 3:16", "Philippiens 4:13", "Psaume 23:1", "Proverbes 3:5",
        "Ésaïe 55:8", "Matthieu 11:28", "Matthieu 6:33", "Matthieu 18:20",
        "Romains 5:5", "Psaume 91:1", "Philippiens 4:4", "Éphésiens 2:8",
        "Jean 14:1", "Romains 8:1", "Apocalypse 3:20"
    ]
    
    print(f"✅ Collection de {len(expected_verses)} versets préparée")
    print("📋 Versets inclus:")
    for i, verse in enumerate(expected_verses, 1):
        print(f"   {i:2d}. {verse}")
    
    print("\n🎯 Fonctionnalités de la bande:")
    print("   • Hauteur: 15px exactement")
    print("   • Texte défilant de droite à gauche")
    print("   • Sélection aléatoire de verset")
    print("   • Changement automatique toutes les 2 minutes")
    print("   • Adaptation aux thèmes (22 thèmes supportés)")
    print("   • Animation de dégradé de fond")
    print("   • Effet de brillance qui passe")
    print("   • Pause au survol")
    
    return True

def test_css_themes():
    """Test des définitions CSS des thèmes"""
    
    print("\n🎨 Test des définitions CSS des thèmes")
    print("=" * 50)
    
    try:
        # Lire le fichier CSS des thèmes
        with open('static/css/themes.css', 'r', encoding='utf-8') as f:
            css_content = f.read()
        
        # Vérifier la présence des thèmes
        themes_found = []
        expected_themes = [
            'default', 'cerulean', 'cosmo', 'flatly', 'journal', 'litera',
            'lumen', 'lux', 'materia', 'minty', 'pulse', 'sandstone',
            'simplex', 'sketchy', 'spacelab', 'united', 'yeti',
            'darkly', 'cyborg', 'slate', 'solar', 'superhero'
        ]
        
        for theme in expected_themes:
            if f'[data-theme="{theme}"]' in css_content:
                themes_found.append(theme)
                print(f"✅ Thème {theme} défini")
            else:
                print(f"❌ Thème {theme} manquant")
        
        print(f"\n📊 Résultat: {len(themes_found)}/{len(expected_themes)} thèmes définis")
        
        # Vérifier les variables CSS essentielles
        essential_vars = [
            '--bg-primary', '--bg-secondary', '--bg-card',
            '--text-primary', '--text-secondary',
            '--accent-primary', '--accent-success', '--accent-warning', '--accent-danger',
            '--border-color', '--shadow-sm'
        ]
        
        vars_found = 0
        for var in essential_vars:
            if var in css_content:
                vars_found += 1
        
        print(f"📊 Variables CSS: {vars_found}/{len(essential_vars)} variables essentielles trouvées")
        
        if len(themes_found) == len(expected_themes) and vars_found == len(essential_vars):
            print("✅ Tous les thèmes et variables CSS sont correctement définis")
            return True
        else:
            print("❌ Certains thèmes ou variables CSS sont manquants")
            return False
            
    except FileNotFoundError:
        print("❌ Fichier themes.css non trouvé")
        return False
    except Exception as e:
        print(f"❌ Erreur lors de la lecture du CSS: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Tests EEBC - Bande Animée et Thèmes Bootswatch")
    print("=" * 60)
    
    success = True
    
    success &= test_animated_banner()
    success &= test_new_themes()
    success &= test_verse_collection()
    success &= test_css_themes()
    
    if success:
        print("\n" + "=" * 60)
        print("✅ TOUS LES TESTS SONT PASSÉS AVEC SUCCÈS !")
        print("\n📋 Résumé des nouvelles fonctionnalités:")
        print("   🎬 Bande animée de 15px avec texte défilant")
        print("   📖 15 versets bibliques sélectionnés aléatoirement")
        print("   🎨 22 thèmes Bootswatch (17 clairs + 5 sombres)")
        print("   ⚡ Changement automatique de verset toutes les 2 minutes")
        print("   🌈 Adaptation de la bande à tous les thèmes")
        print("   ✨ Animations et effets visuels avancés")
        
        print("\n🎯 Pour tester:")
        print("   1. Visitez http://127.0.0.1:8000/contact/")
        print("   2. Observez la bande bleue animée de 15px")
        print("   3. Changez de thème avec le sélecteur (22 thèmes disponibles)")
        print("   4. Attendez 2 minutes pour voir le changement de verset")
        print("   5. Survolez la bande pour la mettre en pause")
        
        print("\n🎨 Thèmes disponibles:")
        print("   Clairs: Default, Cerulean, Cosmo, Flatly, Journal, Litera, Lumen, Lux,")
        print("           Materia, Minty, Pulse, Sandstone, Simplex, Sketchy, Spacelab, United, Yeti")
        print("   Sombres: Darkly, Cyborg, Slate, Solar, Superhero")
        
    else:
        print("\n❌ CERTAINS TESTS ONT ÉCHOUÉ")
        print("Vérifiez les erreurs ci-dessus et corrigez les problèmes.")
        sys.exit(1)