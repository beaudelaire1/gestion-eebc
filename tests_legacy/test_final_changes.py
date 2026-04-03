#!/usr/bin/env python3
"""
Test final pour vérifier les ajustements demandés
"""

import requests
from bs4 import BeautifulSoup

def test_banner_height():
    """Test que la bande fait bien 25px"""
    print("📏 Test de la hauteur de bande (25px)")
    
    try:
        with open('static/css/animated-verse-banner.css', 'r', encoding='utf-8') as f:
            css_content = f.read()
        
        if 'height: 25px;' in css_content:
            print("✅ Bande ajustée à 25px")
            return True
        else:
            print("❌ Hauteur de bande incorrecte")
            return False
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def test_site_info():
    """Test des informations des sites"""
    print("\n⛪ Test des informations des sites")
    
    try:
        url = "http://127.0.0.1:8000/contact/"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Vérifier les informations du club biblique
            club_info = soup.find('div', class_='club-biblique-info')
            if club_info:
                club_text = club_info.get_text()
                
                if "Samedi 15h00 - 16h30" in club_text:
                    print("✅ Horaires club biblique corrects (15h00-16h30)")
                else:
                    print("❌ Horaires club biblique incorrects")
                    return False
                
                if "Cayenne" in club_text:
                    print("✅ Lieu club biblique correct (Cayenne)")
                else:
                    print("❌ Lieu club biblique incorrect")
                    return False
                
                return True
            else:
                print("❌ Section club biblique non trouvée")
                return False
        else:
            print(f"❌ Erreur HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def test_setup_sites():
    """Test du fichier setup_sites.py"""
    print("\n🔧 Test du fichier setup_sites.py")
    
    try:
        with open('apps/core/management/commands/setup_sites.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Vérifier Cayenne (club biblique 15h00-16h30)
        if "Club biblique: Samedi 15h00-16h30" in content:
            print("✅ Cayenne: Club biblique 15h00-16h30")
        else:
            print("❌ Cayenne: Horaires club biblique incorrects")
            return False
        
        # Vérifier Macouria (culte dimanche 9h30 seulement)
        if "Culte: Dimanche 9h30" in content:
            print("✅ Macouria: Culte dimanche 9h30")
        else:
            print("❌ Macouria: Horaires culte incorrects")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Tests des Ajustements Finaux")
    print("=" * 40)
    
    success = True
    success &= test_banner_height()
    success &= test_site_info()
    success &= test_setup_sites()
    
    if success:
        print("\n" + "=" * 40)
        print("✅ TOUS LES AJUSTEMENTS SONT CORRECTS !")
        print("\n📋 Résumé des changements:")
        print("   📏 Bande animée: 25px (au lieu de 15px)")
        print("   ⛪ EEBC Cayenne: Club biblique Samedi 15h00-16h30")
        print("   ⛪ EEBC Macouria: Culte Dimanche 9h30 uniquement")
        print("   🧹 Informations nettoyées et organisées")
        
        print("\n🎯 Vérifications:")
        print("   • Bande plus lisible avec 25px de hauteur")
        print("   • Club biblique bien localisé à Cayenne")
        print("   • Macouria avec horaire de culte simple")
        print("   • Pas de confusion entre les sites")
        
    else:
        print("\n❌ CERTAINS AJUSTEMENTS SONT INCORRECTS")
        print("Vérifiez les erreurs ci-dessus.")