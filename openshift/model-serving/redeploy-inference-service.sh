#!/bin/bash

set -e

echo "=========================================="
echo "Redéploiement de l'InferenceService"
echo "=========================================="
echo ""

NAMESPACE="train-detection"
INFERENCE_SERVICE="train-person-detection"

echo "1. Suppression de l'InferenceService actuel (avec les anciens arguments)..."
oc delete inferenceservice $INFERENCE_SERVICE -n $NAMESPACE --ignore-not-found=true

echo ""
echo "2. Attente de la suppression complète..."
sleep 5

echo ""
echo "3. Vérification que le ServingRuntime triton-runtime existe..."
if oc get servingruntime triton-runtime -n $NAMESPACE &>/dev/null; then
    echo "   ✓ ServingRuntime 'triton-runtime' existe"
    oc get servingruntime triton-runtime -n $NAMESPACE
else
    echo "   ✗ ServingRuntime 'triton-runtime' n'existe pas!"
    echo "   Déploiement du ServingRuntime..."
    oc apply -f serving-runtime.yaml
fi

echo ""
echo "4. Déploiement du nouveau InferenceService..."
oc apply -f inference-service.yaml

echo ""
echo "5. Attente du déploiement (peut prendre 1-2 minutes)..."
echo "   Surveillance du statut (CTRL+C pour arrêter):"
echo ""

oc get inferenceservice $INFERENCE_SERVICE -n $NAMESPACE -w &
WATCH_PID=$!

# Attendre 60 secondes puis arrêter le watch
sleep 60
kill $WATCH_PID 2>/dev/null || true

echo ""
echo ""
echo "=========================================="
echo "Vérification finale"
echo "=========================================="

echo ""
echo "InferenceService:"
oc get inferenceservice $INFERENCE_SERVICE -n $NAMESPACE

echo ""
echo "Pods:"
oc get pods -l serving.kserve.io/inferenceservice=$INFERENCE_SERVICE -n $NAMESPACE

echo ""
echo "Pour voir les logs du pod:"
echo "  oc logs -f \$(oc get pod -l serving.kserve.io/inferenceservice=$INFERENCE_SERVICE -n $NAMESPACE -o jsonpath='{.items[0].metadata.name}') -c kserve-container"

echo ""
echo "Pour voir les détails du pod:"
echo "  oc describe pod -l serving.kserve.io/inferenceservice=$INFERENCE_SERVICE -n $NAMESPACE"

echo ""
echo "=========================================="
