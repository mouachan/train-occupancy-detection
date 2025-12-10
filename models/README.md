# Models Directory

This directory contains the YOLOv11 model files for person detection.

## Model Files

### YOLOv11n PyTorch Model (`yolo11n.pt`)
- **Type**: PyTorch model
- **Size**: ~6 MB
- **Use Case**: Local development and testing
- **Download**: Automatically downloaded by ultralytics library

```python
from ultralytics import YOLO
model = YOLO('yolo11n.pt')  # Will download if not present
```

### YOLOv11n ONNX Model (`yolo11n.onnx`)
- **Type**: ONNX format (optimized for inference)
- **Size**: ~6 MB
- **Use Case**: Production deployment on OpenShift AI
- **Export**: Use the export script

```bash
python scripts/export_to_onnx.py --model models/yolo11n.pt --output models/yolo11n.onnx
```

## Model Variants

YOLOv11 comes in different sizes. You can use any of these variants:

| Model | Size (MB) | mAP | Speed (ms) | Use Case |
|-------|-----------|-----|------------|----------|
| yolo11n.pt | ~6 | 39.5 | 1.5 | Edge devices, real-time |
| yolo11s.pt | ~22 | 46.7 | 2.5 | Balanced performance |
| yolo11m.pt | ~50 | 51.5 | 5.0 | Higher accuracy |
| yolo11l.pt | ~60 | 53.4 | 7.0 | High accuracy |
| yolo11x.pt | ~140 | 54.7 | 12.0 | Maximum accuracy |

## Downloading Models

### Method 1: Automatic Download (Recommended)
```python
from ultralytics import YOLO
model = YOLO('yolo11n.pt')
```

### Method 2: Manual Download
Download from Ultralytics GitHub releases or official website.

## Person Detection

The models are trained on the COCO dataset, which includes 80 classes. For this project, we filter only the "person" class (class ID: 0).

## Model Performance

### YOLOv11n Benchmarks
- **Input Size**: 640x640
- **FPS (CPU)**: ~60 FPS
- **FPS (GPU)**: ~200+ FPS
- **Person Detection mAP**: ~60%

## ONNX Export Parameters

Default export settings:
- **Format**: ONNX
- **Image Size**: 640x640
- **Dynamic Shapes**: Enabled
- **Simplify**: Enabled
- **Opset Version**: 17

## Storage Requirements

For OpenShift AI deployment, the ONNX model needs to be stored in S3/MinIO:

```bash
# Upload to S3
python scripts/upload_to_s3.py \
    --model models/yolo11n.onnx \
    --bucket train-detection-models \
    --endpoint https://s3.your-cluster.com
```

## Model Optimization

### For CPU Inference
- Use ONNX Runtime with optimization level 3
- Enable quantization (INT8) for faster inference

### For GPU Inference
- Use TensorRT backend with ONNX
- FP16 precision for 2x speedup

## Troubleshooting

### Model Not Found
```
Error: Model file not found: models/yolo11n.pt
```
**Solution**: Run the download script or use ultralytics to download automatically.

### ONNX Export Fails
```
Error: ONNX export failed
```
**Solution**: Ensure ultralytics and onnx packages are installed:
```bash
pip install ultralytics onnx onnxruntime
```

### Model Version Mismatch
If you encounter version issues, ensure you're using the latest ultralytics version:
```bash
pip install --upgrade ultralytics
```

## References

- [YOLOv11 Documentation](https://docs.ultralytics.com/models/yolo11/)
- [ONNX Export Guide](https://docs.ultralytics.com/integrations/onnx/)
- [Ultralytics GitHub](https://github.com/ultralytics/ultralytics)
