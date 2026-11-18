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
- modificado → notificação `12 45 01` (buffer modificado) ou `12 45 00` (buffer salvo);
- ACK de escrita → `14 08 00` (ACK), `14 08 01` (NACK).

### Respostas observadas de comandos de escrita

Medido contra o hardware (Pocket Master, novembro/2026):

| Comando | Resposta observada |
|---|---|
| Escrita no edit buffer (parâmetro) | `12 45 01` ("preset-modified") ou `14 08 00` (ACK) — ambos indicam sucesso |
| Seleção de preset | `12 45 00` ("preset-saved"), `12 45 01` ou `14 08 00` — todos indicam sucesso |
| Save para slot de usuário | `12 45 00` ("preset-saved") — validado em hardware (U46, novembro/2026) |

A flag "modificado" é pegajosa (sticky): uma vez suja, ela só é limpa
recarregando o preset (select) ou salvando. Restaurar os valores anteriores
não limpa a flag.
