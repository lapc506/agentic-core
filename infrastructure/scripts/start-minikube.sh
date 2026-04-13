#!/usr/bin/env bash
# =============================================================================
# start-minikube.sh — Start or reuse a Minikube cluster for agentic-core
#
# Pattern: altrupets-monorepo/infrastructure/scripts/start-minikube.sh
# Driver: podman (rootless, more efficient than Docker on Linux)
# =============================================================================
set -euo pipefail

PROFILE="${MINIKUBE_PROFILE:-agentic-core}"
CPUS="${MINIKUBE_CPUS:-4}"
MEMORY="${MINIKUBE_MEMORY:-8192}"
DISK="${MINIKUBE_DISK:-30g}"
DRIVER="${MINIKUBE_DRIVER:-podman}"
K8S_VERSION="${MINIKUBE_K8S_VERSION:-stable}"

echo "=== agentic-core Minikube cluster ==="
echo "Profile:    $PROFILE"
echo "Driver:     $DRIVER"
echo "Resources:  ${CPUS} CPUs, ${MEMORY}MB RAM, ${DISK} disk"

# Check if cluster already running
if minikube status -p "$PROFILE" 2>/dev/null | grep -q "Running"; then
    echo "Cluster '$PROFILE' already running. Reusing."
    exit 0
fi

# Clean stale locks (podman driver quirk)
rm -rf /tmp/minikube-locks/ 2>/dev/null || true

# Start cluster
minikube start \
    --profile="$PROFILE" \
    --driver="$DRIVER" \
    --cpus="$CPUS" \
    --memory="$MEMORY" \
    --disk-size="$DISK" \
    --kubernetes-version="$K8S_VERSION" \
    --addons=metrics-server

echo "Cluster '$PROFILE' is running."
echo "Context: $(kubectl config current-context)"
