# =============================================================================
# Cloud Run Module - Variables
# =============================================================================

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP region for Cloud Run services"
  type        = string
}

# -----------------------------------------------------------------------------
# Ingest API Configuration
# -----------------------------------------------------------------------------

variable "ingest_api_image" {
  description = "Container image for Ingest API"
  type        = string
  default     = ""
}

variable "ingest_api_min_instances" {
  description = "Minimum instances (0 for scale-to-zero)"
  type        = number
  default     = 0
}

variable "ingest_api_max_instances" {
  description = "Maximum instances"
  type        = number
  default     = 10
}

# -----------------------------------------------------------------------------
# Worker Configuration
# -----------------------------------------------------------------------------

variable "worker_image" {
  description = "Container image for Worker"
  type        = string
  default     = ""
}

variable "worker_min_instances" {
  description = "Minimum instances (0 for scale-to-zero)"
  type        = number
  default     = 0
}

variable "worker_max_instances" {
  description = "Maximum instances"
  type        = number
  default     = 10
}

variable "worker_timeout" {
  description = "Request timeout in seconds"
  type        = number
  default     = 540
}

# -----------------------------------------------------------------------------
# Shared Configuration
# -----------------------------------------------------------------------------

variable "pubsub_topic" {
  description = "Pub/Sub topic name for environment variable"
  type        = string
}
