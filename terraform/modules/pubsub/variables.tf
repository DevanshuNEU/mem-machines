# =============================================================================
# Pub/Sub Module - Variables
# =============================================================================

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "topic_name" {
  description = "Name of the main Pub/Sub topic"
  type        = string
}

variable "worker_service_url" {
  description = "URL of the Worker Cloud Run service"
  type        = string
}

variable "invoker_service_account_email" {
  description = "Service account email for Pub/Sub to invoke Cloud Run"
  type        = string
}

variable "ack_deadline" {
  description = "Acknowledgement deadline in seconds (max 600 for push)"
  type        = number
  default     = 600
}

variable "max_delivery_attempts" {
  description = "Maximum delivery attempts before dead-lettering"
  type        = number
  default     = 5
}
