/**
 * Système de validation JavaScript en temps réel pour les formulaires
 */

class FormValidator {
    constructor(formSelector) {
        this.form = document.querySelector(formSelector);
        if (!this.form) return;
        
        this.init();
    }
    
    init() {
        // Ajouter les événements de validation en temps réel
        this.form.addEventListener('submit', (e) => this.handleSubmit(e));
        
        // Validation en temps réel sur les champs
        const inputs = this.form.querySelectorAll('input, textarea, select');
        inputs.forEach(input => {
            input.addEventListener('blur', (e) => this.validateField(e.target));
            input.addEventListener('input', (e) => this.clearFieldError(e.target));
            
            // Validation spéciale pour certains types
            if (input.type === 'email') {
                input.addEventListener('input', (e) => this.validateEmail(e.target));
            } else if (input.type === 'tel') {
                input.addEventListener('input', (e) => this.validatePhone(e.target));
            } else if (input.type === 'number') {
                input.addEventListener('input', (e) => this.validateNumber(e.target));
            }
        });
    }
    
    handleSubmit(event) {
        let isValid = true;
        
        // Valider tous les champs
        const inputs = this.form.querySelectorAll('input, textarea, select');
        inputs.forEach(input => {
            if (!this.validateField(input)) {
                isValid = false;
            }
        });
        
        // Empêcher la soumission si invalide
        if (!isValid) {
            event.preventDefault();
            this.showFormError('Veuillez corriger les erreurs avant de continuer.');
            
            // Faire défiler vers la première erreur
            const firstError = this.form.querySelector('.is-invalid');
            if (firstError) {
                firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
                firstError.focus();
            }
        }
    }
    
    validateField(field) {
        this.clearFieldError(field);
        
        // Vérifier si le champ est requis
        if (field.hasAttribute('required') && !field.value.trim()) {
            this.showFieldError(field, 'Ce champ est obligatoire.');
            return false;
        }
        
        // Validation spécifique par type
        if (field.value.trim()) {
            switch (field.type) {
                case 'email':
                    return this.validateEmail(field);
                case 'tel':
                    return this.validatePhone(field);
                case 'url':
                    return this.validateUrl(field);
                case 'number':
                    return this.validateNumber(field);
                case 'date':
                    return this.validateDate(field);
                case 'time':
                    return this.validateTime(field);
                default:
                    return this.validateText(field);
            }
        }
        
        return true;
    }
    
    validateEmail(field) {
        const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
        if (!emailRegex.test(field.value)) {
            this.showFieldError(field, 'Veuillez saisir une adresse email valide.');
            return false;
        }
        return true;
    }
    
    validatePhone(field) {
        // Accepter différents formats de téléphone français
        const phoneRegex = /^(?:(?:\+33|0)[1-9](?:[0-9]{8}))$/;
        const cleanPhone = field.value.replace(/[\s\-\(\)\.]/g, '');
        
        if (!phoneRegex.test(cleanPhone)) {
            this.showFieldError(field, 'Veuillez saisir un numéro de téléphone valide (ex: 0694123456).');
            return false;
        }
        return true;
    }
    
    validateUrl(field) {
        try {
            new URL(field.value);
            return true;
        } catch {
            this.showFieldError(field, 'Veuillez saisir une URL valide (ex: https://exemple.com).');
            return false;
        }
    }
    
    validateNumber(field) {
        const value = parseFloat(field.value);
        
        if (isNaN(value)) {
            this.showFieldError(field, 'Veuillez saisir un nombre valide.');
            return false;
        }
        
        // Vérifier min/max
        const min = field.getAttribute('min');
        const max = field.getAttribute('max');
        
        if (min !== null && value < parseFloat(min)) {
            this.showFieldError(field, `La valeur doit être supérieure ou égale à ${min}.`);
            return false;
        }
        
        if (max !== null && value > parseFloat(max)) {
            this.showFieldError(field, `La valeur doit être inférieure ou égale à ${max}.`);
            return false;
        }
        
        return true;
    }
    
    validateDate(field) {
        const date = new Date(field.value);
        if (isNaN(date.getTime())) {
            this.showFieldError(field, 'Veuillez saisir une date valide.');
            return false;
        }
        
        // Vérifier si la date n'est pas trop ancienne (plus de 150 ans)
        const minDate = new Date();
        minDate.setFullYear(minDate.getFullYear() - 150);
        
        if (date < minDate) {
            this.showFieldError(field, 'Cette date semble trop ancienne.');
            return false;
        }
        
        return true;
    }
    
    validateTime(field) {
        const timeRegex = /^([01]?[0-9]|2[0-3]):[0-5][0-9]$/;
        if (!timeRegex.test(field.value)) {
            this.showFieldError(field, 'Veuillez saisir une heure valide (HH:MM).');
            return false;
        }
        return true;
    }
    
    validateText(field) {
        const value = field.value.trim();
        
        // Vérifier la longueur minimale
        const minLength = field.getAttribute('minlength');
        if (minLength && value.length < parseInt(minLength)) {
            this.showFieldError(field, `Ce champ doit contenir au moins ${minLength} caractères.`);
            return false;
        }
        
        // Vérifier la longueur maximale
        const maxLength = field.getAttribute('maxlength');
        if (maxLength && value.length > parseInt(maxLength)) {
            this.showFieldError(field, `Ce champ ne peut pas contenir plus de ${maxLength} caractères.`);
            return false;
        }
        
        // Vérifier le pattern si défini
        const pattern = field.getAttribute('pattern');
        if (pattern) {
            const regex = new RegExp(pattern);
            if (!regex.test(value)) {
                const title = field.getAttribute('title') || 'Format invalide.';
                this.showFieldError(field, title);
                return false;
            }
        }
        
        return true;
    }
    
    showFieldError(field, message) {
        field.classList.add('is-invalid');
        field.classList.remove('is-valid');
        
        // Supprimer l'ancien message d'erreur
        const existingError = field.parentNode.querySelector('.invalid-feedback');
        if (existingError) {
            existingError.remove();
        }
        
        // Ajouter le nouveau message d'erreur
        const errorDiv = document.createElement('div');
        errorDiv.className = 'invalid-feedback';
        errorDiv.textContent = message;
        
        // Insérer après le champ ou après son wrapper
        const wrapper = field.closest('.input-group') || field;
        wrapper.parentNode.insertBefore(errorDiv, wrapper.nextSibling);
    }
    
    clearFieldError(field) {
        field.classList.remove('is-invalid');
        
        // Supprimer le message d'erreur
        const errorDiv = field.parentNode.querySelector('.invalid-feedback');
        if (errorDiv) {
            errorDiv.remove();
        }
        
        // Ajouter la classe valid si le champ a une valeur
        if (field.value.trim()) {
            field.classList.add('is-valid');
        } else {
            field.classList.remove('is-valid');
        }
    }
    
    showFormError(message) {
        // Supprimer l'ancien message d'erreur global
        const existingAlert = this.form.querySelector('.alert-danger');
        if (existingAlert) {
            existingAlert.remove();
        }
        
        // Créer le nouveau message d'erreur
        const alertDiv = document.createElement('div');
        alertDiv.className = 'alert alert-danger alert-dismissible fade show';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        // Insérer au début du formulaire
        this.form.insertBefore(alertDiv, this.form.firstChild);
    }
}

// Validation spéciale pour les mots de passe
class PasswordValidator {
    constructor(passwordField, confirmField = null) {
        this.passwordField = document.querySelector(passwordField);
        this.confirmField = confirmField ? document.querySelector(confirmField) : null;
        
        if (this.passwordField) {
            this.init();
        }
    }
    
    init() {
        this.passwordField.addEventListener('input', () => this.validatePassword());
        
        if (this.confirmField) {
            this.confirmField.addEventListener('input', () => this.validatePasswordMatch());
        }
    }
    
    validatePassword() {
        const password = this.passwordField.value;
        const requirements = {
            length: password.length >= 8,
            uppercase: /[A-Z]/.test(password),
            lowercase: /[a-z]/.test(password),
            number: /\d/.test(password),
            special: /[!@#$%^&*(),.?":{}|<>]/.test(password)
        };
        
        const messages = [];
        if (!requirements.length) messages.push('Au moins 8 caractères');
        if (!requirements.uppercase) messages.push('Une majuscule');
        if (!requirements.lowercase) messages.push('Une minuscule');
        if (!requirements.number) messages.push('Un chiffre');
        
        if (messages.length > 0) {
            this.showPasswordError(`Le mot de passe doit contenir : ${messages.join(', ')}`);
            return false;
        } else {
            this.clearPasswordError();
            return true;
        }
    }
    
    validatePasswordMatch() {
        if (this.passwordField.value !== this.confirmField.value) {
            this.showConfirmError('Les mots de passe ne correspondent pas.');
            return false;
        } else {
            this.clearConfirmError();
            return true;
        }
    }
    
    showPasswordError(message) {
        this.passwordField.classList.add('is-invalid');
        this.showError(this.passwordField, message);
    }
    
    showConfirmError(message) {
        this.confirmField.classList.add('is-invalid');
        this.showError(this.confirmField, message);
    }
    
    clearPasswordError() {
        this.passwordField.classList.remove('is-invalid');
        this.clearError(this.passwordField);
    }
    
    clearConfirmError() {
        this.confirmField.classList.remove('is-invalid');
        this.clearError(this.confirmField);
    }
    
    showError(field, message) {
        const existingError = field.parentNode.querySelector('.invalid-feedback');
        if (existingError) {
            existingError.textContent = message;
        } else {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'invalid-feedback';
            errorDiv.textContent = message;
            field.parentNode.appendChild(errorDiv);
        }
    }
    
    clearError(field) {
        const errorDiv = field.parentNode.querySelector('.invalid-feedback');
        if (errorDiv) {
            errorDiv.remove();
        }
    }
}

// Initialisation automatique
document.addEventListener('DOMContentLoaded', function() {
    // Initialiser la validation pour tous les formulaires
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        if (!form.hasAttribute('novalidate')) {
            new FormValidator(`#${form.id}` || 'form');
        }
    });
    
    // Initialiser la validation des mots de passe
    const passwordFields = document.querySelectorAll('input[type="password"]');
    passwordFields.forEach(field => {
        if (field.name.includes('password1') || field.name.includes('new_password1')) {
            const confirmField = document.querySelector(`input[name="${field.name.replace('1', '2')}"]`);
            new PasswordValidator(`#${field.id}`, confirmField ? `#${confirmField.id}` : null);
        }
    });
});

// Utilitaires pour validation personnalisée
window.FormValidation = {
    validateField: function(fieldSelector) {
        const field = document.querySelector(fieldSelector);
        if (field && field.closest('form')) {
            const form = field.closest('form');
            const validator = new FormValidator(`#${form.id}`);
            return validator.validateField(field);
        }
        return false;
    },
    
    showError: function(fieldSelector, message) {
        const field = document.querySelector(fieldSelector);
        if (field) {
            const validator = new FormValidator();
            validator.showFieldError(field, message);
        }
    },
    
    clearError: function(fieldSelector) {
        const field = document.querySelector(fieldSelector);
        if (field) {
            const validator = new FormValidator();
            validator.clearFieldError(field);
        }
    }
};