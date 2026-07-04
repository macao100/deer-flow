"""Skill search tool — discover installable skills at runtime.

Agents call this tool to search the online skill catalog. Results include
the skill name, description, icon, and category. The agent can then suggest
installation via ``skill_manage(action="install", name="...")``.
"""

from __future__ import annotations

import json

from langchain.tools import tool

from deerflow.skills.catalog import search_catalog

MAX_RESULTS = 5


@tool("skill_search", parse_docstring=True)
def skill_search_tool(query: str = "", category: str | None = None) -> str:
    """Search the online skill catalog for installable skills.

    Use this tool to discover skills that could help with the current task.
    Skills provide optimized workflows, best practices, and references for
    specific tasks. Once you find a useful skill, suggest it to the user or
    install it with skill_manage(action="install", ...).

    Query forms:
      - "data analysis" — keyword search across name and description
      - "research" — broad search returning up to 5 results
      - "" (empty) — list all available skills (first 5)

    Args:
        query: Keywords to search for in skill names and descriptions.
        category: Optional filter — one of research, creation, analysis, dev, design.
    """
    results = search_catalog(query=query, category=category)[:MAX_RESULTS]

    if not results:
        categories = "research, creation, analysis, dev, design"
        return (
            f"No skills found matching '{query}'"
            + (f" in category '{category}'" if category else "")
            + f". Try a broader search or browse categories: {categories}."
        )

    items = []
    for entry in results:
        items.append(
            {
                "name": entry.name,
                "icon": entry.icon,
                "category": entry.category,
                "description": entry.description,
            }
        )

    return json.dumps(items, indent=2, ensure_ascii=False)
