"""
AI Face/Person Tracking — pan/tilt servos follow detected people.

This is the AI Camera equivalent of example 8.stare_at_you.py (which uses Vilib).
The AICamera's detect_obj_parameter dict is Vilib-compatible, so the tracking
logic is nearly identical.

Requires:
    - Raspberry Pi AI Camera (IMX500) connected via CSI
    - sudo apt install imx500-all python3-picamera2

Usage:
    python3 15.ai_face_tracking.py
"""

from picarx import Picarx
from robot_hat import AICamera
from time import sleep


def clamp_number(num, a, b):
    return max(min(num, max(a, b)), min(a, b))


def main():
    px = Picarx()
    cam = AICamera(model='ssd_mobilenet', confidence_threshold=0.5)
    cam.start()

    print("Waiting for AI Camera to initialize...")
    sleep(2)
    print("Tracking people — press Ctrl+C to stop.")

    x_angle = 0
    y_angle = 0

    try:
        while True:
            if cam.detect_obj_parameter['human_n'] != 0:
                coordinate_x = cam.detect_obj_parameter['human_x']
                coordinate_y = cam.detect_obj_parameter['human_y']

                # Adjust pan/tilt to track the person
                x_angle += (coordinate_x * 10 / cam.FRAME_WIDTH) - 5
                x_angle = clamp_number(x_angle, -35, 35)
                px.set_cam_pan_angle(x_angle)

                y_angle -= (coordinate_y * 10 / cam.FRAME_HEIGHT) - 5
                y_angle = clamp_number(y_angle, -35, 35)
                px.set_cam_tilt_angle(y_angle)

            sleep(0.05)
    finally:
        cam.stop()
        px.stop()
        print("Stopped.")


if __name__ == "__main__":
    main()
