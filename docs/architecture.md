# Arquitetura

O projeto tem três camadas, separadas para simplificar testes, portais de
empacotamento e contribuições externas.

```
┌─────────────────────────────────────────────────┐
│ GUI (Qt) — sonicake_manager.gui                 │
├─────────────────────────────────────────────────┤
│ Device API — sonicake_manager.device            │
├─────────────────────────────────────────────────┤
│ Protocol — sonicake_manager.protocol            │
│   framing, CRC, nibble expansion, ACK/NACK      │
├─────────────────────────────────────────────────┤
│ Transport — sonicake_manager.transport          │
│   ALSA sequencer via mido/rtmidi                │
└─────────────────────────────────────────────────┘
```

## Princípios

- **Sem dependência de ambiente específico:** o app roda em qualquer Linux
  com ALSA disponível (X11, Wayland, sessão remota); não toca em nada de
  um ambiente gráfico específico. Configuração e estado ficam em XDG base
  directories (`$XDG_DATA_HOME`, `$XDG_CONFIG_HOME`).
- **Empacotável:** o binário final será um app Python empacotado (Flatpak,
  AppImage, RPM/deb via `python-build`). Toda lógica fica em código
  importável, nunca em scripts soltos.
- **Testável sem hardware:** a camada de protocolo é pura (nenhuma
  dependência de rede/MIDI) e cobre CRC, framing, remontagem de pacotes e
  encode/decode de presets. Testes podem rodar em CI sem pedal conectado.
- **On-wire first:** cada byte enviado/recebido está documentado em
  `docs/protocol.md`; nenhum comportamento depende de "magia" escondida
  em binários fechados.

## Layout do repositório

```
src/sonicake_manager/
  __init__.py          # versão
  protocol/            # tudo que é byte-level: CRC, frames, dumps
  transport/           # abertura de porta ALSA, timeouts, filas
  device.py            # API de alto nível (read/write presets, IR, saves)
  effects.py           # catálogo de módulos/efeitos disponível nos modelos
  cli.py               # ponto de entrada CLI
  gui.py               # ponto de entrada GUI (Qt)
  gui/                 # widgets, páginas e estilo
  data/                # tabelas de dados (efeitos, mapeamento de comandos)
tests/                 # testes unitários e de transporte fake
docs/                  # documentação pública
```

## Compatibilidade alvo

- **Runtime:** Python ≥ 3.11, qualquer glibc/Linux padrão (Fedora atomic,
  Debian, Ubuntu/derivatives, Arch).
- **Áudio/MIDI:** ALSA obrigatório; funciona sob PipeWire/PipeWire-JACK
  e sobre ALSA direto.
- **GUI:** Qt (PySide6) — mesma renderização em X11 e Wayland.
- **Empacotamento:** Flatpak (flatpak-builder com PyPyRuntime/org.python),
  AppImage, e RPMs/deb simples via `flatpak-builder` manifesto futuro.
