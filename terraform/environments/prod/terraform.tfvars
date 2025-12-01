# =============================================================================
# Production Environment Configuration
# =============================================================================
# This configuration matches the deployed infrastructure
# Project: Memory Machines Backend Assessment
# =============================================================================

# GCP Project Configuration
project_id = "memory-machines-479818"
region     = "us-central1"
environment = "prod"

# Pub/Sub Configuration
pubsub_topic_name            = "log-ingestion"
pubsub_ack_deadline          = 600
pubsub_max_delivery_attempts = 5

# Cloud Run - Ingest API
ingest_api_image         = "us-central1-docker.pkg.dev/memory-machines-479818/cloud-run-source-deploy/ingest-api:latest"
ingest_api_min_instances = 0
ingest_api_max_instances = 10

# Cloud Run - Worker
worker_image         = "us-central1-docker.pkg.dev/memory-machines-479818/cloud-run-source-deploy/worker:latest"
worker_min_instances = 0
worker_max_instances = 10
worker_timeout       = 540
