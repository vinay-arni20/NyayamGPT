import { useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Scale } from "lucide-react";
import { ChatMessage } from "./ChatMessage";
import { ChatInput } from "./ChatInput";
import { useChatStore } from "@/hooks/useChatStore";
import { cn } from "@/lib/utils";

// Example prompts for empty state
const EXAMPLE_PROMPTS = [
  "What are the legal grounds for divorce under the Hindu Marriage Act, 1955?",
  "Explain the procedure for filing an anticipatory bail application under CrPC.",
  "What are the fundamental rights guaranteed under Article 21 of the Constitution?",
  "Discuss the liability for dishonour of cheque under Section 138 of the NI Act.",
];

interface ChatWindowProps {
  onSendMessage: (message: string) => Promise<void>;
  onStop?: () => void;
}

export function ChatWindow({ onSendMessage, onStop }: ChatWindowProps) {
  // Subscribe to individual store values for proper reactivity
  const sessions = useChatStore((state) => state.sessions);
  const currentSessionId = useChatStore((state) => state.currentSessionId);
  const isLoading = useChatStore((state) => state.isLoading);
  const error = useChatStore((state) => state.error);
  const createNewSession = useChatStore((state) => state.createNewSession);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Get current session's messages
  const currentSession = sessions.find((s) => s.id === currentSessionId);
  const messages = currentSession?.messages || [];

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleExampleClick = (prompt: string) => {
    if (!currentSession) {
      createNewSession();
    }
    onSendMessage(prompt);
  };

  return (
    <div className='flex flex-col h-full relative'>
      {/* Messages area */}
      <div
        ref={containerRef}
        className='flex-1 overflow-y-auto scrollbar-thin scrollbar-thumb-border scrollbar-track-transparent'
      >
        {messages.length === 0 ? (
          <EmptyState
            onExampleClick={handleExampleClick}
            onSendMessage={onSendMessage}
            isLoading={isLoading}
          />
        ) : (
          <div className='max-w-3xl mx-auto pb-32 pt-8'>
            <AnimatePresence mode='popLayout'>
              {messages.map((message) => (
                <ChatMessage key={message.id} message={message} />
              ))}
            </AnimatePresence>
            <div ref={messagesEndRef} className='h-4' />
          </div>
        )}

        {/* Error display */}
        {error && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className='max-w-3xl mx-auto px-4 py-3'
          >
            <div className='p-4 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive text-sm'>
              {error}
            </div>
          </motion.div>
        )}
      </div>

      {/* Input area - Only show at bottom if there are messages */}
      {messages.length > 0 && (
        <ChatInput
          onSend={onSendMessage}
          onStop={onStop}
          isLoading={isLoading}
        />
      )}
    </div>
  );
}

interface EmptyStateProps {
  onExampleClick: (prompt: string) => void;
  onSendMessage: (message: string) => void;
  isLoading: boolean;
}

function EmptyState({
  onExampleClick,
  onSendMessage,
  isLoading,
}: EmptyStateProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className='flex flex-col items-center justify-center min-h-full px-4 py-12 max-w-3xl mx-auto'
    >
      {/* Logo */}
      <motion.div
        initial={{ scale: 0.8 }}
        animate={{ scale: 1 }}
        transition={{ delay: 0.1, type: "spring" }}
        className='mb-8 flex flex-col items-center'
      >
        <div className='p-4 rounded-2xl bg-transparent mb-4'>
          {/* Perplexity-style minimal logo */}
          <Scale className='w-16 h-16 text-primary' />
        </div>
        <h1 className='text-4xl font-serif font-medium text-foreground tracking-tight'>
          Where knowledge begins
        </h1>
      </motion.div>

      {/* Centered Search Input */}
      <div className='w-full mb-8'>
        <ChatInput
          onSend={onSendMessage}
          isLoading={isLoading}
          variant='centered'
          placeholder='Ask anything...'
        />
      </div>

      {/* Example prompts */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4 }}
        className='w-full'
      >
        <div className='grid gap-3 sm:grid-cols-2'>
          {EXAMPLE_PROMPTS.map((prompt, index) => (
            <motion.button
              key={index}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 + index * 0.1 }}
              onClick={() => onExampleClick(prompt)}
              className={cn(
                "p-3 rounded-lg text-left text-sm transition-all duration-200",
                "bg-muted/50 hover:bg-muted text-muted-foreground hover:text-foreground",
                "border border-transparent hover:border-border"
              )}
            >
              <span className='line-clamp-1'>{prompt}</span>
            </motion.button>
          ))}
        </div>
      </motion.div>
    </motion.div>
  );
}
