"""
AI Object Following — drives toward and follows a detected person (or other object).

Combines steering, speed control, and pan/tilt tracking. The car steers toward
the largest detected person, adjusts speed based on distance (bounding box size),
and uses the pan servo to keep the target in view.

Requires:
    - Raspberry Pi AI Camera (IMX500) connected via CSI
    - sudo apt install imx500-all python3-picamera2

Usage:
    python3 17.ai_object_following.py
    python3 17.ai_object_following.py --label cat   # follow a different object
"""

from picarx import Picarx
from robot_hat import AICamera
import time
import sys

TARGET_LABEL = 'person'
FOLLOW_SPEED = 35
STEER_GAIN = 1.2
# Target area ratio — stop advancing when the object is this fraction of frame
TARGET_AREA_RATIO = 0.20
MIN_AREA_RATIO = 0.02  # Object too far — move faster


def main():
    label = TARGET_LABEL
    if '--label' in sys.argv:
        idx = sys.argv.index('--label')
        if idx + 1 < len(sys.argv):
            label = sys.argv[idx + 1]

    px = Picarx()
    cam = AICamera(model='ssd_mobilenet', confidence_threshold=0.45)
    cam.start()

    print("Waiting for AI Camera to initialize...")
    time.sleep(2)
    print(f"Following '{label}' — press Ctrl+C to stop.")

    pan_angle = 0
    frame_area = cam.FRAME_WIDTH * cam.FRAME_HEIGHT

    try:
        while True:
            det = cam.get_largest_detection(label)

            if det is None:
                # Lost target — stop and search
                px.stop()
                time.sleep(0.1)
                continue

            cx, cy = det.center
            area_ratio = det.area / frame_area

            # Steering — steer toward the object
            x_offset = (cx - cam.FRAME_WIDTH / 2) / (cam.FRAME_WIDTH / 2)
            steer_angle = x_offset * 30 * STEER_GAIN
            px.set_dir_servo_angle(steer_angle)

            # Pan servo — keep object centered
            pan_angle += x_offset * 3
            pan_angle = max(-35, min(35, pan_angle))
            px.set_cam_pan_angle(pan_angle)

            # Speed control based on distance (bounding box size)
            if area_ratio > TARGET_AREA_RATIO:
                # Close enough — stop
                px.stop()
            elif area_ratio < MIN_AREA_RATIO:
                # Far away — drive faster
                px.forward(FOLLOW_SPEED + 15)
            else:
                px.forward(FOLLOW_SPEED)

            time.sleep(0.05)
    finally:
        px.stop()
        cam.stop()
        print("Stopped.")


if __name__ == "__main__":
    main()
