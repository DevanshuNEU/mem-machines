# Memory Machines Backend Assessment

A scalable, fault-tolerant data ingestion pipeline that handles high-throughput log ingestion with multi-tenant isolation.

## Live Deployment

| Service | URL |
|---------|-----|
| Ingest API | `https://ingest-api-774022449866.us-central1.run.app` |
| Worker | `https://worker-774022449866.us-central1.run.app` (internal) |
| Project | `memory-machines-479818` |
| Region | `us-central1` |

### Quick Test

```bash
# JSON payload
curl -X POST https://ingest-api-774022449866.us-central1.run.app/ingest \
  -H "Content-Type: application/json" \
  -d '{"tenant_id": "demo", "text": "Contact: 555-1234, email: test@example.com"}'

# Text payload  
curl -X POST https://ingest-api-774022449866.us-central1.run.app/ingest \
  -H "Content-Type: text/plain" \
  -H "X-Tenant-ID: demo" \
  -d "Raw log entry with phone 555-9876"
```

---

## Architecture

```
Client (JSON/TXT) --> Ingest API (Cloud Run) --> Pub/Sub --> Worker (Cloud Run) --> Firestore
                           |
                           | 202 Accepted (immediate)
```

**Components:**

- **Ingest API**: Validates and normalizes incoming data, publishes to Pub/Sub
- **Pub/Sub**: Message broker with dead letter queue for failed messages
- **Worker**: Processes messages, redacts PII, stores in Firestore
- **Firestore**: Multi-tenant storage using subcollections for isolation

---

## Key Features

**Non-blocking Ingestion**
- Returns 202 Accepted immediately
- Processing happens asynchronously via Pub/Sub

**Multi-tenant Isolation**
- Data stored in `tenants/{tenant_id}/processed_logs/{log_id}`
- Physical separation prevents cross-tenant data leaks

**PII Redaction**
- Phone numbers, emails, SSNs automatically redacted
- Original text preserved for audit, modified_data contains redacted version

**Fault Tolerance**
- Idempotent writes using log_id as document ID
- Pub/Sub redelivers on failure (5 retries before DLQ)
- Scale-to-zero with Cloud Run

---

## Load Test Results

```
Total Requests:     377
Successful (202):   377 (100.0%)
Failed:             0 (0.0%)

Latency:
  Average:  98ms
  p95:      132ms
  p99:      448ms
```

---

## Project Structure

```
├── services/
│   ├── ingest-api/     # Ingestion gateway
│   └── worker/         # Processing worker
├── terraform/          # Infrastructure as code
│   ├── modules/
│   │   ├── cloud-run/
│   │   ├── pubsub/
│   │   └── firestore/
│   └── environments/
│       └── prod/
├── scripts/
│   └── load_test.py    # Load testing script
└── Makefile            # Development commands
```

---

## Local Development

```bash
# Setup
make setup
source venv/bin/activate

# Run locally
make run-api      # Port 8080
make run-worker   # Port 8081

# Run tests
make test
```

---

## Deployment

Infrastructure is managed with Terraform:

```bash
cd terraform
terraform init
terraform plan -var-file=environments/prod/terraform.tfvars
terraform apply -var-file=environments/prod/terraform.tfvars
```

To deploy services:

```bash
# Ingest API
cd services/ingest-api
gcloud run deploy ingest-api --source . --region us-central1 --allow-unauthenticated

# Worker
cd services/worker
gcloud run deploy worker --source . --region us-central1 --no-allow-unauthenticated
```

---

## API Reference

### POST /ingest

**JSON Format:**
```json
{
  "tenant_id": "acme_corp",
  "text": "Log message here",
  "log_id": "optional_custom_id"
}
```

**Text Format:**
```
Content-Type: text/plain
X-Tenant-ID: acme_corp

Raw log text here
```

**Response (202 Accepted):**
```json
{
  "status": "accepted",
  "log_id": "log_abc123",
  "message": "Data queued for processing"
}
```

---

## Future Improvements

- CI/CD pipeline with Cloud Build triggers
- Remote Terraform state with GCS backend
- Custom monitoring dashboards
- Secrets Manager for sensitive config
- Per-tenant rate limiting

---

## Author

Devanshu Chicholikar  
MS Software Engineering, Northeastern University  
[LinkedIn](https://linkedin.com/in/devanshu-chicholikar) | [Portfolio](https://devanshu.dev)
