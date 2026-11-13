# Fases de desenvolvimento

Ordem obrigatória. **Não avançar** enquanto o critério de saída da fase não for validado no banco (botões + REPL). Wi-Fi e Web são a última fase.

Stack: **MicroPython** no ESP32-C3. Instalação e upload: [SETUP.md](SETUP.md).

Prioridade: **injeção correta e segura** > persistência > rede.

---

## Fase 0 — Esqueleto e fail-safe de boot

**Objetivo:** MicroPython a correr na placa; GPIO 4 conhecido e desligado no reset.

**Fazer:**

- Instalar firmware `ESP32_GENERIC_C3` (`esptool`) — ver [SETUP.md](SETUP.md)
- `pins.py` com GPIO 6, 7, 4
- `boot.py`: Pin 4 como saída valor `0` **antes** de qualquer outro I/O
- GPIO 6 e 7 como entrada com `Pin.PULL_UP`
- `print` de identificação no REPL (`CSI Fase 0`)
- `requirements-dev.txt` (`esptool`, `mpremote`)

**Não fazer:** máquina de estados, Wi-Fi, PWM variável.

**Teste:**

1. `mpremote` liga ao REPL.
2. Reset: aparece a mensagem de boot.
3. Multímetro / LED no MOSFET: saída **não** aciona sozinha no reset.

**Saída:** firmware “morto-seguro” no pino de potência.

---

## Fase 1 — Validar entradas (banco atual)

**Objetivo:** confirmar opto + botões de simulação e a lógica invertida.

**Fazer:**

- Ler GPIO 6 e 7 (`Pin.value()`)
- Debounce simples com `ticks_ms`
- Imprimir no REPL a cada mudança: `post_key=ON/OFF start=ON/OFF` (já invertido: nível físico 0 = ON)

**Não fazer:** acionar MOSFET automaticamente.

**Teste no banco:**

| Botão | Serial esperado |
|---|---|
| Nenhum | `post=OFF start=OFF` |
| Só Pós-Chave | `post=ON start=OFF` |
| Só Partida | `post=OFF start=ON` |
| Ambos | `post=ON start=ON` |

**Saída:** entradas fiáveis. Se o nível estiver invertido, corrigir só em `hardware.py` / documentação, não espalhar `not pin.value()` pelo resto.

---

## Fase 2 — Validar atuador (PWM / MOSFET)

**Objetivo:** GPIO 4 realmente liga bomba+válvula (ou carga de teste).

**Fazer:**

- `machine.PWM` no GPIO 4 (freq. ~1 kHz, duty 0 no arranque)
- Modo de teste **explícito**, por exemplo:
  - Pós-Chave ON **e** comando no REPL `pwm 50` / `pwm 0`, **ou**
  - Partida pressionada **com** Pós-Chave liga PWM 100% até soltar (hold-to-run), sem tempos
- Duty 0 se Pós-Chave off, mesmo neste modo

**Não fazer:** delays de injeção, persistência, Web. Remover ou desligar o modo hold/REPL quando a Fase 3 entrar.

**Teste:**

1. Sem Pós-Chave: PWM não liga (software + VIN+ do MOSFET).
2. Com Pós-Chave: carga responde ao comando.
3. Reset: carga desliga.
4. Se houver solenoide: confirmar que 100% não treme; anotar `freq` usada.

**Saída:** cadeia de potência validada.

---

## Fase 3 — Máquina de estados (funcionalidade principal)

**Objetivo:** comportamento de produção no banco, ainda com constantes no código.

**Fazer:**

- `controller.py` conforme [STATE_MACHINE.md](STATE_MACHINE.md)
- Constantes iniciais sugeridas: `delay_ms=200`, `inject_ms=1500`, `pwm_percent=100`, `enabled=True`, `MAX_INJECT_MS=5000`
- Log de estado no REPL
- Sem `time.sleep()` no loop (`ticks_ms` / `ticks_diff`)

**Teste (checklist):**

- [ ] Só chave → espera, PWM 0
- [ ] Toque curto em partida → delay → pulso → off
- [ ] Botão de partida mantido → um único pulso, depois lockout
- [ ] Soltar partida → pode disparar de novo (novo toque)
- [ ] Soltar chave a meio do pulso → corta na hora
- [ ] Partida sem chave → nada
- [ ] Reset a meio → PWM 0

**Saída:** produto útil no banco. Esta fase é o marco de **prioridade máxima**.

---

## Fase 4 — Parâmetros persistentes

**Objetivo:** sobreviver a reboot; ajustar sem reeditar código.

**Fazer:**

- JSON na flash e/ou `esp32.NVS`
- Defaults se o ficheiro não existir
- Validar limites ao carregar e ao gravar
- Interface **REPL/Serial** (`delay`, `inject`, `pwm`, `enabled`, `save`, `dump`) — não Web

**Teste:**

1. Alterar `inject_ms`, `save`, reset, comportamento novo.
2. Valor absurdo (ex. 999999) limitado por `MAX_INJECT_MS`.
3. `enabled=0`: chave + partida não acionam.

**Saída:** configuração persistente sem rede.

---

## Fase 5 — Wi-Fi AP + página Web (por último)

**Objetivo:** configurar no telemóvel, sem mudar a lógica de tempo real.

**Fazer:**

- AP local (ex. `CSI-XXXX`) via `network.WLAN`
- Servir `www/index.html` (e CSS/JS) a partir da flash
- Rotas só para ler/gravar os mesmos campos da Fase 4
- Controller **não** chama o servidor; o servidor só atualiza `config`

**Não fazer nesta fase (ainda):** Station, mDNS, OTA.

**Teste:**

1. Injeção continua a funcionar **sem** cliente Wi-Fi.
2. Gravou na página → reboot → mesmos valores.
3. Desabilitar na página = equivalente ao Serial da Fase 4.
4. O servidor não bloqueia o loop de controlo (`uasyncio` ou polls curtos).

**Nota:** AP sempre ligado drena a 18650 em standby. Aceitável no primeiro corte da Fase 5; depois pode limitar AP a “chave on” ou timeout.

---

## Depois do MVP (não calendário agora)

OTA, Station, mDNS, logs, contador de partidas, ADC de bateria, temperatura, modo automático, diagnóstico Web, histórico.

---

## Como usar este ficheiro no Cursor

1. Implementar **só a fase atual**.
2. Enviar com `mpremote` e marcar o checklist no banco antes da fase seguinte.
3. Se algo falhar no hardware, parar e corrigir pinos/opto/MOSFET — não “compensar” com Web ou mais estados.
