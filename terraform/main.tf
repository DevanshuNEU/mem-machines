# =============================================================================
# Memory Machines Infrastructure - Main Configuration
# =============================================================================
#
# This Terraform configuration deploys:
#
# 1. Google Cloud APIs (enabled)
# 2. Firestore Database (Native mode)
# 3. Cloud Run Services (Ingest API + Worker)
# 4. Pub/Sub Topic and Subscriptions (with Dead Letter Queue)
# 5. IAM Configuration for service-to-service authentication
#
# Deployment Order:
#   APIs -> Firestore -> Cloud Run -> IAM -> Pub/Sub
#
# =============================================================================

# -----------------------------------------------------------------------------
# Enable Required APIs
# -----------------------------------------------------------------------------

resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "pubsub.googleapis.com",
    "firestore.googleapis.com",
    "cloudbuild.googleapis.com",
    "artifactregistry.googleapis.com",
    "iam.googleapis.com",
  ])

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

# -----------------------------------------------------------------------------
# Get Project Info
# -----------------------------------------------------------------------------

data "google_project" "project" {
  project_id = var.project_id
}

# -----------------------------------------------------------------------------
# Firestore Module
# -----------------------------------------------------------------------------

module "firestore" {
  source = "./modules/firestore"

  project_id = var.project_id
  region     = var.region

  depends_on = [google_project_service.apis]
}

# -----------------------------------------------------------------------------
# Cloud Run Module (deploys before Pub/Sub)
# -----------------------------------------------------------------------------

module "cloud_run" {
  source = "./modules/cloud-run"

  project_id = var.project_id
  region     = var.region

  # Ingest API Configuration
  ingest_api_image         = var.ingest_api_image
  ingest_api_min_instances = var.ingest_api_min_instances
  ingest_api_max_instances = var.ingest_api_max_instances

  # Worker Configuration
  worker_image         = var.worker_image
  worker_min_instances = var.worker_min_instances
  worker_max_instances = var.worker_max_instances
  worker_timeout       = var.worker_timeout

  # Environment
  pubsub_topic = var.pubsub_topic_name

  depends_on = [google_project_service.apis]
}

# -----------------------------------------------------------------------------
# Service Account for Pub/Sub -> Cloud Run
# -----------------------------------------------------------------------------

resource "google_service_account" "pubsub_invoker" {
  account_id   = "pubsub-invoker"
  display_name = "Pub/Sub to Cloud Run Invoker"
  description  = "Service account used by Pub/Sub to invoke Cloud Run Worker"
  project      = var.project_id

  depends_on = [google_project_service.apis]
}

# Grant the service account permission to invoke Worker
resource "google_cloud_run_v2_service_iam_member" "worker_invoker" {
  project  = var.project_id
  location = var.region
  name     = module.cloud_run.worker_name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.pubsub_invoker.email}"

  depends_on = [module.cloud_run]
}

# Grant Pub/Sub the ability to create auth tokens
resource "google_project_iam_member" "pubsub_token_creator" {
  project = var.project_id
  role    = "roles/iam.serviceAccountTokenCreator"
  member  = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-pubsub.iam.gserviceaccount.com"

  depends_on = [google_project_service.apis]
}

# -----------------------------------------------------------------------------
# IAM Bindings for Default Compute Service Account
# -----------------------------------------------------------------------------
# These permissions are needed for Cloud Build and Cloud Run

resource "google_project_iam_member" "compute_storage_admin" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${data.google_project.project.number}-compute@developer.gserviceaccount.com"
}

resource "google_project_iam_member" "compute_logging" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${data.google_project.project.number}-compute@developer.gserviceaccount.com"
}

resource "google_project_iam_member" "compute_artifact_registry" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${data.google_project.project.number}-compute@developer.gserviceaccount.com"
}

resource "google_project_iam_member" "compute_pubsub" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${data.google_project.project.number}-compute@developer.gserviceaccount.com"
}

resource "google_project_iam_member" "compute_firestore" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${data.google_project.project.number}-compute@developer.gserviceaccount.com"
}

# -----------------------------------------------------------------------------
# Pub/Sub Module (deploys after Cloud Run and IAM)
# -----------------------------------------------------------------------------

module "pubsub" {
  source = "./modules/pubsub"

  project_id                    = var.project_id
  topic_name                    = var.pubsub_topic_name
  ack_deadline                  = var.pubsub_ack_deadline
  max_delivery_attempts         = var.pubsub_max_delivery_attempts
  worker_service_url            = module.cloud_run.worker_url
  invoker_service_account_email = google_service_account.pubsub_invoker.email

  depends_on = [
    google_project_service.apis,
    module.cloud_run,
    google_service_account.pubsub_invoker,
    google_cloud_run_v2_service_iam_member.worker_invoker,
    google_project_iam_member.pubsub_token_creator,
  ]
}
