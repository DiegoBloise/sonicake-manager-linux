"""Global-settings tab."""

from __future__ import annotations

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..i18n import t


class GlobalsTab(QWidget):
    """Edit global settings; read-only raw values for the rest."""

    apply_requested = Signal(dict)
    refresh_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.global_volume = QSlider(Qt.Horizontal)
        self.global_volume.setRange(0, 100)
        self.global_volume_label = QLabel("100")
        self.global_volume.valueChanged.connect(lambda v: self.global_volume_label.setText(str(v)))

        def db_spin() -> QSpinBox:
            spin = QSpinBox()
            spin.setRange(-20, 20)
            return spin

        self.input_level = db_spin()
        self.fx_rec_level = db_spin()
        self.bt_rec_level = db_spin()
        self.monitor_level = db_spin()

        volume_row = QHBoxLayout()
        volume_row.addWidget(self.global_volume, stretch=1)
        volume_row.addWidget(self.global_volume_label)

        form = QFormLayout()
        form.addRow(t("globals_global_volume"), volume_row)
        form.addRow(t("globals_input_level"), self.input_level)
        form.addRow(t("globals_fx_rec"), self.fx_rec_level)
        form.addRow(t("globals_bt_rec"), self.bt_rec_level)
        form.addRow(t("globals_monitor"), self.monitor_level)

        self.read_only = QLabel("–")

        self.apply_button = QPushButton(t("globals_apply"))
        self.apply_button.clicked.connect(self._emit_apply)
        self.refresh_button = QPushButton(t("action_refresh"))
        self.refresh_button.clicked.connect(self.refresh_requested)

        buttons = QHBoxLayout()
        buttons.addWidget(self.apply_button)
        buttons.addWidget(self.refresh_button)
        buttons.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(t("globals_title")))
        layout.addLayout(form)
        layout.addWidget(self.read_only)
        layout.addLayout(buttons)
        layout.addStretch(1)
        self.setEnabled(False)
        self._loaded: dict[str, object] = {}

    # -- populate --------------------------------------------------------------

    def load_globals(self, data: dict[str, object]) -> None:
        def as_int(key, default=0):
            try:
                return int(data[key])
            except (KeyError, TypeError, ValueError):
                return default

        self._loaded = dict(data)
        widgets = (
            self.global_volume,
            self.input_level,
            self.fx_rec_level,
            self.bt_rec_level,
            self.monitor_level,
        )
        for widget in widgets:
            widget.blockSignals(True)
        self.global_volume.setValue(as_int("globalVolume", 100))
        self.input_level.setValue(as_int("inputLevel", 0))
        self.fx_rec_level.setValue(as_int("fxRecLevel", 0))
        self.bt_rec_level.setValue(as_int("btRecLevel", 0))
        self.monitor_level.setValue(as_int("monitorLevel", 0))
        for widget in widgets:
            widget.blockSignals(False)
        raw = ", ".join(
            f"{k}={v}" for k, v in sorted(data.items())
            if k in ("backlight", "mode", "reamp", "eco", "expFsType")
        )
        self.read_only.setText(f"{t('globals_read_only')} {raw or '–'}")
        self.setEnabled(True)

    # -- apply: only send what changed ----------------------------------------

    def _emit_apply(self) -> None:
        changes: dict[str, int] = {}
        current = {
            "globalVolume": self.global_volume.value(),
            "inputLevel": self.input_level.value(),
            "fxRecLevel": self.fx_rec_level.value(),
            "btRecLevel": self.bt_rec_level.value(),
            "monitorLevel": self.monitor_level.value(),
        }
        for key, value in current.items():
            try:
                original = int(self._loaded.get(key, value))
            except (TypeError, ValueError):
                original = value
            if original != value:
                changes[key] = value
        self.apply_requested.emit(changes)
