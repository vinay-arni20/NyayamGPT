import { motion } from "framer-motion";
import { User, Scale, Copy, Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { CitationsPanel } from "./CitationBox";
import type { Message } from "@/hooks/useChatStore";
import { useState } from "react";
import ReactMarkdown from "react-markdown";

interface ChatMessageProps {
  message: Message;
}

// Typing indicator dots
function TypingIndicator() {
  return (
    <div className='flex items-center gap-1 py-2'>
      {[0, 1, 2].map((i) => (
        <motion.div
          key={i}
          className='w-2 h-2 rounded-full bg-primary/60'
          animate={{
            y: [0, -8, 0],
            opacity: [0.5, 1, 0.5],
          }}
          transition={{
            duration: 0.8,
            repeat: Infinity,
            delay: i * 0.15,
          }}
        />
      ))}
    </div>
  );
}

export function ChatMessage({ message }: ChatMessageProps) {
  const [copied, setCopied] = useState(false);
  const isUser = message.role === "user";
  const isStreaming = message.isStreaming;

  // Remove "Sources", "References", "Citations" sections at the end of the content
  // to avoid duplication with the CitationsPanel
  const cleanContent = (content: string) => {
    if (!content) return "";
    return content.replace(
      /(\n\n|\r\n)(##?#?|[*_]{2})?\s*(Sources|References|Citations)\s*(##?#?|[*_]{2})?[\s\S]*$/i,
      ""
    );
  };

  const displayContent = isUser
    ? message.content
    : cleanContent(message.content);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(displayContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={cn(
        "group flex flex-col gap-2 py-6",
        isUser ? "border-b border-border/50" : ""
      )}
    >
      {/* Header */}
      <div className='flex items-center gap-3 mb-2'>
        <div
          className={cn(
            "w-6 h-6 rounded-full flex items-center justify-center",
            isUser
              ? "bg-muted text-muted-foreground"
              : "bg-primary/10 text-primary"
          )}
        >
          {isUser ? (
            <User className='w-3 h-3' />
          ) : (
            <Scale className='w-3 h-3' />
          )}
        </div>
        <span className='font-semibold text-base text-foreground'>
          {isUser ? message.content : "Answer"}
        </span>
      </div>

      {/* Content */}
      <div className='pl-9'>
        {!isUser && message.citations && message.citations.length > 0 && (
          <CitationsPanel citations={message.citations} />
        )}

        {/* Message content */}
        {!isUser && (
          <div className='prose prose-neutral dark:prose-invert max-w-none text-base leading-relaxed'>
            {isStreaming && !displayContent ? (
              <TypingIndicator />
            ) : (
              <ReactMarkdown
                components={{
                  p: ({ children }) => (
                    <p className='mb-4 last:mb-0'>{children}</p>
                  ),
                  ul: ({ children }) => (
                    <ul className='list-disc pl-4 mb-4 space-y-1'>
                      {children}
                    </ul>
                  ),
                  ol: ({ children }) => (
                    <ol className='list-decimal pl-4 mb-4 space-y-1'>
                      {children}
                    </ol>
                  ),
                  h1: ({ children }) => (
                    <h1 className='text-xl font-bold mb-3 mt-6'>{children}</h1>
                  ),
                  h2: ({ children }) => (
                    <h2 className='text-lg font-bold mb-2 mt-4'>{children}</h2>
                  ),
                  h3: ({ children }) => (
                    <h3 className='text-base font-bold mb-2 mt-3'>
                      {children}
                    </h3>
                  ),
                  blockquote: ({ children }) => (
                    <blockquote className='border-l-4 border-primary/30 pl-4 italic my-4 text-muted-foreground'>
                      {children}
                    </blockquote>
                  ),
                  code: ({ children }) => (
                    <code className='bg-muted px-1.5 py-0.5 rounded text-sm font-mono'>
                      {children}
                    </code>
                  ),
                }}
              >
                {displayContent}
              </ReactMarkdown>
            )}
          </div>
        )}

        {/* Copy button for assistant messages */}
        {!isUser && displayContent && (
          <div className='mt-4 flex items-center gap-2'>
            <button
              onClick={handleCopy}
              className='inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors px-2 py-1 rounded-md hover:bg-muted'
              title='Copy response'
            >
              {copied ? (
                <>
                  <Check className='w-3 h-3' />
                  Copied
                </>
              ) : (
                <>
                  <Copy className='w-3 h-3' />
                  Copy
                </>
              )}
            </button>
          </div>
        )}
      </div>
    </motion.div>
  );
}
