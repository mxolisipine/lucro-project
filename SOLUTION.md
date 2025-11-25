## **Fintech Transaction Ingestion & Async Enrichment Pipeline**

### *Technical Lead – Lucro*

This document describes the architecture, design decisions, trade-offs, operational considerations, and production deployment strategy for the Django + Celery–based fintech ingestion system.

---

# **1. High-Level Architecture**

```
               ┌────────────────────────┐
               │ External Integrations   │
               │ (Banking APIs)          │
               └──────────┬─────────────┘
                          │ JSON batch ingestion
                          ▼
                ┌────────────────────────┐
                │ Django REST API         │
                │ /api/integrations/...   │
                └──────────┬─────────────┘
                          │
                          │ Persist batch + TX records
                          ▼
                ┌────────────────────────┐
                │ PostgreSQL              │
                │ Accounts / Batches / TX │
                └──────────┬─────────────┘
                          │
                          │ Dispatch Celery job
                          ▼
                ┌────────────────────────┐
                │ Celery Worker Pool      │
                │ (Redis broker)          │
                └──────────┬─────────────┘
                          │ Enrichment
                          ▼
                ┌────────────────────────┐
                │ Categorization Engine   │
                └────────────────────────┘

 BI / Reporting:
 GET /api/reports/account/... → Aggregation queries in PostgreSQL
```

Key characteristics:

* **Fully asynchronous pipeline**
* **Transaction-safe ingestion**
* **Row-level locking** during Celery processing
* **Pluggable categorizer** (LLM-ready)
* **Deterministic behavior** for financial correctness
* **Horizontally scalable** Celery workers

---

# **2. Design Goals & Principles**

### ✔ Reliability

Atomic ingestion, idempotency through transaction IDs, row-level locks for concurrency safety.

### ✔ Scalability

Workers scale horizontally; `select_for_update(skip_locked=True)` prevents contention.

### ✔ Maintainability

Modular code: `ingestion`, `categorization`, `reports`.

### ✔ Observability

Structured logging, ingestion status tracking, metrics-friendly DB indexes.

### ✔ Future AI Integration

Rule-based categorizer → easily swappable for an LLM service without refactoring workers.

---

# **3. Data Modeling**

### **Account**

Represents financial accounts from external APIs.
Indexed by account_id.

### **Batch**

Each ingestion request creates a batch with a UUID.
Allows grouping + independent processing.

### **Transaction**

Contains raw transaction data + enrichment fields:

* category
* ingestion status (pending → processing → completed/failed)
* timestamps
* FK to both `Batch` and `Account`

### **Indexing Decisions**

* `(account, date)` → improves reporting queries
* `ingestion_status` → fast worker filtering

This structure optimizes read-heavy BI workloads and write-heavy ingestion.

---

# **4. Ingestion Pipeline (Task 1)**

### **Endpoint:**

`POST /api/integrations/transactions/`

### **Flow:**

1. Validate incoming payload via DRF serializer
2. Begin DB transaction (`atomic()`)
3. Create or reuse `Account`
4. Create `Batch`
5. Bulk-insert `Transactions` with `ingestion_status = pending`
6. Dispatch Celery task for batch enrichment
7. Return `202 Accepted` with `batch_id`

### **Trade-offs:**

#### **Why 202 instead of 201?**

Because ingestion is *asynchronous*, and processing may take time.

#### **Why batch-level atomicity?**

To prevent partial ingestion:

* If 5/15 transactions fail validation → none are inserted.

#### **Why bulk_create?**

* Dramatic performance boost (15–20× faster)
* Prevents per-row overhead

---

# **5. Async Processing Pipeline (Task 2)**

### **Celery Task:** `process_batch_enrichment(batch_id)`

### **Key Logic**

* Lock rows using:

```python
batch.transactions.select_for_update(skip_locked=True)
```

This ensures:

* multiple workers can process the same batch
* no row is double-processed
* no deadlocks

### **Processing Steps**

1. Mark TX as `processing`
2. Simulate latency (0.5–1s)
3. Categorize using `RuleBasedCategorizer`
4. Save category
5. Update status → `completed`
6. On error: mark `failed`

### **Why row-level locks?**

Because financial ingestion must be **exactly-once** or **effectively-once**, even under multi-worker parallelism.

### **Categorization Engine**

A clean, pluggable class:

```python
class RuleBasedCategorizer:
    def categorize(self, merchant_name, description):
        ...
```

This allows future swapping with:

* OpenAI function call
* in-house ML model
* fine-tuned classifier

without touching worker code.

---

# **6. BI Summary Endpoint (Task 3)**

### **Endpoint:**

`GET /api/reports/account/{account_id}/summary?start_date&end_date`

### **Aggregations:**

* Total transactions
* Total spend (negative amounts)
* Total income (positive amounts)
* Net value
* Top 3 spend categories
* Ingestion status breakdown

### **Implementation**

Single optimized PostgreSQL query using:

* `annotate`
* `Sum`
* `Case`/`When`
* `Count`
* date filters
* category grouping with ordering

### **Why compute in the database?**

* Faster
* Uses DB indexes
* Avoids transferring thousands of transactions to Python

---

# **7. Simulation Command (Task 4)**

Command:

```bash
python manage.py simulate_integration
```

Generates 10–15 realistic transactions and simulates an external integration.

Flow:

1. Build JSON payload
2. POST to ingestion endpoint
3. Print batch_id
4. Poll worker status to show progress

This provides an end-to-end smoke test.

---

# **8. Testing Approach (Task 4)**

I included **the two highest-value tests**:

### **Test 1 — Ingestion Atomicity**

Ensures:

* invalid transaction → entire batch rejected
* no partial insertion
* no orphaned accounts/batches

Why important:
Prevents financial inconsistencies and improves data integrity.

### **Test 2 — Worker Enrichment Correctness**

Asserts:

* worker marks status correctly
* category assigned
* status transitions (pending → processing → completed)
* no duplicate processing

Why important:
This ensures the core business logic is reliable.

---

# **9. Docker Deployment Strategy**

### **docker-compose services**

* **PostgreSQL 14**
* **Redis** (Celery broker)
* **Django API (Gunicorn)**
* **Celery Worker**
* **Celery Beat** (I would use it if there are scheduled tasks to be added in future)

### **Volumes**

Persistent Docker volume for Postgres.

### **Networking**

All services on internal Docker network.

---

# **10. Production Deployment Strategy**

### **A. Infrastructure**

* Deploy using **AWS ECS** or **EKS**
* Use **AWS RDS Postgres**
* Use **AWS ElastiCache Redis**

### **B. Scaling**

#### **Django API**

Scale on:

* requests/second
* response latency

#### **Celery Workers**

Scale on:

* number of pending tasks
* time-to-process per transaction

Horizontal scaling is automatic due to the use of:

* Redis as broker
* Row-level locks
* Skip-locked processing

Workers can safely run in parallel and handle the same batch.

---

# **11. Observability & Logging**

### **Metrics**

* Transaction ingestion count
* Pending vs processing vs completed metrics
* Worker throughput per minute
* Category distribution

### **Logging**

Structured logs with:

* batch_id
* transaction_id
* ingestion status
* error details

### **Tracing**

If using OTEL:

* trace ingestion → database → celery → DB writeback

### **Dashboards**

Grafana dashboards:

* ingestion latency
* worker success rates
* API throughput

---

# **12. Security Considerations**

### **Transport**

* HTTPS for all API endpoints

### **Database**

* Enforce least-privilege Postgres roles
* Disable public schema write access

### **API**

* Validate all external inputs
* Enforce schema correctness with DRF
* Reject invalid currencies, dates, IDs

### **Secrets**

* Use environment variables
* Use AWS Secrets Manager or Vault in production

---

# **13. AI Integration Points (Future Roadmap)**

The categorizer class is intentionally abstracted:

```python
class BaseCategorizer:
    def categorize(self, merchant_name, description):
        raise NotImplementedError
```

Future integrations:

* LLM classification
* Embedding-based similarity search
* RAG over historical categories
* Fine-tuned transformer model

No architectural changes required.

---

# **14. Key Trade-offs**

### ✔ Used rule-based categorization instead of ML

Complies with assignment constraints; easier to test; deterministic.

### ✔ Chose row-level locking

Safer than optimistic concurrency for financial systems.

### ✔ Used one batch per ingestion request

Keeps contracts simple; easier to restart processing.

### ✔ Chose UUID for batch_id

Globally unique, safe to pass between services.

