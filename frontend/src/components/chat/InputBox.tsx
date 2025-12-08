/**
 * NyayamGPT Premium Input Box
 * ============================
 * Dynamic input with mode-specific placeholders
 */

import { useState, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Paperclip, Loader2, Mic, MicOff, Square } from "lucide-react";
import { cn } from "@/lib/utils";
import { type ChatMode } from "@/styles/theme";

interface InputBoxProps {
  mode?: ChatMode; // Optional now, ignored
  onSend: (message: string) => void;
  onStop?: () => void;
  isLoading?: boolean;
  maxLength?: number;
  showAttachment?: boolean;
  showVoice?: boolean;
}

export function InputBox({
  onSend,
  onStop,
  isLoading = false,
  maxLength = 2000,
  showAttachment = false,
  showVoice = false,
}: InputBoxProps) {
  const [message, setMessage] = useState("");
  const [isFocused, setIsFocused] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const charCount = message.length;
  const isNearLimit = charCount > maxLength * 0.8;
  const isOverLimit = charCount > maxLength;
  const canSend = message.trim().length > 0 && !isLoading && !isOverLimit;

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    }
  }, [message]);

  // Handle keyboard shortcuts
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      // Shift+Enter to send (or Enter without Shift on desktop)
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        if (canSend) {
          handleSend();
        }
      }
    },
    [canSend, message]
  );

  const handleSend = () => {
    if (isLoading && onStop) {
      onStop();
      return;
    }
    if (!canSend) return;
    onSend(message.trim());
    setMessage("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleVoiceToggle = () => {
    setIsRecording(!isRecording);
    // Voice recording logic would go here
  };

  return (
    <motion.div
      className={cn(
        "relative rounded-[2rem] transition-all duration-300",
        "glass-input",
        isFocused ? "shadow-2xl ring-2 ring-primary/20" : "shadow-lg"
      )}
      initial={{ y: 20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
    >
      <div className='flex items-end gap-2 p-2'>
        {/* Attachment Button (Optional) */}
        {showAttachment && (
          <button
            className='p-3 rounded-full text-muted-foreground hover:bg-secondary/50 transition-colors'
            title='Attach file'
          >
            <Paperclip className='w-5 h-5' />
          </button>
        )}

        {/* Text Area */}
        <textarea
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          placeholder='Ask anything about Indian Law...'
          className={cn(
            "flex-1 bg-transparent border-none focus:ring-0 resize-none",
            "max-h-[200px] min-h-[56px] py-4 px-2",
            "text-base md:text-lg placeholder:text-muted-foreground/70",
            "scrollbar-thin scrollbar-thumb-gray-300 dark:scrollbar-thumb-gray-700"
          )}
          rows={1}
        />

        {/* Action Buttons */}
        <div className='flex items-center gap-2 pb-1.5 pr-1.5'>
          {/* Voice Input */}
          {showVoice && (
            <motion.button
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
              onClick={handleVoiceToggle}
              className={cn(
                "p-3 rounded-full transition-colors",
                isRecording
                  ? "bg-red-500/10 text-red-500 animate-pulse"
                  : "text-muted-foreground hover:bg-secondary/50"
              )}
            >
              {isRecording ? (
                <MicOff className='w-5 h-5' />
              ) : (
                <Mic className='w-5 h-5' />
              )}
            </motion.button>
          )}

          {/* Send Button */}
          <AnimatePresence mode='wait'>
            {isLoading ? (
              onStop ? (
                <motion.button
                  key='stop'
                  initial={{ scale: 0, rotate: -180 }}
                  animate={{ scale: 1, rotate: 0 }}
                  exit={{ scale: 0, rotate: 180 }}
                  onClick={onStop}
                  className='p-3 rounded-full bg-secondary hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-colors'
                >
                  <Square className='w-5 h-5 fill-current' />
                </motion.button>
              ) : (
                <motion.div
                  key='loading'
                  initial={{ scale: 0, rotate: -180 }}
                  animate={{ scale: 1, rotate: 0 }}
                  exit={{ scale: 0, rotate: 180 }}
                  className='p-3 rounded-full bg-secondary'
                >
                  <Loader2 className='w-5 h-5 animate-spin text-muted-foreground' />
                </motion.div>
              )
            ) : (
              <motion.button
                key='send'
                onClick={handleSend}
                disabled={!canSend}
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.8, opacity: 0 }}
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
                className={cn(
                  "p-3 rounded-full transition-all duration-300",
                  canSend
                    ? "bg-primary text-primary-foreground shadow-lg shadow-primary/25"
                    : "bg-secondary text-muted-foreground opacity-50 cursor-not-allowed"
                )}
              >
                <Send className='w-5 h-5' />
              </motion.button>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Character Count & Limit Warning */}
      <AnimatePresence>
        {isNearLimit && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            className={cn(
              "absolute -top-8 right-4 text-xs font-medium px-2 py-1 rounded-md glass",
              isOverLimit ? "text-destructive" : "text-amber-500"
            )}
          >
            {charCount} / {maxLength}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

export default InputBox;
