# =============================================================================
# Cloud Run Module - Outputs
# =============================================================================

output "ingest_api_url" {
  description = "URL of the Ingest API service"
  value       = google_cloud_run_v2_service.ingest_api.uri
}

output "ingest_api_name" {
  description = "Name of the Ingest API service"
  value       = google_cloud_run_v2_service.ingest_api.name
}

output "worker_url" {
  description = "URL of the Worker service"
  value       = google_cloud_run_v2_service.worker.uri
}

output "worker_name" {
  description = "Name of the Worker service"
  value       = google_cloud_run_v2_service.worker.name
}
