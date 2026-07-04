"use client";

import {
  AlertTriangleIcon,
  CableIcon,
  CheckCircleIcon,
  CheckIcon,
  GlobeIcon,
  Loader2Icon,
  PlusIcon,
  SearchIcon,
  ServerIcon,
  ShieldAlertIcon,
  Trash2Icon,
  WrenchIcon,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
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
import { MCPConfigRequestError, scanMCPServer, searchMCPCatalog } from "@/core/mcp/api";
import {
  useAddMCPServer,
  useDeleteMCPServer,
  useEnableMCPServer,
  useMCPConfig,
} from "@/core/mcp/hooks";
import {
  MCP_CATALOG,
  type MCPCatalogEntry,
  type MCPSecurityScanResult,
  type MCPServerConfig,
  type RegistryMCPServer,
} from "@/core/mcp/types";
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
  const [scanOpen, setScanOpen] = useState(false);
  const [scanResult, setScanResult] = useState<MCPSecurityScanResult | null>(null);
  const [scanning, setScanning] = useState(false);
  const [pendingEntry, setPendingEntry] = useState<MCPCatalogEntry | RegistryMCPServer | null>(null);
  const [pendingServer, setPendingServer] = useState<MCPServerConfig | null>(null);
  const [pendingName, setPendingName] = useState("");

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

  const handleAddFromCatalog = async (entry: MCPCatalogEntry | RegistryMCPServer) => {
    try {
      let name: string;
      let newServer: MCPServerConfig;

      if ("source" in entry) {
        // Registry entry
        name = entry.name;
        if (entry.transport_type === "stdio" && entry.command) {
          newServer = {
            enabled: true,
            type: "stdio",
            command: entry.command,
            args: entry.args,
            env: entry.env,
            headers: {},
            description: entry.description,
          };
        } else if (entry.url) {
          newServer = {
            enabled: true,
            type: entry.transport_type === "sse" ? "sse" : "http",
            command: null,
            args: [],
            env: entry.env,
            url: entry.url,
            headers: {},
            description: entry.description,
          };
        } else {
          toast.error("Impossible d'installer ce serveur : aucune commande ni URL.");
          return;
        }
      } else {
        // Local catalog entry
        name = entry.name.toLowerCase().replace(/\s+/g, "-");
        newServer = {
          enabled: true,
          type: "stdio",
          command: entry.command,
          args: entry.args,
          env: entry.env,
          headers: {},
          description: entry.description,
        };
      }

      // ── Security scan before install ──────────────────────────────
      setPendingEntry(entry);
      setPendingServer(newServer);
      setPendingName(name);
      setScanning(true);
      setScanResult(null);
      setScanOpen(true);

      const result = await scanMCPServer(newServer);
      setScanResult(result);
    } catch (e) {
      toast.error("Erreur", { description: String(e) });
      setScanOpen(false);
    } finally {
      setScanning(false);
    }
  };

  const handleConfirmInstall = async () => {
    if (!pendingServer || !pendingName || !pendingEntry) return;
    try {
      await addServer({ name: pendingName, server: pendingServer });
      const entry = pendingEntry;
      const displayName = "source" in entry
        ? (entry as RegistryMCPServer).title || (entry as RegistryMCPServer).name
        : (entry as MCPCatalogEntry).name;
      toast.success(`MCP "${displayName}" ajouté et activé.`);
      setScanOpen(false);
      setCatalogOpen(false);
      setPendingEntry(null);
      setPendingServer(null);
      setScanResult(null);
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

          {/* ── Dialogue scan de sécurité ─────────────────────────── */}
          <Dialog open={scanOpen} onOpenChange={(open) => { if (!scanning) setScanOpen(open); }}>
            <DialogContent className="sm:max-w-lg">
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2">
                  <ShieldAlertIcon className="size-5" />
                  Scan de sécurité
                </DialogTitle>
                <DialogDescription>
                  {pendingEntry && (
                    <>Analyse de sécurité pour <strong>{"source" in pendingEntry ? (pendingEntry as RegistryMCPServer).title || pendingEntry.name : pendingEntry.name}</strong></>
                  )}
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-3">
                {/* Loading */}
                {scanning && (
                  <div className="flex items-center gap-3 text-muted-foreground py-4">
                    <Loader2Icon className="size-5 animate-spin" />
                    <span>Analyse en cours...</span>
                  </div>
                )}

                {/* Scan result */}
                {!scanning && scanResult && (
                  <>
                    <div
                      className={`border rounded-lg p-4 flex items-start gap-3 ${
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
                      <div className="min-w-0">
                        <p className="font-medium text-sm">
                          {scanResult.decision === "allow"
                            ? "✅ Aucun problème détecté"
                            : scanResult.decision === "warn"
                              ? "⚠️ Points d'attention"
                              : "🛑 Installation bloquée"}
                        </p>
                        <p className="text-xs text-muted-foreground mt-0.5">
                          Score de sécurité : {scanResult.score}/100
                        </p>
                        {scanResult.reasons.length > 0 && (
                          <ul className="mt-2 space-y-1">
                            {scanResult.reasons.map((reason, i) => (
                              <li key={i} className="text-xs flex items-start gap-1.5">
                                <span className="text-muted-foreground mt-0.5">•</span>
                                <span>{reason}</span>
                              </li>
                            ))}
                          </ul>
                        )}
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex gap-2 justify-end">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => { setScanOpen(false); setPendingEntry(null); setPendingServer(null); setScanResult(null); }}
                      >
                        Annuler
                      </Button>
                      {scanResult.decision !== "block" && (
                        <Button
                          size="sm"
                          onClick={handleConfirmInstall}
                          variant={scanResult.decision === "warn" ? "outline" : "default"}
                        >
                          {scanResult.decision === "warn" ? "Installer malgré l'avertissement" : "Installer"}
                        </Button>
                      )}
                    </div>
                  </>
                )}
              </div>
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
  onInstall: (entry: MCPCatalogEntry | RegistryMCPServer) => void;
}) {
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("all");
  const [installing, setInstalling] = useState<string | null>(null);
  const [registryResults, setRegistryResults] = useState<RegistryMCPServer[]>([]);
  const [registryLoading, setRegistryLoading] = useState(false);

  // ── Recherche registre (debounced) ──────────────────────────────────
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  useEffect(() => {
    if (search.length < 2) {
      setRegistryResults([]);
      setRegistryLoading(false);
      return;
    }
    setRegistryLoading(true);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      try {
        const res = await searchMCPCatalog(search, "", 15);
        setRegistryResults(res.servers);
      } catch {
        setRegistryResults([]);
      } finally {
        setRegistryLoading(false);
      }
    }, 400);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [search]);

  // ── Filtrage local ─────────────────────────────────────────────────
  const localFiltered = useMemo(() => {
    return MCP_CATALOG.filter((entry) => {
      const matchCat = category === "all" || entry.category === category;
      const matchSearch =
        !search ||
        entry.name.toLowerCase().includes(search.toLowerCase()) ||
        entry.description.toLowerCase().includes(search.toLowerCase());
      return matchCat && matchSearch;
    });
  }, [search, category]);

  // ── Merge local + registre ──────────────────────────────────────────
  const merged = useMemo(() => {
    if (!search || search.length < 2) {
      return localFiltered.map((e) => ({ ...e, _type: "local" as const }));
    }
    const regNames = new Set(registryResults.map((r) => r.name));
    const local = localFiltered
      .filter((e) => !regNames.has(e.name))
      .map((e) => ({ ...e, _type: "local" as const }));
    const reg = registryResults
      .filter((r) => {
        const matchCat = category === "all" || r.category === category;
        return matchCat;
      })
      .map((r) => ({ ...r, _type: "registry" as const }));
    return [...local, ...reg];
  }, [localFiltered, registryResults, search, category]);

  const handleInstall = async (entry: MCPCatalogEntry | RegistryMCPServer) => {
    const key = "source" in entry ? entry.name : entry.name.toLowerCase().replace(/\s+/g, "-");
    setInstalling(key);
    try {
      await onInstall(entry);
    } finally {
      setInstalling(null);
    }
  };

  const isInstalled = (entry: MCPCatalogEntry | RegistryMCPServer): boolean => {
    if ("source" in entry) {
      return installed.has(entry.name);
    }
    return installed.has(entry.name.toLowerCase().replace(/\s+/g, "-"));
  };

  return (
    <div className="flex flex-col gap-3 overflow-hidden">
      {/* Filtres */}
      <div className="flex gap-2">
        <div className="relative flex-1">
          <SearchIcon className="absolute left-2.5 top-2.5 size-3.5 text-muted-foreground" />
          <Input
            className="h-8 pl-8 text-sm"
            placeholder="Rechercher un MCP (local + registre officiel)..."
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

      {/* Indicateur registre */}
      {search.length >= 2 && registryLoading && (
        <div className="text-muted-foreground text-xs flex items-center gap-2">
          <Loader2Icon className="size-3 animate-spin" />
          Recherche dans le registre officiel...
        </div>
      )}
      {search.length >= 2 && !registryLoading && (
        <div className="text-muted-foreground text-xs">
          {registryResults.length} résultat(s) du registre officiel
          {localFiltered.length > 0 && ` + ${localFiltered.length} local(aux)`}
        </div>
      )}

      {/* Liste */}
      <div className="overflow-y-auto max-h-[55vh] space-y-2">
        {merged.length === 0 && !registryLoading && (
          <div className="text-muted-foreground text-sm text-center py-8">
            Aucun MCP trouvé.
          </div>
        )}
        {merged.map((entry: MCPCatalogEntry & { _type: string } | RegistryMCPServer & { _type: string }) => {
          const slug = "_type" in entry && entry._type === "registry"
            ? (entry as RegistryMCPServer).name
            : (entry as MCPCatalogEntry).name.toLowerCase().replace(/\s+/g, "-");
          const alreadyInstalled = isInstalled(entry);
          const isRegistry = "_type" in entry && entry._type === "registry";
          const regEntry = isRegistry ? (entry as RegistryMCPServer) : null;
          const localEntry = !isRegistry ? (entry as MCPCatalogEntry) : null;

          const displayName = isRegistry && regEntry
            ? (regEntry.title || regEntry.name)
            : (localEntry?.name ?? "");
          const description = isRegistry && regEntry
            ? regEntry.description
            : (localEntry?.description ?? "");
          const categoryVal = isRegistry && regEntry
            ? regEntry.category
            : (localEntry?.category ?? "dev");
          const commandStr = isRegistry && regEntry
            ? (regEntry.command ? `${regEntry.command} ${regEntry.args.join(" ")}` : (regEntry.url ?? "Aucune commande"))
            : `${localEntry?.command ?? ""} ${localEntry?.args?.join(" ") ?? ""}`.trim();
          const transportLabel = isRegistry && regEntry
            ? (regEntry.transport_type === "stdio" ? "stdio" : regEntry.transport_type)
            : "stdio";

          return (
            <div
              key={isRegistry && regEntry ? `reg-${regEntry.name}` : `local-${(entry as MCPCatalogEntry).name}`}
              className="border rounded-lg p-3 flex items-start gap-3 hover:bg-muted/30 transition-colors"
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-medium text-sm">{displayName}</span>
                  {isRegistry ? (
                    <Badge variant="outline" className="text-xs gap-1 border-blue-300 text-blue-600">
                      <GlobeIcon className="size-3" />
                      Registry
                    </Badge>
                  ) : (
                    <Badge variant="outline" className="text-xs gap-1">
                      {CATEGORY_ICONS[categoryVal]}
                      {CATEGORY_LABELS[categoryVal] ?? categoryVal}
                    </Badge>
                  )}
                  <Badge variant="outline" className="text-xs">
                    {transportLabel}
                  </Badge>
                  {alreadyInstalled && (
                    <Badge variant="outline" className="text-xs text-green-600 border-green-300">
                      <CheckIcon className="size-3 mr-0.5" />
                      Installé
                    </Badge>
                  )}
                </div>
                <p className="text-muted-foreground text-xs mt-1 line-clamp-2">
                  {description}
                </p>
                <code className="text-muted-foreground text-[10px] mt-1 block truncate">
                  {commandStr}
                </code>
                {isRegistry && regEntry?.version && (
                  <span className="text-muted-foreground text-[10px]">v{regEntry.version}</span>
                )}
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
