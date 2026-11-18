"""Minimal in-app translations (English default, Portuguese optional).

Chosen over Qt Linguist so no extra tooling is needed at build time and
translations ship inside the wheel/Flatpak.  Language is persisted with
QSettings and applied on the next launch.
"""

from __future__ import annotations

import copy

_EN = {
    "app_title": "Sonicake Manager",
    "status_disconnected": "Disconnected",
    "status_connecting": "Connecting…",
    "status_connected": "Connected to {name}",
    "status_reading": "Reading from device…",
    "status_writing": "Writing to device…",
    "status_error": "Error: {message}",
    "action_refresh": "Refresh",
    "action_connect": "Connect",
    "action_disconnect": "Disconnect",
    "action_export": "Export preset…",
    "status_export_saved": "Preset exported to {path}",
    "tab_editor": "Current Preset",
    "tab_presets": "Presets",
    "tab_globals": "Global",
    "tab_about": "About",
    "editor_preset_slot": "Slot",
    "editor_volume": "Volume",
    "editor_bpm": "BPM",
    "editor_bpm_note": "Accepted by device but not persisted",
    "editor_amp_mode": "Amp mode",
    "editor_amp_normal": "Normal",
    "editor_amp_clone": "Clone",
    "editor_chain": "Signal chain",
    "editor_module_on": "On",
    "editor_save_buffer": "Save to slot…",
    "preset_user": "User",
    "preset_factory": "Factory",
    "presets_current": "Current slot",
    "presets_empty": "(empty)",
    "presets_select": "Select this preset",
    "presets_save_here": "Save current buffer here",
    "presets_name": "Name",
    "presets_slot": "Slot (1–50)",
    "presets_saved": "Saved '{name}' to slot {slot}",
    "presets_selected": "Selected {slot}",
    "globals_title": "Global settings",
    "globals_global_volume": "Global volume (0–100)",
    "globals_input_level": "Input level (dB)",
    "globals_fx_rec": "FX record level (dB)",
    "globals_bt_rec": "Bluetooth record level (dB)",
    "globals_monitor": "Monitor level (dB)",
    "globals_backlight": "Backlight (0–100)",
    "globals_read_only": "Read-only (raw):",
    "globals_apply": "Apply",
    "globals_applied": "Global settings updated",
    "ack_generic": "Device response: {status}",
    "err_no_device": "No Sonicake device found. Connect it via USB, then press Refresh or set SONICAKE_MIDI_ADDRESS.",
    "err_device": "Device error: {message}",
    "err_read_only": "Could not read from the device.",
    "about_text": (
        "Sonicake Manager for Linux\n"
        "Version {version}\n\n"
        "An independent open-source desktop manager for Sonicake processors\n"
        "(Pocket Master / Sonic Master series), built on the documented\n"
        "device protocol — no undocumented firmware internals.\n\n"
        "Protocol knowledge comes from publicly available payload documentation\n"
        "and community notes. This project is not affiliated with Sonicake.\n\n"
        "Bundled data tables (effects, parameters) are distributed under the\n"
        "project license. See docs/ for the protocol description.\n\n"
        "Language: {language} — the change applies on next launch.\n"
    ),
    "about_language": "Language",
    "lang_en": "English",
    "lang_pt": "Português",
}

_PT = copy.deepcopy(_EN)
_PT.update(
    {
        "app_title": "Sonicake Manager",
        "status_disconnected": "Desconectado",
        "status_connecting": "Conectando…",
        "status_connected": "Conectado a {name}",
        "status_reading": "Lendo do aparelho…",
        "status_writing": "Gravando no aparelho…",
        "status_error": "Erro: {message}",
        "action_refresh": "Atualizar",
        "action_connect": "Conectar",
        "action_disconnect": "Desconectar",
        "action_export": "Exportar preset…",
        "status_export_saved": "Preset exportado em {path}",
        "tab_editor": "Preset Atual",
        "tab_presets": "Presets",
        "tab_globals": "Globais",
        "tab_about": "Sobre",
        "editor_preset_slot": "Posição",
        "editor_volume": "Volume",
        "editor_bpm": "BPM",
        "editor_bpm_note": "Aceito pelo aparelho, mas não persistido",
        "editor_amp_mode": "Modo de amp",
        "editor_amp_normal": "Normal",
        "editor_amp_clone": "Clone",
        "editor_chain": "Cadeia de sinal",
        "editor_module_on": "Ligado",
        "editor_save_buffer": "Salvar na posição…",
        "preset_user": "Usuário",
        "preset_factory": "Fábrica",
        "presets_current": "Posição atual",
        "presets_empty": "(vazio)",
        "presets_select": "Selecionar este preset",
        "presets_save_here": "Salvar buffer atual aqui",
        "presets_name": "Nome",
        "presets_slot": "Posição (1–50)",
        "presets_saved": "'{name}' salvo na posição {slot}",
        "presets_selected": "{slot} selecionado",
        "globals_title": "Configurações globais",
        "globals_global_volume": "Volume global (0–100)",
        "globals_input_level": "Nível de entrada (dB)",
        "globals_fx_rec": "Grav. FX (dB)",
        "globals_bt_rec": "Grav. Bluetooth (dB)",
        "globals_monitor": "Monitor (dB)",
        "globals_backlight": "Retroiluminação (0–100)",
        "globals_read_only": "Somente leitura (bruto):",
        "globals_apply": "Aplicar",
        "globals_applied": "Configurações globais atualizadas",
        "ack_generic": "Resposta do aparelho: {status}",
        "err_no_device": "Nenhum aparelho Sonicake encontrado. Conecte via USB e pressione Atualizar ou defina SONICAKE_MIDI_ADDRESS.",
        "err_device": "Erro no aparelho: {message}",
        "err_read_only": "Não foi possível ler do aparelho.",
        "about_text": (
            "Sonicake Manager para Linux\n"
            "Versão {version}\n\n"
            "Gerenciador desktop de código aberto para pedais Sonicake\n"
            "(linha Pocket Master / Sonic Master), construído sobre a\n"
            "documentação pública do protocolo — sem internals não documentados.\n\n"
            "O conhecimento de protocolo vem de documentação pública de payload e\n"
            "notas da comunidade. Este projeto não é afiliado à Sonicake.\n\n"
            "Tabelas de dados (efeitos, parâmetros) são distribuídas sob a licença\n"
            "do projeto. Veja docs/ para a descrição do protocolo.\n\n"
            "Idioma: {language} — a mudança vale no próximo início.\n"
        ),
        "about_language": "Idioma",
        "lang_en": "English",
        "lang_pt": "Português",
    }
)

_TABLES = {"en": _EN, "pt": _PT}
_SUPPORTED = ("en", "pt")

_current = "en"


def set_language(lang: str) -> None:
    global _current
    _current = lang if lang in _SUPPORTED else "en"


def current_language() -> str:
    return _current


def supported_languages() -> tuple[str, ...]:
    return _SUPPORTED


def t(key: str, **kwargs) -> str:
    table = _TABLES.get(_current, _EN)
    template = table.get(key, _EN.get(key, key))
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError):
        return template
