"""
SayItVid Anki Add-on - API Client
Handles thread-safe HTTP communication with SayItVid backend using Python standard library.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("sayitvid_anki")


class SayItVidApiClient:
    def __init__(self, base_url: str = "https://sayitvid.com", api_key: str = ""):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key.strip()
        self.user_agent = "SayItVid-AnkiAddon/1.0.0"

    def lookup_word(
        self,
        word: str,
        accent: str = "us",
        timeout: int = 15,
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Lookup word data, phonetics, video clips, and audio from SayItVid.
        Returns (success: bool, data: Optional[Dict], error_message: Optional[str]).
        """
        clean_word = word.strip()
        if not clean_word:
            return False, None, "Word query is empty."

        query_params = urllib.parse.urlencode({
            "word": clean_word,
            "accent": accent,
        })
        url = f"{self.base_url}/api/anki/lookup?{query_params}"

        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
        }
        if self.api_key:
            headers["x-api-key"] = self.api_key

        req = urllib.request.Request(url, headers=headers, method="GET")

        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                status_code = response.getcode()
                response_data = response.read().decode("utf-8")
                parsed = json.loads(response_data)

                if status_code == 200:
                    data_obj = None
                    if "data" in parsed and isinstance(parsed["data"], dict):
                        data_obj = parsed["data"]
                    elif "word" in parsed or parsed.get("success"):
                        data_obj = parsed
                    else:
                        err = parsed.get("error", f"HTTP {status_code}")
                        return False, None, str(err)

                    if data_obj and not data_obj.get("audioUrl"):
                        data_obj["audioUrl"] = f"{self.base_url}/api/word-audio?word={urllib.parse.quote(clean_word)}&lang=en"

                    return True, data_obj, None
                else:
                    err = parsed.get("error", f"HTTP {status_code}")
                    return False, None, str(err)

        except urllib.error.HTTPError as e:
            if e.code == 404:
                # Production fallback if /api/anki/lookup is not yet deployed on server
                return self._lookup_via_search(clean_word, accent, timeout)
            try:
                err_body = e.read().decode("utf-8")
                err_json = json.loads(err_body)
                msg = err_json.get("error", f"HTTP Error {e.code}")
            except Exception:
                msg = f"HTTP Error {e.code}: {e.reason}"
            return False, None, msg

        except urllib.error.URLError as e:
            return False, None, f"Network Connection Error: {e.reason}"

        except json.JSONDecodeError:
            return False, None, "Invalid JSON response from SayItVid server."

        except Exception as e:
            return False, None, f"Unexpected error: {str(e)}"

    def _lookup_via_search(
        self,
        clean_word: str,
        accent: str,
        timeout: int,
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Fallback to live /api/search endpoint on production server."""
        query_params = urllib.parse.urlencode({
            "q": clean_word,
            "accent": accent,
            "limit": 3,
        })
        url = f"{self.base_url}/api/search?{query_params}"
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
        }
        if self.api_key:
            headers["x-api-key"] = self.api_key

        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                if response.getcode() != 200:
                    return False, None, f"HTTP Error {response.getcode()}"
                parsed = json.loads(response.read().decode("utf-8"))

                hits = parsed.get("hits", [])
                top_hit = hits[0] if hits else None
                word_info = parsed.get("word_info") or {}

                # Format syllables with primary stress
                syllables = word_info.get("syllables", [clean_word])
                stressed_idx = word_info.get("stressedIndex", 0)
                formatted_syllables = " · ".join(
                    f'<b class="sayitvid-stress" style="color:#e11d48;font-weight:700;">{s}</b>'
                    if i == stressed_idx else s
                    for i, s in enumerate(syllables)
                )

                audio_url = word_info.get("audioUrl")
                if not audio_url and word_info.get("audioUrls"):
                    urls = word_info["audioUrls"]
                    audio_url = urls.get(accent) or urls.get("us")

                clip_data = None
                youtube_nocookie_url = None
                if top_hit:
                    tb = top_hit.get("text_before", "")
                    ta = top_hit.get("text_after", "")
                    tw = top_hit.get("text", "")

                    escaped_word = re.escape(clean_word)
                    word_pattern = re.compile(rf"\b({escaped_word})\b", re.IGNORECASE)
                    if word_pattern.search(tw):
                        highlighted_tw = word_pattern.sub(
                            r"<b class='sayitvid-target-word' style='color:#e11d48;font-weight:700;'>\1</b>",
                            tw,
                        )
                    else:
                        loose_pattern = re.compile(rf"({escaped_word})", re.IGNORECASE)
                        highlighted_tw = loose_pattern.sub(
                            r"<b class='sayitvid-target-word' style='color:#e11d48;font-weight:700;'>\1</b>",
                            tw,
                        )

                    before_span = f"<span class='sayitvid-context-before' style='color:#64748b;'>{tb} </span>" if tb else ""
                    after_span = f"<span class='sayitvid-context-after' style='color:#64748b;'> {ta}</span>" if ta else ""
                    formatted_sentence = f"{before_span}{highlighted_tw}{after_span}"

                    video_id = top_hit.get("video_id")
                    start_sec = int(float(top_hit.get("start_time", 0)))
                    if video_id:
                        youtube_nocookie_url = f"https://www.youtube-nocookie.com/embed/{video_id}?start={start_sec}&rel=0"

                    clip_data = {
                        "videoId": video_id,
                        "startTime": top_hit.get("start_time"),
                        "duration": top_hit.get("duration"),
                        "accent": top_hit.get("accent") or accent,
                        "channelName": top_hit.get("channel_name"),
                        "text": tw,
                        "textBefore": tb,
                        "textAfter": ta,
                        "formattedSentenceHtml": formatted_sentence,
                        "youtubeUrl": f"https://www.youtube.com/watch?v={video_id}&t={start_sec}s" if video_id else None,
                        "videoEmbedUrl": youtube_nocookie_url,
                    }

                data = {
                    "word": word_info.get("word") or clean_word,
                    "displayWord": word_info.get("displayWord") or clean_word,
                    "accent": accent,
                    "ipa": word_info.get("ipa"),
                    "syllables": syllables,
                    "syllableText": word_info.get("syllableText") or " · ".join(syllables),
                    "stressedIndex": stressed_idx,
                    "formattedSyllablesHtml": formatted_syllables,
                    "cefr": None,
                    "definition": word_info.get("primaryDefinition"),
                    "audioUrl": audio_url,
                    "clip": clip_data,
                    "embedUrl": youtube_nocookie_url or f"https://sayitvid.com/embed/word/{urllib.parse.quote(clean_word)}?accent={accent}",
                    "sayitvidUrl": word_info.get("sayitvidUrl") or f"https://sayitvid.com/pronounce/{clean_word}",
                }
                return True, data, None
        except Exception as e:
            return False, None, f"SayItVid Search Error: {str(e)}"

    def download_audio(
        self,
        audio_url: str,
        timeout: int = 15,
    ) -> Tuple[bool, Optional[bytes], Optional[str]]:
        """
        Download binary audio MP3 content from URL.
        Returns (success: bool, audio_bytes: Optional[bytes], error_message: Optional[str]).
        """
        if not audio_url:
            return False, None, "No audio URL provided."

        headers = {
            "User-Agent": self.user_agent,
            "Accept": "audio/mpeg, audio/*; q=0.9, */*; q=0.5",
        }
        req = urllib.request.Request(audio_url, headers=headers, method="GET")

        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                content_type = response.headers.get("Content-Type", "")
                data = response.read()

                if len(data) == 0:
                    return False, None, "Audio response was empty."

                # Basic validation: check audio size or header
                if len(data) < 500:
                    return False, None, "Audio file suspiciously small."

                return True, data, None

        except urllib.error.HTTPError as e:
            return False, None, f"HTTP Error downloading audio: {e.code}"
        except urllib.error.URLError as e:
            return False, None, f"Network Error downloading audio: {e.reason}"
        except Exception as e:
            return False, None, f"Failed to download audio: {str(e)}"

    @staticmethod
    def sanitize_filename(word: str, accent: str = "us") -> str:
        """
        Generate a safe, unique filename for storage in collection.media.
        e.g. sayitvid_courage_us.mp3
        """
        clean = re.sub(r"[^a-zA-Z0-9_\-]", "_", word.lower().strip())
        clean = re.sub(r"_+", "_", clean).strip("_")
        return f"sayitvid_{clean}_{accent}.mp3"
