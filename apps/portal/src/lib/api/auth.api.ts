import { apiClient } from './client';

export interface LoginPayload {
  email: string;
  password: string;
  tenantSlug: string;
}

export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
}

export interface AuthUser {
  id: string;
  name: string;
  email: string;
  role: string;
  tenantId: string;
  avatarUrl?: string;
}

export interface LoginResponse {
  user: AuthUser;
  accessToken: string;
  refreshToken: string;
}

export interface RefreshResponse {
  accessToken: string;
  refreshToken: string;
}

export const authApi = {
  /**
   * Authenticate a user with email, password, and tenant slug.
   */
  login: async (email: string, password: string, tenantSlug: string): Promise<LoginResponse> => {
    const { data } = await apiClient.post<LoginResponse>('/v1/auth/login', {
      email,
      password,
      tenantSlug,
    });
    return data;
  },

  /**
   * Refresh authentication tokens using a refresh token.
   */
  refresh: async (refreshToken: string): Promise<RefreshResponse> => {
    const { data } = await apiClient.post<RefreshResponse>('/v1/auth/refresh', {
      refreshToken,
    });
    return data;
  },

  /**
   * Logout the current user, invalidating tokens server-side.
   */
  logout: async (): Promise<void> => {
    await apiClient.post('/v1/auth/logout');
  },

  /**
   * Get the currently authenticated user's profile.
   */
  getMe: async (): Promise<AuthUser> => {
    const { data } = await apiClient.get<AuthUser>('/v1/auth/me');
    return data;
  },
};
