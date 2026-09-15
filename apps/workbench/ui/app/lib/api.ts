// Typed client for workbench.api.v1 (ADR-0037 §4). Every call is a plain
// `fetch` against `workbench-api`'s JSON endpoints -- this file is the
// entire boundary between `workbench_ui` and the outside world; it never
// imports anything server-side, and workbench-api serves this app's own
// static build at the same origin (ADR-0044 decision 3), so a relative path
// is the production default. `NEXT_PUBLIC_API_BASE_URL` overrides it for
// `next dev`, run against a separately-started `workbench-api` on its own
// port.

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!response.ok) {
    const body: { error?: string } = await response.json().catch(() => ({}));
    throw new ApiError(
      response.status,
      body.error ?? `request failed: ${response.status}`,
    );
  }
  return response.json() as Promise<T>;
}

export type TemplateSource = "FRAMEWORK" | "USER";
export type TemplateStatus = "SUPPORTED" | "SHADOWED" | "UNSUPPORTED";

export interface TemplateSummary {
  template_id: string;
  template_version: number | null;
  title: string | null;
  description: string | null;
  source: TemplateSource;
  status: TemplateStatus;
  reason: string | null;
  unresolvable_model_aliases: string[];
}

export interface DatasetSummary {
  dataset_ref: string;
  instrument_id: string;
  timeframe: string;
  start_at: string;
  end_at: string;
  row_count: number;
}

export interface PhaseEvent {
  event: string;
  name: string;
  index: number;
  of: number;
  at?: string;
}

export type JobState =
  "QUEUED" | "RUNNING" | "SUCCEEDED" | "FAILED" | "CANCELLED" | "INTERRUPTED";

export interface JobResult {
  run_id?: string;
  research_id?: string;
  definition_hash?: string;
}

export interface JobSummary {
  job_id: string;
  job_kind: string;
  state: JobState;
  config_path: string;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  finished_at: string | null;
  exit_code: number | null;
  latest_phase: PhaseEvent | null;
  termination_path: string | null;
  interrupted_reason: string | null;
  result: JobResult | null;
}

export interface ValidateResult {
  ok: boolean;
  plan: Record<string, unknown> | null;
  error_type: string | null;
  error_message: string | null;
}

export function listTemplates(): Promise<{ templates: TemplateSummary[] }> {
  return apiFetch("/api/v1/templates");
}

export function applyTemplate(
  templateId: string,
  overrides: Record<string, unknown>,
): Promise<{ definition: Record<string, unknown> }> {
  return apiFetch(`/api/v1/templates/${encodeURIComponent(templateId)}/apply`, {
    method: "POST",
    body: JSON.stringify({ overrides }),
  });
}

export function listDatasets(): Promise<{ datasets: DatasetSummary[] }> {
  return apiFetch("/api/v1/datasets");
}

export interface ModelAliases {
  market_models: string[];
  signal_models: string[];
}

export function listModels(): Promise<ModelAliases> {
  return apiFetch("/api/v1/models");
}

export function validateDefinition(
  definition: Record<string, unknown>,
): Promise<ValidateResult> {
  return apiFetch("/api/v1/validate", {
    method: "POST",
    body: JSON.stringify({ definition }),
  });
}

export function listDefinitions(): Promise<{ definitions: string[] }> {
  return apiFetch("/api/v1/definitions");
}

export function saveDefinition(
  name: string,
  definition: Record<string, unknown>,
): Promise<{ name: string; path: string }> {
  return apiFetch("/api/v1/definitions", {
    method: "POST",
    body: JSON.stringify({ name, definition }),
  });
}

export function loadDefinition(
  name: string,
): Promise<{ name: string; definition: Record<string, unknown> }> {
  return apiFetch(`/api/v1/definitions/${encodeURIComponent(name)}`);
}

export function submitJob(definitionPath: string): Promise<JobSummary> {
  return apiFetch("/api/v1/jobs", {
    method: "POST",
    body: JSON.stringify({ definition_path: definitionPath }),
  });
}

export function getJob(jobId: string): Promise<JobSummary> {
  return apiFetch(`/api/v1/jobs/${encodeURIComponent(jobId)}`);
}

export function listJobs(): Promise<{ jobs: JobSummary[] }> {
  return apiFetch("/api/v1/jobs");
}

export function getJobLog(
  jobId: string,
): Promise<{ job_id: string; stdout: string }> {
  return apiFetch(`/api/v1/jobs/${encodeURIComponent(jobId)}/log`);
}

export function cancelJob(jobId: string): Promise<JobSummary> {
  return apiFetch(`/api/v1/jobs/${encodeURIComponent(jobId)}/cancel`, {
    method: "POST",
  });
}
