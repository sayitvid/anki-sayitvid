"""
SayItVid Anki Add-on - Note Enricher Engine
Embeds responsive SayItVid pronunciation & video widgets directly into Anki note fields.
Zero API calls, zero server keys required.
"""

from __future__ import annotations

import html
import re
from typing import Any, Dict, List, Optional

from .card_filter import clean_text_for_embed, render_sayitvid_widget


class NoteEnricher:
    def __init__(
        self,
        config: Dict[str, Any],
        media_writer: Optional[Any] = None,
    ):
        self.config = config
        self.base_url = config.get("base_url") or config.get("api_base_url") or "https://sayitvid.com"

    @staticmethod
    def clean_html_text(raw_text: str) -> str:
        """Strip HTML tags and unescape entities to extract clean search word."""
        return clean_text_for_embed(raw_text)

    @staticmethod
    def is_sayitvid_content(text: str) -> bool:
        """Check if the string already contains SayItVid generated elements."""
        if not text:
            return False
        markers = [
            "sayitvid.com",
            "sayitvid-embed-container",
            "sayitvid-stress",
            "sayitvid-target-word",
            "{{sayitvid:",
        ]
        return any(marker in text for marker in markers)

    def enrich_single_note(
        self,
        note: Any,
        source_field: str = "Front",
        target_mappings: Optional[Dict[str, str]] = None,
        accent: str = "us",
        theme: str = "auto",
        overwrite: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Enrich a single Anki note object or dict with the SayItVid embed widget.
        Returns result summary dict.
        """
        result = {
            "word": "",
            "success": False,
            "updated_fields": [],
            "skipped_fields": [],
            "error": None,
        }

        note_keys = list(note.keys()) if hasattr(note, "keys") else []
        actual_source = source_field

        # 1. Extract source word
        if hasattr(note, "__getitem__"):
            if actual_source not in note and note_keys:
                common_sources = ["Front", "Word", "Expression", "Text", "Term", "Vocab", "Vocabulary"]
                for candidate in common_sources:
                    for k in note_keys:
                        if k.lower() == candidate.lower():
                            actual_source = k
                            break
                    if actual_source in note:
                        break
                if actual_source not in note:
                    actual_source = note_keys[0]

            try:
                raw_word = note[actual_source]
            except KeyError:
                result["error"] = f"Source field '{source_field}' not found on note."
                return result
        else:
            raw_word = getattr(note, source_field, "")

        clean_word = self.clean_html_text(raw_word)
        if not clean_word:
            result["error"] = f"Source field '{actual_source}' is empty."
            return result

        result["word"] = clean_word

        # 2. Determine target video field
        mappings = target_mappings or self.config.get("field_mappings", {})
        configured_target = mappings.get("target_video", "Video")

        target_field = None
        if configured_target and configured_target != "(None)":
            if configured_target in note_keys:
                target_field = configured_target

        if not target_field:
            for alias in ["Video", "SayItVid", "Clip", "Movie", "YouTube", "Embed", "Back"]:
                for k in note_keys:
                    if k.lower() == alias.lower():
                        target_field = k
                        break
                if target_field:
                    break

        if not target_field:
            result["error"] = (
                f"No suitable target field found on note (available: {', '.join(note_keys)}). "
                f"Create a 'Video' or 'SayItVid' field or configure field mapping in settings."
            )
            return result

        # 3. Check existing content
        current_val = note[target_field].strip() if hasattr(note, "__getitem__") else ""
        if current_val and not overwrite:
            if not self.is_sayitvid_content(current_val):
                result["skipped_fields"].append(target_field)
                result["success"] = True
                return result

        # 4. Generate responsive widget HTML
        widget_html = render_sayitvid_widget(
            clean_word,
            accent=accent,
            theme=theme,
            base_url=self.base_url,
        )

        note[target_field] = widget_html
        result["updated_fields"].append(target_field)
        result["success"] = True

        return result
