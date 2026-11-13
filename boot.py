from machine import Pin

from pins import GPIO_MOSFET_PWM, GPIO_POST_KEY, GPIO_START_BUTTON

Pin(GPIO_MOSFET_PWM, Pin.OUT, value=0)
Pin(GPIO_POST_KEY, Pin.IN, Pin.PULL_UP)
Pin(GPIO_START_BUTTON, Pin.IN, Pin.PULL_UP)
print("CSI boot")
