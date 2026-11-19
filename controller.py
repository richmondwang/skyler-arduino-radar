"""
Arduino joystick -> WASD + Space for Roblox (Windows).

Reads "J,<x>,<y>,<sw>" lines from joystick.ino and holds W/A/S/D down while the
stick is tilted past the deadzone (diagonals hold two keys). Clicking the stick
holds Space. Keys are sent as hardware scan codes through pydirectinput, which
Roblox picks up reliably. Plain virtual-key libraries are often ignored by games.

Usage:  python controller.py            (auto-detect port)
        python controller.py COM3       (force a port)
Stop with Ctrl+C. All keys are released on exit.
"""

import sys
import time

import serial
import serial.tools.list_ports
import pydirectinput

# ---------------- Settings ----------------
BAUD = 115200
DEADZONE = 0.30        # fraction of full tilt before a key is pressed (0..1)
RELEASE_ZONE = 0.22    # lower release threshold (hysteresis) prevents key flicker
INVERT_X = False       # flip if A/D come out reversed
INVERT_Y = True        # most modules read low when pushed "up", so up -> W
FULL_SCALE = 500.0     # approx max |value| sent by the sketch
SIGNAL_TIMEOUT = 0.5   # seconds without data -> release everything
# ------------------------------------------

pydirectinput.PAUSE = 0          # no artificial delay between key events
pydirectinput.FAILSAFE = False   # don't abort when the mouse hits a corner

KNOWN_IDS = {
    (0x2341, 0x0043), (0x2341, 0x0001), (0x2341, 0x0243),  # Official Uno / R3
    (0x2A03, 0x0043),                                     # arduino.org Uno
    (0x1A86, 0x7523),                                     # CH340 clones
    (0x0403, 0x6001),                                     # FTDI
    (0x10C4, 0xEA60),                                     # CP210x
}


def find_arduino_port():
    ports = list(serial.tools.list_ports.comports())
    for p in ports:
        if (p.vid, p.pid) in KNOWN_IDS:
            return p.device
    for p in ports:
        text = f"{p.description} {p.manufacturer or ''}".lower()
        if any(k in text for k in ("arduino", "ch340", "usb-serial", "usb serial")):
            return p.device
    return None


class KeyState:
    def __init__(self):
        self.down = set()

    def set(self, key, pressed):
        if pressed and key not in self.down:
            pydirectinput.keyDown(key)
            self.down.add(key)
        elif not pressed and key in self.down:
            pydirectinput.keyUp(key)
            self.down.discard(key)

    def release_all(self):
        for k in list(self.down):
            pydirectinput.keyUp(k)
        self.down.clear()


def axis_keys(value, neg_key, pos_key, keys):
    """Apply hysteresis to one axis and press/release its two keys."""
    held_neg = neg_key in keys.down
    held_pos = pos_key in keys.down
    thr_neg = RELEASE_ZONE if held_neg else DEADZONE
    thr_pos = RELEASE_ZONE if held_pos else DEADZONE
    keys.set(neg_key, value <= -thr_neg)
    keys.set(pos_key, value >= thr_pos)


def run(port):
    keys = KeyState()
    print(f"Connecting to {port} @ {BAUD}...")
    with serial.Serial(port, BAUD, timeout=0.1) as ser:
        # Opening the port resets the Uno; it recalibrates the center (hands off!)
        time.sleep(2.0)
        ser.reset_input_buffer()
        print("Connected. Tilt stick for WASD, click for Space. Ctrl+C to quit.")
        last_data = time.monotonic()
        try:
            while True:
                line = ser.readline().decode("ascii", errors="ignore").strip()
                if not line:
                    if time.monotonic() - last_data > SIGNAL_TIMEOUT and keys.down:
                        keys.release_all()
                    continue
                if line.startswith("READY"):
                    print(f"Arduino calibrated: {line}")
                    continue
                parts = line.split(",")
                if len(parts) != 4 or parts[0] != "J":
                    continue
                try:
                    x, y, sw = int(parts[1]), int(parts[2]), int(parts[3])
                except ValueError:
                    continue
                last_data = time.monotonic()

                nx = max(-1.0, min(1.0, x / FULL_SCALE)) * (-1 if INVERT_X else 1)
                ny = max(-1.0, min(1.0, y / FULL_SCALE)) * (-1 if INVERT_Y else 1)

                axis_keys(nx, "a", "d", keys)
                axis_keys(ny, "s", "w", keys)
                keys.set("space", sw == 1)
        finally:
            keys.release_all()


def main():
    forced = sys.argv[1] if len(sys.argv) > 1 else None
    while True:
        port = forced or find_arduino_port()
        if not port:
            print("Arduino not found. Plug it in... (retrying)")
            time.sleep(2)
            continue
        try:
            run(port)
        except serial.SerialException as e:
            print(f"Serial error: {e}. Reconnecting in 2s "
                  "(is the Arduino IDE Serial Monitor open?)")
            time.sleep(2)
        except KeyboardInterrupt:
            print("\nStopped. All keys released.")
            return


if __name__ == "__main__":
    main()
