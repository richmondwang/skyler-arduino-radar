# Submarine Sonar 🟢

A motor swings a distance sensor back and forth. The Arduino measures how far away things are, and your computer draws it as a radar screen.

---

## 1. The whole system

```
  ┌──────────┐   points    ┌──────────┐   echo time   ┌──────────┐   "97,34"   ┌────────┐       ┌───────────┐
  │  SERVO   │ ──────────► │  SENSOR  │ ────────────► │ ARDUINO  │ ──────────► │ app.py │ ────► │  RADAR    │
  │ (motor)  │   sensor    │ (HC-SR04)│               │ (brain)  │  over USB   │(Python)│       │ (browser) │
  └──────────┘             └──────────┘               └────┬─────┘             └────────┘       └───────────┘
                                                           │
                                                           ▼
                                                      ┌──────────┐
                                                      │ RGB LED  │  warning light
                                                      └──────────┘
```

## 2. The loop (repeats forever)

```
        ┌──────────────────────────────┐
        ▼                              │
  1. POINT  servo turns to an angle    │
        │                              │
  2. MEASURE  sensor finds distance    │
        │                              │
  3. WARN  LED shows green/blue/red    │
        │                              │
  4. SEND  "angle,distance" to PC      │
        │                              │
  5. MOVE  +1°  (turn back at 0°/180°) ┘
```

---

## 3. How each part works

### 🦇 Distance sensor (HC-SR04): it uses sound, like a bat

```
   Arduino               Sensor                       Object
  ─────────            ─────────                     ┌─────┐
  Trig ──"go!"──────►  [ speaker ] ))) ))) ))) ────► │     │
                                                     │     │
  Echo ◄─"took 1160µs" [   mic   ] ((( ((( ((( ◄──── │     │
                                                     └─────┘
```

- It sends out a sound too high for humans to hear and times how long the echo takes to come back.
- **Distance = time ÷ 58** (sound travels 0.0343 cm per µs, and it goes there **and back**, so halve it).
- Example: 1160 µs ÷ 58 = **20 cm**. No echo comes back → reports **0** (nothing found).

### ⚙️ Servo: a motor that goes to an exact angle

```
   Pulse from Arduino (50 times a second)           Servo angle

   ▕▔▏________________   1.0 ms pulse   ──►    0°   ◄──
   ▕▔▔▏_______________   1.5 ms pulse   ──►   90°    ↑   (straight ahead)
   ▕▔▔▔▏______________   2.0 ms pulse   ──►  180°   ──►
```

- A longer pulse means a bigger angle.
- Inside, a sensor checks where the shaft is and keeps adjusting until it matches the pulse. This is called **feedback**.

### 🚦 RGB LED: three lights in one bulb

```
   D3 ──[220Ω]──► RED   ─┐
   D5 ──[220Ω]──► GREEN ─┼──► common leg ──► GND
   D6 ──[220Ω]──► BLUE  ─┘
```

| Distance | Colour |
|---|---|
| more than 50 cm | 🟢 Green |
| 20 – 50 cm | 🔵 Blue |
| less than 20 cm | 🔴 Flashing red |

- **Why the resistors?** Without them, too much current flows and the LED burns out. Ohm's law: (5 V − 2 V) ÷ 220 Ω ≈ **14 mA**, which is safe.
- **Dimming (PWM):** the pin switches on and off very fast. More time on = brighter.

```
   dim     ▔|___|▔|___|▔|___     (on 25% of the time)
   bright  ▔▔▔|_|▔▔▔|_|▔▔▔|_     (on 75% of the time)
```

### 🔋 Power and ground

```
   Arduino 5V  ──────► + rail ──► servo, sensor
   Arduino GND ──────► – rail ──► servo, sensor, LED   (everything MUST share GND)
```

- A capacitor across + and – acts like a small tank of charge. It stops the Arduino resetting when the motor suddenly pulls a lot of power.

---

## 4. Arduino → screen

```
   Arduino says:    "97,34"   =  at 97°, something is 34 cm away

   app.py:          reads the USB port ──► passes readings to the web page

   index.html:      turns angle + distance into a dot on the screen

                         90°
       dot at (97°, 34 cm) → • │
                          │
           180° ──────────┼────────── 0°
                        sensor
```

- Each angle-and-distance reading becomes an x/y position: **x = distance × cos(angle)**, **y = distance × sin(angle)**.
- No Arduino plugged in? `app.py` runs a **demo mode** with fake targets.

---

## 5. How the code works

There are three programs, and each one hands its work to the next:

```
  radar/radar.ino  ──"97,34\n"──►  app.py  ──Server-Sent Events──►  index.html
   (on the Arduino)     USB          (on your PC)      http://127.0.0.1:5000     (in the browser)
```

### 🤖 [radar/radar.ino](radar/radar.ino): the Arduino sketch

**Settings at the top.** Pin numbers and values you can change (`STEP_DELAY_MS`, `DANGER_CM`, `WARNING_CM`, `MAX_RANGE_CM`, `COMMON_ANODE`) are all in one block, so you never have to dig through the code to change them.

**`setup()`** runs once:
1. Starts the USB serial link at **9600 baud**.
2. Sets the pins as inputs or outputs and attaches the servo to D9.
3. Flashes the LED **red → green → blue** as a self-test, so you know all three colours are wired correctly.

**`loop()`** runs forever, once per degree:

| Step | Code | What it does |
|---|---|---|
| 1 | `sonarServo.write(angle)` | Turn the servo to the current angle |
| 2 | `waitWithLED(STEP_DELAY_MS)` | Wait 15 ms for the servo to get there, while keeping the LED flashing |
| 3 | `readDistanceCm()` | Send a 10 µs pulse on Trig, time the echo with `pulseIn()`, then divide by 58 to get cm |
| 4 | `updateZone(cm)` | Decide if it's `CLEAR`, `WARNING` or `DANGER` |
| 5 | `refreshLED()` | Set the LED to green, blue or flashing red |
| 6 | `Serial.println(...)` | Send `angle,distance` to the PC |
| 7 | `angle += dir` | Move one degree. At 0° or 180°, flip `dir` to sweep back |

**Clever bits:**
- **Timeout on `pulseIn()`.** If nothing is in range, it gives up after about 250 cm worth of time instead of waiting a whole second. This keeps the sweep fast.
- **Bad readings become `0`.** Anything under 2 cm or over `MAX_RANGE_CM` is treated as "no echo".
- **Flashing without `delay()`.** `refreshLED()` checks `millis()` to decide when to toggle red on or off. `waitWithLED()` keeps calling it while waiting, so the LED keeps flashing even while the servo moves.
- **Common anode support.** `writeRGB()` flips each colour value (`255 − value`) if `COMMON_ANODE` is `true`, because those LEDs light up when the pin is **low**.

### 🐍 [app.py](app.py): the Python web server

It does two jobs at the same time, using **threads**:

```
   Thread 1 (background)                      Thread 2 (Flask web server)
   ─────────────────────                      ──────────────────────────
   read a line from USB                        "/"        → sends index.html
        │                                      "/stream"  → sends every new reading
   "97,34" → {angle: 97, distance: 34}                       to the browser, live
        │                                                         ▲
        └────────►  shared buffer (last 500 readings)  ───────────┘
```

1. **Finding the Arduino.** `find_arduino_port()` looks through the COM ports for a USB ID or name that belongs to an Arduino or a common USB chip (CH340, FTDI, CP210x). If it can't tell, it picks any port that isn't Bluetooth.
2. **Reading.** `serial_reader()` opens the port, waits 2 s (the Uno restarts when the port opens), then reads one line at a time. It splits on the comma, turns both halves into numbers, and throws away anything broken or outside 0–180°.
3. **Sharing.** `publish()` adds each reading to a shared list and wakes up anyone waiting, using a `threading.Condition`. The list only keeps the last 500 readings so it doesn't grow forever.
4. **Streaming.** `/stream` uses **Server-Sent Events**: the browser opens one connection and the server keeps pushing `data: {...}` messages down it. If nothing new arrives for 15 s, it sends a `keepalive` so the connection stays open.
5. **Status.** `set_status()` tells the page whether it's `live`, `demo` or `error`. For example, if the port is busy, it says to close the Serial Monitor.
6. **Demo mode.** `run_demo()` fakes a sweep with three targets that slowly drift closer and further away. If no Arduino is found, it runs demo mode for 3 s, then checks for hardware again. Plug the Uno in and it switches to live by itself.

### 🖥️ [index.html](index.html): the radar screen

All the drawing happens on one `<canvas>` with plain JavaScript (no libraries).

1. **Getting data.** `new EventSource("/stream")` listens to `app.py`. Each `reading` message goes to `onReading()`. Each `status` message updates the LIVE / DEMO light in the top right.
2. **Remembering echoes.** `onReading()` stores each echo in a `Map` keyed by angle (`blips`). A new reading at the same angle replaces the old one, and a `0` deletes it. Blips fade out after 6 s.
3. **Angle → screen.** `pt(angle, r)` uses `cos` and `sin` to turn an angle and distance into x/y pixels. Distance is scaled so the outer ring equals the zoom level (50–250 cm).
4. **Drawing, 60 times a second.** `frame()` clears the screen, then draws:
   - `drawGrid()`: range rings, angle spokes and tinted red/blue danger zones
   - `drawBeam()`: the sweeping line with a fading trail behind it. It eases toward the newest angle, so it moves smoothly even though readings come in steps.
   - `drawBlips()`: a glowing dot for each echo, with a ring that spreads out when it's new
5. **Finding targets.** `contacts()` groups neighbouring blips (within 3° and 15 cm of each other) into one target. A wall becomes one contact instead of 40 dots. The closest one decides the **ALL CLEAR / CONTACT / COLLISION ALERT** banner.
6. **Sound.** The Web Audio API makes the sounds directly, with no audio files: a sonar *ping* with an echo for contacts, and a two-tone *alarm* for danger. Browsers block sound until you click, which is why the **ENGAGE** screen is there.
7. **Settings.** Mirror and sound on/off are saved in `localStorage`, so they're remembered next time.

---

## 6. Pins at a glance

| Arduino pin | Goes to |
|---|---|
| D9 | Servo signal |
| D7 | Sensor Trig |
| D8 | Sensor Echo |
| D3 / D5 / D6 | LED red / green / blue (each through 220 Ω) |
| 5V / GND | + and – rails |

Full wiring steps: [WIRING.md](WIRING.md)

---

## 7. Run it

1. Wire it up, then upload [radar/radar.ino](radar/radar.ino) with the Arduino IDE.
2. Close the Serial Monitor (only one program can use the USB port at a time).
3. Run:
   ```
   python -m pip install pyserial flask
   python app.py
   ```
4. The browser opens **http://127.0.0.1:5000**. Click **ENGAGE** for sound.

**Keys:** `+`/`−` zoom · `M` mirror · `S` sound · `C` clear · **No hardware?** `python app.py --demo`

| Problem | Fix |
|---|---|
| Port busy / access denied | Close the Serial Monitor |
| DEMO MODE with Arduino plugged in | `python app.py --port COM3` (check Device Manager) |
| Radar backwards | Press `M` |
| LED white/cyan instead of red | Set `COMMON_ANODE` to `true` in `radar.ino` |
| Arduino resets when the motor moves | Add a 100–470 µF capacitor between 5V and GND |

---

## 🧪 Try this

- Hold a book at 10, 20 and 50 cm and check the readings with a ruler.
- Compare a wall and a pillow. Soft things absorb sound.
- Change `DANGER_CM` or `STEP_DELAY_MS` at the top of `radar.ino` and see what happens.
