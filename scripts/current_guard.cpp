#include "current_guard.h"
#include <Arduino.h>
#include <math.h>

const int CURRENT_ADC_PIN = 35;      // WCS1700 Aout (ADC1, ca sa nu se bata cu WiFi)
const int CUTOFF_PIN = 4;            // IN pe modulul releu

const float MV_PER_AMP = 32.0;       // sensibilitatea WCS1700
const float ADC_REF_VOLTAGE = 3.3;
const int ADC_RESOLUTION = 4095;

const float STALL_THRESHOLD_A = 2.5;

const int SMOOTHING_SAMPLES = 8;

const unsigned long STALL_SUSTAIN_MS = 150;  // curentul trebuie sa stea peste prag atat, ca sa ignore varfurile scurte

float zeroOffsetVoltage = 0.0;
float readings[SMOOTHING_SAMPLES];
int readingIndex = 0;
bool bufferFilled = false;

bool servoPowered = true;
unsigned long overThresholdSince = 0;
bool overThresholdActive = false;


float adcToVoltage(int raw) {
  return (raw / (float)ADC_RESOLUTION) * ADC_REF_VOLTAGE;
}

void currentGuardInit() {
  pinMode(CUTOFF_PIN, OUTPUT);
  digitalWrite(CUTOFF_PIN, HIGH);  // releu activ-HIGH: HIGH = alimentat

  analogReadResolution(12);
  analogSetPinAttenuation(CURRENT_ADC_PIN, ADC_11db);

  // servourile trebuie sa fie in release() aici, altfel offsetul iese gresit
  Serial.println("Calibrare offset zero-curent...");
  float total = 0;
  const int samples = 100;
  for (int i = 0; i < samples; i++) {
    total += adcToVoltage(analogRead(CURRENT_ADC_PIN));
    delay(5);
  }
  zeroOffsetVoltage = total / samples;
  Serial.print("Offset zero: ");
  Serial.println(zeroOffsetVoltage, 4);
  Serial.println("READY");

  for (int i = 0; i < SMOOTHING_SAMPLES; i++) readings[i] = 0;
}

float readCurrentRaw() {
  float v = adcToVoltage(analogRead(CURRENT_ADC_PIN)) - zeroOffsetVoltage;
  float amps = (v * 1000.0) / MV_PER_AMP;
  return fabs(amps);
}

float smoothedCurrent() {
  readings[readingIndex] = readCurrentRaw();
  readingIndex = (readingIndex + 1) % SMOOTHING_SAMPLES;
  if (readingIndex == 0) bufferFilled = true;

  int count = bufferFilled ? SMOOTHING_SAMPLES : max(1, readingIndex);
  float sum = 0;
  for (int i = 0; i < count; i++) sum += readings[i];
  return sum / count;
}

void cutServoPower() {
  Serial.println("STALL");       // trimit intai, ca Pi-ul sa apuce sa opreasca PWM-ul
  delay(80);
  digitalWrite(CUTOFF_PIN, LOW);   // taie alimentarea
  servoPowered = false;          // ramane taiat pana la RESET de la Pi
}

void restoreServoPower() {
  digitalWrite(CUTOFF_PIN, HIGH);
  servoPowered = true;
  Serial.println("RECOVERED");
}

void updateCurrentGuard() {
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd == "RESET" && !servoPowered) {
      restoreServoPower();
    } else if (cmd == "PING") {
      Serial.println("READY");   // raspuns la handshake, rezolva timing-ul de boot
    }
  }

  if (servoPowered) {
    float current = smoothedCurrent();

    if (current > STALL_THRESHOLD_A) {
      if (!overThresholdActive) {
        overThresholdSince = millis();
        overThresholdActive = true;
      } else if (millis() - overThresholdSince >= STALL_SUSTAIN_MS) {
        cutServoPower();   // a stat peste prag destul -> stall real
        overThresholdActive = false;
      }
    } else {
      overThresholdActive = false;   // a scazut sub prag -> a fost doar un varf
    }
  }
}

bool isServoPowerCut() {
  return !servoPowered;
}