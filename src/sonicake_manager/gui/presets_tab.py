"""Preset browser tab."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..i18n import t
from ..validation import is_valid_name
from .common import preset_label


class PresetsTab(QWidget):
    """Browse the 100 slots; select or save presets."""

    select_requested = Signal(int, bool)   # index (0-99), factory
    save_requested = Signal(str, int)      # name, slot 1-50
    refresh_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(lambda _item: self._emit_select())

        self.current_label = QLabel("–")
        self.select_button = QPushButton(t("presets_select"))
        self.select_button.clicked.connect(self._emit_select)

        self.name_edit = QLineEdit()
        self.name_edit.setMaxLength(10)
        self.name_edit.setPlaceholderText(t("presets_name"))

        self.slot_spin = QSpinBox()
        self.slot_spin.setRange(1, 50)
        self.slot_spin.setValue(1)

        self.save_button = QPushButton(t("presets_save_here"))
        self.save_button.clicked.connect(self._emit_save)

        self.refresh_button = QPushButton(t("action_refresh"))
        self.refresh_button.clicked.connect(self.refresh_requested)

        right = QVBoxLayout()
        right.addWidget(QLabel(t("presets_current")))
        right.addWidget(self.current_label)
        right.addWidget(self.select_button)
        right.addStretch(1)
        right.addWidget(QLabel(t("presets_name")))
        right.addWidget(self.name_edit)
        right.addWidget(QLabel(t("presets_slot")))
        right.addWidget(self.slot_spin)
        right.addWidget(self.save_button)
        right.addWidget(self.refresh_button)

        layout = QHBoxLayout(self)
        layout.addWidget(self.list, stretch=2)
        layout.addLayout(right, stretch=1)
        self.setEnabled(False)

    # -- populate --------------------------------------------------------------

    def set_names(self, names: list[str], current_index: int | None = None) -> None:
        self.list.clear()
        for index, name in enumerate(names):
            label = preset_label(index)
            if label is None:
                continue
            suffix = f"  {t('presets_empty')}" if not name else ""
            item = QListWidgetItem(f"{label}  {name}{suffix}")
            item.setData(1, index)  # Qt.UserRole
            self.list.addItem(item)
        if current_index is not None:
            self.set_current(current_index)
        self.setEnabled(True)

    def set_current(self, index: int) -> None:
        label = preset_label(index)
        self.current_label.setText(label or "?")

    # -- emitters ---------------------------------------------------------------

    def _selected_index(self) -> int | None:
        item = self.list.currentItem()
        return None if item is None else int(item.data(1))

    def _emit_select(self) -> None:
        index = self._selected_index()
        if index is None:
            return
        self.select_requested.emit(index, index >= 50)

    def _emit_save(self) -> None:
        name = self.name_edit.text().strip().upper()
        if not is_valid_name(name):
            return
        self.save_requested.emit(name, self.slot_spin.value())
