# Diagnóstico — ESP32 sem REPL (Thonny / mpremote)

Objetivo: separar **USB/chip vivos** de **firmware que não arranca** e de **curto sob a cola**.

Já sabemos de sessões anteriores:

- A porta **COM6** aparece como `USB JTAG/serial debug unit` (VID `303A`).
- O `esptool` chegou a ler o chip: **ESP32-C3 rev. 0.4**, flash 4 MB.
- Depois de gravar MicroPython, **não há bytes no Serial** (nem `>>>`).
- O Thonny chega a **apagar a flash** (modo download) mas falha o Shell depois.

Isto **não** parece um curto total em 3,3 V/USB: nesse caso o PC nem via COM6 e o erase nem começava.

## Antes de qualquer teste

1. **Fecha o Thonny por completo** (o “Install MicroPython” segura a COM6).
2. Desliga outros `mpremote` / monitor.
3. USB-C **de dados** (não só carga).

No Cursor, na pasta do projeto:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe" tools\diagnose.py --port COM6
```

Cola aqui a saída. O script diz se o bootloader vive e se o REPL está mudo.

---

## Árvore de decisão

```
PC vê COM6 (303A)?
  NAO → cabo / faltar 5 V USB / curto USB / driver
  SIM → esptool chip-id funciona?
            NAO → Thonny a ocupar COM, ou chip preso em reset
            SIM → ha banner MicroPython / >>> ?
                      SIM → so falha de upload; enviamos .py
                      NAO → firmware/run mode (rev 0.4) OU EN/BOOT presos
                            OU curto leve em GPIO, NAO curto total de alimentacao
```

---

## Alimentação correta (quando voltares à 18650)

USB do PC já alimenta o pino 5 V da Super Mini e o LDO gera 3,3 V. A 18650 **não** deve ir ao pino 3V3.

Caminho certo mais tarde: `18650 / TP4056 OUT → pino 5V da ESP` (o regulador da placa faz 3,3 V). Isolar 3V3 da célula.

Com **só USB**, esse problema está fora da equação. Os testes abaixo assumem USB-only.

---

## Testes com só USB (o que ainda faz sentido)

Já feito no PC:

- COM6 = USB-JTAG Espressif
- Bootloader responde (rev **0.4**)
- Flash tem imagem válida (byte mágico `E9`) — o Thonny **gravou**
- Consola RUN = 0 bytes — o firmware **não fala** no USB

### U1 — Temperatura (tu)

USB ligado ~20 s. ESP morna = ok. Quente demais = curto (aí sim cola/GPIO).

### U2 — Fios GPIO 4, 6 e 7 (tu)

Mesmo com USB-only, opto/MOSFET podem prender pinos. Se os fios se vêem: solta GPIO 4, RST, diz o resultado. Depois 6 e 7.

### U3 — Firmware para rev. 0.4 (PC + tu no Thonny)

O bin que o Thonny instala (`ESP32_GENERIC_C3` atual) é para silício **rev. 3+**. A tua é **0.4**. Isto basta para REPL mudo com flash “sucesso”.

No Thonny: Interpreter → Install MicroPython → opções (`=`) e um firmware **mais antigo** (v1.20–v1.22), ou avisa e gravamos `v1.22.2` com `esptool` daqui.

Fecha o Thonny antes de eu gravar.

### U4 — UART0 se tiveres um USB-TTL (opcional)

TX da Super Mini (GPIO21) → RX do adaptador, GND comum, 3,3 V. 115200. Se aparecer `MicroPython` no TTL e não na COM6, o chip corre e o problema é só a consola USB-JTAG.

### U5 — Não é teste de curto total

Curto pesado em USB/3V3: COM6 desaparecia e o erase falhava. Não é o caso.

---

## Testes que tu fazes (cola quente não impede)

Faz **um de cada vez** e responde com o resultado (ok / falhou / valor).

### T1 — Só USB, sem bateria

Desliga o fio da **18650** (ou o OUT do TP4056) que vai à ESP32. Deixa **só o USB** do PC.

- A placa deve enumerar COM6.
- Corre `diagnose.py`.

| Resultado | Leitura |
|---|---|
| Passa a haver REPL | Alimentação 18650 a atrapalhar (tensão no sítio errado) |
| Igual (COM6, sem REPL) | Não é a bateria o único problema |
| Some a COM6 | Sem USB o circuito puxava mal; ou a ESP só “viva” pela célula |

### T2 — Quente ou cheiro

Com USB ligado 20 s, toca **de leve** na ESP (não nos fios de 12 V).

- Morna: normal.
- **Muito quente / queima o dedo**: curto ou 5 V no 3,3 V. Para USB. Não precisas de abrir a cola ainda.

### T3 — Consumo USB (se tiveres USB meter ou fonte)

Corrente típica C3 em idle: dezenas de mA.  
**> 200–300 mA** parado, sem Wi-Fi: suspeito.  
**> 500 mA** ou a porta USB do PC a cair: curto.

### T4 — Periféricos fora

Se os fios GPIO 4 / 6 / 7 ainda se vêem **antes** da cola:

- Solta **só o MOSFET (GPIO 4)**. RST. `diagnose.py`.
- Depois solta **os optos (6 e 7)**.

Se o REPL aparecer com o MOSFET solto: curto ou carga no pino 4, não na ESP por baixo da cola.

### T5 — BOTÕES

BOOT solto. Toca **RST** com o USB já ligado. Corre outra vez o diagnose.

BOOT premido + RST = modo download (o Thonny apaga flash). Para o MicroPython tens de **soltar o BOOT**.

### T6 — Tensão (multímetro), pontos que costumam estar de fora

Não abras a cola ainda.

| Onde | Esperado |
|---|---|
| USB 5 V (pino 5V da Super Mini, se visível) | ~5 V com USB |
| Pino **3V3** da Super Mini | **3,2–3,4 V**, nunca ~4,2 V |
| Polos da 18650 | 3,5–4,2 V |
| 3V3 da ESP **vs** positivo da 18650 | Se estiverem iguais a ~4 V, a célula está no pino 3V3 — isso mata o arranque |

O 3V3 a 4,2 V é o teste mais importante da alimentação. A ESP32 **não** pode levar a 18650 no pino 3,3 V.

---

## O que ainda **não** fazer

- Não arrancar a cola enquanto T1–T6 não estiverem feitos.
- Não gravar outro `.bin` no Thonny em simultâneo com o `diagnose.py`.
- Não deixar o Thonny aberto “à espera” no erase — isso prende a COM6.

---

## Como me ajudar neste chat

Depois de **T1**, envia:

1. Saída completa do `diagnose.py`
2. Bateria ligada ou não
3. Placa quente ou não
4. Tensão no 3V3 se mediste

Com isso escolhemos o próximo passo (firmware antigo vs alimentação vs abrir cola).
