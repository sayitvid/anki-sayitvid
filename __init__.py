"""
SayItVid Anki Add-on
Main add-on entry point connecting SayItVid to Anki Desktop.
"""

from __future__ import annotations

import logging
import os
from typing import Any, List

try:
    from aqt import mw, gui_hooks
    from aqt.browser import Browser
    from aqt.editor import Editor
    from aqt.qt import QAction, QKeySequence
    from aqt.utils import showInfo, showWarning, tooltip
    ANKI_AVAILABLE = True
except ImportError:
    mw = None
    gui_hooks = None
    ANKI_AVAILABLE = False

from .card_filter import setup_card_filter
from .enricher import NoteEnricher
from .ui_dialog import BatchEnrichDialog

logger = logging.getLogger("sayitvid_anki")


def get_addon_config() -> dict:
    """Load configuration from Anki addon manager."""
    if mw and hasattr(mw, "addonManager"):
        cfg = mw.addonManager.getConfig(__name__)
        if isinstance(cfg, dict):
            return cfg
    return {
        "api_base_url": "https://sayitvid.com",
        "api_key": "",
        "default_accent": "us",
        "download_audio": True,
        "overwrite_existing": False,
        "field_mappings": {
            "source_word": "Front",
            "target_audio": "Audio",
            "target_ipa": "IPA",
            "target_syllables": "Syllables",
            "target_definition": "Definition",
            "target_sentence": "Sentence",
            "target_video": "Video",
            "target_cefr": "CEFR",
        },
        "tag_cefr": True,
    }


def on_enrich_browser_selection(browser: Browser):
    """Open BatchEnrichDialog for currently selected notes in the Browser."""
    selected_nids = browser.selected_notes()
    if not selected_nids:
        showWarning("Please select at least one note to enrich with SayItVid.", parent=browser)
        return

    config = get_addon_config()
    dialog = BatchEnrichDialog(browser, selected_nids, config)
    dialog.exec()


def setup_browser_menu(browser: Browser):
    """Add SayItVid action to Anki's Browser Edit menu."""
    action = QAction("SayItVid: Enrich Selected Notes...", browser)
    action.setShortcut(QKeySequence("Ctrl+Shift+S"))
    action.triggered.connect(lambda: on_enrich_browser_selection(browser))

    # Add to Edit menu
    if hasattr(browser, "form") and hasattr(browser.form, "menuEdit"):
        browser.form.menuEdit.addSeparator()
        browser.form.menuEdit.addAction(action)


def on_editor_quick_enrich(editor: Editor):
    """Enrich the current note directly in the Add/Edit Note dialog."""
    note = editor.note
    if not note:
        return

    config = get_addon_config()
    source_field = config.get("field_mappings", {}).get("source_word", "Front")

    def media_writer_wrapper(filename: str, data: bytes) -> str:
        if mw and mw.col and mw.col.media:
            return mw.col.media.write_data(filename, data)
        return filename

    enricher = NoteEnricher(config=config, media_writer=media_writer_wrapper)
    result = enricher.enrich_single_note(
        note=note,
        source_field=source_field,
        target_mappings=config.get("field_mappings", {}),
        accent=config.get("default_accent", "us"),
        overwrite=config.get("overwrite_existing", False),
        download_audio=config.get("download_audio", True),
        tag_cefr=config.get("tag_cefr", True),
    )

    parent_win = getattr(editor, "parentWindow", None)
    if callable(parent_win):
        parent_win = parent_win()
    if not parent_win:
        parent_win = getattr(editor, "widget", None) or mw

    if result["success"]:
        # Persist changes to database if note already exists
        if getattr(note, "id", None) and mw and mw.col:
            try:
                mw.col.update_note(note)
            except Exception as save_err:
                logger.warning("Could not persist note directly: %s", save_err)

        # Force Editor to redraw with the new field values
        if hasattr(editor, "loadNoteKeepingFocus"):
            editor.loadNoteKeepingFocus()
        else:
            editor.loadNote()

        word = result.get("word", "")
        updated = result.get("updated_fields", [])
        skipped = result.get("skipped_fields", [])
        if updated:
            fields_str = ", ".join(updated)
            try:
                tooltip(f"SayItVid enriched '{word}' ({fields_str})", parent=parent_win)
            except Exception:
                if hasattr(mw, "statusBar"):
                    mw.statusBar().showMessage(f"SayItVid enriched '{word}': {fields_str}", 4000)
        elif skipped:
            fields_str = ", ".join(skipped)
            showInfo(
                f"SayItVid found data for '{word}', but field(s) '{fields_str}' already have content.\n\n"
                f"Enable 'Overwrite existing' in SayItVid preferences or use the Note Browser to overwrite.",
                parent=parent_win
            )
        else:
            note_keys = list(note.keys()) if hasattr(note, "keys") else []
            model_name = note.model().get("name", "") if hasattr(note, "model") else "Unknown"
            showWarning(
                f"SayItVid found data for '{word}', but could not map to fields on note type '{model_name}'.\n"
                f"Available fields on this card: {', '.join(note_keys)}\n\n"
                f"Check field mappings in Tools → Add-ons → SayItVid → Config.",
                parent=parent_win
            )
    else:
        showWarning(result.get("error", "Failed to enrich note with SayItVid."), parent=parent_win)


def setup_editor_button(buttons: List[str], editor: Editor) -> List[str]:
    """Add a SayItVid button to Anki's Note Editor toolbar."""
    addon_dir = os.path.dirname(__file__)
    icon_path = os.path.join(addon_dir, "icon.png")
    if not os.path.exists(icon_path):
        icon_path = os.path.join(addon_dir, "icon.svg")

    btn = editor.addButton(
        icon=icon_path if os.path.exists(icon_path) else None,
        cmd="sayitvid_enrich",
        func=lambda ed: on_editor_quick_enrich(ed),
        label="SayItVid",
        id="sayitvid_button",
        tip="Enrich with SayItVid (Audio, IPA, Syllables, Video) [F8]",
        keys="F8",
    )

    custom_style = (
        "<style>"
        "#sayitvid_button, button[data-command='sayitvid_enrich'] {"
        "  display: inline-flex !important;"
        "  align-items: center !important;"
        "  justify-content: center !important;"
        "  gap: 6px !important;"
        "  padding: 0 10px !important;"
        "  width: auto !important;"
        "  min-width: unset !important;"
        "  height: 32px !important;"
        "  border-radius: 5px !important;"
        "  font-size: 13px !important;"
        "  font-weight: 600 !important;"
        "  line-height: 1 !important;"
        "  cursor: pointer !important;"
        "  box-sizing: border-box !important;"
        "  vertical-align: middle !important;"
        "}"
        "#sayitvid_button img.topbut, button[data-command='sayitvid_enrich'] img.topbut {"
        "  position: static !important;"
        "  display: inline-block !important;"
        "  width: 18px !important;"
        "  height: 18px !important;"
        "  min-width: 18px !important;"
        "  min-height: 18px !important;"
        "  max-width: 18px !important;"
        "  max-height: 18px !important;"
        "  margin: 0 !important;"
        "  padding: 0 !important;"
        "  border: none !important;"
        "  object-fit: contain !important;"
        "  vertical-align: middle !important;"
        "  filter: none !important;"
        "}"
        ".nightMode #sayitvid_button img.topbut, "
        ".nightMode button[data-command='sayitvid_enrich'] img.topbut {"
        "  filter: none !important;"
        "}"
        "</style>"
    )
    buttons.append(btn + custom_style)
    return buttons


def on_editor_web_view_init(web_view: Any):
    """Ensure custom button styles are injected into editor webview."""
    js = """
    (function() {
        if (document.getElementById('sayitvid-style')) return;
        const s = document.createElement('style');
        s.id = 'sayitvid-style';
        s.textContent = `
            #sayitvid_button, button[data-command="sayitvid_enrich"] {
                display: inline-flex !important;
                align-items: center !important;
                justify-content: center !important;
                gap: 6px !important;
                padding: 0 10px !important;
                width: auto !important;
                min-width: unset !important;
                height: 32px !important;
                border-radius: 5px !important;
                font-size: 13px !important;
                font-weight: 600 !important;
                line-height: 1 !important;
                cursor: pointer !important;
                box-sizing: border-box !important;
                vertical-align: middle !important;
            }
            #sayitvid_button img.topbut, button[data-command="sayitvid_enrich"] img.topbut {
                position: static !important;
                display: inline-block !important;
                width: 18px !important;
                height: 18px !important;
                min-width: 18px !important;
                min-height: 18px !important;
                max-width: 18px !important;
                max-height: 18px !important;
                margin: 0 !important;
                padding: 0 !important;
                border: none !important;
                object-fit: contain !important;
                vertical-align: middle !important;
                filter: none !important;
            }
            .nightMode #sayitvid_button img.topbut,
            .nightMode button[data-command="sayitvid_enrich"] img.topbut {
                filter: none !important;
            }
        `;
        document.head.appendChild(s);
    })();
    """
    if hasattr(web_view, "loadFinished"):
        try:
            web_view.loadFinished.connect(lambda ok: web_view.eval(js) if ok else None)
        except Exception:
            pass


def init_addon():
    """Initialize all Anki hooks and filters."""
    if not ANKI_AVAILABLE or not gui_hooks:
        return

    # 1. Register card filter hook {{sayitvid:...}}
    setup_card_filter()

    # 2. Register Browser menu action
    gui_hooks.browser_menus_did_init.append(setup_browser_menu)

    # 3. Register Editor toolbar button
    gui_hooks.editor_did_init_buttons.append(setup_editor_button)

    # 4. Register Editor webview styling
    if hasattr(gui_hooks, "editor_web_view_did_init"):
        gui_hooks.editor_web_view_did_init.append(on_editor_web_view_init)


# Run initialization on import inside Anki
init_addon()
