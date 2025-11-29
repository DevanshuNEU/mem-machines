# =============================================================================
# Firestore Module - Outputs
# =============================================================================

output "database_name" {
  description = "Firestore database name"
  value       = google_firestore_database.main.name
}

output "database_id" {
  description = "Firestore database ID"
  value       = google_firestore_database.main.id
}
