# Protocolo

Este documento descreve o protocolo troca de dados usado pelos processadores
Sonicake. É a referência de design do `sonicake_manager.protocol`.

## Visão geral

- Transporte: **USB-MIDI** classe-compliant ou **BLE-MIDI**.
- Sem SDKs de terceiros: tudo é **SysEx**.
- Frame: `8080 F0 <CRC> <total> <seq> <len> <payload> F7`.
- **Todo** byte lógico — inclusive CRC/total/seq/len — é transmitido com
  nibble-expansion: `0xAB` → `0A 0B`.
- CRC: **CRC-8/SMBUS** (poly `0x07`, init `0x00`), calculado sobre
  `[01, 00, len] + payload` para pacotes únicos, ou `[total, seq, len] +
  payload` para pacotes de um upload em bloco.

## Leitura vs. escrita

### Requests (leem do pedal)

Frames validados contra o dispositivo — use os bytes documentados em
`docs/protocol-requests.md` exatamente como estão:

### Writes (escrevem no pedal)

Frames com payload nibble-expanded, a partir de `11 4x`:

- `11 42` — volume/BPM do preset
- `11 43` — selecionar preset
- `11 44` — ordem da cadeia
- `11 47` — tipo de efeito do módulo
- `11 48` — valor de parâmetro
- `11 49` — liga/desliga módulo (e modo clone)
- `11 4A` — salvar preset
- `11 4D` — footswitch

### ACK / NACK

| Payload lógico | Significado |
|---|---|
| `01 04 00 08 00 00` | ACK (sucesso) |
| `01 04 00 08 00 01` | NACK (falha/inválido) |
| `01 02 04 05 00 01` | preset modificado |
| `01 02 04 05 00 00` | preset salvo |

## Remontagem de pacotes

Respostas grandes são divididas em vários pacotes com `total` constante e
`seq` crescente. Concatene os payloads ordenados por `seq`. A resposta não
ecoia o request — o roteamento é por contexto.

## Uploads em bloco

IR e perfis de clone são enviados com `build_chunked_frames()` (chunks de 19
bytes, CRC por pacote sobre `[total, seq, len] + chunk`), com ACK por pacote.

## Observações de implementação

- Até 10–20 ms entre frames para evitar perda/NACK.
- Buffer de edição não é persistente: salvar em slot é necessário para
  fixar modificações.
- Prefixo `8080` é aceito/exigido em pedidos de globais.

Veja também:

- [docs/protocol-requests.md](docs/protocol-requests.md)
- [docs/protocol-writes.md](docs/protocol-writes.md)
