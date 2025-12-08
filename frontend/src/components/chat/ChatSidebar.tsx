import * as React from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  MessageSquarePlus,
  Trash2,
  ChevronLeft,
  Scale,
  MessageCircle,
  Search,
  History,
  MoreHorizontal,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/Button";
import { useChatStore } from "@/hooks/useChatStore";

interface ChatSidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export function ChatSidebar({ isOpen, onClose }: ChatSidebarProps) {
  const [searchQuery, setSearchQuery] = React.useState("");

  const {
    sessions,
    currentSessionId,
    createNewSession,
    setCurrentSession,
    deleteSession,
    loadSessionWithMessages,
  } = useChatStore();

  // Filter sessions by search query
  const filteredSessions = React.useMemo(() => {
    if (!searchQuery.trim()) return sessions;
    const query = searchQuery.toLowerCase();
    return sessions.filter(
      (session) =>
        (session.title && session.title.toLowerCase().includes(query)) ||
        (session.messages &&
          session.messages.some(
            (m) => m.content && m.content.toLowerCase().includes(query)
          ))
    );
  }, [sessions, searchQuery]);

  // Group sessions by date
  const groupedSessions = React.useMemo(() => {
    const groups: { label: string; sessions: typeof sessions }[] = [];
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    const lastWeek = new Date(today);
    lastWeek.setDate(lastWeek.getDate() - 7);
    const lastMonth = new Date(today);
    lastMonth.setMonth(lastMonth.getMonth() - 1);

    const todaySessions: typeof sessions = [];
    const yesterdaySessions: typeof sessions = [];
    const lastWeekSessions: typeof sessions = [];
    const lastMonthSessions: typeof sessions = [];
    const olderSessions: typeof sessions = [];

    filteredSessions.forEach((session) => {
      const sessionDate = new Date(session.updatedAt);
      if (sessionDate.toDateString() === today.toDateString()) {
        todaySessions.push(session);
      } else if (sessionDate.toDateString() === yesterday.toDateString()) {
        yesterdaySessions.push(session);
      } else if (sessionDate > lastWeek) {
        lastWeekSessions.push(session);
      } else if (sessionDate > lastMonth) {
        lastMonthSessions.push(session);
      } else {
        olderSessions.push(session);
      }
    });

    if (todaySessions.length)
      groups.push({ label: "Today", sessions: todaySessions });
    if (yesterdaySessions.length)
      groups.push({ label: "Yesterday", sessions: yesterdaySessions });
    if (lastWeekSessions.length)
      groups.push({ label: "Previous 7 Days", sessions: lastWeekSessions });
    if (lastMonthSessions.length)
      groups.push({ label: "Previous 30 Days", sessions: lastMonthSessions });
    if (olderSessions.length)
      groups.push({ label: "Older", sessions: olderSessions });

    return groups;
  }, [filteredSessions]);

  const handleNewChat = () => {
    createNewSession();
  };

  const handleSelectSession = async (sessionId: string) => {
    // Load messages if not already loaded
    const session = sessions.find((s) => s.id === sessionId);
    if (session && session.messages.length === 0) {
      await loadSessionWithMessages(sessionId);
    } else {
      setCurrentSession(sessionId);
    }
    // Close on mobile
    if (window.innerWidth < 1024) {
      onClose();
    }
  };

  const handleDeleteSession = (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation();
    deleteSession(sessionId);
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop for mobile */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className='fixed inset-0 z-40 bg-black/50 backdrop-blur-sm lg:hidden'
            onClick={onClose}
          />
        )}
      </AnimatePresence>

      {/* Sidebar */}
      <motion.aside
        initial={{ width: 0, opacity: 0 }}
        animate={{ width: 300, opacity: 1 }}
        exit={{ width: 0, opacity: 0 }}
        transition={{ type: "spring", damping: 25, stiffness: 200 }}
        className={cn(
          "h-full flex flex-col overflow-hidden",
          "fixed left-0 top-0 z-50 lg:relative lg:z-0",
          "bg-white/80 dark:bg-black/80 backdrop-blur-xl",
          "border-r border-white/20 dark:border-white/10"
        )}
        style={{ width: 300 }}
      >
        {/* Header */}
        <div className='flex items-center justify-between p-4 border-b border-white/10'>
          <div className='flex items-center gap-3'>
            <div className='p-2 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 shadow-lg shadow-orange-500/20'>
              <Scale className='w-5 h-5 text-white' />
            </div>
            <div>
              <h1 className='font-bold text-lg tracking-tight'>NyayamGPT</h1>
              <p className='text-xs text-muted-foreground font-medium'>
                Legal Intelligence
              </p>
            </div>
          </div>
          <Button
            variant='ghost'
            size='icon-sm'
            onClick={onClose}
            className='lg:hidden text-muted-foreground hover:bg-white/10'
          >
            <ChevronLeft className='w-5 h-5' />
          </Button>
        </div>

        {/* New Chat Button */}
        <div className='p-4'>
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={handleNewChat}
            className={cn(
              "w-full flex items-center gap-3 px-4 py-3 rounded-xl",
              "bg-gradient-to-r from-amber-500 to-orange-600",
              "text-white font-medium shadow-lg shadow-orange-500/25",
              "hover:shadow-orange-500/40 transition-all duration-200"
            )}
          >
            <MessageSquarePlus className='w-5 h-5' />
            <span>New Chat</span>
          </motion.button>
        </div>

        {/* Search */}
        <div className='px-4 pb-2'>
          <div className='relative group'>
            <Search className='absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground group-focus-within:text-amber-500 transition-colors' />
            <input
              type='text'
              placeholder='Search conversations...'
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className={cn(
                "w-full pl-10 pr-4 py-2.5 text-sm rounded-xl",
                "bg-secondary/50 border border-transparent",
                "focus:bg-background focus:border-amber-500/50 focus:ring-2 focus:ring-amber-500/20",
                "transition-all duration-200 outline-none",
                "placeholder:text-muted-foreground/70"
              )}
            />
          </div>
        </div>

        {/* Chat List */}
        <div className='flex-1 overflow-y-auto px-3 pb-3 scrollbar-thin scrollbar-thumb-secondary scrollbar-track-transparent'>
          {groupedSessions.length > 0 ? (
            <div className='space-y-6 mt-2'>
              {groupedSessions.map((group) => (
                <div key={group.label}>
                  <p className='text-xs font-semibold text-muted-foreground/60 px-3 mb-2 uppercase tracking-wider'>
                    {group.label}
                  </p>
                  <div className='space-y-1'>
                    <AnimatePresence mode='popLayout'>
                      {group.sessions.map((session) => (
                        <motion.div
                          key={session.id}
                          layout
                          initial={{ opacity: 0, x: -20 }}
                          animate={{ opacity: 1, x: 0 }}
                          exit={{ opacity: 0, x: -20 }}
                          className='group relative'
                        >
                          <button
                            onClick={() => handleSelectSession(session.id)}
                            className={cn(
                              "w-full text-left px-3 py-2.5 rounded-xl transition-all duration-200",
                              "hover:bg-secondary/80",
                              currentSessionId === session.id
                                ? "bg-secondary shadow-sm ring-1 ring-black/5 dark:ring-white/5"
                                : "text-muted-foreground"
                            )}
                          >
                            <div className='flex items-start gap-3'>
                              <MessageCircle
                                className={cn(
                                  "w-4 h-4 mt-0.5 flex-shrink-0 transition-colors",
                                  currentSessionId === session.id
                                    ? "text-amber-500"
                                    : "text-muted-foreground/50 group-hover:text-muted-foreground"
                                )}
                              />
                              <div className='flex-1 min-w-0'>
                                <h3
                                  className={cn(
                                    "text-sm font-medium truncate transition-colors",
                                    currentSessionId === session.id
                                      ? "text-foreground"
                                      : "text-muted-foreground group-hover:text-foreground"
                                  )}
                                >
                                  {session.title || "New Conversation"}
                                </h3>
                                <p className='text-xs text-muted-foreground/60 truncate mt-0.5'>
                                  {session.messages[session.messages.length - 1]
                                    ?.content || "No messages yet"}
                                </p>
                              </div>
                            </div>
                          </button>

                          {/* Delete Button */}
                          <div className='absolute right-2 top-1/2 -translate-y-1/2 opacity-100 lg:opacity-0 lg:group-hover:opacity-100 transition-opacity'>
                            <button
                              onClick={(e) =>
                                handleDeleteSession(e, session.id)
                              }
                              className='p-1.5 rounded-lg text-muted-foreground hover:text-red-500 hover:bg-red-500/10 transition-colors'
                              title='Delete chat'
                            >
                              <Trash2 className='w-4 h-4' />
                            </button>
                          </div>
                        </motion.div>
                      ))}
                    </AnimatePresence>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className='flex flex-col items-center justify-center h-full text-center px-4 text-muted-foreground/60'>
              <div className='p-4 rounded-full bg-secondary/50 mb-4'>
                <History className='w-8 h-8 opacity-50' />
              </div>
              <p className='text-sm font-medium'>No conversations yet</p>
              <p className='text-xs mt-1'>Start a new chat to begin</p>
            </div>
          )}
        </div>

        {/* User Profile / Footer */}
        <div className='p-4 border-t border-white/10 bg-white/5'>
          <button className='w-full flex items-center gap-3 p-2 rounded-xl hover:bg-white/5 transition-colors group'>
            <div className='w-8 h-8 rounded-full bg-gradient-to-br from-slate-700 to-slate-900 flex items-center justify-center text-white font-medium text-xs'>
              US
            </div>
            <div className='flex-1 text-left'>
              <p className='text-sm font-medium text-foreground'>User</p>
              <p className='text-xs text-muted-foreground'>Free Plan</p>
            </div>
            <MoreHorizontal className='w-4 h-4 text-muted-foreground group-hover:text-foreground transition-colors' />
          </button>
        </div>
      </motion.aside>
    </>
  );
}
