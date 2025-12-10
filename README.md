# Train Occupancy Detection System

A comprehensive person detection system using YOLOv11 to identify passengers in train cars at their final destination before parking in the hangar. The system provides real-time video analysis with bounding box visualization and confidence scores, deployable on OpenShift AI.

## Features

- **YOLOv11 Person Detection**: State-of-the-art deep learning model for accurate person detection
- **Dual Deployment Modes**:
  - Local embedded model for development and testing
  - REST API mode for scalable cloud deployment on OpenShift AI
- **Real-time Video Processing**: Process video files with frame-by-frame person detection
- **Visual Analytics**: Bounding boxes, confidence scores, and summary statistics overlay
- **Streamlit Web Interface**: User-friendly monitoring console
- **Production Ready**: Complete Kubernetes manifests for OpenShift deployment

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      User Interface                              │
│              (Streamlit Web Application)                         │
└────────────────┬────────────────────────────────────────────────┘
                 │
        ┌────────┴────────┐
        │                 │
┌───────▼──────┐  ┌───────▼────────────────────────────────┐
│ Local Model  │  │     API Client (KServe V2 Protocol)    │
│  (YOLOv11)   │  └───────┬────────────────────────────────┘
└──────────────┘          │
                 ┌────────▼─────────────────────────────────┐
                 │    OpenShift AI / KServe                  │
                 │  ┌──────────────────────────────────────┐ │
                 │  │  InferenceService                    │ │
                 │  │  (Triton Runtime + ONNX Model)       │ │
                 │  └──────────────────────────────────────┘ │
                 │                                           │
                 │  ┌──────────────────────────────────────┐ │
                 │  │  S3/MinIO Model Storage              │ │
                 │  │  (yolo11n.onnx)                      │ │
                 │  └──────────────────────────────────────┘ │
                 └───────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.11+
- pip
- (Optional) CUDA-capable GPU for faster inference
- (For deployment) OpenShift cluster with OpenShift AI installed

### Local Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd train-occupancy-detection
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Download YOLOv11 model:
```python
from ultralytics import YOLO
model = YOLO('yolo11n.pt')
# Model will be downloaded automatically
```

4. Run local detection test:
```bash
python scripts/test_inference.py --mode yolo --model models/yolo11n.pt --image test_image.jpg
```

### Running Jupyter Notebooks

1. Install Jupyter dependencies:
```bash
pip install -r requirements.txt
```

2. Launch Jupyter:
```bash
jupyter notebook
```

3. Open and run notebooks:
   - `notebooks/01_local_detection.ipynb` - Test local YOLOv11 model
   - `notebooks/02_export_and_upload.ipynb` - Export to ONNX and upload to S3
   - `notebooks/03_api_detection.ipynb` - Test REST API inference

### Running Streamlit Application

1. Install Streamlit dependencies:
```bash
pip install -r requirements-streamlit.txt
```

2. Download YOLOv11 model (if not already done):
```bash
python -c "from ultralytics import YOLO; YOLO('yolo11n.pt')"
mkdir -p models
mv yolo11n.pt models/
```

3. Launch Streamlit app:
```bash
streamlit run streamlit_app/app.py
```

4. Open browser to `http://localhost:8501`

5. Upload a video file and select detection mode (Local or API)

## Deployment on OpenShift AI

### Step 1: Export Model to ONNX

```bash
python scripts/export_to_onnx.py \
    --model models/yolo11n.pt \
    --output models/yolo11n.onnx \
    --imgsz 640 \
    --dynamic
```

### Step 2: Upload Model to S3/MinIO

```bash
# Set credentials
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"

# For MinIO with self-signed HTTPS certificates, disable SSL verification
export AWS_S3_VERIFY_SSL=0  # Set to 1 or omit for valid certificates

# Upload model
python scripts/upload_to_s3.py \
    --model models/yolo11n.onnx \
    --bucket train-detection-models \
    --endpoint https://s3.your-cluster.com
```

**Note**: For SSL/HTTPS configuration details, see [S3_SSL_CONFIG.md](S3_SSL_CONFIG.md)

### Step 3: Deploy Model Serving on OpenShift AI

1. Create namespace:
```bash
oc new-project train-detection
```

2. Create S3 credentials secret:
```bash
# Copy and edit the template
cp openshift/model-serving/s3-secret.yaml.template openshift/model-serving/s3-secret.yaml
# Edit s3-secret.yaml with your credentials

# Apply secret
oc apply -f openshift/model-serving/s3-secret.yaml
```

3. Deploy ServingRuntime:
```bash
oc apply -f openshift/model-serving/serving-runtime.yaml
```

4. Update InferenceService with your S3 URI:
```bash
# Edit inference-service.yaml and update storageUri
vi openshift/model-serving/inference-service.yaml

# Apply InferenceService
oc apply -f openshift/model-serving/inference-service.yaml
```

5. Wait for deployment to be ready:
```bash
oc get inferenceservice yolo11-person-detection -w
```

6. Test the endpoint:
```bash
# Get the endpoint URL
ENDPOINT=$(oc get inferenceservice yolo11-person-detection -o jsonpath='{.status.url}')

# Test inference
python scripts/test_inference.py \
    --mode api \
    --endpoint $ENDPOINT \
    --image test_image.jpg
```

### Step 4: Deploy Streamlit Application on OpenShift

1. Build and push container image:
```bash
# Build image with podman
podman build -f Dockerfile.streamlit -t train-detection-streamlit:latest .

# Tag for Quay.io registry (replace 'username' with your Quay.io username)
podman tag train-detection-streamlit:latest \
    quay.io/username/train-detection-streamlit:latest

# Login to Quay.io
podman login quay.io

# Push image
podman push quay.io/username/train-detection-streamlit:latest
```

2. Update deployment with your Quay.io username:
```bash
# Edit deployment.yaml and replace 'username' with your actual Quay.io username
vi openshift/streamlit-app/deployment.yaml
# Update line: image: quay.io/username/train-detection-streamlit:latest
```

3. Deploy Kubernetes resources:
```bash
# Apply ConfigMap
oc apply -f openshift/streamlit-app/configmap.yaml

# Apply PVC
oc apply -f openshift/streamlit-app/pvc.yaml

# Apply Deployment
oc apply -f openshift/streamlit-app/deployment.yaml

# Apply Service
oc apply -f openshift/streamlit-app/service.yaml

# Apply Route
oc apply -f openshift/streamlit-app/route.yaml
```

4. Get application URL:
```bash
oc get route train-detection-streamlit -o jsonpath='{.spec.host}'
```

5. Access the application in your browser using the route URL.

## Project Structure

```
train-occupancy-detection/
├── src/                          # Core application source code
│   ├── detection/               # Detection modules
│   │   ├── yolo_detector.py    # YOLOv11 local inference
│   │   ├── onnx_detector.py    # ONNX runtime inference
│   │   └── visualizer.py       # Bounding box rendering
│   ├── api/                     # API client modules
│   │   ├── kserve_client.py    # KServe REST API client
│   │   └── schemas.py          # Data models
│   └── utils/                   # Utility modules
│       ├── video_processor.py  # Video handling
│       └── config.py           # Configuration
├── notebooks/                   # Jupyter notebooks
│   ├── 01_local_detection.ipynb
│   ├── 02_export_and_upload.ipynb
│   └── 03_api_detection.ipynb
├── streamlit_app/              # Streamlit web application
│   └── app.py
├── openshift/                   # OpenShift deployment manifests
│   ├── model-serving/          # Model serving configuration
│   │   ├── serving-runtime.yaml
│   │   ├── inference-service.yaml
│   │   └── s3-secret.yaml.template
│   └── streamlit-app/          # Streamlit app deployment
│       ├── deployment.yaml
│       ├── service.yaml
│       ├── route.yaml
│       ├── configmap.yaml
│       └── pvc.yaml
├── scripts/                     # Utility scripts
│   ├── export_to_onnx.py
│   ├── upload_to_s3.py
│   └── test_inference.py
├── models/                      # Model artifacts
├── tests/                       # Unit tests
├── requirements.txt            # Core dependencies
├── requirements-streamlit.txt  # Streamlit dependencies
├── Dockerfile.streamlit        # Container image
└── README.md                   # This file
```

## Usage

### Command-Line Inference

Test inference with different modes:

```bash
# Local YOLOv11 inference
python scripts/test_inference.py \
    --mode yolo \
    --model models/yolo11n.pt \
    --image test_image.jpg

# ONNX runtime inference
python scripts/test_inference.py \
    --mode onnx \
    --model models/yolo11n.onnx \
    --image test_image.jpg

# API inference (OpenShift AI)
python scripts/test_inference.py \
    --mode api \
    --endpoint http://yolo11-person-detection.apps.cluster.com \
    --model-name yolo11-person-detection \
    --image test_image.jpg
```

### Python API

```python
from src.detection.yolo_detector import YOLODetector
from src.detection.visualizer import draw_detections
import cv2

# Initialize detector
detector = YOLODetector(model_path='models/yolo11n.pt')

# Process image
image, detections = detector.process_image('test.jpg')

# Visualize
annotated = draw_detections(image, detections)
cv2.imwrite('result.jpg', annotated)

# Print detections
for i, det in enumerate(detections):
    print(f"Person {i+1}: confidence={det.confidence:.2f}, bbox={det.bbox}")
```

### REST API Client

```python
from src.api.kserve_client import KServeClient

# Initialize client
client = KServeClient(
    endpoint_url='http://yolo11-person-detection.apps.cluster.com',
    model_name='yolo11-person-detection'
)

# Health check
if client.health_check():
    print("API is healthy")

# Run inference
result = client.predict_from_file('test.jpg')
print(f"Detected {len(result.detections)} persons")
print(f"Inference time: {result.inference_time_ms:.2f} ms")
```

## Configuration

### Environment Variables

- `KSERVE_ENDPOINT`: KServe inference endpoint URL
- `MODEL_NAME`: Model name for API inference
- `MAX_UPLOAD_SIZE_MB`: Maximum video upload size (default: 500 MB)
- `AWS_ACCESS_KEY_ID`: S3 access key
- `AWS_SECRET_ACCESS_KEY`: S3 secret key
- `AWS_S3_ENDPOINT`: S3 endpoint URL
- `AWS_S3_VERIFY_SSL`: Enable/disable SSL verification (set to `0` to disable for self-signed certs, default: `1`)

### Detection Parameters

- `conf_threshold`: Confidence threshold for detections (default: 0.25)
- `iou_threshold`: IoU threshold for NMS (default: 0.45)
- `input_size`: Input image size (default: 640)

## Performance

### YOLOv11n Benchmarks

**Local Inference (CPU - Intel i7):**
- Inference time: ~50-60 ms per frame
- Throughput: ~18 FPS
- Memory: ~500 MB

**ONNX Runtime (CPU):**
- Inference time: ~25-30 ms per frame
- Throughput: ~35 FPS
- Memory: ~400 MB

**API Inference (OpenShift AI):**
- Inference time: ~80-100 ms per request (including network overhead)
- Throughput: ~10-12 requests/sec
- Scalable with auto-scaling

**GPU Inference (NVIDIA T4):**
- Inference time: ~5-8 ms per frame
- Throughput: ~120+ FPS

## Troubleshooting

### Model Not Found

**Error**: `Model file not found: models/yolo11n.pt`

**Solution**:
```python
from ultralytics import YOLO
model = YOLO('yolo11n.pt')
```

### ONNX Export Fails

**Error**: `ONNX export failed`

**Solution**: Install required packages:
```bash
pip install --upgrade ultralytics onnx onnxruntime
```

### API Connection Failed

**Error**: `Failed to connect to KServe endpoint`

**Solution**:
1. Verify endpoint URL is correct
2. Check InferenceService status: `oc get inferenceservice`
3. Check network connectivity
4. For local testing, use port-forward:
```bash
oc port-forward svc/yolo11-person-detection 8080:8080
```

### Streamlit Upload Size Limit

**Error**: `File too large`

**Solution**: Update `MAX_UPLOAD_SIZE_MB` in ConfigMap:
```bash
oc edit configmap streamlit-config
```

### Out of Memory

**Error**: `CUDA out of memory` or system OOM

**Solution**:
1. Reduce batch size
2. Use smaller model (yolo11n instead of yolo11x)
3. Process fewer frames (increase skip_frames)
4. Increase resource limits in deployment.yaml

## Development

### Running Tests

```bash
# Install test dependencies
pip install -r requirements.txt

# Run tests
pytest tests/

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

### Code Style

This project follows PEP 8 style guidelines. Format code with:
```bash
pip install black flake8
black src/
flake8 src/
```

## Performance Optimization

### For Production Deployment

1. **Use ONNX format**: 2-3x faster than PyTorch
2. **Enable GPU**: Add NVIDIA GPU resources to InferenceService
3. **Adjust scaling**: Configure autoscaling based on load
4. **Optimize video processing**: Increase skip_frames for real-time processing
5. **Use TensorRT**: Convert ONNX to TensorRT for maximum GPU performance

### For Edge Deployment

1. **Use quantized models**: INT8 quantization for CPU
2. **Reduce model size**: Use yolo11n (smallest variant)
3. **Frame sampling**: Process every Nth frame
4. **Resolution reduction**: Scale down input resolution

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -am 'Add new feature'`
4. Push to the branch: `git push origin feature/your-feature`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## References

- [YOLOv11 Documentation](https://docs.ultralytics.com/models/yolo11/)
- [OpenShift AI Documentation](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed)
- [KServe Documentation](https://kserve.github.io/website/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [ONNX Runtime](https://onnxruntime.ai/)

## Acknowledgments

- [Ultralytics](https://ultralytics.com/) for YOLOv11
- [OpenShift AI](https://www.redhat.com/en/technologies/cloud-computing/openshift/openshift-ai) for model serving platform
- [KServe](https://kserve.github.io/) for inference serving protocol

## Support

For issues, questions, or contributions, please open an issue on the GitHub repository.
