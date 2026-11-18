"""Read-only tab listing user IR and clone profile slot names."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..i18n import t


class SlotsTab(QWidget):
    refresh_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.ir_list = QListWidget()
        self.clone_list = QListWidget()

        ir_box = QGroupBox(t("slots_ir"))
        ir_layout = QVBoxLayout(ir_box)
        ir_layout.addWidget(self.ir_list)

        clone_box = QGroupBox(t("slots_clone"))
        clone_layout = QVBoxLayout(clone_box)
        clone_layout.addWidget(self.clone_list)

        self.refresh_button = QPushButton(t("action_refresh"))
        self.refresh_button.clicked.connect(self.refresh_requested)

        lists = QHBoxLayout()
        lists.addWidget(ir_box)
        lists.addWidget(clone_box)

        layout = QVBoxLayout(self)
        layout.addLayout(lists, stretch=1)
        layout.addWidget(self.refresh_button)
        layout.addWidget(QLabel(t("slots_note")))
        self.setEnabled(False)

    def load(self, ir_names: list[str], clone_names: list[str]) -> None:
        self.ir_list.clear()
        self.clone_list.clear()
        for index, name in enumerate(ir_names, start=1):
            self.ir_list.addItem(f"IR {index}  {name}")
        for index, name in enumerate(clone_names, start=1):
            self.clone_list.addItem(f"CLONE {index}  {name}")
        self.setEnabled(True)
