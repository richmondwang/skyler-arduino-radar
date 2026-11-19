# Joystick → Arduino Uno R3 Wiring

Standard 5-pin analog joystick module (KY-023 style). Five female-to-male jumper wires.

| Joystick pin | Arduino Uno R3 pin | Purpose                          |
|--------------|--------------------|----------------------------------|
| **GND**      | **GND**            | Ground (any GND header pin)      |
| **+5V**      | **5V**             | Power for the potentiometers     |
| **VRx**      | **A0**             | X axis (left/right) analog value |
| **VRy**      | **A1**             | Y axis (up/down) analog value    |
| **SW**       | **D2**             | Push button (stick click)        |

```
 Joystick module            Arduino Uno R3
 ┌──────────┐
 │      GND ├──────────────── GND
 │     +5V  ├──────────────── 5V
 │      VRx ├──────────────── A0
 │      VRy ├──────────────── A1
 │       SW ├──────────────── D2
 └──────────┘
```

## Notes

- **SW needs no resistor.** The sketch enables the Uno's internal pull-up on D2
  (`INPUT_PULLUP`). The pin reads HIGH when released and LOW when the stick is pressed.
- **Use 5V, not 3.3V.** The sketch assumes the stick's center is about 512 on a 0–1023 range.
  It also calibrates the center at startup, so **leave the stick untouched for about 1 second
  after plugging in or resetting the Uno**.
- **Axis direction:** modules differ in how they're mounted. If W/S or A/D come out
  reversed, flip `INVERT_X` / `INVERT_Y` at the top of `controller.py`. You don't need to rewire.
- Connect the Uno to the PC with a USB-B cable. That one cable carries both power and serial data.

## Uploading the sketch

The Arduino IDE needs a sketch to live in a folder with the same name. Open `joystick.ino`
and let the IDE move it into a `joystick/` folder when it asks. Then pick
**Tools → Board → Arduino Uno**, choose the right **Port**, and click **Upload**.
Close the IDE's Serial Monitor before running `controller.py`, because only one program can
use the port at a time.
