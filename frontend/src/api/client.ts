/**
 * NyayamGPT API Client
 */

import type { ChatRequest, ChatResponse, HealthStatus, ApiError, SessionResponse, SessionWithMessages } from '../types'

// Use environment variable or default to localhost backend
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Token storage keys (same as auth.ts)
const ACCESS_TOKEN_KEY = 'nyayamgpt_access_token';

class ApiClient {
  private baseUrl: string

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl
  }

  private getAuthHeaders(): Record<string, string> {
    const token = localStorage.getItem(ACCESS_TOKEN_KEY);
    if (token) {
      return { 'Authorization': `Bearer ${token}` };
    }
    return {};
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`
    
    const config: RequestInit = {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...this.getAuthHeaders(),
        ...options.headers,
      },
    }

    const response = await fetch(url, config)

    if (!response.ok) {
      const error: ApiError = await response.json().catch(() => ({
        detail: 'An unexpected error occurred',
        status_code: response.status,
      }))
      
      // Handle validation errors where detail is an array/object
      const errorMessage = typeof error.detail === 'string' 
        ? error.detail 
        : Array.isArray(error.detail)
          ? error.detail.map((e: any) => e.msg).join(', ')
          : JSON.stringify(error.detail);

      throw new Error(errorMessage)
    }

    return response.json()
  }

  /**
   * Send a chat message and get a response
   */
  async chat(request: ChatRequest, signal?: AbortSignal): Promise<ChatResponse> {
    return this.request<ChatResponse>('/chat', {
      method: 'POST',
      body: JSON.stringify(request),
      signal,
    })
  }

  /**
   * Stream chat response
   */
  async *streamChat(request: ChatRequest, signal?: AbortSignal): AsyncGenerator<any> {
    const url = `${this.baseUrl}/chat/stream`
    
    const response = await fetch(url, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        ...this.getAuthHeaders(),
      },
      body: JSON.stringify(request),
      signal,
    })

    if (!response.ok) {
      throw new Error('Stream request failed')
    }

    const reader = response.body?.getReader()
    if (!reader) {
      throw new Error('No response body')
    }

    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n\n')
      buffer = lines.pop() || '' // Keep the last incomplete chunk

      for (const line of lines) {
        const trimmed = line.trim()
        if (trimmed.startsWith('data: ')) {
          const data = trimmed.slice(6)
          try {
            yield JSON.parse(data)
          } catch (e) {
            console.error('Failed to parse SSE data', e)
          }
        }
      }
    }
  }

  /**
   * Get health status
   */
  async getHealth(): Promise<HealthStatus> {
    return this.request<HealthStatus>('/health')
  }

  /**
   * Get detailed health status
   */
  async getHealthDetails(): Promise<HealthStatus> {
    return this.request<HealthStatus>('/health/details')
  }

  // =========================================================================
  // Session Management
  // =========================================================================

  /**
   * Get all chat sessions for the current user
   */
  async getSessions(limit: number = 50, offset: number = 0): Promise<SessionResponse[]> {
    return this.request<SessionResponse[]>(`/chat/sessions?limit=${limit}&offset=${offset}`)
  }

  /**
   * Get a specific session with all its messages
   */
  async getSession(sessionId: string): Promise<SessionWithMessages> {
    return this.request<SessionWithMessages>(`/chat/sessions/${sessionId}`)
  }

  /**
   * Delete a chat session
   */
  async deleteSession(sessionId: string): Promise<void> {
    return this.request<void>(`/chat/sessions/${sessionId}`, {
      method: 'DELETE',
    })
  }
}

// Export singleton instance
export const apiClient = new ApiClient()

// Export class for custom instances
export { ApiClient }
