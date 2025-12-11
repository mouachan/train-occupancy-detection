# Train Occupancy Detection System

A comprehensive person detection system using YOLOv11 to identify passengers in train cars at their final destination before parking in the hangar. The system provides real-time video analysis with bounding box visualization, confidence scores, and automated deployment on OpenShift AI with complete infrastructure automation.

## Features

- **YOLOv11 Person Detection**: State-of-the-art deep learning model (ONNX) for accurate person detection
- **Real-time Video Processing**: Process video files with frame-by-frame person detection and occupancy metrics
- **Visual Analytics**: Bounding boxes, confidence scores, and comprehensive statistics with charts
- **Automated Storage**: Detection logs and annotated frames saved to MinIO S3-compatible storage
- **Streamlit Web Interface**: User-friendly monitoring console with statistics dashboard
- **One-Command Deployment**: Complete automated deployment on OpenShift with Kustomize
- **Flexible Namespace**: Deploy to any OpenShift namespace with single variable
- **Production Ready**: Complete infrastructure automation including MinIO, KServe, and Streamlit

## Architecture

```
┌───────────────────────────────────────────────────────────────────────┐
│                          OpenShift Cluster                             │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │                   User Interface Layer                            │ │
│  │         Streamlit Web Application (2 replicas)                    │ │
│  │         Route: https://train-detection-streamlit.apps...          │ │
│  └────────────┬─────────────────────────────────────────────────────┘ │
│               │                                                        │
│       ┌───────┴───────┐                                               │
│       │               │                                               │
│  ┌────▼─────┐  ┌──────▼──────────────────────────────────────┐       │
│  │  MinIO   │  │      Model Serving (KServe)                 │       │
│  │  S3      │  │  ┌────────────────────────────────────────┐ │       │
│  │  Storage │◄─┤  │  InferenceService                      │ │       │
│  │          │  │  │  train-detection-model                 │ │       │
│  │  Buckets:│  │  │                                        │ │       │
│  │  • models│  │  │  ┌──────────────────────────────────┐ │ │       │
│  │  • train-│  │  │  │ Storage Initializer              │ │ │       │
│  │    detect│  │  │  │ Downloads from S3: s3://models   │ │ │       │
│  │    ions  │  │  │  └──────────────┬───────────────────┘ │ │       │
│  │          │  │  │                 │                       │ │       │
│  │  Routes: │  │  │  ┌──────────────▼───────────────────┐ │ │       │
│  │  • API   │  │  │  │  Triton Inference Server         │ │ │       │
│  │  • Console│ │  │  │  Runtime: onnxruntime            │ │ │       │
│  └──────────┘  │  │  │  Model: yolo11n.onnx             │ │ │       │
│                │  │  │  Endpoint: /v2/models/yolo11n    │ │ │       │
│                │  │  └──────────────────────────────────┘ │ │       │
│                │  │                                        │ │       │
│                │  │  Route: https://train-detection-model  │ │       │
│                │  └────────────────────────────────────────┘ │       │
│                └───────────────────────────────────────────────┘       │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │              Automated Initialization                             │ │
│  │  minio-init Job (runs on deployment):                            │ │
│  │  1. Downloads yolo11n.onnx from GitHub                           │ │
│  │  2. Creates MinIO buckets and directory structure                │ │
│  │  3. Uploads model and config.pbtxt to S3                         │ │
│  └──────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
User uploads video → Streamlit App
                         ↓
            Frame extraction & preprocessing
                         ↓
            HTTP POST to InferenceService
            (KServe V2 Protocol)
                         ↓
      Triton loads model from /mnt/models/yolo11n/1/
                         ↓
            YOLO inference on ONNX model
                         ↓
            Detections returned to Streamlit
                         ↓
        ┌────────────────┴────────────────┐
        ↓                                  ↓
  Visualization                    Save to MinIO
  (bounding boxes,              (detection logs +
   statistics charts)            annotated frames)
```

## Quick Start - Automated Deployment on OpenShift

### Prerequisites

- OpenShift cluster access with `oc` CLI installed
- OpenShift AI installed on the cluster
- Logged in to OpenShift: `oc login`
- Quay.io account for Streamlit image (or use existing `quay.io/mouachan/train-detection-streamlit:latest`)

### One-Command Deployment

1. **Clone the repository**:
```bash
git clone https://github.com/mouachan/train-occupancy-detection
cd train-occupancy-detection/openshift
```

2. **Create MinIO credentials** (first time only):
```bash
cp minio/secret-template.yaml minio/secret.yaml
# Edit credentials in minio/secret.yaml (default: admin/minio123)
```

3. **Deploy everything** to any namespace:
```bash
# Deploy to default namespace (train-detection)
./deploy-all.sh

# Or deploy to custom namespace
NAMESPACE=my-project ./deploy-all.sh
```

That's it! The script automatically:
- ✅ Creates namespace if doesn't exist
- ✅ Installs Triton ServingRuntime template (shared in redhat-ods-applications)
- ✅ Deploys MinIO S3 storage with routes
- ✅ Downloads YOLOv11 model from GitHub
- ✅ Creates model directory structure and uploads model to MinIO
- ✅ Creates S3 credentials with actual MinIO route URL
- ✅ Deploys InferenceService with Triton runtime
- ✅ Deploys Streamlit application (2 replicas)
- ✅ Configures all networking (Services & Routes)
- ✅ Waits for all components to be ready

### Accessing the Application

After deployment completes, access points will be displayed:

```
Access Points:
  📊 Streamlit App:    https://train-detection-streamlit-NAMESPACE.apps...
  🤖 Model API:        https://train-detection-model-NAMESPACE.apps...
  💾 MinIO Console:    https://minio-console-NAMESPACE.apps...
  📦 MinIO S3 API:     https://minio-api-NAMESPACE.apps...
```

### Cleanup

Remove all resources from a namespace:
```bash
NAMESPACE=my-project ./cleanup-all.sh
```

## Features in Detail

### Person Detection & Counting

- **Frame-by-frame analysis**: Process every frame of uploaded video
- **Bounding box visualization**: Visual overlay with confidence scores
- **Occupancy metrics**:
  - Maximum persons detected (peak occupancy)
  - Average persons per frame
  - Real-time frame counter

### Statistics Dashboard

Interactive charts powered by Plotly:
- **Occupancy over time**: Line chart showing person count per frame
- **Distribution histogram**: Frequency of different occupancy levels
- **Summary statistics**: Max, average, total frames processed
- **Occupancy breakdown**: Low/Medium/High occupancy percentages

### Automated MinIO Storage

All detection results automatically saved to MinIO:
- **Detection logs** (JSON format):
  - Video name and timestamp
  - Frame-by-frame person counts
  - Summary statistics (max, average)
  - Stored in: `train-detections/logs/{video_name}_{timestamp}.json`

- **Annotated frames** (JPEG format):
  - Every 10th frame with bounding boxes
  - Stored in: `train-detections/frames/{video_name}_{timestamp}/frame_{N}.jpg`

## Project Structure

```
train-occupancy-detection/
├── openshift/                      # OpenShift deployment (Kustomize)
│   ├── deploy-all.sh              # Automated deployment script
│   ├── cleanup-all.sh             # Cleanup script
│   ├── kustomization.yaml         # Main Kustomize config
│   │
│   ├── minio/                     # MinIO S3 storage
│   │   ├── deployment.yaml        # MinIO deployment
│   │   ├── service.yaml           # Internal service
│   │   ├── route-api.yaml         # S3 API route (external)
│   │   ├── route-console.yaml     # Web console route
│   │   ├── pvc.yaml               # Persistent storage (10Gi)
│   │   ├── secret-template.yaml   # Credentials template
│   │   └── init-job.yaml          # Initialization job
│   │                              # - Downloads model from GitHub
│   │                              # - Creates buckets & structure
│   │                              # - Uploads model to S3
│   │
│   ├── model-serving/             # KServe InferenceService
│   │   ├── template-triton-runtime.yaml  # Triton runtime template
│   │   ├── service-account.yaml   # ServiceAccount for S3 access
│   │   ├── s3-secret-template.yaml # S3 credentials template
│   │   └── inference-service.yaml # InferenceService manifest
│   │                              # - storageUri: s3://models/model
│   │                              # - Runtime: triton-runtime
│   │
│   └── streamlit-app/             # Streamlit web application
│       ├── deployment.yaml        # Deployment (2 replicas)
│       ├── service.yaml           # ClusterIP service
│       ├── route.yaml             # External HTTPS route
│       ├── configmap.yaml         # Configuration
│       │                          # - KServe endpoint URL
│       │                          # - MinIO configuration
│       └── pvc.yaml               # Video upload storage
│
├── streamlit_app/                 # Streamlit application code
│   ├── app.py                    # Main application
│   │                             # - Video upload interface
│   │                             # - Real-time detection display
│   │                             # - Statistics dashboard
│   │                             # - MinIO integration
│   └── pages/
│       └── 01_Statistics.py      # Statistics page with charts
│
├── models/                        # Model artifacts
│   ├── yolo11n.onnx              # YOLOv11n ONNX model (10MB)
│   └── README.md                 # Model documentation
│
├── notebooks/                     # Jupyter notebooks
│   ├── 01_local_detection.ipynb  # Local YOLO testing
│   ├── 02_export_and_upload.ipynb # ONNX export & S3 upload
│   └── 03_api_detection.ipynb    # KServe API testing
│
├── Dockerfile.streamlit-api       # Lightweight container (API mode)
├── requirements-streamlit-api.txt # Minimal dependencies (~500MB)
└── README.md                      # This file
```

## Configuration

### Streamlit ConfigMap

`openshift/streamlit-app/configmap.yaml`:

```yaml
kserve_endpoint: "https://train-detection-model-NAMESPACE.apps..."
model_name: "yolo11n"
confidence_threshold: "0.25"
max_upload_size_mb: "500"

# MinIO configuration (optional - for saving results)
minio_endpoint: "https://minio-api-NAMESPACE.apps..."
minio_access_key: "admin"
minio_secret_key: "minio123"
minio_bucket: "train-detections"
```

### MinIO Credentials

`openshift/minio/secret.yaml`:

```yaml
stringData:
  MINIO_ROOT_USER: "admin"
  MINIO_ROOT_PASSWORD: "minio123"  # Change this!
```

### Flexible Namespace Deployment

Deploy to any namespace by setting `NAMESPACE` variable:

```bash
# Development
NAMESPACE=dev ./deploy-all.sh

# Staging
NAMESPACE=staging ./deploy-all.sh

# Production
NAMESPACE=production ./deploy-all.sh
```

The script automatically:
- Updates `kustomization.yaml` with target namespace
- Creates S3 secret with correct MinIO route for that namespace
- Installs ServingRuntime instance in the namespace
- Deploys all resources with proper namespace configuration

## Triton Model Repository Structure

MinIO automatically creates the correct structure:

```
s3://models/
└── model/                    # Downloaded to /mnt/models/ by storage-initializer
    └── yolo11n/              # Model name (must match InferenceService)
        ├── config.pbtxt      # Triton config (minimal: name, backend, max_batch_size)
        └── 1/                # Version directory
            └── model.onnx    # ONNX model file (10MB)
```

**Config.pbtxt**:
```
name: "yolo11n"
backend: "onnxruntime"
max_batch_size: 0
```

## Usage

### Upload Video for Detection

1. Access Streamlit app via route URL
2. Upload video file (mp4, avi, mov)
3. Click "Start Detection"
4. View real-time results:
   - Annotated frames with bounding boxes
   - Max persons detected
   - Average occupancy
   - Frame-by-frame progress

### View Statistics

1. Go to "Statistics" page in sidebar
2. Select from dropdown of processed videos
3. View interactive charts:
   - Occupancy timeline
   - Distribution histogram
   - Summary metrics

### Access MinIO Console

1. Open MinIO Console URL
2. Login with credentials from `minio/secret.yaml`
3. Browse buckets:
   - `models`: YOLO model files
   - `train-detections`: Detection logs and frames

## Troubleshooting

### InferenceService Not Ready

```bash
# Check InferenceService status
oc get inferenceservice train-detection-model -n NAMESPACE

# Check predictor pod logs
oc logs -l serving.kserve.io/inferenceservice=train-detection-model -c kserve-container

# Common issues:
# - Model not found: Check MinIO has model at models/model/yolo11n/1/model.onnx
# - Config error: Verify config.pbtxt is minimal (name, backend, max_batch_size)
# - S3 connection: Check s3-credentials secret has correct MinIO route URL
```

### Streamlit ImagePullBackOff

```bash
# Check deployment
oc get deployment train-detection-streamlit -n NAMESPACE

# Verify image exists
oc describe deployment train-detection-streamlit -n NAMESPACE | grep Image

# If using custom Quay.io username, update deployment:
oc set image deployment/train-detection-streamlit streamlit=quay.io/YOUR_USERNAME/train-detection-streamlit:latest
```

### MinIO Init Job Failed

```bash
# Check job status
oc get job minio-init -n NAMESPACE

# View logs
oc logs job/minio-init -c download-model  # Model download
oc logs job/minio-init -c init-minio      # MinIO upload

# Recreate job if needed
oc delete job minio-init -n NAMESPACE
oc apply -f minio/init-job.yaml -n NAMESPACE
```

### Model Not Loading in Triton

**Error**: "No model version was found"

**Check**:
1. Model exists in MinIO: `mc ls myminio/models/model/yolo11n/1/`
2. Config.pbtxt exists: `mc cat myminio/models/model/yolo11n/config.pbtxt`
3. InferenceService storageUri: `s3://models/model` (not `s3://models`)
4. Restart predictor: `oc rollout restart deployment train-detection-model-predictor`

## Performance

### Resource Usage

**MinIO**:
- CPU: 100m request, 500m limit
- Memory: 256Mi request, 1Gi limit
- Storage: 10Gi PVC

**InferenceService (Triton)**:
- CPU: 2 cores (requests = limits)
- Memory: 4Gi (requests = limits)
- Replicas: 1-3 (autoscaling on concurrency)

**Streamlit**:
- CPU: 250m request, 1 core limit
- Memory: 512Mi request, 2Gi limit
- Replicas: 2 (high availability)

### Inference Performance

**ONNX Model on CPU**:
- Inference time: ~25-30 ms per frame
- Throughput: ~35 FPS
- Memory: ~400 MB

**With Network Overhead**:
- End-to-end: ~80-100 ms per request
- Includes: preprocessing + network + inference + postprocessing

## Development

### Building Custom Streamlit Image

```bash
# Build lightweight API-only image
podman build --platform linux/amd64 -f Dockerfile.streamlit-api -t train-detection-streamlit:latest .

# Tag for Quay.io
podman tag train-detection-streamlit:latest quay.io/YOUR_USERNAME/train-detection-streamlit:latest

# Push to registry
podman login quay.io
podman push quay.io/YOUR_USERNAME/train-detection-streamlit:latest

# Update deployment
# Edit openshift/streamlit-app/deployment.yaml:
# image: quay.io/YOUR_USERNAME/train-detection-streamlit:latest
```

### Testing Locally

```bash
# Install dependencies
pip install -r requirements-streamlit-api.txt

# Set environment variables
export KSERVE_ENDPOINT="https://train-detection-model-NAMESPACE.apps..."
export MODEL_NAME="yolo11n"

# Run Streamlit
streamlit run streamlit_app/app.py
```

## Advanced Topics

### Adding New Model

1. Place ONNX model in `models/` directory
2. Update `models/yolo11n.onnx` or change init-job.yaml GitHub URL
3. Update `config.pbtxt` model name in init-job.yaml
4. Push to GitHub
5. Redeploy: delete and recreate minio-init job

### Scaling InferenceService

```bash
# Edit autoscaling parameters
oc edit inferenceservice train-detection-model

# spec:
#   predictor:
#     minReplicas: 2
#     maxReplicas: 5
#     scaleTarget: 100  # concurrent requests
```

### Custom Confidence Threshold

Update ConfigMap and restart Streamlit:
```bash
oc edit configmap streamlit-config -n NAMESPACE
# Change confidence_threshold: "0.25" to desired value

oc rollout restart deployment train-detection-streamlit -n NAMESPACE
```

## References

- [YOLOv11 Documentation](https://docs.ultralytics.com/models/yolo11/)
- [OpenShift AI Documentation](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed)
- [KServe Documentation](https://kserve.github.io/website/)
- [Triton Inference Server](https://github.com/triton-inference-server/server)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [MinIO Documentation](https://min.io/docs/minio/linux/index.html)
- [Kustomize Documentation](https://kustomize.io/)

## License

This project is licensed under the MIT License.

## Support

For issues or questions, please open an issue on the [GitHub repository](https://github.com/mouachan/train-occupancy-detection).
