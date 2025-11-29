# =============================================================================
# Pub/Sub Module - Outputs
# =============================================================================

output "topic_name" {
  description = "Main topic name"
  value       = google_pubsub_topic.main.name
}

output "topic_id" {
  description = "Main topic ID"
  value       = google_pubsub_topic.main.id
}

output "subscription_name" {
  description = "Worker push subscription name"
  value       = google_pubsub_subscription.worker_push.name
}

output "dlq_topic_name" {
  description = "Dead letter queue topic name"
  value       = google_pubsub_topic.dlq.name
}

output "dlq_subscription_name" {
  description = "Dead letter queue subscription name"
  value       = google_pubsub_subscription.dlq.name
}
