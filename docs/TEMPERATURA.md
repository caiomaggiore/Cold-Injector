# Temperatura do motor — resumo para o outro PC e para a mecânica

Este arquivo é a fonte da alteração de temperatura. O chat não viaja com o projeto; este documento sim.

Hardware já montado: [HARDWARE.md](HARDWARE.md). Arquitetura: [ARCHITECTURE.md](ARCHITECTURE.md).

## O que o produto já faz

Partida a frio no **Seeed XIAO ESP32-C6** (MicroPython). Três fios na placa:

| Função | Pad XIAO | GPIO |
|---|---|---|
| Pós-Chave (opto, 12 V isolado) | D0 | 0 |
| Partida (opto, 12 V isolado) | D1 | 1 |
| PWM bomba + válvula | D2 | 2 |

Os 12 V de chave e de partida **não entram no chip**. Passam por opto PC817. O MOSFET de potência usa o +12 V e o GND da moto no lado da carga. A lógica fica em 3,3 V.

A temperatura **ainda não entra** na máquina de estados. Nesta etapa só se descobre o tipo de sinal e se deixa o pino e o circuito de proteção definidos. A injeção continua igual.

## Resposta direta: o GND da moto queima a ESP32?

O GND da moto **não é 12 V**. O GND do chassi é **0 V**. Os 12 V (na prática cerca de 11 V parado e até ~14,5 V com o motor a carregar) estão no positivo da bateria, em relação a esse GND.

O que queima o pino é o **fio do sinal**, se ele for ligado direto num GPIO ou num ADC.

ESP32, ESP32-C3 e ESP32-C6 aceitam no máximo cerca de **3,6 V** no pino. Não são tolerantes a 5 V. Um fio que esteja em 5 V (pull-up da ECU) ou em 12 V (alimentação, ou sensor antigo em série com o painel) destrói o pino e pode levar o chip junto. Pico de ignição no mesmo fio também destrói, mesmo que o multímetro mostre “só 2 V” em DC.

Não é obrigatório um sensor só da ESP32. Também não se liga o sensor original direto no pino. O produto, em moto e em carro, usa um **front-end** que aceita sinal automotivo (0 a 16 V) e só entrega 0 a 3,3 V ao ADC. O chip continua em 3,3 V. O que deixa de estar limitado a 3,3–5 V é a **entrada do produto**, não o pino do microcontrolador.

Sensor NTC dedicado (10 kΩ, alimentado pelo 3,3 V da própria placa) serve como plano B: quando o fio original for digital, for barramento, ou quando “ouvir” o fio alterar a leitura da ECU. Não é o caminho principal.

## O que a mecânica provavelmente tem no fio

Quase todo sensor de temperatura de motor (moto e carro) é um **NTC**: a resistência **cai** quando esquenta. A ECU põe um pull-up (muito comum em 5 V, às vezes outra tensão) e lê a tensão no meio do divisor. O outro lado do sensor é GND da ECU ou o próprio chassi.

| O que o multímetro mostrar | O que é | O que fazer |
|---|---|---|
| Ohms entre os fios, chave desligada, valor que cai ao esquentar | NTC | Dá para usar o fio, só escutando, com o front-end |
| Tensão DC contínua, chave ligada, que muda devagar ao esquentar (faixa típica 0,2 a 5 V) | Sinal analógico da ECU | Mesmo caso. Não colocar outro pull-up em paralelo |
| Tensão perto de 12 V, ou que acompanha a bateria | Alimentação, ou sensor em série com marcador antigo | Front-end obrigatório. Nunca no pino cru |
| 0 V firme, 5 V firme, ou pulso / frequência | Digital, ou fio errado | Não forçar no ADC. Aí sim um NTC dedicado |
| Resistência infinita nos dois sentidos | Fio errado, sensor aberto, ou não é NTC de 2 fios | Parar e identificar o conector antes de ligar qualquer coisa |

Escutar o fio da ECU é leitura de alta impedância: **não** alimentar esse sensor com o 3,3 V da ESP32 ao mesmo tempo que a ECU está ligada. Dois pull-ups brigam e a moto passa a ver temperatura errada.

## Front-end único (moto e carro)

Colocar isto **entre o fio do sensor e o pino**. A ESP32 só vê o nó do meio.

```
fio do sensor (0 a 16 V em relação ao GND do chassi)
        |
      470 kΩ
        |
        +------ nó do ADC ------ 1 kΩ ------ pino ADC da ESP32
        |                          |
      100 kΩ                     100 nF
        |                          |
       GND                        GND
        |
   BAT54S: anodo no nó do ADC, catodo no 3V3 da ESP32
```

Contas, de propósito folgadas para 16 V na entrada:

| Tensão no fio | Tensão no nó do ADC |
|---|---|
| 5 V | ~0,9 V |
| 12 V | ~2,1 V |
| 14,5 V (motor carregando) | ~2,5 V |
| 16 V | ~2,8 V |

O BAT54S segura pico acima de 3,3 V. O 100 nF segura o ruído da ignição e dá carga para o ADC amostrar, porque o divisor é de alta impedância e quase não altera a leitura da ECU.

GND do chassi e GND da ESP32 precisam ser o **mesmo ponto**. Sem esse elo a leitura não tem referência. Um elo só, curto. Se o módulo MOSFET já junta o GND da moto ao GND da placa, usar esse mesmo ponto em vez de um segundo fio longo.

Na visita à oficina a ESP32 **fica desligada do sensor** até o multímetro ter medido o fio. O notebook, se for usado depois, fica na bateria (fonte desligada da tomada), para não criar caminho entre o terra do PC e o chassi.

Peças, nenhuma delas é “sensor de 3,3 V”: resistor 470 kΩ, resistor 100 kΩ, resistor 1 kΩ, capacitor cerâmico 100 nF, diodo BAT54S. Um NTC 10 kΩ 3950 só se o teste abaixo cair na linha “digital / fio errado”.

## Teste no serial (já no código, placa DevKit)

A ESP ligada neste PC é a padrão, ponte CP210x na **COM4**. O `pins.py` escolhe os GPIO pelo chip: nesta placa a temperatura é o **GPIO34**. Na XIAO C6 continua D0/D1/D2 e o pad MTCK.

O `main.py` imprime, uma vez por segundo:

```
temp gpio=34 raw=0 pin_V=0.00
```

`pin_V` é a tensão **no pino**, com fundo de escala ~3,3 V. Se o fio tiver 5 V ou 12 V, o número encosta em 3,3 e o GPIO queima na mesma hora. Essa linha **não** serve para decidir se o sinal passa de 5 V. Quem decide é o multímetro, com a ESP **fora** desse fio. Só encostar o fio no GPIO34 se essa medição ficou abaixo de 3,3 V. Entre 3,3 V e 5 V o pino também queima.

Sem nada ligado no GPIO34 o valor flutua. Isso é pino solto, não é temperatura.

Nesta ESP32 de teste o ponto de acesso Wi-Fi fica desligado. Com o MicroPython 1.25 que o Thonny gravou, `WLAN.active(True)` reinicia o chip em loop e a leitura não chega a aparecer. O log do GPIO34 sai pela USB (115200). Na XIAO C6 o AP continua ligado.

## Qual pino em cada placa

O ADC só existe em alguns GPIOs. D3 da XIAO **não** é analógico (é GPIO21).

| Placa | Pino de temperatura | Onde está no cobre | Porquê este |
|---|---|---|---|
| ESP32 DevKit padrão (o de teste, WROOM-32) | **GPIO34** | Pino marcado `34` / `ADC1_CH6` | Só entrada, ADC1 (funciona com Wi-Fi). Não existe este número na C3 nem na C6 |
| ESP32-C3 Super Mini | **GPIO3** | Seda `3` | ADC1_CH3. O GPIO4 fica livre para o PWM antigo |
| ESP32-C6 Super Mini | **GPIO3** | Seda `3` | ADC1_CH3. GPIO4 e GPIO5 são strapping |
| XIAO ESP32-C6 (placa do produto) | **GPIO6** | Pad de baixo **MTCK** | Único ADC livre no header já está ocupado (D0, D1, D2). GPIO3 na XIAO alimenta a chave da antena e **não** está no header |

Na XIAO, não soldar o sensor em D3–D10: esses pads não têm ADC. Não usar o GPIO3 da XIAO.

Nas Mini C3 e Mini C6 a seda `3` é o GPIO3. O número coincide. O pad da XIAO não coincide: lá a temperatura vai no **MTCK**.

Enquanto o sinal não estiver classificado, `pins.py` **não muda**. Continua D0/D1/D2 da XIAO. O GPIO34 (ou o 3, ou o MTCK) só entra no código depois do teste da oficina e com o front-end no meio.

### Não gravar o `pins.py` atual na ESP32 padrão

No DevKit clássico, GPIO0 é boot, GPIO1 é o TX da serial e GPIO2 é strapping. O firmware de hoje usa exatamente 0, 1 e 2. Copiar isso para a ESP32 padrão derruba o REPL e pode impedir o boot.

Quando for a hora de limpar essa placa de teste, o interpretador é outro e o endereço de gravação também:

| Placa | Chip no esptool | Firmware MicroPython | Endereço |
|---|---|---|---|
| DevKit ESP32 padrão | `esp32` | `ESP32_GENERIC` | **0x1000** |
| Super Mini C3 | `esp32c3` | `ESP32_GENERIC_C3` | 0x0 |
| Super Mini C6 / XIAO C6 | `esp32c6` | `ESP32_GENERIC_C6` ou `SEEED_XIAO_ESP32C6` | 0x0 |

Exemplo só para a ESP32 padrão (ajustar a porta COM):

```powershell
python -m esptool --chip esp32 --port COM5 erase_flash
python -m esptool --chip esp32 --port COM5 --baud 460800 write_flash -z 0x1000 firmware\ESP32_GENERIC.bin
```

O `.bin` da ESP32 padrão ainda não está em `firmware\` (lá só há builds C3). Baixar o stable em [https://micropython.org/download/ESP32_GENERIC/](https://micropython.org/download/ESP32_GENERIC/). Não reutilizar o bin da C3 nem o da C6.

Mapa se um dia o sistema completo for para o DevKit (não é o da XIAO):

| Função | DevKit |
|---|---|
| Pós-Chave | GPIO25 |
| Partida | GPIO26 |
| PWM | GPIO27 |
| Temperatura | GPIO34 |

## Teste na mecânica (só multímetro)

A ESP32 não entra neste roteiro. Chave desligada no começo. Não furar fio: usar o conector do sensor ou um backprobe.

Anotar na ficha do fim. Uma linha por medição, com o motor na temperatura em que estava.

1. Achar o sensor de temperatura do motor (cabeçote, coolant, ou o que o módulo da moto usa). Contar os fios. Foto do conector.
2. Chave **off**, conector **encaixado**. Resistência entre cada fio e o chassi. O fio de terra costuma dar perto de 0 Ω.
3. Chave **off**, conector **solto do lado da ECU** (sensor ainda no motor). Resistência entre os pinos do sensor. Anotar o valor e se o motor está frio ou quente. Se der para esperar esfriar ou comparar com o motor já quente, anotar os dois. NTC frio fica **maior** em ohms do que NTC quente. Ordem de grandeza típica: alguns kΩ a ~25 °C, dezenas de kΩ bem frio, centenas de ohms bem quente. Se não for esta família de números, não assumir NTC.
4. Conector de volta no lugar. Chave **on**, motor **parado**. Tensão DC de cada fio contra o chassi. Anotar o máximo.
5. Se a tensão do passo 4 for estável e abaixo de 16 V, observar por um minuto. Se não se mexe, é nível fixo (alimentação ou referência), não temperatura.
6. Motor a aquecer, mesma ponta de prova. Anotar tensão com o motor frio e de novo morno/quente. NTC com pull-up: a tensão **desce** conforme esquenta. Se subir, anotar mesmo assim.
7. Se a tensão ficar parada, passar o multímetro para Hz no mesmo fio, motor ligado. Pulso rápido = não é ADC lento.
8. Tensão máxima vista no fio. Se passou de 3,3 V em qualquer momento, o pino da ESP32 só pode ver esse fio **depois** do divisor. Se passou de 16 V, parar e rever o fio (pode ser o positivo da bateria).

Critério para a próxima sessão de código: a ficha preenchida, mais a frase “o nó do divisor, medido no multímetro, ficou abaixo de 3,0 V com o fio ligado”. Aí sim um script só de log do ADC, sem mexer no PWM.

## Ficha para preencher na oficina

```
Moto / carro:
Sensor (onde está) e quantos fios:
Motor frio ou quente no início:

Ohms fio A contra chassi (chave off):
Ohms fio B contra chassi (chave off):
Ohms do sensor sozinho, frio:
Ohms do sensor sozinho, quente:

Tensão fio sinal contra chassi, chave on, motor parado:
Tensão com motor frio:
Tensão com motor quente:
Máxima tensão vista:
Tem frequência? (Hz ou “não”):

Conclusão (uma): NTC analógico / nível 12 V / digital ou fio errado
```

## O que não fazer com este sinal

- Não ligar o fio do sensor, o +12 V ou o positivo da bobina num GPIO.
- Não usar o PC817 deste sinal. Opto não reproduz tensão analógica.
- Não colocar pull-up da ESP32 no fio que a ECU já está lendo.
- Não cortar injeção com base nesta leitura até haver curva (volts ou ohms → temperatura) desta moto. Leitura crua primeiro.
