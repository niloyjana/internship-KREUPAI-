import { create } from 'zustand';
import { apiClient } from '../api/client';

export interface AdminUser {
  id: string;
  name: string;
  email: string;
  role: string;
  avatarUrl?: string;
}

interface AuthState {
  user: AdminUser | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  /**
   * Login with email and password (platform admin, no tenant slug).
   * Stores tokens in cookies and user in state.
   */
  login: (email: string, password: string) => Promise<void>;

  /**
   * Logout: calls API, clears cookies, and resets state.
   */
  logout: () => Promise<void>;

  /**
   * Check if the user is authenticated by calling getMe().
   * Sets user in state if valid, clears otherwise.
   */
  checkAuth: () => Promise<boolean>;
}

function setCookie(name: string, value: string, days: number = 7) {
  const expires = new Date(Date.now() + days * 864e5).toUTCString();
  document.cookie = `${name}=${value}; path=/; expires=${expires}; SameSite=Lax`;
}

function clearCookie(name: string) {
  document.cookie = `${name}=; path=/; max-age=0`;
}

function getCookie(name: string): string | null {
  if (typeof window === 'undefined') return null;
  const match = document.cookie.split('; ').find((row) => row.startsWith(`${name}=`));
  return match ? match.split('=')[1] : null;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  accessToken: null,
  refreshToken: null,
  isAuthenticated: false,
  isLoading: false,

  login: async (email, password) => {
    set({ isLoading: true });
    try {
      const response = await apiClient.post('/auth/login', { email, password });
      const { user, accessToken, refreshToken } = response.data;

      // Store tokens in cookies
      setCookie('accessToken', accessToken, 1); // 1 day
      setCookie('refreshToken', refreshToken, 7); // 7 days

      set({
        user,
        accessToken,
        refreshToken,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (error) {
      set({ isLoading: false });
      throw error;
    }
  },

  logout: async () => {
    try {
      await apiClient.post('/auth/logout');
    } catch {
      // Ignore logout API errors -- clear local state regardless
    } finally {
      clearCookie('accessToken');
      clearCookie('refreshToken');
      set({
        user: null,
        accessToken: null,
        refreshToken: null,
        isAuthenticated: false,
        isLoading: false,
      });
    }
  },

  checkAuth: async () => {
    const token = getCookie('accessToken');
    if (!token) {
      set({ user: null, isAuthenticated: false });
      return false;
    }

    set({ isLoading: true });
    try {
      const response = await apiClient.get('/auth/me');
      const user = response.data;
      set({
        user,
        accessToken: token,
        refreshToken: getCookie('refreshToken'),
        isAuthenticated: true,
        isLoading: false,
      });
      return true;
    } catch {
      clearCookie('accessToken');
      clearCookie('refreshToken');
      set({
        user: null,
        accessToken: null,
        refreshToken: null,
        isAuthenticated: false,
        isLoading: false,
      });
      return false;
    }
  },
}));
