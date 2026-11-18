"""Main window and application entry point."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QSettings, QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QComboBox, QFileDialog, QLabel, QMainWindow, QMessageBox, QStatusBar, QTabWidget, QToolBar

from .. import __version__
from ..device import SonicakeDevice, DeviceError
from ..i18n import set_language, t
from ..preset_file import build_export, dumps_export, preset_index_from_raw
from ..transport import AlsaSequencerTransport, TransportError, find_devices, list_devices
from .about_tab import AboutTab
from .common import preset_label
from .editor_tab import EditorTab
from .globals_tab import GlobalsTab
from .presets_tab import PresetsTab
from .slots_tab import SlotsTab


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(t("app_title"))
        self.setMinimumSize(980, 640)

        self.dev: SonicakeDevice | None = None
        self.current_index: int | None = None

        # -- toolbar -----------------------------------------------------------
        toolbar = QToolBar("main")
        toolbar.setMovable(False)
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(260)
        self._refresh_ports()
        self.refresh_ports_action = QAction(t("action_refresh"), self)
        self.refresh_ports_action.triggered.connect(self._on_refresh_ports)
        self.connect_action = QAction(t("action_connect"), self)
        self.connect_action.triggered.connect(self._on_toggle_connect)
        self.export_action = QAction(t("action_export"), self)
        self.export_action.setEnabled(False)
        self.export_action.triggered.connect(self._on_export_preset)
        toolbar.addWidget(self.port_combo)
        toolbar.addAction(self.refresh_ports_action)
        toolbar.addAction(self.connect_action)
        toolbar.addAction(self.export_action)
        self.addToolBar(toolbar)

        quit_action = QAction("Quit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        self.addAction(quit_action)

        # -- tabs ---------------------------------------------------------------
        self.tabs = QTabWidget()
        self.editor = EditorTab()
        self.presets = PresetsTab()
        self.slots = SlotsTab()
        self.globals_tab = GlobalsTab()
        self.about = AboutTab()

        self.tabs.addTab(self.editor, t("tab_editor"))
        self.tabs.addTab(self.presets, t("tab_presets"))
        self.tabs.addTab(self.slots, t("tab_slots"))
        self.tabs.addTab(self.globals_tab, t("tab_globals"))
        self.tabs.addTab(self.about, t("tab_about"))
        self.setCentralWidget(self.tabs)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.unsaved_label = QLabel("")
        self.status.addPermanentWidget(self.unsaved_label)
        self._set_status(t("status_disconnected"))

        # -- wiring --------------------------------------------------------------
        self.editor.module_toggled.connect(self._on_module_toggled)
        self.editor.effect_changed.connect(self._on_effect_changed)
        self.editor.parameter_changed.connect(self._on_parameter_changed)
        self.editor.volume_changed.connect(self._on_volume_changed)
        self.editor.bpm_changed.connect(self._on_bpm_changed)
        self.editor.amp_mode_changed.connect(self._on_amp_mode_changed)
        self.editor.save_requested.connect(self._on_save_from_editor)

        self.presets.select_requested.connect(self._on_select_preset)
        self.presets.save_requested.connect(self._on_save_preset)
        self.presets.refresh_requested.connect(self._on_refresh_names)
        self.slots.refresh_requested.connect(self._on_refresh_slots)

        self.globals_tab.apply_requested.connect(self._on_globals_apply)
        self.globals_tab.refresh_requested.connect(self._on_refresh_globals)

        self.about.language_changed.connect(lambda _code: self._set_status(t("app_title")))

    # -- plumbing ---------------------------------------------------------------

    def _set_status(self, text: str) -> None:
        self.status.showMessage(text)

    def _set_unsaved(self, unsaved: bool) -> None:
        self.unsaved_label.setText(t("status_unsaved") if unsaved else "")

    def _sync_unsaved(self) -> None:
        if self.dev is None:
            return
        try:
            self._set_unsaved(self.dev.preset_modified())
        except DeviceError:
            pass

    def _busy(self, text: str):
        from .common import busy_cursor

        self._set_status(text)
        QApplication.processEvents()
        return busy_cursor()

    def _refresh_ports(self) -> None:
        current = self.port_combo.currentData() if self.port_combo.count() else None
        self.port_combo.clear()
        for port in list_devices():
            self.port_combo.addItem(f"{port.client}:{port.port}  {port.name}", port)
        matches = find_devices()
        preferred = matches[0] if matches else None
        index = -1
        for i in range(self.port_combo.count()):
            item = self.port_combo.itemData(i)
            if current is not None and (item.client, item.port) == (current.client, current.port):
                index = i
            elif preferred is not None and (item.client, item.port) == (preferred.client, preferred.port):
                index = index if index >= 0 else i
        if index >= 0:
            self.port_combo.setCurrentIndex(index)

    def _on_refresh_ports(self) -> None:
        self._refresh_ports()
        self._set_status(t("action_refresh"))

    def _selected_port(self):
        return self.port_combo.currentData()

    def _require_device(self) -> SonicakeDevice | None:
        if self.dev is None:
            QMessageBox.warning(self, t("app_title"), t("err_no_device"))
        return self.dev

    def _ack(self, status: str) -> None:
        self._set_status(t("ack_generic", status=status))

    # -- connect / disconnect ----------------------------------------------------

    def _on_toggle_connect(self) -> None:
        if self.dev is not None:
            self._disconnect()
            return
        self._set_status(t("status_connecting"))
        try:
            with self._busy(t("status_connecting")):
                self.dev = SonicakeDevice(AlsaSequencerTransport(self._selected_port()))
                self._reload_all()
        except (TransportError, DeviceError, ValueError) as exc:
            self.dev = None
            self._set_status(t("status_error", message=str(exc)))
            QMessageBox.critical(self, t("app_title"), t("err_device", message=str(exc)))
            return
        self.connect_action.setText(t("action_disconnect"))
        self.export_action.setEnabled(True)
        self.editor.setEnabled(True)
        self.presets.setEnabled(True)
        self.slots.setEnabled(True)
        self.globals_tab.setEnabled(True)

    def _disconnect(self) -> None:
        try:
            if self.dev is not None:
                self.dev.close()
        finally:
            self.dev = None
            self.export_action.setEnabled(False)
            self.editor.setEnabled(False)
            self.presets.setEnabled(False)
            self.slots.setEnabled(False)
            self.globals_tab.setEnabled(False)
            self.connect_action.setText(t("action_connect"))
            self._set_unsaved(False)
            self._set_status(t("status_disconnected"))

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt API)
        self._disconnect()
        super().closeEvent(event)

    # -- reads -------------------------------------------------------------------

    def _reload_all(self) -> None:
        assert self.dev is not None
        state = self.dev.state()
        raw = self.dev.preset_number_raw()
        index = None
        if len(raw) >= 2:
            index = raw[0] | (raw[1] << 8)
            self.current_index = index
        self.editor.load_state(state, preset_label(index) if index is not None else None)
        names = self.dev.preset_names()
        self.presets.set_names(names, index)
        self.slots.load(self.dev.ir_name_list(), self.dev.clone_name_list())
        glob = self.dev.globals()
        self.globals_tab.load_globals(glob)
        self._sync_unsaved()
        self._set_status(t("status_connected", name=self.port_combo.currentText()))

    def _on_refresh_names(self) -> None:
        dev = self._require_device()
        if dev is None:
            return
        with self._busy(t("status_reading")):
            names = dev.preset_names()
        self.presets.set_names(names, self.current_index)

    def _on_refresh_slots(self) -> None:
        dev = self._require_device()
        if dev is None:
            return
        with self._busy(t("status_reading")):
            ir_names = dev.ir_name_list()
            clone_names = dev.clone_name_list()
        self.slots.load(ir_names, clone_names)

    def _on_refresh_globals(self) -> None:
        dev = self._require_device()
        if dev is None:
            return
        with self._busy(t("status_reading")):
            glob = dev.globals()
        self.globals_tab.load_globals(glob)

    def _on_export_preset(self) -> None:
        dev = self._require_device()
        if dev is None:
            return
        with self._busy(t("status_reading")):
            state = dev.state()
            index = preset_index_from_raw(dev.preset_number_raw())
            try:
                names = dev.preset_names()
            except DeviceError:
                names = []
        name = names[index] if index is not None and 0 <= index < len(names) else None
        data = build_export(state, slot_index=index, name=name)
        slot = (data.get("slot") or {}).get("label") or "preset"
        filename = f"sonicake-{slot.lower()}.json"
        path, _selected = QFileDialog.getSaveFileName(self, t("action_export"), filename, "JSON (*.json)")
        if not path:
            return
        Path(path).write_text(dumps_export(data), encoding="utf-8")
        self._set_status(t("status_export_saved", path=path))

    # -- editor writes ----------------------------------------------------------

    def _device_or_return(self):
        return self._require_device()

    def _on_module_toggled(self, module: str, on: bool) -> None:
        dev = self._require_device()
        if dev is None:
            return
        with self._busy(t("status_writing")):
            self._ack(dev.set_module_state(module, on))
        self._set_unsaved(True)

    def _on_effect_changed(self, module: str, effect_id: int) -> None:
        dev = self._require_device()
        if dev is None:
            return
        with self._busy(t("status_writing")):
            self._ack(dev.set_effect_type(module, effect_id))
        self._set_unsaved(True)
        QTimer.singleShot(250, self._reload_state_after_effect)

    def _reload_state_after_effect(self) -> None:
        if self.dev is None:
            return
        with self._busy(t("status_reading")):
            try:
                state = self.dev.state()
            except DeviceError:
                return
        raw = self.dev.preset_number_raw() if self.dev else b""
        index = None
        if len(raw) >= 2:
            index = raw[0] | (raw[1] << 8)
            self.current_index = index
        self.editor.load_state(state, preset_label(index) if index is not None else None)

    def _on_parameter_changed(self, module: str, alg_id: int, value) -> None:
        dev = self._require_device()
        if dev is None:
            return
        with self._busy(t("status_writing")):
            self._ack(dev.set_parameter(module, alg_id, value))
        self._set_unsaved(True)

    def _on_volume_changed(self, value: int) -> None:
        dev = self._require_device()
        if dev is None:
            return
        with self._busy(t("status_writing")):
            self._ack(dev.set_preset_volume(value))
        self._set_unsaved(True)

    def _on_bpm_changed(self, value: int) -> None:
        dev = self._require_device()
        if dev is None:
            return
        with self._busy(t("status_writing")):
            self._ack(dev.set_bpm(value))
        self._set_unsaved(True)

    def _on_amp_mode_changed(self, clone: bool) -> None:
        dev = self._require_device()
        if dev is None:
            return
        with self._busy(t("status_writing")):
            self._ack(dev.set_amp_mode(clone))
        self._set_unsaved(True)

    # -- presets -----------------------------------------------------------------

    def _on_select_preset(self, index: int, factory: bool) -> None:
        dev = self._require_device()
        if dev is None:
            return
        number = index - 50 + 1 if factory else index + 1
        with self._busy(t("status_writing")):
            ack = dev.select_preset(number, factory=factory)
        self._ack(ack)
        self._on_refresh_after_select(index)

    def _on_refresh_after_select(self, index: int) -> None:
        if self.dev is None:
            return
        with self._busy(t("status_reading")):
            try:
                state = self.dev.state()
            except DeviceError:
                return
        self.current_index = index
        self.editor.load_state(state, preset_label(index))
        self.presets.set_current(index)
        self._sync_unsaved()

    def _on_save_from_editor(self) -> None:
        self.tabs.setCurrentIndex(1)  # presets tab

    def _on_save_preset(self, name: str, slot: int) -> None:
        dev = self._require_device()
        if dev is None:
            return
        with self._busy(t("status_writing")):
            ack = dev.save_preset(name, slot)
        self._ack(ack)
        if ack == "ack":
            self._set_status(t("presets_saved", name=name, slot=slot))
        self._sync_unsaved()

    # -- globals -------------------------------------------------------------------

    def _on_globals_apply(self, changes: dict) -> None:
        dev = self._require_device()
        if dev is None:
            return
        with self._busy(t("status_writing")):
            for key, value in changes.items():
                try:
                    dev.set_global(key, value)
                except (KeyError, DeviceError) as exc:
                    self._set_status(t("status_error", message=str(exc)))
                    return
        self._on_refresh_globals()


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("sonicake-manager")
    app.setOrganizationName("sonicake-manager")
    settings = QSettings("sonicake-manager", "sonicake-manager")
    set_language(str(settings.value("language", "en")))

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
