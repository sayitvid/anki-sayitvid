"""
SayItVid Anki Add-on - Card Template Filter
Provides {{sayitvid:FieldName}} filter for live, interactive pronunciation & video playback.
"""

from __future__ import annotations

import html
import re
import urllib.parse
from typing import Any

try:
    from anki import hooks
    ANKI_AVAILABLE = True
except ImportError:
    hooks = None
    ANKI_AVAILABLE = False


def clean_text_for_embed(raw: str) -> str:
    """Strip sound tags and HTML to get clean word for widget."""
    if not raw:
        return ""
    no_sound = re.sub(r"\[sound:[^\]]+\]", "", raw)
    clean = re.sub(r"<[^>]+>", " ", no_sound)
    unescaped = html.unescape(clean)
    return " ".join(unescaped.split()).strip()


def render_sayitvid_widget(word: str, accent: str = "us", base_url: str = "https://sayitvid.com") -> str:
    """Render the responsive HTML5 iframe widget for Anki Qt WebEngine."""
    if not word:
        return ""
    slug = urllib.parse.quote(word.lower())
    embed_url = f"{base_url.rstrip('/')}/embed/word/{slug}?accent={accent}&theme=auto"

    return f"""
<div class="sayitvid-embed-container" style="margin: 10px auto; max-width: 580px; width: 100%;">
  <div style="position: relative; width: 100%; aspect-ratio: 16/9; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.12); background: #000;">
    <iframe
      src="{embed_url}"
      style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: 0;"
      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
      allowfullscreen
    ></iframe>
  </div>
</div>
"""


def on_field_filter(
    field_text: str,
    field_name: str,
    filter_name: str,
    context: Any,
) -> str:
    """
    Hook for Anki's field filter system.
    Matches {{sayitvid:FieldName}} in card templates.
    """
    if filter_name.lower() == "sayitvid":
        word = clean_text_for_embed(field_text)
        if not word:
            return field_text
        return render_sayitvid_widget(word)
    return field_text


def setup_card_filter():
    """Register filter hook with Anki."""
    if ANKI_AVAILABLE and hooks and hasattr(hooks, "field_filter"):
        hooks.field_filter.append(on_field_filter)
