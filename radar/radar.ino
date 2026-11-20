/*
  Submarine Sonar - 180 degree sweeping radar
  Arduino Uno R3 + SG90 servo + HC-SR04 + 4-pin RGB LED

  Serial output (9600 baud), one line per reading:
      angle,distance
  distance is in cm. 0 means "no echo / out of range".
  See WIRING.md for the pin connections.
*/

#include <Servo.h>

// ---------- Configuration ----------
#define COMMON_ANODE false   // set true if your RGB LED's long leg goes to 5V

const uint8_t SERVO_PIN = 9;
const uint8_t TRIG_PIN  = 7;
const uint8_t ECHO_PIN  = 8;
const uint8_t RED_PIN   = 3;
const uint8_t GREEN_PIN = 5;
const uint8_t BLUE_PIN  = 6;

const int  MIN_ANGLE      = 0;
const int  MAX_ANGLE      = 180;
const int  STEP_DEG       = 1;     // degrees per step (smooth)
const int  STEP_DELAY_MS  = 15;    // settle time per step (servo + sensor)
const int  MAX_RANGE_CM   = 250;   // ignore echoes beyond this
const int  DANGER_CM      = 20;    // < 20 cm  -> flashing red
const int  WARNING_CM     = 50;    // 20-50 cm -> blue, > 50 -> green
const unsigned long FLASH_MS = 120; // red flash half-period
// -----------------------------------

Servo sonarServo;
int angle = MIN_ANGLE;
int dir   = 1;

enum Zone { CLEAR, WARNING, DANGER };
Zone zone = CLEAR;
bool flashOn = false;
unsigned long lastFlash = 0;

void writeRGB(uint8_t r, uint8_t g, uint8_t b) {
#if COMMON_ANODE
  r = 255 - r; g = 255 - g; b = 255 - b;
#endif
  analogWrite(RED_PIN, r);
  analogWrite(GREEN_PIN, g);
  analogWrite(BLUE_PIN, b);
}

// Returns distance in cm, or 0 if no echo / out of range.
int readDistanceCm() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  // Timeout ~ (MAX_RANGE_CM * 58 us) keeps the sweep fast when nothing is there.
  unsigned long duration = pulseIn(ECHO_PIN, HIGH, (unsigned long)MAX_RANGE_CM * 58UL + 500UL);
  if (duration == 0) return 0;
  int cm = (int)(duration / 58UL);
  if (cm < 2 || cm > MAX_RANGE_CM) return 0;
  return cm;
}

void updateZone(int cm) {
  if (cm > 0 && cm < DANGER_CM)        zone = DANGER;
  else if (cm >= DANGER_CM && cm <= WARNING_CM) zone = WARNING;
  else                                 zone = CLEAR;
}

// Non-blocking LED refresh (keeps red flashing while the servo moves)
void refreshLED() {
  switch (zone) {
    case CLEAR:   writeRGB(0, 255, 0); break;
    case WARNING: writeRGB(0, 0, 255); break;
    case DANGER:
      if (millis() - lastFlash >= FLASH_MS) {
        lastFlash = millis();
        flashOn = !flashOn;
      }
      writeRGB(flashOn ? 255 : 0, 0, 0);
      break;
  }
}

// Delay that keeps the LED flashing
void waitWithLED(unsigned long ms) {
  unsigned long start = millis();
  while (millis() - start < ms) {
    refreshLED();
  }
}

void setup() {
  Serial.begin(9600);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(RED_PIN, OUTPUT);
  pinMode(GREEN_PIN, OUTPUT);
  pinMode(BLUE_PIN, OUTPUT);

  sonarServo.attach(SERVO_PIN);
  sonarServo.write(angle);

  // Startup self-test: R -> G -> B
  writeRGB(255, 0, 0); delay(250);
  writeRGB(0, 255, 0); delay(250);
  writeRGB(0, 0, 255); delay(250);
  writeRGB(0, 0, 0);
  delay(300);
}

void loop() {
  sonarServo.write(angle);
  waitWithLED(STEP_DELAY_MS);

  int cm = readDistanceCm();
  updateZone(cm);
  refreshLED();

  Serial.print(angle);
  Serial.print(',');
  Serial.println(cm);

  // Advance and bounce at the ends
  angle += dir * STEP_DEG;
  if (angle >= MAX_ANGLE) { angle = MAX_ANGLE; dir = -1; }
  else if (angle <= MIN_ANGLE) { angle = MIN_ANGLE; dir = 1; }
}
