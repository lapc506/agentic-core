# =============================================================================
# agentic-core Makefile
#
# Naming convention (Minikube targets): dev-<resource>-<verb>
# Pattern reference: altrupets-monorepo/Makefile
# =============================================================================

# --- Variables ---------------------------------------------------------------

ENV            ?= dev
NAMESPACE      ?= agentic-core
MINIKUBE_PROFILE ?= agentic-core
IMAGE_NAME     ?= localhost/agentic-core
IMAGE_TAG      ?= dev
HELM_RELEASE   ?= agentic-core
HELM_CHART     ?= deployment/helm/agentic-core
HELM_VALUES_DEV ?= $(HELM_CHART)/values-dev.yaml

K8S_DEPS_DIR   = k8s/dependencies
SCRIPTS_DIR    = infrastructure/scripts

# --- Phony -------------------------------------------------------------------

.PHONY: help proto test lint typecheck \
	bootstrap-dev \
	dev-minikube-start dev-minikube-stop dev-minikube-destroy dev-minikube-status \
	dev-secret-create \
	dev-deps-deploy dev-deps-destroy dev-deps-status dev-deps-wait \
	dev-build dev-build-push \
	dev-deploy dev-deploy-destroy dev-deploy-upgrade \
	dev-port-forward dev-port-forward-stop \
	dev-logs dev-logs-deps \
	dev-status \
	dev-clean \
	build-web build-docker up down clean \
	build-desktop desktop desktop-dev \
	tui tui-build \
	docs-site docs-specs docs

# =============================================================================
# HELP (default target)
# =============================================================================

help: ## Show this help
	@echo ""
	@echo "  agentic-core — AI Agent Orchestration Library"
	@echo "  =============================================="
	@echo ""
	@echo "  Development:"
	@echo "    make test              Run unit tests"
	@echo "    make lint              Run ruff linter"
	@echo "    make typecheck         Run mypy strict"
	@echo ""
	@echo "  Bootstrap (one-command cluster setup):"
	@echo "    make bootstrap-dev     Full local cluster: minikube + deps + build + deploy"
	@echo ""
	@echo "  Minikube Cluster:"
	@echo "    make dev-minikube-start     Start Minikube cluster"
	@echo "    make dev-minikube-stop      Pause cluster (preserves state)"
	@echo "    make dev-minikube-destroy   Delete cluster entirely"
	@echo "    make dev-minikube-status    Show cluster status"
	@echo ""
	@echo "  Dependencies (Redis, PostgreSQL+pgvector, FalkorDB):"
	@echo "    make dev-deps-deploy        Deploy all dependencies"
	@echo "    make dev-deps-destroy       Remove all dependencies"
	@echo "    make dev-deps-status        Show dependency pod status"
	@echo "    make dev-deps-wait          Wait for all deps to be ready"
	@echo ""
	@echo "  Build & Deploy (standalone mode):"
	@echo "    make dev-build              Build image into Minikube"
	@echo "    make dev-deploy             Helm install agentic-core"
	@echo "    make dev-deploy-upgrade     Helm upgrade (after rebuild)"
	@echo "    make dev-deploy-destroy     Helm uninstall"
	@echo ""
	@echo "  Access:"
	@echo "    make dev-port-forward       Forward WS:8765 + gRPC:50051"
	@echo "    make dev-port-forward-stop  Kill port-forward processes"
	@echo ""
	@echo "  Observability:"
	@echo "    make dev-logs               Tail agentic-core logs"
	@echo "    make dev-logs-deps          Tail dependency logs"
	@echo "    make dev-status             Full cluster status report"
	@echo ""
	@echo "  Cleanup:"
	@echo "    make dev-clean              Destroy everything (cluster + images)"
	@echo ""

# =============================================================================
# DEVELOPMENT (local, no K8s)
# =============================================================================

proto:
	python -m grpc_tools.protoc \
		-I proto \
		--python_out=src/agentic_core/adapters/primary/grpc/generated \
		--grpc_python_out=src/agentic_core/adapters/primary/grpc/generated \
		--pyi_out=src/agentic_core/adapters/primary/grpc/generated \
		proto/agentic_core.proto

test:
	pytest --cov=agentic_core --cov-report=term-missing -v

lint:
	ruff check src/ tests/

typecheck:
	mypy src/agentic_core/

# =============================================================================
# BOOTSTRAP — one command to rule them all
# =============================================================================

bootstrap-dev: dev-minikube-start dev-secret-create dev-deps-deploy dev-deps-wait dev-build dev-deploy ## Full local cluster setup
	@echo ""
	@echo "=== agentic-core cluster ready ==="
	@echo ""
	@echo "  Run:  make dev-port-forward"
	@echo "  Then: ws://localhost:8765  (WebSocket)"
	@echo "        localhost:50051      (gRPC)"
	@echo ""

# =============================================================================
# MINIKUBE CLUSTER
# =============================================================================

dev-minikube-start: ## Start Minikube cluster
	@bash $(SCRIPTS_DIR)/start-minikube.sh

dev-minikube-stop: ## Pause cluster (preserves state)
	minikube stop -p $(MINIKUBE_PROFILE)

dev-minikube-destroy: ## Delete cluster entirely
	minikube delete -p $(MINIKUBE_PROFILE) || true
	@echo "Cluster '$(MINIKUBE_PROFILE)' destroyed."

dev-minikube-status: ## Show cluster status
	@minikube status -p $(MINIKUBE_PROFILE) 2>/dev/null || echo "Cluster not running"

# =============================================================================
# SECRETS
# =============================================================================

dev-secret-create: ## Create dev secrets (auto-generated passwords)
	@bash $(SCRIPTS_DIR)/create-secret.sh $(NAMESPACE)

# =============================================================================
# DEPENDENCIES (Redis, PostgreSQL+pgvector, FalkorDB)
# =============================================================================

dev-deps-deploy: ## Deploy all dependencies into cluster
	@echo "=== Deploying dependencies ==="
	kubectl apply -f $(K8S_DEPS_DIR)/namespace.yaml
	kubectl apply -f $(K8S_DEPS_DIR)/redis/
	kubectl apply -f $(K8S_DEPS_DIR)/postgres/
	kubectl apply -f $(K8S_DEPS_DIR)/falkordb/
	@echo "Dependencies deployed."

dev-deps-destroy: ## Remove all dependency deployments
	kubectl delete -f $(K8S_DEPS_DIR)/falkordb/ --ignore-not-found
	kubectl delete -f $(K8S_DEPS_DIR)/postgres/ --ignore-not-found
	kubectl delete -f $(K8S_DEPS_DIR)/redis/ --ignore-not-found
	@echo "Dependencies removed."

dev-deps-status: ## Show dependency pod status
	@kubectl get pods -n $(NAMESPACE) -l 'app in (redis,postgres,falkordb)' -o wide

dev-deps-wait: ## Wait for all dependencies to be ready
	@echo "Waiting for Redis..."
	@kubectl wait --for=condition=Ready pod -l app=redis -n $(NAMESPACE) --timeout=120s
	@echo "Waiting for PostgreSQL..."
	@kubectl wait --for=condition=Ready pod -l app=postgres -n $(NAMESPACE) --timeout=120s
	@echo "Waiting for FalkorDB..."
	@kubectl wait --for=condition=Ready pod -l app=falkordb -n $(NAMESPACE) --timeout=120s
	@echo "All dependencies ready."

# =============================================================================
# BUILD — container image into Minikube
# =============================================================================

dev-build: ## Build agentic-core image and load into Minikube
	@echo "=== Building agentic-core image ==="
	podman build \
		-t $(IMAGE_NAME):$(IMAGE_TAG) \
		-f deployment/docker/Dockerfile \
		.
	@echo "Loading image into Minikube..."
	podman save $(IMAGE_NAME):$(IMAGE_TAG) | minikube -p $(MINIKUBE_PROFILE) image load -
	@echo "Image loaded: $(IMAGE_NAME):$(IMAGE_TAG)"

dev-build-push: dev-build ## Alias: build + push (same as dev-build for local)

# =============================================================================
# DEPLOY — Helm install/upgrade agentic-core (standalone)
# =============================================================================

dev-deploy: ## Helm install agentic-core
	@echo "=== Deploying agentic-core (standalone) ==="
	helm upgrade --install $(HELM_RELEASE) $(HELM_CHART) \
		-f $(HELM_VALUES_DEV) \
		-n $(NAMESPACE) \
		--create-namespace \
		--wait --timeout 120s
	@echo "agentic-core deployed."

dev-deploy-upgrade: dev-build ## Rebuild image + Helm upgrade
	helm upgrade $(HELM_RELEASE) $(HELM_CHART) \
		-f $(HELM_VALUES_DEV) \
		-n $(NAMESPACE) \
		--wait --timeout 120s
	@echo "agentic-core upgraded."

dev-deploy-destroy: ## Helm uninstall agentic-core
	helm uninstall $(HELM_RELEASE) -n $(NAMESPACE) || true
	@echo "agentic-core removed."

# =============================================================================
# PORT FORWARDING — local access to cluster services
# =============================================================================

dev-port-forward: ## Forward WebSocket (8765) + gRPC (50051) to localhost
	@echo "=== Port forwarding ==="
	@echo "  WebSocket: localhost:8765"
	@echo "  gRPC:      localhost:50051"
	@echo "  Press Ctrl+C to stop"
	@echo ""
	@kubectl port-forward -n $(NAMESPACE) svc/$(HELM_RELEASE)-agentic-core 8765:8765 50051:50051

dev-port-forward-bg: ## Port forward in background (PID saved to .port-forward.pid)
	@kubectl port-forward -n $(NAMESPACE) svc/$(HELM_RELEASE)-agentic-core 8765:8765 50051:50051 &
	@echo $$! > .port-forward.pid
	@echo "Port forwarding started (PID: $$(cat .port-forward.pid))"

dev-port-forward-stop: ## Kill background port-forward
	@if [ -f .port-forward.pid ]; then \
		kill $$(cat .port-forward.pid) 2>/dev/null || true; \
		rm -f .port-forward.pid; \
		echo "Port forwarding stopped."; \
	else \
		echo "No port-forward PID file found."; \
	fi

# =============================================================================
# POSTGRES PORT FORWARD — direct DB access (DBeaver, psql)
# =============================================================================

dev-postgres-port-forward: ## Forward PostgreSQL to localhost:5432
	@echo "PostgreSQL available at localhost:5432"
	@kubectl port-forward -n $(NAMESPACE) svc/postgres 5432:5432

# =============================================================================
# OBSERVABILITY — logs and status
# =============================================================================

dev-logs: ## Tail agentic-core container logs
	kubectl logs -n $(NAMESPACE) -l app=agentic-core -f --tail=100

dev-logs-deps: ## Tail all dependency logs
	@echo "=== Redis ===" && kubectl logs -n $(NAMESPACE) -l app=redis --tail=5 2>/dev/null; \
	echo "=== PostgreSQL ===" && kubectl logs -n $(NAMESPACE) -l app=postgres --tail=5 2>/dev/null; \
	echo "=== FalkorDB ===" && kubectl logs -n $(NAMESPACE) -l app=falkordb --tail=5 2>/dev/null

dev-status: ## Full cluster status report
	@echo "=== Minikube ==="
	@minikube status -p $(MINIKUBE_PROFILE) 2>/dev/null || echo "Not running"
	@echo ""
	@echo "=== Namespace: $(NAMESPACE) ==="
	@kubectl get all -n $(NAMESPACE) 2>/dev/null || echo "Namespace not found"
	@echo ""
	@echo "=== Helm Releases ==="
	@helm list -n $(NAMESPACE) 2>/dev/null || echo "No releases"

# =============================================================================
# CLEANUP
# =============================================================================

dev-clean: dev-port-forward-stop dev-deploy-destroy dev-deps-destroy dev-minikube-destroy ## Destroy everything
	podman rmi $(IMAGE_NAME):$(IMAGE_TAG) 2>/dev/null || true
	@echo "Full cleanup complete."

# =============================================================================
# STANDALONE AGENT STUDIO (docker compose, no K8s)
# =============================================================================

build-web:
	cd ui && flutter pub get && flutter build web --release

build-docker: build-web
	podman build -t agentic-core -f deployment/docker/Dockerfile .

up: build-docker
	podman compose up -d
	@echo "Agent Studio running at http://localhost:8765"

down:
	podman compose down

clean-compose:
	podman compose down -v
	podman rmi agentic-core 2>/dev/null || true
	rm -rf ui/build/

# --- Desktop App (Linux) ---

build-desktop:
	cd ui && flutter build linux --release

desktop: build-docker
	@echo "Starting backend services..."
	podman compose up -d
	@echo "Waiting for backend..."
	@sleep 3
	@echo "Launching Agent Studio Desktop..."
	cd ui && ./build/linux/x64/release/bundle/agent_studio

desktop-dev:
	@echo "Starting backend services..."
	podman compose up -d
	@echo "Launching Flutter Desktop (hot reload)..."
	cd ui && flutter run -d linux

# --- TUI ---

tui:
	cd tui && go run . --url http://localhost:8080

tui-build:
	cd tui && go build -o agentic-tui .

# --- Documentation ---

docs-site:
	cd docs/site && zensical build

docs-specs:
	cd docs/specs && myst build --html

docs: docs-site docs-specs
