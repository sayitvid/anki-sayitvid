"""
SayItVid Anki Add-on - Card Template Filter
Provides {{sayitvid:FieldName}} filter for live, interactive pronunciation & authentic video widget playback.
Similar to Aglish / YouGlish, but powered by SayItVid.
"""

from __future__ import annotations

import html
import re
import urllib.parse
from typing import Any

try:
    from anki import hooks
    import aqt
    ANKI_AVAILABLE = True
except ImportError:
    hooks = None
    aqt = None
    ANKI_AVAILABLE = False


def clean_text_for_embed(raw: str) -> str:
    """Strip sound tags, HTML tags, and extra punctuation to get clean word for widget."""
    if not raw:
        return ""
    # Strip sound tags like [sound:xxx.mp3]
    no_sound = re.sub(r"\[sound:[^\]]+\]", "", raw)
    # Strip HTML tags
    clean = re.sub(r"<[^>]+>", " ", no_sound)
    # Unescape HTML entities
    unescaped = html.unescape(clean)
    # Normalize whitespace
    return " ".join(unescaped.split()).strip()


def render_sayitvid_widget(
    word: str,
    accent: str = "us",
    theme: str = "auto",
    base_url: str = "https://sayitvid.com",
    width: str = "100%",
    height: str = "380px",
) -> str:
    """
    Render the responsive HTML5 iframe widget for Anki Qt WebEngine / WebViews.
    No API calls required; loads directly via SayItVid's embed player.
    """
    if not word:
        return ""

    clean_word = clean_text_for_embed(word)
    if not clean_word:
        return ""

    # Night mode auto-detection if running inside desktop Anki
    resolved_theme = theme
    if resolved_theme in ("auto", "anki") and aqt and hasattr(aqt, "theme") and hasattr(aqt.theme, "theme_manager"):
        if getattr(aqt.theme.theme_manager, "night_mode", False):
            resolved_theme = "dark"
        else:
            resolved_theme = "light"

    slug = urllib.parse.quote(clean_word.lower().strip())
    embed_url = f"{base_url.rstrip('/')}/embed/word/{slug}?accent={urllib.parse.quote(accent)}&theme={urllib.parse.quote(resolved_theme)}"

    return f"""<div class="sayitvid-embed-container" style="margin: 12px auto; max-width: 580px; width: 100%;">
  <div style="position: relative; width: 100%; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.12); background: #0f172a;">
    <iframe
      src="{embed_url}"
      style="width: {width}; height: {height}; border: 0; display: block;"
      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
      allowfullscreen
      loading="lazy"
    ></iframe>
  </div>
</div>"""


def on_field_filter(
    field_text: str,
    field_name: str,
    filter_name: str,
    context: Any,
) -> str:
    """
    Hook for Anki's field filter system.
    Supports:
      {{sayitvid:FieldName}}
      {{sayitvid accent=uk:FieldName}}
      {{sayitvid accent=aus theme=dark:FieldName}}
    """
    parts = filter_name.split()
    if not parts or parts[0].lower() != "sayitvid":
        return field_text

    accent = "us"
    theme = "auto"
    for part in parts[1:]:
        if "=" in part:
            k, v = part.split("=", 1)
            k = k.lower().strip()
            v = v.lower().strip()
            if k in ("accent", "lang", "language"):
                accent = v
            elif k == "theme":
                theme = v

    word = clean_text_for_embed(field_text)
    if not word:
        return field_text

    return render_sayitvid_widget(word, accent=accent, theme=theme)


def setup_card_filter():
    """Register filter hook with Anki."""
    if ANKI_AVAILABLE and hooks and hasattr(hooks, "field_filter"):
        hooks.field_filter.append(on_field_filter)
