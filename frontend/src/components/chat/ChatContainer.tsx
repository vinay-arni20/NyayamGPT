/**
 * NyayamGPT Premium Chat Container
 * =================================
 * Full-height chat interface with glassmorphism design
 */

import { useRef, useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Scale, ArrowDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { MessageBubble } from "./MessageBubble";
import { InputBox } from "./InputBox";
import { TrendingTopics } from "../features/TrendingTopics";
import { ChatHeader } from "./ChatHeader";
import { type ChatMode } from "@/styles/theme";
import type { Message } from "@/hooks/useChatStore";

interface ChatContainerProps {
  messages: Message[];
  isLoading: boolean;
  activeMode?: ChatMode; // Optional/Ignored
  onModeChange?: (mode: ChatMode) => void; // Optional/Ignored
  onSendMessage: (message: string) => void;
  onStop?: () => void; // Added
  onTopicClick: (topic: string) => void;
  sidebarOpen: boolean;
  onSidebarToggle: () => void;
}

export function ChatContainer({
  messages,
  isLoading,
  onSendMessage,
  onStop, // Added
  onTopicClick,
  sidebarOpen,
  onSidebarToggle,
}: ChatContainerProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [showScrollButton, setShowScrollButton] = useState(false);
  const [isNearBottom, setIsNearBottom] = useState(true);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (isNearBottom) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isNearBottom]);

  // Handle scroll events
  const handleScroll = () => {
    if (!scrollRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    const distanceFromBottom = scrollHeight - scrollTop - clientHeight;
    setIsNearBottom(distanceFromBottom < 100);
    setShowScrollButton(distanceFromBottom > 300);
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const hasMessages = messages.length > 0;

  return (
    <div className='relative flex flex-col flex-1 w-full h-full overflow-hidden bg-background/50 backdrop-blur-3xl'>
      {/* Animated Background Blobs */}
      <div className='absolute inset-0 overflow-hidden pointer-events-none'>
        <div className='absolute top-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full bg-amber-500/10 blur-[100px] animate-pulse-slow' />
        <div className='absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] rounded-full bg-orange-500/10 blur-[100px] animate-pulse-slow delay-1000' />
      </div>

      {/* Chat Header */}
      <ChatHeader
        onMenuClick={onSidebarToggle}
        showMenuButton
        sidebarOpen={sidebarOpen}
      />

      {/* Messages Area */}
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className={cn(
          "flex-1 overflow-y-auto px-4 md:px-8 lg:px-32 py-6",
          "scrollbar-thin scrollbar-thumb-secondary scrollbar-track-transparent"
        )}
      >
        <div className='max-w-4xl mx-auto space-y-8 min-h-full flex flex-col'>
          <AnimatePresence mode='popLayout'>
            {!hasMessages ? (
              /* Welcome State */
              <motion.div
                key='welcome'
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className='flex-1 flex flex-col items-center justify-center text-center space-y-8 py-12'
              >
                <motion.div
                  initial={{ scale: 0.8, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{ delay: 0.2, duration: 0.5 }}
                  className='relative'
                >
                  <div className='absolute inset-0 bg-amber-500/20 blur-3xl rounded-full' />
                  <div className='relative p-6 rounded-3xl bg-gradient-to-br from-amber-500 to-orange-600 shadow-2xl shadow-orange-500/30'>
                    <Scale className='w-16 h-16 text-white' />
                  </div>
                </motion.div>

                <div className='space-y-4 max-w-lg'>
                  <motion.h1
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 }}
                    className='text-4xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-foreground to-foreground/70'
                  >
                    NyayamGPT
                  </motion.h1>
                  <motion.p
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.4 }}
                    className='text-lg text-muted-foreground leading-relaxed'
                  >
                    Your advanced AI legal assistant. Ask about Indian laws,
                    case precedents, or get help with legal drafting.
                  </motion.p>
                </div>

                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.5 }}
                  className='w-full max-w-2xl'
                >
                  <TrendingTopics onTopicClick={onTopicClick} />
                </motion.div>
              </motion.div>
            ) : (
              /* Message List */
              <>
                {messages
                  .filter((msg): msg is Message => Boolean(msg))
                  .map((msg, idx) => (
                    <MessageBubble key={idx} message={msg} />
                  ))}
                {/* Invisible element to scroll to */}
                <div ref={messagesEndRef} className='h-4' />
              </>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Scroll to Bottom Button */}
      <AnimatePresence>
        {showScrollButton && (
          <motion.button
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            onClick={scrollToBottom}
            className='absolute bottom-24 right-8 p-3 rounded-full bg-primary text-primary-foreground shadow-lg hover:shadow-xl transition-all z-10'
          >
            <ArrowDown className='w-5 h-5' />
          </motion.button>
        )}
      </AnimatePresence>

      {/* Input Area */}
      <div className='relative z-20 px-4 md:px-8 lg:px-32 pb-6 pt-2 bg-gradient-to-t from-background via-background/80 to-transparent'>
        <div className='max-w-4xl mx-auto'>
          <InputBox
            onSend={onSendMessage}
            onStop={onStop}
            isLoading={isLoading}
            showAttachment
            showVoice
          />
          <p className='text-center text-xs text-muted-foreground mt-3 opacity-60'>
            NyayamGPT can make mistakes. Consider checking important
            information.
          </p>
        </div>
      </div>
    </div>
  );
}
