export interface MCPOAuthConfig {
  enabled: boolean;
  token_url: string;
  grant_type: "client_credentials" | "refresh_token";
  client_id?: string | null;
  client_secret?: string | null;
  refresh_token?: string | null;
  scope?: string | null;
  audience?: string | null;
  token_field: string;
  token_type_field: string;
  expires_in_field: string;
  default_token_type: string;
  refresh_skew_seconds: number;
  extra_token_params: Record<string, string>;
}

export interface MCPServerConfig {
  enabled: boolean;
  type: "stdio" | "sse" | "http";
  command?: string | null;
  args: string[];
  env: Record<string, string>;
  url?: string | null;
  headers: Record<string, string>;
  oauth?: MCPOAuthConfig | null;
  description: string;
}

export interface MCPConfig {
  mcp_servers: Record<string, MCPServerConfig>;
}

// ── Catalogue des MCP populaires ──────────────────────────────────────

export interface MCPCatalogEntry {
  name: string;
  description: string;
  command: string;
  args: string[];
  env: Record<string, string>;
  category: "dev" | "data" | "search" | "productivity" | "communication";
}

// ── Catalogue du Registre MCP Officiel ──────────────────────────────────

export interface RegistryMCPServer {
  name: string;
  title: string;
  description: string;
  version: string;
  command: string | null;
  args: string[];
  env: Record<string, string>;
  url: string | null;
  transport_type: "stdio" | "streamable-http" | "sse";
  website_url: string | null;
  repository: string | null;
  category: "dev" | "data" | "search" | "productivity" | "communication";
  source: "registry" | "local";
}

export interface RegistrySearchResponse {
  servers: RegistryMCPServer[];
  next_cursor: string | null;
  count: number;
}

// ── Security Scan ───────────────────────────────────────────────────────

export interface MCPSecurityScanResult {
  decision: "allow" | "warn" | "block";
  reasons: string[];
  score: number;
}

// ── Catalogue local (intégré) ──────────────────────────────────────────

export const MCP_CATALOG: MCPCatalogEntry[] = [
  {
    name: "GitHub",
    description: "Dépôts, PRs, issues, branches — opérations GitHub complètes",
    command: "npx",
    args: ["-y", "@modelcontextprotocol/server-github"],
    env: { GITHUB_TOKEN: "$GITHUB_TOKEN" },
    category: "dev",
  },
  {
    name: "Filesystem",
    description: "Lire, écrire et lister des fichiers sur le disque local",
    command: "npx",
    args: ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed"],
    env: {},
    category: "dev",
  },
  {
    name: "PostgreSQL",
    description: "Requêtes SQL, exploration de schéma, accès base de données",
    command: "npx",
    args: ["-y", "@modelcontextprotocol/server-postgres", "postgresql://localhost/mydb"],
    env: {},
    category: "data",
  },
  {
    name: "Brave Search",
    description: "Recherche web et locale via l'API Brave Search",
    command: "npx",
    args: ["-y", "@modelcontextprotocol/server-brave-search"],
    env: { BRAVE_API_KEY: "$BRAVE_API_KEY" },
    category: "search",
  },
  {
    name: "Puppeteer",
    description: "Navigation web headless — screenshots, scraping, interactions",
    command: "npx",
    args: ["-y", "@modelcontextprotocol/server-puppeteer"],
    env: {},
    category: "dev",
  },
  {
    name: "Memory",
    description: "Système de mémoire persistante via graphe de connaissances",
    command: "npx",
    args: ["-y", "@modelcontextprotocol/server-memory"],
    env: {},
    category: "data",
  },
  {
    name: "Sequential Thinking",
    description: "Raisonnement étape par étape pour problèmes complexes",
    command: "npx",
    args: ["-y", "@modelcontextprotocol/server-sequential-thinking"],
    env: {},
    category: "dev",
  },
  {
    name: "Fetch",
    description: "Récupération de contenu web (pages, JSON, images)",
    command: "npx",
    args: ["-y", "@modelcontextprotocol/server-fetch"],
    env: {},
    category: "search",
  },
  {
    name: "Slack",
    description: "Messages, canaux, utilisateurs — intégration Slack",
    command: "npx",
    args: ["-y", "@modelcontextprotocol/server-slack"],
    env: { SLACK_BOT_TOKEN: "$SLACK_BOT_TOKEN" },
    category: "communication",
  },
  {
    name: "Notion",
    description: "Pages, bases de données, commentaires — API Notion",
    command: "npx",
    args: ["-y", "@notionhq/notion-mcp-server"],
    env: { NOTION_API_KEY: "$NOTION_API_KEY" },
    category: "productivity",
  },
  {
    name: "Exa Search",
    description: "Recherche web sémantique avec Exa AI",
    command: "npx",
    args: ["-y", "@anthropic/exa-mcp-server"],
    env: { EXA_API_KEY: "$EXA_API_KEY" },
    category: "search",
  },
  {
    name: "Google Maps",
    description: "Géocodage, itinéraires, recherche de lieux",
    command: "npx",
    args: ["-y", "@modelcontextprotocol/server-google-maps"],
    env: { GOOGLE_MAPS_API_KEY: "$GOOGLE_MAPS_API_KEY" },
    category: "search",
  },
  {
    name: "Docker",
    description: "Gestion de conteneurs, images, volumes Docker",
    command: "npx",
    args: ["-y", "@modelcontextprotocol/server-docker"],
    env: {},
    category: "dev",
  },
  {
    name: "SQLite",
    description: "Requêtes et exploration de bases SQLite locales",
    command: "npx",
    args: ["-y", "@modelcontextprotocol/server-sqlite", "/path/to/database.db"],
    env: {},
    category: "data",
  },
  {
    name: "Redis",
    description: "Cache, pub/sub, structures de données Redis",
    command: "npx",
    args: ["-y", "@anthropic/server-redis"],
    env: {},
    category: "data",
  },
];
