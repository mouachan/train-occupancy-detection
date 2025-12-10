# Model Serving on OpenShift AI

This directory contains manifests for deploying YOLOv11 models on OpenShift AI using KServe.

## Components

### 1. ServingRuntime

The ServingRuntime defines how models are served using NVIDIA Triton Inference Server.

**Two Deployment Options:**

- **`serving-runtime.yaml`** - Project-scoped runtime (namespace: train-detection)
  - Deployed in a specific namespace
  - Only available to that namespace
  - Use for project-specific configurations

- **`serving-runtime-global.yaml`** - Global-scoped runtime (cluster-wide)
  - Deployed without namespace (cluster-wide)
  - Available to all projects in OpenShift AI
  - Appears in the dropdown list when deploying models (like OpenVINO)
  - Requires cluster-admin privileges to deploy

**Key Features:**
- ✅ **OpenShift AI Dashboard Integration**: `opendatahub.io/dashboard: "true"` label makes it visible in the UI
- ✅ **Prometheus Metrics**: Configured on port 8002 with `/metrics` endpoint
- ✅ **Multiple Model Formats**: ONNX, TensorRT, TensorFlow, PyTorch, Python
- ✅ **Triton 24.09**: Latest stable version with improved ONNX support
- ✅ **Health Probes**: Liveness and readiness checks for reliability

**Supported Formats:**
- ONNX (version 1) - **Primary for YOLOv11** ✓
- TensorRT (version 8)
- TensorFlow (versions 1 & 2)
- PyTorch (version 1)
- Triton (version 2)
- Python (version 1)

**Resources:**
- Requests: 1 CPU, 2Gi Memory
- Limits: 2 CPU, 4Gi Memory

### 2. InferenceService (`inference-service.yaml`)

Deploys the YOLOv11 ONNX model using the ServingRuntime.

**Configuration:**
- Model location: S3/MinIO bucket
- Auto-scaling: 1-3 replicas
- KServe V2 protocol

### 3. S3 Credentials (`s3-secret.yaml.template`)

Template for S3/MinIO access credentials.

## Deployment Guide

### Prerequisites

1. OpenShift AI installed and configured
2. Namespace created: `train-detection`
3. Model exported to ONNX and uploaded to S3

### Step 1: Create Namespace

```bash
oc new-project train-detection
```

### Step 2: Create S3 Secret

```bash
# Copy template
cp s3-secret.yaml.template s3-secret.yaml

# Edit with your credentials
vi s3-secret.yaml

# Apply secret
oc apply -f s3-secret.yaml
```

**Required fields in secret:**
- `AWS_ACCESS_KEY_ID`: MinIO/S3 access key
- `AWS_SECRET_ACCESS_KEY`: MinIO/S3 secret key
- `AWS_S3_ENDPOINT`: S3 endpoint URL (e.g., `https://minio.example.com`)
- `AWS_DEFAULT_REGION`: Region (default: `us-east-1`)

### Step 3: Deploy ServingRuntime

**Option A: Project-scoped (Recommended for single project)**

```bash
oc apply -f serving-runtime.yaml
```

**Verify deployment:**
```bash
# Check ServingRuntime
oc get servingruntime yolo11-triton-runtime -n train-detection

# Should show:
NAME                    DISABLED   MODELTYPE   CONTAINERS        AGE
yolo11-triton-runtime   false      onnx        kserve-container  10s
```

**Option B: Global-scoped (Requires cluster-admin, appears in dropdown like OpenVINO)**

```bash
# Deploy globally (requires cluster-admin privileges)
oc apply -f serving-runtime-global.yaml

# Verify global ServingRuntime
oc get servingruntime yolo11-triton-runtime
```

This will make the runtime appear in the **Serving runtime** dropdown when deploying models in OpenShift AI, just like the OpenVINO template.

**Check in OpenShift AI Dashboard:**
1. Open OpenShift AI Console
2. Navigate to "Model Serving" → "Serving Runtimes"
3. You should see "Triton Runtime for YOLOv11"
4. When creating a model deployment, it should appear in the "Serving runtime" dropdown

### Step 4: Update InferenceService

Edit `inference-service.yaml` to point to your S3 model location:

```yaml
spec:
  predictor:
    model:
      storageUri: s3://YOUR_BUCKET/yolo11n.onnx
```

Or use the auto-generated file from the notebook:

```bash
# If you ran notebooks/02_export_and_upload.ipynb
oc apply -f inference-service-generated.yaml
```

### Step 5: Deploy InferenceService

```bash
oc apply -f inference-service.yaml
```

**Monitor deployment:**
```bash
# Watch InferenceService status
oc get inferenceservice yolo11-person-detection -w

# Check pods
oc get pods -l serving.kserve.io/inferenceservice=yolo11-person-detection

# Check logs
oc logs -f deployment/yolo11-person-detection-predictor
```

**Wait for Ready status:**
```
NAME                       URL                                                 READY   PREV   LATEST   AGE
yolo11-person-detection    http://yolo11-person-detection.train-detection...  True    100                 2m
```

### Step 6: Test the Endpoint

**Get the endpoint URL:**
```bash
ENDPOINT=$(oc get inferenceservice yolo11-person-detection -o jsonpath='{.status.url}')
echo $ENDPOINT
```

**Test with curl:**
```bash
# Health check
curl $ENDPOINT/v2/health/live

# Model metadata
curl $ENDPOINT/v2/models/yolo11-person-detection
```

**Test with Python notebook:**
```bash
# Open and run notebooks/03_api_detection.ipynb
jupyter notebook notebooks/03_api_detection.ipynb
```

## Monitoring

### Prometheus Metrics

The ServingRuntime exposes Prometheus metrics on port 8002:

```bash
# Port-forward to access metrics
oc port-forward svc/yolo11-person-detection-predictor 8002:8002

# Access metrics
curl http://localhost:8002/metrics
```

**Key metrics:**
- `nv_inference_request_success`: Successful inference requests
- `nv_inference_request_failure`: Failed inference requests
- `nv_inference_queue_duration_us`: Request queue time
- `nv_inference_compute_duration_us`: Inference compute time

### Logs

```bash
# Predictor logs
oc logs -f deployment/yolo11-person-detection-predictor

# Filter for errors
oc logs deployment/yolo11-person-detection-predictor | grep ERROR

# Follow specific pod
POD=$(oc get pod -l serving.kserve.io/inferenceservice=yolo11-person-detection -o jsonpath='{.items[0].metadata.name}')
oc logs -f $POD
```

## Scaling

### Manual Scaling

Edit InferenceService to change replica count:

```yaml
spec:
  predictor:
    minReplicas: 2  # Minimum replicas
    maxReplicas: 5  # Maximum replicas
```

Apply changes:
```bash
oc apply -f inference-service.yaml
```

### Auto-scaling Configuration

The InferenceService auto-scales based on:
- **Target**: 80% concurrency
- **Metric**: Concurrent requests per pod

Adjust in `inference-service.yaml`:
```yaml
spec:
  predictor:
    scaleTarget: 80        # Target concurrency
    scaleMetric: concurrency
```

## Troubleshooting

### ServingRuntime not visible in Dashboard

**Check labels:**
```bash
oc get servingruntime yolo11-triton-runtime -o yaml | grep opendatahub
```

Should show: `opendatahub.io/dashboard: "true"`

**Fix:**
```bash
oc label servingruntime yolo11-triton-runtime opendatahub.io/dashboard=true
```

### InferenceService stuck in "Not Ready"

**Check events:**
```bash
oc describe inferenceservice yolo11-person-detection
```

**Common issues:**

1. **S3 credentials missing:**
   ```bash
   oc get secret s3-credentials -n train-detection
   ```

2. **Model file not found:**
   ```bash
   # Verify S3 URI in InferenceService
   oc get inferenceservice yolo11-person-detection -o yaml | grep storageUri

   # Test S3 access
   aws s3 ls s3://YOUR_BUCKET/yolo11n.onnx --endpoint-url $AWS_S3_ENDPOINT
   ```

3. **Image pull errors:**
   ```bash
   # Check pod events
   oc get events --sort-by='.lastTimestamp' | grep yolo11
   ```

### Model loading errors

**Check Triton logs:**
```bash
oc logs deployment/yolo11-person-detection-predictor | grep -A 10 "loading model"
```

**Common issues:**

1. **ONNX format mismatch:**
   - Ensure model is exported with correct ONNX opset version
   - Re-export: `python scripts/export_to_onnx.py --opset 17`

2. **Model configuration:**
   - Triton needs `config.pbtxt` or auto-generates it
   - For ONNX, auto-configuration usually works

3. **Memory issues:**
   - Increase memory limits in `serving-runtime.yaml`
   - Check pod resource usage: `oc top pod`

### SSL/Certificate errors

If MinIO uses self-signed certificates:

```bash
# In S3 secret, add:
AWS_S3_VERIFY_SSL: "0"
```

Or provide CA bundle:
```bash
oc create secret generic ca-bundle --from-file=ca-bundle.crt
```

## Performance Tuning

### Resource Optimization

For CPU-only inference (default):
```yaml
resources:
  requests:
    cpu: "1"
    memory: 2Gi
  limits:
    cpu: "2"
    memory: 4Gi
```

For GPU inference:
```yaml
resources:
  requests:
    cpu: "2"
    memory: 4Gi
    nvidia.com/gpu: 1
  limits:
    cpu: "4"
    memory: 8Gi
    nvidia.com/gpu: 1
```

### Batch Processing

For better throughput, enable dynamic batching in Triton:

```yaml
args:
  - tritonserver
  - --model-store=/mnt/models
  - --grpc-port=9000
  - --http-port=8080
  - --allow-grpc=true
  - --allow-http=true
  - --model-control-mode=explicit
  - --max-batch-size=8  # Add this
```

## Updating the Model

### Rolling Update

1. Upload new model version to S3:
   ```bash
   python scripts/upload_to_s3.py --model models/yolo11n_v2.onnx --key yolo11n.onnx
   ```

2. Trigger rollout:
   ```bash
   oc rollout restart deployment/yolo11-person-detection-predictor
   ```

3. Monitor rollout:
   ```bash
   oc rollout status deployment/yolo11-person-detection-predictor
   ```

### Canary Deployment

For safer updates, use KServe canary:

```yaml
spec:
  predictor:
    canaryTrafficPercent: 20  # 20% to new version
    model:
      storageUri: s3://bucket/yolo11n_v2.onnx
```

## Cleanup

Remove all resources:

```bash
# Delete InferenceService
oc delete inferenceservice yolo11-person-detection

# Delete ServingRuntime
oc delete servingruntime yolo11-triton-runtime

# Delete secret
oc delete secret s3-credentials

# Delete namespace (removes everything)
oc delete project train-detection
```

## References

- [KServe Documentation](https://kserve.github.io/website/)
- [OpenShift AI Model Serving](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/2.22/html/serving_models/)
- [Triton Inference Server](https://github.com/triton-inference-server/server)
- [NVIDIA Triton ONNX Backend](https://github.com/triton-inference-server/onnx_backend)
