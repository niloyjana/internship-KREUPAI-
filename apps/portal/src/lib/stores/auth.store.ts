import { create } from 'zustand';
import { authApi, type AuthUser } from '../api/auth.api';

interface AuthState {
  user: AuthUser | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  setUser: (user: AuthUser | null) => void;

  /**
   * Login with email, password, and tenant slug.
   * Stores tokens in cookies and user in state.
   */
  login: (email: string, password: string, tenantSlug: string) => Promise<void>;

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
  const match = document.cookie
    .split('; ')
    .find((row) => row.startsWith(`${name}=`));
  return match ? match.split('=')[1] : null;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  accessToken: null,
  refreshToken: null,
  isAuthenticated: false,
  isLoading: false,

  setUser: (user) =>
    set({ user, isAuthenticated: !!user }),

  login: async (email, password, tenantSlug) => {
    set({ isLoading: true });
    try {
      const response = await authApi.login(email, password, tenantSlug);
      const { user, accessToken, refreshToken } = response;

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
      await authApi.logout();
    } catch {
      // Ignore logout API errors — clear local state regardless
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
      const user = await authApi.getMe();
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
