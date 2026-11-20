# Submarine Sonar – Wiring Guide

Hardware: **Arduino Uno R3**, **SG90 micro servo**, **HC-SR04 ultrasonic sensor**, **4-pin RGB LED**, **3 × 220 Ω resistors**, breadboard + jumper wires.

> Why these pins? The Arduino `Servo` library takes over Timer1, which **disables PWM on pins 9 and 10**.
> So the servo goes on pin 9, and the RGB LED uses PWM pins **3, 5, 6** that are not affected.

---

## 1. Power rails

| From (Arduino) | To (breadboard) |
|---|---|
| **5V** | Red **+** rail |
| **GND** | Blue **–** rail |

---

## 2. SG90 Servo (3 wires)

| Servo wire | Connects to |
|---|---|
| **Brown** (GND) | **–** rail (GND) |
| **Red** (VCC) | **+** rail (5V) |
| **Orange / Yellow** (Signal) | Arduino **D9** |

**Tip:** If the Uno resets or the servo twitches when it moves, put a **100–470 µF electrolytic capacitor** across the + and – rails, with the long leg on +. A single SG90 is fine on USB power. For larger loads, use an external 5 V supply and **connect its GND to the Arduino GND**.

---

## 3. HC-SR04 Ultrasonic Sensor (4 pins)

| HC-SR04 pin | Connects to |
|---|---|
| **VCC** | **+** rail (5V) |
| **Trig** | Arduino **D7** |
| **Echo** | Arduino **D8** |
| **GND** | **–** rail (GND) |

The Uno is a 5 V board, so Echo can go straight to D8 with no level shifter.

### Mounting the HC-SR04 on the servo
1. Snap the **single or double-arm horn** onto the servo shaft. Don't screw it down yet.
2. In code (or by hand), move the servo to **90°**. That is straight ahead.
3. Attach the HC-SR04 to the horn with double-sided foam tape, a hot-glue blob, a zip tie or a small 3D-printed/cardboard bracket. Point the two "eyes" **straight forward** when the servo is at 90°.
4. Now screw the horn down with the small screw that came with the servo.
5. Use **female-to-male jumpers that are 15–20 cm long** for the sensor, and leave a slack loop so the wires don't pull as it sweeps 0–180°.
6. Fix the servo body down (tape, glue or a bracket) so it doesn't spin itself around.

---

## 4. RGB LED (4 pins) + 220 Ω resistors

The **longest leg** is the common pin. Hold the LED with the longest leg second from the left. The usual order is:

```
   R   COMMON   G   B
   |     |      |   |
  (1)   (2)    (3) (4)     <- (2) is the longest leg
```

Put **one 220 Ω resistor on each colour leg** (R, G, B), between the leg and the Arduino pin. **Never** put a resistor on the common leg only. Without a resistor on each colour, the LED or the Arduino pin can burn out.

| LED leg | Through | Connects to |
|---|---|---|
| **Red** | 220 Ω | Arduino **D3** |
| **Common (longest)** | — | see below |
| **Green** | 220 Ω | Arduino **D5** |
| **Blue** | 220 Ω | Arduino **D6** |

**Common leg:**
- **Common Cathode** (most kits): common goes to **GND** (– rail). This is the default in `radar.ino`.
- **Common Anode**: common goes to **5V** (+ rail). Then change `#define COMMON_ANODE false` to `true` at the top of `radar.ino`.

Not sure which one you have? Wire it as common cathode. If the colours come out inverted (white or cyan when it should be red), you have common anode.

---

## 5. Quick summary

| Arduino pin | Goes to |
|---|---|
| 5V | Servo red, HC-SR04 VCC, (LED common if anode) |
| GND | Servo brown, HC-SR04 GND, (LED common if cathode) |
| D3 | 220 Ω → LED Red |
| D5 | 220 Ω → LED Green |
| D6 | 220 Ω → LED Blue |
| D7 | HC-SR04 Trig |
| D8 | HC-SR04 Echo |
| D9 | Servo signal (orange) |

## 6. Threat-zone LED behaviour

| Distance | LED |
|---|---|
| > 50 cm or no echo | **Green** (clear) |
| 20 – 50 cm | **Blue** (contact) |
| < 20 cm | **Flashing Red** (danger) |

## 7. Running it
1. Open `radar/radar.ino` in the Arduino IDE (the Servo library must be installed: Library Manager → "Servo"). Pick **Tools → Board → Arduino Uno** and the right **Port**, then click **Upload**.
2. **Close the Serial Monitor.** Only one program can use the COM port at a time.
3. Run `python app.py`. It finds the Uno automatically and opens the sonar website.
   - `python app.py --port COM5` forces a port.
   - `python app.py --demo` runs with simulated data and no hardware.
