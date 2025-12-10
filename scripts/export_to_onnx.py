#!/usr/bin/env python3
"""
Export YOLOv11 model to ONNX format for deployment on OpenShift AI.

Usage:
    python scripts/export_to_onnx.py --model models/yolo11n.pt --output models/yolo11n.onnx
"""

import argparse
from pathlib import Path
from ultralytics import YOLO


def export_to_onnx(model_path: str, output_path: str, imgsz: int = 640, dynamic: bool = True, simplify: bool = True):
    """
    Export YOLOv11 model to ONNX format.

    Args:
        model_path: Path to YOLOv11 PyTorch model (.pt)
        output_path: Path for output ONNX model (.onnx)
        imgsz: Input image size (typically 640)
        dynamic: Enable dynamic input shapes
        simplify: Simplify ONNX model using onnx-simplifier
    """
    print(f"Loading model from: {model_path}")
    model = YOLO(model_path)

    print(f"Exporting to ONNX format...")
    print(f"  Image size: {imgsz}")
    print(f"  Dynamic shapes: {dynamic}")
    print(f"  Simplify: {simplify}")

    # Export to ONNX
    success = model.export(
        format='onnx',
        imgsz=imgsz,
        dynamic=dynamic,
        simplify=simplify
    )

    if success:
        # The export method automatically saves to the same directory as the input model
        # We need to move it to the desired output path
        exported_path = Path(model_path).with_suffix('.onnx')

        if exported_path.exists():
            output_path = Path(output_path)
            if exported_path != output_path:
                import shutil
                shutil.move(str(exported_path), str(output_path))

            print(f"\nExport successful!")
            print(f"ONNX model saved to: {output_path}")
            print(f"Model size: {output_path.stat().st_size / (1024**2):.2f} MB")

            return str(output_path)
        else:
            print(f"Error: Expected export file not found at {exported_path}")
            return None
    else:
        print("Export failed!")
        return None


def main():
    parser = argparse.ArgumentParser(description="Export YOLOv11 model to ONNX format")
    parser.add_argument(
        '--model',
        type=str,
        default='models/yolo11n.pt',
        help='Path to YOLOv11 PyTorch model (.pt)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='models/yolo11n.onnx',
        help='Path for output ONNX model (.onnx)'
    )
    parser.add_argument(
        '--imgsz',
        type=int,
        default=640,
        help='Input image size (default: 640)'
    )
    parser.add_argument(
        '--dynamic',
        action='store_true',
        default=True,
        help='Enable dynamic input shapes'
    )
    parser.add_argument(
        '--simplify',
        action='store_true',
        default=True,
        help='Simplify ONNX model'
    )

    args = parser.parse_args()

    # Ensure model file exists
    model_path = Path(args.model)
    if not model_path.exists():
        print(f"Error: Model file not found: {model_path}")
        print(f"\nTo download YOLOv11n model, run:")
        print(f"  from ultralytics import YOLO")
        print(f"  model = YOLO('yolo11n.pt')")
        return

    # Ensure output directory exists
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Export model
    export_to_onnx(
        str(model_path),
        str(output_path),
        args.imgsz,
        args.dynamic,
        args.simplify
    )


if __name__ == '__main__':
    main()
