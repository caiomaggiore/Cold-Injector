# Ligar o ESP32-C3 e enviar MicroPython (Cursor)

Tudo corre no **terminal integrado do Cursor** (PowerShell). Não é preciso Thonny nem PlatformIO para o fluxo normal.

Há **dois passos diferentes**:

1. **Uma vez:** gravar o interpretador MicroPython na flash (`esptool`).
2. **Sempre:** copiar os `.py` do projeto para a placa (`mpremote`).

## 0. PC — Python e ferramentas

No Windows, Python 3 no PATH. Depois, na pasta do projeto:

```powershell
pip install esptool mpremote
```

Ou:

```powershell
pip install -r requirements-dev.txt
```

## 1. Descobrir a porta COM

Liga a **XIAO ESP32-C6** por USB-C ao PC.

```powershell
mpremote connect list
```

Ou:

```powershell
Get-PnpDevice -Class Ports | Where-Object { $_.Status -eq 'OK' } | Format-Table FriendlyName
```

Anota a porta (`COM3`, `COM5`, …). Nos comandos abaixo usa a tua; o exemplo é `COM5`.

A XIAO C6 usa **USB-Serial/JTAG**. Se a porta não aparecer: cabo de dados, ou fecha o Thonny.

## 2. Primeira vez — gravar o firmware MicroPython

Isto **apaga** o que estiver na flash (Arduino antigo, sketches, etc.).

1. Descarrega o `.bin` oficial **ESP32-C3** (USB serial/JTAG ligado):  
   [https://micropython.org/download/ESP32_GENERIC_C3/](https://micropython.org/download/ESP32_GENERIC_C3/)  
   Usa a versão **stable** mais recente (não preview). Guarda o ficheiro, por exemplo em `firmware\ESP32_GENERIC_C3.bin`.

2. Entra em **bootloader** (Super Mini):
   - Mantém **BOOT** premido
   - Toca em **RST** (ou desliga/liga o USB ainda com BOOT premido)
   - Solta **BOOT**
   - A porta COM pode mudar; volta a listar se falhar

3. Apaga e grava (ajusta `COM5` e o nome do `.bin`):

```powershell
python -m esptool --chip esp32c3 --port COM5 erase_flash
python -m esptool --chip esp32c3 --port COM5 --baud 460800 write_flash -z 0x0 firmware\ESP32_GENERIC_C3.bin
```

4. RST ou desliga/liga o USB.

5. Abre o REPL:

```powershell
mpremote connect COM5
```

Deves ver `>>>`. Ctrl+D faz soft reboot. Para sair: Ctrl+] ou desligar o terminal.

Neste PC (Python 3.14, XIAO ESP32-C6 em COM7):

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe" -m mpremote connect COM7
& "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe" tools\esp.py monitor --port COM7
& "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe" tools\esp.py reboot --port COM7
& "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe" tools\esp.py upload --port COM7
```

### Encerrar a porta ou reiniciar

| Onde | Ação | Como |
|---|---|---|
| Terminal `mpremote` | Fechar comunicação | **Ctrl+X** ou **Ctrl+]** |
| Cursor | Fechar comunicação | fechar esse terminal |
| REPL / loop da app | Soft reboot | escrever `reboot` e Enter |
| Porta livre | Soft reboot pelo PC | `tools\esp.py reboot` (equivale a `mpremote reset`) |
| REPL clássico | Soft reboot | **Ctrl+D** (só com `>>>`, não no loop da Fase 1) |

A ESP32 **não** fecha o USB sozinha. `disconnect` no PC é largar o COM. `reboot` reinicia o chip; a sessão serial pode cair e voltar.

Se `mpremote` disser que a porta está ocupada, fecha o outro Serial primeiro.

## 3. Enviar a aplicação (o dia-a-dia)

Na raiz do repositório (`Cold Start Injector`):

```powershell
# Copia os .py para a flash e reinicia
mpremote connect COM5 fs cp boot.py :boot.py
mpremote connect COM5 fs cp main.py :main.py
mpremote connect COM5 fs cp pins.py :pins.py
mpremote connect COM5 reset
```

Vários ficheiros de uma vez (quando existirem):

```powershell
mpremote connect COM5 fs cp boot.py main.py pins.py hardware.py :
mpremote connect COM5 reset
```

Ver o que está na placa:

```powershell
mpremote connect COM5 fs ls
```

Ver prints de `boot.py` / `main.py` (REPL após reset):

```powershell
mpremote connect COM5
```

Correr um ficheiro **sem** gravar na flash (teste rápido):

```powershell
mpremote connect COM5 run main.py
```

`run` não substitui o `main.py` permanente; para o comportamento no próximo power-on usa `fs cp`.

Atalho se só houver **uma** placa USB:

```powershell
mpremote fs cp boot.py main.py pins.py :
mpremote reset
```

## 4. Ordem no ESP32 (importante)

Em cada reset o MicroPython faz:

1. `boot.py` — **aqui** o GPIO 4 vai a OFF, antes de mais nada  
2. `main.py` — aplicação  

Nunca colocar PWM ativo em `boot.py`.

## 5. Problemas frequentes

| Sintoma | O quê tentar |
|---|---|
| Porta não existe | Cabo de dados; outra USB; listar COM de novo |
| `could not open port` | Outro programa a usar o Serial; fecha e tenta |
| Flash falha / timeout | BOOT+RST outra vez; baud 115200 em vez de 460800 |
| REPL lixo / não entra | Firmware C3 USB; RST após gravar |
| Código antigo depois do cp | Falta `reset`; ou editaste no PC e não copiaste |
| MOSFET liga no boot | Falha da Fase 0 — `boot.py` tem de pôr GPIO 4 a 0 **primeiro** |

## 6. O que não usar neste projeto

- PlatformIO / Arduino IDE como fluxo principal  
- `ampy` (preferir `mpremote`)  
- Gravar o `.bin` MicroPython em **todo** o upload — só na instalação ou se a flash corromper  

O Cursor **não** tem um botão “Upload ESP”. O fluxo é: guardar o `.py` → terminal `mpremote fs cp` → `reset`.
