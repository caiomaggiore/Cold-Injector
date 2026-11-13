import os
from time import sleep_ms, ticks_diff, ticks_ms

from config import Config
from controller import Controller
from hardware import Hardware
from pins import GPIO_TEMP
from web_server import WebServer


def _wifi_on_this_board():
    # Nesta ESP32 padrão, com o MicroPython gravado pelo Thonny (1.25),
    # WLAN.active(True) reinicia o chip (SW_CPU_RESET) e o teste morre.
    # C3 e C6 seguem com o AP.
    try:
        name = os.uname().machine.upper()
    except AttributeError:
        return True
    return ("C3" in name) or ("C6" in name)

print("Cold Start Injector")
print(
    "TEMP GPIO%d: o pino so aceita ate 3.3 V. "
    "Medir o fio com o multimetro e a ESP desligada desse fio. "
    "5 V ou 12 V queimam o GPIO. Esta leitura satura em 3.3 V e nao mostra o excesso."
    % GPIO_TEMP
)

cfg = Config()
hw = Hardware()
ctl = Controller(hw, cfg)
web = WebServer(ctl, cfg)
if _wifi_on_this_board():
    web.start()
else:
    print("wifi AP desligado nesta ESP32 de teste")
ctl._log()

temp_at = ticks_ms()

while True:
    ctl.tick()
    hw.pwm_tick()
    web.poll()
    now = ticks_ms()
    if ticks_diff(now, temp_at) >= 1000:
        temp_at = now
        raw, volts = hw.read_temp()
        print("temp gpio=%d raw=%d pin_V=%.2f" % (GPIO_TEMP, raw, volts))
    sleep_ms(2)
