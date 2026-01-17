/**
 * NyayamGPT Auth API Client
 */

import type { 
  LoginCredentials, 
  SignupData, 
  AuthTokens, 
  User,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Token storage keys
const ACCESS_TOKEN_KEY = 'nyayam_access_token';
const REFRESH_TOKEN_KEY = 'nyayam_refresh_token';

class AuthApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
    console.log('Auth Client initialized with URL:', this.baseUrl);
  }

  // Token management
  getAccessToken(): string | null {
    return localStorage.getItem(ACCESS_TOKEN_KEY);
  }

  getRefreshToken(): string | null {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  }

  setTokens(accessToken: string, refreshToken: string): void {
    localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  }

  clearTokens(): void {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  }

  isAuthenticated(): boolean {
    return !!this.getAccessToken();
  }

  // HTTP helpers
  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
    authenticated = false
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };

    if (authenticated) {
      const token = this.getAccessToken();
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    // Handle 401 - try refresh token
    if (response.status === 401 && authenticated) {
      const refreshed = await this.refreshTokens();
      if (refreshed) {
        // Retry with new token
        headers['Authorization'] = `Bearer ${this.getAccessToken()}`;
        const retryResponse = await fetch(url, { ...options, headers });
        if (retryResponse.ok) {
          return retryResponse.json();
        }
      }
      // Refresh failed, clear tokens
      this.clearTokens();
      throw new Error('Session expired. Please login again.');
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({
        message: 'An unexpected error occurred',
      }));
      
      let errorMessage = error.message || 'An unexpected error occurred';
      
      if (error.detail) {
        if (typeof error.detail === 'string') {
          errorMessage = error.detail;
        } else if (Array.isArray(error.detail)) {
          // Handle FastAPI validation errors
          errorMessage = error.detail
            .map((err: any) => err.msg || JSON.stringify(err))
            .join(', ');
        } else if (typeof error.detail === 'object') {
          errorMessage = JSON.stringify(error.detail);
        }
      }
      
      throw new Error(errorMessage);
    }

    return response.json();
  }

  // Auth endpoints
  async signup(data: SignupData): Promise<AuthTokens> {
    const result = await this.request<AuthTokens>('/auth/signup', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    
    this.setTokens(result.access_token, result.refresh_token);
    return result;
  }

  async login(credentials: LoginCredentials): Promise<AuthTokens> {
    const result = await this.request<AuthTokens>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });
    
    this.setTokens(result.access_token, result.refresh_token);
    return result;
  }

  async logout(): Promise<void> {
    try {
      const refreshToken = this.getRefreshToken();
      if (refreshToken) {
        await this.request('/auth/logout', { 
          method: 'POST',
          body: JSON.stringify({ refresh_token: refreshToken })
        }, true);
      }
    } catch {
      // Ignore logout errors
    } finally {
      this.clearTokens();
    }
  }

  async refreshTokens(): Promise<boolean> {
    const refreshToken = this.getRefreshToken();
    if (!refreshToken) return false;

    try {
      const result = await this.request<AuthTokens>('/auth/refresh', {
        method: 'POST',
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      
      this.setTokens(result.access_token, result.refresh_token);
      return true;
    } catch {
      return false;
    }
  }

  async getCurrentUser(): Promise<User> {
    return this.request<User>('/auth/me', {}, true);
  }

  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    await this.request('/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
        confirm_new_password: newPassword,
      }),
    }, true);
  }
}

// Export singleton instance
export const authApi = new AuthApiClient();
