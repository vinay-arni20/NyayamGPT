import {
  Sun,
  Moon,
  Monitor,
  LogOut,
  PanelLeftClose,
  PanelLeft,
  Settings,
} from "lucide-react";
import { useTheme } from "@/hooks/useTheme";
import { useAuthStore } from "@/hooks/useAuthStore";
import { cn } from "@/lib/utils";
import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";

interface ChatHeaderProps {
  onMenuClick: () => void;
  showMenuButton?: boolean;
  sidebarOpen?: boolean;
}

export function ChatHeader({
  onMenuClick,
  showMenuButton = true,
  sidebarOpen = false,
}: ChatHeaderProps) {
  const { theme, setTheme } = useTheme();
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const [showThemeMenu, setShowThemeMenu] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const themeMenuRef = useRef<HTMLDivElement>(null);
  const userMenuRef = useRef<HTMLDivElement>(null);

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        themeMenuRef.current &&
        !themeMenuRef.current.contains(event.target as Node)
      ) {
        setShowThemeMenu(false);
      }
      if (
        userMenuRef.current &&
        !userMenuRef.current.contains(event.target as Node)
      ) {
        setShowUserMenu(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  const themeOptions = [
    { value: "light" as const, label: "Light", icon: Sun },
    { value: "dark" as const, label: "Dark", icon: Moon },
    { value: "system" as const, label: "System", icon: Monitor },
  ];

  return (
    <header className='sticky top-0 z-30 flex items-center justify-between px-6 py-4 bg-transparent pointer-events-none'>
      <div className='flex items-center gap-3 pointer-events-auto'>
        {showMenuButton && (
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={onMenuClick}
            className={cn(
              "p-2.5 rounded-xl transition-all duration-200",
              "bg-white/50 dark:bg-black/20 backdrop-blur-md",
              "border border-white/20 dark:border-white/10",
              "text-muted-foreground hover:text-foreground",
              "shadow-sm hover:shadow-md"
            )}
            aria-label={sidebarOpen ? "Close sidebar" : "Open sidebar"}
          >
            {sidebarOpen ? (
              <PanelLeftClose className='w-5 h-5' />
            ) : (
              <PanelLeft className='w-5 h-5' />
            )}
          </motion.button>
        )}
      </div>

      {/* Right Actions */}
      <div className='flex items-center gap-3 pointer-events-auto'>
        {/* Theme Switcher */}
        <div className='relative' ref={themeMenuRef}>
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => setShowThemeMenu(!showThemeMenu)}
            className={cn(
              "p-2.5 rounded-xl transition-all duration-200",
              "bg-white/50 dark:bg-black/20 backdrop-blur-md",
              "border border-white/20 dark:border-white/10",
              "text-muted-foreground hover:text-foreground",
              "shadow-sm hover:shadow-md"
            )}
          >
            <Sun className='w-5 h-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0' />
            <Moon className='absolute top-2.5 left-2.5 w-5 h-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100' />
          </motion.button>

          <AnimatePresence>
            {showThemeMenu && (
              <motion.div
                initial={{ opacity: 0, y: 10, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 10, scale: 0.95 }}
                className={cn(
                  "absolute right-0 mt-2 w-40 rounded-xl overflow-hidden",
                  "glass border border-white/20 dark:border-white/10",
                  "shadow-xl shadow-black/5"
                )}
              >
                <div className='p-1'>
                  {themeOptions.map((option) => (
                    <button
                      key={option.value}
                      onClick={() => {
                        setTheme(option.value);
                        setShowThemeMenu(false);
                      }}
                      className={cn(
                        "w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors",
                        theme === option.value
                          ? "bg-amber-500/10 text-amber-600 dark:text-amber-400"
                          : "text-muted-foreground hover:bg-secondary/50 hover:text-foreground"
                      )}
                    >
                      <option.icon className='w-4 h-4' />
                      {option.label}
                    </button>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* User Menu */}
        <div className='relative' ref={userMenuRef}>
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => setShowUserMenu(!showUserMenu)}
            className={cn(
              "p-1 rounded-xl transition-all duration-200",
              "bg-white/50 dark:bg-black/20 backdrop-blur-md",
              "border border-white/20 dark:border-white/10",
              "shadow-sm hover:shadow-md"
            )}
          >
            <div className='w-8 h-8 rounded-lg bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center text-white font-medium text-sm'>
              {user?.full_name?.[0] || "U"}
            </div>
          </motion.button>

          <AnimatePresence>
            {showUserMenu && (
              <motion.div
                initial={{ opacity: 0, y: 10, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 10, scale: 0.95 }}
                className={cn(
                  "absolute right-0 mt-2 w-56 rounded-xl overflow-hidden",
                  "glass border border-white/20 dark:border-white/10",
                  "shadow-xl shadow-black/5"
                )}
              >
                <div className='p-4 border-b border-white/10'>
                  <p className='font-medium truncate'>
                    {user?.full_name || "User"}
                  </p>
                  <p className='text-xs text-muted-foreground truncate'>
                    {user?.email || "user@example.com"}
                  </p>
                </div>
                <div className='p-1'>
                  <button
                    onClick={() => navigate("/settings")}
                    className='w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-muted-foreground hover:bg-secondary/50 hover:text-foreground transition-colors'
                  >
                    <Settings className='w-4 h-4' />
                    Settings
                  </button>
                  <button
                    onClick={handleLogout}
                    className='w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-red-500 hover:bg-red-500/10 transition-colors'
                  >
                    <LogOut className='w-4 h-4' />
                    Log out
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </header>
  );
}
