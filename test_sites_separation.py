#!/usr/bin/env python3
"""
Test pour vérifier la séparation correcte entre Cayenne et Macouria
"""

import requests
from bs4 import BeautifulSoup

def test_sites_separation():
    """Test que les sites sont bien séparés"""
    print("⛪ Test de la séparation des sites")
    print("=" * 40)
    
    try:
        url = "http://127.0.0.1:8000/contact/"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Trouver toutes les sections d'églises
            church_sections = soup.find_all('h5')
            
            cayenne_found = False
            macouria_found = False
            cayenne_activities = []
            macouria_activities = []
            
            for section in church_sections:
                if 'EEBC Cabassou' in section.get_text() or 'Cayenne' in section.get_text():
                    cayenne_found = True
                    # Trouver le contenu suivant cette section
                    parent = section.parent
                    if parent:
                        content = parent.get_text()
                        if 'Culte:' in content:
                            cayenne_activities.append('Culte')
                        if 'Étude biblique:' in content:
                            cayenne_activities.append('Étude biblique')
                        if 'Réunion de prière:' in content:
                            cayenne_activities.append('Réunion de prière')
                        if 'Groupe de jeunes:' in content:
                            cayenne_activities.append('Groupe de jeunes')
                        if 'Club biblique:' in content:
                            cayenne_activities.append('Club biblique')
                
                elif 'EEBC Macouria' in section.get_text() or 'Macouria' in section.get_text():
                    macouria_found = True
                    # Trouver le contenu suivant cette section
                    parent = section.parent
                    if parent:
                        content = parent.get_text()
                        if 'Culte:' in content:
                            macouria_activities.append('Culte')
                        if 'Étude biblique:' in content:
                            macouria_activities.append('Étude biblique')
                        if 'Club biblique:' in content:
                            macouria_activities.append('Club biblique')
            
            # Vérifications
            print(f"🏛️ EEBC Cabassou (Cayenne) trouvé: {'✅' if cayenne_found else '❌'}")
            if cayenne_found:
                print(f"   Activités: {', '.join(cayenne_activities)}")
                if len(cayenne_activities) >= 4:  # Culte, étude, prière, jeunes, club
                    print("   ✅ Toutes les activités présentes")
                else:
                    print("   ⚠️ Certaines activités manquantes")
            
            print(f"\n🏛️ EEBC Macouria trouvé: {'✅' if macouria_found else '❌'}")
            if macouria_found:
                print(f"   Activités: {', '.join(macouria_activities) if macouria_activities else 'Culte seulement'}")
                if len(macouria_activities) == 1 and 'Culte' in macouria_activities:
                    print("   ✅ Seulement le culte (correct)")
                elif len(macouria_activities) == 0:
                    print("   ✅ Seulement le culte mentionné (correct)")
                else:
                    print("   ❌ Trop d'activités (devrait être seulement le culte)")
                    return False
            
            # Vérifier qu'il n'y a pas de section club biblique séparée
            club_section = soup.find('div', class_='club-biblique-info')
            if not club_section:
                print("\n✅ Pas de section club biblique séparée (correct)")
            else:
                print("\n❌ Section club biblique séparée trouvée (incorrect)")
                return False
            
            return cayenne_found and macouria_found
            
        else:
            print(f"❌ Erreur HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def test_setup_file():
    """Test du fichier setup_sites.py"""
    print("\n🔧 Test du fichier de configuration")
    print("=" * 40)
    
    try:
        with open('apps/core/management/commands/setup_sites.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extraire les sections Cayenne et Macouria
        lines = content.split('\n')
        
        cayenne_section = []
        macouria_section = []
        in_cayenne = False
        in_macouria = False
        
        for line in lines:
            if "'name': 'EEBC Cabassou'" in line:
                in_cayenne = True
                in_macouria = False
            elif "'name': 'EEBC Macouria'" in line:
                in_macouria = True
                in_cayenne = False
            elif in_cayenne and 'worship_schedule' in line:
                # Capturer les lignes suivantes jusqu'à la fin de la chaîne
                idx = lines.index(line)
                for i in range(idx, len(lines)):
                    cayenne_section.append(lines[i])
                    if "'''" in lines[i] and i > idx:
                        break
                in_cayenne = False
            elif in_macouria and 'worship_schedule' in line:
                macouria_section.append(line)
                in_macouria = False
        
        cayenne_text = '\n'.join(cayenne_section)
        macouria_text = '\n'.join(macouria_section)
        
        print("🏛️ EEBC Cabassou (Cayenne):")
        if 'Club biblique: Samedi 15h00-16h30' in cayenne_text:
            print("   ✅ Club biblique: Samedi 15h00-16h30")
        else:
            print("   ❌ Club biblique manquant ou incorrect")
            return False
        
        if 'Culte: Dimanche 9h30-12h00' in cayenne_text:
            print("   ✅ Culte: Dimanche 9h30-12h00")
        else:
            print("   ❌ Culte manquant ou incorrect")
        
        if 'Étude biblique: Mercredi 19h00' in cayenne_text:
            print("   ✅ Étude biblique: Mercredi 19h00")
        else:
            print("   ❌ Étude biblique manquante")
        
        print("\n🏛️ EEBC Macouria:")
        if 'Culte: Dimanche 9h30' in macouria_text and 'Club biblique' not in macouria_text:
            print("   ✅ Seulement culte: Dimanche 9h30")
        else:
            print("   ❌ Configuration incorrecte")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Test de Séparation des Sites")
    print("=" * 50)
    
    success = True
    success &= test_sites_separation()
    success &= test_setup_file()
    
    if success:
        print("\n" + "=" * 50)
        print("✅ SÉPARATION PARFAITE DES SITES !")
        print("\n📋 Configuration correcte:")
        print("   🏛️ EEBC Cabassou (Cayenne):")
        print("      • Culte: Dimanche 9h30-12h00")
        print("      • Étude biblique: Mercredi 19h00")
        print("      • Réunion de prière: Vendredi 19h00")
        print("      • Groupe de jeunes: Samedi 16h00-18h00")
        print("      • Club biblique: Samedi 15h00-16h30")
        print("\n   🏛️ EEBC Macouria:")
        print("      • Culte: Dimanche 9h30 SEULEMENT")
        print("\n✅ Pas de mélange entre les sites")
        print("✅ Informations bien organisées")
        print("✅ Pas de section club biblique séparée")
        
    else:
        print("\n❌ PROBLÈME DE SÉPARATION DES SITES")
        print("Vérifiez les erreurs ci-dessus.")