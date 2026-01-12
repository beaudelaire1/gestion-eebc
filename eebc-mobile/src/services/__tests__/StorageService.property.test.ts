/**
 * StorageService Property-Based Tests
 * Feature: eebc-mobile-app, Property 1: JWT Token Lifecycle
 * Validates: Requirements 1.3, 1.6
 *
 * Property 1: JWT Token Lifecycle
 * For any authenticated user, storing a token then retrieving it SHALL return
 * the same token value, and clearing tokens SHALL result in no tokens being retrievable.
 */

import fc from 'fast-check';
import * as SecureStore from 'expo-secure-store';
import { StorageService } from '../StorageService';

// Mock implementations with in-memory storage
const mockSecureStorage = new Map<string, string>();

jest.mock('expo-secure-store', () => ({
  setItemAsync: jest.fn((key: string, value: string) => {
    mockSecureStorage.set(key, value);
    return Promise.resolve();
  }),
  getItemAsync: jest.fn((key: string) => {
    return Promise.resolve(mockSecureStorage.get(key) ?? null);
  }),
  deleteItemAsync: jest.fn((key: string) => {
    mockSecureStorage.delete(key);
    return Promise.resolve();
  }),
}));

describe('StorageService Property Tests', () => {
  let storageService: StorageService;

  beforeEach(() => {
    mockSecureStorage.clear();
    jest.clearAllMocks();
    storageService = new StorageService();
  });

  /**
   * Property 1: JWT Token Lifecycle
   * For any token string, storing then retrieving SHALL return the same value
   */
  describe('Property 1: JWT Token Lifecycle', () => {
    it('should return the same token value after store and retrieve (round-trip)', async () => {
      await fc.assert(
        fc.asyncProperty(
          // Generate valid JWT-like tokens (non-empty strings)
          fc.string({ minLength: 1, maxLength: 500 }).filter((s) => s.trim().length > 0),
          fc.string({ minLength: 1, maxLength: 50 }).filter((s) => /^[a-zA-Z_][a-zA-Z0-9_]*$/.test(s)),
          async (tokenValue, tokenKey) => {
            // Store the token
            await storageService.setSecure(tokenKey, tokenValue);

            // Retrieve the token
            const retrievedToken = await storageService.getSecure(tokenKey);

            // Should be exactly the same
            return retrievedToken === tokenValue;
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should return null after clearing a token', async () => {
      await fc.assert(
        fc.asyncProperty(
          fc.string({ minLength: 1, maxLength: 500 }).filter((s) => s.trim().length > 0),
          fc.string({ minLength: 1, maxLength: 50 }).filter((s) => /^[a-zA-Z_][a-zA-Z0-9_]*$/.test(s)),
          async (tokenValue, tokenKey) => {
            // Store the token
            await storageService.setSecure(tokenKey, tokenValue);

            // Delete the token
            await storageService.deleteSecure(tokenKey);

            // Retrieve should return null
            const retrievedToken = await storageService.getSecure(tokenKey);

            return retrievedToken === null;
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should clear multiple tokens when clearSecure is called', async () => {
      await fc.assert(
        fc.asyncProperty(
          fc.array(
            fc.record({
              key: fc.string({ minLength: 1, maxLength: 30 }).filter((s) => /^[a-zA-Z_][a-zA-Z0-9_]*$/.test(s)),
              value: fc.string({ minLength: 1, maxLength: 100 }),
            }),
            { minLength: 1, maxLength: 5 }
          ),
          async (tokens) => {
            // Ensure unique keys
            const uniqueTokens = tokens.filter(
              (t, i, arr) => arr.findIndex((x) => x.key === t.key) === i
            );

            // Store all tokens
            for (const token of uniqueTokens) {
              await storageService.setSecure(token.key, token.value);
            }

            // Clear all tokens
            const keys = uniqueTokens.map((t) => t.key);
            await storageService.clearSecure(keys);

            // All tokens should be null
            for (const token of uniqueTokens) {
              const retrieved = await storageService.getSecure(token.key);
              if (retrieved !== null) {
                return false;
              }
            }

            return true;
          }
        ),
        { numRuns: 100 }
      );
    });
  });
});
