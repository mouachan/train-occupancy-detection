import cv2
import numpy as np
from pathlib import Path
from typing import List, Generator, Tuple, Optional
from ultralytics import YOLO

from .visualizer import Detection


class YOLODetector:
    """Person detector using YOLOv11 model."""

    def __init__(self, model_path: str, conf_threshold: float = 0.25, device: str = 'cpu'):
        """
        Initialize YOLO detector with local model.

        Args:
            model_path: Path to YOLOv11 model file (.pt)
            conf_threshold: Confidence threshold for detections (0.0-1.0)
            device: Device to run inference on ('cpu', 'cuda', 'mps')
        """
        self.model_path = Path(model_path)
        self.conf_threshold = conf_threshold
        self.device = device

        if not self.model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")

        # Load YOLO model
        self.model = YOLO(str(self.model_path))
        self.model.to(device)

        # COCO class names - person is class 0
        self.person_class_id = 0

    def detect_persons(self, frame: np.ndarray) -> List[Detection]:
        """
        Detect persons in a single frame.

        Args:
            frame: Input image as numpy array (BGR format)

        Returns:
            List of Detection objects for persons found in the frame
        """
        # Run inference - filter for person class only
        results = self.model(frame, classes=[self.person_class_id], conf=self.conf_threshold, verbose=False)

        detections = []

        # Parse results
        for result in results:
            boxes = result.boxes
            for box in boxes:
                # Extract bounding box coordinates
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()

                # Extract confidence and class
                confidence = float(box.conf[0].cpu().numpy())
                class_id = int(box.cls[0].cpu().numpy())

                # Create Detection object
                detection = Detection(
                    bbox=[float(x1), float(y1), float(x2), float(y2)],
                    confidence=confidence,
                    class_id=class_id,
                    class_name='person'
                )
                detections.append(detection)

        return detections

    def process_video(self, video_path: str, skip_frames: int = 0) -> Generator[Tuple[np.ndarray, List[Detection]], None, None]:
        """
        Process video file frame by frame.

        Args:
            video_path: Path to video file
            skip_frames: Number of frames to skip between processing (for performance)

        Yields:
            Tuple of (frame, detections) for each processed frame
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        cap = cv2.VideoCapture(str(video_path))

        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {video_path}")

        frame_count = 0

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                # Skip frames if requested
                if skip_frames > 0 and frame_count % (skip_frames + 1) != 0:
                    frame_count += 1
                    continue

                # Detect persons in frame
                detections = self.detect_persons(frame)

                yield frame, detections

                frame_count += 1

        finally:
            cap.release()

    def process_image(self, image_path: str) -> Tuple[np.ndarray, List[Detection]]:
        """
        Process a single image file.

        Args:
            image_path: Path to image file

        Returns:
            Tuple of (image, detections)
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")

        # Read image
        frame = cv2.imread(str(image_path))
        if frame is None:
            raise ValueError(f"Could not read image file: {image_path}")

        # Detect persons
        detections = self.detect_persons(frame)

        return frame, detections

    def get_model_info(self) -> dict:
        """
        Get information about the loaded model.

        Returns:
            Dictionary with model metadata
        """
        return {
            'model_path': str(self.model_path),
            'model_type': 'YOLOv11',
            'device': self.device,
            'conf_threshold': self.conf_threshold,
            'target_class': 'person',
            'target_class_id': self.person_class_id
        }
