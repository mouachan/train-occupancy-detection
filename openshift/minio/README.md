# MinIO Object Storage on OpenShift

This directory contains manifests for deploying MinIO S3-compatible object storage on OpenShift for model storage.

## Why MinIO?

- **S3-compatible**: Works with existing S3 tooling and libraries
- **Self-hosted**: Full control and autonomy on OpenShift
- **Lightweight**: Efficient resource usage
- **Web console**: Easy bucket and object management
- **Perfect for models**: Store ONNX models for Triton/OpenVINO

## Components

### 1. Secret (`secret-template.yaml`)
Stores MinIO credentials (access key, secret key).

**⚠️ IMPORTANT**: Change default credentials before deploying!

### 2. PersistentVolumeClaim (`pvc.yaml`)
20Gi persistent storage for MinIO data.

### 3. Deployment (`deployment.yaml`)
MinIO server container with:
- API endpoint (port 9000)
- Web console (port 9001)
- Health probes
- Resource limits

### 4. Service (`service.yaml`)
ClusterIP service exposing both API and console.

### 5. Routes (`route-api.yaml`, `route-console.yaml`)
HTTPS external access for:
- **API Route**: S3 API endpoint for model uploads/downloads
- **Console Route**: Web UI for bucket management

## Deployment Guide

### Prerequisites

```bash
# Create namespace
oc new-project train-detection
```

### Step 1: Create Secret

**⚠️ Change credentials first!**

```bash
# Edit secret-template.yaml and change:
# - MINIO_ROOT_USER: "your-username"
# - MINIO_ROOT_PASSWORD: "your-strong-password"

# Copy template
cp secret-template.yaml secret.yaml

# Edit credentials
vi secret.yaml

# Deploy secret
oc apply -f secret.yaml
```

### Step 2: Deploy Storage

```bash
# Create PVC (20Gi storage)
oc apply -f pvc.yaml

# Wait for PVC to be bound
oc get pvc minio-storage -w
```

### Step 3: Deploy MinIO

```bash
# Deploy MinIO server
oc apply -f deployment.yaml

# Wait for pod to be running
oc get pods -l app=minio -w
```

### Step 4: Expose with Service and Routes

```bash
# Create service
oc apply -f service.yaml

# Create routes for API and Console
oc apply -f route-api.yaml
oc apply -f route-console.yaml

# Get route URLs
oc get routes
```

Expected output:
```
NAME             HOST/PORT
minio-api        minio-api-train-detection.apps.cluster...
minio-console    minio-console-train-detection.apps.cluster...
```

## Access MinIO

### Web Console

1. Get console URL:
   ```bash
   echo "https://$(oc get route minio-console -o jsonpath='{.spec.host}')"
   ```

2. Open in browser

3. Login with credentials from secret:
   - Username: `MINIO_ROOT_USER`
   - Password: `MINIO_ROOT_PASSWORD`

4. Create bucket: `models`

### S3 API Endpoint

Get API endpoint URL:
```bash
echo "https://$(oc get route minio-api -o jsonpath='{.spec.host}')"
```

Use in notebooks and scripts:
```python
AWS_S3_ENDPOINT = "https://minio-api-train-detection.apps.cluster..."
AWS_S3_BUCKET = "models"
AWS_ACCESS_KEY_ID = "your-username"
AWS_SECRET_ACCESS_KEY = "your-password"
```

## Upload Models to MinIO

### Using MinIO Console (Web UI)

1. Open MinIO Console
2. Create bucket: `models`
3. Upload `yolo11n.onnx` with structure:
   ```
   models/
   └── yolo11n/
       └── 1/
           └── model.onnx
   ```

### Using Python (boto3)

```python
import boto3
from botocore.client import Config

# Configure MinIO client
s3_client = boto3.client(
    's3',
    endpoint_url='https://minio-api-train-detection.apps.cluster...',
    aws_access_key_id='your-username',
    aws_secret_access_key='your-password',
    config=Config(signature_version='s3v4'),
    verify=False  # If using self-signed certs
)

# Create bucket
s3_client.create_bucket(Bucket='models')

# Upload model
with open('yolo11n.onnx', 'rb') as f:
    s3_client.put_object(
        Bucket='models',
        Key='yolo11n/1/model.onnx',
        Body=f
    )
```

### Using AWS CLI (mc - MinIO Client)

```bash
# Install mc
wget https://dl.min.io/client/mc/release/linux-amd64/mc
chmod +x mc

# Configure alias
mc alias set minio https://minio-api-train-detection.apps.cluster... \
  your-username your-password

# Create bucket
mc mb minio/models

# Upload model
mc cp yolo11n.onnx minio/models/yolo11n/1/model.onnx
```

## Configure InferenceService to Use MinIO

### Update S3 Secret

Edit `openshift/model-serving/s3-secret.yaml`:

```yaml
stringData:
  AWS_ACCESS_KEY_ID: "your-minio-username"
  AWS_SECRET_ACCESS_KEY: "your-minio-password"
  AWS_S3_ENDPOINT: "https://minio-api-train-detection.apps.cluster..."
  AWS_DEFAULT_REGION: "us-east-1"
  AWS_S3_BUCKET: "models"
```

Apply:
```bash
oc apply -f openshift/model-serving/s3-secret.yaml
```

### Update InferenceService

The `inference-service.yaml` already uses `storageUri: s3://models`, so it will automatically use MinIO!

```bash
oc apply -f openshift/model-serving/inference-service.yaml
```

## Monitoring

### Check MinIO Logs

```bash
# View logs
oc logs -f deployment/minio

# Check specific pod
POD=$(oc get pod -l app=minio -o jsonpath='{.items[0].metadata.name}')
oc logs -f $POD
```

### Check Storage Usage

```bash
# PVC usage
oc get pvc minio-storage

# Describe PVC
oc describe pvc minio-storage
```

### Health Check

```bash
# Via service
oc exec deployment/minio -- curl -I http://localhost:9000/minio/health/live

# Via route
curl -k https://$(oc get route minio-api -o jsonpath='{.spec.host}')/minio/health/live
```

## Troubleshooting

### Pod not starting

```bash
# Check pod status
oc get pods -l app=minio

# Check events
oc describe pod -l app=minio

# Common issues:
# - PVC not bound → check storage class
# - Secret not found → verify secret name
# - Image pull error → check network/registry access
```

### Can't access console

```bash
# Check route
oc get route minio-console

# Check service
oc get svc minio

# Test internally
oc exec deployment/minio -- curl http://localhost:9001
```

### S3 connection errors

```bash
# Check API route
oc get route minio-api

# Verify credentials
oc get secret minio-credentials -o yaml

# Test with curl
curl -k https://$(oc get route minio-api -o jsonpath='{.spec.host}')/minio/health/ready
```

### Certificate errors (self-signed)

If using self-signed certificates, clients need to disable SSL verification:

```python
# Python boto3
s3_client = boto3.client('s3', ..., verify=False)

# In notebooks
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
```

Or add CA certificate to trusted store.

## Scaling

### Increase Storage

Edit PVC (requires recreation):
```bash
# Delete deployment first
oc delete deployment minio

# Edit PVC storage size
oc edit pvc minio-storage
# Change: storage: 50Gi

# Recreate deployment
oc apply -f deployment.yaml
```

### Resource Limits

Edit `deployment.yaml` to adjust CPU/memory:
```yaml
resources:
  requests:
    memory: 1Gi
    cpu: 500m
  limits:
    memory: 2Gi
    cpu: 1
```

## Backup and Restore

### Backup Data

```bash
# Using mc client
mc mirror minio/models /backup/models

# Or using oc rsync
POD=$(oc get pod -l app=minio -o jsonpath='{.items[0].metadata.name}')
oc rsync $POD:/data /backup/minio-data
```

### Restore Data

```bash
# Using mc client
mc mirror /backup/models minio/models

# Or using oc rsync
POD=$(oc get pod -l app=minio -o jsonpath='{.items[0].metadata.name}')
oc rsync /backup/minio-data $POD:/data
```

## Security Best Practices

1. **Change default credentials** in secret before deploying
2. **Use strong passwords** (min 12 characters, alphanumeric + special)
3. **Enable HTTPS** (already configured via routes)
4. **Limit access** with OpenShift RBAC
5. **Regular backups** of critical model data
6. **Monitor access logs** via MinIO console

## Cleanup

Remove all MinIO resources:

```bash
# Delete all MinIO resources
oc delete route minio-api minio-console
oc delete svc minio
oc delete deployment minio
oc delete pvc minio-storage
oc delete secret minio-credentials

# Or delete everything with label
oc delete all,pvc,secret -l app=minio
```

## References

- [MinIO Documentation](https://min.io/docs/minio/linux/index.html)
- [MinIO on Kubernetes](https://min.io/docs/minio/kubernetes/upstream/index.html)
- [S3 API Reference](https://docs.aws.amazon.com/AmazonS3/latest/API/Welcome.html)
- [OpenShift Routes](https://docs.openshift.com/container-platform/latest/networking/routes/route-configuration.html)
