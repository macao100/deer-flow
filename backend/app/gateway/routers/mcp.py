import json
import logging
import os
from pathlib import Path
from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from deerflow.config.extensions_config import ExtensionsConfig, get_extensions_config, reload_extensions_config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["mcp"])


_MCP_STDIO_COMMAND_ALLOWLIST_ENV = "DEER_FLOW_MCP_STDIO_COMMAND_ALLOWLIST"
_DEFAULT_MCP_STDIO_COMMAND_ALLOWLIST = frozenset({"npx", "uvx"})
_SHELL_METACHARS = frozenset(";|&`$<>\n\r")


class McpOAuthConfigResponse(BaseModel):
    """OAuth configuration for an MCP server."""

    enabled: bool = Field(default=True, description="Whether OAuth token injection is enabled")
    token_url: str = Field(default="", description="OAuth token endpoint URL")
    grant_type: Literal["client_credentials", "refresh_token"] = Field(default="client_credentials", description="OAuth grant type")
    client_id: str | None = Field(default=None, description="OAuth client ID")
    client_secret: str | None = Field(default=None, description="OAuth client secret")
    refresh_token: str | None = Field(default=None, description="OAuth refresh token")
    scope: str | None = Field(default=None, description="OAuth scope")
    audience: str | None = Field(default=None, description="OAuth audience")
    token_field: str = Field(default="access_token", description="Token response field containing access token")
    token_type_field: str = Field(default="token_type", description="Token response field containing token type")
    expires_in_field: str = Field(default="expires_in", description="Token response field containing expires-in seconds")
    default_token_type: str = Field(default="Bearer", description="Default token type when response omits token_type")
    refresh_skew_seconds: int = Field(default=60, description="Refresh this many seconds before expiry")
    extra_token_params: dict[str, str] = Field(default_factory=dict, description="Additional form params sent to token endpoint")


class McpServerConfigResponse(BaseModel):
    """Response model for MCP server configuration."""

    enabled: bool = Field(default=True, description="Whether this MCP server is enabled")
    type: str = Field(default="stdio", description="Transport type: 'stdio', 'sse', or 'http'")
    command: str | None = Field(default=None, description="Command to execute to start the MCP server (for stdio type)")
    args: list[str] = Field(default_factory=list, description="Arguments to pass to the command (for stdio type)")
    env: dict[str, str] = Field(default_factory=dict, description="Environment variables for the MCP server")
    url: str | None = Field(default=None, description="URL of the MCP server (for sse or http type)")
    headers: dict[str, str] = Field(default_factory=dict, description="HTTP headers to send (for sse or http type)")
    oauth: McpOAuthConfigResponse | None = Field(default=None, description="OAuth configuration for MCP HTTP/SSE servers")
    description: str = Field(default="", description="Human-readable description of what this MCP server provides")


class McpConfigResponse(BaseModel):
    """Response model for MCP configuration."""

    mcp_servers: dict[str, McpServerConfigResponse] = Field(
        default_factory=dict,
        description="Map of MCP server name to configuration",
    )


class McpConfigUpdateRequest(BaseModel):
    """Request model for updating MCP configuration."""

    mcp_servers: dict[str, McpServerConfigResponse] = Field(
        ...,
        description="Map of MCP server name to configuration",
    )


# ── Registry Catalog Models ──────────────────────────────────────────────

_MCP_REGISTRY_BASE = "https://registry.modelcontextprotocol.io"


class RegistryMCPServerResponse(BaseModel):
    """Transformed MCP server entry from the official registry."""

    name: str = Field(..., description="Unique server identifier (e.g. 'anthropic/server-github')")
    title: str = Field(..., description="Human-readable title")
    description: str = Field("", description="Server description")
    version: str = Field("", description="Latest version")
    command: str | None = Field(None, description="Command for stdio transport (npx/uvx), None if hosted")
    args: list[str] = Field(default_factory=list, description="Arguments for the command")
    env: dict[str, str] = Field(default_factory=dict, description="Environment variables with $VAR placeholders")
    url: str | None = Field(None, description="Remote URL for HTTP/SSE transports")
    transport_type: str = Field("stdio", description="Transport type: stdio, streamable-http, or sse")
    website_url: str | None = Field(None, description="Project website URL")
    repository: str | None = Field(None, description="Source repository URL")
    category: str = Field("dev", description="Inferred category: dev, data, search, productivity, communication")
    source: str = Field("registry", description="Source of this entry (always 'registry')")


class RegistrySearchResponse(BaseModel):
    """Response model for MCP registry catalog search."""

    servers: list[RegistryMCPServerResponse] = Field(default_factory=list)
    next_cursor: str | None = Field(None, description="Cursor for next page, None if last page")
    count: int = Field(0, description="Number of results in this page")


# ── Category Inference ───────────────────────────────────────────────────

_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "data": ["database", "postgres", "mysql", "sqlite", "redis", "mongodb", "duckdb", "vector", "qdrant", "milvus", "weaviate", "pinecone", "supabase", "firebase", "bigquery", "snowflake"],
    "search": ["search", "brave", "tavily", "exa", "serp", "google", "scrape", "fetch", "crawl", "firecrawl", "jina", "browser", "puppeteer", "playwright"],
    "communication": ["slack", "discord", "telegram", "teams", "whatsapp", "messenger", "email", "gmail", "outlook", "sendgrid", "twilio", "notifier"],
    "productivity": ["notion", "jira", "trello", "asana", "linear", "confluence", "airtable", "google", "calendar", "gcal", "docs", "sheets", "todo", "task"],
    "dev": ["github", "gitlab", "bitbucket", "git", "filesystem", "docker", "kubernetes", "aws", "cloudflare", "vercel", "netlify", "terraform", "sentry", "datadog", "prometheus", "cli", "terminal", "shell", "npm", "pypi", "package"],
}


def _infer_category(name: str, description: str) -> str:
    """Infer a category from server name and description keywords."""
    combined = f"{name} {description}".lower()
    for category, keywords in _CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in combined:
                return category
    return "dev"


# ── Registry Transformation ──────────────────────────────────────────────

def _transform_registry_server(entry: dict) -> RegistryMCPServerResponse:
    """Transform a raw registry server entry into the DeerFlow format."""
    server = entry.get("server", entry)
    name = server.get("name", "")
    description = server.get("description", "")
    title = server.get("title", name.rsplit("/", 1)[-1] if "/" in name else name)
    version = server.get("version", "")
    packages: list[dict] = server.get("packages", [])
    remotes: list[dict] = server.get("remotes", [])
    repository_raw = server.get("repository", {})
    repository = repository_raw.get("url", "") if isinstance(repository_raw, dict) else str(repository_raw) if repository_raw else None
    website_url = server.get("websiteUrl")

    command: str | None = None
    args: list[str] = []
    env: dict[str, str] = {}
    url: str | None = None
    transport_type: str = "stdio"

    if remotes:
        first_remote = remotes[0]
        transport_type = first_remote.get("type", "streamable-http")
        url = first_remote.get("url")

    if packages:
        for pkg in packages:
            registry_type = pkg.get("registryType", "npm")
            identifier = pkg.get("identifier", "")
            pkg_env_vars: list[dict] = pkg.get("environmentVariables", [])
            if identifier:
                if not command:
                    if registry_type == "npm":
                        command = "npx"
                        args = ["-y", identifier]
                    elif registry_type == "pypi":
                        command = "uvx"
                        args = [identifier]
                for ev in pkg_env_vars:
                    ev_name = ev.get("name", "")
                    if ev_name:
                        env[ev_name] = f"${ev_name}"

    category = _infer_category(name, description)

    return RegistryMCPServerResponse(
        name=name,
        title=title,
        description=description,
        version=version,
        command=command,
        args=args,
        env=env,
        url=url,
        transport_type=transport_type,
        website_url=website_url,
        repository=repository,
        category=category,
        source="registry",
    )


_MASKED_VALUE = "***"


async def _require_admin_user(request: Request) -> None:
    """Require the authenticated caller to be an admin user.

    ``AuthMiddleware`` normally stamps ``request.state.user`` before the
    request reaches this router. Falling back to the strict dependency keeps
    this route safe even in tests or alternative ASGI compositions that mount
    the router without the global middleware.
    """
    user = getattr(request.state, "user", None)
    if user is None:
        from app.gateway.deps import get_current_user_from_request

        user = await get_current_user_from_request(request)

    if getattr(user, "system_role", None) != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required to manage MCP configuration.",
        )


def _allowed_stdio_commands() -> set[str]:
    """Return executable names allowed for API-managed stdio MCP servers."""
    raw = os.environ.get(_MCP_STDIO_COMMAND_ALLOWLIST_ENV)
    base = set(_DEFAULT_MCP_STDIO_COMMAND_ALLOWLIST)
    if raw is None:
        return base
    extra = {item.strip() for item in raw.split(",") if item.strip()}
    return base | extra


def _stdio_command_name(command: str | None, *, server_name: str) -> str:
    """Normalize and validate a stdio command field from the API boundary."""
    if command is None or not command.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"MCP server '{server_name}' with stdio transport requires a command.",
        )

    stripped = command.strip()
    has_path_separator = "/" in stripped or "\\" in stripped
    if stripped != command or has_path_separator or any(ch.isspace() for ch in stripped) or any(ch in stripped for ch in _SHELL_METACHARS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(f"MCP server '{server_name}' command must be a single executable name; put parameters in args instead."),
        )

    return stripped


def _validate_mcp_update_request(request: McpConfigUpdateRequest) -> None:
    """Validate API-submitted MCP config before it is persisted.

    Local config files can still express arbitrary advanced setups, but the
    HTTP API is an untrusted boundary. Restricting stdio commands here reduces
    the blast radius of a compromised authenticated browser session.
    """
    allowed_commands = _allowed_stdio_commands()
    for name, server in request.mcp_servers.items():
        transport_type = (server.type or "stdio").lower()
        if transport_type != "stdio":
            continue

        command_name = _stdio_command_name(server.command, server_name=name)
        if command_name not in allowed_commands:
            allowed = ", ".join(sorted(allowed_commands)) or "<none>"
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(f"MCP server '{name}' uses disallowed stdio command '{command_name}'. Allowed commands: {allowed}. Configure {_MCP_STDIO_COMMAND_ALLOWLIST_ENV} to extend this list."),
            )


def _mask_server_config(server: McpServerConfigResponse) -> McpServerConfigResponse:
    """Return a copy of server config with sensitive fields masked.

    Masks env values, header values, and removes OAuth secrets so they
    are not exposed through the GET API endpoint.
    """
    masked_env = {k: _MASKED_VALUE for k in server.env}
    masked_headers = {k: _MASKED_VALUE for k in server.headers}
    masked_oauth = None
    if server.oauth is not None:
        masked_oauth = server.oauth.model_copy(
            update={
                "client_secret": None,
                "refresh_token": None,
            }
        )
    return server.model_copy(
        update={
            "env": masked_env,
            "headers": masked_headers,
            "oauth": masked_oauth,
        }
    )


def _merge_preserving_secrets(
    incoming: McpServerConfigResponse,
    existing: McpServerConfigResponse,
) -> McpServerConfigResponse:
    """Merge incoming config with existing, preserving secrets masked by GET.

    When the frontend toggles ``enabled`` it round-trips the full config:
    GET (masked) → modify enabled → PUT (masked values sent back).
    This function ensures masked values (``***``) are replaced with the
    real secrets from the current on-disk config.

    ``***`` is only accepted for keys that already exist in *existing*.
    New keys must provide a real value.

    For OAuth secrets, ``None`` means "preserve the existing stored value"
    so masked GET responses can be safely round-tripped. To explicitly clear
    a stored secret, clients may send an empty string, which is converted
    to ``None`` before persisting.
    """
    merged_env = {}
    for k, v in incoming.env.items():
        if v == _MASKED_VALUE:
            if k in existing.env:
                merged_env[k] = existing.env[k]
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot set env key '{k}' to masked value '***'; provide a real value.",
                )
        else:
            merged_env[k] = v

    merged_headers = {}
    for k, v in incoming.headers.items():
        if v == _MASKED_VALUE:
            if k in existing.headers:
                merged_headers[k] = existing.headers[k]
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot set header '{k}' to masked value '***'; provide a real value.",
                )
        else:
            merged_headers[k] = v

    merged_oauth = incoming.oauth
    if incoming.oauth is not None and existing.oauth is not None:
        # None = preserve (masked round-trip), "" = explicitly clear, else = new value
        merged_client_secret = existing.oauth.client_secret if incoming.oauth.client_secret is None else (None if incoming.oauth.client_secret == "" else incoming.oauth.client_secret)
        merged_refresh_token = existing.oauth.refresh_token if incoming.oauth.refresh_token is None else (None if incoming.oauth.refresh_token == "" else incoming.oauth.refresh_token)
        merged_oauth = incoming.oauth.model_copy(
            update={
                "client_secret": merged_client_secret,
                "refresh_token": merged_refresh_token,
            }
        )
    return incoming.model_copy(
        update={
            "env": merged_env,
            "headers": merged_headers,
            "oauth": merged_oauth,
        }
    )


@router.get(
    "/mcp/catalog/search",
    response_model=RegistrySearchResponse,
    summary="Search MCP Registry Catalog",
    description="Search the official MCP Registry at registry.modelcontextprotocol.io for available servers. Results are merged with the local catalog.",
)
async def search_mcp_catalog(
    q: str = Query("", description="Search query (matches name, title, description)"),
    cursor: str = Query("", description="Pagination cursor from previous response"),
    count: int = Query(30, ge=1, le=100, description="Number of results per page"),
) -> RegistrySearchResponse:
    """Proxy and transform results from the Official MCP Registry.

    This endpoint is public (no admin required) — it only reads from the
    public registry and the local hardcoded catalog.
    """
    servers: list[RegistryMCPServerResponse] = []
    next_cursor: str | None = None

    # ── Fetch from Official MCP Registry ───────────────────────────────
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            params: dict[str, str | int] = {"count": min(count, 100)}
            if cursor:
                params["cursor"] = cursor

            reg_response = await client.get(
                f"{_MCP_REGISTRY_BASE}/v0/servers",
                params=params,
            )

            if reg_response.status_code == 200:
                reg_data = reg_response.json()
                raw_servers: list[dict] = reg_data.get("servers", [])
                metadata: dict = reg_data.get("metadata", {})

                for entry in raw_servers:
                    server = _transform_registry_server(entry)
                    if not q or (
                        q.lower() in server.name.lower()
                        or q.lower() in server.title.lower()
                        or q.lower() in server.description.lower()
                    ):
                        servers.append(server)

                next_cursor = metadata.get("nextCursor")
            else:
                logger.warning(f"MCP Registry returned {reg_response.status_code}")
    except httpx.RequestError as exc:
        logger.warning(f"Failed to reach MCP Registry: {exc}")
    except Exception as exc:
        logger.error(f"Unexpected error fetching MCP Registry: {exc}", exc_info=True)

    return RegistrySearchResponse(
        servers=servers[:count],
        next_cursor=next_cursor,
        count=len(servers[:count]),
    )


@router.get(
    "/mcp/config",
    response_model=McpConfigResponse,
    summary="Get MCP Configuration",
    description="Retrieve the current Model Context Protocol (MCP) server configurations.",
)
async def get_mcp_configuration(request: Request) -> McpConfigResponse:
    """Get the current MCP configuration.

    Returns:
        The current MCP configuration with all servers.

    Example:
        ```json
        {
            "mcp_servers": {
                "github": {
                    "enabled": true,
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-github"],
                    "env": {"GITHUB_TOKEN": "***"},
                    "description": "GitHub MCP server for repository operations"
                }
            }
        }
        ```
    """
    await _require_admin_user(request)

    config = get_extensions_config()

    servers = {name: _mask_server_config(McpServerConfigResponse(**server.model_dump())) for name, server in config.mcp_servers.items()}
    return McpConfigResponse(mcp_servers=servers)


@router.put(
    "/mcp/config",
    response_model=McpConfigResponse,
    summary="Update MCP Configuration",
    description="Update Model Context Protocol (MCP) server configurations and save to file.",
)
async def update_mcp_configuration(request: Request, body: McpConfigUpdateRequest) -> McpConfigResponse:
    """Update the MCP configuration.

    This will:
    1. Save the new configuration to the mcp_config.json file
    2. Reload the configuration cache
    3. Reset MCP tools cache to trigger reinitialization

    Args:
        request: The new MCP configuration to save.

    Returns:
        The updated MCP configuration.

    Raises:
        HTTPException: 500 if the configuration file cannot be written.

    Example Request:
        ```json
        {
            "mcp_servers": {
                "github": {
                    "enabled": true,
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-github"],
                    "env": {"GITHUB_TOKEN": "$GITHUB_TOKEN"},
                    "description": "GitHub MCP server for repository operations"
                }
            }
        }
        ```
    """
    try:
        await _require_admin_user(request)
        _validate_mcp_update_request(body)

        # Get the current config path (or determine where to save it)
        config_path = ExtensionsConfig.resolve_config_path()

        # If no config file exists, create one in the parent directory (project root)
        if config_path is None:
            config_path = Path.cwd().parent / "extensions_config.json"
            logger.info(f"No existing extensions config found. Creating new config at: {config_path}")

        # Load current config to preserve skills
        current_config = get_extensions_config()

        # Load raw (un-resolved) JSON from disk to use as the merge source.
        # This preserves $VAR placeholders in env values and top-level keys
        # like mcpInterceptors that would otherwise be lost.
        raw_servers: dict[str, dict] = {}
        raw_other_keys: dict = {}
        if config_path is not None and config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                raw_data = json.load(f)
            raw_servers = raw_data.get("mcpServers", {})
            # Preserve any top-level keys beyond mcpServers/skills
            for key, value in raw_data.items():
                if key not in ("mcpServers", "skills"):
                    raw_other_keys[key] = value

        # Merge incoming server configs with raw on-disk secrets
        merged_servers: dict[str, McpServerConfigResponse] = {}
        for name, incoming in body.mcp_servers.items():
            raw_server = raw_servers.get(name)
            if raw_server is not None:
                merged_servers[name] = _merge_preserving_secrets(
                    incoming,
                    McpServerConfigResponse(**raw_server),
                )
            else:
                merged_servers[name] = incoming

        # Build config data preserving all top-level keys from the original file
        config_data = dict(raw_other_keys)
        config_data["mcpServers"] = {name: server.model_dump() for name, server in merged_servers.items()}
        config_data["skills"] = {name: {"enabled": skill.enabled} for name, skill in current_config.skills.items()}

        # Write the configuration to file
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2)

        logger.info(f"MCP configuration updated and saved to: {config_path}")

        # Reload the Gateway configuration and update the global cache. The
        # agent runtime lives in Gateway, so this keeps API reads and tool
        # execution aligned after extensions_config.json changes.
        reloaded_config = reload_extensions_config()
        servers = {name: _mask_server_config(McpServerConfigResponse(**server.model_dump())) for name, server in reloaded_config.mcp_servers.items()}
        return McpConfigResponse(mcp_servers=servers)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update MCP configuration: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update MCP configuration: {str(e)}")
