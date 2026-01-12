/**
 * Auth Store - Zustand store for authentication state management
 * Requirements: 1.1, 1.6
 */

import { create } from 'zustand';
import { User, AuthResult } from '../types/api';
import { authService } from '../services/AuthService';

interface AuthState {
  // State
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  mustChangePassword: boolean;
  error: string | null;

  // Actions
  login: (username: string, password: string) => Promise<AuthResult>;
  logout: () => Promise<void>;
  loginWithBiometric: () => Promise<AuthResult>;
  changePassword: (oldPassword: string, newPassword: string) => Promise<void>;
  initialize: () => Promise<boolean>;
  clearError: () => void;
  setMustChangePassword: (value: boolean) => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  // Initial state
  user: null,
  isAuthenticated: false,
  isLoading: false,
  mustChangePassword: false,
  error: null,

  /**
   * Login with username and password
   * Requirements: 1.1
   */
  login: async (username: string, password: string): Promise<AuthResult> => {
    set({ isLoading: true, error: null });

    try {
      const result = await authService.login(username, password);

      if (result.success) {
        set({
          user: result.user ?? null,
          isAuthenticated: true,
          mustChangePassword: result.mustChangePassword ?? false,
          isLoading: false,
          error: null,
        });
      } else {
        set({
          isLoading: false,
          error: result.error ?? 'Échec de la connexion',
        });
      }

      return result;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Erreur inconnue';
      set({
        isLoading: false,
        error: errorMessage,
      });
      return {
        success: false,
        error: errorMessage,
      };
    }
  },

  /**
   * Logout and clear all auth state
   * Requirements: 1.6
   */
  logout: async (): Promise<void> => {
    set({ isLoading: true });

    try {
      await authService.logout();
    } finally {
      set({
        user: null,
        isAuthenticated: false,
        mustChangePassword: false,
        isLoading: false,
        error: null,
      });
    }
  },

  /**
   * Login with biometric authentication
   * Requirements: 1.7
   */
  loginWithBiometric: async (): Promise<AuthResult> => {
    set({ isLoading: true, error: null });

    try {
      const result = await authService.authenticateWithBiometric();

      if (result.success) {
        set({
          user: result.user ?? null,
          isAuthenticated: true,
          isLoading: false,
          error: null,
        });
      } else {
        set({
          isLoading: false,
          error: result.error ?? 'Échec de l\'authentification biométrique',
        });
      }

      return result;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Erreur inconnue';
      set({
        isLoading: false,
        error: errorMessage,
      });
      return {
        success: false,
        error: errorMessage,
      };
    }
  },

  /**
   * Change password
   * Requirements: 1.5
   */
  changePassword: async (oldPassword: string, newPassword: string): Promise<void> => {
    set({ isLoading: true, error: null });

    try {
      await authService.changePassword(oldPassword, newPassword);
      set({
        mustChangePassword: false,
        isLoading: false,
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Erreur inconnue';
      set({
        isLoading: false,
        error: errorMessage,
      });
      throw error;
    }
  },

  /**
   * Initialize auth state from storage (call on app start)
   */
  initialize: async (): Promise<boolean> => {
    set({ isLoading: true });

    try {
      const isAuthenticated = await authService.initialize();
      
      if (isAuthenticated) {
        const user = await authService.getCurrentUser();
        set({
          user,
          isAuthenticated: true,
          isLoading: false,
        });
        return true;
      }

      set({ isLoading: false });
      return false;
    } catch (error) {
      set({ isLoading: false });
      return false;
    }
  },

  /**
   * Clear error state
   */
  clearError: (): void => {
    set({ error: null });
  },

  /**
   * Set must change password flag
   */
  setMustChangePassword: (value: boolean): void => {
    set({ mustChangePassword: value });
  },
}));
