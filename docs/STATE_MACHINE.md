# Máquina de estados

Sem `time.sleep()` no caminho de controlo. Tempos com `time.ticks_ms()` e `ticks_diff()`. PWM só no estado `INJECTING` (duty configurado); em todos os outros, duty **0**.

## Estados

| Estado | Significado | MOSFET |
|---|---|---|
| `STANDBY` | Sem Pós-Chave (chave off ou simulador aberto) | OFF |
| `WAIT_START` | Chave on; à espera de borda de partida | OFF |
| `INJECTION_DELAY` | Partida detectada; a contar `delay_ms` | OFF |
| `INJECTING` | PWM ativo; a contar `inject_ms` | ON (duty) |
| `LOCKOUT` | Injeção terminou; à espera de soltar o botão | OFF |

`IGNITION_ON` do rascunho inicial é um estado de passagem: pode existir no enum ou fundir-se em `WAIT_START`. Preferência: **um ciclo** `IGNITION_ON` só para log, depois `WAIT_START`.

## Fluxo principal

```
STANDBY
  │  Pós-Chave ativo (GPIO 0 / D0 LOW estável) e enabled
  ▼
WAIT_START
  │  borda de partida (GPIO 1 HIGH→LOW, debounce) e enabled
  ▼
INJECTION_DELAY     (se delay_ms == 0, atravessa no mesmo ciclo)
  │  ticks_diff(now, t_delay) >= delay_ms
  ▼
INJECTING
  │  ticks_diff(now, t_inj) >= inject_ms  (limitado por max_inject_ms)
  ▼
LOCKOUT
  │  botão de partida liberado (GPIO 1 HIGH estável)
  ▼
WAIT_START
```

## Transição global (prioridade máxima)

Em **qualquer** estado:

- Pós-Chave ausente (`GPIO 0 HIGH` estável), **ou**
- `enabled == false`

→ duty 0 **imediatamente** → `STANDBY`.

Isto cobre chave desligada a meio da injeção.

## Regras de disparo

1. Partida é **borda**, não nível. Botão preso não dispara de novo.
2. Só dispara com Pós-Chave já ativo (`WAIT_START`).
3. Depois de `INJECTING`, `LOCKOUT` até o botão ir a inativo.
4. `inject_ms` efetivo = `min(config.inject_ms, MAX_INJECT_MS)`.
5. Watchdog lógico: se permanecer em `INJECTING` além de `MAX_INJECT_MS` + margem → duty 0 → `LOCKOUT`.
6. Debounce 20–50 ms nas duas entradas.

## Relação com o banco de testes

| Ação no banco | Esperado (a partir da Fase 3) |
|---|---|
| Nada pressionado | `STANDBY`, PWM 0 |
| Só Pós-Chave | `WAIT_START`, PWM 0 |
| Pós-Chave + toque em Partida | delay → PWM pelo tempo → off → lockout |
| Soltar Partida | volta a `WAIT_START` |
| Soltar Pós-Chave a meio | PWM 0, `STANDBY` |
| Partida sem Pós-Chave | ignorar, `STANDBY` |

## Log Serial (até existir Web)

A cada mudança de estado, uma linha, por exemplo:

```
state=WAIT_START post=1 start=0 pwm=0
```

`post`/`start` já na lógica de aplicação: `1` = sinal presente (GPIO físico LOW).
