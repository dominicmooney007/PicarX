"""
AI Object Detection — prints detected objects with labels, confidence, and boxes.

Requires:
    - Raspberry Pi AI Camera (IMX500) connected via CSI
    - sudo apt install imx500-all python3-picamera2

Usage:
    python3 14.ai_object_detect.py
"""

from robot_hat import AICamera
import time

def main():
    cam = AICamera(model='ssd_mobilenet', confidence_threshold=0.5)
    cam.start()

    # Wait for first inference results
    print("Waiting for detections...")
    time.sleep(2)

    try:
        while True:
            detections = cam.get_detections()
            if detections:
                print(f"\n--- {len(detections)} object(s) detected ---")
                for det in detections:
                    print(f"  {det.label}: {det.confidence:.0%} "
                          f"at ({det.box[0]}, {det.box[1]}) "
                          f"size {det.box[2]}x{det.box[3]}")
            else:
                print(".", end="", flush=True)
            time.sleep(0.5)
    finally:
        cam.stop()
        print("\nStopped.")


if __name__ == "__main__":
    main()
