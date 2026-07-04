"""Tests for _detect_possible_truncation in sandbox/tools.py."""

import pytest
from deerflow.sandbox.tools import _detect_possible_truncation


class TestDetectPossibleTruncation:
    """Unit tests for _detect_possible_truncation."""

    # ── JSON ──────────────────────────────────────────────────────────

    def test_json_valid_returns_none(self):
        assert _detect_possible_truncation("data.json", '{"key": "value"}') is None

    def test_json_truncated_returns_warning(self):
        result = _detect_possible_truncation("data.json", '{"key": "val')
        assert result is not None
        assert "JSON" in result

    # ── TypeScript / JavaScript ───────────────────────────────────────

    def test_ts_balanced_returns_none(self):
        content = "export function foo() {\n  return 42;\n}\n"
        assert _detect_possible_truncation("app.ts", content) is None

    def test_ts_unbalanced_braces_returns_warning(self):
        content = "export function foo() {\n  return 42;\n"
        result = _detect_possible_truncation("app.ts", content)
        assert result is not None
        assert "possiblement tronqué" in result

    def test_ts_unbalanced_parens_returns_warning(self):
        content = "const x = foo(bar(1, 2;"
        result = _detect_possible_truncation("app.ts", content)
        assert result is not None
        assert "possiblement tronqué" in result

    def test_jsx_valid_returns_none(self):
        content = 'export const App = () => <div>Hello</div>;\n'
        assert _detect_possible_truncation("App.tsx", content) is None

    def test_js_truncated_ending_returns_warning(self):
        content = "const x = 1\nconst y = 2\nconst z ="
        result = _detect_possible_truncation("app.js", content)
        assert result is not None
        assert "possiblement tronqué" in result

    # ── MDX / MD ─────────────────────────────────────────────────────

    def test_mdx_frontmatter_closed_returns_none(self):
        content = "---\ntitle: Test\n---\n\n# Content\n"
        assert _detect_possible_truncation("page.mdx", content) is None

    def test_mdx_frontmatter_open_returns_warning(self):
        content = "---\ntitle: Test\n"
        result = _detect_possible_truncation("page.mdx", content)
        assert result is not None
        assert "Frontmatter" in result

    def test_md_no_frontmatter_returns_none(self):
        content = "# Title\n\nSome content.\n"
        assert _detect_possible_truncation("doc.md", content) is None

    # ── YAML ──────────────────────────────────────────────────────────

    def test_yaml_valid_returns_none(self):
        content = "key: value\nlist:\n  - a\n  - b\n"
        assert _detect_possible_truncation("config.yaml", content) is None

    def test_yaml_truncated_returns_warning(self):
        # Mapping sans valeur — invalide en YAML
        content = "key:\n  - item1\n  -\n"
        result = _detect_possible_truncation("config.yaml", content)
        assert result is not None
        assert "YAML" in result
    def test_yaml_truncated_returns_warning(self):
        # Tab character dans un flow mapping — invalide en YAML
        content = "{key: value,\tkey2: value2}"
        result = _detect_possible_truncation("config.yaml", content)
        assert result is not None
        assert "YAML" in result

    def test_yml_valid_returns_none(self):
        content = "name: test\n"
        assert _detect_possible_truncation("config.yml", content) is None

    # ── Unknown extensions ───────────────────────────────────────────

    def test_txt_unknown_extension_returns_none(self):
        content = "anything"
        assert _detect_possible_truncation("file.txt", content) is None

    def test_no_extension_returns_none(self):
        content = "anything"
        assert _detect_possible_truncation("Makefile", content) is None

    # ── Cas limites ──────────────────────────────────────────────────

    def test_json_empty_file_returns_none(self):
        """Un fichier JSON vide (juste créé, pas encore rempli) n'est pas une troncature."""
        assert _detect_possible_truncation("empty.json", "") is None
        assert _detect_possible_truncation("whitespace.json", "   \n  ") is None

    def test_mdx_dash_line_in_body_returns_none(self):
        """Une ligne --- dans le corps du markdown n'est pas considérée comme frontmatter."""
        content = "# Title\n\nSome text.\n\n---\n\nMore text.\n"
        assert _detect_possible_truncation("doc.mdx", content) is None
