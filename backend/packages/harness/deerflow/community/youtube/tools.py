"""Outils YouTube pour DeerFlow — recherche et transcription."""

import json
import os

from langchain.tools import tool

from deerflow.community.youtube.youtube_client import YouTubeClient
from deerflow.config import get_app_config


def _get_youtube_client() -> YouTubeClient:
    """Crée un client YouTube avec la clé API configurée."""
    api_key = None
    config = get_app_config().get_tool_config("youtube_search")
    if config is not None:
        api_key = config.model_extra.get("api_key")
    # Fallback sur la variable d'environnement
    if not api_key:
        api_key = os.getenv("YOUTUBE_API_KEY", "")
    return YouTubeClient(api_key=api_key)


def _coerce_max_results(value: object, default: int = 5) -> int:
    """Convertit une valeur en entier pour max_results."""
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return max(1, min(value, 10))
    if isinstance(value, str):
        try:
            return max(1, min(int(value), 10))
        except ValueError:
            return default
    return default


@tool("youtube_search", parse_docstring=True)
async def youtube_search_tool(query: str, max_results: int = 5) -> str:
    """Search YouTube for videos matching the query.
    Returns a list of videos with title, channel, description, publication date, and URL.
    Use this tool when the user asks to find YouTube videos or wants to search video content.

    Args:
        query: Search terms for finding YouTube videos.
        max_results: Maximum number of results to return (1-10, default 5).
    """
    client = _get_youtube_client()
    config = get_app_config().get_tool_config("youtube_search")
    if config is not None:
        max_results = _coerce_max_results(config.model_extra.get("max_results", max_results), default=max_results)
    results = await client.search(query, max_results=max_results)
    if results and "error" in results[0]:
        return results[0]["error"]
    return json.dumps(results, indent=2, ensure_ascii=False)


@tool("youtube_transcript", parse_docstring=True)
async def youtube_transcript_tool(video_id: str) -> str:
    """Get the transcript (subtitles/captions) of a YouTube video.
    Works without any API key — extracts timedtext captions directly.
    Use this to read the spoken content of a YouTube video.
    Prefers French captions, then English, then any available language.

    Args:
        video_id: The YouTube video ID (the part after ?v= in the URL). For example, for https://www.youtube.com/watch?v=VDwQnLhpod0, the video_id is VDwQnLhpod0.
    """
    client = _get_youtube_client()
    config = get_app_config().get_tool_config("youtube_transcript")
    languages = ["fr", "en"]
    if config is not None:
        configured_langs = config.model_extra.get("languages")
        if isinstance(configured_langs, list):
            languages = configured_langs
    return await client.get_transcript(video_id, languages=languages)
