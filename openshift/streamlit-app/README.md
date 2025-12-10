# Streamlit Application Deployment on OpenShift

This directory contains Kubernetes manifests for deploying the Train Occupancy Detection Streamlit application on OpenShift.

## Prerequisites

- OpenShift cluster access
- `oc` CLI configured
- Container image pushed to Quay.io registry

## Configuration

### 1. Update Container Image

Before deploying, update the `deployment.yaml` file with your Quay.io username:

```yaml
# In deployment.yaml, line 23:
image: quay.io/YOUR_USERNAME/train-detection-streamlit:latest
```

Replace `username` with your actual Quay.io username.

### 2. Build and Push Image

```bash
# From project root directory
cd /path/to/train-occupancy-detection

# Build image with podman
podman build -f Dockerfile.streamlit -t train-detection-streamlit:latest .

# Tag for Quay.io
podman tag train-detection-streamlit:latest \
    quay.io/YOUR_USERNAME/train-detection-streamlit:latest

# Login to Quay.io
podman login quay.io

# Push image
podman push quay.io/YOUR_USERNAME/train-detection-streamlit:latest
```

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

## Deployment Steps

### 1. Create Namespace

```bash
oc new-project train-detection
```

### 2. Apply Manifests

```bash
# Apply in order
oc apply -f configmap.yaml
oc apply -f pvc.yaml
oc apply -f deployment.yaml
oc apply -f service.yaml
oc apply -f route.yaml
```

### 3. Verify Deployment

```bash
# Check pods
oc get pods -n train-detection

# Check deployment status
oc get deployment train-detection-streamlit -n train-detection

# Get application URL
oc get route train-detection-streamlit -o jsonpath='{.spec.host}'
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
# Build and push new image
podman build -f Dockerfile.streamlit -t quay.io/YOUR_USERNAME/train-detection-streamlit:v2 .
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
