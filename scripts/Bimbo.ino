#include "current_guard.h"

void setup() {
  Serial.begin(115200);
  currentGuardInit();
}

void loop() {
  updateCurrentGuard();
}