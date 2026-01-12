/**
 * StorageService - Wrapper for SecureStore (tokens) and AsyncStorage (cache)
 * Provides secure storage for sensitive data and regular storage for cache
 * Requirements: 1.3, 9.1
 */

import * as SecureStore from 'expo-secure-store';
import AsyncStorage from '@react-native-async-storage/async-storage';

export interface StorageServiceInterface {
  // Secure storage (for tokens)
  setSecure(key: string, value: string): Promise<void>;
  getSecure(key: string): Promise<string | null>;
  deleteSecure(key: string): Promise<void>;

  // Regular storage (for cache)
  set<T>(key: string, value: T): Promise<void>;
  get<T>(key: string): Promise<T | null>;
  delete(key: string): Promise<void>;
  clear(): Promise<void>;
}

class StorageService implements StorageServiceInterface {
  /**
   * Store a value securely (encrypted)
   * Use for sensitive data like tokens
   */
  async setSecure(key: string, value: string): Promise<void> {
    try {
      await SecureStore.setItemAsync(key, value);
    } catch (error) {
      console.error(`Error storing secure value for key ${key}:`, error);
      throw new Error(`Failed to store secure value: ${(error as Error).message}`);
    }
  }

  /**
   * Retrieve a securely stored value
   */
  async getSecure(key: string): Promise<string | null> {
    try {
      return await SecureStore.getItemAsync(key);
    } catch (error) {
      console.error(`Error retrieving secure value for key ${key}:`, error);
      return null;
    }
  }

  /**
   * Delete a securely stored value
   */
  async deleteSecure(key: string): Promise<void> {
    try {
      await SecureStore.deleteItemAsync(key);
    } catch (error) {
      console.error(`Error deleting secure value for key ${key}:`, error);
      throw new Error(`Failed to delete secure value: ${(error as Error).message}`);
    }
  }


  /**
   * Store a value in regular storage (for cache)
   * Values are JSON serialized
   */
  async set<T>(key: string, value: T): Promise<void> {
    try {
      const jsonValue = JSON.stringify(value);
      await AsyncStorage.setItem(key, jsonValue);
    } catch (error) {
      console.error(`Error storing value for key ${key}:`, error);
      throw new Error(`Failed to store value: ${(error as Error).message}`);
    }
  }

  /**
   * Retrieve a value from regular storage
   * Values are JSON parsed
   */
  async get<T>(key: string): Promise<T | null> {
    try {
      const jsonValue = await AsyncStorage.getItem(key);
      if (jsonValue === null) {
        return null;
      }
      return JSON.parse(jsonValue) as T;
    } catch (error) {
      console.error(`Error retrieving value for key ${key}:`, error);
      return null;
    }
  }

  /**
   * Delete a value from regular storage
   */
  async delete(key: string): Promise<void> {
    try {
      await AsyncStorage.removeItem(key);
    } catch (error) {
      console.error(`Error deleting value for key ${key}:`, error);
      throw new Error(`Failed to delete value: ${(error as Error).message}`);
    }
  }

  /**
   * Clear all values from regular storage
   * Note: This does NOT clear secure storage
   */
  async clear(): Promise<void> {
    try {
      await AsyncStorage.clear();
    } catch (error) {
      console.error('Error clearing storage:', error);
      throw new Error(`Failed to clear storage: ${(error as Error).message}`);
    }
  }

  /**
   * Clear all tokens from secure storage
   * Useful for logout
   */
  async clearSecure(keys: string[]): Promise<void> {
    try {
      await Promise.all(keys.map((key) => this.deleteSecure(key)));
    } catch (error) {
      console.error('Error clearing secure storage:', error);
      throw new Error(`Failed to clear secure storage: ${(error as Error).message}`);
    }
  }
}

// Export singleton instance
export const storageService = new StorageService();

// Export class for testing
export { StorageService };
