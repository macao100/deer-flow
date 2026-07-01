"""Client léger pour l'API YouTube Data v3 (recherche) et l'extraction de transcripts."""

import json
import logging
import os
import re
import xml.etree.ElementTree as ET
from html import unescape

import httpx

logger = logging.getLogger(__name__)

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
_placeholder_warned = False


class YouTubeClient:
    """Client HTTP pour l'API YouTube Data v3 et les transcripts."""

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or os.getenv("YOUTUBE_API_KEY", "")
        # Ignorer les placeholders
        if self._api_key and self._api_key.startswith("your-"):
            self._api_key = ""

    def _headers(self) -> dict[str, str]:
        return {"Content-Type": "application/json"}

    async def search(
        self,
        query: str,
        max_results: int = 5,
        order: str = "relevance",
        timeout: int = 15,
    ) -> list[dict]:
        """Recherche de vidéos YouTube via l'API Data v3.

        Args:
            query: Termes de recherche.
            max_results: Nombre de résultats (max 10).
            order: Tri — relevance, date, rating, viewCount.
            timeout: Timeout HTTP en secondes.

        Returns:
            Liste de dicts {video_id, title, channel, description, published_at, url}.
        """
        if not self._api_key:
            return [{"error": "YOUTUBE_API_KEY non configurée. Créez une clé gratuite sur https://console.cloud.google.com/apis/credentials"}]

        params = {
            "part": "snippet",
            "q": query,
            "maxResults": min(max_results, 10),
            "order": order,
            "type": "video",
            "key": self._api_key,
        }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(f"{YOUTUBE_API_BASE}/search", params=params)
                if resp.status_code != 200:
                    logger.error(f"YouTube API error {resp.status_code}: {resp.text[:300]}")
                    return [{"error": f"YouTube API returned status {resp.status_code}"}]

                data = resp.json()
                results = []
                for item in data.get("items", []):
                    video_id = item["id"]["videoId"]
                    snippet = item["snippet"]
                    results.append({
                        "video_id": video_id,
                        "title": snippet["title"],
                        "channel": snippet["channelTitle"],
                        "description": (snippet.get("description", "") or "")[:300],
                        "published_at": snippet.get("publishedAt", ""),
                        "url": f"https://www.youtube.com/watch?v={video_id}",
                    })
                return results
        except Exception as e:
            logger.warning(f"YouTube search failed: {type(e).__name__}: {e}")
            return [{"error": f"Échec de la recherche YouTube: {e}"}]

    async def get_transcript(
        self,
        video_id: str,
        languages: list[str] | None = None,
        timeout: int = 15,
    ) -> str:
        """Récupère le transcript (sous-titres) d'une vidéo YouTube.

        Utilise l'endpoint timedtext interne de YouTube — pas besoin de clé API.

        Args:
            video_id: ID de la vidéo YouTube.
            languages: Liste de codes langue préférée (ex: ['fr', 'en']). Défaut: ['fr', 'en'].
            timeout: Timeout HTTP en secondes.

        Returns:
            Transcript formaté ou message d'erreur.
        """
        if not languages:
            languages = ["fr", "en"]

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                # Étape 1 : récupérer la page pour extraire les données de sous-titres
                resp = await client.get(
                    f"https://www.youtube.com/watch?v={video_id}",
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                    follow_redirects=True,
                )
                if resp.status_code != 200:
                    return f"Erreur: impossible d'accéder à la page YouTube (status {resp.status_code})"

                html = resp.text

                # Étape 2 : extraire les données de captions depuis ytInitialPlayerResponse
                match = re.search(r'var\s+ytInitialPlayerResponse\s*=\s*({.*?});', html, re.DOTALL)
                if not match:
                    match = re.search(r'window\["ytInitialPlayerResponse"\]\s*=\s*({.*?});', html, re.DOTALL)
                if not match:
                    # Essayer autre pattern
                    match = re.search(r'ytInitialPlayerResponse\s*=\s*({.*?});', html, re.DOTALL)

                if not match:
                    # Fallback: chercher les timedtext URLs directement dans le HTML
                    caption_urls = re.findall(r'"captionTracks":\s*(\[.*?\])', html, re.DOTALL)
                    if caption_urls:
                        try:
                            tracks = json.loads(unescape(caption_urls[0]))
                            return await self._best_transcript_from_tracks(client, tracks, languages, video_id)
                        except (json.JSONDecodeError, KeyError):
                            pass
                    return "Erreur: impossible d'extraire les données de sous-titres. La vidéo a peut-être des sous-titres désactivés."

                try:
                    player_data = json.loads(match.group(1))
                    captions = (
                        player_data.get("captions", {})
                        .get("playerCaptionsTracklistRenderer", {})
                        .get("captionTracks", [])
                    )
                    if not captions:
                        return "Aucun sous-titre disponible pour cette vidéo."

                    return await self._best_transcript_from_tracks(client, captions, languages, video_id)

                except (json.JSONDecodeError, KeyError) as e:
                    return f"Erreur lors du décodage des sous-titres: {e}"

        except Exception as e:
            logger.warning(f"Transcript fetch failed: {type(e).__name__}: {e}")
            return f"Erreur: échec de récupération du transcript — {e}"

    async def _best_transcript_from_tracks(
        self,
        client: httpx.AsyncClient,
        tracks: list[dict],
        languages: list[str],
        video_id: str,
    ) -> str:
        """Trouve la meilleure piste de sous-titres et la récupère."""
        # Chercher la piste dans les langues préférées
        for lang in languages:
            for track in tracks:
                if track.get("languageCode") == lang:
                    transcript = await self._fetch_transcript_xml(client, track, video_id)
                    if transcript and not transcript.startswith("Erreur"):
                        return f"[Transcript {lang.upper()}]\n\n{transcript}"

        # Fallback: première piste disponible
        if tracks:
            lang = tracks[0].get("languageCode", "??")
            transcript = await self._fetch_transcript_xml(client, tracks[0], video_id)
            if transcript and not transcript.startswith("Erreur"):
                return f"[Transcript {lang.upper()}]\n\n{transcript}"

        return "Aucun transcript trouvé dans les langues demandées."

    async def _fetch_transcript_xml(
        self,
        client: httpx.AsyncClient,
        track: dict,
        video_id: str,
    ) -> str:
        """Récupère et parse le XML timedtext d'une piste."""
        base_url = track.get("baseUrl", "")
        if not base_url:
            return "Erreur: URL de sous-titres introuvable"

        try:
            resp = await client.get(base_url)
            if resp.status_code != 200:
                return f"Erreur: échec de récupération des sous-titres (status {resp.status_code})"

            # Parser le XML timedtext
            root = ET.fromstring(resp.text)
            lines = []
            for text_elem in root.iter("{http://www.w3.org/2006/10/ttaf1}text") if root.tag.startswith("{") else root.iter("text"):
                text = "".join(text_elem.itertext())
                text = text.strip()
                if text:
                    lines.append(text)

            if not lines:
                return "Transcript vide."

            return "\n".join(lines)

        except ET.ParseError:
            # Si le XML est invalide, essayer d'extraire le texte brut
            text = re.sub(r"<[^>]+>", " ", resp.text)
            text = unescape(text).strip()
            return text if text else "Erreur: transcript illisible"
        except Exception as e:
            return f"Erreur lors du parsing du transcript: {e}"
