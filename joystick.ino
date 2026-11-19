// Joystick -> USB serial for controller.py
// Output (115200 baud, ~100 Hz):  "J,<x>,<y>,<sw>\n"
//   x, y : centered axis values, roughly -512..+511 (0 = stick at rest)
//   sw   : 1 = pressed, 0 = released

const uint8_t PIN_X  = A0;
const uint8_t PIN_Y  = A1;
const uint8_t PIN_SW = 2;

const unsigned long SEND_INTERVAL_MS = 10;   // 100 updates per second
const unsigned long DEBOUNCE_MS      = 15;

int centerX = 512;
int centerY = 512;

bool swStable = false;          // debounced pressed state
bool swLastRaw = false;
unsigned long swChangedAt = 0;

int readAvg(uint8_t pin) {
  long sum = 0;
  for (uint8_t i = 0; i < 4; i++) sum += analogRead(pin);
  return sum / 4;
}

void calibrate() {
  long sx = 0, sy = 0;
  const int N = 64;
  for (int i = 0; i < N; i++) {
    sx += analogRead(PIN_X);
    sy += analogRead(PIN_Y);
    delay(5);
  }
  centerX = sx / N;
  centerY = sy / N;
}

void setup() {
  pinMode(PIN_SW, INPUT_PULLUP);
  Serial.begin(115200);
  delay(300);          // let the stick settle
  calibrate();         // keep hands off the stick during startup
  Serial.print(F("READY,"));
  Serial.print(centerX);
  Serial.print(',');
  Serial.println(centerY);
}

void loop() {
  static unsigned long lastSend = 0;

  // Debounce the button
  bool raw = digitalRead(PIN_SW) == LOW;
  if (raw != swLastRaw) {
    swLastRaw = raw;
    swChangedAt = millis();
  }
  if (millis() - swChangedAt >= DEBOUNCE_MS) swStable = swLastRaw;

  unsigned long now = millis();
  if (now - lastSend >= SEND_INTERVAL_MS) {
    lastSend = now;
    int x = readAvg(PIN_X) - centerX;
    int y = readAvg(PIN_Y) - centerY;

    Serial.print(F("J,"));
    Serial.print(x);
    Serial.print(',');
    Serial.print(y);
    Serial.print(',');
    Serial.println(swStable ? 1 : 0);
  }
}
