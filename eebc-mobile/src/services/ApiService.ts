/**
 * ApiService - HTTP client wrapper using Axios
 * Handles API requests with automatic token management and error handling
 * Requirements: 1.3
 */

import axios, {
  AxiosInstance,
  AxiosError,
  InternalAxiosRequestConfig,
  AxiosResponse,
} from 'axios';
import { API_BASE_URL, API_TIMEOUT } from '../constants';
import { ApiResponse } from '../types/api';

export enum NetworkError {
  NO_CONNECTION = 'NO_CONNECTION',
  TIMEOUT = 'TIMEOUT',
  SERVER_ERROR = 'SERVER_ERROR',
  UNAUTHORIZED = 'UNAUTHORIZED',
  FORBIDDEN = 'FORBIDDEN',
  NOT_FOUND = 'NOT_FOUND',
}

export interface ApiServiceConfig {
  baseURL?: string;
  timeout?: number;
}

type TokenRefreshCallback = () => Promise<string | null>;

class ApiService {
  private client: AxiosInstance;
  private authToken: string | null = null;
  private tokenRefreshCallback: TokenRefreshCallback | null = null;
  private isRefreshing = false;
  private refreshSubscribers: Array<(token: string) => void> = [];

  constructor(config?: ApiServiceConfig) {
    this.client = axios.create({
      baseURL: config?.baseURL ?? API_BASE_URL,
      timeout: config?.timeout ?? API_TIMEOUT,
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
    });

    this.setupInterceptors();
  }


  private setupInterceptors(): void {
    // Request interceptor - add auth token to headers
    this.client.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        if (this.authToken) {
          config.headers.Authorization = `Bearer ${this.authToken}`;
        }
        return config;
      },
      (error: AxiosError) => Promise.reject(error)
    );

    // Response interceptor - handle errors and token refresh
    this.client.interceptors.response.use(
      (response: AxiosResponse) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config as InternalAxiosRequestConfig & {
          _retry?: boolean;
        };

        // Handle 401 Unauthorized - attempt token refresh
        if (
          error.response?.status === 401 &&
          !originalRequest._retry &&
          this.tokenRefreshCallback
        ) {
          if (this.isRefreshing) {
            // Wait for the refresh to complete
            return new Promise((resolve) => {
              this.refreshSubscribers.push((token: string) => {
                originalRequest.headers.Authorization = `Bearer ${token}`;
                resolve(this.client(originalRequest));
              });
            });
          }

          originalRequest._retry = true;
          this.isRefreshing = true;

          try {
            const newToken = await this.tokenRefreshCallback();
            if (newToken) {
              this.setAuthToken(newToken);
              this.onRefreshSuccess(newToken);
              originalRequest.headers.Authorization = `Bearer ${newToken}`;
              return this.client(originalRequest);
            }
          } catch (refreshError) {
            this.onRefreshFailure();
            return Promise.reject(refreshError);
          } finally {
            this.isRefreshing = false;
          }
        }

        return Promise.reject(this.normalizeError(error));
      }
    );
  }

  private onRefreshSuccess(token: string): void {
    this.refreshSubscribers.forEach((callback) => callback(token));
    this.refreshSubscribers = [];
  }

  private onRefreshFailure(): void {
    this.refreshSubscribers = [];
  }


  private normalizeError(error: AxiosError): Error & { code: NetworkError } {
    const normalizedError = new Error() as Error & { code: NetworkError };

    if (!error.response) {
      if (error.code === 'ECONNABORTED') {
        normalizedError.message = 'Le serveur met trop de temps à répondre';
        normalizedError.code = NetworkError.TIMEOUT;
      } else {
        normalizedError.message = 'Pas de connexion internet';
        normalizedError.code = NetworkError.NO_CONNECTION;
      }
      return normalizedError;
    }

    switch (error.response.status) {
      case 401:
        normalizedError.message = 'Session expirée';
        normalizedError.code = NetworkError.UNAUTHORIZED;
        break;
      case 403:
        normalizedError.message = 'Accès non autorisé';
        normalizedError.code = NetworkError.FORBIDDEN;
        break;
      case 404:
        normalizedError.message = 'Ressource non trouvée';
        normalizedError.code = NetworkError.NOT_FOUND;
        break;
      default:
        normalizedError.message = 'Une erreur est survenue';
        normalizedError.code = NetworkError.SERVER_ERROR;
    }

    return normalizedError;
  }

  /**
   * Set the authentication token for API requests
   */
  setAuthToken(token: string): void {
    this.authToken = token;
  }

  /**
   * Clear the authentication token
   */
  clearAuthToken(): void {
    this.authToken = null;
  }

  /**
   * Get the current auth token (for testing purposes)
   */
  getAuthToken(): string | null {
    return this.authToken;
  }

  /**
   * Set callback for token refresh when 401 is received
   */
  onTokenExpired(callback: TokenRefreshCallback): void {
    this.tokenRefreshCallback = callback;
  }


  /**
   * GET request
   */
  async get<T>(
    endpoint: string,
    params?: Record<string, unknown>
  ): Promise<ApiResponse<T>> {
    try {
      const response = await this.client.get<T>(endpoint, { params });
      return {
        data: response.data,
        status: response.status,
        success: true,
      };
    } catch (error) {
      const err = error as Error & { code?: NetworkError };
      return {
        data: null as unknown as T,
        status: (error as AxiosError).response?.status ?? 0,
        success: false,
        error: err.message,
      };
    }
  }

  /**
   * POST request
   */
  async post<T>(
    endpoint: string,
    data: Record<string, unknown>
  ): Promise<ApiResponse<T>> {
    try {
      const response = await this.client.post<T>(endpoint, data);
      return {
        data: response.data,
        status: response.status,
        success: true,
      };
    } catch (error) {
      const err = error as Error & { code?: NetworkError };
      return {
        data: null as unknown as T,
        status: (error as AxiosError).response?.status ?? 0,
        success: false,
        error: err.message,
      };
    }
  }

  /**
   * PUT request
   */
  async put<T>(
    endpoint: string,
    data: Record<string, unknown>
  ): Promise<ApiResponse<T>> {
    try {
      const response = await this.client.put<T>(endpoint, data);
      return {
        data: response.data,
        status: response.status,
        success: true,
      };
    } catch (error) {
      const err = error as Error & { code?: NetworkError };
      return {
        data: null as unknown as T,
        status: (error as AxiosError).response?.status ?? 0,
        success: false,
        error: err.message,
      };
    }
  }

  /**
   * DELETE request
   */
  async delete(endpoint: string): Promise<ApiResponse<void>> {
    try {
      const response = await this.client.delete(endpoint);
      return {
        data: undefined as unknown as void,
        status: response.status,
        success: true,
      };
    } catch (error) {
      const err = error as Error & { code?: NetworkError };
      return {
        data: undefined as unknown as void,
        status: (error as AxiosError).response?.status ?? 0,
        success: false,
        error: err.message,
      };
    }
  }
}

// Export singleton instance
export const apiService = new ApiService();

// Export class for testing
export { ApiService };
