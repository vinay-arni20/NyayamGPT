/**
 * NyayamGPT Message Bubble Component
 * ====================================
 * Premium message bubbles with citations and animations
 */

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  User,
  Scale,
  Copy,
  Check,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  BookOpen,
  Sparkles,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { Message } from "@/hooks/useChatStore";
import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";

interface MessageBubbleProps {
  message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const [copied, setCopied] = useState(false);
  const [showCitations, setShowCitations] = useState(true);

  const isUser = message.role === "user";
  const hasCitations = message.citations && message.citations.length > 0;

  const handleCopy = () => {
    const text = message.content || "";

    void navigator.clipboard
      .writeText(text)
      .then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      })
      .catch((error) => {
        console.error("Failed to copy message", error);
      });
  };

  const formatTime = (date: Date) => {
    return new Intl.DateTimeFormat("en-US", {
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    }).format(new Date(date));
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.4, ease: [0.23, 1, 0.32, 1] }}
      className={cn(
        "flex gap-4 group mb-6",
        isUser ? "flex-row-reverse" : "flex-row"
      )}
    >
      {/* Avatar */}
      <motion.div
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ delay: 0.1, type: "spring", stiffness: 200 }}
        className={cn(
          "flex-shrink-0 w-10 h-10 rounded-2xl flex items-center justify-center shadow-lg",
          isUser
            ? "bg-gradient-to-br from-blue-500 to-indigo-600"
            : "bg-gradient-to-br from-amber-500 to-orange-600"
        )}
      >
        {isUser ? (
          <User className='w-5 h-5 text-white' />
        ) : (
          <Scale className='w-5 h-5 text-white' />
        )}
      </motion.div>

      {/* Message Content */}
      <div
        className={cn(
          "flex-1 max-w-[85%]",
          isUser ? "items-end" : "items-start"
        )}
      >
        {/* Message Bubble */}
        <motion.div
          className={cn(
            "relative rounded-2xl px-6 py-4 shadow-sm overflow-hidden",
            isUser
              ? "bg-gradient-to-br from-blue-600 to-indigo-700 text-white shadow-blue-500/20"
              : "glass border border-white/20 dark:border-white/10"
          )}
          whileHover={{ scale: 1.002 }}
          transition={{ duration: 0.2 }}
        >
          {/* Background Glow for Assistant */}
          {!isUser && (
            <div className='absolute -top-20 -right-20 w-40 h-40 bg-amber-500/10 rounded-full blur-3xl pointer-events-none' />
          )}

          {/* Loading State */}
          {message.isStreaming ? (
            <div className='flex items-center gap-3 py-2'>
              <motion.div className='flex gap-1.5'>
                {[0, 1, 2].map((i) => (
                  <motion.span
                    key={i}
                    className='w-2.5 h-2.5 rounded-full bg-amber-500'
                    animate={{
                      y: [0, -8, 0],
                      opacity: [0.5, 1, 0.5],
                    }}
                    transition={{
                      repeat: Infinity,
                      duration: 0.8,
                      delay: i * 0.15,
                    }}
                  />
                ))}
              </motion.div>
              <span className='text-sm text-muted-foreground animate-pulse'>
                Analyzing legal context...
              </span>
            </div>
          ) : (
            <div
              className={cn(
                "prose prose-lg max-w-none leading-relaxed",
                isUser
                  ? "prose-invert"
                  : "dark:prose-invert prose-headings:text-foreground prose-p:text-foreground/90 prose-strong:text-foreground prose-li:text-foreground/90"
              )}
            >
              <ReactMarkdown
                components={{
                  code({ node, className, children, ...props }) {
                    const match = /language-(\w+)/.exec(className || "");
                    const isInline = !match;
                    return !isInline ? (
                      <div className='relative group/code my-4 rounded-xl overflow-hidden shadow-lg border border-white/10'>
                        <div className='absolute top-0 right-0 p-2 opacity-0 group-hover/code:opacity-100 transition-opacity z-10'>
                          <button
                            aria-label='Copy code block'
                            title='Copy code block'
                            onClick={() => {
                              void navigator.clipboard.writeText(
                                String(children)
                              );
                            }}
                            className='p-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-white/80 transition-colors'
                          >
                            <Copy className='w-4 h-4' />
                          </button>
                        </div>
                        <SyntaxHighlighter
                          style={oneDark}
                          language={match[1]}
                          PreTag='div'
                          className='!bg-[#1e1e1e] !m-0 !p-4'
                          {...(props as any)}
                        >
                          {String(children).replace(/\n$/, "")}
                        </SyntaxHighlighter>
                      </div>
                    ) : (
                      <code
                        className={cn(
                          "px-1.5 py-0.5 rounded-md text-sm font-mono",
                          isUser
                            ? "bg-white/20 text-white"
                            : "bg-amber-100 dark:bg-amber-900/30 text-amber-800 dark:text-amber-200"
                        )}
                        {...props}
                      >
                        {children}
                      </code>
                    );
                  },
                  a({ href, children }) {
                    return (
                      <a
                        href={href}
                        target='_blank'
                        rel='noopener noreferrer'
                        className={cn(
                          "font-medium hover:underline decoration-2 underline-offset-2 transition-colors",
                          isUser
                            ? "text-white decoration-white/50 hover:decoration-white"
                            : "text-amber-600 dark:text-amber-400 decoration-amber-500/30 hover:decoration-amber-500"
                        )}
                      >
                        {children}
                        <ExternalLink className='w-3 h-3 inline-block ml-1 opacity-70' />
                      </a>
                    );
                  },
                  blockquote({ children }) {
                    return (
                      <blockquote
                        className={cn(
                          "border-l-4 pl-4 italic my-4",
                          isUser
                            ? "border-white/30 text-white/90"
                            : "border-amber-500/50 text-muted-foreground bg-amber-50/50 dark:bg-amber-900/10 py-2 pr-2 rounded-r-lg"
                        )}
                      >
                        {children}
                      </blockquote>
                    );
                  },
                }}
              >
                {message.content || ""}
              </ReactMarkdown>
            </div>
          )}

          {/* Copy Button - Only for assistant messages */}
          {!isUser && !message.isStreaming && (
            <motion.button
              onClick={handleCopy}
              className={cn(
                "absolute top-3 right-3 p-2 rounded-xl",
                "opacity-0 group-hover:opacity-100 transition-all duration-200",
                "bg-white/50 dark:bg-black/20 hover:bg-white/80 dark:hover:bg-black/40",
                "backdrop-blur-sm border border-white/20"
              )}
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
              title='Copy to clipboard'
            >
              {copied ? (
                <Check className='w-4 h-4 text-green-600 dark:text-green-400' />
              ) : (
                <Copy className='w-4 h-4 text-muted-foreground' />
              )}
            </motion.button>
          )}
        </motion.div>

        {/* Citations Section */}
        <AnimatePresence>
          {!isUser && hasCitations && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className='mt-3 ml-2'
            >
              <button
                onClick={() => setShowCitations(!showCitations)}
                className='flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors mb-2'
              >
                <Sparkles className='w-4 h-4 text-amber-500' />
                <span>Sources & Citations</span>
                {showCitations ? (
                  <ChevronUp className='w-3 h-3' />
                ) : (
                  <ChevronDown className='w-3 h-3' />
                )}
              </button>

              {showCitations && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className='grid gap-2 sm:grid-cols-2'
                >
                  {message.citations?.map((citation, idx) => {
                    const stripHtml = (html: string) => {
                      if (!html) return "";
                      return html.replace(/<[^>]*>/g, "");
                    };

                    return (
                      <a
                        key={idx}
                        href={citation.url}
                        target='_blank'
                        rel='noopener noreferrer'
                        className={cn(
                          "flex items-start gap-3 p-3 rounded-xl",
                          "glass hover:bg-white/40 dark:hover:bg-white/5",
                          "border border-white/20 transition-all duration-200",
                          "group/citation hover:scale-[1.02] hover:shadow-md"
                        )}
                      >
                        <div className='mt-0.5 p-1.5 rounded-lg bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400'>
                          {citation.context?.includes("Kanoon") ? (
                            <Scale className='w-4 h-4' />
                          ) : (
                            <BookOpen className='w-4 h-4' />
                          )}
                        </div>
                        <div className='flex-1 min-w-0'>
                          <h4 className='text-sm font-medium truncate group-hover/citation:text-amber-600 dark:group-hover/citation:text-amber-400 transition-colors'>
                            {stripHtml(citation.law || citation.act || "")}{" "}
                            {citation.section}
                          </h4>
                          <p className='text-xs text-muted-foreground mt-0.5 line-clamp-2'>
                            {stripHtml(citation.title || "")}
                          </p>
                        </div>
                        <ExternalLink className='w-3 h-3 text-muted-foreground opacity-0 group-hover/citation:opacity-100 transition-opacity' />
                      </a>
                    );
                  })}
                </motion.div>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Timestamp */}
        <div
          className={cn(
            "mt-2 text-xs text-muted-foreground/60 font-medium px-2",
            isUser ? "text-right" : "text-left"
          )}
        >
          {formatTime(new Date(message.timestamp))}
        </div>
      </div>
    </motion.div>
  );
}

export default MessageBubble;
