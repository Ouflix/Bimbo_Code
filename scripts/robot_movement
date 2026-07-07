const int RPWM_PIN = 25; 
const int LPWM_PIN = 26; 

const int PWM_FREQ = 20000;    
const int PWM_RESOLUTION = 8;  

const int RPWM_CHANNEL = 0;
const int LPWM_CHANNEL = 1;

unsigned long motorStartTime = 0;
const unsigned long RUN_DURATION = 2000; // 1.5 seconds
bool isRunning = false;

void setup() {
  // Over USB, we use the main Serial port at 115200 baud
  Serial.begin(115200); 

  ledcAttachChannel(RPWM_PIN, PWM_FREQ, PWM_RESOLUTION, RPWM_CHANNEL);
  ledcAttachChannel(LPWM_PIN, PWM_FREQ, PWM_RESOLUTION, LPWM_CHANNEL);

  // Note: While testing with the Pi, keep the Arduino IDE Serial Monitor closed,
  // because only one device can read a USB serial port at a time!
}

void loop() {
  // Read from the USB Serial link
  if (Serial.available() > 0) {
    int targetSpeed = Serial.parseInt(); 

    targetSpeed = constrain(targetSpeed, 0, 210);

    if (targetSpeed > 0) {
      moveMotor(targetSpeed, 0); 
      motorStartTime = millis();
      isRunning = true;
    } else {
      stopMotors();
    }
  }

  if (isRunning && (millis() - motorStartTime >= RUN_DURATION)) {
    stopMotors();
  }
}

void stopMotors() {
  moveMotor(0, 0);
  isRunning = false;
}

void moveMotor(int forwardSpeed, int reverseSpeed) {
  ledcWriteChannel(RPWM_CHANNEL, forwardSpeed);
  ledcWriteChannel(LPWM_CHANNEL, reverseSpeed);
}
