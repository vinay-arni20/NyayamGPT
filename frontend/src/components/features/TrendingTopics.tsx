/**
 * NyayamGPT Suggestion Prompts Component
 * ========================================
 * ChatGPT-style suggestion chips for the home page.
 * Displays contextual, categorized prompt suggestions
 * that reflect the full breadth of NyayamGPT's capabilities.
 */

import { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowRight,
  Scale,
  FileText,
  Shield,
  Gavel,
  Search,
  Car,
  Users,
  Globe,
  Lightbulb,
  Shuffle,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface TrendingTopicsProps {
  onTopicClick: (topic: string) => void;
  className?: string;
}

// ---------------------------------------------------------------------------
// Suggestion data – covers every major capability of NyayamGPT
// ---------------------------------------------------------------------------

interface Suggestion {
  id: number;
  label: string;
  query: string;
  icon: typeof Scale;
  category: string;
}

const allSuggestions: Suggestion[] = [
  // Criminal Law (BNS / BNSS / BSA — 2023 codes)
  {
    id: 1,
    label: "Punishment for theft under BNS",
    query: "What is the punishment for theft under Bharatiya Nyaya Sanhita (BNS)?",
    icon: Gavel,
    category: "Criminal",
  },
  {
    id: 2,
    label: "Difference between IPC and BNS",
    query: "What are the key differences between IPC and the new Bharatiya Nyaya Sanhita 2023?",
    icon: Scale,
    category: "Criminal",
  },
  {
    id: 3,
    label: "FIR filing process under BNSS",
    query: "How to file an FIR under the new BNSS? What is the procedure?",
    icon: FileText,
    category: "Procedure",
  },
  {
    id: 4,
    label: "Bail provisions explained",
    query: "Explain the bail provisions under BNSS and when can anticipatory bail be granted?",
    icon: Gavel,
    category: "Criminal",
  },

  // Cyber Crime
  {
    id: 5,
    label: "Cyber fraud complaint process",
    query: "How to file a cyber fraud complaint in India? What sections of IT Act apply?",
    icon: Globe,
    category: "Cyber",
  },
  {
    id: 6,
    label: "Online harassment laws",
    query: "What are the legal remedies for online harassment and cyberstalking in India?",
    icon: Shield,
    category: "Cyber",
  },

  // Domestic & Women
  {
    id: 7,
    label: "Dowry harassment remedies",
    query: "What legal actions can be taken against dowry harassment? Explain Section 498A and Dowry Prohibition Act.",
    icon: Shield,
    category: "Women",
  },
  {
    id: 8,
    label: "Domestic violence protection",
    query: "What protections are available under the Domestic Violence Act? How to get a protection order?",
    icon: Users,
    category: "Women",
  },

  // Consumer & Civil
  {
    id: 9,
    label: "Consumer complaint for defective product",
    query: "How to file a consumer complaint for a defective product under Consumer Protection Act 2019?",
    icon: FileText,
    category: "Consumer",
  },
  {
    id: 10,
    label: "RTI application guide",
    query: "How to file an RTI application? What information can be requested under Right to Information Act?",
    icon: Search,
    category: "Civil Rights",
  },

  // Motor Vehicles & Traffic
  {
    id: 11,
    label: "Traffic violation fines 2019",
    query: "What are the traffic violation fines under Motor Vehicle Amendment Act 2019?",
    icon: Car,
    category: "Traffic",
  },
  {
    id: 12,
    label: "Accident compensation claim",
    query: "How to claim compensation for a road accident under Motor Vehicles Act?",
    icon: Car,
    category: "Traffic",
  },

  // Special Laws
  {
    id: 13,
    label: "POCSO Act explained",
    query: "What are the key provisions and penalties under the POCSO Act for offenses against children?",
    icon: Shield,
    category: "Special Law",
  },
  {
    id: 14,
    label: "NDPS Act drug offenses",
    query: "What are the penalties for drug possession and trafficking under the NDPS Act?",
    icon: Gavel,
    category: "Special Law",
  },

  // Constitutional
  {
    id: 15,
    label: "Fundamental Rights overview",
    query: "Explain the Fundamental Rights under the Indian Constitution and their significance.",
    icon: Scale,
    category: "Constitution",
  },
  {
    id: 16,
    label: "SC/ST Act protections",
    query: "What protections and penalties are provided under the SC/ST Prevention of Atrocities Act?",
    icon: Users,
    category: "Constitution",
  },

  // Legal Drafting
  {
    id: 17,
    label: "Draft a legal notice",
    query: "Help me draft a legal notice for recovery of unpaid dues from a tenant.",
    icon: FileText,
    category: "Drafting",
  },
  {
    id: 18,
    label: "Draft a bail application",
    query: "Help me draft a bail application for a bailable offense under BNSS.",
    icon: FileText,
    category: "Drafting",
  },

  // Hindu Marriage Act
  {
    id: 19,
    label: "Divorce grounds under HMA",
    query: "What are the grounds for divorce under the Hindu Marriage Act?",
    icon: Users,
    category: "Family",
  },
  {
    id: 20,
    label: "Maintenance rights after separation",
    query: "What are the maintenance rights of a spouse after separation under Indian law?",
    icon: Users,
    category: "Family",
  },
];

// ---------------------------------------------------------------------------
// Helpers – pick N random suggestions without repeat
// ---------------------------------------------------------------------------

function pickRandom(arr: Suggestion[], n: number): Suggestion[] {
  const shuffled = [...arr].sort(() => Math.random() - 0.5);
  return shuffled.slice(0, n);
}

const VISIBLE_COUNT = 4;

// ---------------------------------------------------------------------------
// Animation variants
// ---------------------------------------------------------------------------

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.08 },
  },
};

const chipVariants = {
  hidden: { opacity: 0, y: 16, scale: 0.95 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { type: "spring" as const, stiffness: 350, damping: 25 },
  },
  exit: {
    opacity: 0,
    y: -10,
    scale: 0.95,
    transition: { duration: 0.15 },
  },
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function TrendingTopics({
  onTopicClick,
  className,
}: TrendingTopicsProps) {
  const [refreshKey, setRefreshKey] = useState(0);

  const suggestions = useMemo(
    () => pickRandom(allSuggestions, VISIBLE_COUNT),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [refreshKey]
  );

  const handleRefresh = () => setRefreshKey((k) => k + 1);

  return (
    <div className={cn("w-full", className)}>
      {/* Header row */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className='flex items-center justify-between mb-5 px-1'
      >
        <div className='flex items-center gap-2'>
          <div className='p-1.5 rounded-lg bg-amber-500/10 text-amber-600 dark:text-amber-400'>
            <Lightbulb className='w-4 h-4' />
          </div>
          <h3 className='text-sm font-semibold text-muted-foreground uppercase tracking-wider'>
            Try asking
          </h3>
        </div>

        <motion.button
          onClick={handleRefresh}
          whileHover={{ rotate: 180 }}
          whileTap={{ scale: 0.85 }}
          transition={{ type: "spring", stiffness: 300, damping: 15 }}
          className='p-1.5 rounded-lg text-muted-foreground/50 hover:text-amber-600 dark:hover:text-amber-400 hover:bg-amber-500/10 transition-colors'
          aria-label='Refresh suggestions'
        >
          <Shuffle className='w-4 h-4' />
        </motion.button>
      </motion.div>

      {/* Suggestion chips grid — 2 × 2 on md+, stacked on mobile */}
      <AnimatePresence mode='popLayout'>
        <motion.div
          key={refreshKey}
          variants={containerVariants}
          initial='hidden'
          animate='visible'
          className='grid grid-cols-1 md:grid-cols-2 gap-3'
        >
          {suggestions.map((s) => (
            <motion.button
              key={s.id}
              variants={chipVariants}
              layout
              onClick={() => onTopicClick(s.query)}
              className={cn(
                "group relative flex items-center gap-3 px-4 py-3.5 rounded-2xl text-left transition-all duration-200",
                "glass border border-white/15 dark:border-white/10",
                "hover:bg-white/40 dark:hover:bg-white/5 hover:border-amber-500/30 hover:shadow-md"
              )}
              whileHover={{ y: -2 }}
              whileTap={{ scale: 0.97 }}
            >
              {/* Icon */}
              <div
                className={cn(
                  "shrink-0 p-2.5 rounded-xl transition-colors duration-200",
                  "bg-secondary/50 group-hover:bg-amber-500/10",
                  "text-muted-foreground group-hover:text-amber-600 dark:group-hover:text-amber-400"
                )}
              >
                <s.icon className='w-4 h-4' />
              </div>

              {/* Text */}
              <div className='flex-1 min-w-0'>
                <span className='text-[10px] font-semibold text-muted-foreground/50 uppercase tracking-widest'>
                  {s.category}
                </span>
                <p className='text-sm font-medium text-foreground group-hover:text-amber-600 dark:group-hover:text-amber-400 transition-colors leading-snug line-clamp-1'>
                  {s.label}
                </p>
              </div>

              {/* Arrow */}
              <ArrowRight className='shrink-0 w-3.5 h-3.5 text-muted-foreground/30 opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-200' />
            </motion.button>
          ))}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
