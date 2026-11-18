"""Current-preset editor tab."""

from __future__ import annotations

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
    QDoubleSpinBox,
)

from ..i18n import t
from .common import MODULE_ORDER, effect_catalog, effect_params


class ParameterRow(QWidget):
    """Label + slider + spinbox for one algId; syncs both ways."""

    value_changed = Signal(object)  # emitted on explicit user edits

    def __init__(self, descriptor: dict, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.descriptor = descriptor
        self.name = descriptor.get("name", "?")
        self.alg_id = int(descriptor.get("algId", 0))
        self.minimum = float(descriptor.get("min", 0))
        self.maximum = float(descriptor.get("max", 100))
        self.step = float(descriptor.get("step", 1))
        self._scale = 10 if self.step < 1 else 1

        self.label = QLabel(self.name)
        self.label.setMinimumWidth(72)

        slider_max = int(self.maximum * self._scale)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(int(self.minimum * self._scale), slider_max)
        self.slider.sliderReleased.connect(self._on_slider_released)

        if self._scale == 1:
            self.spin: QSpinBox | QDoubleSpinBox = QSpinBox()
            self.spin.setRange(int(self.minimum), int(self.maximum))
        else:
            self.spin = QDoubleSpinBox()
            self.spin.setRange(self.minimum, self.maximum)
            self.spin.setSingleStep(self.step)
            self.spin.setDecimals(1)
        self.spin.editingFinished.connect(self._on_spin_edited)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label)
        layout.addWidget(self.slider, stretch=1)
        layout.addWidget(self.spin)

    # -- programmatic set (signals blocked) ----------------------------------

    def set_value(self, value) -> None:
        for widget in (self.slider, self.spin):
            widget.blockSignals(True)
        try:
            self.slider.setValue(int(round(float(value) * self._scale)))
            self.spin.setValue(float(value) if self._scale > 1 else int(round(float(value))))
        finally:
            for widget in (self.slider, self.spin):
                widget.blockSignals(False)

    def _current_value(self) -> float | int:
        value = float(self.spin.value())
        if self._scale == 1:
            return int(round(value))
        return round(value, 1)

    def _on_slider_released(self) -> None:
        value = self.slider.value() / self._scale
        self.spin.blockSignals(True)
        self.spin.setValue(int(round(value)) if self._scale == 1 else value)
        self.spin.blockSignals(False)
        self.value_changed.emit(self._current_value())

    def _on_spin_edited(self) -> None:
        value = self._current_value()
        self.slider.blockSignals(True)
        self.slider.setValue(int(round(value * self._scale)))
        self.slider.blockSignals(False)
        self.value_changed.emit(value)


class ModulePanel(QGroupBox):
    """Group box with on/off, effect selection and its parameter rows."""

    toggled_module = Signal(str, bool)
    effect_changed = Signal(str, int)
    parameter_changed = Signal(str, int, object)

    def __init__(self, module_name: str, parent: QWidget | None = None) -> None:
        super().__init__(module_name, parent)
        self.module_name = module_name

        self.enable = QCheckBox(t("editor_module_on"))
        self.enable.toggled.connect(lambda on: self.toggled_module.emit(self.module_name, on))

        self.effect = QComboBox()
        options = effect_catalog(module_name)
        for effect_id, name in options:
            self.effect.addItem(name, effect_id)
        if not options:
            self.effect.addItem("Gate", 1)
            self.effect.setEnabled(False)  # NR: fixed effect
        self.effect.currentIndexChanged.connect(self._on_effect_index)

        head = QHBoxLayout()
        head.addWidget(self.enable)
        head.addWidget(self.effect, stretch=1)

        self.params_box = QVBoxLayout()
        self.params_box.setSpacing(2)

        layout = QVBoxLayout(self)
        layout.addLayout(head)
        layout.addLayout(self.params_box)
        self._param_rows: list[ParameterRow] = []

    def set_state(self, enabled: bool, effect_name: str | None, parameters: dict[str, object]) -> None:
        for widget in (self.enable, self.effect):
            widget.blockSignals(True)
        try:
            self.enable.setChecked(bool(enabled))
            if effect_name is not None:
                index = self.effect.findText(effect_name)
                if index >= 0:
                    self.effect.setCurrentIndex(index)
        finally:
            for widget in (self.enable, self.effect):
                widget.blockSignals(False)
        self._rebuild_params(self._selected_effect_id(), parameters)

    def _selected_effect_id(self) -> int:
        return int(self.effect.currentData())

    def _rebuild_params(self, effect_id: int, parameters: dict[str, object]) -> None:
        for row in self._param_rows:
            row.setParent(None)
        self._param_rows = []
        while self.params_box.count():
            item = self.params_box.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        for descriptor in effect_params(effect_id):
            row = ParameterRow(descriptor)
            name = descriptor.get("name", "")
            if name in parameters:
                row.set_value(parameters[name])
            row.value_changed.connect(
                lambda value, module=self.module_name, alg=row.alg_id: self.parameter_changed.emit(module, alg, value)
            )
            self.params_box.addWidget(row)
            self._param_rows.append(row)

    def _on_effect_index(self, _index: int) -> None:
        self.effect_changed.emit(self.module_name, self._selected_effect_id())


class EditorTab(QWidget):
    """The current-preset editor."""

    module_toggled = Signal(str, bool)
    effect_changed = Signal(str, int)
    parameter_changed = Signal(str, int, object)
    volume_changed = Signal(int)
    bpm_changed = Signal(int)
    amp_mode_changed = Signal(bool)  # clone?
    save_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.slot_label = QLabel("–")

        self.amp_mode = QComboBox()
        self.amp_mode.addItem(t("editor_amp_normal"), False)
        self.amp_mode.addItem(t("editor_amp_clone"), True)
        self.amp_mode.currentIndexChanged.connect(
            lambda _: self.amp_mode_changed.emit(bool(self.amp_mode.currentData()))
        )

        self.volume = QSlider(Qt.Horizontal)
        self.volume.setRange(0, 100)
        self.volume.setValue(75)
        self.volume.setMinimumWidth(120)
        self.volume.sliderReleased.connect(lambda: self.volume_changed.emit(self.volume.value()))
        self.volume_label = QLabel("75")
        self.volume.valueChanged.connect(lambda v: self.volume_label.setText(str(v)))

        self.bpm = QSpinBox()
        self.bpm.setRange(40, 300)
        self.bpm.setValue(120)
        self.bpm.editingFinished.connect(lambda: self.bpm_changed.emit(self.bpm.value()))

        self.save_button = QPushButton(t("editor_save_buffer"))
        self.save_button.clicked.connect(self.save_requested)

        header = QHBoxLayout()
        header.addWidget(QLabel(t("editor_preset_slot")))
        header.addWidget(self.slot_label)
        header.addWidget(QLabel(t("editor_amp_mode")))
        header.addWidget(self.amp_mode)
        header.addWidget(QLabel(t("editor_volume")))
        header.addWidget(self.volume)
        header.addWidget(self.volume_label)
        header.addWidget(QLabel(t("editor_bpm")))
        header.addWidget(self.bpm)
        header.addWidget(self.save_button)

        self.chain_label = QLabel()

        self.module_panels: dict[str, ModulePanel] = {}
        grid_host = QWidget()
        from PySide6.QtWidgets import QGridLayout

        grid = QGridLayout(grid_host)
        grid.setSpacing(8)
        for index, name in enumerate(MODULE_ORDER):
            panel = ModulePanel(name)
            panel.toggled_module.connect(self.module_toggled)
            panel.effect_changed.connect(self.effect_changed)
            panel.parameter_changed.connect(self.parameter_changed)
            self.module_panels[name] = panel
            grid.addWidget(panel, index // 3, index % 3)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(grid_host)

        layout = QVBoxLayout(self)
        layout.addLayout(header)
        layout.addWidget(QLabel(t("editor_bpm_note")))
        layout.addWidget(self.chain_label)
        layout.addWidget(scroll, stretch=1)
        self.setEnabled(False)

    # -- populate / clear -----------------------------------------------------

    def load_state(self, state: dict, slot_label: str | None) -> None:
        self.slot_label.setText(slot_label or "?")
        self.chain_label.setText(t("editor_chain") + ": " + " › ".join(state.get("signalChain", [])))
        for widget in (self.amp_mode, self.volume, self.bpm):
            widget.blockSignals(True)
        try:
            self.amp_mode.setCurrentIndex(1 if state.get("cloneMode") else 0)
            if state.get("presetVolume") is not None:
                self.volume.setValue(int(state["presetVolume"]))
            if state.get("presetBpm") is not None:
                self.bpm.setValue(int(state["presetBpm"]))
        finally:
            for widget in (self.amp_mode, self.volume, self.bpm):
                widget.blockSignals(False)
        states = state.get("moduleStates", {})
        effects = state.get("selectedEffects", {})
        params = state.get("parameters", {})
        for name, panel in self.module_panels.items():
            panel.set_state(states.get(name, True), effects.get(name), params.get(name, {}))
        self.setEnabled(True)
