import { useState, useRef, useEffect, KeyboardEvent } from "react";
import { motion } from "framer-motion";
import { Send, Square } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/Button";

interface ChatInputProps {
  onSend: (message: string) => void;
  onStop?: () => void;
  isLoading: boolean;
  placeholder?: string;
  variant?: "bottom" | "centered";
  selectedLanguage?: string;
  onLanguageChange?: (lang: string) => void;
}

export function ChatInput({
  onSend,
  onStop,
  isLoading,
  placeholder = "Ask anything...",
  variant = "bottom",
}: ChatInputProps) {
  const [message, setMessage] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    }
  }, [message]);

  const handleSubmit = () => {
    if (isLoading && onStop) {
      onStop();
      return;
    }
    const trimmedMessage = message.trim();
    if (trimmedMessage && !isLoading) {
      onSend(trimmedMessage);
      setMessage("");
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
      }
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const isCentered = variant === "centered";

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        isCentered
          ? "w-full"
          : "sticky bottom-0 bg-gradient-to-t from-background via-background to-transparent pt-6 pb-4 px-4"
      )}
    >
      <div className={cn("mx-auto", isCentered ? "w-full" : "max-w-3xl")}>
        <div
          className={cn(
            "relative flex items-end gap-2 p-2 transition-all duration-200",
            "bg-background border border-border/50",
            "focus-within:border-primary/50 focus-within:ring-2 focus-within:ring-primary/10",
            isCentered
              ? "rounded-full shadow-sm hover:shadow-md px-4 py-3"
              : "rounded-2xl shadow-lg"
          )}
        >
          <textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={isLoading}
            rows={1}
            className={cn(
              "flex-1 resize-none bg-transparent px-2 py-2 text-base",
              "placeholder:text-muted-foreground/70",
              "focus:outline-none disabled:opacity-50",
              "max-h-[200px] scrollbar-thin"
            )}
          />

          <Button
            onClick={handleSubmit}
            disabled={!message.trim() && !isLoading}
            size='icon'
            variant={isCentered ? "ghost" : "gradient"}
            className={cn(
              "flex-shrink-0 rounded-full transition-all duration-200",
              !message.trim() && !isLoading && "opacity-50",
              isCentered && "hover:bg-muted"
            )}
          >
            {isLoading ? (
              <Square className='w-5 h-5 fill-current text-white' />
            ) : (
              <Send
                className={cn(
                  "w-5 h-5",
                  isCentered ? "text-muted-foreground" : "text-white"
                )}
              />
            )}
          </Button>
        </div>

        {!isCentered && (
          <p className='text-center text-[10px] text-muted-foreground mt-2 opacity-70'>
            NyayamGPT can make mistakes. Please verify important information.
          </p>
        )}
      </div>
    </motion.div>
  );
}
