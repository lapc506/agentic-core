.PHONY: proto test lint typecheck build-web build-docker up down clean docs-site docs-specs docs

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

# --- Standalone Agent Studio ---

build-web:
	cd ui && flutter pub get && flutter build web --release

build-docker: build-web
	podman build -t agentic-core -f deployment/docker/Dockerfile .

up: build-docker
	podman compose up -d
	@echo "Agent Studio running at http://localhost:8765"

down:
	podman compose down

clean:
	podman compose down -v
	podman rmi agentic-core 2>/dev/null || true
	rm -rf ui/build/

# --- Documentation ---

docs-site:
	cd docs/site && zensical build

docs-specs:
	cd docs/specs && myst build --html

docs: docs-site docs-specs
