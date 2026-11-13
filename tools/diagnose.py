"""Diagnostico PC <-> ESP32-C3 (nao precisa de REPL a funcionar).

Fecha o Thonny e qualquer monitor serial antes de correr:

  py -3.14 tools/diagnose.py
  py -3.14 tools/diagnose.py --port COM6
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time

PY = sys.executable


def section(title: str) -> None:
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


def run(args: list[str], timeout: int = 25) -> tuple[int, str]:
    try:
        p = subprocess.run(
            args,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout,
        )
        out = (p.stdout or "") + (p.stderr or "")
        return p.returncode, out
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or "") + (e.stderr or "")
        if isinstance(out, bytes):
            out = out.decode("utf-8", "replace")
        return 124, out + "\n[TIMEOUT]\n"
    except FileNotFoundError as e:
        return 127, str(e)


def test_ports() -> str | None:
    section("1) Portas USB/COM")
    code, out = run([PY, "-m", "mpremote", "connect", "list"])
    print(out.strip() or "(sem saida)")
    port = None
    for line in out.splitlines():
        if "303a:1001" in line.lower():
            port = line.split()[0]
            break
        parts = line.split()
        if parts and parts[0].upper().startswith("COM") and parts[0].upper() != "COM1":
            port = parts[0]
    if port:
        print(">> Porta Espressif USB-JTAG:", port)
        print(">> Interpretacao: o PC VE o chip (USB nao esta totalmente morto).")
    else:
        print(">> Sem VID 303A. Cabo, driver, ou a placa nao enumera.")
    return port


def test_port_free(port: str) -> bool:
    section("2) Porta livre?")
    try:
        import serial
    except ImportError:
        print("pyserial em falta")
        return False
    try:
        s = serial.Serial(port, 115200, timeout=0.2, exclusive=True)
        s.close()
        print(">> COM livre. Bom para o resto dos testes.")
        return True
    except Exception as e:
        print(">> COM ocupada ou falhou:", e)
        print(">> Fecha o Thonny (Shell + Install MicroPython) e tenta outra vez.")
        return False


def test_bootloader(port: str) -> bool:
    section("3) Bootloader (esptool) — modo DOWNLOAD")
    print("Se isto passar, CPU + USB-JTAG + flash respondem no bootloader.")
    code, out = run(
        [PY, "-m", "esptool", "--chip", "esp32c3", "--port", port, "--after", "hard-reset", "chip-id"],
        timeout=30,
    )
    print(out.strip() or "(sem saida)")
    ok = code == 0 and "ESP32-C3" in out
    if ok:
        print(">> PASS: modo download OK. Curto total em USB/3V3 e pouco provavel.")
        if "revision v0.4" in out or "revision 0.4" in out:
            print(">> ATENCAO: silicio rev. 0.4. MicroPython GENERIC_C3 atual e para rev. 3+.")
            print("   Isto sozinho explica REPL mudo mesmo com flash 'sucesso'.")
    else:
        print(">> FAIL: bootloader nao falou. Sem USB estavel, ou chip preso, ou curto pesado.")
    return ok


def test_repl_bytes(port: str) -> bool:
    section("4) Consola apos reset (modo RUN / MicroPython)")
    import serial

    try:
        s = serial.Serial()
        s.port = port
        s.baudrate = 115200
        s.timeout = 0.2
        s.dsrdtr = False
        s.rtscts = False
        s.dtr = False
        s.rts = False
        s.open()
    except Exception as e:
        print(">> Nao abriu serial:", e)
        return False

    # Liberta EN/BOOT (USB-JTAG: DTR~GPIO9, RTS~EN)
    try:
        s.rts = True
        time.sleep(0.05)
        s.rts = False
        s.dtr = False
        time.sleep(0.3)
    except Exception:
        pass

    buf = b""
    t0 = time.time()
    while time.time() - t0 < 3.0:
        buf += s.read(2048)

    s.write(b"\r\x03\x03")
    time.sleep(0.4)
    buf += s.read(4096)

    s.write(b"\r\x01")
    time.sleep(0.6)
    raw = s.read(4096)
    buf += raw
    s.close()

    print("bytes lidos:", len(buf))
    print("amostra:", repr(buf[:400]) if buf else "(vazio)")
    text = buf.decode("utf-8", "replace")
    if "MicroPython" in text or ">>>" in text or "raw REPL" in text:
        print(">> PASS: ha REPL / banner. O problema nao e firmware mudo.")
        return True
    if buf:
        print(">> PARCIAL: ha lixo/log mas nao REPL. Firmware a crashar ou baud/USB.")
        return False
    print(">> FAIL: zero bytes em modo RUN. Firmware nao arranca, ou DTR/RTS a prender BOOT/EN.")
    return False


def test_mpremote(port: str) -> bool:
    section("5) mpremote raw REPL")
    code, out = run([PY, "-m", "mpremote", "connect", port, "exec", "print(123)"], timeout=20)
    print(out.strip() or "(sem saida)")
    if code == 0 and "123" in out:
        print(">> PASS: da para enviar codigo. Upload deve funcionar.")
        return True
    print(">> FAIL: mpremote nao entra em raw REPL (igual ao Thonny sem Shell).")
    return False


def print_verdict(boot_ok: bool, repl_ok: bool, mp_ok: bool) -> None:
    section("Veredicto automatico")
    if boot_ok and not repl_ok:
        print("Cenario mais provavel: HARDWARE USB OK + firmware NAO corre em modo normal.")
        print("Causas tipicas, por ordem:")
        print("  1) ESP32-C3 rev 0.4 com bin GENERIC_C3 novo (rev 3+).")
        print("  2) EN ou GPIO9 (BOOT) preso (cola, solda, DTR do PC).")
        print("  3) Curto leve em GPIO que deixa o bootloader vivo mas trava o app.")
        print("  4) Tensao da 18650 no pino 3V3 (4.2 V) a corromper o arranque.")
        print()
        print("Proximo: testes fisicos em docs/DIAGNOSTICS.md (tu com o multimetro).")
    elif not boot_ok:
        print("Cenario: USB-JTAG/bootloader falhou. Cabo, Thonny a ocupar COM,")
        print("ou curto/alimentacao a impedir o chip de enumerar.")
    elif mp_ok:
        print("REPL OK. Podemos enviar boot.py/main.py. O problema anterior era a porta ocupada")
        print("ou o firmware antigo.")
    else:
        print("Bootloader OK, REPL incerto. Segue o roteiro em docs/DIAGNOSTICS.md.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnostico CSI ESP32-C3")
    parser.add_argument("--port", default=None)
    ns = parser.parse_args()
    print("CSI diagnose — fecha Thonny antes disto.")
    port = ns.port or test_ports()
    if not ns.port:
        pass
    else:
        section("1) Porta forçada")
        print(ns.port)
        port = ns.port
    if not port:
        print_verdict(False, False, False)
        return 2
    free = test_port_free(port)
    if not free:
        print_verdict(False, False, False)
        return 3
    boot_ok = test_bootloader(port)
    repl_ok = test_repl_bytes(port) if boot_ok else False
    mp_ok = test_mpremote(port) if repl_ok else False
    if boot_ok and not repl_ok:
        test_mpremote(port)
    print_verdict(boot_ok, repl_ok, mp_ok)
    return 0 if mp_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
