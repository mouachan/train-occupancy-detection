#!/bin/bash
# Build Streamlit image for x86_64 architecture (from Mac ARM)

set -e

# Configuration
IMAGE_NAME=${IMAGE_NAME:-"train-occupancy-detection"}
IMAGE_TAG=${IMAGE_TAG:-"latest"}
REGISTRY=${REGISTRY:-""}  # Set to your registry, e.g., "quay.io/myuser"

# Full image name
if [ -z "$REGISTRY" ]; then
    FULL_IMAGE="${IMAGE_NAME}:${IMAGE_TAG}"
else
    FULL_IMAGE="${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
fi

echo "======================================"
echo "Building Streamlit Image for x86_64"
echo "======================================"
echo ""
echo "Image: $FULL_IMAGE"
echo "Platform: linux/amd64"
echo ""

# Check if using podman or docker
if command -v podman &> /dev/null; then
    BUILDER="podman"
elif command -v docker &> /dev/null; then
    BUILDER="docker"
else
    echo "Error: Neither podman nor docker found"
    exit 1
fi

echo "Using builder: $BUILDER"
echo ""

# Build for x86_64 (linux/amd64)
echo "Building image..."
$BUILDER build \
    --platform linux/amd64 \
    -t "$FULL_IMAGE" \
    -f Dockerfile.streamlit \
    .

echo ""
echo "======================================"
echo "Build Complete!"
echo "======================================"
echo ""
echo "Image: $FULL_IMAGE"
echo "Platform: linux/amd64"
echo ""

# Show image info
echo "Image details:"
$BUILDER images "$FULL_IMAGE"
echo ""

# Instructions
echo "Next steps:"
echo ""
if [ -z "$REGISTRY" ]; then
    echo "  1. Tag for registry:"
    echo "     $BUILDER tag $FULL_IMAGE <registry>/<image>:<tag>"
    echo ""
    echo "  2. Push to registry:"
    echo "     $BUILDER push <registry>/<image>:<tag>"
else
    echo "  1. Push to registry:"
    echo "     $BUILDER push $FULL_IMAGE"
fi
echo ""
echo "  Or login to OpenShift and push to internal registry:"
echo "     oc registry login"
echo "     $BUILDER tag $FULL_IMAGE \$(oc registry info)/train-detection/$IMAGE_NAME:$IMAGE_TAG"
echo "     $BUILDER push \$(oc registry info)/train-detection/$IMAGE_NAME:$IMAGE_TAG"
echo ""
