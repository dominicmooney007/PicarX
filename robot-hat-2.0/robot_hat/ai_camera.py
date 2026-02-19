# -*- coding: utf-8 -*-
"""
AI Camera module for Raspberry Pi AI Camera (IMX500).

Wraps the picamera2/IMX500 stack to provide object detection, classification,
and pose estimation with near-zero CPU load. Inference runs on the camera's
onboard AI processor.

Requires:
    - Raspberry Pi AI Camera (Sony IMX500) connected via CSI
    - System packages: sudo apt install imx500-all python3-picamera2
    - Python packages: picamera2>=0.3.17, numpy>=1.24

Usage:
    from robot_hat import AICamera
    cam = AICamera(model='ssd_mobilenet')
    cam.start()
    detections = cam.get_detections()
    cam.stop()
"""

import threading
import time
import os
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .basic import _Basic_class

# ---------------------------------------------------------------------------
# Model registry — friendly names to /usr/share/imx500-models/ rpk files
# ---------------------------------------------------------------------------
MODEL_REGISTRY = {
    # Object detection
    'ssd_mobilenet': '/usr/share/imx500-models/imx500_network_ssd_mobilenetv2_fpnlite_320x320_pp.rpk',
    'yolov8n': '/usr/share/imx500-models/imx500_network_yolov8n_pp.rpk',
    'nanodet': '/usr/share/imx500-models/imx500_network_nanodet_plus_416x416_pp.rpk',
    'efficientdet': '/usr/share/imx500-models/imx500_network_efficientdet_lite0_pp.rpk',
    # Pose estimation
    'posenet': '/usr/share/imx500-models/imx500_network_posenet.rpk',
    # Classification
    'mobilenet_cls': '/usr/share/imx500-models/imx500_network_mobilenet_v2.rpk',
    'efficientnet_cls': '/usr/share/imx500-models/imx500_network_efficientnet_bo.rpk',
}

# Default COCO labels for detection models
COCO_LABELS_PATH = '/usr/share/imx500-models/coco_labels.txt'

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Detection:
    """A single object detection result."""
    box: Tuple[int, int, int, int]  # (x, y, w, h)
    category: int
    label: str
    confidence: float

    @property
    def center(self) -> Tuple[int, int]:
        """Center point of the bounding box."""
        x, y, w, h = self.box
        return (x + w // 2, y + h // 2)

    @property
    def area(self) -> int:
        """Area of the bounding box in pixels."""
        return self.box[2] * self.box[3]


@dataclass
class ClassificationResult:
    """A single classification result."""
    category: int
    label: str
    confidence: float


@dataclass
class PoseKeypoint:
    """A single pose estimation result."""
    keypoints: list  # List of (x, y, score) tuples for each body part
    box: Tuple[int, int, int, int]  # Bounding box (x, y, w, h)
    score: float


# ---------------------------------------------------------------------------
# AICamera class
# ---------------------------------------------------------------------------

class AICamera(_Basic_class):
    """
    AI Camera interface for the Raspberry Pi AI Camera (IMX500).

    Runs neural network inference on the camera's onboard processor and
    provides detection/classification/pose results via a background thread.

    Provides a ``detect_obj_parameter`` dict compatible with SunFounder's
    Vilib library for easy migration of existing examples.

    :param model: Model name (key in MODEL_REGISTRY) or absolute path to .rpk
    :param labels_file: Path to labels text file (one label per line).
                        If None, uses COCO labels for detection models.
    :param confidence_threshold: Minimum confidence to keep a detection (0-1)
    :param debug_level: Logging level (see _Basic_class)
    """

    _class_name = 'AICamera'

    # Image dimensions used by the camera stream
    FRAME_WIDTH = 640
    FRAME_HEIGHT = 480

    def __init__(self, model='ssd_mobilenet', labels_file=None,
                 confidence_threshold=0.5, debug_level='warning'):
        super().__init__(debug_level)

        self._model_name = model
        self._model_path = self._resolve_model(model)
        self._labels_file = labels_file
        self._labels = {}
        self._confidence_threshold = confidence_threshold

        # Camera / inference state (populated in start())
        self._picam2 = None
        self._imx500 = None
        self._running = False
        self._thread = None
        self._lock = threading.Lock()

        # Current results (protected by _lock)
        self._detections: List[Detection] = []
        self._classifications: List[ClassificationResult] = []
        self._poses: List[PoseKeypoint] = []
        self._frame = None
        self._inference_fps = 0.0

        # Vilib-compatible parameter dict
        self.detect_obj_parameter = {
            'human_n': 0,
            'human_x': 0,
            'human_y': 0,
            'human_w': 0,
            'human_h': 0,
            'object_n': 0,
            'object_x': 0,
            'object_y': 0,
            'object_w': 0,
            'object_h': 0,
            'detections': [],
        }

    # ------------------------------------------------------------------
    # Model resolution
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_model(model):
        """Resolve a model name or path to an absolute .rpk path."""
        if model in MODEL_REGISTRY:
            return MODEL_REGISTRY[model]
        if os.path.isabs(model) and model.endswith('.rpk'):
            return model
        raise ValueError(
            f"Unknown model '{model}'. Use one of {list(MODEL_REGISTRY.keys())} "
            "or provide an absolute path to a .rpk file."
        )

    def _load_labels(self, labels_file=None):
        """Load label names from a text file (one label per line)."""
        path = labels_file or self._labels_file
        if path is None:
            path = COCO_LABELS_PATH
        self._labels = {}
        if path and os.path.isfile(path):
            with open(path, 'r') as f:
                for i, line in enumerate(f):
                    label = line.strip()
                    if label:
                        self._labels[i] = label
            self._info(f"Loaded {len(self._labels)} labels from {path}")
        else:
            self._warning(f"Labels file not found: {path}")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self, show_preview=False):
        """
        Initialize the camera, upload model firmware, and start inference.

        The first call takes 1-3 minutes while the model firmware is uploaded
        to the IMX500 sensor.

        :param show_preview: If True, open a desktop preview window
        """
        if self._running:
            self._warning("AICamera is already running")
            return

        # Lazy imports — only needed on a Pi with the AI Camera
        try:
            from picamera2 import Picamera2
            from picamera2.devices import IMX500
            from picamera2.devices.imx500 import NetworkIntrinsics
        except ImportError as e:
            raise ImportError(
                "picamera2 with IMX500 support is required. "
                "Install with: sudo apt install imx500-all python3-picamera2"
            ) from e

        self._info(f"Loading model: {self._model_name} ({self._model_path})")
        print(f"[AICamera] Loading model firmware onto IMX500 sensor...")
        print(f"[AICamera] Model: {self._model_path}")
        print(f"[AICamera] This may take 1-3 minutes on first load...")

        # Initialize IMX500 with the model
        self._imx500 = IMX500(self._model_path)
        intrinsics = self._imx500.network_intrinsics
        if not intrinsics:
            intrinsics = NetworkIntrinsics()
            intrinsics.task = "object detection"

        # Load labels
        if intrinsics.labels:
            self._labels = {i: l for i, l in enumerate(intrinsics.labels)}
            self._info(f"Loaded {len(self._labels)} labels from model intrinsics")
        else:
            self._load_labels()

        # Initialize Picamera2
        self._picam2 = Picamera2(self._imx500.camera_num)
        config = self._picam2.create_preview_configuration(
            controls={"FrameRate": intrinsics.inference_rate or 30},
            buffer_count=12
        )
        self._picam2.configure(config)

        if show_preview:
            self._picam2.start_preview()

        self._picam2.start()
        print("[AICamera] Camera started. Waiting for inference results...")

        # Start background inference thread
        self._running = True
        self._thread = threading.Thread(target=self._inference_loop, daemon=True)
        self._thread.start()
        self._info("Inference thread started")

    def stop(self):
        """Stop the camera and inference loop."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None
        if self._picam2 is not None:
            try:
                self._picam2.stop()
                self._picam2.close()
            except Exception as e:
                self._warning(f"Error stopping camera: {e}")
            self._picam2 = None
        self._imx500 = None
        self._info("AICamera stopped")

    def load_model(self, model, labels_file=None):
        """
        Switch to a different model at runtime.

        This stops the camera, re-initializes with the new model, and restarts.

        :param model: Model name or absolute .rpk path
        :param labels_file: Optional labels file for the new model
        """
        was_running = self._running
        if was_running:
            self.stop()
        self._model_name = model
        self._model_path = self._resolve_model(model)
        self._labels_file = labels_file
        if was_running:
            self.start()

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_confidence_threshold(self, value):
        """
        Set the minimum confidence threshold for detections.

        :param value: Confidence threshold between 0.0 and 1.0
        """
        self._confidence_threshold = max(0.0, min(1.0, float(value)))

    # ------------------------------------------------------------------
    # Background inference loop
    # ------------------------------------------------------------------

    def _inference_loop(self):
        """Background thread that polls the camera for inference results."""
        from picamera2.devices.imx500 import IMX500

        fps_start = time.monotonic()
        frame_count = 0

        while self._running:
            try:
                metadata = self._picam2.capture_metadata()

                # Attempt to parse outputs based on model type
                detections = self._parse_detections(metadata)
                classifications = self._parse_classifications(metadata)
                poses = self._parse_poses(metadata)

                # Capture current frame
                frame = self._picam2.capture_array()

                # Update shared state
                with self._lock:
                    self._detections = detections
                    self._classifications = classifications
                    self._poses = poses
                    self._frame = frame
                    self._update_vilib_compat(detections)

                # FPS calculation
                frame_count += 1
                elapsed = time.monotonic() - fps_start
                if elapsed >= 1.0:
                    self._inference_fps = frame_count / elapsed
                    frame_count = 0
                    fps_start = time.monotonic()

            except Exception as e:
                self._error(f"Inference loop error: {e}")
                time.sleep(0.1)

    def _parse_detections(self, metadata):
        """Parse object detection results from camera metadata."""
        detections = []
        try:
            from picamera2.devices.imx500 import IMX500

            outputs = self._imx500.get_outputs(metadata)
            if outputs is None:
                return detections

            # IMX500 detection output: boxes, scores, classes
            # Format depends on the model but post-processed models
            # provide standardized numpy arrays
            input_w, input_h = self._imx500.get_input_size()
            if hasattr(self._imx500, 'get_results'):
                # Newer picamera2 API
                results = self._imx500.get_results(metadata)
                if results is None:
                    return detections
                for result in results:
                    confidence = float(result.confidence)
                    if confidence < self._confidence_threshold:
                        continue
                    category = int(result.category)
                    label = self._labels.get(category, f"class_{category}")
                    box = (int(result.x), int(result.y),
                           int(result.width), int(result.height))
                    detections.append(Detection(
                        box=box, category=category,
                        label=label, confidence=confidence
                    ))
            else:
                # Direct output parsing for post-processed models
                # Output format: [boxes(N,4), scores(N), classes(N), num_detections]
                if len(outputs) >= 4:
                    boxes = outputs[0]
                    classes = outputs[1]
                    scores = outputs[2]
                    num = int(outputs[3][0]) if len(outputs[3]) > 0 else len(scores)

                    for i in range(min(num, len(scores))):
                        confidence = float(scores[i])
                        if confidence < self._confidence_threshold:
                            continue
                        category = int(classes[i])
                        label = self._labels.get(category, f"class_{category}")

                        # Convert normalized coordinates to pixel coordinates
                        y0, x0, y1, x1 = boxes[i]
                        x = int(x0 * self.FRAME_WIDTH)
                        y = int(y0 * self.FRAME_HEIGHT)
                        w = int((x1 - x0) * self.FRAME_WIDTH)
                        h = int((y1 - y0) * self.FRAME_HEIGHT)

                        detections.append(Detection(
                            box=(x, y, w, h), category=category,
                            label=label, confidence=confidence
                        ))
        except Exception as e:
            self._debug(f"Detection parse error: {e}")

        return detections

    def _parse_classifications(self, metadata):
        """Parse classification results from camera metadata."""
        results = []
        try:
            outputs = self._imx500.get_outputs(metadata)
            if outputs is None or len(outputs) == 0:
                return results

            # Classification models output a single array of class scores
            scores = outputs[0]
            if len(scores.shape) == 1 and len(scores) > 10:
                # Likely a classification output (many classes)
                import numpy as np
                top_indices = np.argsort(scores)[::-1][:5]
                for idx in top_indices:
                    confidence = float(scores[idx])
                    if confidence < self._confidence_threshold:
                        continue
                    label = self._labels.get(int(idx), f"class_{idx}")
                    results.append(ClassificationResult(
                        category=int(idx), label=label, confidence=confidence
                    ))
        except Exception as e:
            self._debug(f"Classification parse error: {e}")
        return results

    def _parse_poses(self, metadata):
        """Parse pose estimation results from camera metadata."""
        poses = []
        try:
            outputs = self._imx500.get_outputs(metadata)
            if outputs is None:
                return poses

            # PoseNet outputs: keypoints and scores
            if len(outputs) >= 4:
                # PoseNet format: [scores, keypoint_coords, ...]
                pose_scores = outputs[0]
                keypoint_scores = outputs[1]
                keypoint_coords = outputs[2]

                for i in range(len(pose_scores)):
                    score = float(pose_scores[i])
                    if score < self._confidence_threshold:
                        continue

                    kps = []
                    coords = keypoint_coords[i]
                    kp_scores = keypoint_scores[i]
                    for j in range(len(kp_scores)):
                        y = int(coords[j][0] * self.FRAME_HEIGHT)
                        x = int(coords[j][1] * self.FRAME_WIDTH)
                        s = float(kp_scores[j])
                        kps.append((x, y, s))

                    # Compute bounding box from keypoints
                    xs = [k[0] for k in kps if k[2] > 0.1]
                    ys = [k[1] for k in kps if k[2] > 0.1]
                    if xs and ys:
                        bx = min(xs)
                        by = min(ys)
                        bw = max(xs) - bx
                        bh = max(ys) - by
                    else:
                        bx, by, bw, bh = 0, 0, 0, 0

                    poses.append(PoseKeypoint(
                        keypoints=kps, box=(bx, by, bw, bh), score=score
                    ))
        except Exception as e:
            self._debug(f"Pose parse error: {e}")
        return poses

    # ------------------------------------------------------------------
    # Vilib compatibility layer
    # ------------------------------------------------------------------

    def _update_vilib_compat(self, detections):
        """Update the Vilib-compatible detect_obj_parameter dict."""
        # Filter person detections (COCO class 0 = person)
        persons = [d for d in detections if d.label == 'person']

        if persons:
            p = persons[0]
            cx, cy = p.center
            self.detect_obj_parameter['human_n'] = len(persons)
            self.detect_obj_parameter['human_x'] = cx
            self.detect_obj_parameter['human_y'] = cy
            self.detect_obj_parameter['human_w'] = p.box[2]
            self.detect_obj_parameter['human_h'] = p.box[3]
        else:
            self.detect_obj_parameter['human_n'] = 0
            self.detect_obj_parameter['human_x'] = 0
            self.detect_obj_parameter['human_y'] = 0
            self.detect_obj_parameter['human_w'] = 0
            self.detect_obj_parameter['human_h'] = 0

        if detections:
            d = detections[0]
            cx, cy = d.center
            self.detect_obj_parameter['object_n'] = len(detections)
            self.detect_obj_parameter['object_x'] = cx
            self.detect_obj_parameter['object_y'] = cy
            self.detect_obj_parameter['object_w'] = d.box[2]
            self.detect_obj_parameter['object_h'] = d.box[3]
        else:
            self.detect_obj_parameter['object_n'] = 0
            self.detect_obj_parameter['object_x'] = 0
            self.detect_obj_parameter['object_y'] = 0
            self.detect_obj_parameter['object_w'] = 0
            self.detect_obj_parameter['object_h'] = 0

        self.detect_obj_parameter['detections'] = detections

    # ------------------------------------------------------------------
    # Public query methods
    # ------------------------------------------------------------------

    def get_detections(self, label_filter=None):
        """
        Get current object detections.

        :param label_filter: Optional label string to filter by (e.g. 'person')
        :returns: List of Detection objects
        """
        with self._lock:
            dets = list(self._detections)
        if label_filter:
            dets = [d for d in dets if d.label == label_filter]
        return dets

    def get_largest_detection(self, label_filter=None):
        """
        Get the detection with the largest bounding box area.

        Useful as a proxy for the closest object.

        :param label_filter: Optional label to filter by
        :returns: Detection or None
        """
        dets = self.get_detections(label_filter)
        if not dets:
            return None
        return max(dets, key=lambda d: d.area)

    def get_closest_detection(self, label_filter=None):
        """
        Get the detection closest to the center of the frame.

        :param label_filter: Optional label to filter by
        :returns: Detection or None
        """
        dets = self.get_detections(label_filter)
        if not dets:
            return None
        cx, cy = self.FRAME_WIDTH // 2, self.FRAME_HEIGHT // 2
        return min(dets, key=lambda d: (d.center[0] - cx) ** 2 + (d.center[1] - cy) ** 2)

    def get_object_center_offset(self, label_filter=None):
        """
        Get the normalized offset (-1 to +1) of the largest detection
        from the center of the frame.

        Returns (0, 0) if no detection is found.

        :param label_filter: Optional label to filter by
        :returns: (x_offset, y_offset) tuple, each in range [-1, 1]
        """
        det = self.get_largest_detection(label_filter)
        if det is None:
            return (0.0, 0.0)
        cx, cy = det.center
        x_offset = (cx - self.FRAME_WIDTH / 2) / (self.FRAME_WIDTH / 2)
        y_offset = (cy - self.FRAME_HEIGHT / 2) / (self.FRAME_HEIGHT / 2)
        return (x_offset, y_offset)

    def has_detection(self, label=None):
        """
        Check if any detection is currently present.

        :param label: Optional label to check for
        :returns: True if at least one matching detection exists
        """
        return len(self.get_detections(label)) > 0

    def get_classifications(self, top_n=3):
        """
        Get classification results (for classification models).

        :param top_n: Maximum number of results to return
        :returns: List of ClassificationResult, sorted by confidence descending
        """
        with self._lock:
            cls = list(self._classifications)
        cls.sort(key=lambda c: c.confidence, reverse=True)
        return cls[:top_n]

    def get_poses(self):
        """
        Get pose estimation results (for pose models).

        :returns: List of PoseKeypoint objects
        """
        with self._lock:
            return list(self._poses)

    # ------------------------------------------------------------------
    # Frame access
    # ------------------------------------------------------------------

    @property
    def frame(self):
        """Current camera frame as a numpy array (OpenCV compatible)."""
        with self._lock:
            return self._frame

    def capture_image(self, filepath):
        """
        Save the current frame to an image file.

        :param filepath: Output file path (e.g. 'capture.jpg')
        """
        f = self.frame
        if f is None:
            self._warning("No frame available to capture")
            return
        try:
            from PIL import Image
            img = Image.fromarray(f)
            img.save(filepath)
            self._info(f"Image saved to {filepath}")
        except ImportError:
            self._error("Pillow is required for image capture: pip install Pillow")

    @property
    def inference_fps(self):
        """Current inference frames per second."""
        return self._inference_fps

    # ------------------------------------------------------------------
    # Available models
    # ------------------------------------------------------------------

    @staticmethod
    def available_models():
        """Return a dict of available model names and their .rpk paths."""
        return dict(MODEL_REGISTRY)

    def __repr__(self):
        status = "running" if self._running else "stopped"
        return f"AICamera(model='{self._model_name}', status='{status}')"

    def __del__(self):
        if self._running:
            self.stop()
