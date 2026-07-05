import cv2
import numpy as np
from ultralytics import YOLO
from modules.motor_hc595 import turn, moveUntilStopped, shift_out, STOP, UNRESERVED
import time
import threading
from queue import Queue
import os
import subprocess
from modules.ultrasonicsensor import mesure_distance_low, mesure_distance_high
from enum import Enum
import signal
import sys

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

# Robot states
class RobotState(Enum):
    SEARCHING = "searching"
    TRACKING = "tracking"
    APPROACHING = "approaching"
    REACHED = "reached"
    STOPPED = "stopped"

# Constants
CONFIDENCE_THRESHOLD = 0.3  # Slightly higher for better detection accuracy
FOV_DEGREES = 62
TURN_SPEED = 0.5  # Reduced for more precise turning
TOLERANCE_PIXELS = 30  # Pixel tolerance for centering
MIN_SAFE_DISTANCE = 30  # Minimum safe distance in cm
MAX_SEARCH_TIME = 60  # Maximum search time in seconds
SEARCH_TURN_DEGREES = 45  # Degrees to turn when searching
TURN_DURATION_PER_DEGREE = 0.02  # Calibrate this based on your robot

# Global model management
class ModelManager:
    _model = None
    
    @classmethod
    def get_model(cls):
        if cls._model is None:
            print("Loading YOLO model...")
            cls._model = YOLO("yolov8n.pt")
            print("YOLO model loaded successfully")
        return cls._model

# Improved camera manager
class CameraManager:
    _instance = None
    _camera = None
    _lock = threading.Lock()
    
    @classmethod
    def initialize(cls):
        with cls._lock:
            if cls._camera is not None:
                cls.cleanup()
            
            # Kill any existing camera processes
            subprocess.run(["pkill", "-f", "libcamera"], stderr=subprocess.DEVNULL)
            time.sleep(0.5)
            
            from picamera2 import Picamera2
            try:
                cls._camera = Picamera2()
                config = cls._camera.create_preview_configuration(
                    main={"format": "RGB888", "size": (640, 480)},
                    buffer_count=4,
                    controls={
                        "FrameDurationLimits": (33333, 33333),  # 30fps
                        "AwbEnable": True,
                        "AeEnable": True
                    }
                )
                cls._camera.configure(config)
                cls._camera.start()
                time.sleep(1.0)  # Camera warm-up
                print("Camera initialized successfully")
                return cls._camera
            except Exception as e:
                print(f"Failed to initialize camera: {e}")
                cls.cleanup()
                raise
    
    @classmethod
    def cleanup(cls):
        with cls._lock:
            if cls._camera is not None:
                try:
                    cls._camera.stop()
                    cls._camera.close()
                except:
                    pass
                cls._camera = None
            subprocess.run(["pkill", "-f", "libcamera"], stderr=subprocess.DEVNULL)

# Main movement sequence class
class MovementSequence:
    def __init__(self, target_object):
        self.target_object = target_object.lower()
        self.model = ModelManager.get_model()
        self.camera = None
        self.state = RobotState.SEARCHING
        self.running = False
        self.target_last_seen = None
        self.search_direction = 1  # 1 for right, -1 for left
        self.no_target_count = 0
        self.frame_queue = Queue(maxsize=2)
        self.stop_motors()
        
    def stop_motors(self):
        """Ensure motors are stopped"""
        try:
            shift_out(STOP, UNRESERVED)
            time.sleep(0.1)
        except Exception as e:
            print(f"Error stopping motors: {e}")
    
    def check_obstacles(self):
        """Check if path is clear"""
        try:
            dist_low = mesure_distance_low()
            dist_high = mesure_distance_high()
            print(f"Distance readings - Low: {dist_low}cm, High: {dist_high}cm")
            return dist_low > MIN_SAFE_DISTANCE and dist_high > MIN_SAFE_DISTANCE
        except Exception as e:
            print(f"Error reading sensors: {e}")
            return False
    
    def turn_robot(self, degrees):
        """Turn robot by specified degrees"""
        self.stop_motors()
        time.sleep(0.1)
        
        duration = abs(degrees) * TURN_DURATION_PER_DEGREE
        print(f"Turning {degrees} degrees for {duration:.2f} seconds")
        
        turn(degrees, duration)
        self.stop_motors()
        time.sleep(0.2)
    
    def move_forward(self):
        """Move forward safely"""
        if not self.check_obstacles():
            print("Obstacle detected, cannot move forward")
            return False
        
        self.stop_motors()
        time.sleep(0.1)
        
        print("Moving forward until obstacle detected")
        result = moveUntilStopped()
        
        self.stop_motors()
        time.sleep(0.2)
        
        return result
    
    def process_frame(self, frame):
        """Process a single frame for object detection"""
        # Resize for faster processing
        small_frame = cv2.resize(frame, (320, 240))
        
        # Run detection
        results = self.model(small_frame, conf=CONFIDENCE_THRESHOLD, verbose=False)[0]
        
        # Scale factors
        scale_x = frame.shape[1] / 320
        scale_y = frame.shape[0] / 240
        
        # Create display frame
        display_frame = frame.copy()
        
        # Add UI elements
        cv2.putText(display_frame, f"State: {self.state.value}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(display_frame, f"Target: {self.target_object}", (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Draw center line
        center_x = frame.shape[1] // 2
        cv2.line(display_frame, (center_x, 0), (center_x, frame.shape[0]), (255, 0, 0), 1)
        
        target_detected = False
        target_info = None
        
        # Process detections
        for box in results.boxes:
            cls = int(box.cls[0])
            name = self.model.names[cls].lower()
            confidence = float(box.conf[0])
            
            # Scale coordinates
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            x1, x2 = int(x1 * scale_x), int(x2 * scale_x)
            y1, y2 = int(y1 * scale_y), int(y2 * scale_y)
            
            # Draw bounding box
            is_target = name == self.target_object
            color = (0, 255, 0) if is_target else (255, 0, 0)
            cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(display_frame, f"{name} {confidence:.2f}", (x1, y1-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            if is_target and confidence > CONFIDENCE_THRESHOLD:
                target_detected = True
                obj_center_x = (x1 + x2) // 2
                obj_area = (x2 - x1) * (y2 - y1)
                target_info = {
                    'center_x': obj_center_x,
                    'offset': obj_center_x - center_x,
                    'area': obj_area,
                    'confidence': confidence
                }
                
                # Draw target center
                cv2.circle(display_frame, (obj_center_x, (y1+y2)//2), 5, (0, 0, 255), -1)
                cv2.putText(display_frame, f"Offset: {target_info['offset']}px", 
                           (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        
        return display_frame, target_detected, target_info
    
    def search_behavior(self):
        """Execute search pattern"""
        print(f"Searching... (turn direction: {self.search_direction})")
        self.turn_robot(SEARCH_TURN_DEGREES * self.search_direction)
        
        # Change direction occasionally for better coverage
        if self.no_target_count > 8:
            self.search_direction *= -1
            self.no_target_count = 0
    
    def tracking_behavior(self, target_info):
        """Track and approach the target"""
        offset = target_info['offset']
        
        if abs(offset) < TOLERANCE_PIXELS:
            # Target is centered, move forward
            print("Target centered, moving forward")
            self.state = RobotState.APPROACHING
            
            if self.move_forward():
                print("Target reached!")
                self.state = RobotState.REACHED
                return True
            else:
                # Obstacle encountered, go back to tracking
                self.state = RobotState.TRACKING
        else:
            # Turn towards target
            turn_degrees = (offset / self.camera.capture_array().shape[1]) * FOV_DEGREES
            turn_degrees = max(-30, min(30, turn_degrees))  # Limit turn angle
            self.turn_robot(turn_degrees)
        
        return False
    
    def run(self):
        """Main execution loop"""
        try:
            # Initialize camera
            print("Initializing camera...")
            self.camera = CameraManager.initialize()
            self.running = True
            
            # Create OpenCV window
            cv2.namedWindow("Robot Vision", cv2.WINDOW_NORMAL)
            cv2.resizeWindow("Robot Vision", 640, 480)
            
            start_time = time.time()
            last_frame_time = 0
            frame_interval = 0.1  # Process frame every 100ms
            
            print(f"Starting search for: {self.target_object}")
            
            while self.running and (time.time() - start_time < MAX_SEARCH_TIME):
                current_time = time.time()
                
                # Control frame rate
                if current_time - last_frame_time < frame_interval:
                    time.sleep(0.01)
                    continue
                
                try:
                    # Capture frame
                    frame = self.camera.capture_array()
                    last_frame_time = current_time
                    
                    # Process frame
                    display_frame, target_detected, target_info = self.process_frame(frame)
                    
                    # State machine logic
                    if self.state == RobotState.SEARCHING:
                        if target_detected:
                            print(f"Target found! Confidence: {target_info['confidence']:.2f}")
                            self.state = RobotState.TRACKING
                            self.target_last_seen = current_time
                            self.no_target_count = 0
                        else:
                            self.no_target_count += 1
                            if self.no_target_count > 2:  # Search after a few frames without target
                                self.search_behavior()
                    
                    elif self.state == RobotState.TRACKING:
                        if target_detected:
                            self.target_last_seen = current_time
                            if self.tracking_behavior(target_info):
                                # Target reached
                                break
                        else:
                            # Lost target
                            if current_time - self.target_last_seen > 2.0:
                                print("Target lost, returning to search")
                                self.state = RobotState.SEARCHING
                                self.no_target_count = 0
                    
                    elif self.state == RobotState.REACHED:
                        print("Target successfully reached!")
                        break
                    
                    # Display frame
                    cv2.imshow("Robot Vision", display_frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        print("User quit")
                        break
                    
                except Exception as e:
                    print(f"Error in main loop: {e}")
                    continue
            
            # Check timeout
            if time.time() - start_time >= MAX_SEARCH_TIME:
                print("Search timeout reached")
            
            return self.state == RobotState.REACHED
            
        except Exception as e:
            print(f"Critical error: {e}")
            import traceback
            traceback.print_exc()
            return False
            
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        print("Cleaning up...")
        self.running = False
        self.stop_motors()
        CameraManager.cleanup()
        cv2.destroyAllWindows()
        print("Cleanup complete")

def movement_sequence(target_object):
    """Main entry point for movement sequence"""
    # Set up signal handler for clean shutdown
    def signal_handler(sig, frame):
        print("\nInterrupt received, shutting down...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Create and run movement sequence
    sequence = MovementSequence(target_object)
    return sequence.run()

if __name__ == "__main__":
    # Test with a bottle
    success = movement_sequence("bottle")
    print(f"Movement sequence {'succeeded' if success else 'failed'}")
