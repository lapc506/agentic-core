#!/usr/bin/env bash
# =============================================================================
# create-secret.sh — Create K8s secret for agentic-core dev environment
#
# Generates random credentials for local development. NEVER use in production.
# Pattern: altrupets-monorepo/infrastructure/scripts/create-fallback-secret.sh
# =============================================================================
set -euo pipefail

NAMESPACE="${1:-agentic-core}"
SECRET_NAME="agentic-core-secret"

# Auto-generate dev-only credentials
DB_PASSWORD="dev-$(openssl rand -hex 12)"
DB_USER="agentic"
DB_NAME="agentic"

echo "=== Creating dev secret in namespace: $NAMESPACE ==="

# Ensure namespace exists
kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -

# Delete existing secret if present
kubectl delete secret "$SECRET_NAME" -n "$NAMESPACE" 2>/dev/null || true

# Create secret
kubectl create secret generic "$SECRET_NAME" \
    --namespace="$NAMESPACE" \
    --from-literal=AGENTIC_POSTGRES_DSN="postgresql://${DB_USER}:${DB_PASSWORD}@postgres.${NAMESPACE}.svc.cluster.local:5432/${DB_NAME}" \
    --from-literal=AGENTIC_REDIS_URL="redis://redis.${NAMESPACE}.svc.cluster.local:6379" \
    --from-literal=AGENTIC_FALKORDB_URL="redis://falkordb.${NAMESPACE}.svc.cluster.local:6380" \
    --from-literal=POSTGRES_USER="$DB_USER" \
    --from-literal=POSTGRES_PASSWORD="$DB_PASSWORD" \
    --from-literal=POSTGRES_DB="$DB_NAME"

echo "Secret '$SECRET_NAME' created."
echo "DB password: $DB_PASSWORD (dev-only, auto-generated)"
