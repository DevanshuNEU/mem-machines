# =============================================================================
# Firestore Module - Variables
# =============================================================================

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP region (used for reference, Firestore uses location_id)"
  type        = string
}

variable "firestore_location" {
  description = "Firestore database location"
  type        = string
  default     = "nam5"  # US multi-region (free tier friendly)
}
