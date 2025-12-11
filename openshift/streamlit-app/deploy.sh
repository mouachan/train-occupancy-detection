#!/bin/bash
# Deploy Streamlit application on OpenShift

set -e

NAMESPACE=${NAMESPACE:-train-detection}

echo "======================================"
echo "Streamlit App Deployment on OpenShift"
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
echo "Deploying application..."
echo ""

# Deploy using kustomize (automatically replaces image)
oc apply -k .

echo ""
echo "Waiting for deployment to be ready..."
oc wait --for=condition=available deployment/train-detection-streamlit --timeout=300s || true

echo ""
echo "======================================"
echo "Deployment Complete!"
echo "======================================"
echo ""

# Get route URL
ROUTE=$(oc get route train-detection-streamlit -o jsonpath='{.spec.host}' 2>/dev/null || echo "N/A")

echo "Application URL: https://$ROUTE"
echo ""

# Get pod status
echo "Pod status:"
oc get pods -l app=train-detection-streamlit
echo ""

echo "To check logs:"
echo "  oc logs -f deployment/train-detection-streamlit"
echo ""
