# Streamlit Application Deployment on OpenShift

This directory contains Kubernetes manifests for deploying the Train Occupancy Detection Streamlit application on OpenShift.

## Prerequisites

- OpenShift cluster access
- `oc` CLI configured and logged in
- Container image pushed to Quay.io registry

## Quick Start

**Deploy everything with one command (using kustomize):**

```bash
cd openshift/streamlit-app
./deploy.sh
```

This will:
- Create namespace `train-detection` if needed
- Deploy all manifests
- Automatically use the image `quay.io/mouachan/train-detection-streamlit:latest`
- Wait for deployment to be ready
- Display the application URL

**To cleanup:**

```bash
./cleanup.sh
```

## Configuration

### Customize Image (kustomization.yaml)

The deployment uses **kustomize** to override the image without modifying YAML files.

Edit `kustomization.yaml` to change the image:

```yaml
images:
  - name: quay.io/username/train-detection-streamlit
    newName: quay.io/YOUR_USERNAME/train-detection-streamlit
    newTag: latest  # or specific version like v1.0
```

Then deploy:

```bash
oc apply -k .
```

### 2. Build and Push Image

**Important for Mac ARM users**: OpenShift runs on x86_64 architecture. You must build for `linux/amd64` platform.

#### Option A: Using Build Script (Recommended)

```bash
# From project root directory
cd /path/to/train-occupancy-detection

# Build for x86_64 with default settings
./build-image.sh

# Or build with custom registry
REGISTRY=quay.io/YOUR_USERNAME IMAGE_NAME=train-detection-streamlit ./build-image.sh
```

#### Option B: Manual Build for x86_64

```bash
# From project root directory
cd /path/to/train-occupancy-detection

# Build image for x86_64 platform
podman build \
    --platform linux/amd64 \
    -f Dockerfile.streamlit \
    -t train-detection-streamlit:latest \
    .

# Tag for Quay.io
podman tag train-detection-streamlit:latest \
    quay.io/YOUR_USERNAME/train-detection-streamlit:latest

# Login to Quay.io
podman login quay.io

# Push image
podman push quay.io/YOUR_USERNAME/train-detection-streamlit:latest
```

**Note**: The `--platform linux/amd64` flag is **critical** when building from Mac ARM (M1/M2/M3). Without it, the image will be ARM-based and won't run on OpenShift.

### 3. Make Image Public (Optional)

If you want the image to be publicly accessible:

1. Go to https://quay.io/repository/YOUR_USERNAME/train-detection-streamlit
2. Click on "Settings" → "Make Public"

Or keep it private and configure image pull secrets in OpenShift:

```bash
# Create image pull secret
oc create secret docker-registry quay-secret \
    --docker-server=quay.io \
    --docker-username=YOUR_USERNAME \
    --docker-password=YOUR_PASSWORD \
    --docker-email=YOUR_EMAIL \
    -n train-detection

# Add secret to default service account
oc secrets link default quay-secret --for=pull -n train-detection
```

## Manual Deployment (Alternative)

If you prefer to deploy manually instead of using the script:

### 1. Create Namespace

```bash
oc new-project train-detection
```

### 2. Deploy with Kustomize

```bash
# Deploy all manifests at once (kustomize handles image override)
oc apply -k .
```

Or deploy files individually:

```bash
# Apply in order
oc apply -f configmap.yaml
oc apply -f pvc.yaml
oc apply -f deployment.yaml
oc apply -f service.yaml
oc apply -f route.yaml

# Then override image
oc set image deployment/train-detection-streamlit \
  streamlit=quay.io/mouachan/train-detection-streamlit:latest
```

### 3. Verify Deployment

```bash
# Check pods
oc get pods -l app=train-detection-streamlit

# Check deployment status
oc get deployment train-detection-streamlit

# Get application URL
oc get route train-detection-streamlit -o jsonpath='{.spec.host}'

# Check logs
oc logs -f deployment/train-detection-streamlit
```

## Manifests Description

### configmap.yaml
Configuration data for the application:
- KServe endpoint URL
- Model name
- Detection parameters
- Upload limits

### pvc.yaml
Persistent Volume Claim for video uploads:
- Size: 10Gi
- Access mode: ReadWriteOnce
- Storage class: gp3-csi (update if needed)

### deployment.yaml
Application deployment:
- 2 replicas for high availability
- Container image from Quay.io
- Environment variables from ConfigMap
- Volume mounts for uploads and models
- Health probes

### service.yaml
ClusterIP service:
- Exposes port 8501
- Routes traffic to pods

### route.yaml
External access:
- HTTPS endpoint with TLS termination
- Redirects HTTP to HTTPS

## Updating the Application

To update the application with a new image:

```bash
# Build and push new image (from Mac ARM, use --platform flag)
podman build \
    --platform linux/amd64 \
    -f Dockerfile.streamlit \
    -t quay.io/YOUR_USERNAME/train-detection-streamlit:v2 \
    .
podman push quay.io/YOUR_USERNAME/train-detection-streamlit:v2

# Update deployment
oc set image deployment/train-detection-streamlit \
    streamlit=quay.io/YOUR_USERNAME/train-detection-streamlit:v2 \
    -n train-detection

# Or edit deployment.yaml and re-apply
vi deployment.yaml  # Update image tag
oc apply -f deployment.yaml
```

## Scaling

Scale the number of replicas:

```bash
# Scale up
oc scale deployment train-detection-streamlit --replicas=3 -n train-detection

# Scale down
oc scale deployment train-detection-streamlit --replicas=1 -n train-detection
```

## Troubleshooting

### Pod not starting

```bash
# Check pod logs
oc logs -f deployment/train-detection-streamlit -n train-detection

# Describe pod for events
oc describe pod -l app=train-detection-streamlit -n train-detection
```

### Image pull errors

If you see `ImagePullBackOff`:

1. Verify image exists: `podman pull quay.io/YOUR_USERNAME/train-detection-streamlit:latest`
2. Check image is public or configure pull secrets
3. Verify image name in deployment.yaml

### Application not accessible

```bash
# Check route
oc get route train-detection-streamlit -n train-detection

# Check service endpoints
oc get endpoints train-detection-streamlit -n train-detection

# Test from within cluster
oc run -it --rm debug --image=curlimages/curl --restart=Never -- \
    curl http://train-detection-streamlit:8501/_stcore/health
```

### Storage issues

```bash
# Check PVC status
oc get pvc streamlit-uploads-pvc -n train-detection

# Check storage class availability
oc get sc

# Update pvc.yaml if storage class is different
```

## Cleanup

Remove all resources:

```bash
oc delete -f route.yaml
oc delete -f service.yaml
oc delete -f deployment.yaml
oc delete -f pvc.yaml
oc delete -f configmap.yaml

# Or delete entire project
oc delete project train-detection
```
