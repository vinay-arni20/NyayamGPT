import { useState, useCallback, useRef } from "react";
import { ChatSidebar, ChatContainer } from "../components/chat";
import { useChatStore } from "../hooks/useChatStore";
import { useTheme } from "../hooks/useTheme";
import { apiClient } from "../api/client";
import { SEOWrapper } from "../components/layout/SEOWrapper";

export default function ChatPage() {
  const [sidebarOpen, setSidebarOpen] = useState(true); // Default open on desktop
  const abortControllerRef = useRef<AbortController | null>(null);

  // Use individual selectors for better reactivity
  const addMessage = useChatStore((state) => state.addMessage);
  const updateLastMessage = useChatStore((state) => state.updateLastMessage);
  const setLoading = useChatStore((state) => state.setLoading);
  const isLoading = useChatStore((state) => state.isLoading);
  const setError = useChatStore((state) => state.setError);
  const createNewSession = useChatStore((state) => state.createNewSession);
  const replaceSessionId = useChatStore((state) => state.replaceSessionId);
  const sessions = useChatStore((state) => state.sessions);
  const currentSessionId = useChatStore((state) => state.currentSessionId);

  const currentSession = sessions.find((s) => s.id === currentSessionId);
  const messages = currentSession?.messages || [];

  // Initialize theme
  useTheme();

  const handleStop = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setLoading(false);
    }
  }, [setLoading]);

  const handleSendMessage = useCallback(
    async (content: string) => {
      // Ensure we have a session
      let activeSessionId = currentSessionId;
      if (!activeSessionId) {
        activeSessionId = createNewSession();
      }

      // Cancel previous request if any
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      // Create new controller
      const abortController = new AbortController();
      abortControllerRef.current = abortController;

      // Add user message
      addMessage({ role: "user", content });

      // Add placeholder for assistant response
      addMessage({ role: "assistant", content: "", isStreaming: true });

      setLoading(true);
      setError(null);

      try {
        // Check if it's a local session (starts with chat_)
        // If so, don't send session_id to backend so it creates a new one
        const isLocalSession = activeSessionId.startsWith("chat_");

        const response = await apiClient.chat(
          {
            message: content,
            session_id: isLocalSession ? undefined : activeSessionId,
            language: "en",
            mode: "deep", // Default to deep/unified mode
          },
          abortController.signal
        );

        console.log("Backend response:", response);

        // If we had a local session, update it with the backend ID
        if (isLocalSession && response.session_id) {
          replaceSessionId(activeSessionId, response.session_id);
        }

        // Update assistant message with response
        const citations = (response.citations || []).map(
          (c: {
            act?: string;
            law?: string;
            section?: string;
            title?: string;
            url?: string;
            context?: string;
            verified?: boolean;
          }) => ({
            act: c.act || c.law || "",
            law: c.act || c.law || "",
            section: c.section || "",
            title: c.title || "",
            url: c.url || "",
            context: c.context || "Indian Kanoon",
            verified: c.verified ?? false,
          })
        );

        updateLastMessage(
          response.answer || "I apologize, but I couldn't generate a response.",
          citations
        );
      } catch (error) {
        if (error instanceof Error && error.name === "AbortError") {
          console.log("Request aborted");
          return;
        }
        console.error("Chat error:", error);
        const errorMessage =
          error instanceof Error
            ? error.message
            : "An unexpected error occurred";
        setError(errorMessage);
        updateLastMessage(
          "I apologize, but an error occurred while processing your request. Please try again."
        );
      } finally {
        if (abortControllerRef.current === abortController) {
          abortControllerRef.current = null;
          setLoading(false);
        }
      }
    },
    [
      addMessage,
      updateLastMessage,
      setLoading,
      setError,
      currentSession,
      createNewSession,
      replaceSessionId,
      currentSessionId,
    ]
  );

  const handleTopicClick = useCallback(
    (topic: string) => {
      handleSendMessage(topic);
    },
    [handleSendMessage]
  );

  return (
    <>
      <SEOWrapper
        title='Chat with NyayamGPT - AI Legal Assistant'
        description='Get instant answers to your Indian legal questions with NyayamGPT. Supports multiple modes including Lawyer, Q&A, and Deep Research.'
      />
      <div className='flex h-screen overflow-hidden bg-background'>
        {/* Sidebar */}
        <ChatSidebar
          isOpen={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
        />

        {/* Main content - New Premium ChatContainer */}
        <ChatContainer
          messages={messages}
          isLoading={isLoading}
          onSendMessage={handleSendMessage}
          onStop={handleStop}
          onTopicClick={handleTopicClick}
          sidebarOpen={sidebarOpen}
          onSidebarToggle={() => setSidebarOpen(!sidebarOpen)}
        />
      </div>
    </>
  );
}
