import React, { useState } from "react";
import { Search, Sparkles, CheckSquare, Square } from "lucide-react";

interface PaperInputProps {
  onStart: (target: string, autoApprove: boolean) => void;
  isStreaming: boolean;
  selectedTarget?: string;
}

export const PaperInput: React.FC<PaperInputProps> = ({ onStart, isStreaming, selectedTarget }) => {
  const [target, setTarget] = useState(selectedTarget || "2106.09685");
  const [autoApprove, setAutoApprove] = useState(false);

  // Sync when selectedTarget prop changes
  React.useEffect(() => {
    if (selectedTarget) {
      setTarget(selectedTarget);
    }
  }, [selectedTarget]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!target.trim() || isStreaming) return;
    onStart(target.trim(), autoApprove);
  };

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 p-2 bg-slate-900/80 border border-slate-800 rounded-xl shadow-lg backdrop-blur">
        <div className="relative flex-1 flex items-center">
          <Search className="absolute left-3.5 w-4 h-4 text-slate-500" />
          <input
            type="text"
            value={target}
            onChange={(e) => setTarget(e.target.value)}
            placeholder="Enter arXiv ID (e.g. 2106.09685) or PDF URL..."
            className="w-full pl-10 pr-4 py-2.5 bg-transparent text-sm text-white placeholder-slate-500 focus:outline-none"
            disabled={isStreaming}
          />
        </div>

        <div className="flex items-center gap-3 px-2">
          <button
            type="button"
            onClick={() => setAutoApprove(!autoApprove)}
            className="flex items-center space-x-1.5 text-xs text-slate-400 hover:text-white transition-colors cursor-pointer select-none"
          >
            {autoApprove ? (
              <CheckSquare className="w-4 h-4 text-brand-400" />
            ) : (
              <Square className="w-4 h-4 text-slate-600" />
            )}
            <span>Auto-Approve</span>
          </button>

          <button
            type="submit"
            disabled={isStreaming || !target.trim()}
            className="flex items-center justify-center space-x-2 px-5 py-2.5 bg-brand-500 hover:bg-brand-400 disabled:bg-slate-800 text-slate-950 disabled:text-slate-500 font-semibold text-xs rounded-lg shadow-md transition-all cursor-pointer disabled:cursor-not-allowed"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>{isStreaming ? "Streaming..." : "Replicate"}</span>
          </button>
        </div>
      </div>
    </form>
  );
};
