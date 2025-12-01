# =============================================================================
# Cloud Run Module - Main Configuration
# =============================================================================
#
# Deploys two Cloud Run services:
# 1. Ingest API - Public-facing, handles data ingestion
# 2. Worker - Internal, triggered by Pub/Sub
#
# =============================================================================

# -----------------------------------------------------------------------------
# Ingest API Service
# -----------------------------------------------------------------------------

resource "google_cloud_run_v2_service" "ingest_api" {
  name     = "ingest-api"
  location = var.region
  project  = var.project_id

  # Allow unauthenticated access (public API)
  ingress = "INGRESS_TRAFFIC_ALL"

  template {
    # Scaling configuration
    scaling {
      min_instance_count = var.ingest_api_min_instances
      max_instance_count = var.ingest_api_max_instances
    }

    # Container configuration
    containers {
      # Use placeholder image if none specified (for initial setup)
      image = var.ingest_api_image != "" ? var.ingest_api_image : "gcr.io/cloudrun/hello"

      # Resource limits
      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
        cpu_idle = true  # Scale to zero
      }

      # Environment variables
      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "PUBSUB_TOPIC"
        value = var.pubsub_topic
      }
      env {
        name  = "ENVIRONMENT"
        value = "production"
      }
      env {
        name  = "LOG_LEVEL"
        value = "INFO"
      }

      # Port configuration
      ports {
        container_port = 8080
      }

      # Startup probe
      startup_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        initial_delay_seconds = 0
        period_seconds        = 10
        failure_threshold     = 3
        timeout_seconds       = 3
      }

      # Liveness probe
      liveness_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        period_seconds    = 30
        failure_threshold = 3
        timeout_seconds   = 3
      }
    }

    # Request timeout
    timeout = "60s"

    # Max concurrent requests per instance
    max_instance_request_concurrency = 80
  }

  # Traffic configuration
  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  labels = {
    environment = "prod"
    component   = "ingest-api"
  }
}

# Make Ingest API publicly accessible
resource "google_cloud_run_v2_service_iam_member" "ingest_api_public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.ingest_api.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# -----------------------------------------------------------------------------
# Worker Service
# -----------------------------------------------------------------------------

resource "google_cloud_run_v2_service" "worker" {
  name     = "worker"
  location = var.region
  project  = var.project_id

  # Internal only - triggered by Pub/Sub
  ingress = "INGRESS_TRAFFIC_ALL"

  template {
    # Scaling configuration
    scaling {
      min_instance_count = var.worker_min_instances
      max_instance_count = var.worker_max_instances
    }

    # Container configuration
    containers {
      image = var.worker_image != "" ? var.worker_image : "gcr.io/cloudrun/hello"

      # Resource limits - more memory for processing
      resources {
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }
        cpu_idle = true
      }

      # Environment variables
      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "PROCESSING_DELAY_PER_CHAR"
        value = "0.05"
      }
      env {
        name  = "ENVIRONMENT"
        value = "production"
      }
      env {
        name  = "LOG_LEVEL"
        value = "INFO"
      }

      # Port
      ports {
        container_port = 8080
      }

      # Probes
      startup_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        initial_delay_seconds = 0
        period_seconds        = 10
        failure_threshold     = 3
        timeout_seconds       = 3
      }

      liveness_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        period_seconds    = 30
        failure_threshold = 3
        timeout_seconds   = 3
      }
    }

    # Long timeout for processing (9 minutes)
    timeout = "${var.worker_timeout}s"

    # Concurrency 1 for CPU-bound work - each instance handles one message
    max_instance_request_concurrency = 1
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  labels = {
    environment = "prod"
    component   = "worker"
  }
}

# Worker is NOT public - only Pub/Sub can invoke it
# IAM is configured in the main module
