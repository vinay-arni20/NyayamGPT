/**
 * NyayamGPT Auth Store
 * Zustand store for authentication state management
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User, LoginCredentials, SignupData, UserRole } from '../types';
import { authApi } from '../api/auth';
import { useChatStore } from './useChatStore';

interface AuthState {
  // State
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  
  // Actions
  login: (credentials: LoginCredentials) => Promise<void>;
  signup: (data: SignupData) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  checkAuth: () => Promise<boolean>;
  clearError: () => void;
  
  // Role helpers
  hasRole: (...roles: UserRole[]) => boolean;
  isAdmin: () => boolean;
  isLawyer: () => boolean;
  isJudge: () => boolean;
}

// Helper to sync chat store with current user
const syncChatWithUser = async (userId: string | null) => {
  const chatStore = useChatStore.getState();
  
  if (userId) {
    // Set user ID first (this preserves sessions on first login)
    chatStore.setCurrentUserId(userId);
    
    // Load sessions from backend and merge with local
    await chatStore.loadSessionsFromBackend();
  } else {
    // On logout, only clear current session selection, keep sessions in store
    // They'll be loaded from backend on next login
    chatStore.setCurrentUserId(null);
    chatStore.setCurrentSession('');
  }
};

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      // Initial state
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      // Login
      login: async (credentials: LoginCredentials) => {
        set({ isLoading: true, error: null });
        
        try {
          const result = await authApi.login(credentials);
          set({ 
            user: result.user, 
            isAuthenticated: true, 
            isLoading: false,
            error: null,
          });
          
          // Load user's chat sessions from backend
          await syncChatWithUser(result.user.id);
        } catch (error) {
          set({ 
            isLoading: false, 
            error: error instanceof Error ? error.message : 'Login failed',
          });
          throw error;
        }
      },

      // Signup
      signup: async (data: SignupData) => {
        set({ isLoading: true, error: null });
        
        try {
          const result = await authApi.signup(data);
          set({ 
            user: result.user, 
            isAuthenticated: true, 
            isLoading: false,
            error: null,
          });
          
          // Initialize chat store for new user (will be empty)
          await syncChatWithUser(result.user.id);
        } catch (error) {
          set({ 
            isLoading: false, 
            error: error instanceof Error ? error.message : 'Signup failed',
          });
          throw error;
        }
      },

      // Logout
      logout: async () => {
        set({ isLoading: true });
        
        try {
          await authApi.logout();
        } finally {
          // Don't clear chat storage - it's persisted and will be loaded on next login
          // Just reset current session state
          await syncChatWithUser(null);
          
          set({ 
            user: null, 
            isAuthenticated: false, 
            isLoading: false,
            error: null,
          });
        }
      },

      // Refresh user data
      refreshUser: async () => {
        if (!authApi.isAuthenticated()) {
          set({ user: null, isAuthenticated: false });
          return;
        }

        try {
          const user = await authApi.getCurrentUser();
          set({ user, isAuthenticated: true });
        } catch {
          set({ user: null, isAuthenticated: false });
          authApi.clearTokens();
        }
      },

      // Check if user is authenticated (on app load)
      checkAuth: async () => {
        if (!authApi.isAuthenticated()) {
          set({ user: null, isAuthenticated: false });
          return false;
        }

        try {
          const user = await authApi.getCurrentUser();
          set({ user, isAuthenticated: true });
          
          // Load user's chat sessions from backend
          await syncChatWithUser(user.id);
          
          return true;
        } catch {
          set({ user: null, isAuthenticated: false });
          authApi.clearTokens();
          return false;
        }
      },

      // Clear error
      clearError: () => {
        set({ error: null });
      },

      // Role helpers
      hasRole: (...roles: UserRole[]) => {
        const { user } = get();
        if (!user) return false;
        return roles.includes(user.role);
      },

      isAdmin: () => {
        const { user } = get();
        return user?.role === 'admin';
      },

      isLawyer: () => {
        const { user } = get();
        return user?.role === 'lawyer';
      },

      isJudge: () => {
        const { user } = get();
        return user?.role === 'judge';
      },
    }),
    {
      name: 'nyayam-auth',
      // Only persist user data, not tokens (handled by authApi)
      partialize: (state) => ({ 
        user: state.user, 
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
