"use client";

import {
  CableIcon,
  CheckIcon,
  GlobeIcon,
  Loader2Icon,
  PlusIcon,
  SearchIcon,
  ServerIcon,
  Trash2Icon,
  WrenchIcon,
} from "lucide-react";
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
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
  ItemTitle,
} from "@/components/ui/item";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { useI18n } from "@/core/i18n/hooks";
import { MCPConfigRequestError } from "@/core/mcp/api";
import {
  useAddMCPServer,
  useDeleteMCPServer,
  useEnableMCPServer,
  useMCPConfig,
} from "@/core/mcp/hooks";
import { MCP_CATALOG, type MCPCatalogEntry, type MCPServerConfig } from "@/core/mcp/types";
import { env } from "@/env";

import { SettingsSection } from "./settings-section";

const CATEGORY_LABELS: Record<string, string> = {
  dev: "Développement",
  data: "Données",
  search: "Recherche",
  productivity: "Productivité",
  communication: "Communication",
};

const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  dev: <WrenchIcon className="size-3" />,
  data: <ServerIcon className="size-3" />,
  search: <GlobeIcon className="size-3" />,
  productivity: <CheckIcon className="size-3" />,
  communication: <CableIcon className="size-3" />,
};

// ── Page principale ────────────────────────────────────────────────────────

export function MCPSettingsPage() {
  const { t } = useI18n();
  const { config, isLoading, error } = useMCPConfig();
  const { mutate: enableMCPServer } = useEnableMCPServer();
  const { mutateAsync: addServer } = useAddMCPServer();
  const { mutateAsync: deleteServer } = useDeleteMCPServer();
  const [catalogOpen, setCatalogOpen] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);

  const adminRequired =
    error instanceof MCPConfigRequestError && error.isAdminRequired;

  const servers = useMemo(() => {
    if (!config?.mcp_servers) return [];
    return Object.entries(config.mcp_servers);
  }, [config]);

  const handleDelete = async (name: string) => {
    if (deleting) return;
    if (!confirm(`Supprimer le serveur MCP "${name}" ?`)) return;
    setDeleting(name);
    try {
      await deleteServer(name);
      toast.success(`Serveur "${name}" supprimé.`);
    } catch (e) {
      toast.error("Erreur", { description: String(e) });
    } finally {
      setDeleting(null);
    }
  };

  const handleAddFromCatalog = async (entry: MCPCatalogEntry) => {
    try {
      const slug = entry.name.toLowerCase().replace(/\s+/g, "-");
      const newServer: MCPServerConfig = {
        enabled: true,
        type: "stdio",
        command: entry.command,
        args: entry.args,
        env: entry.env,
        headers: {},
        description: entry.description,
      };
      await addServer({ name: slug, server: newServer });
      toast.success(`MCP "${entry.name}" ajouté et activé.`);
      setCatalogOpen(false);
    } catch (e) {
      toast.error("Erreur", { description: String(e) });
    }
  };

  return (
    <SettingsSection
      title="MCP Servers"
      description="Installez et gérez les serveurs MCP (Model Context Protocol). Les serveurs MCP donnent à l'agent l'accès à des outils externes : GitHub, bases de données, recherche web, etc."
    >
      {isLoading ? (
        <div className="text-muted-foreground text-sm">{t.common.loading}</div>
      ) : adminRequired ? (
        <div className="text-muted-foreground text-sm">
          Privilèges administrateur requis pour gérer les MCP.
        </div>
      ) : error ? (
        <div>Error: {error.message}</div>
      ) : (
        <div className="space-y-3">
          {/* ── Liste des serveurs installés ─────────────────────────── */}
          {servers.length === 0 ? (
            <div className="text-muted-foreground text-sm text-center py-8">
              Aucun serveur MCP installé. Ouvrez le catalogue pour en ajouter.
            </div>
          ) : (
            servers.map(([name, srv]) => (
              <Item className="w-full" variant="outline" key={name}>
                <ItemContent>
                  <ItemTitle>
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-sm">{name}</span>
                      {srv.type && (
                        <Badge variant="outline" className="text-xs">
                          {srv.type}
                        </Badge>
                      )}
                    </div>
                  </ItemTitle>
                  <ItemDescription className="line-clamp-2">
                    {srv.description || "Aucune description"}
                  </ItemDescription>
                  {srv.command && (
                    <div className="text-muted-foreground text-xs mt-1 font-mono">
                      {srv.command} {srv.args?.join(" ")}
                    </div>
                  )}
                </ItemContent>
                <ItemActions>
                  <Switch
                    checked={srv.enabled}
                    disabled={env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY === "true"}
                    onCheckedChange={(checked) =>
                      enableMCPServer({ serverName: name, enabled: checked })
                    }
                  />
                  <Button
                    variant="ghost"
                    size="icon"
                    className="size-7 text-destructive hover:text-destructive"
                    disabled={deleting === name}
                    onClick={() => handleDelete(name)}
                  >
                    {deleting === name ? (
                      <Loader2Icon className="size-3.5 animate-spin" />
                    ) : (
                      <Trash2Icon className="size-3.5" />
                    )}
                  </Button>
                </ItemActions>
              </Item>
            ))
          )}

          {/* ── Bouton Ajouter → Catalogue ─────────────────────────── */}
          <Dialog open={catalogOpen} onOpenChange={setCatalogOpen}>
            <DialogTrigger asChild>
              <Button variant="outline" size="sm" className="w-full mt-2">
                <PlusIcon className="size-3.5 mr-2" />
                Installer un MCP depuis le catalogue
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-2xl max-h-[80vh] flex flex-col">
              <DialogHeader>
                <DialogTitle>Catalogue MCP</DialogTitle>
                <DialogDescription>
                  Choisissez un serveur MCP à installer. Il sera immédiatement disponible pour l&apos;agent.
                </DialogDescription>
              </DialogHeader>
              <MCPServerCatalog
                installed={new Set(servers.map(([n]) => n))}
                onInstall={handleAddFromCatalog}
              />
            </DialogContent>
          </Dialog>
        </div>
      )}
    </SettingsSection>
  );
}

// ── Catalogue ──────────────────────────────────────────────────────────────

function MCPServerCatalog({
  installed,
  onInstall,
}: {
  installed: Set<string>;
  onInstall: (entry: MCPCatalogEntry) => void;
}) {
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("all");
  const [installing, setInstalling] = useState<string | null>(null);

  const filtered = useMemo(() => {
    return MCP_CATALOG.filter((entry) => {
      const name = entry.name.toLowerCase().replace(/\s+/g, "-");
      const matchCat = category === "all" || entry.category === category;
      const matchSearch =
        !search ||
        entry.name.toLowerCase().includes(search.toLowerCase()) ||
        entry.description.toLowerCase().includes(search.toLowerCase());
      return matchCat && matchSearch;
    });
  }, [search, category]);

  const handleInstall = async (entry: MCPCatalogEntry) => {
    const slug = entry.name.toLowerCase().replace(/\s+/g, "-");
    setInstalling(slug);
    try {
      await onInstall(entry);
    } finally {
      setInstalling(null);
    }
  };

  return (
    <div className="flex flex-col gap-3 overflow-hidden">
      {/* Filtres */}
      <div className="flex gap-2">
        <div className="relative flex-1">
          <SearchIcon className="absolute left-2.5 top-2.5 size-3.5 text-muted-foreground" />
          <Input
            className="h-8 pl-8 text-sm"
            placeholder="Rechercher un MCP..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <Select value={category} onValueChange={setCategory}>
          <SelectTrigger className="h-8 w-40 text-sm">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Toutes catégories</SelectItem>
            {Object.entries(CATEGORY_LABELS).map(([k, v]) => (
              <SelectItem key={k} value={k}>
                {v}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Liste */}
      <div className="overflow-y-auto max-h-[55vh] space-y-2">
        {filtered.length === 0 && (
          <div className="text-muted-foreground text-sm text-center py-8">
            Aucun MCP trouvé.
          </div>
        )}
        {filtered.map((entry) => {
          const slug = entry.name.toLowerCase().replace(/\s+/g, "-");
          const alreadyInstalled = installed.has(slug);
          return (
            <div
              key={entry.name}
              className="border rounded-lg p-3 flex items-start gap-3 hover:bg-muted/30 transition-colors"
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-medium text-sm">{entry.name}</span>
                  <Badge variant="outline" className="text-xs gap-1">
                    {CATEGORY_ICONS[entry.category]}
                    {CATEGORY_LABELS[entry.category] ?? entry.category}
                  </Badge>
                  {alreadyInstalled && (
                    <Badge variant="outline" className="text-xs text-green-600 border-green-300">
                      <CheckIcon className="size-3 mr-0.5" />
                      Installé
                    </Badge>
                  )}
                </div>
                <p className="text-muted-foreground text-xs mt-1 line-clamp-2">
                  {entry.description}
                </p>
                <code className="text-muted-foreground text-[10px] mt-1 block truncate">
                  {entry.command} {entry.args.join(" ")}
                </code>
              </div>
              <Button
                size="sm"
                variant={alreadyInstalled ? "outline" : "default"}
                disabled={alreadyInstalled || installing === slug}
                onClick={() => handleInstall(entry)}
              >
                {installing === slug ? (
                  <Loader2Icon className="size-3.5 animate-spin mr-1" />
                ) : alreadyInstalled ? (
                  <CheckIcon className="size-3.5 mr-1" />
                ) : (
                  <PlusIcon className="size-3.5 mr-1" />
                )}
                {alreadyInstalled ? "Installé" : "Installer"}
              </Button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
