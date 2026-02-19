"""
AI Pose Detection — detects human body poses using PoseNet on the IMX500.

Prints detected keypoints (nose, eyes, ears, shoulders, elbows, wrists,
hips, knees, ankles) with their coordinates and confidence scores.

Requires:
    - Raspberry Pi AI Camera (IMX500) connected via CSI
    - sudo apt install imx500-all python3-picamera2

Usage:
    python3 18.ai_pose_detection.py
"""

from robot_hat import AICamera
import time

# PoseNet keypoint names (COCO format)
KEYPOINT_NAMES = [
    'nose', 'left_eye', 'right_eye', 'left_ear', 'right_ear',
    'left_shoulder', 'right_shoulder', 'left_elbow', 'right_elbow',
    'left_wrist', 'right_wrist', 'left_hip', 'right_hip',
    'left_knee', 'right_knee', 'left_ankle', 'right_ankle',
]


def main():
    cam = AICamera(model='posenet', confidence_threshold=0.3)
    cam.start()

    print("Waiting for AI Camera to initialize...")
    time.sleep(2)
    print("Detecting poses — press Ctrl+C to stop.")

    try:
        while True:
            poses = cam.get_poses()
            if poses:
                print(f"\n--- {len(poses)} pose(s) detected ---")
                for i, pose in enumerate(poses):
                    print(f"  Person {i + 1} (score: {pose.score:.2f}):")
                    for j, (x, y, score) in enumerate(pose.keypoints):
                        if score > 0.3:
                            name = KEYPOINT_NAMES[j] if j < len(KEYPOINT_NAMES) else f"kp_{j}"
                            print(f"    {name}: ({x}, {y}) score={score:.2f}")
            else:
                print(".", end="", flush=True)
            time.sleep(0.5)
    finally:
        cam.stop()
        print("\nStopped.")


if __name__ == "__main__":
    main()
