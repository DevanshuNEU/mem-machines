# Memory Machines Backend Assessment
## Robust Data Processing Pipeline

A scalable, fault-tolerant data ingestion pipeline built for the Memory Machines backend engineering assessment. This system handles high-throughput log ingestion with strict multi-tenant isolation.

![Architecture](docs/architecture.png)

---

## 🎯 Overview

This project implements a **Unified Ingestion Gateway** that:

- **Normalizes Data**: Accepts both JSON and raw text payloads, normalizing them into a consistent internal format
- **Ensures Isolation**: Strict multi-tenant data separation using Firestore subcollections  
- **Survives Chaos**: Handles 1000+ RPM with graceful crash recovery through idempotent processing

---

## 🏗️ Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│    Client    │     │  Ingest API  │     │   Pub/Sub    │     │    Worker    │
│  (JSON/TXT)  │────▶│  (Cloud Run) │────▶│   (Queue)    │────▶│  (Cloud Run) │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                            │                                          │
                            │ 202 Accepted                             │
                            │ (immediate)                              ▼
                                                               ┌──────────────┐
                                                               │  Firestore   │
                                                               │ (Multi-Tenant)│
                                                               └──────────────┘
```

### Components

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Ingest API** | Cloud Run + FastAPI | Validates, normalizes, and queues incoming data |
| **Message Broker** | Cloud Pub/Sub | Decouples ingestion from processing, handles bursts |
| **Worker** | Cloud Run + FastAPI | Processes messages, writes to Firestore |
| **Database** | Firestore | Multi-tenant storage with subcollection isolation |
| **Infrastructure** | Terraform | Infrastructure as Code for reproducibility |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Google Cloud SDK (`gcloud`)
- Terraform 1.0+
- Docker (optional, for local testing)

### Local Development

```bash
# Clone and setup
git clone <repo-url>
cd memory-machines-assessment

# Create virtual environment
make setup
source venv/bin/activate

# Run services locally
make run-api      # Terminal 1: Ingest API on :8080
make run-worker   # Terminal 2: Worker on :8081
```

### Deploy to GCP

```bash
# Set your project
export GCP_PROJECT_ID="your-project-id"
export GCP_REGION="us-central1"

# Deploy infrastructure
make deploy-infra

# Deploy services
make deploy-services
```

---

## 📡 API Reference

### POST /ingest

Ingests log data. Returns immediately with `202 Accepted`.

#### JSON Payload

```bash
curl -X POST https://YOUR_API_URL/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "acme_corp",
    "log_id": "log_12345",
    "text": "User 555-0199 accessed the system"
  }'
```

#### Raw Text Payload

```bash
curl -X POST https://YOUR_API_URL/ingest \
  -H "Content-Type: text/plain" \
  -H "X-Tenant-ID: acme_corp" \
  -d "User 555-0199 accessed the system at 2024-01-15"
```

#### Response

```json
{
  "status": "accepted",
  "log_id": "log_12345",
  "message": "Data queued for processing"
}
```

---

## 🗄️ Multi-Tenant Data Structure

Data is isolated per tenant using Firestore subcollections:

```
tenants/
├── acme_corp/
│   └── processed_logs/
│       ├── log_12345
│       │   ├── source: "json_upload"
│       │   ├── original_text: "User 555-0199..."
│       │   ├── modified_data: "User [REDACTED]..."
│       │   └── processed_at: "2024-01-15T10:00:00Z"
│       └── log_67890
│           └── ...
└── beta_inc/
    └── processed_logs/
        └── ...
```

---

## 🛡️ Fault Tolerance

### Crash Recovery

1. **Idempotent Processing**: Using `log_id` as Firestore document ID ensures re-processing produces identical results
2. **At-Least-Once Delivery**: Pub/Sub redelivers unacknowledged messages
3. **Dead Letter Queue**: Failed messages after 5 attempts are routed to DLQ for investigation

### High Availability

- Cloud Run auto-scales based on traffic
- Pub/Sub buffers messages during traffic spikes
- No single point of failure

---

## 🧪 Testing

```bash
# Run unit tests
make test

# Run with coverage
make test-cov

# Load test (1000 RPM)
python scripts/load_test.py --url YOUR_API_URL --rpm 1000
```

---

## 📁 Project Structure

```
memory-machines-assessment/
├── terraform/              # Infrastructure as Code
│   ├── modules/
│   │   ├── pubsub/        # Pub/Sub topic, subscription, DLQ
│   │   ├── cloud-run/     # Cloud Run service configuration
│   │   └── firestore/     # Firestore database setup
│   └── environments/
│       └── prod/          # Production configuration
├── services/
│   ├── ingest-api/        # Component A: Ingestion Gateway
│   └── worker/            # Component B: Processing Worker
├── scripts/               # Utility scripts
├── docs/                  # Documentation
└── .github/workflows/     # CI/CD pipelines
```

---

## 🔧 Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `GCP_PROJECT_ID` | Google Cloud project ID | Required |
| `GCP_REGION` | Deployment region | `us-central1` |
| `PUBSUB_TOPIC` | Pub/Sub topic name | `log-ingestion` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |

---

## 📊 Monitoring

- **Cloud Logging**: Structured logs from both services
- **Cloud Monitoring**: Request latency, error rates, throughput
- **Pub/Sub Metrics**: Queue depth, delivery latency

---

## 📝 License

MIT License - Built for Memory Machines assessment.

---

## 👤 Author

**Devanshu Chicholikar**  
MS Software Engineering, Northeastern University  
[LinkedIn](https://linkedin.com/in/devanshu-chicholikar) | [Portfolio](https://devanshu.dev)
