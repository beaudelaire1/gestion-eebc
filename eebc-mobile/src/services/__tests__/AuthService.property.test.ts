/**
 * AuthService Property-Based Tests
 * Feature: eebc-mobile-app
 * Property 2: Token Auto-Refresh
 * Property 3: Password Change Redirect
 * Validates: Requirements 1.4, 1.5
 */

import fc from 'fast-check';
import { AuthService } from '../AuthService';
import { apiService } from '../ApiService';
import { storageService } from '../StorageService';
import { STORAGE_KEYS } from '../../constants';
import { User } from '../../types/api';

// Mock the services
jest.mock('../ApiService', () => ({
  apiService: {
    post: jest.fn(),
    put: jest.fn(),
    setAuthToken: jest.fn(),
    clearAuthToken: jest.fn(),
    onTokenExpired: jest.fn(),
  },
}));

jest.mock('../StorageService', () => ({
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
const userArbitrary = fc.record({
  id: fc.integer({ min: 1, max: 10000 }),
  username: fc.string({ minLength: 3, maxLength: 30 }).filter((s) => /^[a-zA-Z0-9_]+$/.test(s)),
  email: fc.emailAddress(),
  firstName: fc.string({ minLength: 1, maxLength: 50 }),
  lastName: fc.string({ minLength: 1, maxLength: 50 }),
  role: fc.constantFrom('admin', 'pastor', 'secretary', 'leader', 'member') as fc.Arbitrary<User['role']>,
  memberId: fc.option(fc.integer({ min: 1, max: 10000 }), { nil: undefined }),
  permissions: fc.array(fc.string({ minLength: 1, maxLength: 30 }), { maxLength: 10 }),
});

const tokenArbitrary = fc.string({ minLength: 20, maxLength: 500 }).filter((s) => s.trim().length > 0);

describe('AuthService Property Tests', () => {
  let authService: AuthService;

  beforeEach(() => {
    jest.clearAllMocks();
    authService = new AuthService();
  });


  /**
   * Property 2: Token Auto-Refresh
   * For any expired access token with a valid refresh token, the system SHALL
   * automatically obtain a new valid access token without user intervention.
   */
  describe('Property 2: Token Auto-Refresh', () => {
    it('should return new access token when refresh token is valid', async () => {
      await fc.assert(
        fc.asyncProperty(
          tokenArbitrary, // refresh token
          tokenArbitrary, // new access token
          async (refreshToken, newAccessToken) => {
            // Setup: refresh token exists in storage
            (storageService.getSecure as jest.Mock).mockImplementation((key: string) => {
              if (key === STORAGE_KEYS.REFRESH_TOKEN) {
                return Promise.resolve(refreshToken);
              }
              return Promise.resolve(null);
            });

            // API returns new access token
            (apiService.post as jest.Mock).mockResolvedValue({
              success: true,
              data: { access: newAccessToken },
              status: 200,
            });

            // Execute refresh
            const result = await authService.refreshToken();

            // Verify: new token is returned and stored
            expect(result).toBe(newAccessToken);
            expect(storageService.setSecure).toHaveBeenCalledWith(
              STORAGE_KEYS.ACCESS_TOKEN,
              newAccessToken
            );
            expect(apiService.setAuthToken).toHaveBeenCalledWith(newAccessToken);

            return result === newAccessToken;
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should return null and logout when refresh token is invalid', async () => {
      await fc.assert(
        fc.asyncProperty(tokenArbitrary, async (refreshToken) => {
          // Setup: refresh token exists
          (storageService.getSecure as jest.Mock).mockImplementation((key: string) => {
            if (key === STORAGE_KEYS.REFRESH_TOKEN) {
              return Promise.resolve(refreshToken);
            }
            return Promise.resolve(null);
          });

          // API returns error (invalid refresh token)
          (apiService.post as jest.Mock).mockResolvedValue({
            success: false,
            error: 'Invalid refresh token',
            status: 401,
          });

          // Execute refresh
          const result = await authService.refreshToken();

          // Verify: null returned and logout triggered
          expect(result).toBeNull();
          expect(storageService.clearSecure).toHaveBeenCalled();

          return result === null;
        }),
        { numRuns: 100 }
      );
    });

    it('should return null when no refresh token exists', async () => {
      // Setup: no refresh token
      (storageService.getSecure as jest.Mock).mockResolvedValue(null);

      const result = await authService.refreshToken();

      expect(result).toBeNull();
      expect(apiService.post).not.toHaveBeenCalled();
    });
  });


  /**
   * Property 3: Password Change Redirect
   * For any user with must_change_password flag set to true, authentication SHALL
   * redirect to the password change screen before allowing access to main app.
   */
  describe('Property 3: Password Change Redirect', () => {
    it('should return mustChangePassword=true when user must change password', async () => {
      await fc.assert(
        fc.asyncProperty(
          fc.string({ minLength: 3, maxLength: 30 }), // username
          fc.string({ minLength: 8, maxLength: 50 }), // password
          userArbitrary,
          tokenArbitrary, // access token
          tokenArbitrary, // refresh token
          async (username, password, user, accessToken, refreshToken) => {
            // Setup: API returns must_change_password = true
            (apiService.post as jest.Mock).mockResolvedValue({
              success: true,
              data: {
                access: accessToken,
                refresh: refreshToken,
                user,
                must_change_password: true,
              },
              status: 200,
            });

            // No previous failed attempts
            (storageService.get as jest.Mock).mockResolvedValue(null);

            // Execute login
            const result = await authService.login(username, password);

            // Verify: mustChangePassword is true
            expect(result.success).toBe(true);
            expect(result.mustChangePassword).toBe(true);

            return result.mustChangePassword === true;
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should return mustChangePassword=false when user does not need to change password', async () => {
      await fc.assert(
        fc.asyncProperty(
          fc.string({ minLength: 3, maxLength: 30 }),
          fc.string({ minLength: 8, maxLength: 50 }),
          userArbitrary,
          tokenArbitrary,
          tokenArbitrary,
          async (username, password, user, accessToken, refreshToken) => {
            // Setup: API returns must_change_password = false or undefined
            (apiService.post as jest.Mock).mockResolvedValue({
              success: true,
              data: {
                access: accessToken,
                refresh: refreshToken,
                user,
                must_change_password: false,
              },
              status: 200,
            });

            // No previous failed attempts
            (storageService.get as jest.Mock).mockResolvedValue(null);

            // Execute login
            const result = await authService.login(username, password);

            // Verify: mustChangePassword is false
            expect(result.success).toBe(true);
            expect(result.mustChangePassword).toBe(false);

            return result.mustChangePassword === false;
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should store tokens and user data on successful login regardless of mustChangePassword', async () => {
      await fc.assert(
        fc.asyncProperty(
          fc.string({ minLength: 3, maxLength: 30 }),
          fc.string({ minLength: 8, maxLength: 50 }),
          userArbitrary,
          tokenArbitrary,
          tokenArbitrary,
          fc.boolean(), // must_change_password
          async (username, password, user, accessToken, refreshToken, mustChange) => {
            // Setup
            (apiService.post as jest.Mock).mockResolvedValue({
              success: true,
              data: {
                access: accessToken,
                refresh: refreshToken,
                user,
                must_change_password: mustChange,
              },
              status: 200,
            });

            (storageService.get as jest.Mock).mockResolvedValue(null);

            // Execute login
            const result = await authService.login(username, password);

            // Verify: tokens are stored regardless of mustChangePassword
            expect(result.success).toBe(true);
            expect(storageService.setSecure).toHaveBeenCalledWith(
              STORAGE_KEYS.ACCESS_TOKEN,
              accessToken
            );
            expect(storageService.setSecure).toHaveBeenCalledWith(
              STORAGE_KEYS.REFRESH_TOKEN,
              refreshToken
            );
            expect(storageService.set).toHaveBeenCalledWith(STORAGE_KEYS.USER_DATA, user);

            return result.success === true;
          }
        ),
        { numRuns: 100 }
      );
    });
  });
});
