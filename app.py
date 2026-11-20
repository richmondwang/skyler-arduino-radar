"""
Submarine Sonar web server.

Reads "angle,distance" lines from the Arduino (9600 baud), and streams them
to the browser via Server-Sent Events. Serves index.html (the radar UI).

Usage:
    python app.py               # auto-detect Arduino, fall back to demo mode
    python app.py --port COM5   # force a port
    python app.py --demo        # simulated targets, no hardware
"""

import argparse
import json
import math
import os
import random
import threading
import time
import webbrowser

from flask import Flask, Response, send_from_directory

try:
    import serial
    import serial.tools.list_ports
except ImportError:  # pragma: no cover
    serial = None

BAUD = 9600
HTTP_PORT = 5000
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)

# ---------- shared state ----------
_cond = threading.Condition()
_buffer = []          # list of (seq, dict)
_seq = 0
status = {"mode": "starting", "port": None, "message": "Initializing..."}


def publish(event: dict):
    global _seq
    with _cond:
        _seq += 1
        _buffer.append((_seq, event))
        if len(_buffer) > 500:
            del _buffer[: len(_buffer) - 500]
        _cond.notify_all()


def set_status(mode, port=None, message=""):
    status.update(mode=mode, port=port, message=message)
    publish({"type": "status", **status})


# ---------- serial port detection ----------
ARDUINO_HINTS = ("arduino", "ch340", "ch341", "usb-serial", "usb serial",
                 "cp210", "ftdi", "wch", "silicon labs")
ARDUINO_VIDS = {0x2341, 0x2A03, 0x1A86, 0x10C4, 0x0403}


def find_arduino_port():
    if serial is None:
        return None
    ports = list(serial.tools.list_ports.comports())
    for p in ports:
        text = f"{p.description} {p.manufacturer or ''} {p.hwid}".lower()
        if (p.vid in ARDUINO_VIDS) or any(h in text for h in ARDUINO_HINTS):
            return p.device
    # Last resort: any non-Bluetooth COM port
    for p in ports:
        if "bluetooth" not in (p.description or "").lower():
            return p.device
    return None


# ---------- reader threads ----------
def serial_reader(forced_port=None, allow_demo=True):
    demo_started = False
    while True:
        port = forced_port or find_arduino_port()
        if not port:
            if allow_demo and not demo_started:
                print("[sonar] No Arduino found -> DEMO mode (simulated targets). "
                      "Plug in the Uno; it will switch to live automatically.")
                demo_started = True
            run_demo(duration=3.0)  # simulate briefly, then rescan for hardware
            continue
        try:
            print(f"[sonar] Connecting to {port} @ {BAUD} baud...")
            with serial.Serial(port, BAUD, timeout=2) as ser:
                time.sleep(2)  # Uno auto-resets when the port opens
                ser.reset_input_buffer()
                set_status("live", port, f"Connected to {port}")
                print(f"[sonar] LIVE on {port}")
                demo_started = False
                while True:
                    line = ser.readline().decode("ascii", errors="ignore").strip()
                    if not line:
                        continue
                    parts = line.split(",")
                    if len(parts) != 2:
                        continue
                    try:
                        a, d = int(parts[0]), int(float(parts[1]))
                    except ValueError:
                        continue
                    if 0 <= a <= 180:
                        publish({"type": "reading", "angle": a, "distance": d})
        except serial.SerialException as e:
            msg = str(e)
            if "PermissionError" in msg or "Access is denied" in msg:
                msg = f"{port} is busy - close the Arduino IDE Serial Monitor."
            print(f"[sonar] Serial error: {msg}")
            set_status("error", port, msg)
            if not allow_demo:
                time.sleep(2)
            else:
                run_demo(duration=3.0, note=f"{msg} (showing simulated contacts)")


_demo_angle = 0
_demo_dir = 1
_demo_targets = [
    {"angle": 40, "dist": 120, "drift": 0.15},
    {"angle": 100, "dist": 38, "drift": -0.1},
    {"angle": 150, "dist": 15, "drift": 0.05},
]


def run_demo(duration=None, note=None):
    """Simulated sweep; runs forever if duration is None."""
    global _demo_angle, _demo_dir
    message = note or "No Arduino detected - simulated contacts"
    if status.get("mode") != "demo" or status.get("message") != message:
        set_status("demo", None, message)
    end = time.time() + duration if duration else float("inf")
    while time.time() < end:
        for t in _demo_targets:
            t["dist"] += t["drift"] * random.uniform(0.5, 1.5)
            if t["dist"] < 8 or t["dist"] > 180:
                t["drift"] = -t["drift"]
        d = 0
        for t in _demo_targets:
            width = max(4, 300 / max(t["dist"], 1))
            if abs(_demo_angle - t["angle"]) <= width / 2:
                d = int(t["dist"] + random.uniform(-1.5, 1.5))
                break
        publish({"type": "reading", "angle": _demo_angle, "distance": max(d, 0)})
        _demo_angle += _demo_dir
        if _demo_angle >= 180:
            _demo_angle, _demo_dir = 180, -1
        elif _demo_angle <= 0:
            _demo_angle, _demo_dir = 0, 1
        time.sleep(0.025)


# ---------- web routes ----------
@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/stream")
def stream():
    def gen():
        yield f"data: {json.dumps({'type': 'status', **status})}\n\n"
        with _cond:
            last = _seq
        while True:
            with _cond:
                _cond.wait_for(lambda: _seq > last, timeout=15)
                items = [(s, e) for s, e in _buffer if s > last]
            if not items:
                yield ": keepalive\n\n"
                continue
            last = items[-1][0]
            yield "".join(f"data: {json.dumps(e)}\n\n" for _, e in items)

    return Response(gen(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


def main():
    ap = argparse.ArgumentParser(description="Submarine Sonar web server")
    ap.add_argument("--port", help="Serial port, e.g. COM5 (default: auto-detect)")
    ap.add_argument("--demo", action="store_true", help="Simulated data, no hardware")
    ap.add_argument("--no-browser", action="store_true", help="Don't open the browser")
    ap.add_argument("--http-port", type=int, default=HTTP_PORT)
    args = ap.parse_args()

    if args.demo:
        threading.Thread(target=run_demo, daemon=True).start()
    else:
        threading.Thread(target=serial_reader, args=(args.port, args.port is None),
                         daemon=True).start()

    url = f"http://127.0.0.1:{args.http_port}/"
    print(f"[sonar] Website: {url}")
    if not args.no_browser:
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    app.run(host="127.0.0.1", port=args.http_port, threaded=True, debug=False)


if __name__ == "__main__":
    main()
