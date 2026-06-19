import { fetch } from "@/core/api/fetcher";
import { getBackendBaseURL } from "@/core/config";

function url(path: string) {
  return `${getBackendBaseURL()}/api/settings${path}`;
}

// ── General config ────────────────────────────────────────────────────────────

export type GeneralConfig = {
  log_level: string;
  token_usage_enabled: boolean;
  title_enabled: boolean;
  title_max_words: number;
  title_max_chars: number;
  summarization_enabled: boolean;
  memory_enabled: boolean;
  memory_injection_enabled: boolean;
  memory_debounce_seconds: number;
  memory_max_facts: number;
  memory_fact_confidence_threshold: number;
  memory_max_injection_tokens: number;
  memory_token_counting: string;
  subagents_enabled: boolean;
  loop_detection_enabled: boolean;
};

export type GeneralConfigPatch = Partial<GeneralConfig>;

export type ConfigWriteResponse = {
  success: boolean;
  message: string;
  restart_required: boolean;
};

export async function loadGeneralConfig(): Promise<GeneralConfig> {
  const r = await fetch(url("/config"));
  if (!r.ok) throw new Error(`Failed to load config: ${r.statusText}`);
  return r.json() as Promise<GeneralConfig>;
}

export async function patchGeneralConfig(patch: GeneralConfigPatch): Promise<ConfigWriteResponse> {
  const r = await fetch(url("/config"), {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: r.statusText }));
    throw new Error((err as { detail?: string }).detail ?? r.statusText);
  }
  return r.json() as Promise<ConfigWriteResponse>;
}

// ── Models config ─────────────────────────────────────────────────────────────

export type ModelEntry = {
  name: string;
  display_name: string | null;
  description: string | null;
  provider: string | null;
  model: string;
  use: string;
  base_url: string | null;
  api_key_env: string | null;
  max_tokens: number;
  timeout: number;
  max_retries: number;
  supports_thinking: boolean;
  supports_vision: boolean;
  supports_reasoning_effort: boolean;
  input_price_per_mtok: number | null;
  output_price_per_mtok: number | null;
  fallback_chain: string[];
};

export type ModelTemplate = Record<string, unknown>;

export type ModelsConfigResponse = {
  models: ModelEntry[];
  templates: Record<string, ModelTemplate>;
};

export type ModelCreateRequest = {
  name: string;
  display_name?: string;
  description?: string;
  provider: string;
  model: string;
  base_url?: string;
  api_key_env?: string;
  max_tokens?: number;
  timeout?: number;
  max_retries?: number;
  supports_thinking?: boolean;
  supports_vision?: boolean;
  input_price_per_mtok?: number;
  output_price_per_mtok?: number;
  fallback_chain?: string[];
};

export type ModelUpdateRequest = Partial<Omit<ModelCreateRequest, "name" | "provider">>;

async function throwIfFailed(r: Response): Promise<void> {
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: r.statusText }));
    throw new Error((err as { detail?: string }).detail ?? r.statusText);
  }
}

export async function loadModelsConfig(): Promise<ModelsConfigResponse> {
  const r = await fetch(url("/models"));
  if (!r.ok) throw new Error(`Failed to load models: ${r.statusText}`);
  return r.json() as Promise<ModelsConfigResponse>;
}

export async function addModel(req: ModelCreateRequest): Promise<ConfigWriteResponse> {
  const r = await fetch(url("/models"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  await throwIfFailed(r);
  return r.json() as Promise<ConfigWriteResponse>;
}

export async function updateModel(name: string, req: ModelUpdateRequest): Promise<ConfigWriteResponse> {
  const r = await fetch(url(`/models/${encodeURIComponent(name)}`), {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  await throwIfFailed(r);
  return r.json() as Promise<ConfigWriteResponse>;
}

export async function deleteModel(name: string): Promise<ConfigWriteResponse> {
  const r = await fetch(url(`/models/${encodeURIComponent(name)}`), { method: "DELETE" });
  await throwIfFailed(r);
  return r.json() as Promise<ConfigWriteResponse>;
}
