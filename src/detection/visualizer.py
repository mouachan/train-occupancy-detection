import cv2
import numpy as np
from typing import List, Dict, Any


class Detection:
    """Represents a single object detection."""

    def __init__(self, bbox: List[float], confidence: float, class_id: int, class_name: str):
        self.bbox = bbox  # [x1, y1, x2, y2]
        self.confidence = confidence
        self.class_id = class_id
        self.class_name = class_name


def draw_detections(frame: np.ndarray, detections: List[Detection],
                    color: tuple = (0, 255, 0), thickness: int = 2) -> np.ndarray:
    """
    Draw bounding boxes and confidence scores on a frame.

    Args:
        frame: Input image as numpy array (BGR format)
        detections: List of Detection objects
        color: BGR color tuple for bounding boxes (default: green)
        thickness: Line thickness for bounding boxes

    Returns:
        Annotated frame with bounding boxes and labels
    """
    annotated_frame = frame.copy()

    for detection in detections:
        x1, y1, x2, y2 = map(int, detection.bbox)

        # Draw bounding box
        cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, thickness)

        # Prepare label with confidence score
        label = f"{detection.class_name}: {detection.confidence:.2f}"

        # Get label size for background rectangle
        (label_width, label_height), baseline = cv2.getTextSize(
            label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
        )

        # Draw label background
        cv2.rectangle(
            annotated_frame,
            (x1, y1 - label_height - baseline - 5),
            (x1 + label_width, y1),
            color,
            -1
        )

        # Draw label text
        cv2.putText(
            annotated_frame,
            label,
            (x1, y1 - baseline - 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 0, 0),
            1
        )

    return annotated_frame


def create_detection_summary(detections: List[Detection]) -> Dict[str, Any]:
    """
    Generate summary statistics for detections.

    Args:
        detections: List of Detection objects

    Returns:
        Dictionary with summary statistics
    """
    if not detections:
        return {
            'total_persons': 0,
            'avg_confidence': 0.0,
            'high_conf_count': 0,
            'max_confidence': 0.0,
            'min_confidence': 0.0
        }

    confidences = [d.confidence for d in detections]

    return {
        'total_persons': len(detections),
        'avg_confidence': np.mean(confidences),
        'high_conf_count': sum(1 for c in confidences if c > 0.8),
        'max_confidence': max(confidences),
        'min_confidence': min(confidences)
    }


def draw_summary_on_frame(frame: np.ndarray, summary: Dict[str, Any]) -> np.ndarray:
    """
    Draw detection summary statistics on frame.

    Args:
        frame: Input image as numpy array
        summary: Summary dictionary from create_detection_summary

    Returns:
        Frame with summary text overlay
    """
    annotated_frame = frame.copy()

    # Create summary text
    summary_lines = [
        f"Persons Detected: {summary['total_persons']}",
        f"Avg Confidence: {summary['avg_confidence']:.2f}",
        f"High Conf (>0.8): {summary['high_conf_count']}"
    ]

    # Draw semi-transparent background for summary
    overlay = annotated_frame.copy()
    cv2.rectangle(overlay, (10, 10), (350, 100), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.6, annotated_frame, 0.4, 0, annotated_frame)

    # Draw summary text
    y_offset = 30
    for line in summary_lines:
        cv2.putText(
            annotated_frame,
            line,
            (20, y_offset),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2
        )
        y_offset += 25

    return annotated_frame
