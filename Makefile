# =============================================================================
# Memory Machines Backend Assessment
# Robust Data Processing Pipeline
# =============================================================================

.PHONY: help setup install lint test deploy-infra deploy-services clean

# Default target
help:
	@echo "Memory Machines Assessment - Available Commands"
	@echo "================================================"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make setup          - Create virtual environment and install dependencies"
	@echo "  make install        - Install all dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make lint           - Run linters (ruff, mypy)"
	@echo "  make format         - Format code with ruff"
	@echo "  make test           - Run all tests"
	@echo "  make test-cov       - Run tests with coverage"
	@echo ""
	@echo "Local Running:"
	@echo "  make run-api        - Run ingest API locally"
	@echo "  make run-worker     - Run worker locally"
	@echo ""
	@echo "Deployment:"
	@echo "  make deploy-infra   - Deploy infrastructure with Terraform"
	@echo "  make deploy-services - Build and deploy Cloud Run services"
	@echo "  make deploy-all     - Deploy everything"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean          - Remove generated files"
	@echo "  make destroy        - Destroy Terraform infrastructure"

# -----------------------------------------------------------------------------
# Setup & Installation
# -----------------------------------------------------------------------------

setup:
	python3 -m venv venv
	./venv/bin/pip install --upgrade pip
	./venv/bin/pip install -r services/ingest-api/requirements.txt
	./venv/bin/pip install -r services/worker/requirements.txt
	@echo "✅ Setup complete! Activate with: source venv/bin/activate"

install:
	pip install -r services/ingest-api/requirements.txt
	pip install -r services/worker/requirements.txt

# -----------------------------------------------------------------------------
# Development
# -----------------------------------------------------------------------------

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

# -----------------------------------------------------------------------------
# Local Running
# -----------------------------------------------------------------------------

run-api:
	cd services/ingest-api && uvicorn src.main:app --reload --port 8080

run-worker:
	cd services/worker && uvicorn src.main:app --reload --port 8081

# -----------------------------------------------------------------------------
# Deployment
# -----------------------------------------------------------------------------

deploy-infra:
	cd terraform && terraform init && terraform apply -auto-approve

deploy-services:
	@echo "Building and deploying Ingest API..."
	cd services/ingest-api && gcloud run deploy ingest-api \
		--source . \
		--region $(GCP_REGION) \
		--allow-unauthenticated \
		--set-env-vars="GCP_PROJECT_ID=$(GCP_PROJECT_ID)"
	@echo "Building and deploying Worker..."
	cd services/worker && gcloud run deploy worker \
		--source . \
		--region $(GCP_REGION) \
		--no-allow-unauthenticated \
		--set-env-vars="GCP_PROJECT_ID=$(GCP_PROJECT_ID)"

deploy-all: deploy-infra deploy-services
	@echo "✅ Full deployment complete!"

# -----------------------------------------------------------------------------
# Cleanup
# -----------------------------------------------------------------------------

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	rm -rf venv/ 2>/dev/null || true
	@echo "✅ Cleaned!"

destroy:
	cd terraform && terraform destroy -auto-approve
	@echo "⚠️  Infrastructure destroyed!"
