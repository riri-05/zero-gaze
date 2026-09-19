import React from "react";
import { Award, CheckCircle, XCircle, Clock, Cpu } from "lucide-react";
import { ReplicationReport, ExecutionResult } from "../types/protocol";

interface ReportCardProps {
  report: ReplicationReport | null;
  executionResult: ExecutionResult | null;
}

export const ReportCard: React.FC<ReportCardProps> = ({ report, executionResult }) => {
  if (!report) return null;

  const isSuccess = report.verdict === "approved_for_replication";
  const metrics = executionResult?.output_metrics || {};

  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 shadow-sm space-y-4">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
        <div className="flex items-center space-x-2">
          <Award className="w-5 h-5 text-amber-400" />
          <h3 className="font-bold text-base text-white">Replication Evaluation Summary</h3>
        </div>

        <div className="flex items-center gap-2">
          <span
            className={`text-xs uppercase font-mono px-3 py-1 rounded-full border flex items-center gap-1.5 ${
              isSuccess
                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                : "bg-rose-500/10 text-rose-400 border-rose-500/30"
            }`}
          >
            {isSuccess ? <CheckCircle className="w-3.5 h-3.5" /> : <XCircle className="w-3.5 h-3.5" />}
            {report.verdict}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="p-3 bg-slate-950/40 border border-slate-800 rounded-lg">
          <span className="text-[10px] uppercase font-mono text-slate-400 block mb-1">Paper</span>
          <p className="text-xs font-semibold text-white truncate">{report.paper_title}</p>
        </div>

        <div className="p-3 bg-slate-950/40 border border-slate-800 rounded-lg">
          <span className="text-[10px] uppercase font-mono text-slate-400 flex items-center gap-1 mb-1">
            <Cpu className="w-3 h-3 text-indigo-400" /> Hardware Target
          </span>
          <p className="text-xs font-mono font-semibold text-slate-200">
            {report.hardware_target || "CPU"}
          </p>
        </div>

        <div className="p-3 bg-slate-950/40 border border-slate-800 rounded-lg">
          <span className="text-[10px] uppercase font-mono text-slate-400 flex items-center gap-1 mb-1">
            <Clock className="w-3 h-3 text-amber-400" /> Total Runtime
          </span>
          <p className="text-xs font-mono font-semibold text-slate-200">
            {executionResult?.runtime_seconds ? `${executionResult.runtime_seconds}s` : "0.0s"}
          </p>
        </div>
      </div>

      {Object.keys(metrics).length > 0 && (
        <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-lg">
          <h4 className="text-xs font-mono text-slate-300 uppercase mb-2">Measured Empirical Metrics</h4>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {Object.entries(metrics).map(([key, val]) => (
              <div key={key} className="p-2 bg-slate-900 border border-slate-800 rounded text-center">
                <span className="text-[10px] text-slate-400 block font-mono">{key}</span>
                <span className="text-sm font-bold font-mono text-brand-400">{val}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {report.summary_markdown && (
        <div className="pt-2">
          <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
            Detailed Findings
          </h4>
          <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-lg text-xs leading-relaxed font-mono whitespace-pre-wrap text-slate-300 max-h-60 overflow-y-auto scrollbar-thin scrollbar-thumb-slate-800">
            {report.summary_markdown}
          </div>
        </div>
      )}
    </div>
  );
};
