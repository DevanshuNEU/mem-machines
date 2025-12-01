# =============================================================================
# Firestore Module - Main Configuration
# =============================================================================
#
# Creates a Firestore database in Native mode for multi-tenant data storage.
#
# Data Structure:
#   tenants/{tenant_id}/processed_logs/{log_id}
#
# =============================================================================

# -----------------------------------------------------------------------------
# Firestore Database
# -----------------------------------------------------------------------------

resource "google_firestore_database" "main" {
  project     = var.project_id
  name        = "(default)"
  location_id = var.firestore_location
  type        = "FIRESTORE_NATIVE"

  # Concurrency mode for better performance
  concurrency_mode            = "OPTIMISTIC"
  app_engine_integration_mode = "DISABLED"

  # Prevent accidental deletion
  deletion_policy = "DELETE"
}

# Note: Composite indexes removed - Firestore auto-creates single-field indexes
