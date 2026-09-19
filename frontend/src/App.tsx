import React, { useState } from "react";
import { Header } from "./components/Header";
import { PaperInput } from "./components/PaperInput";
import { PipelineStepper } from "./components/PipelineStepper";
import { PaperCard } from "./components/PaperCard";
import { ClaimsTable } from "./components/ClaimsTable";
import { DiscoveryGrid } from "./components/DiscoveryGrid";
import { ApprovalCockpit } from "./components/ApprovalCockpit";
import { LiveTerminal } from "./components/LiveTerminal";
import { ReportCard } from "./components/ReportCard";
import { useZeroGazeStream } from "./hooks/useZeroGazeStream";
import { AlertCircle } from "lucide-react";

export const App: React.FC = () => {
  const { state, startReplication, sendApproval } = useZeroGazeStream();
  const [selectedTarget, setSelectedTarget] = useState<string>("2106.09685");

  const handleSelectSample = (target: string) => {
    setSelectedTarget(target);
    startReplication(target);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <Header
        onSelectSample={handleSelectSample}
        isStreaming={state.isStreaming}
        activeStage={state.activeNode || state.stage}
      />

      <main className="max-w-7xl mx-auto px-4 py-6 w-full space-y-6 flex-1">
        {/* Top Control Section */}
        <div className="space-y-4">
          <PaperInput
            onStart={(target, autoApprove) => startReplication(target, autoApprove)}
            isStreaming={state.isStreaming}
            selectedTarget={selectedTarget}
          />

          <PipelineStepper
            completedNodes={state.completedNodes}
            activeNode={state.activeNode}
            stage={state.stage}
          />
        </div>

        {/* Global Error Banner */}
        {state.error && (
          <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl flex items-center space-x-3 text-rose-400 text-xs font-mono">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <span>{state.error}</span>
          </div>
        )}

        {/* Two-Column Working Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
          {/* Left Column: Paper Ingestion & Discovery */}
          <div className="space-y-6">
            <PaperCard paper={state.paper} />
            <DiscoveryGrid codeResource={state.codeResource} />
          </div>

          {/* Right Column: Claims & Live Console */}
          <div className="space-y-6">
            <ClaimsTable claims={state.claims} />
            <LiveTerminal logs={state.terminalLogs} />
          </div>
        </div>

        {/* Terminal / Finished Report View */}
        {state.report && (
          <div className="pt-2">
            <ReportCard report={state.report} executionResult={state.executionResult} />
          </div>
        )}
      </main>

      {/* Human-in-the-Loop Approval Modal */}
      <ApprovalCockpit
        payload={state.approvalPayload}
        onResolve={(decision, overrides, comments) =>
          sendApproval(decision, overrides, comments)
        }
      />
    </div>
  );
};

export default App;
