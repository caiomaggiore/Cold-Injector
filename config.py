import ujson

PATH = "config.json"
PRESETS_PATH = "presets.json"
WIFI_PATH = "wifi.json"
MAX_PRESETS = 8
NAME_MAX = 20

MAX_INJECT_MS = 5000
DELAY_MS_MAX = 2000
INJECT_MS_MIN = 50

AP_SSID = "Cold-Start-Injector"
DEFAULT_WIFI_PASSWORD = "partidafria"
WIFI_PASS_MIN = 8
WIFI_PASS_MAX = 63

DEFAULTS = {
    "enabled": True,
    "delay_ms": 200,
    "inject_ms": 1500,
    "pwm_percent": 100,
    "trigger_mode": "start",
}


def _clamp(cfg):
    cfg["enabled"] = bool(cfg.get("enabled", True))
    cfg["delay_ms"] = max(0, min(DELAY_MS_MAX, int(cfg.get("delay_ms", 200))))
    inj = max(INJECT_MS_MIN, int(cfg.get("inject_ms", 1500)))
    cfg["inject_ms"] = min(inj, MAX_INJECT_MS)
    cfg["pwm_percent"] = max(0, min(100, int(cfg.get("pwm_percent", 100))))
    mode = cfg.get("trigger_mode", "start")
    if mode not in ("start", "post_key"):
        mode = "start"
    cfg["trigger_mode"] = mode
    cfg["max_inject_ms"] = MAX_INJECT_MS
    return cfg


def wifi_password_ok(pw):
    if pw is None:
        return False
    text = str(pw)
    if len(text) < WIFI_PASS_MIN or len(text) > WIFI_PASS_MAX:
        return False
    for ch in text:
        o = ord(ch)
        if o < 32 or o > 126:
            return False
    return True


class Config:
    def __init__(self):
        self._data = _clamp(dict(DEFAULTS))
        self.wifi_password = DEFAULT_WIFI_PASSWORD
        self.load()
        self._load_wifi()

    def load(self):
        try:
            with open(PATH, "r") as f:
                raw = ujson.loads(f.read())
            merged = dict(DEFAULTS)
            merged.update(raw)
            self._data = _clamp(merged)
        except OSError:
            self._data = _clamp(dict(DEFAULTS))
            self.save()
        except ValueError:
            self._data = _clamp(dict(DEFAULTS))

    def save(self):
        with open(PATH, "w") as f:
            f.write(ujson.dumps(self.as_dict()))

    def as_dict(self):
        return {
            "enabled": self.enabled,
            "delay_ms": self.delay_ms,
            "inject_ms": self.inject_ms,
            "pwm_percent": self.pwm_percent,
            "trigger_mode": self.trigger_mode,
            "max_inject_ms": MAX_INJECT_MS,
        }

    def update(self, patch, persist=True):
        data = self.as_dict()
        for key in ("enabled", "delay_ms", "inject_ms", "pwm_percent", "trigger_mode"):
            if key in patch:
                data[key] = patch[key]
        self._data = _clamp(data)
        if persist:
            self.save()

    def _load_wifi(self):
        try:
            with open(WIFI_PATH, "r") as f:
                raw = ujson.loads(f.read())
            pw = raw.get("password", DEFAULT_WIFI_PASSWORD)
            if wifi_password_ok(pw):
                self.wifi_password = str(pw)
                return
        except (OSError, ValueError):
            pass
        self.wifi_password = DEFAULT_WIFI_PASSWORD
        self._save_wifi()

    def _save_wifi(self):
        with open(WIFI_PATH, "w") as f:
            f.write(ujson.dumps({"password": self.wifi_password}))

    def set_wifi_password(self, pw):
        if not wifi_password_ok(pw):
            return False
        self.wifi_password = str(pw)
        self._save_wifi()
        return True

    @property
    def enabled(self):
        return self._data["enabled"]

    @property
    def delay_ms(self):
        return self._data["delay_ms"]

    @property
    def inject_ms(self):
        return self._data["inject_ms"]

    @property
    def pwm_percent(self):
        return self._data["pwm_percent"]

    @property
    def trigger_mode(self):
        return self._data["trigger_mode"]

    @property
    def max_inject_ms(self):
        return MAX_INJECT_MS

    def _clean_name(self, name):
        raw = str(name).strip()[:NAME_MAX]
        out = []
        for ch in raw:
            if ch.isalnum() or ch in (" ", "-", "_"):
                out.append(ch)
        return "".join(out).strip() or "Preset"

    def _preset_payload(self):
        return {
            "delay_ms": self.delay_ms,
            "inject_ms": self.inject_ms,
            "pwm_percent": self.pwm_percent,
            "trigger_mode": self.trigger_mode,
        }

    def list_presets(self):
        try:
            with open(PRESETS_PATH, "r") as f:
                data = ujson.loads(f.read())
            items = data.get("items", [])
            if not isinstance(items, list):
                return []
            return items
        except (OSError, ValueError):
            return []

    def _write_presets(self, items):
        with open(PRESETS_PATH, "w") as f:
            f.write(ujson.dumps({"items": items}))

    def save_preset(self, name):
        name = self._clean_name(name)
        item = self._preset_payload()
        item["name"] = name
        items = [x for x in self.list_presets() if x.get("name") != name]
        items.insert(0, item)
        items = items[:MAX_PRESETS]
        self._write_presets(items)
        return items

    def load_preset(self, name):
        name = self._clean_name(name)
        for item in self.list_presets():
            if item.get("name") == name:
                self.update(item, persist=True)
                return True
        return False

    def delete_preset(self, name):
        name = self._clean_name(name)
        items = [x for x in self.list_presets() if x.get("name") != name]
        self._write_presets(items)
        return items
