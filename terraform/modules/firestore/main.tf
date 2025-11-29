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

# -----------------------------------------------------------------------------
# Composite Indexes (optional, for query optimization)
# -----------------------------------------------------------------------------

# Index for querying processed logs by timestamp within a tenant
resource "google_firestore_index" "processed_logs_by_time" {
  project    = var.project_id
  database   = google_firestore_database.main.name
  collection = "processed_logs"

  fields {
    field_path = "processed_at"
    order      = "DESCENDING"
  }

  fields {
    field_path = "__name__"
    order      = "DESCENDING"
  }

  # This is a collection group index (works across all tenant subcollections)
  query_scope = "COLLECTION_GROUP"
}
