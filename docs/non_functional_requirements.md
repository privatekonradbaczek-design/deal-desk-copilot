# /docs/non_functional_requirements.md

**Klasyfikacja:** Wewnętrzna — Technical Leadership / Security Review Board
**Wersja:** 1.0.0
**Status:** Obowiązujący
**Ostatnia aktualizacja:** 2026-02-27

---

## Wprowadzenie

Niniejszy dokument definiuje mierzalne wymagania niefunkcjonalne platformy Deal Desk Copilot. Każde wymaganie posiada wartość liczbową, metodę pomiaru i warunki alertowania. Wymagania bez mierzalnych kryteriów akceptacji nie są traktowane jako wymagania — są traktowane jako życzenia.

---

## 1. Wydajność

### 1.1 Q&A Pipeline — Latencja end-to-end

| Percentyl | Cel | Warunek alertu |
|---|---|---|
| p50 | ≤ 2 000 ms | — |
| p95 | ≤ 5 000 ms | > 5 000 ms przez > 5 min |
| p99 | ≤ 10 000 ms | > 10 000 ms przez > 2 min |
| Max (hard limit) | 30 000 ms | Natychmiastowy alert |

Pomiar: od momentu odebrania żądania przez API Gateway do momentu zwrócenia pełnej odpowiedzi z cytatami. Implementacja: histogram Prometheus `query_duration_seconds` z labelami `{operation, model, tenant}`.

### 1.2 Latencja retrieval (pgvector similarity search)

| Percentyl | Cel | Warunek alertu |
|---|---|---|
| p95 | ≤ 300 ms | > 300 ms przez > 5 min |
| p99 | ≤ 600 ms | > 600 ms przez > 2 min |

Dotyczy: zapytań do pgvector po uprzednim wygenerowaniu embeddingu zapytania. Nie obejmuje czasu generowania embeddingu.

Wymagania indeksowania pgvector:
- Typ indeksu: `HNSW` z parametrami `m=16`, `ef_construction=64`.
- Wymiarowość embeddingów: 1536 (text-embedding-ada-002) lub 3072 (text-embedding-3-large).
- Partycjonowanie tabeli `embeddings` po `tenant_id` dla izolacji i performance.

### 1.3 Przepustowość indeksowania dokumentów

| Metryka | Cel |
|---|---|
| Throughput (pojedyncza instancja) | ≥ 10 dokumentów/minutę (dokument ≤ 50 stron) |
| Throughput (3 instancje równoległe) | ≥ 25 dokumentów/minutę |
| Czas indeksowania dokumentu 100-stronicowego | ≤ 120 s end-to-end |
| Max rozmiar dokumentu | 50 MB (binarny), 500 stron |

Pomiar: metryki Prometheus `document_indexing_duration_seconds` i `documents_indexed_total`.

### 1.4 Latencja generowania embeddingów

| Operacja | Cel p95 |
|---|---|
| Pojedynczy chunk (≤ 512 tokenów) | ≤ 500 ms (z uwzględnieniem API call) |
| Batch 100 chunks | ≤ 5 000 ms |

Cache hit rate embeddingów: cel ≥ 60% dla dokumentów z powtarzającymi się fragmentami (np. standardowe klauzule).

---

## 2. Skalowalność

### 2.1 Model skalowania horyzontalnego

Każdy serwis jest skalowalny niezależnie. Poniżej docelowe limity dla deployment na AKS:

| Serwis | Min repliki | Max repliki | Metryka skalowania |
|---|---|---|---|
| API Gateway | 2 | 10 | CPU > 70%, req/s > 100 |
| Document Processor | 1 | 8 | Redpanda consumer lag > 50 |
| Query Service | 2 | 12 | CPU > 60%, req/s > 50 |
| Agent Orchestrator | 1 | 6 | Redpanda consumer lag > 20 |
| Audit Service | 2 | 4 | Redpanda consumer lag > 200 |

### 2.2 Partycjonowanie zdarzeń Redpanda

| Topic | Liczba partycji | Klucz partycji | Uzasadnienie |
|---|---|---|---|
| `document.upload` | 12 | `tenant_id` | Izolacja obciążenia per tenant |
| `document.indexed` | 12 | `tenant_id` | Downstream consumption per tenant |
| `query.requested` | 24 | `user_id` | Równoległość zapytań |
| `agent.task` | 12 | `session_id` | Zachowanie kolejności w sesji |
| `audit.event` | 6 | `correlation_id` | Ordered audit trail |

Replication factor: 3 dla wszystkich topiców w produkcji. Retention: 7 dni dla topiców operacyjnych, 90 dni dla `audit.event`.

### 2.3 Limity pojemności

| Zasób | Cel | Limit twardy |
|---|---|---|
| Dokumenty per tenant | 10 000 | 100 000 |
| Chunks per dokument | 2 000 | 10 000 |
| Równoległe sesje Q&A | 100 | 500 |
| Rozmiar bazy embeddingów | 100 GB | 1 TB (pgvector) |

---

## 3. Niezawodność

### 3.1 SLO (Service Level Objectives)

| Metryka | Cel | Okno pomiaru |
|---|---|---|
| Availability (API Gateway) | ≥ 99.5% | 30 dni |
| Availability (Query Service) | ≥ 99.0% | 30 dni |
| Error rate (5xx) | ≤ 0.5% | 1 godzina |
| Document indexing success rate | ≥ 99.0% | 24 godziny |

### 3.2 Strategia retry

Wszystkie wywołania zewnętrznych API (Azure OpenAI, Azure Blob Storage) oraz operacje bazy danych stosują exponential backoff z jitter:

```
delay = min(base_delay * 2^attempt + jitter, max_delay)
base_delay = 1s
max_delay = 60s
jitter = random(0, base_delay)
max_attempts = 5
```

Wywołania LLM (Azure OpenAI):
- Retry wyłącznie dla kodów: 429 (rate limit), 503 (service unavailable), 500 (server error).
- Brak retry dla: 400 (bad request), 401 (unauthorized), 422 (unprocessable).
- Circuit breaker: po 5 consecutive failures w ciągu 60s — stan `OPEN` przez 120s.

Operacje Redpanda:
- Producer: `acks=all`, `retries=10`, `delivery.timeout.ms=120000`.
- Consumer: manual offset commit po potwierdzeniu przetworzenia.

### 3.3 Izolacja błędów

- **Bulkhead pattern:** każdy serwis posiada osobne pule połączeń do bazy danych i brokera zdarzeń.
- **Circuit breaker (per downstream):** izolacja awarii Azure OpenAI nie wpływa na retrieval i obsługę cache hitów.
- **Dead Letter Queue:** zdarzenia, których przetworzenie zakończyło się błędem po wyczerpaniu retries, trafiają do DLQ `{topic}.dlq`. Alert Prometheus po pierwszym zdarzeniu w DLQ.
- **Graceful degradation:** Query Service w przypadku niedostępności LLM zwraca wyniki retrieval bez syntezy — czyste cytaty z dokumentów bez generowanej odpowiedzi.
- **Timeout hierarchy:** każda operacja posiada jawny timeout: HTTP request (30s), LLM call (25s), DB query (10s), embedding call (15s).

---

## 4. Bezpieczeństwo

### 4.1 Uwierzytelnianie i autoryzacja — JWT

- Standard: JWT (JSON Web Token), podpis RS256 (asymetryczny klucz RSA-2048).
- Issuer: Azure AD B2C lub dedykowany Identity Provider.
- Czas życia tokenu dostępu: 15 minut.
- Refresh token: 8 godzin, single-use, rotacja przy każdym użyciu.
- Wymagane claims: `sub` (user ID), `tenant_id`, `roles`, `iat`, `exp`, `jti` (unique token ID).
- Weryfikacja na poziomie API Gateway — serwisy downstream nie weryfikują JWT ponownie, ufają nagłówkowi `X-Authenticated-User` przekazanemu przez gateway.

### 4.2 RBAC (Role-Based Access Control)

| Rola | Uprawnienia |
|---|---|
| `viewer` | Odczyt wyników Q&A, przeglądanie dokumentów własnego tenanta |
| `analyst` | `viewer` + upload dokumentów, inicjowanie analiz |
| `admin` | `analyst` + zarządzanie użytkownikami tenanta, konfiguracja progów |
| `platform_admin` | Pełny dostęp, zarządzanie tenantami (wyłącznie dla operatorów platformy) |

- Weryfikacja RBAC na poziomie każdego endpointu FastAPI przez dekorator `@require_role(...)`.
- Dostęp do wyników retrieval jest filtrowany przez `tenant_id` i `document_permissions` na poziomie zapytania SQL — użytkownik fizycznie nie może uzyskać danych innego tenanta nawet przy błędzie aplikacyjnym.

### 4.3 Polityka PII (Personally Identifiable Information)

- PII detection uruchamiana na każdym dokumencie podczas indeksowania (przed zapisem embeddingów).
- Wykryte PII (imiona, numery identyfikacyjne, adresy, numery kont) są maskowane w logach i metadanych z zachowaniem oryginału w zaszyfrowanej warstwie.
- Klucz szyfrowania PII: per-tenant klucz przechowywany w Azure Key Vault, rotacja co 90 dni.
- Prawo do usunięcia (GDPR): usunięcie danych tenanta obejmuje usunięcie embeddingów, logów (z wyjątkiem audytowych), dokumentów źródłowych. Procedura udokumentowana w runbooku.
- Zakaz logowania PII w structured logs — walidacja przez pre-commit hook (wyrażenia regularne dla numerów PESEL, NIP, numerów kart).

### 4.4 Mitigacja prompt injection

Szczegółowa specyfikacja w `/docs/governance_model.md`. Podsumowanie wymagań operacyjnych:

- Latencja walidacji anti-injection: ≤ 100 ms dla p95.
- False positive rate walidacji: ≤ 2% (wiadomości legitymne blokowane błędnie).
- False negative rate (wymaganie bezpieczeństwa): ≤ 0.1% (ataki przepuszczone przez filtr).
- Każde zdarzenie injection attempt jest logowane z pełnym payload (zaszyfrowanym) w logu audytowym.

---

## 5. Audytowalność

### 5.1 Zakres obowiązkowego logowania

Każda z poniższych operacji generuje wpis w logu audytowym:

| Kategoria | Operacja | Poziom |
|---|---|---|
| Authentication | Login, logout, token refresh, failed auth | INFO / WARN |
| Document | Upload, indeksowanie, usunięcie, dostęp | INFO |
| Query | Zapytanie użytkownika, wyniki retrieval, odpowiedź AI | INFO |
| Agent | Inicjalizacja, zmiana stanu, zakończenie, błąd | INFO / ERROR |
| Governance | Injection attempt, refusal, schema validation failure | WARN / ERROR |
| Admin | Zmiana RBAC, konfiguracji, tenanta | INFO |
| System | Start/stop serwisu, circuit breaker state change | INFO |

### 5.2 Strategia correlation_id

- `correlation_id`: UUID v4 generowany przez API Gateway przy każdym żądaniu.
- Propagowany przez wszystkie serwisy jako nagłówek HTTP `X-Correlation-ID` i pole zdarzenia Redpanda.
- Każdy log entry zawiera `correlation_id` — umożliwia pełne prześledzenie żądania przez wszystkie serwisy.
- `session_id`: UUID v4 per sesja użytkownika, łączy wiele `correlation_id` w jedną sesję.
- `trace_id`: OpenTelemetry trace ID dla distributed tracing (Azure Monitor Application Insights).

Format log entry (JSON):
```json
{
  "timestamp": "2026-02-27T14:30:00.000Z",
  "level": "INFO",
  "service": "query-service",
  "version": "1.2.3",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "session_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "trace_id": "abc123def456",
  "user_id": "user_xyz",
  "tenant_id": "tenant_abc",
  "event": "query.processed",
  "duration_ms": 1234,
  "model_id": "gpt-4o",
  "tokens_used": 2048
}
```

### 5.3 Śledzenie wersji modelu

- Każda odpowiedź AI zawiera `model_id` i `model_version` w metadanych odpowiedzi.
- Log audytowy rejestruje `model_id` dla każdego wywołania LLM.
- Zmiana wersji modelu wymaga wpisu w CHANGELOG i testu regresji odpowiedzi na zestawie testowym (golden dataset).
- Przechowywanie `model_id` umożliwia retroaktywną analizę — które odpowiedzi zostały wygenerowane przez który model.

---

## 6. Kontrola kosztów

### 6.1 Śledzenie tokenów

- Metryki Prometheus: `llm_tokens_total{type="prompt|completion", model, tenant, operation}`.
- Granularność: per wywołanie LLM, agregowane per tenant, per dzień.
- Alert przy przekroczeniu 80% dziennego budżetu tokenów per tenant.
- Miesięczny raport kosztów per tenant generowany automatycznie z metryk Prometheus.

Budżety tokenów (konfigurowalny per tenant):

| Tier | Dzienny limit tokenów | Miesięczny szacowany koszt |
|---|---|---|
| Standard | 500 000 tokenów | Zgodnie z cennikiem Azure OpenAI |
| Professional | 2 000 000 tokenów | Zgodnie z cennikiem Azure OpenAI |
| Enterprise | Konfigurowalny | Kontrakt |

### 6.2 Strategia reużycia embeddingów

- Embedding cache: `hash(text_content) -> embedding_vector` przechowywany w Redis z TTL 30 dni.
- Przed każdym wywołaniem embedding API: sprawdzenie cache — hit rate monitorowany jako metryka.
- Embedded chunks są reużywane między sesjami i użytkownikami tego samego tenanta.
- Przy aktualizacji dokumentu: inwalidacja cache wyłącznie zmienionych chunks (przez porównanie hash).

### 6.3 Strategia cache dla odpowiedzi

- Semantic cache: odpowiedzi na zapytania o podobieństwie > 0.95 (cosine similarity) są zwracane z cache zamiast ponownego wywołania LLM.
- Cache key: `hash(query_embedding + sorted(chunk_ids_in_context))`.
- TTL cache odpowiedzi: 1 godzina (konfigurowalny `RESPONSE_CACHE_TTL_SECONDS`).
- Cache invalidation: przy aktualizacji lub usunięciu dokumentu — inwalidacja wszystkich odpowiedzi zawierających jego chunks.
- Cache miss rate monitorowany jako metryka — jeśli > 95%, cache nie przynosi korzyści i wymaga przeglądu strategii.
