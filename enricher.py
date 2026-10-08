"""
SayItVid Anki Add-on - Note Enricher Engine
Maps SayItVid linguistic and multimedia data to Anki note fields and writes media files.
"""

from __future__ import annotations

import html
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

from .api_client import SayItVidApiClient


class NoteEnricher:
    def __init__(
        self,
        config: Dict[str, Any],
        api_client: Optional[SayItVidApiClient] = None,
        media_writer: Optional[Callable[[str, bytes], str]] = None,
    ):
        self.config = config
        self.api_client = api_client or SayItVidApiClient(
            base_url=config.get("api_base_url", "https://sayitvid.com"),
            api_key=config.get("api_key", ""),
        )
        self.media_writer = media_writer

    @staticmethod
    def clean_html_text(raw_text: str) -> str:
        """Strip HTML tags and unescape entities to extract clean search word."""
        if not raw_text:
            return ""
        # Remove sound tags like [sound:xxx.mp3]
        no_sound = re.sub(r"\[sound:[^\]]+\]", "", raw_text)
        # Strip HTML tags
        clean = re.sub(r"<[^>]+>", " ", no_sound)
        # Unescape HTML entities
        unescaped = html.unescape(clean)
        # Normalize whitespace
        return " ".join(unescaped.split()).strip()

    @staticmethod
    def is_sayitvid_content(text: str) -> bool:
        """Check if the string already contains SayItVid generated elements."""
        if not text:
            return False
        markers = [
            "sayitvid.com",
            "sayitvid-stress",
            "sayitvid-target-word",
            "sayitvid-card-block",
            "sayitvid-divider",
            "Watch video clips on SayItVid",
            "[sound:sayitvid_",
            "sayitvid_",
            "youtube-nocookie.com/embed",
        ]
        return any(marker in text for marker in markers)

    def enrich_single_note(
        self,
        note: Any,
        source_field: str,
        target_mappings: Dict[str, str],
        accent: str = "us",
        overwrite: bool = False,
        download_audio: bool = True,
        tag_cefr: bool = True,
    ) -> Dict[str, Any]:
        """
        Enrich a single Anki note object or dict with SayItVid data.
        Returns result summary dict.
        """
        result = {
            "word": "",
            "success": False,
            "updated_fields": [],
            "skipped_fields": [],
            "audio_saved": False,
            "error": None,
        }

        note_keys = list(note.keys()) if hasattr(note, "keys") else []
        actual_source = source_field

        # 1. Extract and sanitize source word with smart fallback
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

        # 2. Query SayItVid API
        ok, data, err_msg = self.api_client.lookup_word(clean_word, accent=accent)
        if not ok or not data:
            result["error"] = err_msg or "Failed to retrieve word data."
            return result

        updated_fields: List[str] = []
        skipped_fields: List[str] = []

        # Helper to safely set field
        def set_field_value(field_name: Optional[str], new_val: str, allow_append_sound: bool = False):
            if not field_name:
                return
            if not hasattr(note, "__getitem__"):
                return
            try:
                current_val = note[field_name].strip()
            except KeyError:
                return

            if current_val and not overwrite:
                if self.is_sayitvid_content(current_val):
                    note[field_name] = new_val
                    updated_fields.append(field_name)
                    return
                elif allow_append_sound and "[sound:" not in current_val:
                    note[field_name] = f"{current_val} {new_val}".strip()
                    updated_fields.append(field_name)
                    return
                else:
                    skipped_fields.append(field_name)
                    return

            note[field_name] = new_val
            updated_fields.append(field_name)

        # Smart field resolution with fallback aliases
        def resolve_field(target_key: str, default_name: str, aliases: List[str]) -> Optional[str]:
            configured = target_mappings.get(target_key, default_name)
            if configured and configured != "(None)":
                if configured in note_keys:
                    return configured
            for alias in aliases:
                for k in note_keys:
                    if k.lower() == alias.lower():
                        return k
            return None

        # 3. Audio Download & Tag injection
        audio_field = resolve_field("target_audio", "Audio", ["Audio", "Sound", "Voice", "Pronunciation Audio", "Media"])
        audio_url = data.get("audioUrl")

        if download_audio and audio_field and audio_url and self.media_writer:
            filename = self.api_client.sanitize_filename(clean_word, accent)
            audio_ok, audio_bytes, audio_err = self.api_client.download_audio(audio_url)
            if audio_ok and audio_bytes:
                try:
                    # Write into Anki collection.media
                    saved_filename = self.media_writer(filename, audio_bytes)
                    sound_tag = f"[sound:{saved_filename}]"
                    set_field_value(audio_field, sound_tag, allow_append_sound=True)
                    result["audio_saved"] = True
                except Exception as write_err:
                    logger_msg = f"Failed to save audio media: {write_err}"
                    result["audio_error"] = logger_msg

        # 4. IPA Field
        ipa_field = resolve_field("target_ipa", "IPA", ["IPA", "Phonetic", "Pronunciation", "Reading", "Phonetics"])
        if ipa_field and data.get("ipa"):
            set_field_value(ipa_field, data["ipa"])

        # 5. Syllables & Stress Field
        syllables_field = resolve_field("target_syllables", "Syllables", ["Syllables", "Syllable", "Stress"])
        if syllables_field:
            formatted_syllables = data.get("formattedSyllablesHtml") or data.get("syllableText")
            if formatted_syllables:
                set_field_value(syllables_field, formatted_syllables)

        # 6. Definition Field
        def_field = resolve_field("target_definition", "Definition", ["Definition", "Meaning", "Translation", "Def", "Glossary"])
        if def_field and data.get("definition"):
            set_field_value(def_field, data["definition"])

        # 7. Context Sentence Field
        sentence_field = resolve_field("target_sentence", "Sentence", ["Sentence", "Example", "Context", "Sample Sentence", "Context Sentence", "Examples"])
        clip = data.get("clip")
        if sentence_field and clip:
            sentence_html = clip.get("formattedSentenceHtml") or clip.get("text")
            if sentence_html:
                set_field_value(sentence_field, sentence_html)

        # 8. Video Embed / Link Field
        video_field = resolve_field("target_video", "Video", ["Video", "Clip", "SayItVid", "Movie", "YouTube"])
        clip = data.get("clip") or {}
        video_id = clip.get("videoId")
        start_time = int(float(clip.get("startTime") or 0)) if clip else 0
        video_url = clip.get("videoEmbedUrl")
        if not video_url and video_id:
            video_url = f"https://www.youtube-nocookie.com/embed/{video_id}?start={start_time}&rel=0"
        if not video_url:
            video_url = data.get("embedUrl")

        if video_field and video_url:
            width = self.config.get("video_embed_width", 560)
            height = self.config.get("video_embed_height", 315)
            iframe_html = (
                f'<iframe src="{video_url}" '
                f'width="{width}" height="{height}" '
                f'frameborder="0" allow="autoplay; encrypted-media" '
                f'allowfullscreen style="border-radius:8px;max-width:100%;"></iframe>'
            )
            set_field_value(video_field, iframe_html)

        # 9. CEFR Field & Tag
        cefr_field = resolve_field("target_cefr", "CEFR", ["CEFR", "Level", "Difficulty"])
        cefr_level = data.get("cefr")
        if cefr_field and cefr_level:
            set_field_value(cefr_field, cefr_level)

        if tag_cefr and cefr_level and hasattr(note, "add_tag"):
            note.add_tag(f"CEFR:{cefr_level}")

        # 10. Fallback for standard 2-field cards (e.g. Front / Back)
        # If no dedicated fields were found or updated on the note, compile into Back
        if len(updated_fields) == 0 and note_keys:
            fallback_target = None
            if "Back" in note_keys and actual_source != "Back":
                fallback_target = "Back"
            elif "Back Extra" in note_keys:
                fallback_target = "Back Extra"
            elif len(note_keys) >= 2:
                candidates = [f for f in note_keys if f != actual_source]
                if candidates:
                    fallback_target = candidates[0]

            if fallback_target and hasattr(note, "__getitem__") and fallback_target in note:
                # Ensure audio is downloaded if enabled
                sound_tag = ""
                audio_url = data.get("audioUrl")
                if download_audio and audio_url and self.media_writer:
                    filename = self.api_client.sanitize_filename(clean_word, accent)
                    audio_ok, audio_bytes, audio_err = self.api_client.download_audio(audio_url)
                    if audio_ok and audio_bytes:
                        try:
                            saved_filename = self.media_writer(filename, audio_bytes)
                            sound_tag = f"[sound:{saved_filename}]"
                            result["audio_saved"] = True
                        except Exception as write_err:
                            result["audio_error"] = str(write_err)

                # Format rich composite learning block
                ipa = data.get("ipa") or ""
                formatted_syllables = data.get("formattedSyllablesHtml") or data.get("syllableText") or ""
                definition = data.get("definition") or ""
                clip = data.get("clip") or {}
                sentence = clip.get("formattedSentenceHtml") or clip.get("text") or ""
                video_id = clip.get("videoId")
                start_time = int(float(clip.get("startTime") or 0)) if clip else 0
                video_url = clip.get("videoEmbedUrl")
                if not video_url and video_id:
                    video_url = f"https://www.youtube-nocookie.com/embed/{video_id}?start={start_time}&rel=0"
                if not video_url:
                    video_url = data.get("embedUrl")
                sayitvid_url = data.get("sayitvidUrl") or f"https://sayitvid.com/pronounce/{clean_word}"

                parts = ["<div class='sayitvid-card-block'>"]
                # Header row: word + IPA + sound
                header = f"<div style='font-size: 1.2em; font-weight: bold; margin-bottom: 4px;'>"
                header += f"{clean_word}"
                if ipa:
                    header += f" <span style='font-size: 0.85em; font-weight: normal; color: #64748b; font-family: monospace;'>{ipa}</span>"
                pos = data.get("partOfSpeech")
                cefr = data.get("cefr")
                if pos:
                    header += f" <span style='font-size: 0.7em; font-weight: 600; color: #0284c7; background: #e0f2fe; padding: 2px 6px; border-radius: 4px;'>{pos}</span>"
                if cefr:
                    header += f" <span style='font-size: 0.7em; font-weight: 600; color: #b45309; background: #fef3c7; padding: 2px 6px; border-radius: 4px;'>CEFR {cefr}</span>"
                if sound_tag:
                    header += f" {sound_tag}"
                header += "</div>"
                parts.append(header)

                # Heteronym Warning
                if data.get("heteronymWarning"):
                    parts.append(f"<div style='color: #d97706; font-size: 0.85em; margin-bottom: 6px;'>⚠️ {data['heteronymWarning']}</div>")

                # Homophones
                if data.get("homophones"):
                    h_list = ", ".join(data["homophones"])
                    parts.append(f"<div style='color: #64748b; font-size: 0.85em; margin-bottom: 6px;'>Homophones: {h_list}</div>")

                # Syllables with stress
                if formatted_syllables:
                    parts.append(f"<div style='color: #64748b; font-size: 0.9em; margin-bottom: 6px;'>Syllables: {formatted_syllables}</div>")

                # Definition
                if definition:
                    parts.append(f"<div style='margin-bottom: 8px; line-height: 1.4;'>{definition}</div>")

                # Sentence context
                if sentence:
                    parts.append(f"<div style='margin-bottom: 8px; font-style: italic; color: #334155; line-height: 1.4;'>&ldquo;{sentence}&rdquo;</div>")

                # Video embed player
                if video_url:
                    height = self.config.get("video_embed_height", 280)
                    parts.append(
                        f"<div style='margin-top: 8px; margin-bottom: 6px;'>"
                        f"<iframe src='{video_url}' width='100%' height='{height}' frameborder='0' allow='autoplay; encrypted-media' allowfullscreen style='border-radius:8px;max-width:100%;aspect-ratio:16/9;'></iframe>"
                        f"</div>"
                    )

                # SayItVid link
                parts.append(
                    f"<div><a href='{sayitvid_url}' style='color: #e11d48; text-decoration: none; font-size: 0.85em; font-weight: 600;'>▶ Watch video clips on SayItVid</a></div>"
                )
                parts.append("</div>")

                rich_html = "\n".join(parts)
                current_target_val = note[fallback_target].strip()

                if not current_target_val:
                    note[fallback_target] = rich_html
                    updated_fields.append(fallback_target)
                elif overwrite:
                    note[fallback_target] = rich_html
                    updated_fields.append(fallback_target)
                elif self.is_sayitvid_content(current_target_val):
                    # Replace previous SayItVid block while preserving any custom user header/notes
                    if "<hr class='sayitvid-divider'" in current_target_val:
                        user_prefix = current_target_val.split("<hr class='sayitvid-divider'")[0].strip()
                        note[fallback_target] = f"{user_prefix}\n<hr class='sayitvid-divider' style='margin:12px 0;border:0;border-top:1px dashed #cbd5e1;'>\n{rich_html}"
                    elif "<div class='sayitvid-card-block'" in current_target_val:
                        user_prefix = current_target_val.split("<div class='sayitvid-card-block'")[0].strip()
                        note[fallback_target] = f"{user_prefix}\n{rich_html}" if user_prefix else rich_html
                    else:
                        note[fallback_target] = rich_html
                    updated_fields.append(fallback_target)
                else:
                    # Append cleanly below divider to preserve user's own definition/translation
                    note[fallback_target] = (
                        f"{current_target_val}\n"
                        f"<hr class='sayitvid-divider' style='margin:12px 0;border:0;border-top:1px dashed #cbd5e1;'>\n"
                        f"{rich_html}"
                    )
                    updated_fields.append(fallback_target)

        result["success"] = True
        result["updated_fields"] = updated_fields
        result["skipped_fields"] = skipped_fields
        return result
