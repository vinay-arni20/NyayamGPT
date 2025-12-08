/**
 * NyayamGPT API Types
 */

// ============================================================================
// Auth Types
// ============================================================================

export type UserRole = 'citizen' | 'lawyer' | 'judge' | 'admin';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  preferred_language: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  last_login?: string;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface SignupData {
  email: string;
  password: string;
  confirm_password: string;
  full_name: string;
  role?: UserRole;
  preferred_language?: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface AuthError {
  error: string;
  message: string;
}

// ============================================================================
// Chat Types
// ============================================================================

export interface Citation {
  act: string        // Act name (IPC, CrPC, etc.)
  law?: string       // Alias for act (backwards compatibility)
  section: string    // Section number
  title?: string     // Section title
  url: string        // Official government URL
  context?: string   // Usage context
  verified: boolean  // Whether URL is from official source
  excerpt?: string   // Legacy field for backwards compatibility
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  citations?: Citation[]
  timestamp: Date
  isLoading?: boolean
  validationAttempts?: number
  processingTimeMs?: number
}

export interface ChatSession {
  id: string
  title: string
  language: string
  messages: ChatMessage[]
  createdAt: Date
  updatedAt: Date
}

export interface ChatRequest {
  message: string       // User's legal question
  session_id?: string
  language?: string
  mode?: 'normal' | 'lawyer' | 'qa' | 'web' | 'deep'  // Chat mode for different response styles
}

export interface ChatResponse {
  session_id: string
  answer: string
  citations: Citation[]
  language: string
  intent?: string
  validation_passed: boolean
  validation_attempts: number
  processing_time_ms: number
  trace_id?: string
}

export interface ApiError {
  detail: string | any
  status_code: number
}

export interface HealthStatus {
  status: string
  version: string
  environment: string
  database: string
  vector_store: string
  gemini_api: string
}

// ============================================================================
// Session API Types
// ============================================================================

export interface SessionResponse {
  id: string
  user_id: string | null
  title: string
  language: string
  created_at: string
  updated_at: string
  is_active: boolean
}

export interface MessageResponse {
  id: string
  session_id: string
  role: 'user' | 'assistant'
  content: string
  citations?: Citation[]
  processing_time_ms?: number
  created_at: string
}

export interface SessionWithMessages extends SessionResponse {
  messages: MessageResponse[]
}
