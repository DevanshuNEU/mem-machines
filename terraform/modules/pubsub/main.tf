# =============================================================================
# Pub/Sub Module - Main Configuration
# =============================================================================
#
# Creates:
# - Main topic for log ingestion
# - Push subscription to Worker service
# - Dead Letter Queue (DLQ) topic and subscription
#
# Flow:
#   Ingest API -> Topic -> Push Subscription -> Worker
#                              |
#                              v (on failure)
#                         DLQ Topic -> DLQ Subscription
#
# =============================================================================

# -----------------------------------------------------------------------------
# Main Topic
# -----------------------------------------------------------------------------

resource "google_pubsub_topic" "main" {
  name    = var.topic_name
  project = var.project_id

  # Message retention for replay capability
  message_retention_duration = "86400s"  # 24 hours

  labels = {
    environment = "prod"
    purpose     = "log-ingestion"
  }
}

# -----------------------------------------------------------------------------
# Dead Letter Queue Topic
# -----------------------------------------------------------------------------

resource "google_pubsub_topic" "dlq" {
  name    = "${var.topic_name}-dlq"
  project = var.project_id

  message_retention_duration = "604800s"  # 7 days for DLQ

  labels = {
    environment = "prod"
    purpose     = "dead-letter-queue"
  }
}

# -----------------------------------------------------------------------------
# Dead Letter Queue Subscription (for monitoring/debugging)
# -----------------------------------------------------------------------------

resource "google_pubsub_subscription" "dlq" {
  name    = "${var.topic_name}-dlq-sub"
  project = var.project_id
  topic   = google_pubsub_topic.dlq.name

  # Keep messages for 7 days
  message_retention_duration = "604800s"
  retain_acked_messages      = true

  # Long ack deadline for manual inspection
  ack_deadline_seconds = 600

  # Never expire
  expiration_policy {
    ttl = ""
  }

  labels = {
    environment = "prod"
    purpose     = "dead-letter-monitoring"
  }
}

# -----------------------------------------------------------------------------
# Worker Push Subscription
# -----------------------------------------------------------------------------

resource "google_pubsub_subscription" "worker_push" {
  name    = "${var.topic_name}-worker-push"
  project = var.project_id
  topic   = google_pubsub_topic.main.name

  # Acknowledgement deadline (max 600s for push)
  ack_deadline_seconds = var.ack_deadline

  # Push configuration to Worker service
  push_config {
    push_endpoint = var.worker_service_url

    # Authentication for Cloud Run
    oidc_token {
      service_account_email = var.invoker_service_account_email
    }

    # Attributes to include in push
    attributes = {
      x-goog-version = "v1"
    }
  }

  # Dead letter policy
  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dlq.id
    max_delivery_attempts = var.max_delivery_attempts
  }

  # Retry policy for transient failures
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }

  # Never expire the subscription
  expiration_policy {
    ttl = ""
  }

  # Enable message ordering if needed (disabled for now)
  enable_message_ordering = false

  labels = {
    environment = "prod"
    purpose     = "worker-trigger"
  }
}
