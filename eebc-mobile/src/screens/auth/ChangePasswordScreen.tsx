/**
 * Change Password Screen - Full implementation
 * Requirements: 1.5, 10.3
 * - Password change form with validation
 * - Handles mandatory password change on first login
 * - Password strength validation
 */

import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { AuthStackParamList } from '../../types/navigation';
import { useAuthStore } from '../../stores/authStore';

type Props = NativeStackScreenProps<AuthStackParamList, 'ChangePassword'>;

interface FormErrors {
  oldPassword?: string;
  newPassword?: string;
  confirmPassword?: string;
}

interface PasswordStrength {
  score: number;
  label: string;
  color: string;
}

export const ChangePasswordScreen: React.FC<Props> = ({ route, navigation }) => {
  const { mustChange } = route.params;
  const { changePassword, isLoading, error, clearError, logout } = useAuthStore();

  // Form state
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showOldPassword, setShowOldPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [formErrors, setFormErrors] = useState<FormErrors>({});


  /**
   * Calculate password strength
   */
  const getPasswordStrength = useCallback((password: string): PasswordStrength => {
    let score = 0;

    if (password.length >= 8) score++;
    if (password.length >= 12) score++;
    if (/[a-z]/.test(password)) score++;
    if (/[A-Z]/.test(password)) score++;
    if (/[0-9]/.test(password)) score++;
    if (/[^a-zA-Z0-9]/.test(password)) score++;

    if (score <= 2) {
      return { score, label: 'Faible', color: '#ef4444' };
    } else if (score <= 4) {
      return { score, label: 'Moyen', color: '#f59e0b' };
    } else {
      return { score, label: 'Fort', color: '#22c55e' };
    }
  }, []);

  const passwordStrength = getPasswordStrength(newPassword);

  /**
   * Validate form inputs
   */
  const validateForm = useCallback((): boolean => {
    const errors: FormErrors = {};

    if (!oldPassword) {
      errors.oldPassword = 'L\'ancien mot de passe est requis';
    }

    if (!newPassword) {
      errors.newPassword = 'Le nouveau mot de passe est requis';
    } else if (newPassword.length < 8) {
      errors.newPassword = 'Le mot de passe doit contenir au moins 8 caractères';
    } else if (newPassword === oldPassword) {
      errors.newPassword = 'Le nouveau mot de passe doit être différent de l\'ancien';
    }

    if (!confirmPassword) {
      errors.confirmPassword = 'Veuillez confirmer le mot de passe';
    } else if (confirmPassword !== newPassword) {
      errors.confirmPassword = 'Les mots de passe ne correspondent pas';
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  }, [oldPassword, newPassword, confirmPassword]);

  /**
   * Handle password change submission
   * Requirements: 1.5, 10.3
   */
  const handleChangePassword = async () => {
    if (!validateForm()) {
      return;
    }

    try {
      await changePassword(oldPassword, newPassword);
      
      Alert.alert(
        'Succès',
        'Votre mot de passe a été changé avec succès.',
        [
          {
            text: 'OK',
            onPress: () => {
              if (mustChange) {
                // If it was a mandatory change, navigate to login
                navigation.navigate('Login');
              } else {
                // Otherwise, go back
                navigation.goBack();
              }
            },
          },
        ]
      );
    } catch (err) {
      // Error is handled by the store
    }
  };


  /**
   * Handle cancel/logout for mandatory password change
   */
  const handleCancel = () => {
    if (mustChange) {
      Alert.alert(
        'Déconnexion',
        'Vous devez changer votre mot de passe pour continuer. Voulez-vous vous déconnecter ?',
        [
          { text: 'Non', style: 'cancel' },
          {
            text: 'Oui, déconnecter',
            style: 'destructive',
            onPress: async () => {
              await logout();
            },
          },
        ]
      );
    } else {
      navigation.goBack();
    }
  };

  /**
   * Clear error when inputs change
   */
  React.useEffect(() => {
    if (error) {
      clearError();
    }
  }, [oldPassword, newPassword, confirmPassword]);

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
      >
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.title}>Changer le mot de passe</Text>
          {mustChange && (
            <View style={styles.warningContainer}>
              <Text style={styles.warningText}>
                ⚠️ Vous devez changer votre mot de passe pour continuer à utiliser l'application.
              </Text>
            </View>
          )}
        </View>

        {/* Form */}
        <View style={styles.form}>
          {/* Error Message */}
          {error && (
            <View style={styles.errorContainer}>
              <Text style={styles.errorText}>{error}</Text>
            </View>
          )}

          {/* Old Password Input */}
          <View style={styles.inputContainer}>
            <Text style={styles.label}>Ancien mot de passe</Text>
            <View style={styles.passwordContainer}>
              <TextInput
                style={[
                  styles.input,
                  styles.passwordInput,
                  formErrors.oldPassword && styles.inputError,
                ]}
                placeholder="Entrez votre ancien mot de passe"
                placeholderTextColor="#999"
                value={oldPassword}
                onChangeText={setOldPassword}
                secureTextEntry={!showOldPassword}
                autoCapitalize="none"
                autoCorrect={false}
                editable={!isLoading}
                testID="old-password-input"
              />
              <TouchableOpacity
                style={styles.showPasswordButton}
                onPress={() => setShowOldPassword(!showOldPassword)}
                disabled={isLoading}
              >
                <Text style={styles.showPasswordText}>
                  {showOldPassword ? 'Masquer' : 'Afficher'}
                </Text>
              </TouchableOpacity>
            </View>
            {formErrors.oldPassword && (
              <Text style={styles.fieldError}>{formErrors.oldPassword}</Text>
            )}
          </View>


          {/* New Password Input */}
          <View style={styles.inputContainer}>
            <Text style={styles.label}>Nouveau mot de passe</Text>
            <View style={styles.passwordContainer}>
              <TextInput
                style={[
                  styles.input,
                  styles.passwordInput,
                  formErrors.newPassword && styles.inputError,
                ]}
                placeholder="Entrez votre nouveau mot de passe"
                placeholderTextColor="#999"
                value={newPassword}
                onChangeText={setNewPassword}
                secureTextEntry={!showNewPassword}
                autoCapitalize="none"
                autoCorrect={false}
                editable={!isLoading}
                testID="new-password-input"
              />
              <TouchableOpacity
                style={styles.showPasswordButton}
                onPress={() => setShowNewPassword(!showNewPassword)}
                disabled={isLoading}
              >
                <Text style={styles.showPasswordText}>
                  {showNewPassword ? 'Masquer' : 'Afficher'}
                </Text>
              </TouchableOpacity>
            </View>
            {formErrors.newPassword && (
              <Text style={styles.fieldError}>{formErrors.newPassword}</Text>
            )}

            {/* Password Strength Indicator */}
            {newPassword.length > 0 && (
              <View style={styles.strengthContainer}>
                <View style={styles.strengthBar}>
                  <View
                    style={[
                      styles.strengthFill,
                      {
                        width: `${(passwordStrength.score / 6) * 100}%`,
                        backgroundColor: passwordStrength.color,
                      },
                    ]}
                  />
                </View>
                <Text style={[styles.strengthLabel, { color: passwordStrength.color }]}>
                  {passwordStrength.label}
                </Text>
              </View>
            )}

            {/* Password Requirements */}
            <View style={styles.requirementsContainer}>
              <Text style={styles.requirementsTitle}>Le mot de passe doit contenir :</Text>
              <Text style={[styles.requirement, newPassword.length >= 8 && styles.requirementMet]}>
                • Au moins 8 caractères
              </Text>
              <Text style={[styles.requirement, /[A-Z]/.test(newPassword) && styles.requirementMet]}>
                • Une lettre majuscule
              </Text>
              <Text style={[styles.requirement, /[a-z]/.test(newPassword) && styles.requirementMet]}>
                • Une lettre minuscule
              </Text>
              <Text style={[styles.requirement, /[0-9]/.test(newPassword) && styles.requirementMet]}>
                • Un chiffre
              </Text>
              <Text style={[styles.requirement, /[^a-zA-Z0-9]/.test(newPassword) && styles.requirementMet]}>
                • Un caractère spécial
              </Text>
            </View>
          </View>


          {/* Confirm Password Input */}
          <View style={styles.inputContainer}>
            <Text style={styles.label}>Confirmer le mot de passe</Text>
            <View style={styles.passwordContainer}>
              <TextInput
                style={[
                  styles.input,
                  styles.passwordInput,
                  formErrors.confirmPassword && styles.inputError,
                ]}
                placeholder="Confirmez votre nouveau mot de passe"
                placeholderTextColor="#999"
                value={confirmPassword}
                onChangeText={setConfirmPassword}
                secureTextEntry={!showConfirmPassword}
                autoCapitalize="none"
                autoCorrect={false}
                editable={!isLoading}
                testID="confirm-password-input"
              />
              <TouchableOpacity
                style={styles.showPasswordButton}
                onPress={() => setShowConfirmPassword(!showConfirmPassword)}
                disabled={isLoading}
              >
                <Text style={styles.showPasswordText}>
                  {showConfirmPassword ? 'Masquer' : 'Afficher'}
                </Text>
              </TouchableOpacity>
            </View>
            {formErrors.confirmPassword && (
              <Text style={styles.fieldError}>{formErrors.confirmPassword}</Text>
            )}
            {confirmPassword.length > 0 && confirmPassword === newPassword && (
              <Text style={styles.matchSuccess}>✓ Les mots de passe correspondent</Text>
            )}
          </View>

          {/* Submit Button */}
          <TouchableOpacity
            style={[styles.submitButton, isLoading && styles.submitButtonDisabled]}
            onPress={handleChangePassword}
            disabled={isLoading}
            testID="submit-button"
          >
            {isLoading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.submitButtonText}>Changer le mot de passe</Text>
            )}
          </TouchableOpacity>

          {/* Cancel Button */}
          <TouchableOpacity
            style={styles.cancelButton}
            onPress={handleCancel}
            disabled={isLoading}
            testID="cancel-button"
          >
            <Text style={styles.cancelButtonText}>
              {mustChange ? 'Se déconnecter' : 'Annuler'}
            </Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
};


const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f6fa',
  },
  scrollContent: {
    flexGrow: 1,
    padding: 24,
  },
  header: {
    marginBottom: 24,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#2c3e50',
    marginBottom: 12,
  },
  warningContainer: {
    backgroundColor: '#fef3c7',
    borderRadius: 8,
    padding: 12,
    borderLeftWidth: 4,
    borderLeftColor: '#f59e0b',
  },
  warningText: {
    color: '#92400e',
    fontSize: 14,
    lineHeight: 20,
  },
  form: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 4,
  },
  errorContainer: {
    backgroundColor: '#fee2e2',
    borderRadius: 8,
    padding: 12,
    marginBottom: 16,
    borderLeftWidth: 4,
    borderLeftColor: '#ef4444',
  },
  errorText: {
    color: '#dc2626',
    fontSize: 14,
  },
  inputContainer: {
    marginBottom: 20,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: '#374151',
    marginBottom: 8,
  },
  input: {
    backgroundColor: '#f9fafb',
    borderWidth: 1,
    borderColor: '#e5e7eb',
    borderRadius: 10,
    padding: 14,
    fontSize: 16,
    color: '#1f2937',
  },
  inputError: {
    borderColor: '#ef4444',
    backgroundColor: '#fef2f2',
  },
  passwordContainer: {
    position: 'relative',
  },
  passwordInput: {
    paddingRight: 80,
  },
  showPasswordButton: {
    position: 'absolute',
    right: 14,
    top: 14,
  },
  showPasswordText: {
    color: '#3498db',
    fontSize: 14,
    fontWeight: '500',
  },
  fieldError: {
    color: '#ef4444',
    fontSize: 12,
    marginTop: 4,
  },
  strengthContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 8,
  },
  strengthBar: {
    flex: 1,
    height: 4,
    backgroundColor: '#e5e7eb',
    borderRadius: 2,
    marginRight: 8,
    overflow: 'hidden',
  },
  strengthFill: {
    height: '100%',
    borderRadius: 2,
  },
  strengthLabel: {
    fontSize: 12,
    fontWeight: '500',
    width: 50,
  },
  requirementsContainer: {
    marginTop: 12,
    padding: 12,
    backgroundColor: '#f9fafb',
    borderRadius: 8,
  },
  requirementsTitle: {
    fontSize: 12,
    fontWeight: '600',
    color: '#6b7280',
    marginBottom: 8,
  },
  requirement: {
    fontSize: 12,
    color: '#9ca3af',
    marginBottom: 4,
  },
  requirementMet: {
    color: '#22c55e',
  },
  matchSuccess: {
    color: '#22c55e',
    fontSize: 12,
    marginTop: 4,
  },
  submitButton: {
    backgroundColor: '#3498db',
    borderRadius: 10,
    padding: 16,
    alignItems: 'center',
    marginTop: 8,
  },
  submitButtonDisabled: {
    backgroundColor: '#93c5fd',
  },
  submitButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  cancelButton: {
    marginTop: 12,
    padding: 14,
    alignItems: 'center',
  },
  cancelButtonText: {
    color: '#6b7280',
    fontSize: 14,
    fontWeight: '500',
  },
});
