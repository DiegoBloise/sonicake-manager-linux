"""About tab."""

from __future__ import annotations

from PySide6.QtCore import QSettings, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from .. import __version__
from ..i18n import current_language, t


class AboutTab(QWidget):
    language_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.text = QLabel(
            t("about_text", version=__version__, language=current_language().upper())
        )
        self.text.setWordWrap(True)

        self.language = QComboBox()
        self.language.addItem(t("lang_en"), "en")
        self.language.addItem(t("lang_pt"), "pt")
        index = self.language.findData(current_language())
        if index >= 0:
            self.language.setCurrentIndex(index)
        self.language.currentIndexChanged.connect(self._on_language)

        form = QFormLayout()
        form.addRow(t("about_language"), self.language)

        layout = QVBoxLayout(self)
        layout.addWidget(self.text)
        layout.addLayout(form)
        layout.addStretch(1)

    def _on_language(self, _index: int) -> None:
        code = str(self.language.currentData())
        settings = QSettings("sonicake-manager", "sonicake-manager")
        settings.setValue("language", code)
        self.language_changed.emit(code)
