import React from "react";
import {
  FileText,
  BarChart2,
  Code2,
  Cpu,
  UserCheck,
  Terminal,
  Award,
  CheckCircle2,
  Loader2,
} from "lucide-react";

interface PipelineStepperProps {
  completedNodes: string[];
  activeNode: string | null;
  stage: string;
}

const STAGES = [
  { id: "fetch_paper", label: "Paper Ingestion", icon: FileText },
  { id: "extract_claims", label: "Extract Claims", icon: BarChart2 },
  { id: "find_code_dataset", label: "Discover Repos", icon: Code2 },
  { id: "plan_baseline", label: "Plan Baseline", icon: Cpu },
  { id: "human_approval", label: "Approval Gate", icon: UserCheck },
  { id: "execute_baseline", label: "Execution Sandbox", icon: Terminal },
  { id: "write_report", label: "Replication Report", icon: Award },
];

export const PipelineStepper: React.FC<PipelineStepperProps> = ({
  completedNodes,
  activeNode,
  stage,
}) => {
  return (
    <div className="w-full bg-slate-900/40 border border-slate-800/80 rounded-xl p-4 shadow-sm backdrop-blur">
      <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-2">
        {STAGES.map((s, idx) => {
          const Icon = s.icon;
          const isDone = completedNodes.includes(s.id) || stage === "completed";
          const isActive = activeNode === s.id;

          return (
            <div
              key={s.id}
              className={`relative flex flex-col items-center p-3 rounded-lg border transition-all ${
                isActive
                  ? "bg-brand-500/10 border-brand-500/40 shadow-lg shadow-brand-500/10"
                  : isDone
                  ? "bg-slate-800/30 border-slate-700/40 text-slate-200"
                  : "bg-slate-950/20 border-slate-900 text-slate-500"
              }`}
            >
              <div className="flex items-center justify-center w-8 h-8 rounded-full mb-2 bg-slate-800/60">
                {isDone ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                ) : isActive ? (
                  <Loader2 className="w-5 h-5 text-brand-400 animate-spin" />
                ) : (
                  <Icon className="w-4 h-4 text-slate-500" />
                )}
              </div>
              <span className="text-[11px] font-medium text-center line-clamp-1">
                {idx + 1}. {s.label}
              </span>
              <span className="text-[9px] uppercase font-mono mt-0.5 text-slate-400">
                {isDone ? "Completed" : isActive ? "Running" : "Pending"}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
