# Deal Desk Copilot

Production-grade, event-driven AI platform for enterprise contract analysis.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                        Client / API Gateway                       │
└───────────────────────────┬──────────────────────────────────────┘
                            │ HTTP (FastAPI)
        ┌───────────────────┼──────────────────────┐
        │                   │                       │
        ▼                   ▼                       ▼
┌──────────────┐   ┌──────────────────┐   ┌──────────────────┐
│  Ingestion   │   │  Agent Service   │   │ Guardrail Service │
│  Service     │   │  (LangGraph FSM) │   │ (Injection / PII) │
│  :8001       │   │  :8004           │   │ :8005             │
└──────┬───────┘   └────────┬─────────┘   └──────────────────┘
       │ document.uploaded   │ HTTP /retrieve
       ▼                     ▼
┌──────────────┐   ┌──────────────────┐
│  Indexing    │   │ Retrieval Service │
│  Service     │   │ (pgvector ANN)    │
│  :8002       │   │ :8003             │
└──────┬───────┘   └────────┬─────────┘
       │                    │
       └────────┬───────────┘
                ▼
     ┌──────────────────────┐
     │  PostgreSQL + pgvector│
     │  (documents + chunks  │
     │   + embeddings)       │
     └──────────────────────┘

Event Bus: Redpanda (Kafka-compatible)
Topics: document.uploaded · document.indexed · query.requested · query.completed
```

## Services

| Service | Port | Responsibility |
|---|---|---|
| `ingestion_service` | 8001 | Accept file uploads, validate, store, emit `document.uploaded` |
| `indexing_service` | 8002 | Consume events, chunk text, generate embeddings, store in pgvector |
| `retrieval_service` | 8003 | Semantic similarity search via pgvector HNSW index |
| `agent_service` | 8004 | LangGraph state machine: guardrail → retrieve → synthesize → verify |
| `guardrail_service` | 8005 | Prompt injection detection, PII scanning, citation enforcement |
| `postgres` | 5432 | PostgreSQL 16 + pgvector extension |
| `redpanda` | 19092 | Kafka-compatible event broker |
| `redpanda_console` | 8080 | Redpanda web UI |

## Stack

- **Runtime:** Python 3.11
- **API Framework:** FastAPI + Uvicorn
- **Event Bus:** Redpanda (Kafka-compatible), client: aiokafka
- **Vector Storage:** PostgreSQL 16 + pgvector (HNSW index)
- **ORM:** SQLAlchemy 2.x async + asyncpg
- **Agent Orchestration:** LangGraph (explicit state machine)
- **LLM Provider:** Azure OpenAI (GPT-4o + text-embedding-ada-002)
- **Validation:** Pydantic v2
- **Logging:** structlog (JSON structured output)
- **Configuration:** pydantic-settings (env vars only, no hardcoded values)
- **Containerization:** Docker + docker-compose

## Local Development

### Prerequisites

- Docker Desktop
- Docker Compose v2

### Setup

```bash
# 1. Clone repository
git clone https://github.com/privatekonradbaczek-design/deal-desk-copilot.git
cd deal-desk-copilot

# 2. Configure environment
cp .env.example .env
# Edit .env — fill in Azure OpenAI credentials

# 3. Start all services
docker compose up --build

# 4. Verify services
curl http://localhost:8001/health  # ingestion
curl http://localhost:8002/health  # indexing
curl http://localhost:8003/health  # retrieval
curl http://localhost:8004/health  # agent
curl http://localhost:8005/health  # guardrail
```

### Upload a document

```bash
curl -X POST http://localhost:8001/documents \
  -F "file=@contract.pdf" \
  -F "tenant_id=tenant_001" \
  -F "uploaded_by=user_001"
```

### Query a contract

```bash
curl -X POST http://localhost:8004/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "When does this contract expire?",
    "tenant_id": "tenant_001",
    "user_id": "user_001"
  }'
```

### Validate input (guardrail)

```bash
curl -X POST http://localhost:8005/validate/input \
  -H "Content-Type: application/json" \
  -d '{"text": "What are the payment terms?", "tenant_id": "tenant_001"}'
```

## Project Structure

```
deal-desk-copilot/
├── services/
│   ├── ingestion_service/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── src/ingestion_service/
│   │       ├── domain/          # models, interfaces, services, exceptions
│   │       ├── infrastructure/  # storage adapter, event producer
│   │       └── api/             # FastAPI routes, dependencies
│   ├── indexing_service/        # Event consumer + chunking + embedding
│   ├── retrieval_service/       # pgvector similarity search
│   ├── agent_service/
│   │   └── src/agent_service/
│   │       ├── domain/          # QueryRequest, QueryResponse
│   │       ├── graph/           # LangGraph state, nodes, builder
│   │       └── api/
│   └── guardrail_service/       # Injection detection, PII, citation check
├── shared/
│   ├── schemas/                 # Cross-service Pydantic models
│   ├── events/                  # Event schemas (BaseEvent + subtypes)
│   ├── logging/                 # structlog configuration
│   └── config/                  # BaseServiceSettings
├── infra/
│   └── docker/
│       ├── postgres/init.sql    # pgvector extension + schema
│       └── redpanda/            # Broker configuration
├── docs/                        # Architecture documentation
│   └── adr/                     # Architecture Decision Records
├── docker-compose.yml
├── .env.example
└── README.md
```

## Architecture Decisions

All architectural decisions are documented in `/docs/`. Key documents:

- [AI Engineering Contract](docs/ai_engineering_contract.md)
- [Architecture Principles](docs/architecture_principles.md)
- [Non-Functional Requirements](docs/non_functional_requirements.md)
- [Coding Standards](docs/coding_standards.md)
- [Governance Model](docs/governance_model.md)

## Agent State Machine

The `agent_service` implements an explicit LangGraph state machine:

```
START → guardrail_check → retrieval → synthesis → citation_verification → END
                ↓ (failed)      ↓ (no context)          ↓ (failed, retry)
              refused         refused                  synthesis (retry)
                                                            ↓ (max retries)
                                                          refused → END
```

Each state transition is logged with `correlation_id` and `session_id`.

## Future: Azure Deployment (AKS)

Infrastructure manifests will be located in `infra/k8s/`. Target architecture:

- AKS cluster with HPA per service
- Azure OpenAI (Managed Identity authentication)
- Azure Blob Storage (replace `LocalFileStorage` adapter)
- Azure Key Vault for secrets
- Azure Monitor + Application Insights for observability
- Confluent Cloud or Azure Event Hubs (Kafka-compatible) as Redpanda replacement
