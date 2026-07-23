"""Scans skills directories for ``mcp_config.yaml`` and merges into ExtensionsConfig.

Each skill directory may contain an optional ``mcp_config.yaml`` declaring
additional MCP servers. The bridge scans both ``public/`` and ``custom/``
skill categories, validates each entry, and merges them into the global
ExtensionsConfig (base-config servers take precedence — skill-defined servers
with the same name are not overwritten).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from deerflow.config.extensions_config import ExtensionsConfig, McpServerConfig

logger = logging.getLogger(__name__)

# Name of the MCP config file within a skill directory
MCP_CONFIG_FILENAME = "mcp_config.yaml"

# Variable marker resolved to the skill's absolute host path
SKILL_DIR_VAR = "${SKILL_DIR}"


@dataclass
class SkillMCPServers:
    """MCP server configurations discovered in a skill directory.

    Attributes:
        skill_name: Name of the skill (from directory name, not from SKILL.md).
        skill_path: Absolute path to the skill directory.
        servers: Map of server name → McpServerConfig discovered in the skill.
    """

    skill_name: str
    skill_path: Path
    servers: dict[str, McpServerConfig] = field(default_factory=dict)


class MCPSkillBridge:
    """Scans skills for MCP server configurations and merges into ExtensionsConfig.

    Skill-defined MCP servers are appended to the base configuration without
    overwriting existing servers of the same name. The bridge is designed to
    be called before ``build_servers_config()`` in the MCP tool-loading path.
    """

    # ── Scanning ─────────────────────────────────────────────────────

    @staticmethod
    def scan_skills(skills_root: Path) -> dict[str, SkillMCPServers]:
        """Scan all skill directories for ``mcp_config.yaml`` files.

        Walks both ``public/`` and ``custom/`` subdirectories under
        *skills_root*. Hidden directories (starting with ``.``) are skipped.

        Args:
            skills_root: Path to the skills root directory.

        Returns:
            Dict of ``skill_name → SkillMCPServers``. Empty if no skills
            declare MCP servers.
        """
        result: dict[str, SkillMCPServers] = {}

        if not skills_root.exists() or not skills_root.is_dir():
            logger.debug("Skills root does not exist: %s", skills_root)
            return result

        for category in ("public", "custom"):
            category_path = skills_root / category
            if not category_path.exists() or not category_path.is_dir():
                continue

            for entry in sorted(category_path.iterdir()):
                if entry.name.startswith("."):
                    continue
                if not entry.is_dir():
                    continue

                skill_name = entry.name
                skill_servers = MCPSkillBridge.load_skill_mcp_config(entry)
                if skill_servers is not None and skill_servers:
                    servers_map: dict[str, McpServerConfig] = {}
                    for raw_config in skill_servers:
                        validated = MCPSkillBridge._validate_server_entry(raw_config, entry)
                        if validated is not None:
                            try:
                                cfg = McpServerConfig.model_validate(validated)
                                servers_map[validated["name"]] = cfg
                            except Exception:
                                logger.warning(
                                    "Invalid MCP server entry in skill '%s': %s",
                                    skill_name,
                                    validated.get("name", "<unknown>"),
                                    exc_info=True,
                                )
                    if servers_map:
                        result[skill_name] = SkillMCPServers(
                            skill_name=skill_name,
                            skill_path=entry,
                            servers=servers_map,
                        )
                        logger.info(
                            "Skill '%s' declares %d MCP server(s): %s",
                            skill_name,
                            len(servers_map),
                            list(servers_map.keys()),
                        )

        return result

    # ── Config loading ───────────────────────────────────────────────

    @staticmethod
    def load_skill_mcp_config(skill_path: Path) -> list[dict[str, Any]] | None:
        """Load and parse ``mcp_config.yaml`` from a skill directory.

        Args:
            skill_path: Path to the skill's root directory.

        Returns:
            List of raw server config dicts, or ``None`` if no
            ``mcp_config.yaml`` exists.

        Raises:
            ValueError: If the YAML is malformed.
        """
        import yaml

        config_file = skill_path / MCP_CONFIG_FILENAME
        if not config_file.exists():
            return None

        try:
            with open(config_file, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {config_file}: {e}") from e

        if not isinstance(data, dict):
            logger.warning("mcp_config.yaml in '%s' is not a mapping, ignoring", skill_path.name)
            return None

        servers = data.get("mcp_servers", [])
        if not isinstance(servers, list):
            logger.warning("mcp_servers in '%s' is not a list, ignoring", skill_path.name)
            return None

        return servers

    # ── Validation ───────────────────────────────────────────────────

    @staticmethod
    def _validate_server_entry(
        entry: dict[str, Any],
        skill_path: Path | None = None,
    ) -> dict[str, Any] | None:
        """Validate a single server entry from a skill's YAML config.

        Must have ``name`` and ``transport`` (or ``type``) keys.
        ``${SKILL_DIR}`` is resolved to the skill's absolute path.

        Args:
            entry: Raw server config dict from YAML.
            skill_path: Skill directory path for ``${SKILL_DIR}`` resolution.

        Returns:
            A validated and resolved config dict, or ``None`` if invalid.
        """
        if not isinstance(entry, dict):
            logger.debug("MCP server entry is not a dict, skipping: %s", type(entry).__name__)
            return None

        name = entry.get("name")
        if not name or not isinstance(name, str):
            logger.debug("MCP server entry missing 'name', skipping")
            return None

        transport = entry.get("transport") or entry.get("type")
        if not transport or transport not in ("stdio", "sse", "http"):
            logger.debug("MCP server entry '%s' has invalid or missing transport", name)
            return None

        # Normalize — McpServerConfig uses `type` internally, but YAML
        # uses the MCP-spec `transport`. The model_validator on
        # McpServerConfig already handles this alias.
        entry = dict(entry)

        # Resolve ${SKILL_DIR} variable
        if skill_path is not None:
            entry = MCPSkillBridge._resolve_skill_dir_var(entry, skill_path)

        return entry

    # ── Variable resolution ──────────────────────────────────────────

    @staticmethod
    def _resolve_skill_dir_var(
        entry: dict[str, Any],
        skill_path: Path,
    ) -> dict[str, Any]:
        """Replace ``${SKILL_DIR}`` with the absolute skill path.

        Resolution is applied to all string values (including nested lists
        and dicts).
        """
        resolved: dict[str, Any] = {}
        for key, value in entry.items():
            resolved[key] = MCPSkillBridge._resolve_value(value, skill_path)
        return resolved

    @staticmethod
    def _resolve_value(value: Any, skill_path: Path) -> Any:
        """Recursively resolve ``${SKILL_DIR}`` in a value."""
        if isinstance(value, str):
            return value.replace(SKILL_DIR_VAR, str(skill_path.resolve()))
        if isinstance(value, list):
            return [MCPSkillBridge._resolve_value(item, skill_path) for item in value]
        if isinstance(value, dict):
            return {k: MCPSkillBridge._resolve_value(v, skill_path) for k, v in value.items()}
        return value

    # ── Merging ──────────────────────────────────────────────────────

    @staticmethod
    def merge_into_extensions_config(
        skill_configs: dict[str, SkillMCPServers],
        base_config: ExtensionsConfig,
    ) -> ExtensionsConfig:
        """Deep-merge skill-defined MCP servers into a base ExtensionsConfig.

        Base-config servers take precedence — skill servers with the same
        name as an existing base server are **not** overwritten.

        Args:
            skill_configs: Dict from :meth:`scan_skills`.
            base_config: The base ExtensionsConfig to merge into.

        Returns:
            A new ExtensionsConfig with skill servers appended.
        """
        if not skill_configs:
            return base_config

        merged_servers = dict(base_config.mcp_servers)
        added = 0
        skipped = 0

        for skill_entry in skill_configs.values():
            for server_name, server_config in skill_entry.servers.items():
                if server_name in merged_servers:
                    logger.debug(
                        "Skill server '%s' (from '%s') conflicts with base config — skipping",
                        server_name,
                        skill_entry.skill_name,
                    )
                    skipped += 1
                else:
                    merged_servers[server_name] = server_config
                    added += 1

        if added:
            logger.info("Merged %d skill-defined MCP server(s) into config", added)
        if skipped:
            logger.info("Skipped %d skill MCP server(s) that conflict with base config", skipped)

        return ExtensionsConfig(
            mcp_servers=merged_servers,
            skills=base_config.skills,
        )
