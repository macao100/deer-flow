"""Tests for MCPSkillBridge — scanning, parsing, merging skill MCP configs."""

import pytest
import yaml

from deerflow.config.extensions_config import ExtensionsConfig, McpServerConfig
from deerflow.mcp.skill_bridge import SKILL_DIR_VAR, MCPSkillBridge, SkillMCPServers


class TestLoadSkillMcpConfig:
    """Loading and parsing mcp_config.yaml from skill directories."""

    def test_config_found(self, tmp_path):
        """Valid mcp_config.yaml is loaded and parsed."""
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir(parents=True)
        config = {
            "mcp_servers": [
                {
                    "name": "filesystem",
                    "transport": "stdio",
                    "command": "npx",
                    "args": ["-y", "@mcp/fs"],
                },
            ]
        }
        (skill_dir / "mcp_config.yaml").write_text(yaml.dump(config), encoding="utf-8")

        result = MCPSkillBridge.load_skill_mcp_config(skill_dir)
        assert result is not None
        assert len(result) == 1
        assert result[0]["name"] == "filesystem"
        assert result[0]["transport"] == "stdio"

    def test_config_not_found(self, tmp_path):
        """Returns None when no mcp_config.yaml exists."""
        skill_dir = tmp_path / "no-config"
        skill_dir.mkdir(parents=True)
        result = MCPSkillBridge.load_skill_mcp_config(skill_dir)
        assert result is None

    def test_config_invalid_yaml(self, tmp_path):
        """Raises ValueError for malformed YAML."""
        skill_dir = tmp_path / "bad-yaml"
        skill_dir.mkdir(parents=True)
        (skill_dir / "mcp_config.yaml").write_text("{{{ invalid: [[[", encoding="utf-8")

        with pytest.raises(ValueError, match="Invalid YAML"):
            MCPSkillBridge.load_skill_mcp_config(skill_dir)

    def test_config_not_a_dict(self, tmp_path):
        """Returns None when top-level is not a mapping."""
        skill_dir = tmp_path / "list-root"
        skill_dir.mkdir(parents=True)
        (skill_dir / "mcp_config.yaml").write_text("- item1\n- item2\n", encoding="utf-8")

        result = MCPSkillBridge.load_skill_mcp_config(skill_dir)
        assert result is None

    def test_config_mcp_servers_not_list(self, tmp_path):
        """Returns None when mcp_servers is not a list."""
        skill_dir = tmp_path / "bad-servers"
        skill_dir.mkdir(parents=True)
        (skill_dir / "mcp_config.yaml").write_text("mcp_servers: not-a-list\n", encoding="utf-8")

        result = MCPSkillBridge.load_skill_mcp_config(skill_dir)
        assert result is None

    def test_config_empty_servers(self, tmp_path):
        """Empty mcp_servers returns empty list."""
        skill_dir = tmp_path / "empty-servers"
        skill_dir.mkdir(parents=True)
        (skill_dir / "mcp_config.yaml").write_text("mcp_servers: []\n", encoding="utf-8")

        result = MCPSkillBridge.load_skill_mcp_config(skill_dir)
        assert result == []

    def test_config_with_skill_dir_var(self, tmp_path):
        """${SKILL_DIR} is present in raw config."""
        skill_dir = tmp_path / "var-skill"
        skill_dir.mkdir(parents=True)
        config = {
            "mcp_servers": [
                {
                    "name": "fs",
                    "transport": "stdio",
                    "command": "python",
                    "args": ["${SKILL_DIR}/scripts/server.py"],
                },
            ]
        }
        (skill_dir / "mcp_config.yaml").write_text(yaml.dump(config), encoding="utf-8")

        result = MCPSkillBridge.load_skill_mcp_config(skill_dir)
        assert result is not None
        assert SKILL_DIR_VAR in result[0]["args"][0]

    def test_config_multiple_servers(self, tmp_path):
        """Multiple servers in one mcp_config.yaml."""
        skill_dir = tmp_path / "multi"
        skill_dir.mkdir(parents=True)
        config = {
            "mcp_servers": [
                {"name": "srv1", "transport": "stdio", "command": "cmd1", "args": []},
                {"name": "srv2", "transport": "sse", "url": "http://localhost:8080/sse"},
            ]
        }
        (skill_dir / "mcp_config.yaml").write_text(yaml.dump(config), encoding="utf-8")

        result = MCPSkillBridge.load_skill_mcp_config(skill_dir)
        assert len(result) == 2


class TestScanSkills:
    """Scanning skill directories for mcp_config.yaml."""

    def test_scan_finds_configs(self, tmp_path):
        """Scans public/ and custom/ for skills with mcp_config.yaml."""
        skills_root = tmp_path / "skills"
        skill_dir = skills_root / "public" / "search-skill"
        skill_dir.mkdir(parents=True)
        config = {"mcp_servers": [{"name": "search", "transport": "stdio", "command": "go", "args": []}]}
        (skill_dir / "mcp_config.yaml").write_text(yaml.dump(config), encoding="utf-8")

        result = MCPSkillBridge.scan_skills(skills_root)
        assert "search-skill" in result
        assert result["search-skill"].skill_name == "search-skill"
        assert "search" in result["search-skill"].servers

    def test_scan_skips_hidden_dirs(self, tmp_path):
        """Hidden directories (starting with .) are skipped."""
        skills_root = tmp_path / "skills"
        hidden_dir = skills_root / "public" / ".hidden-skill"
        hidden_dir.mkdir(parents=True)
        config = {"mcp_servers": [{"name": "hidden", "transport": "stdio", "command": "cmd", "args": []}]}
        (hidden_dir / "mcp_config.yaml").write_text(yaml.dump(config), encoding="utf-8")

        result = MCPSkillBridge.scan_skills(skills_root)
        assert len(result) == 0

    def test_scan_empty_root(self, tmp_path):
        """Non-existent root returns empty dict."""
        fake_root = tmp_path / "does-not-exist"
        result = MCPSkillBridge.scan_skills(fake_root)
        assert result == {}

    def test_scan_public_and_custom(self, tmp_path):
        """Both public/ and custom/ are scanned independently."""
        skills_root = tmp_path / "skills"
        pub_dir = skills_root / "public" / "pub-skill"
        cus_dir = skills_root / "custom" / "cus-skill"
        pub_dir.mkdir(parents=True)
        cus_dir.mkdir(parents=True)
        config_pub = {"mcp_servers": [{"name": "pub", "transport": "stdio", "command": "a", "args": []}]}
        config_cus = {"mcp_servers": [{"name": "cus", "transport": "stdio", "command": "b", "args": []}]}
        (pub_dir / "mcp_config.yaml").write_text(yaml.dump(config_pub), encoding="utf-8")
        (cus_dir / "mcp_config.yaml").write_text(yaml.dump(config_cus), encoding="utf-8")

        result = MCPSkillBridge.scan_skills(skills_root)
        assert "pub-skill" in result
        assert "cus-skill" in result
        assert result["pub-skill"].servers["pub"].command == "a"
        assert result["cus-skill"].servers["cus"].command == "b"

    def test_scan_skill_without_config_not_included(self, tmp_path):
        """Skills without mcp_config.yaml are not in results."""
        skills_root = tmp_path / "skills"
        skill_dir = skills_root / "public" / "no-config-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\nname: no-config\ndescription: Test\n---\n# Body\n", encoding="utf-8")

        result = MCPSkillBridge.scan_skills(skills_root)
        assert "no-config-skill" not in result

    def test_scan_invalid_entry_skipped(self, tmp_path):
        """Invalid server entries are skipped gracefully."""
        skills_root = tmp_path / "skills"
        skill_dir = skills_root / "public" / "bad-skill"
        skill_dir.mkdir(parents=True)
        config = {
            "mcp_servers": [
                {"name": "valid", "transport": "stdio", "command": "cmd", "args": []},
                {"no_name": True},  # Invalid: missing name
            ]
        }
        (skill_dir / "mcp_config.yaml").write_text(yaml.dump(config), encoding="utf-8")

        result = MCPSkillBridge.scan_skills(skills_root)
        # Only the valid entry should be included
        assert "bad-skill" in result
        assert "valid" in result["bad-skill"].servers
        assert len(result["bad-skill"].servers) == 1


class TestValidateServerEntry:
    """Validation of individual server entries."""

    def test_valid_minimal_entry(self):
        """Name + transport = valid."""
        entry = {"name": "test", "transport": "stdio", "command": "cmd", "args": []}
        result = MCPSkillBridge._validate_server_entry(entry)
        assert result is not None
        assert result["name"] == "test"

    def test_missing_name(self):
        """Missing name returns None."""
        result = MCPSkillBridge._validate_server_entry({"transport": "stdio"})
        assert result is None

    def test_missing_transport(self):
        """Missing transport returns None."""
        result = MCPSkillBridge._validate_server_entry({"name": "test"})
        assert result is None

    def test_invalid_transport(self):
        """Invalid transport returns None."""
        result = MCPSkillBridge._validate_server_entry({"name": "test", "transport": "grpc"})
        assert result is None

    def test_accepts_type_alias(self):
        """'type' is accepted as alias for 'transport'."""
        entry = {"name": "test", "type": "sse", "url": "http://localhost/sse"}
        result = MCPSkillBridge._validate_server_entry(entry)
        assert result is not None
        assert result["type"] == "sse"

    def test_non_dict_entry(self):
        """Non-dict entry returns None."""
        result = MCPSkillBridge._validate_server_entry("not-a-dict")  # type: ignore[arg-type]
        assert result is None

    def test_resolve_skill_dir_var(self):
        """${SKILL_DIR} is resolved to absolute path."""
        from pathlib import Path

        skill_path = Path("/tmp/skills/public/my-skill")
        entry = {
            "name": "fs",
            "transport": "stdio",
            "command": "python",
            "args": ["${SKILL_DIR}/scripts/run.py", "${SKILL_DIR}/config.json"],
        }
        result = MCPSkillBridge._validate_server_entry(entry, skill_path=skill_path)
        assert result is not None
        assert SKILL_DIR_VAR not in result["args"][0]
        assert str(skill_path.resolve()) in result["args"][0]
        assert str(skill_path.resolve()) in result["args"][1]


class TestMergeIntoExtensionsConfig:
    """Merging skill configs into ExtensionsConfig."""

    def test_empty_skills_no_change(self):
        """Empty skill_configs returns base_config unchanged."""
        base = ExtensionsConfig(mcp_servers={"existing": McpServerConfig(
            enabled=True, type="stdio", command="cmd", args=[]
        )})
        result = MCPSkillBridge.merge_into_extensions_config({}, base)
        assert "existing" in result.mcp_servers
        assert len(result.mcp_servers) == 1

    def test_adds_new_servers(self):
        """Skill servers are appended when no conflict."""
        base = ExtensionsConfig(mcp_servers={})
        skill_configs = {
            "my-skill": SkillMCPServers(
                skill_name="my-skill",
                skill_path="/tmp/skills/public/my-skill",
                servers={"search": McpServerConfig(
                    enabled=True, type="stdio", command="npx", args=["search"]
                )},
            )
        }
        result = MCPSkillBridge.merge_into_extensions_config(skill_configs, base)
        assert "search" in result.mcp_servers
        assert result.mcp_servers["search"].command == "npx"

    def test_base_servers_take_precedence(self):
        """Base config servers are not overwritten by skills."""
        base = ExtensionsConfig(mcp_servers={"search": McpServerConfig(
            enabled=True, type="sse", url="http://base/sse"
        )})
        skill_configs = {
            "my-skill": SkillMCPServers(
                skill_name="my-skill",
                skill_path="/tmp/skill",
                servers={"search": McpServerConfig(
                    enabled=True, type="stdio", command="npx", args=[]
                )},
            )
        }
        result = MCPSkillBridge.merge_into_extensions_config(skill_configs, base)
        # Base wins — URL preserved, not overwritten by stdio
        assert result.mcp_servers["search"].url == "http://base/sse"

    def test_partial_overlap(self):
        """Only non-conflicting skill servers are added."""
        base = ExtensionsConfig(mcp_servers={"base-only": McpServerConfig(
            enabled=True, type="stdio", command="base", args=[]
        )})
        skill_configs = {
            "skill-a": SkillMCPServers(
                skill_name="skill-a",
                skill_path="/tmp/a",
                servers={
                    "base-only": McpServerConfig(enabled=True, type="sse", url="http://skill/sse"),
                    "skill-only": McpServerConfig(enabled=True, type="stdio", command="sk", args=[]),
                },
            )
        }
        result = MCPSkillBridge.merge_into_extensions_config(skill_configs, base)
        assert "base-only" in result.mcp_servers
        assert result.mcp_servers["base-only"].command == "base"  # base wins
        assert "skill-only" in result.mcp_servers  # new server added
        assert len(result.mcp_servers) == 2

    def test_returns_new_instance(self):
        """Original base_config is not mutated."""
        base = ExtensionsConfig(mcp_servers={})
        skill_configs = {
            "s": SkillMCPServers(
                skill_name="s", skill_path="/tmp/s",
                servers={"new": McpServerConfig(enabled=True, type="stdio", command="x", args=[])},
            )
        }
        result = MCPSkillBridge.merge_into_extensions_config(skill_configs, base)
        assert "new" not in base.mcp_servers  # base unchanged
        assert "new" in result.mcp_servers  # result has it
