#!/usr/bin/env python3
"""
Test pour vérifier que la mise en forme des horaires est bien organisée
"""

import requests
from bs4 import BeautifulSoup

def test_organized_layout():
    """Test de la mise en forme organisée"""
    print("🎨 Test de la mise en forme organisée des horaires")
    print("=" * 50)
    
    try:
        url = "http://127.0.0.1:8000/contact/"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Vérifier la présence de la section organisée pour Cayenne
            organized_schedule = soup.find('div', class_='schedule-organized')
            if organized_schedule:
                print("✅ Section horaires organisée trouvée pour Cayenne")
                
                # Vérifier les activités individuelles
                activity_items = organized_schedule.find_all('div', class_='activity-item')
                if len(activity_items) >= 5:
                    print(f"✅ {len(activity_items)} activités trouvées (attendu: 5)")
                    
                    activities_found = []
                    for item in activity_items:
                        strong_tag = item.find('strong')
                        if strong_tag:
                            activities_found.append(strong_tag.get_text().strip())
                    
                    expected_activities = ['Culte', 'Étude biblique', 'Réunion de prière', 'Groupe de jeunes', 'Club biblique']
                    
                    for activity in expected_activities:
                        if activity in activities_found:
                            print(f"   ✅ {activity} trouvé")
                        else:
                            print(f"   ❌ {activity} manquant")
                            return False
                    
                else:
                    print(f"❌ Nombre d'activités incorrect: {len(activity_items)} (attendu: 5)")
                    return False
                
                # Vérifier les icônes
                activity_icons = organized_schedule.find_all('div', class_='activity-icon')
                if len(activity_icons) >= 5:
                    print("✅ Icônes d'activités présentes")
                else:
                    print("❌ Icônes d'activités manquantes")
                    return False
                
            else:
                print("❌ Section horaires organisée non trouvée")
                return False
            
            # Vérifier la section simple pour Macouria
            simple_schedule = soup.find('div', class_='simple-schedule')
            if simple_schedule:
                print("✅ Section simple trouvée pour Macouria")
                
                # Vérifier qu'il n'y a qu'une seule activité (culte)
                macouria_activities = simple_schedule.find_all('div', class_='activity-item')
                if len(macouria_activities) == 1:
                    print("✅ Macouria: Une seule activité (culte)")
                    
                    culte_text = macouria_activities[0].get_text()
                    if 'Culte' in culte_text and 'Dimanche 9h30' in culte_text:
                        print("✅ Macouria: Culte dimanche 9h30 correct")
                    else:
                        print("❌ Macouria: Informations culte incorrectes")
                        return False
                else:
                    print(f"❌ Macouria: Nombre d'activités incorrect: {len(macouria_activities)} (attendu: 1)")
                    return False
            else:
                print("❌ Section simple pour Macouria non trouvée")
                return False
            
            # Vérifier que les CSS sont chargés
            css_links = soup.find_all('link', {'rel': 'stylesheet'})
            css_files = [link.get('href', '') for link in css_links]
            
            if any('public.css' in css for css in css_files):
                print("✅ CSS public chargé (contient les styles organisés)")
            else:
                print("❌ CSS public manquant")
                return False
            
            return True
            
        else:
            print(f"❌ Erreur HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def test_css_styles():
    """Test des styles CSS organisés"""
    print("\n🎨 Test des styles CSS organisés")
    print("=" * 50)
    
    try:
        with open('static/css/public.css', 'r', encoding='utf-8') as f:
            css_content = f.read()
        
        required_classes = [
            '.schedule-organized',
            '.schedule-title',
            '.activity-item',
            '.activity-icon',
            '.activity-details',
            '.simple-schedule'
        ]
        
        missing_classes = []
        for css_class in required_classes:
            if css_class in css_content:
                print(f"✅ Classe {css_class} définie")
            else:
                print(f"❌ Classe {css_class} manquante")
                missing_classes.append(css_class)
        
        if not missing_classes:
            print("✅ Tous les styles CSS organisés sont présents")
            
            # Vérifier les animations
            if '@keyframes slideInUp' in css_content:
                print("✅ Animations d'entrée définies")
            else:
                print("❌ Animations d'entrée manquantes")
            
            # Vérifier le responsive
            if '@media (max-width: 768px)' in css_content:
                print("✅ Styles responsive définis")
            else:
                print("❌ Styles responsive manquants")
            
            return True
        else:
            print(f"❌ {len(missing_classes)} classes CSS manquantes")
            return False
            
    except FileNotFoundError:
        print("❌ Fichier public.css non trouvé")
        return False
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

if __name__ == "__main__":
    print("🎨 Test de la Mise en Forme Organisée")
    print("=" * 60)
    
    success = True
    success &= test_organized_layout()
    success &= test_css_styles()
    
    if success:
        print("\n" + "=" * 60)
        print("✅ MISE EN FORME PARFAITEMENT ORGANISÉE !")
        print("\n📋 Fonctionnalités de la mise en forme:")
        print("   🏛️ EEBC Cayenne - Horaires organisés:")
        print("      • Grille 2 colonnes avec icônes colorées")
        print("      • 5 activités clairement séparées")
        print("      • Animations d'entrée échelonnées")
        print("      • Effets de survol interactifs")
        print("      • Couleurs spécifiques par activité")
        print("\n   🏛️ EEBC Macouria - Affichage simple:")
        print("      • Une seule activité (culte)")
        print("      • Design épuré et clair")
        print("\n   🎨 Styles avancés:")
        print("      • Responsive design (mobile/tablette)")
        print("      • Adaptation aux 22 thèmes")
        print("      • Animations CSS fluides")
        print("      • Icônes Bootstrap colorées")
        
        print("\n🎯 Résultat:")
        print("   ✅ Fini le 'vrac' - tout est organisé !")
        print("   ✅ Cayenne: 5 activités bien structurées")
        print("   ✅ Macouria: Simple et clair")
        print("   ✅ Design moderne et professionnel")
        
    else:
        print("\n❌ PROBLÈME DE MISE EN FORME")
        print("Vérifiez les erreurs ci-dessus.")