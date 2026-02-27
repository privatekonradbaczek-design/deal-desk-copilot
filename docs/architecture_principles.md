# /docs/architecture_principles.md

**Klasyfikacja:** Wewnętrzna — Technical Leadership
**Wersja:** 1.0.0
**Status:** Obowiązujący
**Ostatnia aktualizacja:** 2026-02-27

---

## Wprowadzenie

Niniejszy dokument definiuje niezmienne zasady architektoniczne platformy Deal Desk Copilot. Każda zasada posiada uzasadnienie techniczne oraz bezpośredni wpływ na decyzje implementacyjne. Zasady mają charakter normatywny — odstępstwa wymagają formalnego ADR zatwierdzanego przez Technical Leadership.

---

## Zasada 1: Event-Driven jako domyślny model komunikacji

### Opis

Komunikacja między serwisami domenowymi odbywa się wyłącznie przez asynchroniczną wymianę zdarzeń za pośrednictwem Redpanda. Zdarzenia są jedynym mechanizmem propagacji zmian stanu między komponentami. Synchroniczne wywołania HTTP między serwisami domenowymi są niedopuszczalne.

### Uzasadnienie

Model synchroniczny wprowadza temporal coupling — serwis wywołujący blokuje się na dostępność serwisu wywoływanego. W systemie przetwarzającym dokumenty klasy enterprise, gdzie operacje indeksowania mogą trwać dziesiątki sekund, synchroniczne wywołania prowadziłyby do kaskadowych timeoutów i degradacji całego systemu. Asynchroniczna komunikacja izoluje serwisy w czasie i pozwala na niezależne skalowanie producenta i konsumenta.

### Wpływ na implementację

- Każde zdarzenie posiada własny schemat Avro/JSON Schema wersjonowany w schema registry.
- Serwisy implementują at-least-once delivery z idempotentną obsługą duplikatów.
- Backpressure jest obsługiwany przez mechanizmy Redpanda consumer lag monitoring.
- Dead Letter Queue (DLQ) dla każdego topicu z automatycznym alertem po przekroczeniu progu.
- Synchroniczne FastAPI endpoints służą wyłącznie do komunikacji z klientami zewnętrznymi.

---

## Zasada 2: Loose Coupling i wysoka kohezja

### Opis

Każdy serwis enkapsuluje kompletną logikę swojej domeny i nie dzieli kodu domenowego z innymi serwisami. Interfejs serwisu jest kontraktem — zmiany wewnętrznej implementacji nie wpływają na konsumentów. Serwis nie posiada wiedzy o implementacji innych serwisów.

### Uzasadnienie

Tight coupling prowadzi do sytuacji, w której zmiana w jednym serwisie wymaga modyfikacji i ponownego wdrożenia innych serwisów. W systemie z wieloma zespołami lub szybkim tempem iteracji jest to bezpośrednia przyczyna regresji i wydłużenia cyklu wdrożeń. Wysoka kohezja zapewnia, że logika domenowa jest skoncentrowana, testowalna i modyfikowalna niezależnie.

### Wpływ na implementację

- Zakaz importów cross-service na poziomie kodu (shared libraries wyłącznie dla infrastruktury, nie domeny).
- Każdy serwis posiada własny schemat bazy danych — cross-schema queries są zabronione.
- Współdzielone modele Pydantic dla schematów zdarzeń są utrzymywane w dedykowanym pakiecie `shared-schemas`, bez logiki domenowej.
- Zmiany schematu zdarzeń wymagają zachowania kompatybilności wstecznej przez minimum dwie wersje API.

---

## Zasada 3: Separacja warstwy domenowej i infrastrukturalnej

### Opis

Logika biznesowa jest całkowicie niezależna od szczegółów infrastrukturalnych (baza danych, broker zdarzeń, HTTP client, LLM provider). Domeny definiują interfejsy (porty), infrastruktura dostarcza implementacje (adaptery) — wzorzec Ports & Adapters (Hexagonal Architecture).

### Uzasadnienie

Bezpośrednie użycie klientów infrastruktury w logice domenowej uniemożliwia testowanie domenowe bez uruchamiania zewnętrznych zależności. W systemie AI, gdzie koszt wywołania LLM jest mierzalny, testowanie logiki orkiestracji nie może wymagać rzeczywistych wywołań API. Separacja umożliwia również podmianę infrastruktury (np. migrację z pgvector na Qdrant) bez modyfikacji logiki domenowej.

### Wpływ na implementację

```
services/
  document_processor/
    domain/          # Czysta logika biznesowa, zero importów infrastruktury
      models.py
      services.py
      interfaces.py  # Abstrakcyjne porty (ABC)
    infrastructure/  # Implementacje adapterów
      postgres_repo.py
      redpanda_publisher.py
      openai_client.py
    api/             # Warstwa HTTP
      routes.py
```

- Testy jednostkowe domenowe używają wyłącznie mocków interfejsów.
- Testy integracyjne weryfikują adaptery z rzeczywistymi zależnościami w Docker.
- Wstrzykiwanie zależności (DI) jest jedynym mechanizmem przekazywania implementacji do domeny.

---

## Zasada 4: Idempotencja w obsłudze zdarzeń

### Opis

Każdy konsument zdarzeń musi być zaprojektowany tak, aby wielokrotne przetworzenie tego samego zdarzenia produkowało identyczny wynik jak jego jednokrotne przetworzenie. System nie może polegać na gwarancji exactly-once delivery.

### Uzasadnienie

Redpanda (Kafka) gwarantuje at-least-once delivery. Awarie sieci, restarty konsumentów i rebalancing partycji prowadzą do redelivery zdarzeń. System, który nie obsługuje duplikatów, wyprodukuje spójne dane wyłącznie przy braku awarii — co jest założeniem niedopuszczalnym w systemie produkcyjnym. Koszt implementacji idempotencji jest wielokrotnie niższy niż koszt debugowania niespójności danych.

### Wpływ na implementację

- Każde zdarzenie zawiera `event_id` (UUID v4) jako klucz idempotencji.
- Konsumenci przechowują przetworzone `event_id` w dedykowanej tabeli `processed_events` z TTL.
- Przed przetworzeniem: sprawdzenie `event_id` w tabeli — jeśli istnieje, zdarzenie jest pomijane z logiem `DEBUG`.
- Operacje bazy danych używają `INSERT ... ON CONFLICT DO NOTHING` lub `UPSERT` tam gdzie to możliwe.
- Wywołania LLM dla identycznych inputów są cachowane (embedding cache, response cache z TTL).

---

## Zasada 5: Jawna maszyna stanów dla agentów

### Opis

Każdy przepływ agenta AI jest modelowany jako explicit finite state machine z jawnie zdefiniowanymi stanami, przejściami, warunkami przejść i akcjami wyjścia. Nie istnieje przepływ agenta oparty na łańcuchu wywołań bez modelu stanów. LangGraph jest narzędziem implementacyjnym tej zasady.

### Uzasadnienie

Agenty AI bez jawnego modelu stanów są niedeterministyczne z punktu widzenia obserwatora zewnętrznego — nie można przewidzieć ani zweryfikować, w jakim stanie znajduje się agent bez analizy jego historii wywołań. W systemie produkcyjnym wymagającym audytowalności każda operacja agenta musi być możliwa do prześledzenia przez stan, w którym nastąpiła. Jawna maszyna stanów umożliwia również deterministyczne testowanie i replay.

### Wpływ na implementację

- Każdy agent posiada plik `state_machine.py` z definicją `AgentState` (TypedDict lub Pydantic model).
- Przejścia stanów są wyłącznie funkcjami czystymi: `(state, event) -> new_state`.
- Stan agenta jest serializowalny i persystowany w PostgreSQL — umożliwia resume po awarii.
- Każda zmiana stanu jest emitowana jako zdarzenie do Redpanda z poprzednim i nowym stanem.
- LangGraph checkpointing jest skonfigurowany z backendem PostgreSQL, nie in-memory.

---

## Zasada 6: Auditability by Design

### Opis

Każda operacja mająca wpływ na dane lub decyzję systemu jest rejestrowana w niezmiennym logu audytowym przed wykonaniem operacji i po jej zakończeniu. Nie istnieje operacja bez śladu audytowego. Log audytowy jest traktowany jako osobna, niemodyfikowalna projekcja stanu systemu.

### Uzasadnienie

Systemy AI przetwarzające dokumenty prawne i handlowe podlegają wymogom compliance (GDPR, SOC 2, potencjalnie ISO 27001). Brak pełnej audytowalności dyskwalifikuje system z wdrożeń enterprise. Retroaktywne dodanie audytowalności jest wielokrotnie kosztowniejsze niż jej zaprojektowanie jako pierwszoklasowego wymagania.

### Wpływ na implementację

- Dedykowany `Audit Service` konsumuje zdarzenia ze wszystkich topiców i zapisuje je do niezmiennej tabeli `audit_log`.
- Tabela `audit_log` nie posiada operacji UPDATE ani DELETE na poziomie aplikacji — tylko INSERT.
- Każdy wpis audytowy zawiera: `correlation_id`, `event_id`, `actor_id`, `action`, `resource_id`, `timestamp_utc`, `payload_hash`, `model_version` (dla operacji AI).
- Integrity verification: hash każdego wpisu jest obliczany i weryfikowany przy odczycie.
- Retencja logów audytowych: minimum 7 lat (konfigurowalny parametr środowiskowy).

---

## Zasada 7: Deterministyczny retrieval zamiast generatywnego zgadywania

### Opis

Warstwa RAG systemu zwraca wyłącznie fragmenty dokumentów, które zostały znalezione przez retrieval z mierzalnym score podobieństwa powyżej zdefiniowanego progu. System nie generuje odpowiedzi syntetyzujących wiedzę spoza zaindeksowanych dokumentów bez jawnego oznaczenia i zgody operatora.

### Uzasadnienie

Halucynacje LLM w kontekście analizy kontraktów klasy enterprise są niedopuszczalne — błędna interpretacja klauzuli może prowadzić do decyzji biznesowych opartych na fałszywych przesłankach. Deterministyczny retrieval ogranicza przestrzeń odpowiedzi do zweryfikowanych fragmentów. Koszt false negative (brak odpowiedzi) jest wielokrotnie niższy niż koszt false positive (błędna odpowiedź).

### Wpływ na implementację

- Próg similarity score dla retrieval: `RETRIEVAL_SIMILARITY_THRESHOLD` (domyślnie 0.75, konfigurowalny).
- Każda odpowiedź zawiera listę `citations` z: `chunk_id`, `document_id`, `page_number`, `similarity_score`, `excerpt`.
- Jeśli retrieval nie zwróci wyników powyżej progu, odpowiedź ma status `NO_RELEVANT_CONTEXT` z komunikatem dla użytkownika.
- Prompt LLM zawiera jawną instrukcję: odpowiadaj wyłącznie na podstawie dostarczonych fragmentów.
- Weryfikacja post-generation: odpowiedź jest sprawdzana pod kątem twierdzeń bez pokrycia w fragmentach.

---

## Zasada 8: Security-First Architecture

### Opis

Bezpieczeństwo jest projektowane jako właściwość każdej warstwy systemu, nie jako nakładka na gotową implementację. Każdy komponent zakłada, że jego wejście może być złośliwe, a jego sąsiedzi mogą być skompromitowani.

### Uzasadnienie

Systemy AI są narażone na specyficzną klasę ataków: prompt injection, data poisoning, model inversion, i indirect prompt injection przez zaindeksowane dokumenty. Tradycyjne security controls (firewall, WAF) nie chronią przed atakami warstwą aplikacji AI. Jedyną skuteczną ochroną jest wielowarstwowa weryfikacja na każdym etapie przetwarzania.

### Wpływ na implementację

- **API Gateway:** JWT validation, rate limiting (per user, per endpoint), request size limits.
- **Document Ingestion:** Sanityzacja metadanych, skan antywirusowy binariów, limit rozmiaru dokumentu.
- **Prompt Construction:** Separacja system prompt od user input, enkodowanie znaków specjalnych, detekcja wzorców injection przed wywołaniem LLM.
- **Retrieval Layer:** Filtrowanie wyników retrieval przez RBAC — użytkownik nie widzi fragmentów dokumentów, do których nie ma dostępu.
- **Response Layer:** Weryfikacja czy odpowiedź nie zawiera danych systemowych (connection strings, tokeny) przez pattern matching.
- **Secrets Management:** Azure Key Vault w produkcji, Docker Secrets w środowisku lokalnym. Zakaz `.env` w produkcji.

---

## Zasada 9: Założenia skalowalności

### Opis

System jest projektowany z założeniem możliwości poziomego skalowania każdego serwisu niezależnie od pozostałych, bez zmian w architekturze. Skalowanie pionowe jest traktowane jako tymczasowe obejście, nie rozwiązanie docelowe.

### Uzasadnienie

Obciążenie platformy analizy kontraktów jest asymetryczne i nieprzewidywalne — okresy intensywnego indeksowania (batch upload) przeplatają się z wysoką liczbą równoległych zapytań (Q&A sesje). System, który wymaga skalowania jako całość, jest nieefektywny kosztowo. Niezależne skalowanie pozwala na optymalizację kosztu per operacja.

### Wpływ na implementację

- Serwisy są bezstanowe — stan sesji nie jest przechowywany w pamięci serwisu.
- Consumer groups Redpanda umożliwiają równoległe przetwarzanie przez wiele instancji konsumentów.
- Embeddings są przeliczane tylko przy zmianie dokumentu — nie przy każdym zapytaniu.
- Connection pooling (PgBouncer lub asyncpg pool) dla każdego serwisu z konfigurowalnymi limitami.
- HPA (Horizontal Pod Autoscaler) w AKS skonfigurowany per serwis z metrykami custom (queue lag, request rate).
- Partycjonowanie Redpanda: klucz partycji = `tenant_id` dla izolacji obciążenia per klient.

---

## Zasada 10: Świadomość kosztowa — zarządzanie tokenami

### Opis

Każde wywołanie LLM jest monitorowane pod kątem zużycia tokenów. System posiada mechanizmy limitowania, cachowania i optymalizacji zużycia tokenów na wszystkich poziomach. Koszt operacji AI jest mierzalny i atrybutowalny do konkretnego użytkownika, tenant i operacji.

### Uzasadnienie

Azure OpenAI rozlicza się per token. W systemie produkcyjnym bez kontroli kosztów pojedynczy błąd w implementacji (np. brak cache dla powtarzalnych zapytań, niepoprawna długość kontekstu) może generować koszty przekraczające budżet operacyjny. Świadomość kosztowa na poziomie architektury jest wymaganiem finansowym, nie opcjonalnym ulepszeniem.

### Wpływ na implementację

- Każde wywołanie LLM loguje: `prompt_tokens`, `completion_tokens`, `total_tokens`, `model_id`, `operation_type`, `tenant_id`, `user_id`.
- Embedding cache w Redis/pgvector: identyczne fragmenty tekstu nie są re-embeddowane — `hash(text) -> embedding`.
- Response cache: identyczne zapytania (hash query + hash kontekstu) zwracają cachowalną odpowiedź z TTL.
- Limity tokenów per tenant (konfigurowalny `TOKEN_BUDGET_PER_TENANT_DAILY`).
- Automatyczny alert przy przekroczeniu 80% dziennego budżetu tokenów.
- Context window management: chunking strategia zapewnia, że kontekst przekazywany do LLM nie przekracza `MAX_CONTEXT_TOKENS` (konfigurowalny, domyślnie 8192 dla GPT-4).
- Dashboard kosztów per tenant eksponowany jako metryki Prometheus.
