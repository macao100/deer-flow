"use client";

import {
  BrainIcon,
  EyeIcon,
  Loader2Icon,
  PencilIcon,
  PlusIcon,
  SaveIcon,
  Trash2Icon,
  XIcon,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { type ModelCreateRequest, type ModelEntry, type ModelUpdateRequest } from "@/core/app-config/api";
import { useAddModel, useDeleteModel, useModelsConfig, useUpdateModel } from "@/core/app-config/hooks";

import { SettingsSection } from "./settings-section";

// ── Provider labels ───────────────────────────────────────────────────────────
const PROVIDER_LABELS: Record<string, string> = {
  openai: "OpenAI",
  anthropic: "Anthropic",
  deepseek: "DeepSeek",
  openrouter: "OpenRouter",
  nvidia: "NVIDIA NIM",
  groq: "Groq",
  mistral: "Mistral",
  google: "Google Gemini",
  ollama: "Ollama (local)",
};

// ── API key env suggestions per provider ─────────────────────────────────────
const PROVIDER_KEY_ENV: Record<string, string> = {
  openai: "OPENAI_API_KEY",
  anthropic: "ANTHROPIC_API_KEY",
  deepseek: "DEEPSEEK_API_KEY",
  openrouter: "OPENROUTER_API_KEY",
  nvidia: "NVIDIA_API_KEY",
  groq: "GROQ_API_KEY",
  mistral: "MISTRAL_API_KEY",
  google: "GEMINI_API_KEY",
  ollama: "",
};

// ── Default model IDs per provider ───────────────────────────────────────────
const PROVIDER_DEFAULT_MODEL: Record<string, string> = {
  openai: "gpt-4o",
  anthropic: "claude-opus-4-5-20251101",
  deepseek: "deepseek-chat",
  openrouter: "openai/gpt-4o",
  nvidia: "meta/llama-3.3-70b-instruct",
  groq: "llama-3.3-70b-versatile",
  mistral: "mistral-large-latest",
  google: "gemini-2.0-flash",
  ollama: "llama3.2",
};

// ── Edit card for an existing model ──────────────────────────────────────────
function ModelEditCard({ entry, onSave, onCancel }: {
  entry: ModelEntry;
  onSave: (req: ModelUpdateRequest) => Promise<void>;
  onCancel: () => void;
}) {
  const [form, setForm] = useState<ModelUpdateRequest>({
    display_name: entry.display_name ?? "",
    description: entry.description ?? "",
    model: entry.model,
    base_url: entry.base_url ?? "",
    api_key_env: entry.api_key_env ?? "",
    max_tokens: entry.max_tokens,
    timeout: entry.timeout,
    max_retries: entry.max_retries,
    supports_thinking: entry.supports_thinking,
    supports_vision: entry.supports_vision,
    input_price_per_mtok: entry.input_price_per_mtok ?? undefined,
    output_price_per_mtok: entry.output_price_per_mtok ?? undefined,
    fallback_chain: entry.fallback_chain,
  });
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      await onSave(form);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="border-border rounded-lg border bg-muted/30 p-4 space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1">
          <label className="text-xs font-medium">Nom affiché</label>
          <Input className="h-8 text-sm" value={form.display_name ?? ""} onChange={(e) => setForm((p) => ({ ...p, display_name: e.target.value }))} />
        </div>
        <div className="space-y-1">
          <label className="text-xs font-medium">Model ID (provider)</label>
          <Input className="h-8 text-sm font-mono" value={form.model ?? ""} onChange={(e) => setForm((p) => ({ ...p, model: e.target.value }))} />
        </div>
        <div className="space-y-1">
          <label className="text-xs font-medium">Base URL (optionnel)</label>
          <Input className="h-8 text-sm font-mono" placeholder="https://..." value={form.base_url ?? ""} onChange={(e) => setForm((p) => ({ ...p, base_url: e.target.value }))} />
        </div>
        <div className="space-y-1">
          <label className="text-xs font-medium">Variable clé API (sans $)</label>
          <Input className="h-8 text-sm font-mono" placeholder="OPENAI_API_KEY" value={form.api_key_env ?? ""} onChange={(e) => setForm((p) => ({ ...p, api_key_env: e.target.value }))} />
        </div>
        <div className="space-y-1">
          <label className="text-xs font-medium">Max tokens</label>
          <Input type="number" className="h-8 text-sm" value={form.max_tokens ?? 8096} onChange={(e) => setForm((p) => ({ ...p, max_tokens: Number(e.target.value) }))} />
        </div>
        <div className="space-y-1">
          <label className="text-xs font-medium">Timeout (s)</label>
          <Input type="number" className="h-8 text-sm" value={form.timeout ?? 60} onChange={(e) => setForm((p) => ({ ...p, timeout: Number(e.target.value) }))} />
        </div>
        <div className="space-y-1">
          <label className="text-xs font-medium">Prix input ($/1M tok)</label>
          <Input type="number" step="0.001" className="h-8 text-sm" value={form.input_price_per_mtok ?? ""} onChange={(e) => setForm((p) => ({ ...p, input_price_per_mtok: e.target.value ? Number(e.target.value) : undefined }))} />
        </div>
        <div className="space-y-1">
          <label className="text-xs font-medium">Prix output ($/1M tok)</label>
          <Input type="number" step="0.001" className="h-8 text-sm" value={form.output_price_per_mtok ?? ""} onChange={(e) => setForm((p) => ({ ...p, output_price_per_mtok: e.target.value ? Number(e.target.value) : undefined }))} />
        </div>
      </div>
      <div className="flex items-center gap-6 pt-1">
        <label className="flex items-center gap-2 text-sm cursor-pointer">
          <Switch checked={form.supports_thinking ?? false} onCheckedChange={(v) => setForm((p) => ({ ...p, supports_thinking: v }))} />
          <BrainIcon className="size-3.5" /> Thinking
        </label>
        <label className="flex items-center gap-2 text-sm cursor-pointer">
          <Switch checked={form.supports_vision ?? false} onCheckedChange={(v) => setForm((p) => ({ ...p, supports_vision: v }))} />
          <EyeIcon className="size-3.5" /> Vision
        </label>
      </div>
      <div className="flex gap-2 justify-end pt-1">
        <Button variant="ghost" size="sm" onClick={onCancel}><XIcon className="size-3.5 mr-1" />Annuler</Button>
        <Button size="sm" onClick={handleSave} disabled={saving}>
          {saving ? <Loader2Icon className="size-3.5 animate-spin mr-1" /> : <SaveIcon className="size-3.5 mr-1" />}
          Enregistrer
        </Button>
      </div>
    </div>
  );
}

// ── Add model form ────────────────────────────────────────────────────────────
function AddModelForm({ templates, onAdd, onCancel }: {
  templates: Record<string, Record<string, unknown>>;
  onAdd: (req: ModelCreateRequest) => Promise<void>;
  onCancel: () => void;
}) {
  const [provider, setProvider] = useState("openrouter");
  const [name, setName] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [modelId, setModelId] = useState(PROVIDER_DEFAULT_MODEL["openrouter"] ?? "");
  const [apiKeyEnv, setApiKeyEnv] = useState(PROVIDER_KEY_ENV["openrouter"] ?? "");
  const [baseUrl, setBaseUrl] = useState((templates["openrouter"]?.base_url as string) ?? "");
  const [maxTokens, setMaxTokens] = useState(8096);
  const [supportsThinking, setSupportsThinking] = useState(false);
  const [supportsVision, setSupportsVision] = useState(false);
  const [adding, setAdding] = useState(false);

  const handleProviderChange = (p: string) => {
    setProvider(p);
    setModelId(PROVIDER_DEFAULT_MODEL[p] ?? "");
    setApiKeyEnv(PROVIDER_KEY_ENV[p] ?? "");
    setBaseUrl((templates[p]?.base_url as string) ?? "");
    setSupportsThinking(false);
    setSupportsVision(false);
  };

  const handleAdd = async () => {
    if (!name.trim()) { toast.error("Le nom (slug) est requis."); return; }
    if (!modelId.trim()) { toast.error("Le model ID est requis."); return; }
    setAdding(true);
    try {
      await onAdd({
        name: name.trim(),
        display_name: displayName.trim() || undefined,
        provider,
        model: modelId.trim(),
        base_url: baseUrl.trim() || undefined,
        api_key_env: apiKeyEnv.trim() || undefined,
        max_tokens: maxTokens,
        supports_thinking: supportsThinking,
        supports_vision: supportsVision,
      });
    } finally {
      setAdding(false);
    }
  };

  return (
    <div className="border-border rounded-lg border p-4 space-y-3 bg-muted/20">
      <div className="font-medium text-sm">Ajouter un modèle</div>
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1">
          <label className="text-xs font-medium">Provider</label>
          <Select value={provider} onValueChange={handleProviderChange}>
            <SelectTrigger className="h-8 text-sm">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(PROVIDER_LABELS).map(([k, v]) => (
                <SelectItem key={k} value={k}>{v}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1">
          <label className="text-xs font-medium">Nom (slug unique)</label>
          <Input className="h-8 text-sm font-mono" placeholder="gpt-4o-mini" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="space-y-1">
          <label className="text-xs font-medium">Nom affiché (optionnel)</label>
          <Input className="h-8 text-sm" placeholder="GPT-4o mini" value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
        </div>
        <div className="space-y-1">
          <label className="text-xs font-medium">Model ID</label>
          <Input className="h-8 text-sm font-mono" value={modelId} onChange={(e) => setModelId(e.target.value)} />
        </div>
        <div className="space-y-1">
          <label className="text-xs font-medium">Base URL (optionnel)</label>
          <Input className="h-8 text-sm font-mono" placeholder="https://..." value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} />
        </div>
        <div className="space-y-1">
          <label className="text-xs font-medium">Variable clé API (sans $)</label>
          <Input className="h-8 text-sm font-mono" placeholder="OPENROUTER_API_KEY" value={apiKeyEnv} onChange={(e) => setApiKeyEnv(e.target.value)} />
        </div>
        <div className="space-y-1">
          <label className="text-xs font-medium">Max tokens</label>
          <Input type="number" className="h-8 text-sm" value={maxTokens} onChange={(e) => setMaxTokens(Number(e.target.value))} />
        </div>
      </div>
      <div className="flex items-center gap-6 pt-1">
        <label className="flex items-center gap-2 text-sm cursor-pointer">
          <Switch checked={supportsThinking} onCheckedChange={setSupportsThinking} />
          <BrainIcon className="size-3.5" /> Thinking
        </label>
        <label className="flex items-center gap-2 text-sm cursor-pointer">
          <Switch checked={supportsVision} onCheckedChange={setSupportsVision} />
          <EyeIcon className="size-3.5" /> Vision
        </label>
      </div>
      <div className="flex gap-2 justify-end">
        <Button variant="ghost" size="sm" onClick={onCancel}><XIcon className="size-3.5 mr-1" />Annuler</Button>
        <Button size="sm" onClick={handleAdd} disabled={adding}>
          {adding ? <Loader2Icon className="size-3.5 animate-spin mr-1" /> : <PlusIcon className="size-3.5 mr-1" />}
          Ajouter
        </Button>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export function ModelsSettingsPage() {
  const { data, isLoading } = useModelsConfig();
  const { mutateAsync: add } = useAddModel();
  const { mutateAsync: upd } = useUpdateModel();
  const { mutateAsync: del } = useDeleteModel();
  const [editingName, setEditingName] = useState<string | null>(null);
  const [showAdd, setShowAdd] = useState(false);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2Icon className="text-muted-foreground size-5 animate-spin" />
      </div>
    );
  }

  const models = data?.models ?? [];
  const templates = data?.templates ?? {};

  const handleSave = async (name: string, req: ModelUpdateRequest) => {
    try {
      await upd({ name, req });
      toast.success(`Modèle "${name}" mis à jour.`);
      setEditingName(null);
    } catch (e) {
      toast.error("Erreur", { description: String(e) });
    }
  };

  const handleDelete = async (name: string) => {
    if (!confirm(`Supprimer le modèle "${name}" de la configuration ?`)) return;
    try {
      await del(name);
      toast.success(`Modèle "${name}" supprimé.`);
    } catch (e) {
      toast.error("Erreur", { description: String(e) });
    }
  };

  const handleAdd = async (req: Parameters<typeof add>[0]) => {
    try {
      await add(req);
      toast.success(`Modèle "${req.name}" ajouté.`);
      setShowAdd(false);
    } catch (e) {
      toast.error("Erreur", { description: String(e) });
    }
  };

  return (
    <SettingsSection
      title="Modèles LLM"
      description="Configurez les modèles disponibles dans DeerFlow. Les modifications sont écrites dans config.yaml et appliquées à la prochaine requête (hot-reload)."
    >
      <div className="space-y-3">
        {models.map((m) => (
          <div key={m.name}>
            {editingName === m.name ? (
              <ModelEditCard
                entry={m}
                onSave={(req) => handleSave(m.name, req)}
                onCancel={() => setEditingName(null)}
              />
            ) : (
              <div className="border-border rounded-lg border px-4 py-3 flex items-center gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-medium text-sm">{m.display_name ?? m.name}</span>
                    <code className="text-muted-foreground text-xs bg-muted rounded px-1">{m.name}</code>
                    {m.provider && (
                      <Badge variant="outline" className="text-xs">{PROVIDER_LABELS[m.provider] ?? m.provider}</Badge>
                    )}
                    {m.supports_thinking && (
                      <Badge variant="outline" className="text-xs gap-1 text-purple-600 border-purple-300">
                        <BrainIcon className="size-3" />thinking
                      </Badge>
                    )}
                    {m.supports_vision && (
                      <Badge variant="outline" className="text-xs gap-1 text-blue-600 border-blue-300">
                        <EyeIcon className="size-3" />vision
                      </Badge>
                    )}
                  </div>
                  <div className="text-muted-foreground text-xs mt-0.5 truncate">
                    {m.model}
                    {m.base_url && <> · <span className="font-mono">{m.base_url}</span></>}
                    {m.api_key_env && <> · <span className="font-mono">${m.api_key_env}</span></>}
                  </div>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <Button variant="ghost" size="icon" className="size-7" onClick={() => setEditingName(m.name)}>
                    <PencilIcon className="size-3.5" />
                  </Button>
                  <Button variant="ghost" size="icon" className="size-7 text-destructive hover:text-destructive" onClick={() => handleDelete(m.name)}>
                    <Trash2Icon className="size-3.5" />
                  </Button>
                </div>
              </div>
            )}
          </div>
        ))}

        {models.length === 0 && (
          <div className="text-muted-foreground text-sm text-center py-8">
            Aucun modèle configuré. Ajoutez-en un ci-dessous.
          </div>
        )}

        {showAdd ? (
          <AddModelForm
            templates={templates}
            onAdd={handleAdd}
            onCancel={() => setShowAdd(false)}
          />
        ) : (
          <Button variant="outline" size="sm" onClick={() => setShowAdd(true)} className="w-full mt-2">
            <PlusIcon className="size-3.5 mr-2" />
            Ajouter un modèle
          </Button>
        )}
      </div>
    </SettingsSection>
  );
}
