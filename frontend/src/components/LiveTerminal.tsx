import React, { useRef, useEffect } from "react";
import { Terminal, Trash2 } from "lucide-react";

interface LiveTerminalProps {
  logs: string[];
  onClear?: () => void;
}

export const LiveTerminal: React.FC<LiveTerminalProps> = ({ logs, onClear }) => {
  const terminalEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  return (
    <div className="bg-slate-950 border border-slate-800 rounded-xl overflow-hidden flex flex-col h-72 shadow-inner">
      {/* Terminal Titlebar */}
      <div className="bg-slate-900/80 px-4 py-2 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Terminal className="w-3.5 h-3.5 text-brand-400" />
          <span className="text-xs font-mono text-slate-300">Live Agent & Sandbox Console</span>
          <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-800 text-slate-400">
            {logs.length} events
          </span>
        </div>

        {onClear && (
          <button
            onClick={onClear}
            className="text-slate-400 hover:text-white p-1 rounded hover:bg-slate-800 transition-colors"
            title="Clear logs"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* Terminal Output */}
      <div className="p-4 overflow-y-auto flex-1 font-mono text-[11px] leading-relaxed space-y-1 text-slate-300 scrollbar-thin scrollbar-thumb-slate-800">
        {logs.length === 0 ? (
          <p className="text-slate-600 italic">Awaiting events from Zero Gaze agent stream...</p>
        ) : (
          logs.map((log, index) => {
            const isError = log.includes("[ERROR]") || log.includes("Error") || log.includes("Failed");
            const isStage = log.includes("[STAGE]") || log.includes("[INIT]");
            const isAction = log.includes("[ACTION]") || log.includes("[GATE]");
            const isFinish = log.includes("[FINISH]") || log.includes("Completed");

            let colorClass = "text-slate-300";
            if (isError) colorClass = "text-rose-400";
            else if (isStage) colorClass = "text-indigo-400 font-semibold";
            else if (isAction) colorClass = "text-amber-400 font-semibold";
            else if (isFinish) colorClass = "text-emerald-400 font-bold";

            return (
              <div key={index} className={`${colorClass} break-all whitespace-pre-wrap`}>
                {log}
              </div>
            );
          })
        )}
        <div ref={terminalEndRef} />
      </div>
    </div>
  );
};
