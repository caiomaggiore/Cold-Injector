from machine import ADC, Pin
from time import ticks_diff, ticks_ms

from pins import (
    DEBOUNCE_MS,
    GPIO_MOSFET_PWM,
    GPIO_POST_KEY,
    GPIO_START_BUTTON,
    GPIO_TEMP,
)

# Periodo lento: modulo MOSFET com opto nao segue 1 kHz (fica 100% no gate).
PWM_PERIOD_MS = 20


def signal_present(pin):
    """Opto para GND: nivel fisico 0 = sinal de 12 V presente."""
    return pin.value() == 0


class Hardware:
    def __init__(self):
        self._pin = Pin(GPIO_MOSFET_PWM, Pin.OUT, value=0)
        self._pwm_percent = 0
        self._on_ms = 0
        self._cycle_t = ticks_ms()
        self._post = Pin(GPIO_POST_KEY, Pin.IN, Pin.PULL_UP)
        self._start = Pin(GPIO_START_BUTTON, Pin.IN, Pin.PULL_UP)
        now = ticks_ms()
        self.post_key = signal_present(self._post)
        self.start = signal_present(self._start)
        self._post_raw = self.post_key
        self._start_raw = self.start
        self._post_at = now
        self._start_at = now
        self._temp = None
        try:
            self._temp = ADC(Pin(GPIO_TEMP))
            self._temp.atten(ADC.ATTN_11DB)
        except Exception as exc:
            print("temp ADC indisponivel", exc)

    def set_pwm_percent(self, pct):
        pct = max(0, min(100, int(pct)))
        self._pwm_percent = pct
        self._on_ms = PWM_PERIOD_MS * pct // 100
        if pct <= 0:
            self._pin.value(0)
        elif pct >= 100:
            self._pin.value(1)

    def pwm_off(self):
        self.set_pwm_percent(0)

    def pwm_tick(self):
        if self._pwm_percent <= 0:
            self._pin.value(0)
            return
        if self._pwm_percent >= 100:
            self._pin.value(1)
            return
        now = ticks_ms()
        elapsed = ticks_diff(now, self._cycle_t)
        if elapsed >= PWM_PERIOD_MS:
            self._cycle_t = now
            elapsed = 0
        self._pin.value(1 if elapsed < self._on_ms else 0)

    def read_temp(self):
        """Contagens 0..65535 e volts estimados no pino. Fundo de escala ~3,3 V.

        Satura em ~3,3 V: nao serve para saber se o fio da moto tem 5 V ou 12 V.
        """
        if self._temp is None:
            return 0, 0.0
        raw = self._temp.read_u16()
        return raw, raw * 3.3 / 65535

    def poll(self):
        now = ticks_ms()
        changed = False
        changed = self._debounce_pin(
            now,
            signal_present(self._post),
            "_post_raw",
            "_post_at",
            "post_key",
        ) or changed
        changed = self._debounce_pin(
            now,
            signal_present(self._start),
            "_start_raw",
            "_start_at",
            "start",
        ) or changed
        return changed

    def _debounce_pin(self, now, raw, raw_attr, time_attr, stable_attr):
        if raw != getattr(self, raw_attr):
            setattr(self, raw_attr, raw)
            setattr(self, time_attr, now)
            return False
        if raw != getattr(self, stable_attr) and ticks_diff(now, getattr(self, time_attr)) >= DEBOUNCE_MS:
            setattr(self, stable_attr, raw)
            return True
        return False
