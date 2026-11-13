"""Comandos no PC para a ESP32-C3 (mpremote).

Exemplos (na raiz do projeto):

  py -3.14 tools/esp.py monitor
  py -3.14 tools/esp.py reboot
  py -3.14 tools/esp.py upload
  py -3.14 tools/esp.py disconnect

Porta: --port COMx, variavel ESP_PORT, ou auto (Espressif USB).
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

MPREMOTE = [sys.executable, "-m", "mpremote"]
UPLOAD_FILES = (
    "boot.py",
    "main.py",
    "pins.py",
    "hardware.py",
    "config.py",
    "controller.py",
    "web_server.py",
)


def run_mpremote(args: list[str]) -> int:
    cmd = MPREMOTE + args
    print(" ".join(cmd))
    return subprocess.call(cmd)


def detect_port() -> str:
    env = os.environ.get("ESP_PORT")
    if env:
        return env
    listing = subprocess.check_output(MPREMOTE + ["connect", "list"], text=True, errors="replace")
    for line in listing.splitlines():
        if "303a:1001" in line.lower():
            return line.split()[0]
        parts = line.split()
        if parts and parts[0].upper().startswith("COM") and parts[0].upper() != "COM1":
            return parts[0]
    return "COM7"


def cmd_list(_: argparse.Namespace) -> int:
    return run_mpremote(["connect", "list"])


def cmd_monitor(ns: argparse.Namespace) -> int:
    port = ns.port or detect_port()
    print("Monitor REPL em %s — sair: Ctrl-x ou Ctrl-]" % port)
    return run_mpremote(["connect", port])


def cmd_reboot(ns: argparse.Namespace) -> int:
    port = ns.port or detect_port()
    print("Soft reboot em %s (a porta nao pode estar noutro programa)" % port)
    return run_mpremote(["connect", port, "reset"])


def cmd_upload(ns: argparse.Namespace) -> int:
    port = ns.port or detect_port()
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root)
    missing = [name for name in UPLOAD_FILES if not os.path.isfile(name)]
    if missing:
        print("Ficheiros em falta:", ", ".join(missing))
        return 1
    rc = run_mpremote(["connect", port, "fs", "cp", *UPLOAD_FILES, ":"])
    if rc != 0:
        return rc
    return run_mpremote(["connect", port, "reset"])


def cmd_disconnect(_: argparse.Namespace) -> int:
    print("Para encerrar a comunicacao USB:")
    print("  1. No terminal do mpremote/miniterm: Ctrl-x  ou  Ctrl-]")
    print("  2. Ou fecha esse terminal no Cursor")
    print("A ESP32 nao fecha a porta sozinha; o PC e que larga o COM.")
    print("Depois podes: py -3.14 tools/esp.py reboot")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="CSI — monitor, reboot e upload MicroPython")
    sub = parser.add_subparsers(dest="cmd", required=True)
    port_parent = argparse.ArgumentParser(add_help=False)
    port_parent.add_argument("--port", default=None, help="COMx (default: ESP_PORT ou auto)")
    sub.add_parser("list", help="Listar portas")
    sub.add_parser("monitor", help="Abrir REPL (Ctrl-x sai)", parents=[port_parent])
    sub.add_parser("reboot", help="Reiniciar a ESP32", parents=[port_parent])
    sub.add_parser("upload", help="Copiar .py e reset", parents=[port_parent])
    sub.add_parser("disconnect", help="Como largar a porta COM")
    ns = parser.parse_args()
    if not hasattr(ns, "port"):
        ns.port = None
    handlers = {
        "list": cmd_list,
        "monitor": cmd_monitor,
        "reboot": cmd_reboot,
        "upload": cmd_upload,
        "disconnect": cmd_disconnect,
    }
    return handlers[ns.cmd](ns)


if __name__ == "__main__":
    raise SystemExit(main())
