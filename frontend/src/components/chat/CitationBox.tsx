import { motion } from "framer-motion";
import { ExternalLink, Scale, BookOpen, Gavel } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Citation } from "@/types";

// Map of law codes to display names
const LAW_DISPLAY_NAMES: Record<string, string> = {
  IPC: "Indian Penal Code (1860)",
  CrPC: "Code of Criminal Procedure (1973)",
  CPC: "Code of Civil Procedure (1908)",
  IEA: "Indian Evidence Act (1872)",
  MVA: "Motor Vehicles Act (1988)",
  HMA: "Hindu Marriage Act (1955)",
  IDA: "Industrial Disputes Act (1947)",
  NI: "Negotiable Instruments Act (1881)",
  "Negotiable Instruments Act": "Negotiable Instruments Act (1881)",
  BNS: "Bharatiya Nyaya Sanhita (2023)",
  BNSS: "Bharatiya Nagarik Suraksha Sanhita (2023)",
  BSA: "Bharatiya Sakshya Adhiniyam (2023)",
};

// Check if it's a 2023 criminal code
const is2023Code = (law: string): boolean => {
  return ["BNS", "BNSS", "BSA"].includes(law?.toUpperCase() || "");
};

interface CitationBoxProps {
  citation: Citation;
  index: number;
}

export function CitationBox({ citation, index }: CitationBoxProps) {
  const stripHtml = (html: string) => {
    if (!html) return "";
    return html.replace(/<[^>]*>/g, "");
  };

  const getSourceIcon = (context?: string, law?: string) => {
    // Use Gavel for 2023 criminal codes
    if (is2023Code(law || "")) return Gavel;
    const source = context || "";
    if (source.includes("Indian Kanoon")) return Scale;
    if (source.includes("India Code")) return BookOpen;
    return ExternalLink;
  };

  const lawCode = citation.law || citation.act || "";
  const Icon = getSourceIcon(citation.context, lawCode);
  const displaySource =
    citation.context || (citation.verified ? "Verified" : "Legal Source");

  const lawText = stripHtml(lawCode);
  const titleText = stripHtml(citation.title || "");

  // Get full law name for tooltip
  const fullLawName = LAW_DISPLAY_NAMES[lawText.toUpperCase()] || lawText;

  return (
    <motion.a
      href={citation.url || citation.source_url}
      target='_blank'
      rel='noopener noreferrer'
      title={fullLawName}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
      className={cn(
        "group block p-3 rounded-lg border transition-all duration-200 h-full",
        "bg-card hover:bg-accent/50",
        "border-border hover:border-primary/50",
        "hover:shadow-sm",
        is2023Code(lawText) && "ring-1 ring-purple-500/20"
      )}
    >
      <div className='flex flex-col gap-2'>
        <div className='flex items-center gap-2'>
          <div
            className={cn(
              "p-1 rounded-full text-muted-foreground",
              is2023Code(lawText)
                ? "bg-purple-100 dark:bg-purple-900/30"
                : "bg-muted"
            )}
          >
            <Icon className='w-3 h-3' />
          </div>
          <span className='text-[10px] font-medium text-muted-foreground truncate max-w-[100px]'>
            {displaySource}
          </span>
          {is2023Code(lawText) && (
            <span className='text-[8px] px-1 py-0.5 rounded bg-purple-100 dark:bg-purple-900/50 text-purple-700 dark:text-purple-300 font-medium'>
              2023
            </span>
          )}
        </div>

        <h4 className='text-xs font-semibold text-foreground line-clamp-2 leading-tight'>
          {lawText} {citation.section}
        </h4>
        <p className='text-[10px] text-muted-foreground line-clamp-2'>
          {titleText}
        </p>
      </div>
    </motion.a>
  );
}

interface CitationsPanelProps {
  citations: Citation[];
}

export function CitationsPanel({ citations }: CitationsPanelProps) {
  if (!citations || citations.length === 0) return null;

  // Deduplicate citations based on URL and Law+Section
  const uniqueCitations = citations.filter(
    (citation, index, self) =>
      index ===
      self.findIndex(
        (t) =>
          (t.url && citation.url && t.url === citation.url) ||
          (t.act === citation.act &&
            t.section === citation.section &&
            t.law === citation.law)
      )
  );

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      className='mb-6'
    >
      <h3 className='text-xs font-bold uppercase tracking-wider text-muted-foreground mb-3 flex items-center gap-2'>
        <BookOpen className='w-3 h-3' />
        Sources
      </h3>
      <div className='flex gap-3 overflow-x-auto pb-2 scrollbar-thin scrollbar-thumb-border'>
        {uniqueCitations.map((citation, index) => (
          <div key={index} className='flex-shrink-0 w-48'>
            <CitationBox citation={citation} index={index} />
          </div>
        ))}
      </div>
    </motion.div>
  );
}
