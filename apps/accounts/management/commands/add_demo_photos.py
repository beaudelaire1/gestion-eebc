"""
Commande pour ajouter des photos de démonstration aux enfants et membres.
Utilise des avatars générés depuis pravatar.cc
"""
import os
import urllib.request
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.conf import settings


class Command(BaseCommand):
    help = 'Ajoute des photos de démonstration aux enfants et membres'

    def handle(self, *args, **options):
        from apps.bibleclub.models import Child
        from apps.members.models import Member
        
        self.stdout.write(self.style.NOTICE('Ajout des photos de demonstration...'))
        
        # Photos pour les enfants
        self.stdout.write('Photos enfants...')
        children = Child.objects.all()
        for i, child in enumerate(children):
            if not child.photo:
                try:
                    # Utiliser pravatar.cc pour des avatars aléatoires
                    # Différencier garçons et filles
                    seed = f"{child.first_name}{child.last_name}{i}"
                    if child.gender == 'M':
                        # Avatars de type garçon (seed pairs)
                        url = f"https://api.dicebear.com/7.x/adventurer-neutral/png?seed={seed}&backgroundColor=b6e3f4"
                    else:
                        # Avatars de type fille (seed impairs)
                        url = f"https://api.dicebear.com/7.x/adventurer-neutral/png?seed={seed}&backgroundColor=ffd5dc"
                    
                    # Télécharger l'image
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    response = urllib.request.urlopen(req, timeout=10)
                    image_data = response.read()
                    
                    # Sauvegarder
                    filename = f"child_{child.id}_{child.first_name.lower()}.png"
                    child.photo.save(filename, ContentFile(image_data), save=True)
                    self.stdout.write(f"  + Photo ajoutee pour {child.full_name}")
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"  ! Erreur pour {child.full_name}: {e}"))
        
        # Photos pour les membres
        self.stdout.write('Photos membres...')
        members = Member.objects.all()
        for i, member in enumerate(members):
            if not member.photo:
                try:
                    seed = f"{member.first_name}{member.last_name}{i}"
                    if member.gender == 'M':
                        url = f"https://api.dicebear.com/7.x/avataaars/png?seed={seed}&backgroundColor=b6e3f4"
                    else:
                        url = f"https://api.dicebear.com/7.x/avataaars/png?seed={seed}&backgroundColor=ffd5dc"
                    
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    response = urllib.request.urlopen(req, timeout=10)
                    image_data = response.read()
                    
                    filename = f"member_{member.id}_{member.first_name.lower()}.png"
                    member.photo.save(filename, ContentFile(image_data), save=True)
                    self.stdout.write(f"  + Photo ajoutee pour {member.full_name}")
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"  ! Erreur pour {member.full_name}: {e}"))
        
        self.stdout.write(self.style.SUCCESS('Photos de demonstration ajoutees avec succes!'))

