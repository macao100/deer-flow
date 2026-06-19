"use client";

import { Loader2Icon, SaveIcon } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { type GeneralConfig, type GeneralConfigPatch } from "@/core/app-config/api";
import { useGeneralConfig, usePatchGeneralConfig } from "@/core/app-config/hooks";

import { SettingsSection } from "./settings-section";

function ToggleRow({ label, description, checked, onChange }: {
  label: string;
  description?: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between gap-4 py-2">
      <div className="min-w-0">
        <div className="text-sm font-medium">{label}</div>
        {description && <div className="text-muted-foreground text-xs">{description}</div>}
      </div>
      <Switch checked={checked} onCheckedChange={onChange} />
    </div>
  );
}

function NumberRow({ label, description, value, onChange, min, max, step }: {
  label: string;
  description?: string;
  value: number;
  onChange: (v: number) => void;
  min?: number;
  max?: number;
  step?: number;
}) {
  return (
    <div className="flex items-center justify-between gap-4 py-2">
      <div className="min-w-0">
        <div className="text-sm font-medium">{label}</div>
        {description && <div className="text-muted-foreground text-xs">{description}</div>}
      </div>
      <Input
        type="number"
        value={value}
        min={min}
        max={max}
        step={step ?? 1}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-24 h-8 text-sm text-right"
      />
    </div>
  );
}

export function GeneralSettingsPage() {
  const { data, isLoading } = useGeneralConfig();
  const { mutateAsync: patch, isPending } = usePatchGeneralConfig();
  const [local, setLocal] = useState<GeneralConfig | null>(null);

  useEffect(() => {
    if (data && !local) setLocal(data);
  }, [data, local]);

  if (isLoading || !local) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2Icon className="text-muted-foreground size-5 animate-spin" />
      </div>
    );
  }

  const set = <K extends keyof GeneralConfig>(key: K, value: GeneralConfig[K]) =>
    setLocal((prev) => prev ? { ...prev, [key]: value } : prev);

  const handleSave = async () => {
    if (!local || !data) return;
    const changed: GeneralConfigPatch = {};
    for (const k of Object.keys(local) as (keyof GeneralConfig)[]) {
      if (local[k] !== data[k]) (changed as Record<string, unknown>)[k] = local[k];
    }
    if (Object.keys(changed).length === 0) {
      toast.info("Aucune modification détectée.");
      return;
    }
    try {
      const res = await patch(changed);
      toast.success("Paramètres sauvegardés", { description: res.message });
    } catch (e) {
      toast.error("Erreur lors de la sauvegarde", { description: String(e) });
    }
  };

  const divider = <div className="border-t my-2" />;

  return (
    <div className="space-y-6">
      {/* Agent features */}
      <SettingsSection
        title="Fonctionnalités de l'agent"
        description="Active ou désactive les modules principaux."
      >
        <ToggleRow
          label="Sous-agents (tâches parallèles)"
          description="Permet à l'agent de déléguer des sous-tâches à des agents spécialisés."
          checked={local.subagents_enabled}
          onChange={(v) => set("subagents_enabled", v)}
        />
        {divider}
        <ToggleRow
          label="Détection de boucles"
          description="Arrête l'agent s'il détecte qu'il tourne en boucle sur les mêmes appels d'outils."
          checked={local.loop_detection_enabled}
          onChange={(v) => set("loop_detection_enabled", v)}
        />
        {divider}
        <ToggleRow
          label="Comptage de tokens"
          description="Affiche le nombre de tokens utilisés par échange."
          checked={local.token_usage_enabled}
          onChange={(v) => set("token_usage_enabled", v)}
        />
      </SettingsSection>

      {/* Memory */}
      <SettingsSection
        title="Mémoire"
        description="L'agent apprend de vos conversations pour personnaliser ses réponses."
      >
        <ToggleRow
          label="Activer la mémoire"
          description="Extrait et stocke des faits depuis vos échanges."
          checked={local.memory_enabled}
          onChange={(v) => set("memory_enabled", v)}
        />
        {divider}
        <ToggleRow
          label="Injection de mémoire"
          description="Injecte les faits mémorisés dans le contexte de l'agent à chaque échange."
          checked={local.memory_injection_enabled}
          onChange={(v) => set("memory_injection_enabled", v)}
        />
        {divider}
        <NumberRow
          label="Délai de mise à jour (secondes)"
          description="Temps d'attente après une conversation avant de déclencher l'extraction mémoire."
          value={local.memory_debounce_seconds}
          onChange={(v) => set("memory_debounce_seconds", v)}
          min={5}
          max={300}
        />
        {divider}
        <NumberRow
          label="Nombre max de faits"
          description="Limite du nombre de faits conservés en mémoire."
          value={local.memory_max_facts}
          onChange={(v) => set("memory_max_facts", v)}
          min={10}
          max={500}
        />
        {divider}
        <NumberRow
          label="Tokens max injectés"
          description="Budget de tokens alloué à l'injection mémoire dans le prompt."
          value={local.memory_max_injection_tokens}
          onChange={(v) => set("memory_max_injection_tokens", v)}
          min={500}
          max={8000}
          step={100}
        />
        {divider}
        <NumberRow
          label="Seuil de confiance des faits"
          description="Score minimum (0–1) pour qu'un fait soit conservé."
          value={local.memory_fact_confidence_threshold}
          onChange={(v) => set("memory_fact_confidence_threshold", v)}
          min={0}
          max={1}
          step={0.05}
        />
        {divider}
        <div className="flex items-center justify-between gap-4 py-2">
          <div>
            <div className="text-sm font-medium">Comptage de tokens mémoire</div>
            <div className="text-muted-foreground text-xs">
              <code>tiktoken</code> est précis mais nécessite un accès réseau au premier lancement.
              <code>char</code> est hors-ligne.
            </div>
          </div>
          <Select
            value={local.memory_token_counting}
            onValueChange={(v) => set("memory_token_counting", v)}
          >
            <SelectTrigger className="w-28 h-8 text-sm">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="tiktoken">tiktoken</SelectItem>
              <SelectItem value="char">char</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </SettingsSection>

      {/* Title & summarization */}
      <SettingsSection title="Titre & Résumé" description="Génération automatique du titre et résumé du contexte.">
        <ToggleRow
          label="Génération automatique du titre"
          description="Génère un titre court pour chaque conversation après le premier échange."
          checked={local.title_enabled}
          onChange={(v) => set("title_enabled", v)}
        />
        {divider}
        <NumberRow
          label="Longueur max du titre (mots)"
          value={local.title_max_words}
          onChange={(v) => set("title_max_words", v)}
          min={2}
          max={15}
        />
        {divider}
        <NumberRow
          label="Longueur max du titre (caractères)"
          value={local.title_max_chars}
          onChange={(v) => set("title_max_chars", v)}
          min={20}
          max={200}
        />
        {divider}
        <ToggleRow
          label="Résumé automatique du contexte"
          description="Résume les anciens messages quand la fenêtre de contexte est proche des limites."
          checked={local.summarization_enabled}
          onChange={(v) => set("summarization_enabled", v)}
        />
      </SettingsSection>

      {/* Logging */}
      <SettingsSection title="Journalisation" description="Niveau de détail des logs serveur.">
        <div className="flex items-center justify-between gap-4 py-2">
          <div>
            <div className="text-sm font-medium">Niveau de log</div>
            <div className="text-muted-foreground text-xs">Affecte les modules <code>deerflow</code> et <code>app</code>.</div>
          </div>
          <Select value={local.log_level} onValueChange={(v) => set("log_level", v)}>
            <SelectTrigger className="w-28 h-8 text-sm">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {["debug", "info", "warning", "error"].map((l) => (
                <SelectItem key={l} value={l}>{l}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </SettingsSection>

      <div className="flex justify-end pt-2">
        <Button onClick={handleSave} disabled={isPending} size="sm">
          {isPending ? <Loader2Icon className="size-3.5 animate-spin mr-2" /> : <SaveIcon className="size-3.5 mr-2" />}
          Sauvegarder
        </Button>
      </div>
    </div>
  );
}
