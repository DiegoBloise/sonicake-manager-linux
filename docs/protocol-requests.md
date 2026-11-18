# Requests

Todos os requests são enviados como frames curtos com `len = 2` e payload
"cru" (sem nibble-expansion). Use sempre o prefixo `8080`.

| Nome | Command 2 bytes | Frame completo (hex) |
|---|---|---|
| Estado atual | `01 02 04 01` | `8080F0000900010000000201020401F7` |
| Nomes (100) | `01 02 04 00` | `8080F0000E00010000000201020400F7` |
| Número do preset | `01 02 04 03` | `8080F0000700010000000201020403F7` |
| Configurações globais | `01 02 01 00` | `8080F00B0900010000000201020100F7` |
| Nomes de IR | `01 02 02 00` | `8080F0020900010000000201020200F7` |
| Nomes de clone | `01 02 02 04` | `8080F0030500010000000201020204F7` |
| Modificado? | `01 02 04 05` | `8080F0010500010000000201020405F7` |
| Init de sessão | `01 02 03 00` | `8080F0050900010000000201020300F7` |
