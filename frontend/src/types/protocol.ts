export type PipelineStage =
  | "idle"
  | "fetch_paper"
  | "extract_claims"
  | "find_code_dataset"
  | "plan_baseline"
  | "human_approval"
  | "execute_baseline"
  | "write_report"
  | "completed"
  | "aborted"
  | "failed";

export interface PaperArtifact {
  paper_id: string;
  title: string;
  authors: string[];
  published_date?: string;
  abstract: string;
  pdf_url: string;
  full_text_markdown: string;
  extraction_source: string;
}

export interface ClaimItem {
  benchmark_name: string;
  target_metric: string;
  paper_value: number;
  baseline_algorithm: string;
  dataset_name?: string;
  hyperparameters?: Record<string, unknown>;
}

export interface CodeResource {
  status: "official" | "community" | "synthetic_stub" | "unavailable";
  repo_url?: string;
  stars?: number;
  license?: string;
  dataset_references?: string[];
  generated_baseline_code?: string;
}

export interface ReplicationPlan {
  target_hardware: "cpu" | "cuda" | "mps";
  estimated_runtime_minutes: number;
  execution_command: string;
  dependencies: string[];
  baseline_script: string;
}

export interface ExecutionResult {
  success: boolean;
  exit_code: number;
  stdout: string;
  stderr: string;
  runtime_seconds: number;
  output_metrics: Record<string, number>;
  error_message?: string | null;
}

export interface ReplicationReport {
  paper_title: string;
  verdict: string;
  summary_markdown: string;
  metric_deltas: Record<string, unknown>;
  hardware_target: string;
  runtime_seconds: number;
  reproduction_status: "verified" | "discrepancy" | "failed";
}

export interface InterruptPayload {
  thread_id: string;
  prompt: string;
  plan: ReplicationPlan;
  code_resource?: CodeResource;
}
