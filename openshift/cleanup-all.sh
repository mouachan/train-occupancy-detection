#!/bin/bash
# Complete cleanup of Train Occupancy Detection System

set -e

NAMESPACE=${NAMESPACE:-train-detection}

echo "========================================"
echo "Train Occupancy Detection System"
echo "Complete Cleanup"
echo "========================================"
echo ""
echo "Namespace: $NAMESPACE"
echo ""

# Switch to namespace
oc project $NAMESPACE 2>/dev/null || {
    echo "Namespace $NAMESPACE not found"
    exit 1
}

echo "⚠️  This will delete ALL resources including:"
echo "  - Streamlit Application"
echo "  - Model Serving (InferenceService)"
echo "  - MinIO Storage (ALL DATA WILL BE LOST)"
echo "  - All PVCs and stored data"
echo ""
read -p "Are you sure? Type 'yes' to confirm: " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Aborted"
    exit 0
fi

echo ""
echo "Deleting all resources..."
echo ""

# Delete with kustomize (reverse order)
cd "$(dirname "$0")"

# Update namespace in kustomization.yaml to match
echo "Setting namespace to: $NAMESPACE in kustomization.yaml"
sed -i.bak "s/^namespace: .*/namespace: $NAMESPACE/" kustomization.yaml

oc delete -k . --ignore-not-found=true

# Delete ServingRuntime instance (but NOT the template in redhat-ods-applications)
echo "Deleting ServingRuntime instance..."
oc delete servingruntime triton-runtime -n $NAMESPACE --ignore-not-found=true

# Delete s3-credentials secret (created dynamically by deploy-all.sh)
echo "Deleting s3-credentials secret..."
oc delete secret s3-credentials -n $NAMESPACE --ignore-not-found=true

# NOTE: We do NOT delete the template from redhat-ods-applications
# as it's shared across all projects

echo ""
echo "Waiting for resources to be deleted..."
sleep 5

# Ensure PVCs are deleted
echo "Ensuring PVCs are deleted..."
oc delete pvc --all --ignore-not-found=true

# Wait for pods to terminate
echo "Waiting for pods to terminate..."
oc wait --for=delete pod --all --timeout=120s 2>/dev/null || true

echo ""
echo "========================================"
echo "Cleanup Complete!"
echo "========================================"
echo ""
echo "All resources have been removed from namespace: $NAMESPACE"
echo ""
echo "To delete the namespace completely:"
echo "  oc delete project $NAMESPACE"
echo ""
