from time import ticks_diff, ticks_ms

STANDBY = "STANDBY"
WAIT_START = "WAIT_START"
INJECTION_DELAY = "INJECTION_DELAY"
INJECTING = "INJECTING"
LOCKOUT = "LOCKOUT"

WATCHDOG_EXTRA_MS = 200


class Controller:
    def __init__(self, hw, cfg):
        self.hw = hw
        self.cfg = cfg
        self.state = STANDBY
        self._start_prev = hw.start
        self._post_prev = hw.post_key
        self._mode_prev = cfg.trigger_mode
        self._t0 = 0
        self.pwm_out = 0
        self._web_fire = False

    def request_start(self):
        self._web_fire = True

    def display_state(self):
        if self.state == STANDBY:
            return "Standby"
        if self.state == INJECTING:
            return "Injetando"
        if self.state == INJECTION_DELAY:
            if self.cfg.trigger_mode == "post_key":
                return "Moto Ligada"
            return "Partida Acionada"
        if self.state == LOCKOUT and self.hw.start:
            return "Partida Acionada"
        return "Moto Ligada"

    def status(self):
        return {
            "state": self.display_state(),
            "state_code": self.state,
            "post_key": self.hw.post_key,
            "start": self.hw.start,
            "pwm": self.pwm_out,
            "enabled": self.cfg.enabled,
            "delay_ms": self.cfg.delay_ms,
            "inject_ms": self.cfg.inject_ms,
            "pwm_percent": self.cfg.pwm_percent,
            "trigger_mode": self.cfg.trigger_mode,
        }

    def _log(self):
        print(
            "state=%s post=%d start=%d pwm=%d en=%d mode=%s"
            % (
                self.display_state(),
                1 if self.hw.post_key else 0,
                1 if self.hw.start else 0,
                self.pwm_out,
                1 if self.cfg.enabled else 0,
                self.cfg.trigger_mode,
            )
        )

    def _set_state(self, state):
        if state == self.state:
            return
        self.state = state
        self._log()

    def _pwm(self, pct):
        self.pwm_out = pct
        self.hw.set_pwm_percent(pct)

    def _off(self):
        self._pwm(0)

    def _begin_inject(self, now):
        self._t0 = now
        self._pwm(self.cfg.pwm_percent)
        self._set_state(INJECTING)

    def _arm_delay_or_inject(self, now):
        self._t0 = now
        if self.cfg.delay_ms <= 0:
            self._begin_inject(now)
        else:
            self._off()
            self._set_state(INJECTION_DELAY)

    def _remember_inputs(self):
        self._start_prev = self.hw.start
        self._post_prev = self.hw.post_key
        self._mode_prev = self.cfg.trigger_mode

    def tick(self):
        self.hw.poll()
        now = ticks_ms()
        web_fire = self._web_fire
        self._web_fire = False
        post_edge = (not self._post_prev) and self.hw.post_key
        mode_changed = self.cfg.trigger_mode != self._mode_prev

        if not self.cfg.enabled:
            self._off()
            self._set_state(STANDBY)
            self._remember_inputs()
            return

        if not self.hw.post_key:
            self._off()
            self._set_state(STANDBY)
            self._remember_inputs()
            return

        if web_fire:
            self._arm_delay_or_inject(now)
            self._remember_inputs()
            return

        if mode_changed:
            self._off()
            if self.cfg.trigger_mode == "post_key":
                self._set_state(LOCKOUT)
            else:
                self._set_state(WAIT_START)
            self._remember_inputs()
            return

        if self.cfg.trigger_mode == "post_key":
            self._tick_post_key(now, post_edge)
        else:
            self._tick_start(now)
        self._remember_inputs()

    def _tick_post_key(self, now, post_edge):
        if self.state == STANDBY:
            if post_edge:
                self._arm_delay_or_inject(now)
            else:
                self._set_state(LOCKOUT)
            return
        if self.state == WAIT_START:
            if post_edge:
                self._arm_delay_or_inject(now)
            else:
                self._set_state(LOCKOUT)
            return
        if self.state == INJECTION_DELAY:
            if ticks_diff(now, self._t0) >= self.cfg.delay_ms:
                self._begin_inject(now)
        elif self.state == INJECTING:
            self._tick_injecting(now)
        elif self.state == LOCKOUT:
            pass

    def _tick_start(self, now):
        start_edge = (not self._start_prev) and self.hw.start
        if self.state == STANDBY:
            self._set_state(WAIT_START)
        if self.state == WAIT_START:
            if start_edge:
                self._arm_delay_or_inject(now)
        elif self.state == INJECTION_DELAY:
            if ticks_diff(now, self._t0) >= self.cfg.delay_ms:
                self._begin_inject(now)
        elif self.state == INJECTING:
            self._tick_injecting(now)
        elif self.state == LOCKOUT:
            if not self.hw.start:
                self._set_state(WAIT_START)

    def _tick_injecting(self, now):
        limit = min(self.cfg.inject_ms, self.cfg.max_inject_ms)
        elapsed = ticks_diff(now, self._t0)
        if elapsed >= limit or elapsed >= (self.cfg.max_inject_ms + WATCHDOG_EXTRA_MS):
            self._off()
            self._set_state(LOCKOUT)
