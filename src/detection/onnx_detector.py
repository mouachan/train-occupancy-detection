import cv2
import numpy as np
from pathlib import Path
from typing import List, Tuple
import onnxruntime as ort

from .visualizer import Detection


class ONNXDetector:
    """Person detector using ONNX runtime for YOLOv11 model."""

    def __init__(self, onnx_path: str, conf_threshold: float = 0.25, iou_threshold: float = 0.45, input_size: int = 640):
        """
        Initialize ONNX runtime detector.

        Args:
            onnx_path: Path to ONNX model file
            conf_threshold: Confidence threshold for detections
            iou_threshold: IoU threshold for Non-Maximum Suppression
            input_size: Input image size (typically 640 for YOLO)
        """
        self.onnx_path = Path(onnx_path)
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.input_size = input_size
        self.person_class_id = 0  # COCO person class

        if not self.onnx_path.exists():
            raise FileNotFoundError(f"ONNX model file not found: {onnx_path}")

        # Initialize ONNX Runtime session
        providers = ['CPUExecutionProvider']
        # Try to use GPU if available
        if ort.get_device() == 'GPU':
            providers.insert(0, 'CUDAExecutionProvider')

        self.session = ort.InferenceSession(str(self.onnx_path), providers=providers)

        # Get model input/output names
        self.input_name = self.session.get_inputs()[0].name
        self.output_names = [output.name for output in self.session.get_outputs()]

    def preprocess(self, image: np.ndarray) -> Tuple[np.ndarray, float, Tuple[int, int]]:
        """
        Prepare image for ONNX model input.

        Args:
            image: Input image (BGR format)

        Returns:
            Tuple of (preprocessed_image, scale, (pad_w, pad_h))
        """
        # Get original dimensions
        h, w = image.shape[:2]

        # Calculate scale and padding for letterbox
        scale = min(self.input_size / h, self.input_size / w)
        new_h, new_w = int(h * scale), int(w * scale)

        # Resize image
        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        # Create padded image
        pad_h = (self.input_size - new_h) // 2
        pad_w = (self.input_size - new_w) // 2

        padded = np.full((self.input_size, self.input_size, 3), 114, dtype=np.uint8)
        padded[pad_h:pad_h + new_h, pad_w:pad_w + new_w] = resized

        # Convert to RGB and normalize
        input_image = cv2.cvtColor(padded, cv2.COLOR_BGR2RGB)
        input_image = input_image.astype(np.float32) / 255.0

        # Transpose to CHW format and add batch dimension
        input_image = input_image.transpose(2, 0, 1)
        input_image = np.expand_dims(input_image, axis=0)

        return input_image, scale, (pad_w, pad_h)

    def postprocess(self, outputs: np.ndarray, scale: float, padding: Tuple[int, int], orig_shape: Tuple[int, int]) -> List[Detection]:
        """
        Convert ONNX outputs to detection objects.

        Args:
            outputs: Raw model outputs
            scale: Scale factor used in preprocessing
            padding: Padding (w, h) used in preprocessing
            orig_shape: Original image shape (h, w)

        Returns:
            List of Detection objects after NMS
        """
        # YOLOv11 output format: [batch, num_detections, 85]
        # 85 = x, y, w, h, confidence, 80 class scores
        predictions = outputs[0]

        # Filter by confidence and person class
        detections = []
        boxes = []
        scores = []

        for pred in predictions:
            # Extract box, confidence, and class scores
            box = pred[:4]
            obj_conf = pred[4]
            class_scores = pred[5:]

            # Get person class score
            person_score = class_scores[self.person_class_id]
            confidence = obj_conf * person_score

            if confidence >= self.conf_threshold:
                # Convert from center format to corner format
                cx, cy, w, h = box
                x1 = cx - w / 2
                y1 = cy - h / 2
                x2 = cx + w / 2
                y2 = cy + h / 2

                # Adjust for padding and scale
                pad_w, pad_h = padding
                x1 = (x1 - pad_w) / scale
                y1 = (y1 - pad_h) / scale
                x2 = (x2 - pad_w) / scale
                y2 = (y2 - pad_h) / scale

                # Clip to image boundaries
                x1 = max(0, min(x1, orig_shape[1]))
                y1 = max(0, min(y1, orig_shape[0]))
                x2 = max(0, min(x2, orig_shape[1]))
                y2 = max(0, min(y2, orig_shape[0]))

                boxes.append([x1, y1, x2, y2])
                scores.append(float(confidence))

        # Apply Non-Maximum Suppression
        if boxes:
            indices = cv2.dnn.NMSBoxes(
                boxes,
                scores,
                self.conf_threshold,
                self.iou_threshold
            )

            if len(indices) > 0:
                for i in indices.flatten():
                    detection = Detection(
                        bbox=boxes[i],
                        confidence=scores[i],
                        class_id=self.person_class_id,
                        class_name='person'
                    )
                    detections.append(detection)

        return detections

    def detect_persons(self, frame: np.ndarray) -> List[Detection]:
        """
        Detect persons in a frame using ONNX runtime.

        Args:
            frame: Input image as numpy array (BGR format)

        Returns:
            List of Detection objects
        """
        orig_shape = frame.shape[:2]  # (h, w)

        # Preprocess image
        input_tensor, scale, padding = self.preprocess(frame)

        # Run inference
        outputs = self.session.run(self.output_names, {self.input_name: input_tensor})

        # Postprocess results
        detections = self.postprocess(outputs[0][0], scale, padding, orig_shape)

        return detections

    def get_model_info(self) -> dict:
        """
        Get information about the loaded ONNX model.

        Returns:
            Dictionary with model metadata
        """
        input_info = self.session.get_inputs()[0]
        output_info = self.session.get_outputs()[0]

        return {
            'model_path': str(self.onnx_path),
            'model_type': 'YOLOv11-ONNX',
            'providers': self.session.get_providers(),
            'input_name': self.input_name,
            'input_shape': input_info.shape,
            'output_names': self.output_names,
            'output_shape': output_info.shape,
            'conf_threshold': self.conf_threshold,
            'iou_threshold': self.iou_threshold,
            'target_class': 'person',
            'target_class_id': self.person_class_id
        }
