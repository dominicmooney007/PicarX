"""
AI Vision-Based Obstacle Avoidance — uses the AI Camera to detect objects
ahead and steer around them.

Unlike example 4 (ultrasonic-based), this uses the camera to see obstacles
and estimate their position by bounding box size and location.

Requires:
    - Raspberry Pi AI Camera (IMX500) connected via CSI
    - sudo apt install imx500-all python3-picamera2

Usage:
    python3 16.ai_obstacle_avoidance.py
"""

from picarx import Picarx
from robot_hat import AICamera
import time

SPEED = 40
# Bounding box area thresholds (fraction of frame area)
DANGER_AREA = 0.15   # Object is very close — back up
CAUTION_AREA = 0.06  # Object is approaching — steer away


def main():
    px = Picarx()
    cam = AICamera(model='ssd_mobilenet', confidence_threshold=0.45)
    cam.start()

    print("Waiting for AI Camera to initialize...")
    time.sleep(2)
    print("Driving with vision-based obstacle avoidance — press Ctrl+C to stop.")

    frame_area = cam.FRAME_WIDTH * cam.FRAME_HEIGHT

    try:
        while True:
            det = cam.get_largest_detection()

            if det is None:
                # No obstacles — drive straight
                px.set_dir_servo_angle(0)
                px.forward(SPEED)
            else:
                area_ratio = det.area / frame_area
                cx = det.center[0]

                if area_ratio > DANGER_AREA:
                    # Too close — back up and turn away
                    steer = -30 if cx > cam.FRAME_WIDTH / 2 else 30
                    px.set_dir_servo_angle(steer)
                    px.backward(SPEED)
                    time.sleep(0.5)
                elif area_ratio > CAUTION_AREA:
                    # Approaching — steer away from the object
                    if cx > cam.FRAME_WIDTH / 2:
                        px.set_dir_servo_angle(-25)
                    else:
                        px.set_dir_servo_angle(25)
                    px.forward(SPEED)
                else:
                    # Object is far away — drive straight
                    px.set_dir_servo_angle(0)
                    px.forward(SPEED)

            time.sleep(0.1)
    finally:
        px.stop()
        cam.stop()
        print("Stopped.")


if __name__ == "__main__":
    main()
