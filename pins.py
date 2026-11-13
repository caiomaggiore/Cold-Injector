import os

# A mesma flash serve as tres placas. O chip escolhe os GPIO no boot.
# XIAO C6: D0/D1/D2 e temperatura no pad MTCK.
# C3 Mini: seda 6, 7, 4 e temperatura na seda 3.
# DevKit ESP32 (CP210x): 25, 26, 27 e temperatura no GPIO34.
try:
    _MACHINE = os.uname().machine.upper()
except AttributeError:
    _MACHINE = ""

if "C3" in _MACHINE:
    GPIO_POST_KEY = 6
    GPIO_START_BUTTON = 7
    GPIO_MOSFET_PWM = 4
    GPIO_TEMP = 3
elif "C6" in _MACHINE:
    GPIO_POST_KEY = 0       # D0
    GPIO_START_BUTTON = 1   # D1
    GPIO_MOSFET_PWM = 2     # D2
    GPIO_TEMP = 6           # pad MTCK, unico ADC livre
else:
    GPIO_POST_KEY = 25
    GPIO_START_BUTTON = 26
    GPIO_MOSFET_PWM = 27
    GPIO_TEMP = 34          # ADC1, so entrada

DEBOUNCE_MS = 30
