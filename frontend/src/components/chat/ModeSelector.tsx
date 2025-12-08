/**
 * NyayamGPT Mode Selector Component
 * ==================================
 * Premium mode selector with glassmorphism and animations
 */

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  User,
  Scale,
  Zap,
  Globe,
  BookOpen,
  Info,
  ChevronDown,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { modeConfig, type ChatMode } from "@/styles/theme";

const iconMap = {
  User,
  Scale,
  Zap,
  Globe,
  BookOpen,
};

interface ModeSelectorProps {
  activeMode: ChatMode;
  onModeChange: (mode: ChatMode) => void;
  className?: string;
  compact?: boolean;
}

export function ModeSelector({
  activeMode,
  onModeChange,
  className,
  compact = false,
}: ModeSelectorProps) {
  const [showInfo, setShowInfo] = useState<ChatMode | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);

  const modes = Object.values(modeConfig);
  const activeModeConfig = modeConfig[activeMode];
  const ActiveIcon = iconMap[activeModeConfig.icon as keyof typeof iconMap];

  if (compact) {
    return (
      <div className={cn("relative", className)}>
        {/* Compact Dropdown */}
        <motion.button
          onClick={() => setIsExpanded(!isExpanded)}
          className={cn(
            "flex items-center gap-2 px-3 py-2 rounded-lg",
            "bg-white/10 dark:bg-white/5 backdrop-blur-md",
            "border border-white/20 dark:border-white/10",
            "hover:bg-white/20 dark:hover:bg-white/10",
            "transition-all duration-200"
          )}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          <ActiveIcon
            className='w-4 h-4'
            style={{ color: activeModeConfig.color }}
          />
          <span className='text-sm font-medium text-foreground'>
            {activeModeConfig.name}
          </span>
          <ChevronDown
            className={cn(
              "w-4 h-4 text-muted-foreground transition-transform duration-200",
              isExpanded && "rotate-180"
            )}
          />
        </motion.button>

        <AnimatePresence>
          {isExpanded && (
            <motion.div
              initial={{ opacity: 0, y: -10, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -10, scale: 0.95 }}
              transition={{ duration: 0.15 }}
              className={cn(
                "absolute top-full left-0 mt-2 z-50",
                "min-w-[240px] p-2 rounded-xl",
                "bg-white/90 dark:bg-gray-900/90 backdrop-blur-xl",
                "border border-white/20 dark:border-white/10",
                "shadow-xl"
              )}
            >
              {modes.map((mode) => {
                const Icon = iconMap[mode.icon as keyof typeof iconMap];
                const isActive = activeMode === mode.id;

                return (
                  <motion.button
                    key={mode.id}
                    onClick={() => {
                      onModeChange(mode.id as ChatMode);
                      setIsExpanded(false);
                    }}
                    className={cn(
                      "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg",
                      "transition-all duration-200",
                      isActive
                        ? "bg-gradient-to-r from-white/20 to-transparent"
                        : "hover:bg-white/10 dark:hover:bg-white/5"
                    )}
                    whileHover={{ x: 4 }}
                    whileTap={{ scale: 0.98 }}
                  >
                    <div
                      className={cn(
                        "p-1.5 rounded-lg",
                        isActive
                          ? "bg-white/20 mode-selector-glow"
                          : "bg-white/10 dark:bg-white/5"
                      )}
                      {...(isActive && { style: { color: `${mode.color}40` } })}
                    >
                      <Icon
                        className='w-4 h-4'
                        {...{ style: { color: mode.color } }}
                      />
                    </div>
                    <div className='flex-1 text-left'>
                      <p className='text-sm font-medium text-foreground'>
                        {mode.name}
                      </p>
                      <p className='text-xs text-muted-foreground line-clamp-1'>
                        {mode.description}
                      </p>
                    </div>
                    {isActive && (
                      <motion.div
                        layoutId='activeIndicator'
                        className='w-1.5 h-1.5 rounded-full'
                        style={{ backgroundColor: mode.color }}
                      />
                    )}
                  </motion.button>
                );
              })}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    );
  }

  return (
    <div className={cn("relative", className)}>
      {/* Full Mode Selector */}
      <div
        className={cn(
          "flex items-center gap-1 p-1 rounded-2xl overflow-x-auto",
          "bg-white/10 dark:bg-white/5 backdrop-blur-md",
          "border border-white/20 dark:border-white/10",
          "scrollbar-thin scrollbar-thumb-white/20"
        )}
      >
        {modes.map((mode) => {
          const Icon = iconMap[mode.icon as keyof typeof iconMap];
          const isActive = activeMode === mode.id;

          return (
            <motion.button
              key={mode.id}
              onClick={() => onModeChange(mode.id as ChatMode)}
              onMouseEnter={() => setShowInfo(mode.id as ChatMode)}
              onMouseLeave={() => setShowInfo(null)}
              className={cn(
                "relative flex items-center gap-2 px-4 py-2.5 rounded-xl",
                "whitespace-nowrap transition-all duration-200",
                "min-w-max",
                isActive
                  ? "text-white"
                  : "text-muted-foreground hover:text-foreground"
              )}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              {isActive && (
                <motion.div
                  layoutId='activeModeBackground'
                  className='absolute inset-0 rounded-xl'
                  style={{
                    background: mode.gradient,
                    boxShadow: `0 4px 20px ${mode.color}40`,
                  }}
                  transition={{
                    type: "spring",
                    stiffness: 300,
                    damping: 30,
                  }}
                />
              )}
              <Icon
                className={cn(
                  "relative z-10 w-4 h-4 transition-colors",
                  isActive ? "text-white" : ""
                )}
                style={{ color: isActive ? "white" : mode.color }}
              />
              <span className='relative z-10 text-sm font-medium'>
                {mode.name}
              </span>
            </motion.button>
          );
        })}
      </div>

      {/* Info Tooltip */}
      <AnimatePresence>
        {showInfo && (
          <motion.div
            initial={{ opacity: 0, y: 10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 10, scale: 0.95 }}
            transition={{ duration: 0.15 }}
            className={cn(
              "absolute top-full left-1/2 -translate-x-1/2 mt-3 z-50",
              "px-4 py-3 rounded-xl max-w-xs",
              "bg-white/90 dark:bg-gray-900/90 backdrop-blur-xl",
              "border border-white/20 dark:border-white/10",
              "shadow-xl"
            )}
          >
            <div className='flex items-start gap-3'>
              <Info
                className='w-4 h-4 mt-0.5 flex-shrink-0'
                style={{ color: modeConfig[showInfo].color }}
              />
              <div>
                <p className='text-sm font-medium text-foreground'>
                  {modeConfig[showInfo].name}
                </p>
                <p className='text-xs text-muted-foreground mt-1'>
                  {modeConfig[showInfo].description}
                </p>
              </div>
            </div>
            <div className='tooltip-arrow' />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// Mobile-optimized horizontal scrollable pills
export function ModeSelectorMobile({
  activeMode,
  onModeChange,
  className,
}: Omit<ModeSelectorProps, "compact">) {
  const modes = Object.values(modeConfig);

  return (
    <div
      className={cn(
        "flex gap-2 overflow-x-auto py-2 px-1 -mx-1",
        "scrollbar-none",
        className
      )}
    >
      {modes.map((mode) => {
        const Icon = iconMap[mode.icon as keyof typeof iconMap];
        const isActive = activeMode === mode.id;

        return (
          <motion.button
            key={mode.id}
            onClick={() => onModeChange(mode.id as ChatMode)}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-full",
              "whitespace-nowrap transition-all duration-200",
              "text-xs font-medium",
              isActive
                ? "text-white shadow-lg"
                : "bg-white/10 dark:bg-white/5 text-muted-foreground border border-white/10"
            )}
            style={{
              background: isActive ? mode.gradient : undefined,
              boxShadow: isActive ? `0 4px 12px ${mode.color}30` : undefined,
            }}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            <Icon className='w-3.5 h-3.5' />
            <span>{mode.name.split(" ")[0]}</span>
          </motion.button>
        );
      })}
    </div>
  );
}

export default ModeSelector;
