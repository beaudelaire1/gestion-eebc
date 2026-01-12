/**
 * ApiService Tests
 * Tests for interceptors and error handling
 * Requirements: 1.3
 */

import axios from 'axios';
import { ApiService, NetworkError } from '../ApiService';

// Mock axios
jest.mock('axios', () => ({
  create: jest.fn(() => ({
    interceptors: {
      request: { use: jest.fn() },
      response: { use: jest.fn() },
    },
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    delete: jest.fn(),
  })),
}));

describe('ApiService', () => {
  let apiService: ApiService;
  let mockAxiosInstance: jest.Mocked<ReturnType<typeof axios.create>>;

  beforeEach(() => {
    jest.clearAllMocks();
    mockAxiosInstance = (axios.create as jest.Mock)();
    apiService = new ApiService();
  });

  describe('constructor', () => {
    it('should create axios instance with default config', () => {
      expect(axios.create).toHaveBeenCalledWith(
        expect.objectContaining({
          timeout: 30000,
          headers: {
            'Content-Type': 'application/json',
            Accept: 'application/json',
          },
        })
      );
    });

    it('should setup request and response interceptors', () => {
      expect(mockAxiosInstance.interceptors.request.use).toHaveBeenCalled();
      expect(mockAxiosInstance.interceptors.response.use).toHaveBeenCalled();
    });
  });

  describe('setAuthToken', () => {
    it('should store the auth token', () => {
      apiService.setAuthToken('test-token');
      expect(apiService.getAuthToken()).toBe('test-token');
    });
  });

  describe('clearAuthToken', () => {
    it('should clear the auth token', () => {
      apiService.setAuthToken('test-token');
      apiService.clearAuthToken();
      expect(apiService.getAuthToken()).toBeNull();
    });
  });
});
