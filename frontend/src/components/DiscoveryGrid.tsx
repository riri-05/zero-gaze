import React from "react";
import { GitBranch, Star, ExternalLink, ShieldCheck } from "lucide-react";
import { CodeResource } from "../types/protocol";

interface DiscoveryGridProps {
  codeResource: CodeResource | null;
}

export const DiscoveryGrid: React.FC<DiscoveryGridProps> = ({ codeResource }) => {
  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 shadow-sm space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <GitBranch className="w-4 h-4 text-indigo-400" />
          <h3 className="font-semibold text-sm text-white">Discovered Code Artifacts</h3>
        </div>
        {codeResource?.status && (
          <span
            className={`text-[10px] uppercase font-mono px-2 py-0.5 rounded-full border ${
              codeResource.status === "official"
                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                : codeResource.status === "community"
                ? "bg-blue-500/10 text-blue-400 border-blue-500/20"
                : "bg-amber-500/10 text-amber-400 border-amber-500/20"
            }`}
          >
            {codeResource.status}
          </span>
        )}
      </div>

      {!codeResource ? (
        <div className="py-6 text-center text-xs text-slate-500 border border-dashed border-slate-800/80 rounded-lg">
          No repository discovered yet.
        </div>
      ) : (
        <div className="p-3.5 rounded-lg bg-slate-950/40 border border-slate-800/80 space-y-2.5">
          <div className="flex items-start justify-between">
            <div>
              <h4 className="text-xs font-mono font-medium text-slate-200 break-all">
                {codeResource.repo_url || "Synthetic Baseline Generator"}
              </h4>
              <p className="text-[11px] text-slate-400 mt-0.5">
                {codeResource.status === "official"
                  ? "Verified primary author implementation"
                  : codeResource.status === "community"
                  ? "Community reproduction repository"
                  : "Automatic baseline synthesized from claims"}
              </p>
            </div>
            {codeResource.repo_url && (
              <a
                href={codeResource.repo_url}
                target="_blank"
                rel="noreferrer"
                className="text-slate-400 hover:text-white transition-colors p-1"
              >
                <ExternalLink className="w-4 h-4" />
              </a>
            )}
          </div>

          <div className="flex items-center gap-4 text-xs font-mono text-slate-400 pt-1 border-t border-slate-800/60">
            {codeResource.stars !== undefined && (
              <div className="flex items-center text-amber-400">
                <Star className="w-3.5 h-3.5 mr-1 fill-amber-400" />
                <span>{codeResource.stars.toLocaleString()} stars</span>
              </div>
            )}
            {codeResource.license && (
              <div className="flex items-center text-slate-400">
                <ShieldCheck className="w-3.5 h-3.5 mr-1 text-slate-500" />
                <span>{codeResource.license}</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
