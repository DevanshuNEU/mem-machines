# =============================================================================
# Terraform Outputs
# =============================================================================

output "ingest_api_url" {
  description = "URL of the Ingest API service"
  value       = module.cloud_run.ingest_api_url
}

output "worker_url" {
  description = "URL of the Worker service (internal)"
  value       = module.cloud_run.worker_url
}

output "pubsub_topic" {
  description = "Pub/Sub topic name"
  value       = module.pubsub.topic_name
}

output "pubsub_subscription" {
  description = "Pub/Sub subscription name"
  value       = module.pubsub.subscription_name
}

output "pubsub_dlq_topic" {
  description = "Dead Letter Queue topic name"
  value       = module.pubsub.dlq_topic_name
}

output "firestore_database" {
  description = "Firestore database name"
  value       = module.firestore.database_name
}

output "project_id" {
  description = "GCP Project ID"
  value       = var.project_id
}

output "region" {
  description = "GCP Region"
  value       = var.region
}
