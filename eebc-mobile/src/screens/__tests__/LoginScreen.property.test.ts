/**
 * LoginScreen Property-Based Tests
 * Feature: eebc-mobile-app
 * Property 4: Account Lockout
 * Validates: Requirements 1.8
 * 
 * For any sequence of 5 consecutive failed login attempts for the same user,
 * the system SHALL display an account locked message.
 */

import fc from 'fast-check';
import { AuthService } from '../../services/AuthService';
import { apiService } from '../../services/ApiService';
import { storageService } from '../../services/StorageService';
import { MAX_LOGIN_ATTEMPTS, LOCKOUT_DURATION } from '../../constants';

// Mock the services
jest.mock('../../services/ApiService', () => ({
  apiService: {
    post: jest.fn(),
    put: jest.fn(),
    setAuthToken: jest.fn(),
    clearAuthToken: jest.fn(),
    onTokenExpired: jest.fn(),
  },
}));

jest.mock('../../services/StorageService', () => ({
  storageService: {
    setSecure: jest.fn(),
    getSecure: jest.fn(),
    deleteSecure: jest.fn(),
    set: jest.fn(),
    get: jest.fn(),
    delete: jest.fn(),
    clearSecure: jest.fn(),
  },
}));

// Arbitrary generators
const usernameArbitrary = fc.string({ minLength: 3, maxLength: 30 })
  .filter((s) => /^[a-zA-Z0-9_]+$/.test(s));

const passwordArbitrary = fc.string({ minLength: 4, maxLength: 50 });

describe('LoginScreen Property Tests', () => {
  let authService: AuthService;
  let loginAttemptStorage: Map<string, { count: number; lastAttempt: number; lockedUntil: number | null }>;

  beforeEach(() => {
    jest.clearAllMocks();
    authService = new AuthService();
    loginAttemptStorage = new Map();


    // Mock storage to track login attempts
    (storageService.get as jest.Mock).mockImplementation((key: string) => {
      if (key.startsWith('login_attempts_')) {
        const username = key.replace('login_attempts_', '');
        return Promise.resolve(loginAttemptStorage.get(username) || null);
      }
      return Promise.resolve(null);
    });

    (storageService.set as jest.Mock).mockImplementation((key: string, value: unknown) => {
      if (key.startsWith('login_attempts_')) {
        const username = key.replace('login_attempts_', '');
        loginAttemptStorage.set(username, value as { count: number; lastAttempt: number; lockedUntil: number | null });
      }
      return Promise.resolve();
    });

    (storageService.delete as jest.Mock).mockImplementation((key: string) => {
      if (key.startsWith('login_attempts_')) {
        const username = key.replace('login_attempts_', '');
        loginAttemptStorage.delete(username);
      }
      return Promise.resolve();
    });
  });

  /**
   * Property 4: Account Lockout
   * For any sequence of 5 consecutive failed login attempts for the same user,
   * the system SHALL display an account locked message.
   * Validates: Requirements 1.8
   */
  describe('Property 4: Account Lockout', () => {
    it('should lock account after exactly MAX_LOGIN_ATTEMPTS (5) consecutive failed attempts', async () => {
      await fc.assert(
        fc.asyncProperty(
          usernameArbitrary,
          passwordArbitrary,
          async (username, password) => {
            // Reset storage for this test
            loginAttemptStorage.clear();

            // Setup: API always returns failure (invalid credentials)
            (apiService.post as jest.Mock).mockResolvedValue({
              success: false,
              error: 'Invalid credentials',
              status: 401,
            });

            // Execute: Make MAX_LOGIN_ATTEMPTS failed login attempts
            for (let i = 0; i < MAX_LOGIN_ATTEMPTS; i++) {
              const result = await authService.login(username, password);
              
              // Before the last attempt, account should not be locked
              if (i < MAX_LOGIN_ATTEMPTS - 1) {
                expect(result.success).toBe(false);
                const isLocked = await authService.isAccountLocked(username);
                expect(isLocked).toBe(false);
              }
            }

            // After MAX_LOGIN_ATTEMPTS, account should be locked
            const isLockedAfter = await authService.isAccountLocked(username);
            expect(isLockedAfter).toBe(true);

            // Verify: Next login attempt should return locked message
            const lockedResult = await authService.login(username, password);
            expect(lockedResult.success).toBe(false);
            expect(lockedResult.error).toContain('verrouillé');

            return isLockedAfter === true;
          }
        ),
        { numRuns: 100 }
      );
    });


    it('should not lock account with fewer than MAX_LOGIN_ATTEMPTS failed attempts', async () => {
      await fc.assert(
        fc.asyncProperty(
          usernameArbitrary,
          passwordArbitrary,
          fc.integer({ min: 1, max: MAX_LOGIN_ATTEMPTS - 1 }), // fewer than max attempts
          async (username, password, attemptCount) => {
            // Reset storage for this test
            loginAttemptStorage.clear();

            // Setup: API always returns failure
            (apiService.post as jest.Mock).mockResolvedValue({
              success: false,
              error: 'Invalid credentials',
              status: 401,
            });

            // Execute: Make fewer than MAX_LOGIN_ATTEMPTS failed attempts
            for (let i = 0; i < attemptCount; i++) {
              await authService.login(username, password);
            }

            // Verify: Account should NOT be locked
            const isLocked = await authService.isAccountLocked(username);
            expect(isLocked).toBe(false);

            return isLocked === false;
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should clear failed attempts on successful login', async () => {
      await fc.assert(
        fc.asyncProperty(
          usernameArbitrary,
          passwordArbitrary,
          fc.integer({ min: 1, max: MAX_LOGIN_ATTEMPTS - 1 }), // some failed attempts
          async (username, password, failedAttempts) => {
            // Reset storage for this test
            loginAttemptStorage.clear();

            // Setup: First N attempts fail
            (apiService.post as jest.Mock).mockResolvedValue({
              success: false,
              error: 'Invalid credentials',
              status: 401,
            });

            // Make some failed attempts
            for (let i = 0; i < failedAttempts; i++) {
              await authService.login(username, password);
            }

            // Verify failed attempts were recorded
            const attemptInfo = await authService.getLoginAttemptInfo(username);
            expect(attemptInfo.count).toBe(failedAttempts);

            // Now setup successful login
            (apiService.post as jest.Mock).mockResolvedValue({
              success: true,
              data: {
                access: 'access_token',
                refresh: 'refresh_token',
                user: {
                  id: 1,
                  username,
                  email: 'test@test.com',
                  firstName: 'Test',
                  lastName: 'User',
                  role: 'member',
                  permissions: [],
                },
              },
              status: 200,
            });

            // Execute successful login
            const result = await authService.login(username, password);
            expect(result.success).toBe(true);

            // Verify: Failed attempts should be cleared
            const attemptInfoAfter = await authService.getLoginAttemptInfo(username);
            expect(attemptInfoAfter.count).toBe(0);

            return attemptInfoAfter.count === 0;
          }
        ),
        { numRuns: 100 }
      );
    });


    it('should unlock account after lockout duration expires', async () => {
      await fc.assert(
        fc.asyncProperty(
          usernameArbitrary,
          async (username) => {
            // Reset storage for this test
            loginAttemptStorage.clear();

            // Setup: Account is locked with expired lockout time
            const expiredLockoutTime = Date.now() - 1000; // 1 second ago
            loginAttemptStorage.set(username, {
              count: MAX_LOGIN_ATTEMPTS,
              lastAttempt: expiredLockoutTime - LOCKOUT_DURATION,
              lockedUntil: expiredLockoutTime,
            });

            // Verify: Account should NOT be locked (lockout expired)
            const isLocked = await authService.isAccountLocked(username);
            expect(isLocked).toBe(false);

            return isLocked === false;
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should keep account locked during lockout duration', async () => {
      await fc.assert(
        fc.asyncProperty(
          usernameArbitrary,
          async (username) => {
            // Reset storage for this test
            loginAttemptStorage.clear();

            // Setup: Account is locked with future lockout time
            const futureLockoutTime = Date.now() + LOCKOUT_DURATION;
            loginAttemptStorage.set(username, {
              count: MAX_LOGIN_ATTEMPTS,
              lastAttempt: Date.now(),
              lockedUntil: futureLockoutTime,
            });

            // Verify: Account should be locked
            const isLocked = await authService.isAccountLocked(username);
            expect(isLocked).toBe(true);

            return isLocked === true;
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should track failed attempts independently per username', async () => {
      await fc.assert(
        fc.asyncProperty(
          usernameArbitrary,
          usernameArbitrary.filter((u) => u.length > 3), // ensure different usernames
          passwordArbitrary,
          async (username1, username2, password) => {
            // Ensure usernames are different
            if (username1 === username2) {
              return true; // Skip this case
            }

            // Reset storage for this test
            loginAttemptStorage.clear();

            // Setup: API always returns failure
            (apiService.post as jest.Mock).mockResolvedValue({
              success: false,
              error: 'Invalid credentials',
              status: 401,
            });

            // Make MAX_LOGIN_ATTEMPTS failed attempts for username1
            for (let i = 0; i < MAX_LOGIN_ATTEMPTS; i++) {
              await authService.login(username1, password);
            }

            // Make 2 failed attempts for username2
            for (let i = 0; i < 2; i++) {
              await authService.login(username2, password);
            }

            // Verify: username1 should be locked, username2 should not
            const isLocked1 = await authService.isAccountLocked(username1);
            const isLocked2 = await authService.isAccountLocked(username2);

            expect(isLocked1).toBe(true);
            expect(isLocked2).toBe(false);

            return isLocked1 === true && isLocked2 === false;
          }
        ),
        { numRuns: 100 }
      );
    });
  });
});
