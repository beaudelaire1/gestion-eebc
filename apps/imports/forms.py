from django import forms
from .models import ImportLog


class ImportForm(forms.ModelForm):
    """
    Formulaire pour l'upload de fichiers d'import.
    """
    
    class Meta:
        model = ImportLog
        fields = ['import_type', 'file_path']
        widgets = {
            'import_type': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'file_path': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.xlsx,.xls',
                'required': True
            })
        }
        labels = {
            'import_type': 'Type d\'import',
            'file_path': 'Fichier Excel'
        }
        help_texts = {
            'file_path': 'Formats acceptés: .xlsx, .xls (max 10MB)'
        }
    
    def clean_file_path(self):
        file = self.cleaned_data.get('file_path')
        
        if file:
            # Vérifier la taille (10MB max)
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError("Le fichier ne doit pas dépasser 10MB.")
            
            # Vérifier l'extension
            allowed_extensions = ['.xlsx', '.xls']
            file_extension = '.' + file.name.split('.')[-1].lower()
            
            if file_extension not in allowed_extensions:
                raise forms.ValidationError(
                    f"Format de fichier non supporté. Utilisez: {', '.join(allowed_extensions)}"
                )
        
        return file
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        if self.cleaned_data.get('file_path'):
            instance.file_name = self.cleaned_data['file_path'].name
        
        if commit:
            instance.save()
        
        return instance