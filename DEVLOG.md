# 📓 Devlog — Konrad

Automatyczne dzienne podsumowania pracy z projektów.

---

## 📅 2026-02-27 — Dzienne podsumowanie (aktualizacja)

### ✅ Co zostało zrobione
- Wygenerowano kompletny szkielet platformy mikroserwisowej — 83 pliki, 3185 linii kodu produkcyjnego
- Zbudowano 5 niezależnych serwisów FastAPI z wzorcem Ports & Adapters (domena / infrastruktura / API)
- Zaimplementowano `ingestion_service`: upload plików (PDF/DOCX/TXT), walidacja, zapis do lokalnego storage, PostgreSQL repository, emisja zdarzenia `document.uploaded` do Redpanda
- Zaimplementowano `indexing_service`: konsument Redpanda, ekstrakcja tekstu (pypdf, python-docx), chunking token-aware (tiktoken, 512 tokenów z 64-tokenowym overlappem), generowanie embeddingów (Azure OpenAI), zapis do pgvector, idempotencja przez `processed_events`, emisja `document.indexed`
- Zaimplementowano `retrieval_service`: wyszukiwanie similarity search na pgvector (HNSW cosine), próg similarity konfigurowalny, zwrot `RetrievedChunk` z `similarity_score`
- Zaimplementowano `agent_service`: explicit state machine LangGraph (5 węzłów: guardrail_check → retrieval → synthesis → citation_verification → done/refused), structured JSON output z wymuszaniem cytowań, retry mechanism
- Zaimplementowano `guardrail_service`: detekcja prompt injection (12 wzorców regex), scoring 0.0–1.0, skanowanie PII, walidacja outputu (cytowania, pusty answer)
- Stworzono pakiet `shared/` z cross-service schemas (Pydantic), event schemas (BaseEvent + subtypes), structlog JSON config, BaseServiceSettings
- Skonfigurowano `docker-compose.yml` z health checks dla wszystkich serwisów, pgvector, Redpanda, Redpanda Console
- Stworzono `infra/docker/postgres/init.sql` z pgvector extension, indeksem HNSW, tabelami: `documents`, `document_chunks`, `audit_log`, `processed_events`, `agent_sessions`

### 🔧 Technologie / narzędzia użyte
- **FastAPI 0.115** — API framework dla wszystkich 5 serwisów
- **Pydantic v2** — walidacja danych, BaseSettings dla konfiguracji
- **structlog** — structured JSON logging z context binding (`correlation_id`, `tenant_id`)
- **aiokafka** — async Kafka/Redpanda producer i consumer
- **asyncpg + SQLAlchemy 2.x async** — async PostgreSQL driver
- **pgvector** — wektorowa baza embeddingów z indeksem HNSW (`m=16`, `ef_construction=64`)
- **LangGraph 0.2.45** — explicit state machine dla agent orchestration
- **OpenAI SDK (Azure)** — embeddingi i chat completions (GPT-4o)
- **tiktoken** — token-aware chunking
- **pypdf + python-docx** — ekstrakcja tekstu z PDF i DOCX
- **aiofiles** — async I/O dla plików
- **Docker Compose** — orchestracja lokalnego środowiska

### 🐛 Napotkane problemy i rozwiązania
- **`ingestion_service` miał `repository = None` jako placeholder** — dodano `PostgresDocumentRepository` z pełną implementacją INSERT + ON CONFLICT DO NOTHING
- **`indexing_service/main.py` nie zapisywał chunks do bazy** — dodano `PostgresChunkRepository.save_chunks_batch()` z batch insert i konwersją embedding do formatu pgvector `[v1,v2,...]::vector`
- **`indexing_service` nie emitował `document.indexed`** — dodano `RedpandaIndexingProducer` i podpięto do pipeline po zapisie chunks
- **`agent_service/main.py` miał zduplikowany endpoint `/query`** — wydzielono do `api/routes.py` i użyto `app.include_router(router)`
- **`git rebase --continue --no-edit`** — flaga nieobsługiwana; rozwiązano przez `GIT_EDITOR=true git rebase --continue`

### 📁 Zmienione pliki
- `docker-compose.yml` — 5 serwisów + postgres + redpanda + redpanda_console z health checks i volumes
- `infra/docker/postgres/init.sql` — pgvector, HNSW index, 5 tabel produkcyjnych
- `infra/docker/redpanda/console-config.yaml` — konfiguracja Redpanda Console
- `.env.example` — kompletny szablon konfiguracji środowiskowej
- `shared/` — 12 plików: events, schemas, logging, config
- `services/ingestion_service/` — 11 plików: domain (models, interfaces, services, exceptions), infrastructure (storage, repository, producer), api (routes, dependencies)
- `services/indexing_service/` — 10 plików: domain (models, services), infrastructure (consumer, embedding_client, producer, repository)
- `services/retrieval_service/` — 6 plików: domain (models, interfaces), infrastructure (pgvector_repo)
- `services/agent_service/` — 9 plików: domain (models), graph (state, nodes, builder), api (routes)
- `services/guardrail_service/` — 6 plików: domain (detector, models)
- `README.md` — pełna dokumentacja architektury z ASCII diagram, tabela serwisów, instrukcje uruchomienia

---

## 📅 2026-02-27 — Dzienne podsumowanie

### ✅ Co zostało zrobione
- Zainicjalizowano repozytorium Git i podpięto zdalne repozytorium GitHub (`deal-desk-copilot`)
- Skonfigurowano uwierzytelnianie GitHub przez lokalny `gh.exe` (GitHub CLI v2.87.3)
- Rozwiązano konflikty merge między lokalnym inicjalnym commitem a zdalnym repo GitHub
- Stworzono `README.md` z podstawowym opisem projektu oraz `.gitignore` obejmujący Node.js, Python, Next.js i środowisko lokalne
- Wygenerowano kompletny pakiet dokumentacji architektonicznej (5 dokumentów, łącznie 1702 linie)

### 🔧 Technologie / narzędzia użyte
- **Git** — inicjalizacja repo, zarządzanie konfliktami merge, rebase
- **GitHub CLI (`gh.exe`)** — uwierzytelnianie HTTPS, credential helper
- **Markdown** — dokumentacja architektoniczna
- **Python 3.11** — standardy opisane w dokumentacji (Pydantic v2, FastAPI, structlog, mypy)
- **FastAPI** — opisany jako framework API w dokumentacji architektury
- **PostgreSQL + pgvector** — warstwa embeddingów zdefiniowana w NFR i zasadach
- **Redpanda (Kafka-compatible)** — event bus opisany w zasadach architektonicznych
- **LangGraph** — orkiestracja agentów z explicit state machine
- **Azure OpenAI / AKS** — docelowe środowisko produkcyjne
- **Docker** — lokalne środowisko deweloperskie

### 🐛 Napotkane problemy i rozwiązania
- **`gh` nie rozpoznawane w terminalu** — GitHub CLI nie był zainstalowany globalnie; rozwiązano przez pobranie `gh.exe` i umieszczenie go w folderze projektu, następnie użycie jako `./gh.exe`
- **Push odrzucony przez GitHub** — zdalne repo miało własny inicjalny commit (README z GitHub UI); rozwiązano przez `git pull --allow-unrelated-histories` z rebase i ręczne rozwiązanie konfliktów w `README.md` i `.gitignore`
- **`git rebase --continue --no-edit` nieobsługiwane** — flaga `--no-edit` nie istnieje dla `rebase --continue`; rozwiązano przez `GIT_EDITOR=true git rebase --continue`

### 📁 Zmienione pliki
- `README.md` — opis projektu Deal Desk Copilot
- `.gitignore` — reguły ignorowania dla Python, Node.js, środowiska lokalnego, `gh.exe`
- `docs/ai_engineering_contract.md` — misja, zakres, filozofia inżynieryjna, granice systemu, definicja Done (207 linii)
- `docs/architecture_principles.md` — 10 zasad architektonicznych z uzasadnieniem i wpływem implementacyjnym (228 linii)
- `docs/non_functional_requirements.md` — mierzalne NFR: wydajność, skalowalność, niezawodność, bezpieczeństwo, audytowalność, kontrola kosztów (268 linii)
- `docs/coding_standards.md` — standardy Python 3.11, type hints, Pydantic v2, structlog, DI pattern, struktura folderów, testy (594 linie)
- `docs/governance_model.md` — decision traceability, cytowanie źródeł, detekcja prompt injection, GDPR compliance (405 linii)

---
