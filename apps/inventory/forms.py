from django import forms
from apps.core.forms import EnhancedModelForm
from .models import Equipment, Category


class EquipmentForm(EnhancedModelForm):
    """Formulaire pour créer/modifier un équipement."""
    
    class Meta:
        model = Equipment
        fields = [
            'name', 'description', 'category', 'quantity', 'condition',
            'location', 'purchase_date', 'purchase_price', 'responsible',
            'notes', 'photo'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'Nom de l\'équipement'
            }),
            'description': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Description détaillée...'
            }),
            'quantity': forms.NumberInput(attrs={'min': 1}),
            'location': forms.TextInput(attrs={
                'placeholder': 'Emplacement de l\'équipement'
            }),
            'purchase_date': forms.DateInput(attrs={'type': 'date'}),
            'purchase_price': forms.NumberInput(attrs={
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            'notes': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Notes additionnelles...'
            }),
            'photo': forms.FileInput(attrs={'accept': 'image/*'})
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Rendre certains champs optionnels plus clairs
        self.fields['description'].required = False
        self.fields['category'].required = False
        self.fields['location'].required = False
        self.fields['purchase_date'].required = False
        self.fields['purchase_price'].required = False
        self.fields['responsible'].required = False
        self.fields['notes'].required = False
        self.fields['photo'].required = False
        
        # Ajouter une option vide pour la catégorie
        self.fields['category'].empty_label = "Sélectionner une catégorie"
        self.fields['responsible'].empty_label = "Aucun responsable assigné"
        
        # Personnaliser les labels
        self.fields['name'].label = "Nom de l'équipement *"
        self.fields['description'].label = "Description"
        self.fields['category'].label = "Catégorie"
        self.fields['quantity'].label = "Quantité *"
        self.fields['condition'].label = "État *"
        self.fields['location'].label = "Emplacement"
        self.fields['purchase_date'].label = "Date d'achat"
        self.fields['purchase_price'].label = "Prix d'achat (€)"
        self.fields['responsible'].label = "Responsable"
        self.fields['notes'].label = "Notes"
        self.fields['photo'].label = "Photo"
    
    def clean_quantity(self):
        """Validation de la quantité."""
        quantity = self.cleaned_data.get('quantity')
        if quantity is not None and quantity < 1:
            raise forms.ValidationError("La quantité doit être d'au moins 1.")
        return quantity
    
    def clean_purchase_price(self):
        """Validation du prix d'achat."""
        price = self.cleaned_data.get('purchase_price')
        if price is not None and price < 0:
            raise forms.ValidationError("Le prix d'achat ne peut pas être négatif.")
        return price