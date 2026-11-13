# Cold Start Injector — Arquitetura

Documento-guia do projeto. Qualquer implementação, teste ou alteração deve seguir este arquivo.

- Hardware: [HARDWARE.md](HARDWARE.md)
- Temperatura do motor (sinal, pino, teste na oficina): [TEMPERATURA.md](TEMPERATURA.md)
- Estados: [STATE_MACHINE.md](STATE_MACHINE.md)
- Fases: [PHASES.md](PHASES.md)
- Ligar a placa e enviar código (Cursor): [SETUP.md](SETUP.md)
- Sem REPL / Thonny / curto: [DIAGNOSTICS.md](DIAGNOSTICS.md)

## Objetivo

Sistema embarcado no **Seeed XIAO ESP32-C6** (MicroPython) para auxiliar a partida a frio. A ESP32-C3 Super Mini ficou de fora: bootloader USB vivo, mas **sem REPL** (rev. 0.4). A XIAO C6 no Thonny (COM7, v1.28.0) confirma PC e fluxo MicroPython.

A primeira prioridade é a **função de injeção segura e previsível**. Wi-Fi e página web vêm por último.

## Runtime: MicroPython

O firmware da aplicação é **MicroPython** (uPython), não Arduino/C++ nem PlatformIO.

| Camada | Na XIAO ESP32-C6 |
|---|---|
| Interpretador | MicroPython `SEEED_XIAO_ESP32C6` (Thonny ou `esptool`) |
| Aplicação | Ficheiros `.py` enviados para a flash (`boot.py`, `main.py`, módulos) |
| Ferramenta no PC | `mpremote` no terminal do Cursor |
| GPIO / PWM | `machine.Pin`, `machine.PWM` (periférico LEDC por baixo) |
| Tempo | `time.ticks_ms()` / `ticks_diff()` — sem `time.sleep()` no loop de controlo |
| Persistência | ficheiro JSON na flash e/ou `esp32.NVS` (Fase 4) |

Fluxo de trabalho: editar no Cursor → `mpremote cp` / `mpremote run` → REPL USB. Detalhe em [SETUP.md](SETUP.md).

## Princípio central

Separar sempre:

| Camada | Papel | Ficheiro típico |
|---|---|---|
| Hardware | Pinos, leitura invertida, PWM, debounce | `pins.py`, `hardware.py` |
| Controle | Máquina de estados, tempos, lockout, fail-safe | `controller.py` |
| Persistência | Parâmetros em NVS / JSON | `config.py` |
| Interface | REPL/Serial no início; Web/AP só na fase final | `web_server.py` |

A lógica de partida **não depende** da interface. Serial ou Web apenas alteram parâmetros. O controlador continua a funcionar sem cliente ligado.

## Hardware instalado (referência)

Banco de testes já montado:

- Seeed XIAO ESP32-C6 (controlador atual)
- Opto PC817 (2 canais) nas entradas
- Driver MOSFET na saída PWM
- Botões para **simular** Pós-Chave e Partida
- Cadeia de alimentação:

```
+12 V Pós-Chave (moto / simulador)
        ↓
     LM2596  →  5 V
        ↓
     TP4056  (carga + proteção)
        ↓
   18650 3,7 V 3000 mAh
        ↓
     ESP32-C3
```

Com chave desligada o ESP32 permanece alimentado pela 18650, em standby, **sem precisar de boot** quando a chave liga. O firmware trata alimentação só como conceito operacional (sem monitorar bateria no MVP).

## Mapeamento de pinos

Única fonte de verdade no código: `pins.py`.

| Sinal | XIAO | GPIO | Direção | Lógica |
|---|---|---|---|---|
| Pós-Chave | D0 | 0 | Input pull-up | `0` = 12 V detectado |
| Botão de partida | D1 | 1 | Input pull-up | `0` = pressionado |
| MOSFET PWM | D2 | 2 | `machine.PWM` | Duty 0 = OFF |

Leitura **invertida** por causa do opto (transistor para GND).

Saída de potência: VIN+ do MOSFET em +12 V Pós-Chave, VIN− no GND da moto. Bomba e solenoide no **mesmo** PWM — não há canais separados.

## Fail-safe (obrigatório em todas as fases)

1. GPIO 4 inicia em **OFF** no `boot.py`, **antes** de importar o resto da aplicação.
2. Perder Pós-Chave em qualquer estado → PWM 0 imediato → `STANDBY`.
3. Tempo máximo absoluto de injeção, mesmo com parâmetro inválido na memória.
4. Um disparo por ciclo do botão (lockout até soltar).
5. Sem `time.sleep()` na lógica principal: `ticks_ms()` + estados. `sleep_ms` curto só é aceitável em debounce isolado se não bloquear o corte da chave; preferir polling com `ticks_diff`.
6. PWM via `machine.PWM` (LEDC), não toggling em software.

## Máquina de estados (resumo)

```
STANDBY → (Pós-Chave) → WAIT_START → (borda de partida)
  → INJECTION_DELAY → INJECTING → LOCKOUT → WAIT_START
```

Chave off a qualquer momento: `STANDBY` e MOSFET off. Detalhe em [STATE_MACHINE.md](STATE_MACHINE.md).

## Parâmetros (existir cedo; UI tarde)

| Parâmetro | Uso |
|---|---|
| `enabled` | Liga/desliga o sistema |
| `delay_ms` | Espera após detectar partida |
| `inject_ms` | Duração do PWM |
| `pwm_percent` | Intensidade (0–100) |
| `max_inject_ms` | Teto absoluto (firmware, não só NVS) |

Na Fase 1–3 os valores podem ser constantes no código. Na Fase 4 passam a persistência. Na Fase 5 a Web só lê/grava esses campos.

## Estrutura de código alvo

```
Cold-Start-Injector/
├── boot.py              # fail-safe GPIO 4 OFF; corre em todo reset
├── main.py              # arranque da app (depois de boot.py)
├── pins.py              # GPIO 6, 7, 4
├── hardware.py
├── controller.py        # a partir da Fase 3
├── config.py            # a partir da Fase 4
├── web_server.py        # só na última fase
├── www/                 # HTML/CSS/JS da Fase 5
├── requirements-dev.txt # esptool + mpremote no PC
└── docs/
```

Ficheiros em `boot.py` / `main.py` / módulos são **copiados para a raiz da flash** do ESP32 (`/`). Não há compilação C++.

Não criar Web “pela metade” no meio do caminho. Até a fase de rede, `boot.py` + `main.py` + `hardware.py` (+ `controller.py` / `config.py`) bastam.

## Ordem de desenvolvimento

Funcionalidade primeiro. Rede por último. Cada fase tem um teste no banco atual (botões + REPL) antes de avançar. Critérios em [PHASES.md](PHASES.md).

| Fase | Nome | Entrega |
|---|---|---|
| 0 | Esqueleto | MicroPython na placa, pinos, PWM off no boot, print no REPL |
| 1 | Leituras | Pós-Chave e Partida visíveis no Serial |
| 2 | Atuador | PWM no GPIO 4 comanda MOSFET (teste manual) |
| 3 | Controle | Máquina de estados completa + proteções |
| 4 | Persistência | NVS/JSON; ajuste por Serial |
| 5 | Web | AP + página local |

## Fora do MVP

OTA, mDNS, Wi-Fi Station, logs persistentes, contador de partidas, monitor de bateria, modo automático, histórico. Temperatura do motor está em investigação, fora da máquina de estados até o sinal ser classificado: [TEMPERATURA.md](TEMPERATURA.md).

## Regras para o agente / desenvolvimento

- Seguir as fases: não misturar Web no código de controle.
- Não usar `time.sleep()` no loop de injeção.
- Não acionar PWM sem Pós-Chave ativo (exceto teste **explícito** e temporário da Fase 2, depois removido).
- Documentar no Serial o estado atual — é a interface de diagnóstico até a Fase 5.
- Alterar pinos **somente** em `pins.py`.
- Porta típica da C6: **COM7** (USB JTAG). Fecha o Thonny antes de `mpremote`.
