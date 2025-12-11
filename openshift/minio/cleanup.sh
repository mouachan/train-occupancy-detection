#!/bin/bash
# Remove MinIO from OpenShift

set -e

NAMESPACE=${NAMESPACE:-train-detection}

echo "======================================"
echo "MinIO Cleanup on OpenShift"
echo "======================================"
echo ""
echo "Namespace: $NAMESPACE"
echo ""

# Switch to namespace
oc project $NAMESPACE 2>/dev/null || {
    echo "Namespace $NAMESPACE not found"
    exit 1
}

echo "⚠️  This will delete all MinIO resources including DATA!"
echo ""
read -p "Are you sure? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Aborted"
    exit 0
fi

echo ""
echo "Deleting MinIO resources..."

# Delete routes
echo "  Deleting routes..."
oc delete route minio-api minio-console --ignore-not-found=true

# Delete service
echo "  Deleting service..."
oc delete service minio --ignore-not-found=true

# Delete deployment
echo "  Deleting deployment..."
oc delete deployment minio --ignore-not-found=true

# Wait for pod to terminate
echo "  Waiting for pod to terminate..."
oc wait --for=delete pod -l app=minio --timeout=60s 2>/dev/null || true

# Delete PVC (this will delete all data!)
echo "  Deleting PVC (data will be lost)..."
oc delete pvc minio-storage --ignore-not-found=true

# Delete secret
echo "  Deleting secret..."
oc delete secret minio-credentials --ignore-not-found=true

echo ""
echo "======================================"
echo "Cleanup Complete!"
echo "======================================"
echo ""
echo "All MinIO resources have been removed from namespace: $NAMESPACE"
echo ""
