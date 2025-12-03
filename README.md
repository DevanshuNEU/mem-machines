# Memory Machines Backend Assessment

A scalable, fault-tolerant data ingestion pipeline built on Google Cloud Platform. Handles 1000+ RPM with strict multi-tenant isolation, automatic PII redaction, and crash recovery.

## Live Deployment

| Service | URL |
|---------|-----|
| Ingest API | `https://ingest-api-774022449866.us-central1.run.app` |
| Worker | `https://worker-774022449866.us-central1.run.app` (internal only) |
| Project | `memory-machines-479818` |
| Region | `us-central1` |

### Quick Test

```bash
# JSON payload
curl -X POST https://ingest-api-774022449866.us-central1.run.app/ingest \
  -H "Content-Type: application/json" \
  -d '{"tenant_id": "demo", "text": "Call 555-1234, email test@example.com, SSN 123-45-6789"}'

# Text payload
curl -X POST https://ingest-api-774022449866.us-central1.run.app/ingest \
  -H "Content-Type: text/plain" \
  -H "X-Tenant-ID: demo" \
  -d "Raw log with phone 555-9876"
```

---

## Architecture

```
                                    +------------------+
                                    |                  |
    JSON Payload ------------------>|                  |
    {                               |                  |        +------------+
      "tenant_id": "acme",          |   Ingest API     |        |            |
      "text": "..."                 |   (Cloud Run)    |------->|  Pub/Sub   |
    }                               |                  |        |   Topic    |
                                    |   - Validates    |        |            |
    Text Payload ------------------>|   - Normalizes   |        +-----+------+
    Content-Type: text/plain        |   - Returns 202  |              |
    X-Tenant-ID: acme               |                  |              |
    Body: "raw text"                +------------------+              |
                                                                      | Push
                                                                      v
    +------------------+        +------------------+        +------------------+
    |                  |        |                  |        |                  |
    |    Firestore     |<-------|     Worker       |<-------|   Pub/Sub        |
    |                  |        |   (Cloud Run)    |        |   Subscription   |
    |  tenants/        |        |                  |        |                  |
    |    {tenant_id}/  |        |   - Processes    |        |   - Push to      |
    |      processed_  |        |   - Redacts PII  |        |     Worker URL   |
    |        logs/     |        |   - Writes to DB |        |   - 5 retries    |
    |          {log}   |        |                  |        |   - DLQ on fail  |
    |                  |        +------------------+        +------------------+
    +------------------+
```

Excalidraw

<img width="3095" height="943" alt="image" src="https://github.com/user-attachments/assets/01b087d0-685f-41b7-a654-8be6a19d541b" />


Both JSON and Text payloads are normalized into a single internal message format before being published to Pub/Sub. The Worker processes all messages identically regardless of original format.

---

## Multi-Tenant Architecture

Data is stored using the Firestore subcollection pattern:

```
tenants/
├── acme_corp/
│   └── processed_logs/
│       ├── log_abc123
│       └── log_def456
├── beta_inc/
│   └── processed_logs/
│       └── log_xyz789
```

**Why subcollections over a shared table with tenant_id column?**

With subcollections, isolation is structural. The query path requires the tenant_id: `tenants/{tenant_id}/processed_logs`. It is physically impossible to accidentally query across tenants. This is not a WHERE clause that a developer might forget - isolation is enforced by the data model itself.

---

## Crash Simulation / Recovery

**Problem:** What happens if the Worker crashes after processing but before saving to Firestore?

Pub/Sub does not receive an acknowledgement, so it redelivers the message. The Worker processes it again. Without safeguards, this creates duplicate records.

**Solution:** Idempotent writes using log_id as document ID.

```python
# services/worker/src/services/firestore.py

doc_ref = (
    client.collection("tenants")
    .document(tenant_id)
    .collection("processed_logs")
    .document(log_id)  # <-- log_id as document ID
)
doc_ref.set(data)  # Creates OR overwrites
```

If the same message is processed twice, the second write overwrites the first with identical data. Result: exactly one document, no duplicates, no data loss.

Additionally, a Dead Letter Queue (DLQ) captures messages that fail after 5 delivery attempts, preventing poison messages from blocking the pipeline.

---

## PII Redaction

The Worker automatically redacts sensitive information before storing:

| Type | Pattern | Example |
|------|---------|---------|
| Phone (10-digit) | `\d{3}[-.]?\d{3}[-.]?\d{4}` | 555-123-4567 |
| Phone (7-digit) | `\d{3}[-.]?\d{4}` | 555-1234 |
| Email | Standard email pattern | user@example.com |
| SSN | `\d{3}-\d{2}-\d{4}` | 123-45-6789 |

Both original and redacted text are stored:
- `original_text`: Preserved for audit purposes
- `modified_data`: PII replaced with `[REDACTED]`

---

## Load Test Results

Tested at 1000 RPM with mixed JSON and Text payloads:

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
│   ├── ingest-api/          # Public ingestion endpoint
│   │   └── src/
│   │       ├── api/         # Route handlers
│   │       ├── models/      # Pydantic schemas
│   │       └── services/    # Pub/Sub publisher
│   └── worker/              # Internal processor
│       └── src/
│           ├── api/         # Pub/Sub push handler
│           ├── models/      # Schemas + PII redaction
│           └── services/    # Firestore client
├── terraform/               # Infrastructure as Code
│   ├── modules/
│   │   ├── cloud-run/       # Cloud Run services
│   │   ├── pubsub/          # Topics, subscriptions, DLQ
│   │   └── firestore/       # Database setup
│   └── environments/
│       └── prod/            # Production config
├── scripts/
│   └── load_test.py         # Load testing script
└── Makefile                 # Development commands
```

---

## Deployment

### Infrastructure (Terraform)

```bash
cd terraform
terraform init
terraform plan -var-file=environments/prod/terraform.tfvars
terraform apply -var-file=environments/prod/terraform.tfvars
```

### Services (Cloud Run)

```bash
# Ingest API (public)
cd services/ingest-api
gcloud run deploy ingest-api --source . --region us-central1 --allow-unauthenticated

# Worker (internal)
cd services/worker
gcloud run deploy worker --source . --region us-central1 --no-allow-unauthenticated
```

---

## API Reference

### POST /ingest

Accepts JSON or Text payloads. Returns immediately with 202 Accepted.

**JSON:**
```bash
curl -X POST https://ingest-api-774022449866.us-central1.run.app/ingest \
  -H "Content-Type: application/json" \
  -d '{"tenant_id": "acme", "text": "Log message", "log_id": "optional_id"}'
```

**Text:**
```bash
curl -X POST https://ingest-api-774022449866.us-central1.run.app/ingest \
  -H "Content-Type: text/plain" \
  -H "X-Tenant-ID: acme" \
  -d "Raw log text here"
```

**Response:**
```json
{
  "status": "accepted",
  "log_id": "log_abc123",
  "message": "Data queued for processing"
}
```

---

## Author

Devanshu Chicholikar
MS Software Engineering, Northeastern University
