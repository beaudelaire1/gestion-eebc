/**
 * AuthService - Authentication management
 * Handles login, logout, token refresh, password change, and biometric auth
 * Requirements: 1.1, 1.2, 1.4, 1.5, 1.6, 1.7
 */

import * as LocalAuthentication from 'expo-local-authentication';
import { STORAGE_KEYS, MAX_LOGIN_ATTEMPTS, LOCKOUT_DURATION } from '../constants';
import { AuthResult, User } from '../types/api';
import { apiService } from './ApiService';
import { storageService } from './StorageService';

interface LoginResponse {
  access: string;
  refresh: string;
  user: User;
  must_change_password?: boolean;
}

interface RefreshResponse {
  access: string;
}

interface LoginAttemptInfo {
  count: number;
  lastAttempt: number;
  lockedUntil: number | null;
}

export interface AuthServiceInterface {
  login(username: string, password: string): Promise<AuthResult>;
  logout(): Promise<void>;
  refreshToken(): Promise<string | null>;
  changePassword(oldPassword: string, newPassword: string): Promise<void>;
  isAuthenticated(): Promise<boolean>;
  getCurrentUser(): Promise<User | null>;
  enableBiometric(): Promise<void>;
  disableBiometric(): Promise<void>;
  isBiometricEnabled(): Promise<boolean>;
  authenticateWithBiometric(): Promise<AuthResult>;
  getLoginAttemptInfo(username: string): Promise<LoginAttemptInfo>;
  isAccountLocked(username: string): Promise<boolean>;
}

class AuthService implements AuthServiceInterface {
  private currentUser: User | null = null;

  constructor() {
    // Setup token refresh callback for ApiService
    apiService.onTokenExpired(async () => {
      return this.refreshToken();
    });
  }


  /**
   * Login with username and password
   * Requirements: 1.1, 1.2, 1.8
   */
  async login(username: string, password: string): Promise<AuthResult> {
    // Check if account is locked
    if (await this.isAccountLocked(username)) {
      const attemptInfo = await this.getLoginAttemptInfo(username);
      const remainingTime = attemptInfo.lockedUntil
        ? Math.ceil((attemptInfo.lockedUntil - Date.now()) / 1000 / 60)
        : 0;
      return {
        success: false,
        error: `Compte verrouillé. Réessayez dans ${remainingTime} minutes.`,
      };
    }

    const response = await apiService.post<LoginResponse>('/auth/login/', {
      username,
      password,
    });

    if (!response.success) {
      // Increment failed login attempts
      await this.recordFailedAttempt(username);
      
      // Check if now locked
      if (await this.isAccountLocked(username)) {
        return {
          success: false,
          error: `Compte verrouillé après ${MAX_LOGIN_ATTEMPTS} tentatives échouées.`,
        };
      }

      return {
        success: false,
        error: response.error || 'Identifiants invalides',
      };
    }

    // Clear failed attempts on successful login
    await this.clearFailedAttempts(username);

    const { access, refresh, user, must_change_password } = response.data;

    // Store tokens securely
    await storageService.setSecure(STORAGE_KEYS.ACCESS_TOKEN, access);
    await storageService.setSecure(STORAGE_KEYS.REFRESH_TOKEN, refresh);
    await storageService.set(STORAGE_KEYS.USER_DATA, user);

    // Set token in API service
    apiService.setAuthToken(access);

    this.currentUser = user;

    return {
      success: true,
      user,
      accessToken: access,
      refreshToken: refresh,
      mustChangePassword: must_change_password ?? false,
    };
  }


  /**
   * Logout and clear all stored data
   * Requirements: 1.6
   */
  async logout(): Promise<void> {
    try {
      // Call logout endpoint to invalidate token on server
      await apiService.post('/auth/logout/', {});
    } catch {
      // Continue with local logout even if server call fails
    }

    // Clear tokens from secure storage
    await storageService.clearSecure([
      STORAGE_KEYS.ACCESS_TOKEN,
      STORAGE_KEYS.REFRESH_TOKEN,
    ]);

    // Clear user data
    await storageService.delete(STORAGE_KEYS.USER_DATA);

    // Clear API service token
    apiService.clearAuthToken();

    this.currentUser = null;
  }

  /**
   * Refresh the access token using refresh token
   * Requirements: 1.4
   */
  async refreshToken(): Promise<string | null> {
    const refreshToken = await storageService.getSecure(STORAGE_KEYS.REFRESH_TOKEN);

    if (!refreshToken) {
      return null;
    }

    const response = await apiService.post<RefreshResponse>('/auth/refresh/', {
      refresh: refreshToken,
    });

    if (!response.success) {
      // Refresh failed, user needs to login again
      await this.logout();
      return null;
    }

    const { access } = response.data;

    // Store new access token
    await storageService.setSecure(STORAGE_KEYS.ACCESS_TOKEN, access);
    apiService.setAuthToken(access);

    return access;
  }

  /**
   * Change user password
   * Requirements: 1.5
   */
  async changePassword(oldPassword: string, newPassword: string): Promise<void> {
    const response = await apiService.put('/auth/password/', {
      old_password: oldPassword,
      new_password: newPassword,
    });

    if (!response.success) {
      throw new Error(response.error || 'Échec du changement de mot de passe');
    }
  }


  /**
   * Check if user is authenticated
   */
  async isAuthenticated(): Promise<boolean> {
    const accessToken = await storageService.getSecure(STORAGE_KEYS.ACCESS_TOKEN);
    return accessToken !== null;
  }

  /**
   * Get current user from cache or storage
   */
  async getCurrentUser(): Promise<User | null> {
    if (this.currentUser) {
      return this.currentUser;
    }

    const user = await storageService.get<User>(STORAGE_KEYS.USER_DATA);
    if (user) {
      this.currentUser = user;
    }
    return user;
  }

  /**
   * Initialize auth state from storage (call on app start)
   */
  async initialize(): Promise<boolean> {
    const accessToken = await storageService.getSecure(STORAGE_KEYS.ACCESS_TOKEN);
    
    if (accessToken) {
      apiService.setAuthToken(accessToken);
      await this.getCurrentUser();
      return true;
    }
    
    return false;
  }

  /**
   * Enable biometric authentication
   * Requirements: 1.7
   */
  async enableBiometric(): Promise<void> {
    const hasHardware = await LocalAuthentication.hasHardwareAsync();
    if (!hasHardware) {
      throw new Error('Authentification biométrique non disponible sur cet appareil');
    }

    const isEnrolled = await LocalAuthentication.isEnrolledAsync();
    if (!isEnrolled) {
      throw new Error('Aucune donnée biométrique enregistrée sur cet appareil');
    }

    await storageService.set(STORAGE_KEYS.BIOMETRIC_ENABLED, true);
  }

  /**
   * Disable biometric authentication
   */
  async disableBiometric(): Promise<void> {
    await storageService.set(STORAGE_KEYS.BIOMETRIC_ENABLED, false);
  }

  /**
   * Check if biometric is enabled
   */
  async isBiometricEnabled(): Promise<boolean> {
    const enabled = await storageService.get<boolean>(STORAGE_KEYS.BIOMETRIC_ENABLED);
    return enabled === true;
  }


  /**
   * Authenticate using biometric
   * Requirements: 1.7
   */
  async authenticateWithBiometric(): Promise<AuthResult> {
    const isBiometricEnabled = await this.isBiometricEnabled();
    if (!isBiometricEnabled) {
      return {
        success: false,
        error: 'Authentification biométrique non activée',
      };
    }

    const hasStoredCredentials = await this.isAuthenticated();
    if (!hasStoredCredentials) {
      return {
        success: false,
        error: 'Aucune session enregistrée',
      };
    }

    const result = await LocalAuthentication.authenticateAsync({
      promptMessage: 'Authentification requise',
      cancelLabel: 'Annuler',
      disableDeviceFallback: false,
    });

    if (!result.success) {
      return {
        success: false,
        error: 'Authentification biométrique échouée',
      };
    }

    // Biometric success - restore session
    const accessToken = await storageService.getSecure(STORAGE_KEYS.ACCESS_TOKEN);
    if (accessToken) {
      apiService.setAuthToken(accessToken);
    }

    const user = await this.getCurrentUser();

    return {
      success: true,
      user: user ?? undefined,
      accessToken: accessToken ?? undefined,
    };
  }

  /**
   * Get login attempt info for a username
   * Requirements: 1.8
   */
  async getLoginAttemptInfo(username: string): Promise<LoginAttemptInfo> {
    const key = `login_attempts_${username}`;
    const info = await storageService.get<LoginAttemptInfo>(key);
    return info ?? { count: 0, lastAttempt: 0, lockedUntil: null };
  }

  /**
   * Check if account is locked due to failed attempts
   * Requirements: 1.8
   */
  async isAccountLocked(username: string): Promise<boolean> {
    const info = await this.getLoginAttemptInfo(username);
    
    if (info.lockedUntil && Date.now() < info.lockedUntil) {
      return true;
    }

    // Clear lock if expired
    if (info.lockedUntil && Date.now() >= info.lockedUntil) {
      await this.clearFailedAttempts(username);
    }

    return false;
  }


  /**
   * Record a failed login attempt
   */
  private async recordFailedAttempt(username: string): Promise<void> {
    const key = `login_attempts_${username}`;
    const info = await this.getLoginAttemptInfo(username);

    const newCount = info.count + 1;
    const newInfo: LoginAttemptInfo = {
      count: newCount,
      lastAttempt: Date.now(),
      lockedUntil: newCount >= MAX_LOGIN_ATTEMPTS ? Date.now() + LOCKOUT_DURATION : null,
    };

    await storageService.set(key, newInfo);
  }

  /**
   * Clear failed login attempts
   */
  private async clearFailedAttempts(username: string): Promise<void> {
    const key = `login_attempts_${username}`;
    await storageService.delete(key);
  }
}

// Export singleton instance
export const authService = new AuthService();

// Export class for testing
export { AuthService };
