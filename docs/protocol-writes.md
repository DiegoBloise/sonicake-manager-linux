# Writes

Frames de escrita: payload nibble-expanded, começando em `11`.

## Família `11 42` — volume/BPM do preset

Payload lógico: `11 42 01 <20|LB> <field> <value LE>`

- `11 42 01 20 01 00 <v>` — campo 1 (input gain, 0–127)
- `11 42 01 20 02 00 <v>` — campo 2 (BPM, 40–240)
- `11 42 01 20 03 00 <v>` — campo 3 (output gain, 0–127)

## Família `11 43` — selecionar preset

Payload: `11 43 01 20 01 00 <slot>` — `slot` é `01..64` (valor = slot + 1).

## Família `11 44` — ordem da cadeia

Payload: `11 44 01 20 01 00 <mask...>` — bytes lógicos das posições, do
cofre inicial ao final.

## Família `11 47` — tipo de efeito do módulo

Payload: `11 47 01 20 <moduleId> <effectTypeId> <...>`

## Família `11 48` — valor de parâmetro

Payload: `11 48 01 20 <moduleId> <algId> <value LE>` — `value` depende da
restrição do parâmetro em `data/effects.json`.

## Família `11 49` — liga/desliga módulo (e modo clone)

Payload: `11 49 01 20 <moduleId> <on|off> [<cloneSlot?>]`

- `01` liga o módulo.
- `00` desliga o módulo.
- Adicionalmente, `11 49` pode ativar o modo clone em módulos de IR.

## Família `11 4A` — salvar preset

Payload: `11 4A 01 20 01 00 <slot> <len(nome)> <nome ASCII>`

- `slot`: `01..32` para slots de usuário (endereçados por índice lógico).
- `nome`: até 10 caracteres ASCII.

## Família `11 4D` — footswitch

Payload: `11 4D 01 20 <fsId> <mask>` — `fsId=01` (FS1) ou `02` (FS2),
`mask` são bits dos módulos que o footswitch controla.

## Família `11 11` e `11 4B` — configurações globais

- `11 11` — volume global.
- `11 4B` — outras configurações globais (backlight, ECO, reamp).

O frame completo é montado por `sonicake_manager.protocol.build_frame()`:
`8080 F0 <crc expandido> 00 01 00 00 <len expandido> <payload expandido> F7`.
Consulte `sonicake_manager.protocol.framing` para encode/parse.
