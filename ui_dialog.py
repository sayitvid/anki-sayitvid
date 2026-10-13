"""
SayItVid Anki Add-on - Batch Widget Enrichment GUI Dialog
PyQt dialog for configuring and embedding SayItVid widgets into selected notes.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

try:
    from PyQt6.QtCore import Qt, pyqtSignal, QObject
    from PyQt6.QtWidgets import (
        QCheckBox,
        QComboBox,
        QDialog,
        QFormLayout,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QProgressBar,
        QPushButton,
        QVBoxLayout,
    )
    from aqt import mw
    from aqt.utils import showInfo, showWarning
    QT_AVAILABLE = True
except ImportError:
    try:
        from PyQt5.QtCore import Qt, pyqtSignal, QObject
        from PyQt5.QtWidgets import (
            QCheckBox,
            QComboBox,
            QDialog,
            QFormLayout,
            QGroupBox,
            QHBoxLayout,
            QLabel,
            QProgressBar,
            QPushButton,
            QVBoxLayout,
        )
        from aqt import mw
        from aqt.utils import showInfo, showWarning
        QT_AVAILABLE = True
    except ImportError:
        QT_AVAILABLE = False
        QDialog = object

from .enricher import NoteEnricher

logger = logging.getLogger("sayitvid_anki")


if not QT_AVAILABLE:
    class BatchEnrichDialog:
        def __init__(self, *args, **kwargs):
            pass
        def exec(self):
            pass
else:
    class BatchEnrichDialog(QDialog):
        def __init__(self, browser: Any, note_ids: List[int], config: Dict[str, Any], parent=None):
            super().__init__(parent or browser)
            self.browser = browser
            self.note_ids = note_ids
            self.config = config

            self.setWindowTitle(f"SayItVid — Embed Widgets ({len(note_ids)} selected)")
            self.resize(460, 420)
            self.setup_ui()

        def setup_ui(self):
            layout = QVBoxLayout(self)
            layout.setSpacing(12)

            # Header Banner
            header_label = QLabel(
                "<h3>SayItVid Video Widget Embedder</h3>"
                "<p style='color: #64748b; font-size: 11px; margin-top: -6px;'>"
                "Embed responsive, authentic video clips and native pronunciations into your cards."
                "</p>"
            )
            rich_format = getattr(Qt.TextFormat, "RichText", None) if hasattr(Qt, "TextFormat") else getattr(Qt, "RichText", None)
            if rich_format is not None:
                header_label.setTextFormat(rich_format)
            layout.addWidget(header_label)

            available_fields = self.get_available_fields()

            # Group: Field Mapping
            mapping_group = QGroupBox("Field Mapping")
            form_layout = QFormLayout(mapping_group)

            self.combo_source = self.create_field_combo(available_fields, self.config.get("field_mappings", {}).get("source_word", "Front"))
            self.combo_video = self.create_field_combo(available_fields, self.config.get("field_mappings", {}).get("target_video", "Video"))

            form_layout.addRow("Source Word Field:", self.combo_source)
            form_layout.addRow("Target Video Field:", self.combo_video)
            layout.addWidget(mapping_group)

            # Group: Options
            options_group = QGroupBox("Widget Options")
            options_layout = QFormLayout(options_group)

            self.combo_accent = QComboBox()
            self.combo_accent.addItems(["US (American)", "UK (British)", "AUS (Australian)", "CA (Canadian)"])
            default_accent = self.config.get("default_accent", "us").lower()
            idx = 0
            if "uk" in default_accent:
                idx = 1
            elif "aus" in default_accent:
                idx = 2
            elif "ca" in default_accent:
                idx = 3
            self.combo_accent.setCurrentIndex(idx)
            options_layout.addRow("Accent / Dialect:", self.combo_accent)

            self.combo_theme = QComboBox()
            self.combo_theme.addItems(["Auto (Match System/Anki)", "Dark", "Light"])
            options_layout.addRow("Widget Theme:", self.combo_theme)

            self.chk_overwrite = QCheckBox("Overwrite existing field content")
            self.chk_overwrite.setChecked(self.config.get("overwrite_existing", False))
            options_layout.addRow("", self.chk_overwrite)

            layout.addWidget(options_group)

            # Progress Bar
            self.progress_bar = QProgressBar()
            self.progress_bar.setRange(0, len(self.note_ids))
            self.progress_bar.setValue(0)
            self.progress_bar.setVisible(False)
            layout.addWidget(self.progress_bar)

            # Buttons
            btn_layout = QHBoxLayout()
            self.btn_cancel = QPushButton("Close")
            self.btn_cancel.clicked.connect(self.reject)
            btn_layout.addWidget(self.btn_cancel)

            self.btn_start = QPushButton(f"Embed Widgets ({len(self.note_ids)} Notes)")
            self.btn_start.setStyleSheet("font-weight: bold; background-color: #e11d48; color: white; padding: 6px 12px; border-radius: 4px;")
            self.btn_start.clicked.connect(self.start_enrichment)
            btn_layout.addWidget(self.btn_start)

            layout.addLayout(btn_layout)

        def get_available_fields(self) -> List[str]:
            fields = set()
            if mw and mw.col:
                for nid in self.note_ids[:20]:
                    try:
                        note = mw.col.get_note(nid)
                        fields.update(note.keys())
                    except Exception:
                        pass
            field_list = sorted(list(fields))
            if not field_list:
                field_list = ["Front", "Back", "Video", "SayItVid"]
            return field_list

        def create_field_combo(self, fields: List[str], default_val: str) -> QComboBox:
            combo = QComboBox()
            combo.addItems(fields)
            idx = combo.findText(default_val, Qt.MatchFlag.MatchFixedString if hasattr(Qt, "MatchFlag") else Qt.MatchFixedString)
            if idx >= 0:
                combo.setCurrentIndex(idx)
            return combo

        def start_enrichment(self):
            if not mw or not mw.col:
                return

            self.btn_start.setEnabled(False)
            self.progress_bar.setVisible(True)

            accent_map = {0: "us", 1: "uk", 2: "aus", 3: "ca"}
            theme_map = {0: "auto", 1: "dark", 2: "light"}

            accent = accent_map.get(self.combo_accent.currentIndex(), "us")
            theme = theme_map.get(self.combo_theme.currentIndex(), "auto")
            source_field = self.combo_source.currentText()
            target_field = self.combo_video.currentText()
            overwrite = self.chk_overwrite.isChecked()

            enricher = NoteEnricher(config=self.config)

            updated_count = 0
            skipped_count = 0

            for i, nid in enumerate(self.note_ids):
                try:
                    note = mw.col.get_note(nid)
                    res = enricher.enrich_single_note(
                        note=note,
                        source_field=source_field,
                        target_mappings={"target_video": target_field},
                        accent=accent,
                        theme=theme,
                        overwrite=overwrite,
                    )
                    if res["success"]:
                        if res.get("updated_fields"):
                            mw.col.update_note(note)
                            updated_count += 1
                        else:
                            skipped_count += 1
                except Exception as err:
                    logger.error(f"Error enriching note {nid}: {err}")

                self.progress_bar.setValue(i + 1)

            showInfo(
                f"SayItVid Widget Enrichment Complete!\n\n"
                f"• Embedded in {updated_count} note(s)\n"
                f"• Skipped {skipped_count} note(s) (already had content)\n\n"
                f"Tip: You can also use {{{{sayitvid:{source_field}}}}} directly in your card template without modifying notes!",
                parent=self
            )
            self.accept()
