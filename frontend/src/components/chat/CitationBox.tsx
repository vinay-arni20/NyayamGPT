import { motion } from "framer-motion";
import { ExternalLink, Scale, BookOpen } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Citation } from "@/types";

interface CitationBoxProps {
  citation: Citation;
  index: number;
}

export function CitationBox({ citation, index }: CitationBoxProps) {
  const stripHtml = (html: string) => {
    if (!html) return "";
    return html.replace(/<[^>]*>/g, "");
  };

  const getSourceIcon = (context?: string) => {
    const source = context || "";
    if (source.includes("Indian Kanoon")) return Scale;
    if (source.includes("India Code")) return BookOpen;
    return ExternalLink;
  };

  const Icon = getSourceIcon(citation.context);
  const displaySource =
    citation.context || (citation.verified ? "Verified" : "Legal Source");

  const lawText = stripHtml(citation.law || citation.act || "");
  const titleText = stripHtml(citation.title || "");

  return (
    <motion.a
      href={citation.url}
      target='_blank'
      rel='noopener noreferrer'
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
      className={cn(
        "group block p-3 rounded-lg border transition-all duration-200 h-full",
        "bg-card hover:bg-accent/50",
        "border-border hover:border-primary/50",
        "hover:shadow-sm"
      )}
    >
      <div className='flex flex-col gap-2'>
        <div className='flex items-center gap-2'>
          <div className='p-1 rounded-full bg-muted text-muted-foreground'>
            <Icon className='w-3 h-3' />
          </div>
          <span className='text-[10px] font-medium text-muted-foreground truncate max-w-[100px]'>
            {displaySource}
          </span>
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
