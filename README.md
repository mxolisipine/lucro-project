# 🏦 Fintech Transaction Ingestion & Async Enrichment Pipeline

### **Lucro – Technical Lead Assignment**

This project implements a **production-ready backend system** for ingesting banking transactions, processing them asynchronously via Celery, and exposing BI summary metrics through REST APIs.

It is built according to the requirements described in the provided assignment:
📄 *Lucro – Team Lead / Senior Developer Assignment.pdf*

---

# 🚀 **Tech Stack**

| Component         | Technology                               |
| ----------------- | ---------------------------------------- |
| Backend Framework | **Python 3.11**, **Django 4.2**, **DRF** |
| Database          | **PostgreSQL 14+**                       |
| Message Broker    | **Redis**                                |
| Async Processing  | **Celery 5.x**                           |
| Containerization  | **Docker + docker-compose**              |
| Testing           | Django Test Framework                    |

---

# 📦 **Features Implemented**

### ✅ **Task 1 — Transaction Ingestion API**

* `POST /api/integrations/transactions/`
* Validates and ingests transaction batches
* Creates accounts if missing
* Persists transactions atomically
* Returns `202 Accepted` + `batch_id`
* Batch records stored with UUIDs
* All transactions begin in `pending` status

---

### ✅ **Task 2 — Celery Async Enrichment**

* Background worker triggered after ingestion
* Row-level concurrency with `select_for_update(skip_locked=True)`
* Deterministic rule-based categorizer
* Simulated latency (0.5–1.0s)
* Updates `processing → completed/failed`
* Safe parallel execution across workers

---

### ✅ **Task 3 — BI Summary Reporting API**

`GET /api/reports/account/{account_id}/summary?start_date&end_date`

Returns:

* Total transactions
* Total spend / income
* Net total
* Top 3 categories by spend
* Processing status breakdown

Uses optimized PostgreSQL aggregations.

---

### ✅ **Task 4 — Simulation, Testing, Documentation**

* Management command:

  ```bash
  python manage.py simulate_integration
  ```

  Generates random account + transactions and ingests them
* Two high-value tests:

  1. Ingestion atomicity
  2. Worker enrichment correctness
* Full documentation in `SOLUTION.md`

---

# 🐳 **Running the Project with Docker**

### **1. Clone the Repo**

```bash
git clone git@github.com:mxolisipine/lucro-project.git
cd lucro-project
```

### **2. Start All Services**

```bash
docker-compose up --build
```

This will start:

* Django API (port **8000**)
* Celery worker
* Redis
* PostgreSQL

---

# 🧪 **Running Tests**

```bash
docker-compose exec web python manage.py test
```

---

# 🧩 **API Endpoints**

## **1. Ingestion Endpoint**

### `POST /api/integrations/transactions/`

**Payload example:**

```json
{
  "accounts": [{ ... }],
  "transactions": [{ ... }],
  "total_transactions": 2,
  "request_id": "req_abc123"
}
```

**Response:**

```json
{
  "batch_id": "550e8400-e29b-41d4-a716-446655440000",
  "total_transactions": 2
}
```

---

## **2. BI Summary Endpoint**

### `GET /api/reports/account/{account_id}/summary?...`

**Example:**

```
/api/reports/account/acc_12345/summary?start_date=2025-10-01&end_date=2025-10-31
```

---

## **3. Health Check**

`GET /api/health/` → `{
    "status": "ok",
    "database": "ok",
    "redis": "ok"
}`

# 🛠 **Project Structure**

```
lucro_project/
├── README.md
├── SOLUTION.md
├── requirements.txt
├── docker-compose.yml
├── Dockerfile
├── .gitignore
│
├── project/
│   ├── __init__.py
│   ├── celery.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
│
├── middleware/
│   ├── __init__.py
│   └── observability.py
│
├── transactions/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── tests.py
│   ├── views.py
│   ├── serializers.py
│   ├── tasks.py
│   ├── categorizer.py
│   ├── management/
│   │   ├── __init__.py
│   │   └── commands/
│   │       ├── __init__.py
│   │       └── simulate_integration.py
│   └── urls.py
```

---

# 🔍 **Observability**

* We’ve implemented end-to-end observability across both API endpoints and background tasks. 
* Every request gets a correlation ID, logged with metadata like path, method, client IP, status, and duration. 
* Celery tasks inherit this ID, logging their start, progress, retries, and completion. 
* This lets us trace a request through the system, quickly spot failures, and understand performance across both endpoints and async processing.

---

# 🔐 **Security Considerations**

* Input validation on all ingestion fields
* HTTPS termination recommended in production
* Secrets loaded via environment variables
* PostgreSQL least-privilege role
* Safe async processing with transactional boundaries

---

# 🤖 **AI Integration Ready (Future)**

The categorizer is implemented as a pluggable class:

```python
class BaseCategorizer:
    def categorize(...):
        raise NotImplementedError
```

Can be replaced with:

* LLM classification
* Embeddings + vector search
* Fine-tuned model

No architecture changes needed.

---
