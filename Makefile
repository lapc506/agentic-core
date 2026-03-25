.PHONY: proto test lint typecheck

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
