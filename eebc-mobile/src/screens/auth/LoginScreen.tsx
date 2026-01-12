/**
 * Login Screen - Full implementation
 * Requirements: 1.1, 1.7, 1.8
 * - Login form with username and password fields
 * - Form validation
 * - Biometric authentication option
 * - Account lockout handling after 5 failed attempts
 */

import React, { useState, useEffect, useCallback } from 'react';
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
import * as LocalAuthentication from 'expo-local-authentication';
import { useAuthStore } from '../../stores/authStore';
import { authService } from '../../services/AuthService';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { AuthStackParamList } from '../../types/navigation';
import { useNavigation } from '@react-navigation/native';

type LoginScreenNavigationProp = NativeStackNavigationProp<AuthStackParamList, 'Login'>;

interface FormErrors {
  username?: string;
  password?: string;
}

export const LoginScreen: React.FC = () => {
  const navigation = useNavigation<LoginScreenNavigationProp>();
  const { login, loginWithBiometric, isLoading, error, clearError, isAuthenticated, mustChangePassword } = useAuthStore();

  // Form state
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [formErrors, setFormErrors] = useState<FormErrors>({});

  // Biometric state
  const [biometricAvailable, setBiometricAvailable] = useState(false);
  const [biometricEnabled, setBiometricEnabled] = useState(false);
  const [biometricType, setBiometricType] = useState<string>('');

  // Check biometric availability on mount
  useEffect(() => {
    checkBiometricAvailability();
  }, []);


  // Handle navigation after successful login
  useEffect(() => {
    if (isAuthenticated && mustChangePassword) {
      navigation.navigate('ChangePassword', { mustChange: true });
    }
  }, [isAuthenticated, mustChangePassword, navigation]);

  // Clear error when inputs change
  useEffect(() => {
    if (error) {
      clearError();
    }
  }, [username, password]);

  /**
   * Check if biometric authentication is available
   * Requirements: 1.7
   */
  const checkBiometricAvailability = async () => {
    try {
      const hasHardware = await LocalAuthentication.hasHardwareAsync();
      const isEnrolled = await LocalAuthentication.isEnrolledAsync();
      const supportedTypes = await LocalAuthentication.supportedAuthenticationTypesAsync();

      if (hasHardware && isEnrolled) {
        setBiometricAvailable(true);
        
        // Determine biometric type for display
        if (supportedTypes.includes(LocalAuthentication.AuthenticationType.FACIAL_RECOGNITION)) {
          setBiometricType('Face ID');
        } else if (supportedTypes.includes(LocalAuthentication.AuthenticationType.FINGERPRINT)) {
          setBiometricType('Empreinte digitale');
        } else {
          setBiometricType('Biométrique');
        }

        // Check if biometric is enabled for this app
        const enabled = await authService.isBiometricEnabled();
        setBiometricEnabled(enabled);
      }
    } catch (err) {
      console.log('Biometric check error:', err);
    }
  };

  /**
   * Validate form inputs
   */
  const validateForm = useCallback((): boolean => {
    const errors: FormErrors = {};

    if (!username.trim()) {
      errors.username = 'Le nom d\'utilisateur est requis';
    }

    if (!password) {
      errors.password = 'Le mot de passe est requis';
    } else if (password.length < 4) {
      errors.password = 'Le mot de passe doit contenir au moins 4 caractères';
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  }, [username, password]);

  /**
   * Handle login form submission
   * Requirements: 1.1, 1.8
   */
  const handleLogin = async () => {
    if (!validateForm()) {
      return;
    }

    const result = await login(username.trim(), password);

    if (result.success) {
      // If biometric is available but not enabled, offer to enable it
      if (biometricAvailable && !biometricEnabled) {
        Alert.alert(
          'Activer l\'authentification biométrique ?',
          `Voulez-vous utiliser ${biometricType} pour vous connecter plus rapidement ?`,
          [
            { text: 'Non merci', style: 'cancel' },
            {
              text: 'Activer',
              onPress: async () => {
                try {
                  await authService.enableBiometric();
                  setBiometricEnabled(true);
                } catch (err) {
                  console.log('Failed to enable biometric:', err);
                }
              },
            },
          ]
        );
      }
    }
  };


  /**
   * Handle biometric authentication
   * Requirements: 1.7
   */
  const handleBiometricLogin = async () => {
    const result = await loginWithBiometric();

    if (!result.success && result.error) {
      Alert.alert('Erreur', result.error);
    }
  };

  /**
   * Render the login form
   */
  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
      >
        {/* Logo and Title */}
        <View style={styles.header}>
          <View style={styles.logoContainer}>
            <Text style={styles.logoText}>EEBC</Text>
          </View>
          <Text style={styles.title}>Bienvenue</Text>
          <Text style={styles.subtitle}>
            Église Évangélique Baptiste de Cabassou
          </Text>
        </View>

        {/* Login Form */}
        <View style={styles.form}>
          {/* Error Message */}
          {error && (
            <View style={styles.errorContainer}>
              <Text style={styles.errorText}>{error}</Text>
            </View>
          )}

          {/* Username Input */}
          <View style={styles.inputContainer}>
            <Text style={styles.label}>Nom d'utilisateur</Text>
            <TextInput
              style={[styles.input, formErrors.username && styles.inputError]}
              placeholder="Entrez votre nom d'utilisateur"
              placeholderTextColor="#999"
              value={username}
              onChangeText={setUsername}
              autoCapitalize="none"
              autoCorrect={false}
              editable={!isLoading}
              testID="username-input"
            />
            {formErrors.username && (
              <Text style={styles.fieldError}>{formErrors.username}</Text>
            )}
          </View>

          {/* Password Input */}
          <View style={styles.inputContainer}>
            <Text style={styles.label}>Mot de passe</Text>
            <View style={styles.passwordContainer}>
              <TextInput
                style={[
                  styles.input,
                  styles.passwordInput,
                  formErrors.password && styles.inputError,
                ]}
                placeholder="Entrez votre mot de passe"
                placeholderTextColor="#999"
                value={password}
                onChangeText={setPassword}
                secureTextEntry={!showPassword}
                autoCapitalize="none"
                autoCorrect={false}
                editable={!isLoading}
                testID="password-input"
              />
              <TouchableOpacity
                style={styles.showPasswordButton}
                onPress={() => setShowPassword(!showPassword)}
                disabled={isLoading}
              >
                <Text style={styles.showPasswordText}>
                  {showPassword ? 'Masquer' : 'Afficher'}
                </Text>
              </TouchableOpacity>
            </View>
            {formErrors.password && (
              <Text style={styles.fieldError}>{formErrors.password}</Text>
            )}
          </View>


          {/* Login Button */}
          <TouchableOpacity
            style={[styles.loginButton, isLoading && styles.loginButtonDisabled]}
            onPress={handleLogin}
            disabled={isLoading}
            testID="login-button"
          >
            {isLoading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.loginButtonText}>Se connecter</Text>
            )}
          </TouchableOpacity>

          {/* Biometric Login Button */}
          {biometricAvailable && biometricEnabled && (
            <TouchableOpacity
              style={styles.biometricButton}
              onPress={handleBiometricLogin}
              disabled={isLoading}
              testID="biometric-button"
            >
              <Text style={styles.biometricIcon}>
                {biometricType === 'Face ID' ? '👤' : '👆'}
              </Text>
              <Text style={styles.biometricButtonText}>
                Se connecter avec {biometricType}
              </Text>
            </TouchableOpacity>
          )}
        </View>

        {/* Footer */}
        <View style={styles.footer}>
          <Text style={styles.footerText}>
            Version 1.0.0
          </Text>
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
    justifyContent: 'center',
    padding: 24,
  },
  header: {
    alignItems: 'center',
    marginBottom: 40,
  },
  logoContainer: {
    width: 100,
    height: 100,
    borderRadius: 50,
    backgroundColor: '#3498db',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 8,
    elevation: 8,
  },
  logoText: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#fff',
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#2c3e50',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 14,
    color: '#7f8c8d',
    textAlign: 'center',
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
  loginButton: {
    backgroundColor: '#3498db',
    borderRadius: 10,
    padding: 16,
    alignItems: 'center',
    marginTop: 8,
  },
  loginButtonDisabled: {
    backgroundColor: '#93c5fd',
  },
  loginButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  biometricButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 16,
    padding: 14,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#3498db',
    backgroundColor: '#fff',
  },
  biometricIcon: {
    fontSize: 20,
    marginRight: 8,
  },
  biometricButtonText: {
    color: '#3498db',
    fontSize: 14,
    fontWeight: '500',
  },
  footer: {
    alignItems: 'center',
    marginTop: 32,
  },
  footerText: {
    color: '#9ca3af',
    fontSize: 12,
  },
});
