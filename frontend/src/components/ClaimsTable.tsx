import React from "react";
import { BarChart3, Database } from "lucide-react";
import { ClaimItem } from "../types/protocol";

interface ClaimsTableProps {
  claims: ClaimItem[];
}

export const ClaimsTable: React.FC<ClaimsTableProps> = ({ claims }) => {
  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 shadow-sm space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <BarChart3 className="w-4 h-4 text-brand-400" />
          <h3 className="font-semibold text-sm text-white">Extracted Benchmark Claims</h3>
        </div>
        <span className="text-xs font-mono text-slate-400 bg-slate-800 px-2 py-0.5 rounded-full">
          {claims.length} claims
        </span>
      </div>

      {claims.length === 0 ? (
        <div className="py-8 text-center text-xs text-slate-500 border border-dashed border-slate-800/80 rounded-lg">
          No benchmark claims extracted yet.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/40 text-slate-400 uppercase font-mono text-[10px] tracking-wider border-b border-slate-800">
              <tr>
                <th className="py-2.5 px-3">Benchmark</th>
                <th className="py-2.5 px-3">Target Metric</th>
                <th className="py-2.5 px-3">Reported Value</th>
                <th className="py-2.5 px-3">Baseline</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50">
              {claims.map((claim, idx) => (
                <tr key={idx} className="hover:bg-slate-800/20 transition-colors">
                  <td className="py-2.5 px-3 font-medium text-slate-200 flex items-center gap-1.5">
                    <Database className="w-3 h-3 text-slate-500" />
                    {claim.benchmark_name}
                  </td>
                  <td className="py-2.5 px-3 font-mono text-brand-400">
                    {claim.target_metric}
                  </td>
                  <td className="py-2.5 px-3 font-mono font-bold text-white">
                    {claim.paper_value}
                  </td>
                  <td className="py-2.5 px-3 text-slate-400">
                    {claim.baseline_algorithm || "Default"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
