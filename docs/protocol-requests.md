# Requests

Todos os frames seguem o formato com nibble-expansion uniforme:

```
8080 F0 <crc expandido> <total expandido> <seq expandido> <len expandido>
<payload expandido> F7
```

Esses frames de request são constantes conhecidas — use-os exatamente como
estão. Eles passam pela mesma validação de CRC do formato geral.

| Nome | Frame (hex) | Pacotes da resposta |
|---|---|---|
| Estado atual | `8080F0000900010000000201020401F7` | 26 pacotes / ~952 bytes |
| Nomes (100) | `8080F0000E00010000000201020400F7` | 106 pacotes / ~4004 bytes |
| Número do preset | `8080F0000700010000000201020403F7` | 1 pacote |
| Configurações globais | `8080F00B0900010000000201020100F7` | 1 pacote |
| Nomes de IR | `8080F0020900010000000201020200F7` | 1 pacote |
| Nomes de clone | `8080F0030500010000000201020204F7` | 1 pacote |
| Modificado? | `8080F0010500010000000201020405F7` | 1 pacote |
| Init de sessão | `8080F0050900010000000201020300F7` | 1 pacote |

Os frames estão embalados em `sonicake_manager.protocol.requests.REQUESTS`.

## Respostas

As respostas não ecoam o request. O roteamento é feito por contexto:

- estado/nomes/número/globais → dump remontável por `total`/`seq`;
- modificado → notificação `0102 0405 000N` (N=1 modificado, N=0 salvo).
