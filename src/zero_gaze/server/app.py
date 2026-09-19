"""FastAPI application factory with CORS, routes, and embedded dashboard."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from zero_gaze.server.routes import router


def create_app() -> FastAPI:
    """Construct and configure the Zero Gaze FastAPI application."""
    app = FastAPI(
        title="Zero Gaze Agent API",
        description="Autonomous ML paper to replication plan agent powered by LangGraph and AG-UI 1.0.",
        version="0.1.0",
    )

    import os

    cors_origins = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173",
        ).split(",")
        if origin.strip()
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)

    from pathlib import Path
    dist_dir = Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "dist"
    assets_dir = dist_dir / "assets"
    if assets_dir.is_dir():
        from fastapi.staticfiles import StaticFiles
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="frontend_assets")

    @app.get("/", response_class=HTMLResponse, summary="Interactive Zero Gaze Dashboard")
    def index() -> str:
        """Interactive replication control dashboard."""
        if dist_dir.is_dir() and (dist_dir / "index.html").is_file():
            return (dist_dir / "index.html").read_text(encoding="utf-8")
        return """<!DOCTYPE html>
<head>
  <meta charset="UTF-8">
  <title>Zero Gaze — Replication Dashboard</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-neutral-950 text-neutral-100 min-h-screen flex flex-col font-sans">
  <header class="border-b border-neutral-800 px-6 py-4 flex items-center justify-between">
    <div class="flex items-center gap-3">
      <div class="w-3 h-3 rounded-full bg-emerald-500 animate-pulse"></div>
      <h1 class="text-xl font-bold tracking-tight">Zero Gaze <span class="text-xs text-neutral-400 font-normal">v0.1.0</span></h1>
    </div>
    <span class="text-xs px-2.5 py-1 rounded bg-neutral-900 border border-neutral-700 text-neutral-300">AG-UI 1.0 Active</span>
  </header>

  <main class="flex-1 max-w-4xl w-full mx-auto p-6 space-y-6">
    <div class="bg-neutral-900 border border-neutral-800 rounded-xl p-6 shadow-sm">
      <h2 class="text-base font-semibold mb-3">Initiate Paper Replication</h2>
      <div class="flex gap-3">
        <input id="paperTarget" type="text" placeholder="arXiv ID (e.g. 2106.09685) or PDF URL"
               class="flex-1 bg-neutral-950 border border-neutral-700 rounded-lg px-4 py-2.5 text-sm text-neutral-100 focus:outline-none focus:border-emerald-500" value="2106.09685" />
        <button id="btnStart" onclick="startReplication()"
                class="bg-emerald-600 hover:bg-emerald-500 px-5 py-2.5 rounded-lg text-sm font-medium transition-colors">Start Agent</button>
      </div>
    </div>

    <!-- Active Stream / Status Card -->
    <div id="statusCard" class="hidden bg-neutral-900 border border-neutral-800 rounded-xl p-6 space-y-4">
      <div class="flex items-center justify-between border-b border-neutral-800 pb-3">
        <h3 class="text-sm font-semibold text-neutral-300">Live Agent Execution</h3>
        <span id="badgeStatus" class="text-xs px-2.5 py-0.5 rounded font-mono bg-neutral-800 text-neutral-300">IDLE</span>
      </div>
      <div id="logOutput" class="font-mono text-xs text-neutral-400 bg-neutral-950 p-4 rounded-lg overflow-y-auto max-h-64 whitespace-pre-wrap"></div>

      <!-- Approval Gate Modal -->
      <div id="approvalGate" class="hidden border border-emerald-500/30 bg-emerald-950/20 rounded-lg p-5 space-y-3">
        <div class="flex items-center gap-2 text-emerald-400 font-semibold text-sm">
          <span>Human-in-the-Loop Interrupt Gate</span>
        </div>
        <p class="text-xs text-neutral-300">The replication plan has been synthesized. Review and authorize baseline code execution.</p>
        <pre id="planPreview" class="text-xs bg-neutral-950 p-3 rounded text-neutral-300 overflow-x-auto"></pre>
        <div class="flex gap-3 pt-2">
          <button onclick="resolveApproval('approved')" class="bg-emerald-600 hover:bg-emerald-500 px-4 py-2 rounded text-xs font-semibold">Approve Execution</button>
          <button onclick="resolveApproval('aborted')" class="bg-rose-600 hover:bg-rose-500 px-4 py-2 rounded text-xs font-semibold">Abort</button>
        </div>
      </div>
    </div>
  </main>

  <script>
    let activeThreadId = null;

    async function startReplication() {
      const target = document.getElementById('paperTarget').value.trim();
      if (!target) return;

      document.getElementById('statusCard').classList.remove('hidden');
      document.getElementById('logOutput').textContent = 'Submitting paper target: ' + target + '...\\n';
      document.getElementById('badgeStatus').textContent = 'INITIALIZING';

      const res = await fetch('/api/replication/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ paper_target: target })
      });
      const data = await res.json();
      activeThreadId = data.thread_id;
      document.getElementById('logOutput').textContent += 'Thread initialized: ' + activeThreadId + '\\nStatus: ' + data.status + '\\n';

      if (data.is_interrupted) {
        showApprovalGate(data.state);
      }
    }

    function showApprovalGate(state) {
      document.getElementById('badgeStatus').textContent = 'INTERRUPTED (AWAITING APPROVAL)';
      document.getElementById('badgeStatus').className = 'text-xs px-2.5 py-0.5 rounded font-mono bg-amber-950 text-amber-400 border border-amber-800';
      document.getElementById('approvalGate').classList.remove('hidden');
      document.getElementById('planPreview').textContent = JSON.stringify(state.plan, null, 2);
    }

    async function resolveApproval(decision) {
      if (!activeThreadId) return;
      document.getElementById('approvalGate').classList.add('hidden');
      document.getElementById('badgeStatus').textContent = 'RESUMING (' + decision.toUpperCase() + ')';

      const res = await fetch('/api/replication/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ thread_id: activeThreadId, decision: decision })
      });
      const data = await res.json();
      document.getElementById('badgeStatus').textContent = data.status.toUpperCase();
      document.getElementById('logOutput').textContent += '\\nFinal Status: ' + data.status + '\\n\\n--- Replication Summary ---\\n' + (data.state.report ? data.state.report.summary_markdown : 'No report generated');
    }
  </script>
</body>
</html>
"""

    return app


# Default application instance for ASGI servers
app = create_app()
