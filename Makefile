# Memory Machines Backend Assessment

.PHONY: help setup install lint format test run-api run-worker deploy-infra clean destroy

help:
	@echo "Available commands:"
	@echo "  make setup        - Create virtual environment and install dependencies"
	@echo "  make lint         - Run linters"
	@echo "  make format       - Format code"
	@echo "  make test         - Run tests"
	@echo "  make run-api      - Run ingest API locally (port 8080)"
	@echo "  make run-worker   - Run worker locally (port 8081)"
	@echo "  make deploy-infra - Deploy infrastructure with Terraform"
	@echo "  make clean        - Remove generated files"
	@echo "  make destroy      - Destroy Terraform infrastructure"

# Setup
setup:
	python3 -m venv venv
	./venv/bin/pip install --upgrade pip
	./venv/bin/pip install -r services/ingest-api/requirements.txt
	./venv/bin/pip install -r services/worker/requirements.txt

install:
	pip install -r services/ingest-api/requirements.txt
	pip install -r services/worker/requirements.txt

# Development
lint:
	ruff check services/
	mypy services/ --ignore-missing-imports

format:
	ruff format services/
	ruff check --fix services/

test:
	pytest services/ -v

test-cov:
	pytest services/ -v --cov=services --cov-report=html

# Local running
run-api:
	cd services/ingest-api && uvicorn src.main:app --reload --port 8080

run-worker:
	cd services/worker && uvicorn src.main:app --reload --port 8081

# Deployment
deploy-infra:
	cd terraform && terraform init && terraform apply -var-file=environments/prod/terraform.tfvars

# Cleanup
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf venv/ 2>/dev/null || true

destroy:
	cd terraform && terraform destroy -var-file=environments/prod/terraform.tfvars
