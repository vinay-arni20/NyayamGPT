import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { generateChatId } from '@/lib/utils';
import { apiClient } from '@/api/client';
import type { SessionWithMessages, Citation } from '@/types';

// Re-export Citation for backwards compatibility
export type { Citation };

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  timestamp: Date;
  isStreaming?: boolean;
}

export interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
  createdAt: Date;
  updatedAt: Date;
}

interface ChatStore {
  // State
  sessions: ChatSession[];
  currentSessionId: string | null;
  isLoading: boolean;
  error: string | null;
  currentUserId: string | null;  // Track current user

  // Computed
  currentSession: () => ChatSession | null;
  
  // Actions
  createNewSession: () => string;
  setCurrentSession: (sessionId: string) => void;
  deleteSession: (sessionId: string) => Promise<void>;
  clearAllSessions: () => void;
  
  addMessage: (message: Omit<Message, 'id' | 'timestamp'>) => void;
  updateLastMessage: (content: string, citations?: Citation[]) => void;
  setMessageStreaming: (messageId: string, isStreaming: boolean) => void;
  
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  
  updateSessionTitle: (sessionId: string, title: string) => void;
  replaceSessionId: (oldId: string, newId: string) => void;
  
  // User & Backend sync
  setCurrentUserId: (userId: string | null) => void;
  loadSessionsFromBackend: () => Promise<void>;
  loadSessionWithMessages: (sessionId: string) => Promise<void>;
}

export const useChatStore = create<ChatStore>()(
  persist(
    (set, get) => ({
      // Initial state
      sessions: [],
      currentSessionId: null,
      isLoading: false,
      error: null,
      currentUserId: null,

      // Computed
      currentSession: () => {
        const { sessions, currentSessionId } = get();
        return sessions.find(s => s.id === currentSessionId) || null;
      },

      // Actions
      createNewSession: () => {
        const newSession: ChatSession = {
          id: generateChatId(),
          title: 'New Chat',
          messages: [],
          createdAt: new Date(),
          updatedAt: new Date(),
        };
        
        set(state => ({
          sessions: [newSession, ...state.sessions],
          currentSessionId: newSession.id,
          error: null,
        }));
        
        return newSession.id;
      },

      setCurrentSession: (sessionId: string) => {
        set({ currentSessionId: sessionId, error: null });
      },

      deleteSession: async (sessionId: string) => {
        // Optimistic update
        set(state => {
          const filteredSessions = state.sessions.filter(s => s.id !== sessionId);
          const newCurrentId = state.currentSessionId === sessionId
            ? (filteredSessions[0]?.id || null)
            : state.currentSessionId;
          
          return {
            sessions: filteredSessions,
            currentSessionId: newCurrentId,
          };
        });

        try {
          await apiClient.deleteSession(sessionId);
        } catch (error) {
          console.error('Failed to delete session from backend:', error);
        }
      },

      clearAllSessions: () => {
        set({ sessions: [], currentSessionId: null });
      },

      addMessage: (message) => {
        const { currentSessionId, createNewSession } = get();
        
        // Create a new session if none exists
        let sessionId = currentSessionId;
        if (!sessionId) {
          sessionId = createNewSession();
        }

        const newMessage: Message = {
          ...message,
          id: `msg_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`,
          timestamp: new Date(),
        };

        set(state => ({
          sessions: state.sessions.map(session => {
            if (session.id !== sessionId) return session;
            
            // Update title from first user message
            const newTitle = session.messages.length === 0 && message.role === 'user'
              ? message.content.slice(0, 50) + (message.content.length > 50 ? '...' : '')
              : session.title;
            
            return {
              ...session,
              title: newTitle,
              messages: [...session.messages, newMessage],
              updatedAt: new Date(),
            };
          }),
        }));
      },

      updateLastMessage: (content: string, citations?: Citation[]) => {
        const { currentSessionId } = get();
        console.log("updateLastMessage called:", { currentSessionId, content: content?.substring(0, 100), citations });
        if (!currentSessionId) {
          console.warn("No currentSessionId, cannot update message");
          return;
        }

        set(state => ({
          sessions: state.sessions.map(session => {
            if (session.id !== currentSessionId) return session;
            
            const messages = [...session.messages];
            const lastIndex = messages.length - 1;
            console.log("Updating message at index:", lastIndex, "role:", messages[lastIndex]?.role);
            
            if (lastIndex >= 0 && messages[lastIndex].role === 'assistant') {
              messages[lastIndex] = {
                ...messages[lastIndex],
                content,
                citations: citations || messages[lastIndex].citations,
                isStreaming: false,
              };
              console.log("Message updated successfully");
            }
            
            return { ...session, messages, updatedAt: new Date() };
          }),
        }));
      },

      setMessageStreaming: (messageId: string, isStreaming: boolean) => {
        const { currentSessionId } = get();
        if (!currentSessionId) return;

        set(state => ({
          sessions: state.sessions.map(session => {
            if (session.id !== currentSessionId) return session;
            
            return {
              ...session,
              messages: session.messages.map(msg =>
                msg.id === messageId ? { ...msg, isStreaming } : msg
              ),
            };
          }),
        }));
      },

      setLoading: (loading: boolean) => {
        set({ isLoading: loading });
      },

      setError: (error: string | null) => {
        set({ error, isLoading: false });
      },

      updateSessionTitle: (sessionId: string, title: string) => {
        set(state => ({
          sessions: state.sessions.map(session =>
            session.id === sessionId ? { ...session, title } : session
          ),
        }));
      },

      replaceSessionId: (oldId: string, newId: string) => {
        set(state => ({
          sessions: state.sessions.map(session =>
            session.id === oldId ? { ...session, id: newId } : session
          ),
          currentSessionId: state.currentSessionId === oldId ? newId : state.currentSessionId,
        }));
      },

      // User management
      setCurrentUserId: (userId: string | null) => {
        // If userId is null (logout), do nothing to preserve sessions
        if (!userId) return;

        const prevUserId = get().currentUserId;
        
        // If switching to a different user (not first login), clear local sessions
        if (prevUserId && prevUserId !== userId) {
          set({ 
            currentUserId: userId,
            sessions: [],
            currentSessionId: null,
          });
        } else {
          // First login or same user - preserve sessions
          set({ currentUserId: userId });
        }
      },

      // Load sessions from backend API
      loadSessionsFromBackend: async () => {
        try {
          set({ isLoading: true, error: null });
          
          const backendSessions = await apiClient.getSessions();
          const localSessions = get().sessions;
          const currentSessionId = get().currentSessionId;
          
          // Convert backend sessions to local format
          const sessions: ChatSession[] = backendSessions.map(s => ({
            id: s.id,
            title: s.title || 'Chat',
            messages: [], // Messages will be loaded on-demand
            createdAt: new Date(s.created_at),
            updatedAt: new Date(s.updated_at),
          }));
          
          // If we had a current session that's now in backend, preserve it
          let newCurrentSessionId = currentSessionId;
          if (currentSessionId && sessions.some(s => s.id === currentSessionId)) {
            newCurrentSessionId = currentSessionId;
          } else if (sessions.length > 0) {
            newCurrentSessionId = sessions[0].id;
          } else {
            newCurrentSessionId = null;
          }
          
          // Merge with local sessions to preserve any active session data
          const mergedSessions = sessions.map(backendSession => {
            const localSession = localSessions.find(s => s.id === backendSession.id);
            if (localSession && localSession.messages.length > 0) {
              // Keep local messages if we have them
              return localSession;
            }
            return backendSession;
          });
          
          set({ 
            sessions: mergedSessions,
            isLoading: false,
            currentSessionId: newCurrentSessionId,
          });
          
          console.log(`Loaded ${sessions.length} sessions from backend`);
        } catch (error) {
          console.error('Failed to load sessions from backend:', error);
          set({ isLoading: false, error: 'Failed to load chat history' });
        }
      },

      // Load a specific session with its messages
      loadSessionWithMessages: async (sessionId: string) => {
        try {
          const sessionData: SessionWithMessages = await apiClient.getSession(sessionId);
          
          // Convert messages to local format
          const messages: Message[] = sessionData.messages.map(m => ({
            id: m.id,
            role: m.role,
            content: m.content,
            citations: m.citations?.map(c => {
              // Backend may return either 'act' or 'law' field
              const actOrLaw = (c as any).law || (c as any).act || '';
              return {
                act: actOrLaw,
                law: actOrLaw,
                section: c.section,
                title: c.title || '',
                url: c.url,
                context: c.context || '',
                verified: c.verified ?? false,
              } as Citation;
            }),
            timestamp: new Date(m.created_at),
          }));
          
          // Update the session with messages
          set(state => ({
            sessions: state.sessions.map(session =>
              session.id === sessionId
                ? { ...session, messages }
                : session
            ),
            currentSessionId: sessionId,
          }));
          
          console.log(`Loaded ${messages.length} messages for session ${sessionId}`);
        } catch (error) {
          console.error('Failed to load session messages:', error);
        }
      },
    }),
    {
      name: 'nyayam-chat-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        sessions: state.sessions,
        currentSessionId: state.currentSessionId,
        currentUserId: state.currentUserId,
      }),
      // Only rehydrate if the stored user matches current user
      onRehydrateStorage: () => (state) => {
        if (state) {
          console.log('Chat store rehydrated for user:', state.currentUserId);
        }
      },
    }
  )
);
