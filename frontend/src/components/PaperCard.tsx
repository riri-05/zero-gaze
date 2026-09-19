import React from "react";
import { BookOpen, ExternalLink, Calendar, Users, Layers } from "lucide-react";
import { PaperArtifact } from "../types/protocol";

interface PaperCardProps {
  paper: PaperArtifact | null;
}

export const PaperCard: React.FC<PaperCardProps> = ({ paper }) => {
  if (!paper) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-8 border border-dashed border-slate-800 rounded-xl bg-slate-900/20 text-slate-500">
        <BookOpen className="w-10 h-10 mb-3 opacity-30" />
        <p className="text-sm">Awaiting paper ingestion</p>
        <p className="text-xs text-slate-600">Submit an arXiv target above to begin</p>
      </div>
    );
  }

  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-brand-500/10 text-brand-400 border border-brand-500/20">
              arXiv {paper.paper_id}
            </span>
            <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400">
              {paper.extraction_source}
            </span>
          </div>
          <h2 className="text-lg font-bold text-white tracking-tight leading-snug">
            {paper.title}
          </h2>
        </div>

        <a
          href={paper.pdf_url}
          target="_blank"
          rel="noreferrer"
          className="flex items-center text-xs text-brand-400 hover:text-brand-300 transition-colors shrink-0 bg-brand-500/10 px-2.5 py-1.5 rounded-lg border border-brand-500/20"
        >
          <ExternalLink className="w-3.5 h-3.5 mr-1" /> PDF
        </a>
      </div>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-slate-400">
        {paper.authors && paper.authors.length > 0 && (
          <div className="flex items-center">
            <Users className="w-3.5 h-3.5 mr-1.5 text-slate-500" />
            <span>{paper.authors.slice(0, 3).join(", ")}{paper.authors.length > 3 ? " et al." : ""}</span>
          </div>
        )}
        {paper.published_date && (
          <div className="flex items-center">
            <Calendar className="w-3.5 h-3.5 mr-1.5 text-slate-500" />
            <span>{paper.published_date}</span>
          </div>
        )}
        <div className="flex items-center">
          <Layers className="w-3.5 h-3.5 mr-1.5 text-slate-500" />
          <span>{paper.full_text_markdown.length.toLocaleString()} characters extracted</span>
        </div>
      </div>

      <div className="pt-2 border-t border-slate-800/80">
        <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
          Abstract
        </h4>
        <p className="text-xs text-slate-400 leading-relaxed max-h-36 overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-slate-800">
          {paper.abstract}
        </p>
      </div>
    </div>
  );
};
