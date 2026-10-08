"""
SayItVid Anki Add-on - Batch Enrichment GUI Dialog
PyQt6 dialog for mapping fields and processing selected notes with a progress bar.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Dict, List, Optional

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


if QT_AVAILABLE:
    class WorkerSignals(QObject):
        progress = pyqtSignal(int, int, str)
        finished = pyqtSignal(int, int, int)
        error = pyqtSignal(str)


    class BatchEnrichDialog(QDialog):
        def __init__(self, browser: Any, note_ids: List[int], config: Dict[str, Any], parent=None):
            super().__init__(parent or browser)
            self.browser = browser
            self.note_ids = note_ids
            self.config = config
            self.is_running = False
            self.should_cancel = False

            self.setWindowTitle(f"SayItVid — Enrich Notes ({len(note_ids)} selected)")
            self.resize(520, 560)
            self.setup_ui()

        def setup_ui(self):
            layout = QVBoxLayout(self)
            layout.setSpacing(12)

            # Header Banner
            header_label = QLabel(
                "<h3>SayItVid Flashcard Enricher</h3>"
                "<p style='color: #64748b; font-size: 11px; margin-top: -6px;'>"
                "Fetch authentic native audio, IPA, stressed syllables, CEFR levels, and contextual video clips."
                "</p>"
            )
            rich_format = getattr(Qt.TextFormat, "RichText", None) if hasattr(Qt, "TextFormat") else getattr(Qt, "RichText", None)
            if rich_format is not None:
                header_label.setTextFormat(rich_format)
            layout.addWidget(header_label)

            # Detect available fields across selected notes
            available_fields = self.get_available_fields()

            # Group: Field Mapping
            mapping_group = QGroupBox("Field Mapping")
            form_layout = QFormLayout(mapping_group)

            self.combo_source = self.create_field_combo(available_fields, self.config.get("field_mappings", {}).get("source_word", "Front"))
            self.combo_audio = self.create_field_combo(["(None)"] + available_fields, self.config.get("field_mappings", {}).get("target_audio", "Audio"))
            self.combo_ipa = self.create_field_combo(["(None)"] + available_fields, self.config.get("field_mappings", {}).get("target_ipa", "IPA"))
            self.combo_syllables = self.create_field_combo(["(None)"] + available_fields, self.config.get("field_mappings", {}).get("target_syllables", "Syllables"))
            self.combo_definition = self.create_field_combo(["(None)"] + available_fields, self.config.get("field_mappings", {}).get("target_definition", "Definition"))
            self.combo_sentence = self.create_field_combo(["(None)"] + available_fields, self.config.get("field_mappings", {}).get("target_sentence", "Sentence"))
            self.combo_video = self.create_field_combo(["(None)"] + available_fields, self.config.get("field_mappings", {}).get("target_video", "Video"))
            self.combo_cefr = self.create_field_combo(["(None)"] + available_fields, self.config.get("field_mappings", {}).get("target_cefr", "CEFR"))

            form_layout.addRow("Source Word Field *:", self.combo_source)
            form_layout.addRow("Target Audio [sound:...]:", self.combo_audio)
            form_layout.addRow("Target IPA Phonetics:", self.combo_ipa)
            form_layout.addRow("Target Syllables & Stress:", self.combo_syllables)
            form_layout.addRow("Target Definition:", self.combo_definition)
            form_layout.addRow("Target Subtitle Sentence:", self.combo_sentence)
            form_layout.addRow("Target Video Embed:", self.combo_video)
            form_layout.addRow("Target CEFR Level:", self.combo_cefr)

            layout.addWidget(mapping_group)

            # Group: Options
            options_group = QGroupBox("Preferences")
            options_layout = QVBoxLayout(options_group)

            accent_row = QHBoxLayout()
            accent_row.addWidget(QLabel("Accent / Dialect:"))
            self.combo_accent = QComboBox()
            self.combo_accent.addItems(["US (American)", "UK (British)", "AUS (Australian)"])
            default_acc = self.config.get("default_accent", "us").lower()
            if default_acc == "uk":
                self.combo_accent.setCurrentIndex(1)
            elif default_acc == "aus":
                self.combo_accent.setCurrentIndex(2)
            else:
                self.combo_accent.setCurrentIndex(0)
            accent_row.addWidget(self.combo_accent)
            options_layout.addLayout(accent_row)

            self.chk_download_audio = QCheckBox("Download offline native MP3 audio into collection.media")
            self.chk_download_audio.setChecked(self.config.get("download_audio", True))
            options_layout.addWidget(self.chk_download_audio)

            self.chk_tag_cefr = QCheckBox("Add CEFR difficulty tags to notes (e.g. CEFR:B1)")
            self.chk_tag_cefr.setChecked(self.config.get("tag_cefr", True))
            options_layout.addWidget(self.chk_tag_cefr)

            self.chk_overwrite = QCheckBox("Overwrite existing field contents")
            self.chk_overwrite.setChecked(self.config.get("overwrite_existing", False))
            options_layout.addWidget(self.chk_overwrite)

            layout.addWidget(options_group)

            # Progress Bar & Status
            self.progress_bar = QProgressBar()
            self.progress_bar.setRange(0, len(self.note_ids))
            self.progress_bar.setValue(0)
            layout.addWidget(self.progress_bar)

            self.lbl_status = QLabel("Ready to enrich notes.")
            self.lbl_status.setStyleSheet("color: #64748b; font-size: 11px;")
            layout.addWidget(self.lbl_status)

            # Button Box
            btn_layout = QHBoxLayout()
            self.btn_cancel = QPushButton("Cancel")
            self.btn_cancel.clicked.connect(self.on_cancel)
            self.btn_start = QPushButton("Start Enrichment")
            self.btn_start.setDefault(True)
            self.btn_start.clicked.connect(self.on_start)

            btn_layout.addStretch()
            btn_layout.addWidget(self.btn_cancel)
            btn_layout.addWidget(self.btn_start)
            layout.addLayout(btn_layout)

        def get_available_fields(self) -> List[str]:
            """Retrieve union of field names from selected notes."""
            fields_set = set()
            if not mw or not mw.col:
                return ["Front", "Back", "Audio", "IPA", "Syllables", "Definition", "Sentence", "Video", "CEFR"]

            for nid in self.note_ids[:20]:
                note = mw.col.get_note(nid)
                if note:
                    fields_set.update(note.keys())

            fields_list = sorted(list(fields_set))
            return fields_list if fields_list else ["Front", "Back", "Audio", "IPA"]

        def create_field_combo(self, fields: List[str], default_name: str) -> QComboBox:
            combo = QComboBox()
            combo.addItems(fields)
            idx = combo.findText(default_name)
            if idx >= 0:
                combo.setCurrentIndex(idx)
            return combo

        def on_start(self):
            if self.is_running:
                return

            self.is_running = True
            self.should_cancel = False
            self.btn_start.setEnabled(False)
            self.btn_cancel.setText("Stop")

            source_field = self.combo_source.currentText()
            target_mappings = {
                "target_audio": self.combo_audio.currentText() if self.combo_audio.currentText() != "(None)" else "",
                "target_ipa": self.combo_ipa.currentText() if self.combo_ipa.currentText() != "(None)" else "",
                "target_syllables": self.combo_syllables.currentText() if self.combo_syllables.currentText() != "(None)" else "",
                "target_definition": self.combo_definition.currentText() if self.combo_definition.currentText() != "(None)" else "",
                "target_sentence": self.combo_sentence.currentText() if self.combo_sentence.currentText() != "(None)" else "",
                "target_video": self.combo_video.currentText() if self.combo_video.currentText() != "(None)" else "",
                "target_cefr": self.combo_cefr.currentText() if self.combo_cefr.currentText() != "(None)" else "",
            }

            accent_idx = self.combo_accent.currentIndex()
            accents = ["us", "uk", "aus"]
            accent = accents[accent_idx]

            overwrite = self.chk_overwrite.isChecked()
            download_audio = self.chk_download_audio.isChecked()
            tag_cefr = self.chk_tag_cefr.isChecked()

            self.signals = WorkerSignals()
            self.signals.progress.connect(self.on_worker_progress)
            self.signals.finished.connect(self.on_worker_finished)
            self.signals.error.connect(self.on_worker_error)

            def media_writer_wrapper(filename: str, data: bytes) -> str:
                if mw and mw.col and mw.col.media:
                    return mw.col.media.write_data(filename, data)
                return filename

            enricher = NoteEnricher(
                config=self.config,
                media_writer=media_writer_wrapper,
            )

            # Start worker thread
            thread = threading.Thread(
                target=self.run_batch_worker,
                args=(enricher, source_field, target_mappings, accent, overwrite, download_audio, tag_cefr),
                daemon=True,
            )
            thread.start()

        def run_batch_worker(self, enricher: NoteEnricher, source_field: str, mappings: Dict[str, str], accent: str, overwrite: bool, download_audio: bool, tag_cefr: bool):
            success_count = 0
            audio_count = 0
            total = len(self.note_ids)

            for i, nid in enumerate(self.note_ids):
                if self.should_cancel:
                    break

                try:
                    note = mw.col.get_note(nid) if mw and mw.col else None
                    if note:
                        res = enricher.enrich_single_note(
                            note=note,
                            source_field=source_field,
                            target_mappings=mappings,
                            accent=accent,
                            overwrite=overwrite,
                            download_audio=download_audio,
                            tag_cefr=tag_cefr,
                        )
                        if res["success"]:
                            success_count += 1
                            if res.get("audio_saved"):
                                audio_count += 1
                            if mw and mw.col:
                                mw.col.update_note(note)

                        self.signals.progress.emit(i + 1, total, res.get("word", ""))
                except Exception as ex:
                    logger.error("Error processing note %d: %s", nid, ex)

            self.signals.finished.emit(success_count, audio_count, total)

        def on_worker_progress(self, current: int, total: int, word: str):
            self.progress_bar.setValue(current)
            self.lbl_status.setText(f"Enriching ({current}/{total}): <b>{word}</b>")

        def on_worker_finished(self, success: int, audio: int, total: int):
            self.is_running = False
            self.btn_start.setEnabled(True)
            self.btn_cancel.setText("Close")
            self.lbl_status.setText(f"Completed: {success}/{total} notes enriched ({audio} audio files downloaded).")

            if mw and mw.col:
                mw.reset()

            showInfo(
                f"SayItVid Enrichment Complete!\n\n"
                f"• Notes enriched: {success} / {total}\n"
                f"• Audio recordings saved: {audio}\n",
                parent=self,
            )

        def on_worker_error(self, err: str):
            self.lbl_status.setText(f"Error: {err}")
            showWarning(err, parent=self)

        def on_cancel(self):
            if self.is_running:
                self.should_cancel = True
                self.lbl_status.setText("Stopping worker...")
            else:
                self.accept()
else:
    class BatchEnrichDialog:
        """Fallback stub for headless environments or unit tests without Qt."""
        def __init__(self, browser: Any = None, note_ids: List[int] = None, config: Dict[str, Any] = None, parent: Any = None):
            self.browser = browser
            self.note_ids = note_ids or []
            self.config = config or {}

        def exec(self):
            pass

