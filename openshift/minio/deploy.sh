#!/bin/bash
# Deploy MinIO on OpenShift

set -e

NAMESPACE=${NAMESPACE:-train-detection}

echo "======================================"
echo "MinIO Deployment on OpenShift"
echo "======================================"
echo ""
echo "Namespace: $NAMESPACE"
echo ""

# Check if namespace exists
if ! oc get namespace $NAMESPACE &>/dev/null; then
    echo "Creating namespace: $NAMESPACE"
    oc new-project $NAMESPACE
else
    echo "Using existing namespace: $NAMESPACE"
    oc project $NAMESPACE
fi

echo ""

# Check if secret exists
if [ ! -f secret.yaml ]; then
    echo "⚠️  WARNING: secret.yaml not found!"
    echo ""
    echo "Please create secret.yaml from template:"
    echo "  cp secret-template.yaml secret.yaml"
    echo "  vi secret.yaml  # Change credentials"
    echo ""
    exit 1
fi

echo "Step 1: Creating Secret..."
oc apply -f secret.yaml
echo "✓ Secret created"
echo ""

echo "Step 2: Creating PersistentVolumeClaim..."
oc apply -f pvc.yaml
echo "✓ PVC created"
echo ""

echo "Waiting for PVC to be bound..."
oc wait --for=jsonpath='{.status.phase}'=Bound pvc/minio-storage --timeout=60s || true
echo ""

echo "Step 3: Creating Deployment..."
oc apply -f deployment.yaml
echo "✓ Deployment created"
echo ""

echo "Waiting for pod to be ready..."
oc wait --for=condition=ready pod -l app=minio --timeout=120s || true
echo ""

echo "Step 4: Creating Service..."
oc apply -f service.yaml
echo "✓ Service created"
echo ""

echo "Step 5: Creating Routes..."
oc apply -f route-api.yaml
oc apply -f route-console.yaml
echo "✓ Routes created"
echo ""

echo "======================================"
echo "Deployment Complete!"
echo "======================================"
echo ""

# Get routes
API_ROUTE=$(oc get route minio-api -o jsonpath='{.spec.host}' 2>/dev/null || echo "N/A")
CONSOLE_ROUTE=$(oc get route minio-console -o jsonpath='{.spec.host}' 2>/dev/null || echo "N/A")

echo "MinIO Endpoints:"
echo "  API (S3):     https://$API_ROUTE"
echo "  Console (UI): https://$CONSOLE_ROUTE"
echo ""

# Get credentials
echo "Credentials:"
MINIO_USER=$(oc get secret minio-credentials -o jsonpath='{.data.MINIO_ROOT_USER}' 2>/dev/null | base64 -d || echo "N/A")
MINIO_PASS=$(oc get secret minio-credentials -o jsonpath='{.data.MINIO_ROOT_PASSWORD}' 2>/dev/null | base64 -d || echo "N/A")

echo "  Username: $MINIO_USER"
echo "  Password: $MINIO_PASS"
echo ""

echo "Next Steps:"
echo "  1. Open Console: https://$CONSOLE_ROUTE"
echo "  2. Login with credentials above"
echo "  3. Create bucket: 'models'"
echo "  4. Upload models with Triton structure: models/yolo11n/1/model.onnx"
echo ""

echo "To check status:"
echo "  oc get all,pvc -l app=minio"
echo ""
