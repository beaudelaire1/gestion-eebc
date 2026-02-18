import re
import pandas as pd
from datetime import datetime, date
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from django.core.cache import cache
from apps.members.models import Member
from apps.bibleclub.models import Child, BibleClass, AgeGroup
from .models import ImportLog


# ── Constantes de validation ──────────────────────────────────────────
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
PHONE_REGEX = re.compile(r'^[\d\s\-\+\(\)]{10,20}$')


def validate_email(value: str) -> str:
    """Valide et normalise une adresse email."""
    value = str(value).strip().lower()
    if not EMAIL_REGEX.match(value):
        raise ValidationError(f"Adresse email invalide : {value}")
    return value


def validate_phone(value: str) -> str:
    """Valide et normalise un numéro de téléphone. Plus tolérant pour les formats Excel."""
    # Excel stocke parfois les numéros comme float (ex: 694123456.0)
    if isinstance(value, (int, float)):
        value = str(int(value))
    else:
        value = str(value).strip()
    
    # Compter seulement les chiffres
    digits_only = re.sub(r'[^\d]', '', value)
    
    # Récupérer le 0 initial si le numéro Guyanais commence sans
    if len(digits_only) == 9 and digits_only[0] in '16789':
        digits_only = '0' + digits_only
    
    if len(digits_only) < 8:
        raise ValidationError(f"Numéro de téléphone trop court : {value}")
    
    return value


def validate_postal_code(value) -> str:
    """Valide et normalise un code postal. Non obligatoire.
    Accepte les entiers, floats Excel (97300.0 -> 97300) et chaînes."""
    # Gérer les floats Excel (97300.0 -> '97300')
    if isinstance(value, float):
        value = str(int(value))
    elif isinstance(value, int):
        value = str(value)
    else:
        value = str(value).strip()
    # Nettoyer l'éventuel .0 résiduel
    if value.endswith('.0'):
        value = value[:-2]
    return value


class ExcelImportService:
    """Service pour l'import de données depuis des fichiers Excel."""
    
    def __init__(self, import_log):
        self.import_log = import_log
        self.errors = []
        self.successes = []
        self.warnings = []
        self.created_count = 0
        self.updated_count = 0
    
    def process_import(self):
        """Traite l'import selon le type."""
        try:
            self.import_log.status = ImportLog.Status.PROCESSING
            self.import_log.save()
            
            if self.import_log.import_type == ImportLog.ImportType.MEMBERS:
                self._import_members()
            elif self.import_log.import_type == ImportLog.ImportType.CHILDREN:
                self._import_children()
            
            self._finalize_import()
            
        except Exception as e:
            self.import_log.status = ImportLog.Status.ERROR
            self.import_log.error_log = str(e)
            self.import_log.completed_at = timezone.now()
            self.import_log.save()
            raise
    
    def _import_members(self):
        """Importe les membres depuis un fichier Excel."""
        df = pd.read_excel(self.import_log.file_path.path)
        
        expected_columns = {
            'prenom': 'first_name', 'nom': 'last_name', 'email': 'email',
            'telephone': 'phone', 'date_naissance': 'date_of_birth', 'genre': 'gender',
            'adresse': 'address', 'ville': 'city', 'code_postal': 'postal_code',
            'profession': 'profession', 'statut': 'status', 'date_arrivee': 'date_joined',
            'baptise': 'is_baptized', 'date_bapteme': 'baptism_date',
            'situation_familiale': 'marital_status', 'notes': 'notes'
        }
        
        self.import_log.total_rows = len(df)
        self.import_log.save()
        
        for index, row in df.iterrows():
            try:
                with transaction.atomic():
                    self._process_member_row(row, expected_columns, index + 1)
                    self.import_log.success_rows += 1
            except Exception as e:
                self.import_log.error_rows += 1
                self.errors.append(f"Ligne {index + 1}: {str(e)}")
            
            self.import_log.processed_rows += 1
            if self.import_log.processed_rows % 10 == 0:
                self.import_log.save()
    
    def _process_member_row(self, row, column_mapping, row_number):
        """Traite une ligne de membre avec validations avancées."""
        member_data = {}
        row_warnings = []
        
        for excel_col, model_field in column_mapping.items():
            if excel_col in row and pd.notna(row[excel_col]):
                value = row[excel_col]
                
                # ── Dates ──
                if model_field in ['date_of_birth', 'date_joined', 'baptism_date']:
                    if isinstance(value, str):
                        for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%d.%m.%Y'):
                            try:
                                value = datetime.strptime(value.strip(), fmt).date()
                                break
                            except ValueError:
                                continue
                        else:
                            raise ValidationError(f"Format de date invalide: {value}")
                    elif hasattr(value, 'date'):
                        value = value.date()
                    
                    # Validation de cohérence
                    if model_field == 'date_of_birth' and value > date.today():
                        raise ValidationError(f"Date de naissance dans le futur: {value}")
                    if model_field == 'baptism_date' and value > date.today():
                        raise ValidationError(f"Date de baptême dans le futur: {value}")
                
                # ── Genre ──
                elif model_field == 'gender':
                    value = str(value).strip().upper()
                    gender_mapping = {'MASCULIN': 'M', 'FÉMININ': 'F', 'FEMININ': 'F', 'HOMME': 'M', 'FEMME': 'F', 'H': 'M'}
                    value = gender_mapping.get(value, value)
                    if value not in ['M', 'F']:
                        row_warnings.append(f"Genre '{value}' non reconnu, champ ignoré")
                        continue  # ignore ce champ, continue la ligne
                
                # ── Booléen : baptisé ──
                elif model_field == 'is_baptized':
                    if isinstance(value, str):
                        value = value.strip().lower() in ['oui', 'yes', 'true', '1', 'vrai']
                    else:
                        value = bool(value)
                
                # ── Statut ──
                elif model_field == 'status':
                    status_mapping = {
                        'actif': Member.Status.ACTIF,
                        'inactif': Member.Status.INACTIF,
                        'visiteur': Member.Status.VISITEUR,
                        'transfere': Member.Status.TRANSFERE,
                        'transferé': Member.Status.TRANSFERE,
                    }
                    value = status_mapping.get(str(value).strip().lower(), Member.Status.ACTIF)
                
                # ── Email ──
                elif model_field == 'email':
                    value = str(value).strip()
                    if value:
                        try:
                            value = validate_email(value)
                        except ValidationError:
                            row_warnings.append(f"Email invalide ignoré (membre importé sans email) : {value}")
                            continue  # champ ignoré, le reste de la ligne continue
                
                # ── Téléphone ──
                elif model_field == 'phone':
                    value = str(value).strip()
                    if value:
                        try:
                            value = validate_phone(value)
                        except ValidationError:
                            row_warnings.append(f"Format téléphone douteux: {value}")
                
                # ── Code postal ──
                elif model_field == 'postal_code':
                    value = validate_postal_code(value)
                
                # ── Nettoyage texte générique ──
                elif isinstance(value, str):
                    value = value.strip()
                
                member_data[model_field] = value
        
        # Champs obligatoires
        if not member_data.get('first_name') or not member_data.get('last_name'):
            raise ValidationError("Prénom et nom obligatoires")
        
        # Détection de doublon par nom + date de naissance (plus fiable)
        first_name = member_data['first_name']
        last_name = member_data['last_name']
        
        existing_member = None
        
        # Priorité 1 : email + vérification d'identité (évite les emails familiaux partagés)
        if member_data.get('email'):
            email_matches = Member.objects.filter(email__iexact=member_data['email'])
            if email_matches.count() == 1:
                email_member = email_matches.first()
                same_name = (
                    email_member.first_name.strip().lower() == first_name.strip().lower() and
                    email_member.last_name.strip().lower() == last_name.strip().lower()
                )
                same_dob = (
                    member_data.get('date_of_birth') and
                    email_member.date_of_birth == member_data.get('date_of_birth')
                )
                if same_name or same_dob:
                    existing_member = email_member
                else:
                    row_warnings.append(
                        f"Email partagé détecté ({member_data['email']}) : création d'un nouveau membre"
                    )
            elif email_matches.count() > 1:
                row_warnings.append(
                    f"Email non unique en base ({member_data['email']}) : correspondance ignorée"
                )
        
        # Priorité 2 : doublon par nom + date de naissance  
        if not existing_member and member_data.get('date_of_birth'):
            existing_member = Member.objects.filter(
                first_name__iexact=first_name,
                last_name__iexact=last_name,
                date_of_birth=member_data['date_of_birth']
            ).first()
        
        # Note: pas de détection par nom seul (trop risqué, homonymes fréquents)
        
        if existing_member:
            for field, value in member_data.items():
                setattr(existing_member, field, value)
            existing_member.save()
            self.updated_count += 1
            self.successes.append(f"Ligne {row_number}: {existing_member.full_name} mis \u00e0 jour")
        else:
            member = Member.objects.create(**member_data)
            self.created_count += 1
            self.successes.append(f"Ligne {row_number}: {member.full_name} créé")
        
        # Ajouter les avertissements
        for w in row_warnings:
            self.warnings.append(f"Ligne {row_number}: {w}")
    
    def _import_children(self):
        """Importe les enfants depuis un fichier Excel."""
        df = pd.read_excel(self.import_log.file_path.path)
        
        expected_columns = {
            'prenom': 'first_name', 'nom': 'last_name', 'date_naissance': 'date_of_birth',
            'genre': 'gender', 'nom_pere': 'father_name', 'telephone_pere': 'father_phone',
            'email_pere': 'father_email', 'nom_mere': 'mother_name',
            'telephone_mere': 'mother_phone', 'email_mere': 'mother_email',
            'contact_urgence': 'emergency_contact', 'telephone_urgence': 'emergency_phone',
            'allergies': 'allergies', 'notes_medicales': 'medical_notes',
            'besoin_transport': 'needs_transport', 'adresse_ramassage': 'pickup_address',
            'notes': 'notes'
        }
        
        self.import_log.total_rows = len(df)
        self.import_log.save()
        
        for index, row in df.iterrows():
            try:
                with transaction.atomic():
                    self._process_child_row(row, expected_columns, index + 1)
                    self.import_log.success_rows += 1
            except Exception as e:
                self.import_log.error_rows += 1
                self.errors.append(f"Ligne {index + 1}: {str(e)}")
            
            self.import_log.processed_rows += 1
            if self.import_log.processed_rows % 10 == 0:
                self.import_log.save()
    
    def _process_child_row(self, row, column_mapping, row_number):
        """Traite une ligne d'enfant avec validations avancées."""
        child_data = {}
        row_warnings = []
        
        for excel_col, model_field in column_mapping.items():
            if excel_col in row and pd.notna(row[excel_col]):
                value = row[excel_col]
                
                if model_field == 'date_of_birth':
                    if isinstance(value, str):
                        for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%d.%m.%Y'):
                            try:
                                value = datetime.strptime(value.strip(), fmt).date()
                                break
                            except ValueError:
                                continue
                        else:
                            raise ValidationError(f"Format de date invalide: {value}")
                    elif hasattr(value, 'date'):
                        value = value.date()
                    
                    # Vérifier que la date est cohérente pour un enfant
                    if value > date.today():
                        raise ValidationError(f"Date de naissance dans le futur: {value}")
                    age = (date.today() - value).days // 365
                    if age > 18:
                        row_warnings.append(f"Âge > 18 ans ({age} ans) — vérifier la date de naissance")
                
                elif model_field == 'gender':
                    value = str(value).strip().upper()
                    gender_mapping = {'MASCULIN': 'M', 'FÉMININ': 'F', 'FEMININ': 'F', 'GARÇON': 'M', 'GARCON': 'M', 'FILLE': 'F'}
                    value = gender_mapping.get(value, value)
                    if value not in ['M', 'F']:
                        row_warnings.append(f"Genre '{value}' non reconnu pour enfant, champ ignoré")
                        continue
                
                elif model_field == 'needs_transport':
                    if isinstance(value, str):
                        value = value.strip().lower() in ['oui', 'yes', 'true', '1', 'vrai']
                    else:
                        value = bool(value)
                
                # Validation email parent
                elif model_field in ['father_email', 'mother_email']:
                    value = str(value).strip()
                    if value:
                        try:
                            value = validate_email(value)
                        except ValidationError:
                            row_warnings.append(f"Email parent invalide ignoré: {value}")
                            continue
                
                # Validation téléphone parent
                elif model_field in ['father_phone', 'mother_phone', 'emergency_phone']:
                    value = str(value).strip()
                    if value:
                        try:
                            value = validate_phone(value)
                        except ValidationError:
                            row_warnings.append(f"Téléphone douteux: {value}")
                
                elif isinstance(value, str):
                    value = value.strip()
                
                child_data[model_field] = value
        
        required_fields = ['first_name', 'last_name', 'date_of_birth', 'father_name', 'father_phone']
        for field in required_fields:
            if not child_data.get(field):
                raise ValidationError(f"Champ obligatoire manquant: {field}")
        
        # Assigner à une classe selon l'âge
        birth_date = child_data['date_of_birth']
        age = (date.today() - birth_date).days // 365
        
        age_group = AgeGroup.objects.filter(min_age__lte=age, max_age__gte=age).first()
        if age_group:
            bible_class = BibleClass.objects.filter(age_group=age_group, is_active=True).first()
            if bible_class:
                child_data['bible_class'] = bible_class
        
        existing_child = Child.objects.filter(
            first_name__iexact=child_data['first_name'],
            last_name__iexact=child_data['last_name'],
            date_of_birth=child_data['date_of_birth']
        ).first()
        
        if existing_child:
            for field, value in child_data.items():
                setattr(existing_child, field, value)
            existing_child.save()
            self.updated_count += 1
            self.successes.append(f"Ligne {row_number}: {existing_child.full_name} mis \u00e0 jour")
        else:
            child = Child.objects.create(**child_data)
            self.created_count += 1
            self.successes.append(f"Ligne {row_number}: {child.full_name} créé")
    
    def _finalize_import(self):
        """Finalise l'import et met à jour les logs."""
        self.import_log.error_log = '\n'.join(self.errors)
        
        # R\u00e9sum\u00e9 en t\u00eate du log
        summary_lines = [
            f"=== R\u00c9SUM\u00c9 D'IMPORT ===",
            f"\u2705 Cr\u00e9\u00e9s    : {self.created_count}",
            f"\U0001f504 Mis \u00e0 jour : {self.updated_count}",
            f"\u274c Erreurs  : {self.import_log.error_rows}",
            f"\u26a0\ufe0f  Avertiss.: {len(self.warnings)}",
            f"Total trait\u00e9 : {self.import_log.processed_rows}",
            "=" * 30,
            "",
        ]
        
        # Ajouter les avertissements au log de succ\u00e8s
        success_parts = summary_lines + self.successes[:]
        if self.warnings:
            success_parts.append('\n--- Avertissements ---')
            success_parts.extend(self.warnings)
        
        self.import_log.success_log = '\n'.join(success_parts)
        self.import_log.completed_at = timezone.now()
        
        if self.import_log.error_rows == 0:
            self.import_log.status = ImportLog.Status.SUCCESS
        elif self.import_log.success_rows > 0:
            self.import_log.status = ImportLog.Status.PARTIAL
        else:
            self.import_log.status = ImportLog.Status.ERROR
        
        self.import_log.save()
        
        # Vider le cache pour que les listes de membres/enfants soient à jour immédiatement
        try:
            cache.clear()
        except Exception:
            pass


def generate_template_excel(import_type):
    """Génère un fichier Excel template pour l'import."""
    if import_type == 'members':
        sample_data = {
            'prenom': ['Jean', 'Marie'],
            'nom': ['Dupont', 'Martin'],
            'email': ['jean.dupont@email.com', 'marie.martin@email.com'],
            'telephone': ['0694123456', '0694654321'],
            'date_naissance': ['15/03/1985', '22/07/1990'],
            'genre': ['M', 'F'],
            'adresse': ['123 Rue de la Paix', '456 Avenue des Fleurs'],
            'ville': ['Cayenne', 'Kourou'],
            'code_postal': ['97300', '97310'],
            'profession': ['Ingénieur', 'Professeure'],
            'statut': ['actif', 'actif'],
            'date_arrivee': ['01/01/2020', '15/06/2021'],
            'baptise': ['oui', 'non'],
            'date_bapteme': ['15/02/2020', ''],  # Valeur vide pour le second
            'situation_familiale': ['marié', 'célibataire'],
            'notes': ['Membre actif', 'Nouvelle convertie']
        }
    elif import_type == 'children':
        sample_data = {
            'prenom': ['Paul', 'Sophie'],
            'nom': ['Dupont', 'Martin'],
            'date_naissance': ['10/05/2015', '03/12/2013'],
            'genre': ['M', 'F'],
            'nom_pere': ['Jean Dupont', 'Pierre Martin'],
            'telephone_pere': ['0694123456', '0694654321'],
            'email_pere': ['jean.dupont@email.com', 'pierre.martin@email.com'],
            'nom_mere': ['Anne Dupont', 'Marie Martin'],
            'telephone_mere': ['0694123457', '0694654322'],
            'email_mere': ['anne.dupont@email.com', 'marie.martin@email.com'],
            'contact_urgence': ['Grand-mère Dupont', 'Oncle Martin'],
            'telephone_urgence': ['0694123458', '0694654323'],
            'allergies': ['Aucune', 'Arachides'],
            'notes_medicales': ['', 'Asthme léger'],  # Valeur vide pour le premier
            'besoin_transport': ['oui', 'non'],
            'adresse_ramassage': ['123 Rue de la Paix', ''],  # Valeur vide pour le second
            'notes': ['Enfant calme', 'Très active']
        }
    
    return pd.DataFrame(sample_data)


def export_members_to_excel():
    """Exporte tous les membres actifs vers un fichier Excel."""
    from apps.members.models import Member
    
    # Le modèle Member utilise 'status' au lieu de 'is_active'
    members = Member.objects.filter(status=Member.Status.ACTIF).order_by('last_name', 'first_name')
    
    export_data = []
    for member in members:
        export_data.append({
            'prenom': member.first_name,
            'nom': member.last_name,
            'email': member.email or '',
            'telephone': member.phone or '',
            'date_naissance': member.date_of_birth.strftime('%d/%m/%Y') if member.date_of_birth else '',
            'genre': member.gender or '',
            'adresse': member.address or '',
            'ville': member.city or '',
            'code_postal': member.postal_code or '',
            'profession': member.profession or '',
            'statut': member.status or '',
            'date_arrivee': member.date_joined.strftime('%d/%m/%Y') if member.date_joined else '',
            'baptise': 'oui' if member.is_baptized else 'non',
            'date_bapteme': member.baptism_date.strftime('%d/%m/%Y') if member.baptism_date else '',
            'situation_familiale': member.marital_status or '',
            'notes': member.notes or ''
        })
    
    return pd.DataFrame(export_data)


def export_children_to_excel():
    """Exporte tous les enfants actifs vers un fichier Excel."""
    
    children = Child.objects.filter(is_active=True).select_related('bible_class').order_by('last_name', 'first_name')
    
    export_data = []
    for child in children:
        export_data.append({
            'prenom': child.first_name,
            'nom': child.last_name,
            'date_naissance': child.date_of_birth.strftime('%d/%m/%Y') if child.date_of_birth else '',
            'genre': child.gender or '',
            'classe': str(child.bible_class) if child.bible_class else '',
            'nom_pere': child.father_name or '',
            'telephone_pere': child.father_phone or '',
            'email_pere': child.father_email or '',
            'nom_mere': child.mother_name or '',
            'telephone_mere': child.mother_phone or '',
            'email_mere': child.mother_email or '',
            'contact_urgence': child.emergency_contact or '',
            'telephone_urgence': child.emergency_phone or '',
            'allergies': child.allergies or '',
            'notes_medicales': child.medical_notes or '',
            'besoin_transport': 'oui' if child.needs_transport else 'non',
            'adresse_ramassage': child.pickup_address or '',
            'notes': child.notes or ''
        })
    
    return pd.DataFrame(export_data)


class ExportHistoryService:
    """Service pour gérer l'historique des exports."""
    
    @staticmethod
    def log_export(user, export_type, export_name, file_size=None, record_count=None):
        """Enregistre un export dans l'historique."""
        from .models import ImportLog
        
        # Réutiliser le modèle ImportLog pour les exports aussi
        log = ImportLog.objects.create(
            import_type='export',  # Nouveau type
            file_name=f'export_{export_type}_{timezone.now().strftime("%Y%m%d_%H%M")}',
            imported_by=user,
            status=ImportLog.Status.SUCCESS,
            total_rows=record_count or 0,
            success_rows=record_count or 0,
            error_rows=0,
            completed_at=timezone.now(),
            success_log=f'Export {export_name} réalisé avec succès'
        )
        
        return log
    
    @staticmethod
    def get_export_history(user=None, limit=10):
        """Récupère l'historique des exports."""
        from .models import ImportLog
        
        queryset = ImportLog.objects.filter(import_type='export').order_by('-started_at')
        
        if user and not user.is_superuser:
            queryset = queryset.filter(imported_by=user)
        
        return queryset[:limit]


class GenericExportService:
    """Service générique pour créer des exports Excel."""
    
    @staticmethod
    def create_excel_response(data, filename, sheet_name='Données', info_data=None):
        """Crée une réponse HTTP avec un fichier Excel."""
        import io
        import pandas as pd
        from django.http import HttpResponse
        
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Feuille principale avec les données
            if isinstance(data, pd.DataFrame):
                data.to_excel(writer, index=False, sheet_name=sheet_name)
            else:
                df = pd.DataFrame(data)
                df.to_excel(writer, index=False, sheet_name=sheet_name)
            
            # Feuille d'informations si fournie
            if info_data:
                info_df = pd.DataFrame(info_data)
                info_df.to_excel(writer, index=False, sheet_name='Informations')
        
        output.seek(0)
        
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
    
    @staticmethod
    def export_groups():
        """Exporte les groupes de l'église."""
        from apps.groups.models import Group
        
        groups = Group.objects.filter(is_active=True).prefetch_related('members')
        
        export_data = []
        for group in groups:
            export_data.append({
                'nom': group.name,
                'description': group.description or '',
                'responsable': group.leader.get_full_name() if group.leader else '',
                'email_responsable': group.leader.email if group.leader else '',
                'telephone_responsable': getattr(group.leader, 'phone', '') if group.leader else '',
                'nombre_membres': group.members.count(),
                'lieu_reunion': getattr(group, 'meeting_location', '') or '',
                'horaire': getattr(group, 'meeting_time', '') or '',
                'frequence': getattr(group, 'meeting_frequency', '') or '',
                'actif': 'Oui' if group.is_active else 'Non',
                'date_creation': group.created_at.strftime('%d/%m/%Y') if hasattr(group, 'created_at') and group.created_at else '',
                'notes': getattr(group, 'notes', '') or ''
            })
        
        return pd.DataFrame(export_data)
    
    @staticmethod
    def export_inventory():
        """Exporte l'inventaire des équipements."""
        from apps.inventory.models import Equipment
        
        equipment = Equipment.objects.select_related('category').order_by('category__name', 'name')
        
        export_data = []
        for item in equipment:
            export_data.append({
                'nom': item.name,
                'categorie': item.category.name if item.category else '',
                'description': item.description or '',
                'numero_serie': getattr(item, 'serial_number', '') or '',
                'etat': item.get_condition_display() if hasattr(item, 'get_condition_display') else getattr(item, 'condition', '') or '',
                'localisation': getattr(item, 'location', '') or '',
                'date_achat': item.purchase_date.strftime('%d/%m/%Y') if hasattr(item, 'purchase_date') and item.purchase_date else '',
                'prix_achat': getattr(item, 'purchase_price', '') or '',
                'garantie_jusqu': item.warranty_until.strftime('%d/%m/%Y') if hasattr(item, 'warranty_until') and item.warranty_until else '',
                'responsable': getattr(item, 'responsible_person', '') or '',
                'notes': getattr(item, 'notes', '') or ''
            })
        
        return pd.DataFrame(export_data)
    
    @staticmethod
    def export_transport():
        """Exporte les données de transport."""
        from apps.transport.models import DriverProfile, TransportRequest
        
        # Export des chauffeurs
        drivers = DriverProfile.objects.filter(is_available=True).select_related('user')
        
        export_data = []
        for driver in drivers:
            export_data.append({
                'nom': driver.user.get_full_name(),
                'telephone': getattr(driver, 'phone', '') or '',
                'email': driver.user.email,
                'vehicule': getattr(driver, 'vehicle_model', '') or '',
                'type_vehicule': getattr(driver, 'vehicle_type', '') or '',
                'plaque': getattr(driver, 'license_plate', '') or '',
                'capacite': getattr(driver, 'capacity', '') or '',
                'zone': getattr(driver, 'zone', '') or '',
                'disponible_dimanche': 'Oui' if getattr(driver, 'available_sunday', False) else 'Non',
                'disponible_semaine': 'Oui' if getattr(driver, 'available_week', False) else 'Non',
                'actif': 'Oui' if getattr(driver, 'is_available', True) else 'Non',
                'notes': getattr(driver, 'notes', '') or ''
            })
        
        return pd.DataFrame(export_data)
    
    @staticmethod
    def export_communication_logs():
        """Exporte les logs de communication."""
        from apps.communication.models import EmailLog, SMSLog
        from datetime import datetime, timedelta
        
        # Logs des 3 derniers mois seulement
        three_months_ago = datetime.now() - timedelta(days=90)
        
        export_data = []
        
        # Emails
        emails = EmailLog.objects.filter(sent_at__gte=three_months_ago).order_by('-sent_at')
        for email in emails:
            export_data.append({
                'type': 'Email',
                'destinataire': email.recipient_email,
                'sujet': email.subject,
                'statut': email.get_status_display() if hasattr(email, 'get_status_display') else email.status,
                'date_envoi': email.sent_at.strftime('%d/%m/%Y %H:%M') if email.sent_at else '',
                'erreur': getattr(email, 'error_message', '') or '',
                'expediteur': getattr(email, 'sender', {}).get('username', '') if hasattr(email, 'sender') else ''
            })
        
        # SMS (si disponible)
        try:
            sms_logs = SMSLog.objects.filter(sent_at__gte=three_months_ago).order_by('-sent_at')
            for sms in sms_logs:
                export_data.append({
                    'type': 'SMS',
                    'destinataire': sms.recipient_phone,
                    'sujet': sms.message[:50] + '...' if len(sms.message) > 50 else sms.message,
                    'statut': sms.get_status_display() if hasattr(sms, 'get_status_display') else sms.status,
                    'date_envoi': sms.sent_at.strftime('%d/%m/%Y %H:%M') if sms.sent_at else '',
                    'erreur': getattr(sms, 'error_message', '') or '',
                    'expediteur': getattr(sms, 'sender', {}).get('username', '') if hasattr(sms, 'sender') else ''
                })
        except:
            pass  # SMSLog peut ne pas exister
        
        return pd.DataFrame(export_data)