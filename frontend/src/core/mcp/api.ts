import { fetch } from "@/core/api/fetcher";
import { getBackendBaseURL } from "@/core/config";

import type { MCPConfig, MCPSecurityScanResult, RegistrySearchResponse } from "./types";

export class MCPConfigRequestError extends Error {
  readonly status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "MCPConfigRequestError";
    this.status = status;
  }
  get isAdminRequired(): boolean {
    return this.status === 403;
  }
}

async function readErrorDetail(
  response: Response,
  fallback: string,
): Promise<string> {
  const error = (await response.json().catch(() => ({}))) as {
    detail?: unknown;
  };
  return typeof error.detail === "string" ? error.detail : fallback;
}

export async function loadMCPConfig() {
  const response = await fetch(`${getBackendBaseURL()}/api/mcp/config`);
  if (!response.ok) {
    throw new MCPConfigRequestError(
      response.status,
      await readErrorDetail(response, "Failed to load MCP configuration"),
    );
  }
  return response.json() as Promise<MCPConfig>;
}

export async function searchMCPCatalog(
  q: string = "",
  cursor: string = "",
  count: number = 30,
): Promise<RegistrySearchResponse> {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (cursor) params.set("cursor", cursor);
  params.set("count", String(count));

  const response = await fetch(
    `${getBackendBaseURL()}/api/mcp/catalog/search?${params}`,
  );
  if (!response.ok) {
    throw new Error(
      `Catalog search failed: ${response.status} ${response.statusText}`,
    );
  }
  return response.json() as Promise<RegistrySearchResponse>;
}

export async function updateMCPConfig(config: MCPConfig) {
  const response = await fetch(`${getBackendBaseURL()}/api/mcp/config`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(config),
  });
  if (!response.ok) {
    throw new MCPConfigRequestError(
      response.status,
      await readErrorDetail(response, "Failed to update MCP configuration"),
    );
  }
  return response.json();
}

// ── Security scan ───────────────────────────────────────────────────────

export async function scanMCPServer(server: {
  enabled: boolean;
  type: string;
  command?: string | null;
  args: string[];
  env: Record<string, string>;
  url?: string | null;
  headers: Record<string, string>;
  description: string;
}): Promise<MCPSecurityScanResult> {
  const response = await fetch(`${getBackendBaseURL()}/api/mcp/scan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(server),
  });
  if (!response.ok) {
    throw new Error(
      `MCP scan failed: ${response.status} ${response.statusText}`,
    );
  }
  return response.json() as Promise<MCPSecurityScanResult>;
}
