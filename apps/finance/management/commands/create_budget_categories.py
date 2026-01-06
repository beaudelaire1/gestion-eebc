"""
Commande pour créer les catégories de budget prédéfinies.
"""

from django.core.management.base import BaseCommand
from apps.finance.models import BudgetCategory


class Command(BaseCommand):
    help = 'Crée les catégories de budget prédéfinies'

    def handle(self, *args, **options):
        """Crée les catégories de budget par défaut."""
        
        categories = [
            {
                'name': 'Événements',
                'description': 'Organisation d\'événements, conférences, séminaires',
                'color': '#FF6B6B'
            },
            {
                'name': 'Matériel',
                'description': 'Achat de matériel, équipements, fournitures',
                'color': '#4ECDC4'
            },
            {
                'name': 'Transport',
                'description': 'Frais de transport, déplacements, carburant',
                'color': '#45B7D1'
            },
            {
                'name': 'Formation',
                'description': 'Formation du personnel, stages, cours',
                'color': '#96CEB4'
            },
            {
                'name': 'Communication',
                'description': 'Marketing, publicité, supports de communication',
                'color': '#FFEAA7'
            },
            {
                'name': 'Maintenance',
                'description': 'Entretien, réparations, maintenance des équipements',
                'color': '#DDA0DD'
            }
        ]
        
        created_count = 0
        updated_count = 0
        
        for cat_data in categories:
            category, created = BudgetCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults={
                    'description': cat_data['description'],
                    'color': cat_data['color'],
                    'is_active': True
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Catégorie "{category.name}" créée')
                )
            else:
                # Mettre à jour la description et la couleur si nécessaire
                if (category.description != cat_data['description'] or 
                    category.color != cat_data['color']):
                    category.description = cat_data['description']
                    category.color = cat_data['color']
                    category.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(f'↻ Catégorie "{category.name}" mise à jour')
                    )
                else:
                    self.stdout.write(
                        self.style.HTTP_INFO(f'- Catégorie "{category.name}" existe déjà')
                    )
        
        # Résumé
        self.stdout.write('\n' + '='*50)
        self.stdout.write(f'Résumé:')
        self.stdout.write(f'  • {created_count} catégorie(s) créée(s)')
        self.stdout.write(f'  • {updated_count} catégorie(s) mise(s) à jour')
        self.stdout.write(f'  • {len(categories)} catégorie(s) au total')
        
        if created_count > 0 or updated_count > 0:
            self.stdout.write(
                self.style.SUCCESS('\n✓ Catégories de budget initialisées avec succès!')
            )
        else:
            self.stdout.write(
                self.style.HTTP_INFO('\n- Toutes les catégories existent déjà.')
            )