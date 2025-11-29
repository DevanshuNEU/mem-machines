#!/bin/bash
# =============================================================================
# Deployment Script
# =============================================================================
# Deploys the Memory Machines infrastructure and services to GCP
#
# Usage:
#   ./scripts/deploy.sh <project-id> [region]
#
# Example:
#   ./scripts/deploy.sh my-gcp-project us-central1
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# =============================================================================
# Configuration
# =============================================================================

PROJECT_ID=${1:-""}
REGION=${2:-"us-central1"}

if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}Error: Project ID is required${NC}"
    echo "Usage: ./scripts/deploy.sh <project-id> [region]"
    exit 1
fi

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}Memory Machines Deployment${NC}"
echo -e "${GREEN}============================================${NC}"
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# =============================================================================
# Step 1: Set GCP Project
# =============================================================================

echo -e "${YELLOW}Step 1: Setting GCP project...${NC}"
gcloud config set project $PROJECT_ID
echo -e "${GREEN}✓ Project set${NC}"
echo ""

# =============================================================================
# Step 2: Enable APIs
# =============================================================================

echo -e "${YELLOW}Step 2: Enabling required APIs...${NC}"
gcloud services enable \
    run.googleapis.com \
    pubsub.googleapis.com \
    firestore.googleapis.com \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com \
    --quiet

echo -e "${GREEN}✓ APIs enabled${NC}"
echo ""

# =============================================================================
# Step 3: Build and Deploy Ingest API
# =============================================================================

echo -e "${YELLOW}Step 3: Building and deploying Ingest API...${NC}"
cd services/ingest-api

gcloud run deploy ingest-api \
    --source . \
    --region $REGION \
    --allow-unauthenticated \
    --set-env-vars="GCP_PROJECT_ID=$PROJECT_ID,PUBSUB_TOPIC=log-ingestion" \
    --min-instances=0 \
    --max-instances=10 \
    --memory=512Mi \
    --timeout=60s \
    --quiet

INGEST_API_URL=$(gcloud run services describe ingest-api --region $REGION --format='value(status.url)')
echo -e "${GREEN}✓ Ingest API deployed: $INGEST_API_URL${NC}"
cd ../..
echo ""

# =============================================================================
# Step 4: Build and Deploy Worker
# =============================================================================

echo -e "${YELLOW}Step 4: Building and deploying Worker...${NC}"
cd services/worker

gcloud run deploy worker \
    --source . \
    --region $REGION \
    --no-allow-unauthenticated \
    --set-env-vars="GCP_PROJECT_ID=$PROJECT_ID" \
    --min-instances=0 \
    --max-instances=10 \
    --memory=1Gi \
    --timeout=540s \
    --quiet

WORKER_URL=$(gcloud run services describe worker --region $REGION --format='value(status.url)')
echo -e "${GREEN}✓ Worker deployed: $WORKER_URL${NC}"
cd ../..
echo ""

# =============================================================================
# Step 5: Create Pub/Sub Topic
# =============================================================================

echo -e "${YELLOW}Step 5: Creating Pub/Sub topic...${NC}"

# Create main topic
gcloud pubsub topics create log-ingestion --quiet 2>/dev/null || echo "Topic already exists"

# Create DLQ topic
gcloud pubsub topics create log-ingestion-dlq --quiet 2>/dev/null || echo "DLQ topic already exists"

echo -e "${GREEN}✓ Pub/Sub topics created${NC}"
echo ""

# =============================================================================
# Step 6: Create Service Account for Pub/Sub
# =============================================================================

echo -e "${YELLOW}Step 6: Setting up service account...${NC}"

# Create service account
gcloud iam service-accounts create pubsub-invoker \
    --display-name="Pub/Sub to Cloud Run Invoker" \
    --quiet 2>/dev/null || echo "Service account already exists"

SA_EMAIL="pubsub-invoker@${PROJECT_ID}.iam.gserviceaccount.com"

# Grant invoker permission on Worker
gcloud run services add-iam-policy-binding worker \
    --region=$REGION \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/run.invoker" \
    --quiet

# Get project number
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')

# Grant token creator to Pub/Sub service account
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-pubsub.iam.gserviceaccount.com" \
    --role="roles/iam.serviceAccountTokenCreator" \
    --quiet

echo -e "${GREEN}✓ Service account configured${NC}"
echo ""

# =============================================================================
# Step 7: Create Pub/Sub Subscription
# =============================================================================

echo -e "${YELLOW}Step 7: Creating Pub/Sub subscription...${NC}"

# Delete existing subscription if it exists (to update configuration)
gcloud pubsub subscriptions delete log-ingestion-worker-push --quiet 2>/dev/null || true

# Create push subscription
gcloud pubsub subscriptions create log-ingestion-worker-push \
    --topic=log-ingestion \
    --push-endpoint=$WORKER_URL \
    --push-auth-service-account=$SA_EMAIL \
    --ack-deadline=600 \
    --max-delivery-attempts=5 \
    --dead-letter-topic=log-ingestion-dlq \
    --quiet

# Create DLQ subscription for monitoring
gcloud pubsub subscriptions create log-ingestion-dlq-sub \
    --topic=log-ingestion-dlq \
    --ack-deadline=600 \
    --quiet 2>/dev/null || echo "DLQ subscription already exists"

echo -e "${GREEN}✓ Pub/Sub subscription created${NC}"
echo ""

# =============================================================================
# Step 8: Initialize Firestore
# =============================================================================

echo -e "${YELLOW}Step 8: Initializing Firestore...${NC}"

# Firestore needs to be initialized via console or API
# Check if already initialized
gcloud firestore databases describe --quiet 2>/dev/null || {
    echo "Creating Firestore database..."
    gcloud firestore databases create --region=$REGION --quiet
}

echo -e "${GREEN}✓ Firestore initialized${NC}"
echo ""

# =============================================================================
# Summary
# =============================================================================

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "Ingest API URL: $INGEST_API_URL"
echo "Worker URL: $WORKER_URL (internal only)"
echo ""
echo "Test the API:"
echo "  curl -X POST $INGEST_API_URL/ingest \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"tenant_id\": \"test\", \"text\": \"Hello World\"}'"
echo ""
echo "Run load test:"
echo "  python scripts/load_test.py --url $INGEST_API_URL --rpm 100 --duration 60"
echo ""
