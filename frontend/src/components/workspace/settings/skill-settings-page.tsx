"use client";

import {
  AlertTriangleIcon,
  CheckCircleIcon,
  DownloadIcon,
  GlobeIcon,
  LightbulbIcon,
  Loader2Icon,
  PencilIcon,
  PlusIcon,
  SaveIcon,
  SearchIcon,
  ShieldAlertIcon,
  SparklesIcon,
  Trash2Icon,
  XIcon,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
  ItemTitle,
} from "@/components/ui/item";
import { useI18n } from "@/core/i18n/hooks";
import {
  useCreateSkill,
  useDeleteSkill,
  useEnableSkill,
  useScanSkill,
  useSkills,
  useUpdateSkill,
} from "@/core/skills/hooks";
import { SKILL_CATALOG, type Skill, type SkillScanResult } from "@/core/skills/type";
import { env } from "@/env";

import { SettingsSection } from "./settings-section";

const CATEGORY_ICONS: Record<string, string> = {
  research: "🔍",
  creation: "✨",
  analysis: "📊",
  dev: "🛠️",
  design: "🎨",
};
const CATEGORY_LABELS: Record<string, string> = {
  research: "Recherche",
  creation: "Création",
  analysis: "Analyse",
  dev: "Développement",
  design: "Design",
};

// ── Template SKILL.md ─────────────────────────────────────────────────────
const SKILL_TEMPLATE = `---
name: mon-skill
description: Description courte de ce que fait le skill.
allowed-tools: []
---

# Mon Skill

## Vue d'ensemble
Décrivez ce que fait ce skill.

## Quand l'utiliser
Expliquez dans quelles situations ce skill doit être activé.

## Instructions
Étapes détaillées pour exécuter ce skill.
`;

// ── Page principale ────────────────────────────────────────────────────────

export function SkillSettingsPage({ onClose }: { onClose?: () => void }) {
  const { t } = useI18n();
  const router = useRouter();
  const { skills, isLoading, error } = useSkills();
  const { mutate: enableSkill } = useEnableSkill();
  const { mutateAsync: deleteSkill } = useDeleteSkill();
  const [filter, setFilter] = useState<string>("all");
  const [search, setSearch] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [catalogOpen, setCatalogOpen] = useState(false);
  const [editingName, setEditingName] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  const publicSkills = useMemo(() => skills.filter((s) => s.category === "public"), [skills]);
  const customSkills = useMemo(() => skills.filter((s) => s.category === "custom"), [skills]);

  const filteredSkills = useMemo(() => {
    let list = filter === "public" ? publicSkills : filter === "custom" ? customSkills : skills;
    if (search) {
      const q = search.toLowerCase();
      list = list.filter((s) => s.name.toLowerCase().includes(q) || s.description.toLowerCase().includes(q));
    }
    return list;
  }, [filter, publicSkills, customSkills, skills, search]);

  const handleDelete = async (name: string) => {
    if (deleting) return;
    if (!confirm(`Supprimer définitivement le skill "${name}" ?`)) return;
    setDeleting(name);
    try {
      await deleteSkill(name);
      toast.success(`Skill "${name}" supprimé.`);
    } catch (e) {
      toast.error("Erreur", { description: String(e) });
    } finally {
      setDeleting(null);
    }
  };

  const handleCreateSkill = () => {
    onClose?.();
    router.push("/workspace/chats/new?mode=skill");
  };

  if (isLoading) {
    return (
      <SettingsSection title={t.settings.skills.title} description={t.settings.skills.description}>
        <div className="text-muted-foreground text-sm">{t.common.loading}</div>
      </SettingsSection>
    );
  }

  if (error) {
    return (
      <SettingsSection title={t.settings.skills.title} description={t.settings.skills.description}>
        <div>Error: {error.message}</div>
      </SettingsSection>
    );
  }

  return (
    <>
      <SettingsSection title={t.settings.skills.title} description={t.settings.skills.description}>
      <div className="flex flex-col gap-4">
        {/* ── Toolbar ─────────────────────────────────────────────── */}
        <header className="flex justify-between gap-3 flex-wrap">
          <div className="flex gap-2 items-center">
            <div className="relative w-48">
              <SearchIcon className="absolute left-2.5 top-2.5 size-3.5 text-muted-foreground" />
              <Input
                className="h-8 pl-8 text-sm"
                placeholder="Rechercher..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <Tabs value={filter} onValueChange={setFilter}>
              <TabsList variant="line">
                <TabsTrigger value="all">Tous</TabsTrigger>
                <TabsTrigger value="public">Publics</TabsTrigger>
                <TabsTrigger value="custom">Custom</TabsTrigger>
              </TabsList>
            </Tabs>
          </div>
          <div className="flex gap-2">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button size="sm">
                  <PlusIcon className="size-4 mr-1" />
                  Ajouter un skill
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuItem onClick={() => setShowCreate(true)}>
                  <PencilIcon className="size-4 mr-2" />
                  Créer manuellement
                </DropdownMenuItem>
                <DropdownMenuItem onClick={handleCreateSkill}>
                  <SparklesIcon className="size-4 mr-2" />
                  Créer avec l&apos;IA
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setCatalogOpen(true)}>
                  <GlobeIcon className="size-4 mr-2" />
                  Catalogue en ligne
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>

        {/* ── Liste des skills ────────────────────────────────────── */}
        {filteredSkills.length === 0 && (
          <Empty>
            <EmptyHeader>
              <EmptyMedia variant="icon"><SparklesIcon /></EmptyMedia>
              <EmptyTitle>{t.settings.skills.emptyTitle}</EmptyTitle>
              <EmptyDescription>{t.settings.skills.emptyDescription}</EmptyDescription>
            </EmptyHeader>
            <EmptyContent>
              <Button onClick={() => setShowCreate(true)}>
                {t.settings.skills.emptyButton}
              </Button>
            </EmptyContent>
          </Empty>
        )}
        {filteredSkills.map((skill) => (
          <Item className="w-full" variant="outline" key={skill.name}>
            <ItemContent>
              <ItemTitle>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-medium text-sm">{skill.name}</span>
                  <Badge variant="outline" className="text-xs">
                    {skill.category === "public" ? "Public" : "Custom"}
                  </Badge>
                  {skill.license && (
                    <Badge variant="outline" className="text-xs text-muted-foreground">
                      {skill.license}
                    </Badge>
                  )}
                </div>
              </ItemTitle>
              <ItemDescription className="line-clamp-2">
                {skill.description}
              </ItemDescription>
            </ItemContent>
            <ItemActions>
              <Switch
                checked={skill.enabled}
                disabled={env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY === "true"}
                onCheckedChange={(checked) =>
                  enableSkill({ skillName: skill.name, enabled: checked })
                }
              />
              {skill.category === "custom" && (
                <>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="size-7"
                    onClick={() => setEditingName(skill.name)}
                  >
                    <PencilIcon className="size-3.5" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="size-7 text-destructive hover:text-destructive"
                    disabled={deleting === skill.name}
                    onClick={() => handleDelete(skill.name)}
                  >
                    {deleting === skill.name ? (
                      <Loader2Icon className="size-3.5 animate-spin" />
                    ) : (
                      <Trash2Icon className="size-3.5" />
                    )}
                  </Button>
                </>
              )}
            </ItemActions>
          </Item>
        ))}

        {/* ── Catalogue public ────────────────────────────────────── */}
        {filter === "public" && publicSkills.length === 0 && (
          <SkillCatalog onClose={() => {}} />
        )}

        {/* ── Création / Édition ──────────────────────────────────── */}
        {showCreate && (
          <SkillEditor
            mode="create"
            onClose={() => setShowCreate(false)}
          />
        )}
        {editingName && (
          <SkillEditor
            mode="edit"
            skillName={editingName}
            onClose={() => setEditingName(null)}
          />
        )}
      </div>
    </SettingsSection>

    {/* ── Dialogue catalogue en ligne ──────────────────────────── */}
    <Dialog open={catalogOpen} onOpenChange={setCatalogOpen}>
      <DialogContent className="sm:max-w-2xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Catalogue de skills</DialogTitle>
          <DialogDescription>
            Parcourez les skills disponibles. Vous pourrez bientôt les installer en un clic depuis des repos en ligne.
          </DialogDescription>
        </DialogHeader>
        <SkillCatalog onClose={() => setCatalogOpen(false)} />
      </DialogContent>
    </Dialog>
    </>
  );
}

// ── Catalogue des skills publics ──────────────────────────────────────────

function SkillCatalog({ onClose }: { onClose: () => void }) {
  return (
    <div className="border rounded-lg p-4 bg-muted/20">
      <div className="flex items-center gap-2 mb-3">
        <LightbulbIcon className="size-4 text-amber-500" />
        <span className="font-medium text-sm">Skills publics disponibles</span>
      </div>
      <div className="grid grid-cols-2 gap-2">
        {SKILL_CATALOG.map((entry) => (
          <div key={entry.name} className="border rounded-lg p-3 bg-background flex items-start gap-3">
            <span className="text-lg mt-0.5 shrink-0">{entry.icon}</span>
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <code className="font-medium text-xs">{entry.name}</code>
                <Badge variant="outline" className="text-[10px]">
                  {CATEGORY_LABELS[entry.category] ?? entry.category}
                </Badge>
              </div>
              <p className="text-muted-foreground text-xs mt-1 line-clamp-2">{entry.description}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Éditeur de skill (création / édition) ─────────────────────────────────

function SkillEditor({
  mode,
  skillName,
  onClose,
}: {
  mode: "create" | "edit";
  skillName?: string;
  onClose: () => void;
}) {
  const [name, setName] = useState(skillName ?? "");
  const [content, setContent] = useState(mode === "create" ? SKILL_TEMPLATE : "");
  const [contentLoaded, setContentLoaded] = useState(mode === "create");
  const [scanResult, setScanResult] = useState<SkillScanResult | null>(null);
  const [scanning, setScanning] = useState(false);
  const [saving, setSaving] = useState(false);

  const { mutateAsync: createSkill } = useCreateSkill();
  const { mutateAsync: updateSkill } = useUpdateSkill();
  const { mutateAsync: scanSkill } = useScanSkill();

  // Charger le contenu existant en mode édition
  useMemo(() => {
    if (mode === "edit" && skillName && !contentLoaded) {
      import("@/core/skills/api").then((api) => {
        api.getCustomSkill(skillName).then((s) => {
          setContent(s.content);
          setContentLoaded(true);
        }).catch(() => toast.error("Impossible de charger le skill"));
      });
    }
  }, [mode, skillName, contentLoaded]);

  const handleScan = async () => {
    if (!content.trim()) return;
    setScanning(true);
    setScanResult(null);
    try {
      const result = await scanSkill({ content, skillName: name || undefined });
      setScanResult(result);
    } catch (e) {
      toast.error("Scan échoué", { description: String(e) });
    } finally {
      setScanning(false);
    }
  };

  const handleSave = async () => {
    if (mode === "create" && !name.trim()) {
      toast.error("Le nom du skill est requis.");
      return;
    }
    if (!content.trim()) {
      toast.error("Le contenu SKILL.md est requis.");
      return;
    }
    setSaving(true);
    try {
      if (mode === "create") {
        await createSkill({ name: name.trim(), content });
        toast.success(`Skill "${name.trim()}" créé.`);
      } else if (skillName) {
        await updateSkill({ name: skillName, content });
        toast.success(`Skill "${skillName}" mis à jour.`);
      }
      onClose();
    } catch (e) {
      toast.error("Erreur", { description: String(e) });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="border-border rounded-lg border bg-muted/20 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {mode === "create" ? (
            <PlusIcon className="size-4 text-green-500" />
          ) : (
            <PencilIcon className="size-4 text-blue-500" />
          )}
          <span className="font-medium text-sm">
            {mode === "create" ? "Créer un nouveau skill" : `Éditer "${skillName}"`}
          </span>
        </div>
        <Button variant="ghost" size="icon" className="size-7" onClick={onClose}>
          <XIcon className="size-3.5" />
        </Button>
      </div>

      {mode === "create" && (
        <div className="space-y-1">
          <label className="text-xs font-medium">Nom (slug unique)</label>
          <Input
            className="h-8 text-sm font-mono"
            placeholder="mon-skill"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>
      )}

      <div className="space-y-1">
        <div className="flex items-center justify-between">
          <label className="text-xs font-medium">SKILL.md</label>
          <Button
            variant="outline"
            size="sm"
            className="h-6 text-xs"
            disabled={scanning || !content.trim()}
            onClick={handleScan}
          >
            {scanning ? (
              <Loader2Icon className="size-3 animate-spin mr-1" />
            ) : (
              <ShieldAlertIcon className="size-3 mr-1" />
            )}
            Scanner
          </Button>
        </div>
        <Textarea
          className="min-h-[200px] text-xs font-mono"
          placeholder={SKILL_TEMPLATE}
          value={content}
          onChange={(e) => setContent(e.target.value)}
        />
      </div>

      {/* Résultat du scan */}
      {scanResult && (
        <div
          className={`border rounded-lg p-3 flex items-start gap-3 ${
            scanResult.decision === "allow"
              ? "border-green-300 bg-green-50 dark:bg-green-950/20"
              : scanResult.decision === "warn"
                ? "border-amber-300 bg-amber-50 dark:bg-amber-950/20"
                : "border-red-300 bg-red-50 dark:bg-red-950/20"
          }`}
        >
          {scanResult.decision === "allow" ? (
            <CheckCircleIcon className="size-5 text-green-600 shrink-0 mt-0.5" />
          ) : scanResult.decision === "warn" ? (
            <AlertTriangleIcon className="size-5 text-amber-600 shrink-0 mt-0.5" />
          ) : (
            <ShieldAlertIcon className="size-5 text-red-600 shrink-0 mt-0.5" />
          )}
          <div>
            <span className="font-medium text-sm">
              {scanResult.decision === "allow"
                ? "✅ Accepté"
                : scanResult.decision === "warn"
                  ? "⚠️ Attention"
                  : "🛑 Bloqué"}
            </span>
            <p className="text-xs mt-1 text-muted-foreground">{scanResult.reason}</p>
          </div>
        </div>
      )}

      <div className="flex gap-2 justify-end">
        <Button variant="ghost" size="sm" onClick={onClose}>
          Annuler
        </Button>
        <Button
          size="sm"
          onClick={handleSave}
          disabled={saving || scanResult?.decision === "block"}
        >
          {saving ? (
            <Loader2Icon className="size-3.5 animate-spin mr-1" />
          ) : (
            <SaveIcon className="size-3.5 mr-1" />
          )}
          {mode === "create" ? "Créer" : "Enregistrer"}
        </Button>
      </div>
    </div>
  );
}
