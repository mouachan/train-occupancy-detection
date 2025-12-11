#!/bin/bash
# Remove Streamlit application from OpenShift

set -e

NAMESPACE=${NAMESPACE:-train-detection}

echo "======================================"
echo "Streamlit App Cleanup on OpenShift"
echo "======================================"
echo ""
echo "Namespace: $NAMESPACE"
echo ""

# Switch to namespace
oc project $NAMESPACE 2>/dev/null || {
    echo "Namespace $NAMESPACE not found"
    exit 1
}

echo "⚠️  This will delete all Streamlit application resources!"
echo ""
read -p "Are you sure? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Aborted"
    exit 0
fi

echo ""
echo "Deleting application resources..."

# Delete using kustomize
oc delete -k .

echo ""
echo "======================================"
echo "Cleanup Complete!"
echo "======================================"
echo ""
echo "All Streamlit application resources have been removed from namespace: $NAMESPACE"
echo ""
