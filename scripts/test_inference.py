#!/usr/bin/env python3
"""
Test model inference (local YOLO, ONNX, or API).

Usage:
    python scripts/test_inference.py --mode yolo --model models/yolo11n.pt --image test.jpg
    python scripts/test_inference.py --mode onnx --model models/yolo11n.onnx --image test.jpg
    python scripts/test_inference.py --mode api --endpoint http://localhost:8080 --image test.jpg
"""

import argparse
import cv2
import time
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.detection.yolo_detector import YOLODetector
from src.detection.onnx_detector import ONNXDetector
from src.detection.visualizer import draw_detections, create_detection_summary
from src.api.kserve_client import KServeClient


def test_yolo_inference(model_path: str, image_path: str):
    """Test YOLOv11 local inference."""
    print(f"Testing YOLOv11 inference")
    print(f"Model: {model_path}")
    print(f"Image: {image_path}")

    detector = YOLODetector(model_path)
    print(f"Model info: {detector.get_model_info()}")

    start_time = time.time()
    image, detections = detector.process_image(image_path)
    inference_time = (time.time() - start_time) * 1000

    print(f"\nInference time: {inference_time:.2f} ms")
    print(f"Detections: {len(detections)}")

    summary = create_detection_summary(detections)
    print(f"Summary: {summary}")

    # Draw detections
    annotated = draw_detections(image, detections)

    # Save result
    output_path = Path(image_path).with_name(f"{Path(image_path).stem}_yolo_result.jpg")
    cv2.imwrite(str(output_path), annotated)
    print(f"\nAnnotated image saved to: {output_path}")


def test_onnx_inference(model_path: str, image_path: str):
    """Test ONNX runtime inference."""
    print(f"Testing ONNX inference")
    print(f"Model: {model_path}")
    print(f"Image: {image_path}")

    detector = ONNXDetector(model_path)
    print(f"Model info: {detector.get_model_info()}")

    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Could not read image: {image_path}")

    start_time = time.time()
    detections = detector.detect_persons(image)
    inference_time = (time.time() - start_time) * 1000

    print(f"\nInference time: {inference_time:.2f} ms")
    print(f"Detections: {len(detections)}")

    summary = create_detection_summary(detections)
    print(f"Summary: {summary}")

    # Draw detections
    annotated = draw_detections(image, detections)

    # Save result
    output_path = Path(image_path).with_name(f"{Path(image_path).stem}_onnx_result.jpg")
    cv2.imwrite(str(output_path), annotated)
    print(f"\nAnnotated image saved to: {output_path}")


def test_api_inference(endpoint_url: str, model_name: str, image_path: str):
    """Test KServe API inference."""
    print(f"Testing KServe API inference")
    print(f"Endpoint: {endpoint_url}")
    print(f"Model: {model_name}")
    print(f"Image: {image_path}")

    client = KServeClient(endpoint_url, model_name)

    # Health check
    if client.health_check():
        print("Health check: OK")
    else:
        print("Health check: FAILED")
        return

    # Get metadata
    metadata = client.get_metadata()
    if metadata:
        print(f"Model metadata: {metadata.dict()}")

    # Run inference
    result = client.predict_from_file(image_path)

    print(f"\nInference time: {result.inference_time_ms:.2f} ms")
    print(f"Detections: {len(result.detections)}")
    print(f"Image shape: {result.image_shape}")

    summary = create_detection_summary(result.detections)
    print(f"Summary: {summary}")

    # Draw detections
    image = cv2.imread(image_path)
    annotated = draw_detections(image, result.detections)

    # Save result
    output_path = Path(image_path).with_name(f"{Path(image_path).stem}_api_result.jpg")
    cv2.imwrite(str(output_path), annotated)
    print(f"\nAnnotated image saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Test model inference")
    parser.add_argument(
        '--mode',
        type=str,
        choices=['yolo', 'onnx', 'api'],
        required=True,
        help='Inference mode'
    )
    parser.add_argument(
        '--model',
        type=str,
        help='Path to model file (for yolo/onnx mode)'
    )
    parser.add_argument(
        '--endpoint',
        type=str,
        help='KServe endpoint URL (for api mode)'
    )
    parser.add_argument(
        '--model-name',
        type=str,
        default='yolo11-person-detection',
        help='Model name for API (default: yolo11-person-detection)'
    )
    parser.add_argument(
        '--image',
        type=str,
        required=True,
        help='Path to test image'
    )

    args = parser.parse_args()

    if args.mode in ['yolo', 'onnx'] and not args.model:
        parser.error(f"--model required for {args.mode} mode")

    if args.mode == 'api' and not args.endpoint:
        parser.error("--endpoint required for api mode")

    if not Path(args.image).exists():
        print(f"Error: Image file not found: {args.image}")
        return

    try:
        if args.mode == 'yolo':
            test_yolo_inference(args.model, args.image)
        elif args.mode == 'onnx':
            test_onnx_inference(args.model, args.image)
        elif args.mode == 'api':
            test_api_inference(args.endpoint, args.model_name, args.image)
    except Exception as e:
        print(f"Error during inference: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
