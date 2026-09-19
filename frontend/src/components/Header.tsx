import React from "react";
import { Activity, Cpu, Sparkles } from "lucide-react";

interface HeaderProps {
  onSelectSample: (target: string) => void;
  isStreaming: boolean;
  activeStage: string;
}

export const Header: React.FC<HeaderProps> = ({ onSelectSample, isStreaming, activeStage }) => {
  return (
    <header className="border-b border-slate-800 bg-slate-900/60 backdrop-blur-md sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-brand-500/20">
            <Cpu className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="font-bold text-lg text-white tracking-tight">Zero Gaze</h1>
              <span className="text-[10px] uppercase font-mono tracking-wider px-2 py-0.5 rounded-full bg-brand-500/10 text-brand-400 border border-brand-500/20">
                MNC Grade
              </span>
            </div>
            <p className="text-xs text-slate-400">Autonomous ML Research Replication Engine</p>
          </div>
        </div>

        {/* Quick Sample Selector */}
        <div className="flex items-center space-x-3">
          <span className="text-xs text-slate-400 hidden sm:inline flex items-center">
            <Sparkles className="w-3.5 h-3.5 mr-1 text-amber-400" /> Samples:
          </span>
          <div className="flex items-center space-x-1.5">
            <button
              onClick={() => onSelectSample("2106.09685")}
              className="text-xs px-2.5 py-1 rounded-md bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors border border-slate-700/60"
            >
              LoRA
            </button>
            <button
              onClick={() => onSelectSample("2205.14135")}
              className="text-xs px-2.5 py-1 rounded-md bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors border border-slate-700/60"
            >
              FlashAttention
            </button>
            <button
              onClick={() => onSelectSample("1706.03762")}
              className="text-xs px-2.5 py-1 rounded-md bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors border border-slate-700/60"
            >
              Transformer
            </button>
          </div>

          <div className="h-5 w-[1px] bg-slate-800 mx-1 hidden sm:block" />

          {/* Engine Status indicator */}
          <div className="flex items-center space-x-2 px-3 py-1 rounded-full bg-slate-800/60 border border-slate-700/50">
            <Activity
              className={`w-3.5 h-3.5 ${
                isStreaming ? "text-emerald-400 animate-pulse" : "text-slate-400"
              }`}
            />
            <span className="text-xs font-mono text-slate-300">
              {isStreaming ? activeStage : "Ready"}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
};
