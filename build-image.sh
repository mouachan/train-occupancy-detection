#!/bin/bash
# Build Streamlit image for x86_64 architecture (from Mac ARM)

set -e

# Configuration
IMAGE_NAME=${IMAGE_NAME:-"train-occupancy-detection"}
IMAGE_TAG=${IMAGE_TAG:-"latest"}
REGISTRY=${REGISTRY:-""}  # e.g., "localhost:5000/username" or "registry.local:5000/username"
PUSH=${PUSH:-"false"}  # Set to "true" to push after build
DOCKERFILE=${DOCKERFILE:-"Dockerfile.streamlit-api"}  # Use lightweight API-only by default

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
echo "Image:      $FULL_IMAGE"
echo "Dockerfile: $DOCKERFILE"
echo "Platform:   linux/amd64"
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
    -f "$DOCKERFILE" \
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

# Push if requested
if [ "$PUSH" = "true" ]; then
    echo "======================================"
    echo "Pushing to Registry"
    echo "======================================"
    echo ""

    if [ -z "$REGISTRY" ]; then
        echo "Error: REGISTRY must be set when PUSH=true"
        exit 1
    fi

    echo "Pushing $FULL_IMAGE..."
    $BUILDER push "$FULL_IMAGE"

    echo ""
    echo "======================================"
    echo "Push Complete!"
    echo "======================================"
    echo ""
    echo "Image available at: $FULL_IMAGE"
    echo ""
else
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
        echo "  Push to registry:"
        echo "     $BUILDER push $FULL_IMAGE"
        echo ""
        echo "  Or build and push in one step:"
        echo "     PUSH=true REGISTRY=$REGISTRY IMAGE_NAME=$IMAGE_NAME IMAGE_TAG=$IMAGE_TAG ./build-image.sh"
    fi
    echo ""
fi
