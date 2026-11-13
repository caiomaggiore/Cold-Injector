# Cold Start Injector

Partida a frio para moto e carro. O produto roda em **MicroPython** no **Seeed XIAO ESP32-C6**. A bancada de agora é uma **ESP32 padrão** (DevKit com CP210x), usada para medir o sinal de temperatura do motor antes de levar o fio à placa definitiva.

Não há compilação. O interpretador é um `.bin` em `firmware/`. A aplicação são os `.py` da raiz, copiados para a flash com `mpremote`.

## O que já funciona

- Pós-chave e partida entram por opto (o 12 V não chega no GPIO).
- A bomba e a válvula compartilham um PWM. Sem pós-chave, a saída fica em zero.
- A página local existe na XIAO. Nesta ESP32 de teste o Wi-Fi fica desligado: neste MicroPython, ligar o rádio reinicia o chip.
- A temperatura **não** comanda a injeção. O GPIO34 só publica a tensão do pino, uma vez por segundo, para classificar o sensor na oficina.

## Pinos

| Função | XIAO ESP32-C6 | ESP32 DevKit de teste |
|---|---|---|
| Pós-chave | D0 / GPIO0 | GPIO25 |
| Partida | D1 / GPIO1 | GPIO26 |
| PWM | D2 / GPIO2 | GPIO27 |
| Temperatura | pad **MTCK** / GPIO6 | **GPIO34** |

O `pins.py` escolhe a coluna pelo chip. Detalhe do sensor, do divisor e da ficha da mecânica: [docs/TEMPERATURA.md](docs/TEMPERATURA.md).

O pino do microcontrolador aceita no máximo cerca de **3,3 V**. Medir o fio com o multímetro e a ESP fora desse fio. Uma leitura `pin_V` perto de 3,3 não prova que o sinal é seguro: o ADC satura e um fio de 5 V ou 12 V queima o GPIO.

## Documentos

- [Arquitetura](docs/ARCHITECTURE.md)
- [Hardware montado](docs/HARDWARE.md)
- [Máquina de estados](docs/STATE_MACHINE.md)
- [Fases](docs/PHASES.md)
- [Gravar e enviar o código](docs/SETUP.md)
- [Placa sem REPL](docs/DIAGNOSTICS.md)
- [Temperatura e teste na oficina](docs/TEMPERATURA.md)

## No computador

```powershell
pip install -r requirements-dev.txt
```

Fechar o Thonny antes, porque ele segura a porta COM. Na ESP32 padrão a porta vista até aqui foi a **COM4**. Ajuste se o gerenciador de dispositivos mostrar outra.

```powershell
python -m mpremote connect COM4
```

Sair do monitor: **Ctrl+]**. O programa continua na placa. As linhas úteis são:

```
state=Standby post=0 start=0 pwm=0 en=1 mode=start
temp gpio=34 raw=14115 pin_V=0.71
```

`pin_V` com o GPIO34 solto fica pulando. Isso é pino no ar, não é temperatura.
