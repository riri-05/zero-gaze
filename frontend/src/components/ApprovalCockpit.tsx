import React, { useState, useEffect } from "react";
import { UserCheck, Play, RotateCcw, XCircle, Cpu, Clock, Terminal } from "lucide-react";
import { ReplicationPlan, InterruptPayload } from "../types/protocol";

interface ApprovalCockpitProps {
  payload: InterruptPayload | null;
  onResolve: (
    decision: "approved" | "aborted" | "revised",
    overrides?: { script?: string; timeout_seconds?: number },
    comments?: string
  ) => void;
}

export const ApprovalCockpit: React.FC<ApprovalCockpitProps> = ({ payload, onResolve }) => {
  const [script, setScript] = useState("");
  const [hardware, setHardware] = useState<"cpu" | "cuda">("cpu");
  const [timeout, setTimeout] = useState(60);
  const [comments, setComments] = useState("");

  useEffect(() => {
    if (payload?.plan?.baseline_script) {
      setScript(payload.plan.baseline_script);
      setHardware((payload.plan.target_hardware as "cpu" | "cuda") || "cpu");
      setTimeout((payload.plan.estimated_runtime_minutes || 1) * 60);
    }
  }, [payload]);

  if (!payload) return null;

  const plan: ReplicationPlan = payload.plan || {
    target_hardware: "cpu",
    estimated_runtime_minutes: 5,
    execution_command: "python baseline.py",
    dependencies: [],
    baseline_script: "",
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-brand-500/40 rounded-2xl w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl shadow-brand-500/10 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="p-5 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-brand-500/10 border border-brand-500/30 flex items-center justify-center text-brand-400">
              <UserCheck className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white">Human Approval Gate</h2>
              <p className="text-xs text-slate-400">{payload.prompt}</p>
            </div>
          </div>
          <span className="text-[10px] font-mono uppercase bg-amber-500/10 text-amber-400 border border-amber-500/20 px-2.5 py-1 rounded-full">
            Action Required
          </span>
        </div>

        {/* Cockpit Content */}
        <div className="p-5 space-y-4 overflow-y-auto flex-1 scrollbar-thin scrollbar-thumb-slate-800">
          {/* Controls Bar */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-lg">
              <label className="text-[11px] font-mono text-slate-400 uppercase flex items-center gap-1.5 mb-1.5">
                <Terminal className="w-3.5 h-3.5 text-brand-400" /> Command
              </label>
              <div className="text-xs font-mono font-medium text-slate-200 bg-slate-900 px-2.5 py-1 rounded border border-slate-800">
                {plan.execution_command}
              </div>
            </div>

            <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-lg">
              <label className="text-[11px] font-mono text-slate-400 uppercase flex items-center gap-1.5 mb-1.5">
                <Cpu className="w-3.5 h-3.5 text-indigo-400" /> Target Hardware
              </label>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setHardware("cpu")}
                  className={`text-xs px-3 py-1 rounded font-mono transition-colors ${
                    hardware === "cpu"
                      ? "bg-brand-500 text-slate-950 font-bold"
                      : "bg-slate-900 text-slate-400 hover:text-white"
                  }`}
                >
                  CPU
                </button>
                <button
                  type="button"
                  onClick={() => setHardware("cuda")}
                  className={`text-xs px-3 py-1 rounded font-mono transition-colors ${
                    hardware === "cuda"
                      ? "bg-brand-500 text-slate-950 font-bold"
                      : "bg-slate-900 text-slate-400 hover:text-white"
                  }`}
                >
                  NVIDIA GPU
                </button>
              </div>
            </div>

            <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-lg">
              <label className="text-[11px] font-mono text-slate-400 uppercase flex items-center justify-between mb-1.5">
                <span className="flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-amber-400" /> Timeout Budget
                </span>
                <span className="text-white font-mono">{timeout}s</span>
              </label>
              <input
                type="range"
                min="10"
                max="600"
                step="10"
                value={timeout}
                onChange={(e) => setTimeout(Number(e.target.value))}
                className="w-full accent-brand-500"
              />
            </div>
          </div>

          {/* Code Viewer & Editor */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                Baseline Experiment Script (Review & Edit)
              </label>
              <span className="text-[11px] font-mono text-slate-500">
                {script.split("\n").length} lines
              </span>
            </div>
            <textarea
              value={script}
              onChange={(e) => setScript(e.target.value)}
              className="w-full h-64 p-3 bg-slate-950 font-mono text-xs text-slate-200 border border-slate-800 rounded-lg focus:outline-none focus:border-brand-500/50 resize-none scrollbar-thin scrollbar-thumb-slate-800"
              spellCheck={false}
            />
          </div>

          {/* Revisions Comment */}
          <div>
            <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider block mb-1">
              Revision Feedback (Optional)
            </label>
            <input
              type="text"
              value={comments}
              onChange={(e) => setComments(e.target.value)}
              placeholder="e.g. Please use batch size 16 and add evaluation loop on test split..."
              className="w-full text-xs px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 focus:outline-none focus:border-brand-500/50"
            />
          </div>
        </div>

        {/* Action Buttons */}
        <div className="p-5 border-t border-slate-800 flex items-center justify-between bg-slate-950/40">
          <button
            onClick={() => onResolve("aborted")}
            className="flex items-center gap-2 px-4 py-2 text-xs font-medium text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 rounded-lg transition-colors border border-rose-500/20"
          >
            <XCircle className="w-4 h-4" /> Abort Execution
          </button>

          <div className="flex items-center gap-3">
            <button
              onClick={() => onResolve("revised", { script, timeout_seconds: timeout }, comments)}
              className="flex items-center gap-2 px-4 py-2 text-xs font-medium text-amber-400 hover:text-amber-300 bg-amber-500/10 hover:bg-amber-500/20 rounded-lg transition-colors border border-amber-500/20"
            >
              <RotateCcw className="w-4 h-4" /> Request Revision
            </button>

            <button
              onClick={() => onResolve("approved", { script, timeout_seconds: timeout })}
              className="flex items-center gap-2 px-5 py-2 text-xs font-semibold text-slate-950 bg-brand-500 hover:bg-brand-400 rounded-lg shadow-lg shadow-brand-500/20 transition-colors"
            >
              <Play className="w-4 h-4 fill-slate-950" /> Approve & Execute
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
