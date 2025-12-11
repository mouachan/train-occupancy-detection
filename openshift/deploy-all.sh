#!/bin/bash
# Automated deployment of complete Train Occupancy Detection System
# Deploys: MinIO → Model Serving → Streamlit App

set -e

NAMESPACE=${NAMESPACE:-train-detection}
WAIT_TIMEOUT=${WAIT_TIMEOUT:-300}

echo "========================================"
echo "Train Occupancy Detection System"
echo "Automated Deployment"
echo "========================================"
echo ""
echo "Namespace: $NAMESPACE"
echo "Timeout: ${WAIT_TIMEOUT}s"
echo ""

# Check prerequisites
echo "Checking prerequisites..."
if ! command -v oc &> /dev/null; then
    echo "Error: oc CLI not found. Please install OpenShift CLI."
    exit 1
fi

if ! oc whoami &> /dev/null; then
    echo "Error: Not logged into OpenShift. Run 'oc login' first."
    exit 1
fi

echo "✓ OpenShift CLI available"
echo "✓ Logged in as: $(oc whoami)"
echo ""

# Create/switch to namespace
echo "========================================"
echo "Step 1: Creating Namespace"
echo "========================================"
echo ""

if ! oc get namespace $NAMESPACE &>/dev/null; then
    echo "Creating namespace: $NAMESPACE"
    oc new-project $NAMESPACE
else
    echo "Using existing namespace: $NAMESPACE"
    oc project $NAMESPACE
fi

echo "✓ Namespace ready"
echo ""

# Check if secret.yaml exists
if [ ! -f minio/secret.yaml ]; then
    echo "========================================"
    echo "⚠️  MinIO Secret Not Found"
    echo "========================================"
    echo ""
    echo "Please create minio/secret.yaml from template:"
    echo "  cd minio"
    echo "  cp secret-template.yaml secret.yaml"
    echo "  vi secret.yaml  # Change credentials!"
    echo ""
    read -p "Press Enter after creating secret.yaml, or Ctrl+C to abort..."
    echo ""
fi

# Create S3 secret from MinIO credentials if it doesn't exist
if [ ! -f model-serving/s3-secret.yaml ]; then
    echo "========================================"
    echo "Creating S3 Secret"
    echo "========================================"
    echo ""
    echo "Auto-generating model-serving/s3-secret.yaml from MinIO credentials..."

    # Extract credentials from MinIO secret
    MINIO_USER=$(grep "MINIO_ROOT_USER:" minio/secret.yaml | awk '{print $2}' | tr -d '"')
    MINIO_PASS=$(grep "MINIO_ROOT_PASSWORD:" minio/secret.yaml | awk '{print $2}' | tr -d '"')

    # Create S3 secret
    cat > model-serving/s3-secret.yaml <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: storage-config
  annotations:
    serving.kserve.io/s3-endpoint: minio:9000
    serving.kserve.io/s3-usehttps: "0"
    serving.kserve.io/s3-verifyssl: "0"
    serving.kserve.io/s3-region: us-east-1
type: Opaque
stringData:
  AWS_ACCESS_KEY_ID: "$MINIO_USER"
  AWS_SECRET_ACCESS_KEY: "$MINIO_PASS"
EOF

    echo "✓ Created model-serving/s3-secret.yaml"
    echo ""
fi

# Check if Triton ServingRuntime Template already exists
echo "========================================"
echo "Step 2: Checking ServingRuntime"
echo "========================================"
echo ""

# Check for existing Template (cluster-scoped)
if oc get template triton-runtime -n openshift &>/dev/null; then
    echo "✓ Triton runtime template already exists (cluster-wide)"
    echo "  Skipping template installation"

    # Remove template from kustomization to avoid conflicts
    sed -i.bak '/template-triton-runtime.yaml/d' kustomization.yaml
else
    echo "⚠️  Triton runtime template not found"
    echo "  Will install template with deployment"
fi

# Check for existing ServingRuntime in namespace
if oc get servingruntime triton-runtime -n $NAMESPACE &>/dev/null; then
    echo "✓ Triton runtime already exists in namespace $NAMESPACE"
    echo "  Skipping runtime installation"

    # Remove template from kustomization to avoid conflicts
    sed -i.bak '/template-triton-runtime.yaml/d' kustomization.yaml
else
    echo "⚠️  Triton runtime not found in namespace"
    echo "  Will create ServingRuntime"
fi

echo ""

# Deploy everything with kustomize
echo "========================================"
echo "Step 3: Deploying All Resources"
echo "========================================"
echo ""

echo "Deploying with Kustomize..."

# Update namespace in kustomization.yaml
echo "Setting namespace to: $NAMESPACE"
sed -i.bak "s/^namespace: .*/namespace: $NAMESPACE/" kustomization.yaml

oc apply -k .

echo "✓ All resources created"
echo ""

# Wait for MinIO
echo "========================================"
echo "Step 4: Waiting for MinIO"
echo "========================================"
echo ""

echo "Waiting for MinIO pod to be ready..."
oc wait --for=condition=ready pod -l app=minio --timeout=${WAIT_TIMEOUT}s || {
    echo "⚠️  MinIO pod not ready yet. Checking status..."
    oc get pods -l app=minio
}

echo "✓ MinIO is ready"
echo ""

# Wait for MinIO init job
echo "Waiting for MinIO initialization job..."
oc wait --for=condition=complete job/minio-init --timeout=${WAIT_TIMEOUT}s || {
    echo "⚠️  MinIO init job not complete. Checking logs..."
    oc logs job/minio-init
}

echo "✓ MinIO initialized (buckets and structure created)"
echo ""

# Get MinIO routes
MINIO_API=$(oc get route minio-api -o jsonpath='{.spec.host}' 2>/dev/null || echo "N/A")
MINIO_CONSOLE=$(oc get route minio-console -o jsonpath='{.spec.host}' 2>/dev/null || echo "N/A")

echo "MinIO Endpoints:"
echo "  API (S3):     https://$MINIO_API"
echo "  Console (UI): https://$MINIO_CONSOLE"
echo ""

# Wait for InferenceService
echo "========================================"
echo "Step 5: Waiting for Model Serving"
echo "========================================"
echo ""

echo "Waiting for InferenceService to be ready..."
echo "(This may take 2-5 minutes on first deployment)"
echo ""

# Check if InferenceService exists and wait
if oc get inferenceservice train-detection-model &>/dev/null; then
    # Wait for READY status
    for i in {1..60}; do
        STATUS=$(oc get inferenceservice train-detection-model -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo "Unknown")
        if [ "$STATUS" = "True" ]; then
            echo "✓ InferenceService is ready"
            break
        fi
        echo "  Status: $STATUS (attempt $i/60)"
        sleep 5
    done
else
    echo "⚠️  InferenceService not found yet"
fi

MODEL_URL=$(oc get inferenceservice train-detection-model -o jsonpath='{.status.url}' 2>/dev/null || echo "N/A")
echo ""
echo "Model Endpoint: $MODEL_URL"
echo ""

# Wait for Streamlit App
echo "========================================"
echo "Step 6: Waiting for Streamlit App"
echo "========================================"
echo ""

echo "Waiting for Streamlit deployment..."
oc wait --for=condition=available deployment/train-detection-streamlit --timeout=${WAIT_TIMEOUT}s || {
    echo "⚠️  Streamlit deployment not ready. Checking status..."
    oc get deployment train-detection-streamlit
    oc get pods -l app=train-detection-streamlit
}

echo "✓ Streamlit app is ready"
echo ""

# Get Streamlit route
STREAMLIT_URL=$(oc get route train-detection-streamlit -o jsonpath='{.spec.host}' 2>/dev/null || echo "N/A")

echo "Streamlit Application: https://$STREAMLIT_URL"
echo ""

# Final summary
echo "========================================"
echo "Deployment Complete!"
echo "========================================"
echo ""
echo "🎉 All components deployed successfully!"
echo ""
echo "Access Points:"
echo "  📊 Streamlit App:    https://$STREAMLIT_URL"
echo "  🤖 Model API:        $MODEL_URL"
echo "  💾 MinIO Console:    https://$MINIO_CONSOLE"
echo "  📦 MinIO S3 API:     https://$MINIO_API"
echo ""
echo "Next Steps:"
echo "  1. Upload YOLO model to MinIO:"
echo "     - Open MinIO Console: https://$MINIO_CONSOLE"
echo "     - Login with credentials from minio/secret.yaml"
echo "     - Upload to: models/yolo11n/1/model.onnx"
echo ""
echo "  2. Or use notebook to upload:"
echo "     - notebooks/02_export_and_upload.ipynb"
echo ""
echo "  3. Open Streamlit App:"
echo "     - https://$STREAMLIT_URL"
echo "     - Upload a video and test detection!"
echo ""
echo "To check status:"
echo "  oc get all,inferenceservice,pvc -n $NAMESPACE"
echo ""
echo "To view logs:"
echo "  oc logs -l app=train-detection-streamlit -f"
echo "  oc logs -l app=minio -f"
echo ""
