# =============================================================================
# Terraform Variables
# =============================================================================

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP region for resources"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "prod"
}

# =============================================================================
# Pub/Sub Configuration
# =============================================================================

variable "pubsub_topic_name" {
  description = "Name of the Pub/Sub topic for log ingestion"
  type        = string
  default     = "log-ingestion"
}

variable "pubsub_ack_deadline" {
  description = "Acknowledgement deadline in seconds (max 600 for push)"
  type        = number
  default     = 600
}

variable "pubsub_max_delivery_attempts" {
  description = "Maximum delivery attempts before dead-lettering"
  type        = number
  default     = 5
}

# =============================================================================
# Cloud Run Configuration
# =============================================================================

variable "ingest_api_image" {
  description = "Container image for the Ingest API service"
  type        = string
  default     = ""
}

variable "worker_image" {
  description = "Container image for the Worker service"
  type        = string
  default     = ""
}

variable "ingest_api_min_instances" {
  description = "Minimum instances for Ingest API (0 for scale to zero)"
  type        = number
  default     = 0
}

variable "ingest_api_max_instances" {
  description = "Maximum instances for Ingest API"
  type        = number
  default     = 10
}

variable "worker_min_instances" {
  description = "Minimum instances for Worker (0 for scale to zero)"
  type        = number
  default     = 0
}

variable "worker_max_instances" {
  description = "Maximum instances for Worker"
  type        = number
  default     = 10
}

variable "worker_timeout" {
  description = "Worker request timeout in seconds"
  type        = number
  default     = 540  # 9 minutes - allows for long processing
}
