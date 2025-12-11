# Train Occupancy Detection - OpenShift Deployment

Complete automated deployment of the Train Occupancy Detection System on OpenShift.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Train Occupancy Detection System            │
└─────────────────────────────────────────────────────────┘

┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   MinIO      │───▶│Model Serving │───▶│  Streamlit   │
│   Storage    │    │  (Triton)    │    │     App      │
└──────────────┘    └──────────────┘    └──────────────┘
       │                    │                    │
    models/              yolo11n             API calls
 train-detections        ONNX              detections
```

## Components

1. **MinIO** - S3-compatible storage
   - Bucket `models`: YOLO11 ONNX model + config
   - Bucket `train-detections`: Detection results

2. **Model Serving** - Triton Inference Server via KServe
   - ONNX Runtime
   - REST API endpoint
   - Auto-scaling 1-3 replicas

3. **Streamlit App** - Web interface
   - Video upload and processing
   - Real-time detection visualization
   - Statistics and charts
   - MinIO integration

## Quick Start (Automated Deployment)

### Prerequisites

- OpenShift cluster access
- `oc` CLI installed
- Logged into OpenShift: `oc login <cluster-url>`

### One-Command Deployment

```bash
cd openshift
./deploy-all.sh
```

This will:
1. Create namespace `train-detection`
2. Deploy MinIO storage
3. Initialize MinIO (create buckets and model structure)
4. Deploy Triton model serving
5. Deploy Streamlit application
6. Display all access URLs

**Deployment time:** ~3-5 minutes

### Manual Deployment with Kustomize

```bash
# 1. Create secrets first
cd minio
cp secret-template.yaml secret.yaml
vi secret.yaml  # Change credentials!

cd ../model-serving
cp s3-secret-template.yaml s3-secret.yaml
vi s3-secret.yaml  # Match MinIO credentials

# 2. Deploy everything
cd ..
oc apply -k .

# 3. Wait for completion
oc get pods -w
```

## Configuration

### Namespace

Default namespace: `train-detection`

To use a different namespace:

```bash
# Edit kustomization.yaml
namespace: my-custom-namespace

# Or set via environment variable
NAMESPACE=my-namespace ./deploy-all.sh
```

### MinIO Credentials

Edit `minio/secret.yaml`:

```yaml
stringData:
  MINIO_ROOT_USER: "admin"
  MINIO_ROOT_PASSWORD: "YourSecurePassword123!"
  AWS_ACCESS_KEY_ID: "admin"
  AWS_SECRET_ACCESS_KEY: "YourSecurePassword123!"
```

**Important:** Also update `model-serving/s3-secret.yaml` with the same credentials!

### Streamlit App Configuration

Edit `streamlit-app/configmap.yaml`:

```yaml
data:
  # Auto-configured to use deployed InferenceService
  kserve_endpoint: "https://train-detection-model-..."

  # MinIO integration (optional)
  minio_endpoint: "https://minio-api-train-detection.apps..."
  minio_access_key: "admin"
  minio_secret_key: "YourSecurePassword123!"
```

## Post-Deployment Steps

### 1. Upload YOLO Model

The MinIO init job creates the bucket structure but you need to upload the model:

**Option A: MinIO Console (UI)**

```bash
# Get MinIO Console URL
oc get route minio-console -o jsonpath='{.spec.host}'

# Open in browser: https://minio-console-train-detection.apps...
# Login with credentials from minio/secret.yaml
# Navigate to models/yolo11n/1/
# Upload: model.onnx
```

**Option B: Using mc CLI**

```bash
# Get MinIO API URL
MINIO_URL=$(oc get route minio-api -o jsonpath='{.spec.host}')

# Configure mc
mc alias set myminio https://$MINIO_URL admin YourPassword

# Upload model
mc cp path/to/yolo11n.onnx myminio/models/yolo11n/1/model.onnx
```

**Option C: Using Notebook**

```bash
# Run notebook: notebooks/02_export_and_upload.ipynb
# It will export YOLO to ONNX and upload to MinIO
```

### 2. Verify Model Serving

```bash
# Check InferenceService status
oc get inferenceservice train-detection-model

# Should show READY=True
# Get inference URL
oc get inferenceservice train-detection-model -o jsonpath='{.status.url}'
```

### 3. Access Streamlit App

```bash
# Get Streamlit URL
oc get route train-detection-streamlit -o jsonpath='{.spec.host}'

# Open in browser
# Upload a video and test detection!
```

## Monitoring

### Check All Resources

```bash
oc get all,inferenceservice,pvc -n train-detection
```

### View Logs

```bash
# Streamlit app
oc logs -l app=train-detection-streamlit -f

# Model serving
oc logs -l serving.kserve.io/inferenceservice=train-detection-model -f

# MinIO
oc logs -l app=minio -f

# MinIO init job
oc logs job/minio-init
```

### Check Endpoints

```bash
# Get all routes
oc get routes

# Test model inference
MODEL_URL=$(oc get inferenceservice train-detection-model -o jsonpath='{.status.url}')
curl -k $MODEL_URL/v2/health/live
```

## Scaling

### Streamlit App

```bash
# Scale up
oc scale deployment train-detection-streamlit --replicas=3

# Scale down
oc scale deployment train-detection-streamlit --replicas=1
```

### Model Serving

Edit `model-serving/inference-service.yaml`:

```yaml
spec:
  predictor:
    minReplicas: 1
    maxReplicas: 5  # Increase max replicas
```

Then redeploy:

```bash
oc apply -f model-serving/inference-service.yaml
```

## Troubleshooting

### MinIO Init Job Failed

```bash
# Check job logs
oc logs job/minio-init

# Check if MinIO is running
oc get pods -l app=minio

# Restart job
oc delete job minio-init
oc apply -f minio/init-job.yaml
```

### InferenceService Not Ready

```bash
# Check status
oc describe inferenceservice train-detection-model

# Common issues:
# 1. Model not uploaded to MinIO
# 2. S3 secret credentials mismatch
# 3. Storage URI incorrect

# Check model exists in MinIO
oc exec -it deployment/minio -- mc ls /data/models/yolo11n/1/
```

### Streamlit App CrashLoopBackOff

```bash
# Check logs
oc logs -l app=train-detection-streamlit --tail=100

# Common issues:
# 1. Image pull errors
# 2. Missing dependencies
# 3. Permission errors

# Check events
oc get events --sort-by='.lastTimestamp'
```

### Cannot Access Routes

```bash
# Check routes exist
oc get routes

# Check TLS
oc describe route train-detection-streamlit

# Test internal connectivity
oc run test-curl --rm -it --image=curlimages/curl -- /bin/sh
# Inside pod:
curl http://train-detection-streamlit:8501/_stcore/health
```

## Cleanup

### Complete Removal

```bash
cd openshift
./cleanup-all.sh
```

This will delete:
- All deployments
- All services and routes
- All PVCs (data will be lost!)
- InferenceService
- MinIO and all stored data

### Delete Namespace

```bash
oc delete project train-detection
```

## Directory Structure

```
openshift/
├── kustomization.yaml           # Global orchestration
├── deploy-all.sh               # Automated deployment
├── cleanup-all.sh              # Complete cleanup
│
├── minio/                      # MinIO storage
│   ├── secret-template.yaml   # Credentials template
│   ├── secret.yaml            # ← Create this (gitignored)
│   ├── pvc.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── route-api.yaml
│   ├── route-console.yaml
│   ├── init-job.yaml          # Auto-creates buckets
│   ├── deploy.sh
│   └── cleanup.sh
│
├── model-serving/              # Triton + KServe
│   ├── s3-secret-template.yaml
│   ├── s3-secret.yaml         # ← Create this (gitignored)
│   ├── serving-runtime.yaml
│   ├── inference-service.yaml
│   └── README.md
│
└── streamlit-app/              # Web application
    ├── configmap.yaml
    ├── pvc.yaml
    ├── deployment.yaml
    ├── service.yaml
    ├── route.yaml
    ├── kustomization.yaml
    ├── deploy.sh
    └── cleanup.sh
```

## Advanced Configuration

### Custom Domain

Edit routes to use custom domain:

```yaml
spec:
  host: train-detection.my-domain.com
  tls:
    termination: edge
```

### Resource Limits

Edit deployments to adjust resource allocation:

```yaml
resources:
  requests:
    memory: "1Gi"
    cpu: "500m"
  limits:
    memory: "4Gi"
    cpu: "2000m"
```

### Persistent Storage

Adjust PVC sizes in:
- `minio/pvc.yaml` - MinIO data (default 20Gi)
- `streamlit-app/pvc.yaml` - Video uploads (default 10Gi)

## Security Considerations

1. **Change default credentials** in `minio/secret.yaml`
2. **Use image pull secrets** for private registries
3. **Enable RBAC** for production deployments
4. **Configure network policies** to restrict traffic
5. **Use secrets** instead of ConfigMaps for sensitive data

## Support

For issues or questions:
1. Check logs: `oc logs <pod-name>`
2. Check events: `oc get events --sort-by='.lastTimestamp'`
3. Describe resources: `oc describe <resource-type> <name>`
4. Review documentation in each component's README

## Next Steps

After successful deployment:

1. ✅ Verify all components are running
2. ✅ Upload YOLO model to MinIO
3. ✅ Test model inference via API
4. ✅ Upload a video in Streamlit
5. ✅ Review detection statistics
6. ✅ Check MinIO for saved results

Enjoy your automated train occupancy detection system! 🚂🎉
