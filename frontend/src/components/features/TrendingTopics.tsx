/**
 * NyayamGPT Trending Topics Component
 * =====================================
 * Display trending legal topics with animations
 */

import { motion } from "framer-motion";
import { TrendingUp, ArrowRight, Scale, FileText, Shield } from "lucide-react";
import { cn } from "@/lib/utils";

interface TrendingTopicsProps {
  onTopicClick: (topic: string) => void;
  className?: string;
}

const trendingTopics = [
  {
    id: 1,
    title: "498A IPC - Dowry Harassment",
    query:
      "What is Section 498A IPC and what are the punishments for dowry harassment?",
    icon: Shield,
    category: "Criminal",
  },
  {
    id: 2,
    title: "Section 138 - Cheque Bounce",
    query:
      "Explain Section 138 of Negotiable Instruments Act and the procedure for cheque bounce cases",
    icon: FileText,
    category: "Commercial",
  },
  {
    id: 3,
    title: "Motor Vehicle Act Fines",
    query: "What are the traffic violation fines under Motor Vehicle Act 2019?",
    icon: Scale,
    category: "Traffic",
  },
  {
    id: 4,
    title: "RTI Application Process",
    query:
      "How to file an RTI application and what information can be requested?",
    icon: FileText,
    category: "Civil Rights",
  },
  {
    id: 5,
    title: "Consumer Protection Rights",
    query:
      "What are my rights under Consumer Protection Act 2019 for defective products?",
    icon: Shield,
    category: "Consumer",
  },
  {
    id: 6,
    title: "Bail Provisions in India",
    query:
      "Explain the bail provisions under CrPC and when anticipatory bail can be granted",
    icon: Scale,
    category: "Criminal",
  },
];

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      type: "spring" as const,
      stiffness: 300,
      damping: 24,
    },
  },
};

export function TrendingTopics({
  onTopicClick,
  className,
}: TrendingTopicsProps) {
  return (
    <div className={cn("w-full", className)}>
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className='flex items-center gap-2 mb-6 px-1'
      >
        <div className='p-1.5 rounded-lg bg-amber-500/10 text-amber-600 dark:text-amber-400'>
          <TrendingUp className='w-4 h-4' />
        </div>
        <h3 className='text-sm font-semibold text-muted-foreground uppercase tracking-wider'>
          Trending Legal Topics
        </h3>
      </motion.div>

      {/* Grid */}
      <motion.div
        variants={containerVariants}
        initial='hidden'
        animate='visible'
        className='grid grid-cols-1 md:grid-cols-2 gap-4'
      >
        {trendingTopics.map((topic) => (
          <motion.button
            key={topic.id}
            variants={itemVariants}
            onClick={() => onTopicClick(topic.query)}
            className={cn(
              "group relative flex items-start gap-4 p-4 rounded-2xl text-left transition-all duration-300",
              "glass border border-white/20 dark:border-white/10",
              "hover:bg-white/40 dark:hover:bg-white/5 hover:scale-[1.02] hover:shadow-lg"
            )}
            whileHover={{ y: -2 }}
            whileTap={{ scale: 0.98 }}
          >
            <div
              className={cn(
                "p-3 rounded-xl transition-colors duration-300",
                "bg-secondary/50 group-hover:bg-amber-500/10",
                "text-muted-foreground group-hover:text-amber-600 dark:group-hover:text-amber-400"
              )}
            >
              <topic.icon className='w-5 h-5' />
            </div>

            <div className='flex-1 min-w-0'>
              <div className='flex items-center justify-between gap-2 mb-1'>
                <span className='text-xs font-medium text-muted-foreground/60 uppercase tracking-wider'>
                  {topic.category}
                </span>
                <ArrowRight className='w-3 h-3 text-muted-foreground/40 opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-300' />
              </div>
              <h4 className='font-medium text-foreground group-hover:text-amber-600 dark:group-hover:text-amber-400 transition-colors line-clamp-1'>
                {topic.title}
              </h4>
              <p className='text-sm text-muted-foreground mt-1 line-clamp-2 group-hover:text-muted-foreground/80'>
                {topic.query}
              </p>
            </div>
          </motion.button>
        ))}
      </motion.div>
    </div>
  );
}
