import { fetch } from "@/core/api/fetcher";
import { getBackendBaseURL } from "@/core/config";

export type ApiKeyEntry = {
  env_var: string;
  label: string;
  provider: string;
  placeholder: string;
  docs_url: string;
  is_set: boolean;
  masked_value: string;
};

export type ApiKeysResponse = {
  keys: ApiKeyEntry[];
};

export type UpdateApiKeyRequest = {
  env_var: string;
  value: string;
};

export type UpdateApiKeyResponse = {
  success: boolean;
  restart_required: boolean;
  message: string;
};

export async function loadApiKeys(): Promise<ApiKeysResponse> {
  const response = await fetch(`${getBackendBaseURL()}/api/settings/api-keys`);
  if (!response.ok) {
    throw new Error(`Failed to load API keys: ${response.statusText}`);
  }
  return response.json() as Promise<ApiKeysResponse>;
}

export async function updateApiKey(request: UpdateApiKeyRequest): Promise<UpdateApiKeyResponse> {
  const response = await fetch(`${getBackendBaseURL()}/api/settings/api-keys`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error((err as { detail?: string }).detail ?? response.statusText);
  }
  return response.json() as Promise<UpdateApiKeyResponse>;
}
