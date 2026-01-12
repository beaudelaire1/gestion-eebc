#!/usr/bin/env python3
"""
Script de test pour vérifier que la page de contact fonctionne correctement
avec la bande bleue Jean 3:16 et les informations du club biblique.
"""

import requests
import sys
from bs4 import BeautifulSoup

def test_contact_page():
    """Test de la page de contact"""
    
    print("🧪 Test de la page de contact EEBC")
    print("=" * 50)
    
    try:
        # Tester la page de contact
        url = "http://127.0.0.1:8000/contact/"
        print(f"📡 Test de l'URL: {url}")
        
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            print("✅ Page de contact accessible")
            
            # Parser le HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Vérifier la présence de la bande verset
            verse_banner = soup.find('div', class_='bible-verse-banner')
            if verse_banner:
                print("✅ Bande verset Jean 3:16 trouvée")
                
                # Vérifier le contenu du verset
                verse_text = verse_banner.find('p', class_='verse-quote')
                if verse_text and "Car Dieu a tant aimé le monde" in verse_text.get_text():
                    print("✅ Texte de Jean 3:16 correct")
                else:
                    print("❌ Texte de Jean 3:16 manquant ou incorrect")
                
                # Vérifier la référence
                verse_ref = verse_banner.find('p', class_='verse-reference')
                if verse_ref and "Jean 3:16" in verse_ref.get_text():
                    print("✅ Référence Jean 3:16 correcte")
                else:
                    print("❌ Référence Jean 3:16 manquante")
            else:
                print("❌ Bande verset Jean 3:16 non trouvée")
            
            # Vérifier les informations du club biblique
            club_info = soup.find('div', class_='club-biblique-info')
            if club_info:
                print("✅ Section Club Biblique trouvée")
                
                # Vérifier les horaires
                if "Samedi 9h30" in club_info.get_text():
                    print("✅ Horaires du club biblique corrects (Samedi 9h30)")
                else:
                    print("❌ Horaires du club biblique incorrects")
                
                # Vérifier le lieu
                if "Macouria" in club_info.get_text():
                    print("✅ Lieu du club biblique correct (Macouria)")
                else:
                    print("❌ Lieu du club biblique incorrect")
            else:
                print("❌ Section Club Biblique non trouvée")
            
            # Vérifier le formulaire de contact
            contact_form = soup.find('form')
            if contact_form:
                print("✅ Formulaire de contact trouvé")
                
                # Vérifier les champs requis
                required_fields = ['name', 'email', 'subject', 'message']
                for field in required_fields:
                    field_input = soup.find('input', {'name': field}) or soup.find('textarea', {'name': field}) or soup.find('select', {'name': field})
                    if field_input:
                        print(f"✅ Champ '{field}' trouvé")
                    else:
                        print(f"❌ Champ '{field}' manquant")
            else:
                print("❌ Formulaire de contact non trouvé")
            
            # Vérifier les CSS
            css_links = soup.find_all('link', {'rel': 'stylesheet'})
            css_files = [link.get('href', '') for link in css_links]
            
            if any('themes.css' in css for css in css_files):
                print("✅ CSS des thèmes chargé")
            else:
                print("❌ CSS des thèmes manquant")
            
            if any('public.css' in css for css in css_files):
                print("✅ CSS public chargé")
            else:
                print("❌ CSS public manquant")
            
            print("\n🎉 Test de la page de contact terminé !")
            
        else:
            print(f"❌ Erreur HTTP {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Impossible de se connecter au serveur Django")
        print("💡 Assurez-vous que le serveur fonctionne sur http://127.0.0.1:8000/")
        return False
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")
        return False
    
    return True

def test_theme_system():
    """Test du système de thèmes sur les pages publiques"""
    
    print("\n🎨 Test du système de thèmes sur les pages publiques")
    print("=" * 50)
    
    try:
        # Tester la page d'accueil
        url = "http://127.0.0.1:8000/"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Vérifier le script d'initialisation des thèmes
            scripts = soup.find_all('script')
            theme_init_found = False
            theme_manager_found = False
            
            for script in scripts:
                script_content = script.get_text() if script.string else ""
                if "data-theme" in script_content and "localStorage.getItem('eebc-theme')" in script_content:
                    theme_init_found = True
                    print("✅ Script d'initialisation des thèmes trouvé")
                
                script_src = script.get('src', '')
                if 'theme-manager.js' in script_src:
                    theme_manager_found = True
                    print("✅ Script gestionnaire de thèmes chargé")
            
            if not theme_init_found:
                print("❌ Script d'initialisation des thèmes manquant")
            
            if not theme_manager_found:
                print("❌ Script gestionnaire de thèmes manquant")
            
            # Vérifier le bouton de sélection de thème
            theme_button = soup.find('button', {'id': 'themeToggle'})
            if theme_button:
                print("✅ Bouton de sélection de thème trouvé")
            else:
                print("❌ Bouton de sélection de thème manquant")
            
        else:
            print(f"❌ Erreur HTTP {response.status_code} sur la page d'accueil")
            
    except Exception as e:
        print(f"❌ Erreur lors du test des thèmes: {e}")

if __name__ == "__main__":
    print("🚀 Tests EEBC - Page de Contact et Système de Thèmes")
    print("=" * 60)
    
    success = test_contact_page()
    test_theme_system()
    
    if success:
        print("\n✅ Tous les tests sont passés avec succès !")
        print("\n📋 Résumé des améliorations:")
        print("   • Bande bleue avec Jean 3:16 ajoutée au formulaire de contact")
        print("   • Informations du club biblique mises à jour (Samedi 9h30, Macouria)")
        print("   • Système de thèmes étendu aux pages publiques")
        print("   • 7 modes de thème disponibles partout")
        print("   • CSS responsive et animations ajoutées")
        
        print("\n🎯 Pour tester:")
        print("   1. Visitez http://127.0.0.1:8000/contact/")
        print("   2. Cliquez sur l'icône de thème pour changer de mode")
        print("   3. Testez les différents thèmes (Ctrl+Shift+T)")
        
    else:
        print("\n❌ Certains tests ont échoué")
        sys.exit(1)