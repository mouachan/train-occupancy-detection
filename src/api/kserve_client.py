import requests
import numpy as np
import cv2
import time
from typing import List, Optional
from pathlib import Path

from .schemas import (
    KServeInferenceRequest,
    KServeInferenceResponse,
    KServeInferenceInput,
    DetectionResult,
    Detection,
    ModelMetadata,
    HealthResponse
)


class KServeClient:
    """REST API client for KServe-deployed YOLO models on OpenShift AI."""

    def __init__(self, endpoint_url: str, model_name: str, timeout: int = 30):
        """
        Initialize KServe client.

        Args:
            endpoint_url: Base URL of the KServe endpoint
            model_name: Name of the deployed model
            timeout: Request timeout in seconds
        """
        self.endpoint_url = endpoint_url.rstrip('/')
        self.model_name = model_name
        self.timeout = timeout
        self.session = requests.Session()

        # Inference endpoint
        self.infer_url = f"{self.endpoint_url}/v2/models/{model_name}/infer"
        self.metadata_url = f"{self.endpoint_url}/v2/models/{model_name}"
        self.health_url = f"{self.endpoint_url}/v2/health/live"

    def preprocess_image(self, image: np.ndarray, input_size: int = 640) -> tuple:
        """
        Preprocess image for ONNX model input (same as ONNX detector).

        Args:
            image: Input image (BGR format)
            input_size: Target input size

        Returns:
            Tuple of (preprocessed_tensor, scale, padding, original_shape)
        """
        h, w = image.shape[:2]

        # Calculate scale and padding
        scale = min(input_size / h, input_size / w)
        new_h, new_w = int(h * scale), int(w * scale)

        # Resize
        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        # Pad
        pad_h = (input_size - new_h) // 2
        pad_w = (input_size - new_w) // 2

        padded = np.full((input_size, input_size, 3), 114, dtype=np.uint8)
        padded[pad_h:pad_h + new_h, pad_w:pad_w + new_w] = resized

        # Normalize and convert
        input_image = cv2.cvtColor(padded, cv2.COLOR_BGR2RGB)
        input_image = input_image.astype(np.float32) / 255.0
        input_image = input_image.transpose(2, 0, 1)
        input_image = np.expand_dims(input_image, axis=0)

        return input_image, scale, (pad_w, pad_h), (h, w)

    def postprocess_output(self, output_data: List[float], scale: float, padding: tuple,
                          orig_shape: tuple, conf_threshold: float = 0.25, iou_threshold: float = 0.45) -> List[Detection]:
        """
        Postprocess model output to extract person detections.

        Args:
            output_data: Flattened output data from model
            scale: Scale factor from preprocessing
            padding: Padding (w, h) from preprocessing
            orig_shape: Original image shape (h, w)
            conf_threshold: Confidence threshold
            iou_threshold: IoU threshold for NMS

        Returns:
            List of Detection objects
        """
        # Reshape output data (assuming YOLOv11 format)
        outputs = np.array(output_data).reshape(1, -1, 85)  # [batch, num_detections, 85]
        predictions = outputs[0]

        detections = []
        boxes = []
        scores = []
        person_class_id = 0

        for pred in predictions:
            box = pred[:4]
            obj_conf = pred[4]
            class_scores = pred[5:]

            person_score = class_scores[person_class_id]
            confidence = obj_conf * person_score

            if confidence >= conf_threshold:
                # Convert from center to corner format
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

                # Clip to boundaries
                x1 = max(0, min(x1, orig_shape[1]))
                y1 = max(0, min(y1, orig_shape[0]))
                x2 = max(0, min(x2, orig_shape[1]))
                y2 = max(0, min(y2, orig_shape[0]))

                boxes.append([x1, y1, x2, y2])
                scores.append(float(confidence))

        # Apply NMS
        if boxes:
            indices = cv2.dnn.NMSBoxes(boxes, scores, conf_threshold, iou_threshold)
            if len(indices) > 0:
                for i in indices.flatten():
                    detection = Detection(
                        bbox=boxes[i],
                        confidence=scores[i],
                        class_id=person_class_id,
                        class_name='person'
                    )
                    detections.append(detection)

        return detections

    def predict(self, image: np.ndarray, conf_threshold: float = 0.25) -> DetectionResult:
        """
        Send inference request to KServe endpoint.

        Args:
            image: Input image as numpy array (BGR format)
            conf_threshold: Confidence threshold for detections

        Returns:
            DetectionResult with detected persons
        """
        start_time = time.time()

        # Preprocess image
        input_tensor, scale, padding, orig_shape = self.preprocess_image(image)

        # Prepare KServe V2 request
        request_data = KServeInferenceRequest(
            inputs=[
                KServeInferenceInput(
                    name="images",
                    shape=list(input_tensor.shape),
                    datatype="FP32",
                    data=input_tensor.flatten().tolist()
                )
            ]
        )

        # Send request
        try:
            response = self.session.post(
                self.infer_url,
                json=request_data.dict(),
                timeout=self.timeout
            )
            response.raise_for_status()

            # Parse response
            kserve_response = KServeInferenceResponse(**response.json())

            # Extract output data
            output_data = kserve_response.outputs[0].data

            # Postprocess
            detections = self.postprocess_output(
                output_data, scale, padding, orig_shape, conf_threshold
            )

            inference_time = (time.time() - start_time) * 1000  # Convert to ms

            return DetectionResult(
                detections=detections,
                inference_time_ms=inference_time,
                image_shape=list(orig_shape),
                model_name=kserve_response.model_name
            )

        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Failed to connect to KServe endpoint: {e}")

    def health_check(self) -> bool:
        """
        Check if model serving endpoint is healthy.

        Returns:
            True if endpoint is live, False otherwise
        """
        try:
            response = self.session.get(self.health_url, timeout=self.timeout)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def get_metadata(self) -> Optional[ModelMetadata]:
        """
        Get model metadata from KServe endpoint.

        Returns:
            ModelMetadata object or None if request fails
        """
        try:
            response = self.session.get(self.metadata_url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            return ModelMetadata(**data)
        except requests.exceptions.RequestException:
            return None

    def predict_from_file(self, image_path: str, conf_threshold: float = 0.25) -> DetectionResult:
        """
        Run inference on an image file.

        Args:
            image_path: Path to image file
            conf_threshold: Confidence threshold

        Returns:
            DetectionResult with detected persons
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")

        image = cv2.imread(str(image_path))
        if image is None:
            raise ValueError(f"Could not read image file: {image_path}")

        return self.predict(image, conf_threshold)
