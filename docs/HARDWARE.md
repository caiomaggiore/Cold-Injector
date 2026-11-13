# Hardware — Cold Start Injector

Estado **já montado** no banco de testes. O firmware assume esta topologia.

## Controlador

- Placa: **Seeed XIAO ESP32-C6**
- Firmware: MicroPython **SEEED_XIAO_ESP32C6** (v1.28.0 no Thonny, COM7)
- Lógica: 3,3 V (LDO da XIAO a partir do USB 5 V)
- 18650: **OUT+ do TP4056 → pino 5V (VBUS)** da XIAO. **Não** usar pads BAT. **Nunca** no 3V3.

Não soldar Reset/Boot extra: o USB-C (JTAG) chega para gravar. Pads EN/BOOT/JTAG da traseira ficam livres.

## Soldar só isto (XIAO ESP32-C6)

Lado direito do silkscreen (D0 em cima, junto ao USB): **D0, D1, D2**.  
Lado esquerdo (VBUS em cima): **5V/VBUS** e **GND**.  
**3V3, D3–D10, BAT+, BAT−, círculos JTAG: não soldar.**

| Fio | Pad na XIAO | Função |
|---|---|---|
| TP4056 OUT+ (célula ~3,7–4,2 V) | **5V** (marcado VBUS na traseira) | Alimenta o LDO → 3,3 V interno |
| TP4056 OUT− / GND lógico | **GND** | Massa da lógica |
| Opto canal Pós-Chave (coletor, lado ESP) | **D0** | GPIO 0 — ignição |
| Opto canal Partida (coletor, lado ESP) | **D1** | GPIO 1 — botão de partida |
| Driver MOSFET TRIG/PWM | **D2** | GPIO 2 — bomba + válvula |

Emissores dos optos (lado ESP) → **GND** da XIAO (pull-up interno).  
`GND Signal` do MOSFET → **GND** da XIAO.  
`VIN+` / `VIN−` do MOSFET **não** vão à XIAO: 12 V Pós-Chave e GND da moto.

USB-C: só para programar. **Não** deixar USB do PC e TP4056 no 5V ao mesmo tempo** (o OUT do TP4056 é tensão de bateria, não 5 V regulados; em paralelo com o USB briga e pode recuar tensão para o PC). Programa com USB e célula desligada, ou tira o USB quando a 18650 estiver no 5V.

## Alimentação

```
+12 V Pós-Chave (moto / simulador)
        ↓
     LM2596  →  5 V
        ↓
     TP4056  (carga + proteção da 18650)
        ↓
   OUT+  ──→  5V (VBUS) da XIAO  →  LDO  →  3,3 V interno
   OUT−  ──→  GND da XIAO
```

Pads **BAT** da XIAO ficam **vazios** (evita dois carregadores na mesma célula: TP4056 + carga USB da XIAO).

| Condição | Efeito |
|---|---|
| Chave off / 12 V ausente | LM2596 sem entrada; ESP32 vive da 18650; firmware em `STANDBY` |
| Chave on / 12 V presente | TP4056 carrega a célula; opto de Pós-Chave ativa; ESP32 **já está ligado** |
| 18650 esgotada | Há boot ao ligar a chave (LM2596→TP4056→5V); D2 deve permanecer OFF |

O +12 V Pós-Chave também alimenta o **VIN+ do MOSFET**. Sem chave, a bomba/válvula não têm potência mesmo que o PWM falhe em nível alto — fail-safe elétrico. O software ainda deve forçar duty 0.

## Entradas (opto PC817, 2 canais)

Sinais de 12 V da moto (ou botões de simulação no banco):

1. **+12 V Pós-Chave** — ignição ligada  
2. **+12 V Botão de Partida** — motor de partida acionado  

O PC817 isola o lado automotivo do GND lógico do ESP32. No lado do ESP32 as saídas do opto são transistores para GND.

| Função | XIAO | GPIO | Modo | Nível lógico no código |
|---|---|---|---|---|
| Pós-Chave | D0 | **0** | `Pin.IN`, `Pin.PULL_UP` | `0` = ativo (12 V no opto) |
| Partida | D1 | **1** | `Pin.IN`, `Pin.PULL_UP` | `0` = ativo |
| — | — | — | — | `1` = sinal ausente |

Botões do banco devem reproduzir o mesmo comportamento: fechar o canal do opto (ou o equivalente) de modo que o GPIO vá a GND.

Debounce: 20–50 ms de nível estável no software. Partida tratada como **borda** (pressionou), não como nível contínuo.

## Saída (driver MOSFET + PWM)

| Função | XIAO | GPIO | Periférico |
|---|---|---|---|
| TRIG / PWM | D2 | **2** | `machine.PWM` (LEDC) |

Alimentação do driver:

- `VIN+` → +12 V Pós-Chave  
- `VIN−` → GND da moto  
- `TRIG/PWM` → **D2** (GPIO 2)  
- `GND Signal` → **GND** da XIAO  

Carga no mesmo canal (não separável no MVP):

- Bomba de combustível  
- Válvula solenoide  

Mesmo duty, mesma frequência. No banco, validar primeiro com duty 100% (solenoide puxa de forma limpa). PWM parcial só depois de confirmar que o solenoide não treme.

Sugestão inicial: `PWM(Pin(2), freq=1000, duty=0)`. Duty 0 no `boot.py`.

## Pinos no firmware

```python
# pins.py  — XIAO ESP32-C6
GPIO_POST_KEY = 0      # D0
GPIO_START_BUTTON = 1  # D1
GPIO_MOSFET_PWM = 2    # D2
```

Não reutilizar GPIO 4/6/7 da Super Mini C3: na XIAO esses números são pads JTAG, **não** D4/D6/D7.

Não espalhar números mágicos noutros ficheiros.

## Banco de testes atual

Disponível agora, sem moto:

- Botão / simulação **Pós-Chave**
- Botão / simulação **Partida**
- MOSFET + carga (ou LED/carga de teste, se ainda não estiver a bomba)
- USB CDC / REPL MicroPython para log de estados e níveis (`mpremote`)

Isso é suficiente para as Fases 0–4. A Fase 5 (Wi-Fi) não é necessária para validar injeção.

## O que o firmware NÃO faz (MVP)

- Medir tensão da 18650
- Medir 12 V
- Controlar o LM2596 ou o TP4056
- Canais PWM separados para bomba e válvula
- Ler temperatura do motor (pino, front-end e teste na oficina em [TEMPERATURA.md](TEMPERATURA.md); o GPIO ainda não está em `pins.py`)
