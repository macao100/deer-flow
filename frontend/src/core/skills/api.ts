import { fetch } from "@/core/api/fetcher";
import { getBackendBaseURL } from "@/core/config";

import type { CustomSkillContent, Skill, SkillScanResult } from "./type";

export async function loadSkills(): Promise<Skill[]> {
  const res = await fetch(`${getBackendBaseURL()}/api/skills`);
  const json = await res.json();
  return json.skills as Skill[];
}

export async function enableSkill(skillName: string, enabled: boolean) {
  const response = await fetch(
    `${getBackendBaseURL()}/api/skills/${skillName}`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled }),
    },
  );
  return response.json();
}

// ── Custom skills CRUD ──────────────────────────────────────────────────

export async function getCustomSkill(name: string): Promise<CustomSkillContent> {
  const res = await fetch(`${getBackendBaseURL()}/api/skills/custom/${name}`);
  if (!res.ok) throw new Error((await res.json().catch(() => ({})))?.detail ?? "Failed to load skill");
  return res.json();
}

export async function createCustomSkill(
  name: string,
  content: string,
): Promise<CustomSkillContent> {
  const res = await fetch(`${getBackendBaseURL()}/api/skills/custom`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, content }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

export async function updateCustomSkill(
  name: string,
  content: string,
): Promise<CustomSkillContent> {
  const res = await fetch(`${getBackendBaseURL()}/api/skills/custom/${name}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

export async function deleteCustomSkill(name: string): Promise<void> {
  const res = await fetch(`${getBackendBaseURL()}/api/skills/custom/${name}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
}

// ── Security scan ───────────────────────────────────────────────────────

export async function scanSkillContent(
  content: string,
  skillName?: string,
): Promise<SkillScanResult> {
  const res = await fetch(`${getBackendBaseURL()}/api/skills/custom/scan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content, skill_name: skillName ?? null }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Scan failed");
  }
  return res.json();
}

// ── Install from .skill file ────────────────────────────────────────────

export interface InstallSkillRequest {
  thread_id: string;
  path: string;
}

export interface InstallSkillResponse {
  success: boolean;
  skill_name: string;
  message: string;
}

export async function installSkill(
  request: InstallSkillRequest,
): Promise<InstallSkillResponse> {
  const response = await fetch(`${getBackendBaseURL()}/api/skills/install`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const errorMessage =
      errorData.detail ?? `HTTP ${response.status}: ${response.statusText}`;
    return { success: false, skill_name: "", message: errorMessage };
  }
  return response.json();
}
