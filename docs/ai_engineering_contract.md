# /docs/ai_engineering_contract.md

**Klasyfikacja:** Wewnętrzna — Technical Leadership
**Wersja:** 1.0.0
**Status:** Obowiązujący
**Ostatnia aktualizacja:** 2026-02-27

---

## 1. Misja i zakres projektu

**Deal Desk Copilot** jest produkcyjną platformą automatyzacji analizy kontraktów klasy enterprise. System przetwarza dokumenty prawne i handlowe, ekstrahuje ustrukturyzowane dane, odpowiada na pytania w oparciu o zweryfikowane fragmenty źródłowe oraz zapewnia pełną audytowalność każdej operacji AI.

### 1.1 Zakres funkcjonalny

- Indeksowanie i przetwarzanie dokumentów kontraktowych (PDF, DOCX, TXT) do wektorowej bazy wiedzy.
- Strukturalna ekstrakcja danych kontraktowych: strony, terminy, klauzule, zobowiązania, ryzyka.
- Odpowiadanie na zapytania w języku naturalnym z przymusowym cytowaniem źródeł.
- Orkiestracja wielokrokowych przepływów agentów z jawną maszyną stanów (LangGraph).
- Rejestrowanie każdej decyzji AI w niezmiennym logu audytowym.
- Egzekwowanie reguł governance: wykrywanie prompt injection, walidacja schematu, polityki odmowy.

### 1.2 Zakres poza systemem

System **nie jest** i **nie będzie**:

- Systemem zarządzania dokumentami (DMS) — pełni wyłącznie rolę warstwy analitycznej.
- Silnikiem podpisywania lub autoryzacji umów.
- Interfejsem do bezpośredniej negocjacji kontraktowej bez nadzoru człowieka.
- Substytutem przeglądu prawnego — wyniki systemu wymagają walidacji przez uprawniony personel.

---

## 2. Wizja architektoniczna

Platforma realizuje model **rozproszonego systemu przetwarzania dokumentów sterowanego zdarzeniami**, w którym każdy komponent posiada jednoznacznie zdefiniowaną odpowiedzialność domenową i komunikuje się wyłącznie przez zdarzenia asynchroniczne (Redpanda) lub synchroniczne API (FastAPI) z zachowaniem kontraktu interfejsu.

### 2.1 Warstwy architektury

| Warstwa | Technologia | Odpowiedzialność |
|---|---|---|
| API Gateway | FastAPI + JWT | Uwierzytelnianie, routing, rate limiting |
| Event Bus | Redpanda (Kafka-compatible) | Asynchroniczna komunikacja międzyserwisowa |
| Agent Orchestration | LangGraph | Explicit state machine dla przepływów AI |
| RAG Pipeline | pgvector + custom chunking | Deterministyczny retrieval semantyczny |
| Storage | PostgreSQL + pgvector | Przechowywanie danych i embeddingów |
| Governance | Audit Service | Logowanie decyzji, enforcement cytowań |
| Deployment | Docker → AKS | Lokalny development, produkcyjny Azure |

### 2.2 Przepływ danych — zasada ogólna

Każde zdarzenie w systemie posiada: unikalny `event_id`, `correlation_id` łączący zdarzenia w jednym żądaniu, `timestamp` w UTC, wersję schematu zdarzenia oraz identyfikator inicjatora operacji.

---

## 3. Filozofia inżynieryjna

### 3.1 Jawność ponad implicitność

Każda decyzja systemu — wybór fragmentu dokumentu, ocena ryzyka, odmowa odpowiedzi — musi być możliwa do prześledzenia do konkretnego źródła danych, reguły lub modelu. System nie produkuje odpowiedzi bez weryfikowalnego łańcucha dowodowego.

### 3.2 Deterministyczny retrieval

Warstwa RAG nie generuje wiedzy. Ekstrahuje i cytuje fragmenty istniejących dokumentów. Generatywne uzupełnianie luk w wiedzy jest niedopuszczalne bez jawnego oznaczenia jako `inference` w metadanych odpowiedzi.

### 3.3 Fail-safe jako domyślna postawa

W przypadku niejednoznaczności, braku danych lub wykrycia potencjalnego ataku system zwraca odmowę z kodem przyczyny. Nie próbuje generować przybliżonej odpowiedzi.

### 3.4 Zero trust dla danych wejściowych

Każde wejście użytkownika jest traktowane jako potencjalnie złośliwe do momentu przejścia przez warstwę sanityzacji i detekcji prompt injection. Dotyczy to zarówno treści dokumentów, jak i zapytań użytkownika.

### 3.5 Obserwowalność jako wymaganie funkcjonalne

Każdy serwis eksponuje metryki Prometheus, logi strukturalne (JSON) i trace identifiers. Brak obserwowalności jest traktowany jako defekt blocker, nie jako dług techniczny.

---

## 4. Granice systemu

### 4.1 Granice zaufania

```
[Użytkownik] → [API Gateway — granica zaufania zewnętrznego]
                      ↓
[Serwisy wewnętrzne — strefa zaufana]
                      ↓
[LLM API (Azure OpenAI) — granica zaufania zewnętrznego]
```

Komunikacja między strefami wymaga: uwierzytelnienia (JWT dla użytkowników, Managed Identity dla Azure), walidacji schematu danych oraz rejestracji w logu audytowym.

### 4.2 Granice serwisów

| Serwis | Wejście | Wyjście | Odpowiedzialność wyłączna |
|---|---|---|---|
| Document Processor | Plik binarny | Zdarzenie `document.indexed` | Parsing, chunking, embedding |
| Query Service | Zapytanie użytkownika | Odpowiedź z cytatami | Retrieval, odpowiedź |
| Agent Orchestrator | Zdarzenie zadania | Zdarzenie wyniku | Zarządzanie stanem agenta |
| Audit Service | Każde zdarzenie | Log wpis | Niezmienne logowanie |
| Governance Engine | Dane wejściowe | Ocena bezpieczeństwa | Detekcja zagrożeń |

---

## 5. Jawne ograniczenia architektoniczne

Poniższe ograniczenia są **bezwzględne** i nie podlegają negocjacji bez formalnej zmiany tego dokumentu:

1. **Zakaz architektury monolitycznej.** Każda domena biznesowa jest osobnym serwisem z niezależnym wdrożeniem.
2. **Zakaz synchronicznej komunikacji między serwisami domenowymi.** Serwisy domenowe komunikują się wyłącznie przez Redpanda. Synchroniczne API (FastAPI) obsługuje wyłącznie żądania klientów zewnętrznych.
3. **Zakaz bezpośredniego dostępu do bazy danych między serwisami.** Każdy serwis posiada własny schemat w PostgreSQL. Cross-schema queries są niedopuszczalne.
4. **Zakaz hardcodowania konfiguracji.** Wszystkie parametry środowiskowe, klucze API, connection strings są zarządzane przez zmienne środowiskowe lub Azure Key Vault w produkcji.
5. **Zakaz odpowiedzi bez cytowania źródeł.** Każda odpowiedź systemu na zapytanie kontraktowe musi zawierać co najmniej jedno zweryfikowane źródło z identyfikatorem fragmentu dokumentu.
6. **Zakaz przechowywania PII poza zaszyfrowaną warstwą.** Dane osobowe identyfikowalne są maskowane lub szyfrowane przed zapisem do warstwy analitycznej.

---

## 6. Wymagania produkcyjnej gotowości

Funkcjonalność jest gotowa do produkcji wyłącznie po spełnieniu **wszystkich** poniższych kryteriów:

### 6.1 Jakość kodu

- Pokrycie testami jednostkowymi: ≥ 80% dla logiki domenowej.
- Pokrycie testami integracyjnymi: wszystkie ścieżki krytyczne (happy path + failure modes).
- Brak błędów mypy w trybie `strict` dla nowych modułów.
- Przegląd kodu przez co najmniej jednego inżyniera poza autorem.

### 6.2 Obserwowalność

- Zdefiniowane metryki SLO dla każdego nowego endpointu lub konsumenta zdarzeń.
- Alerty Prometheus skonfigurowane dla warunków SLO breach.
- Structured log entries dla każdej operacji z `correlation_id`.

### 6.3 Bezpieczeństwo

- Skan podatności zależności (pip-audit lub Snyk) bez krytycznych wyników.
- Weryfikacja, że nowe endpointy są objęte RBAC.
- Dane testowe nie zawierają rzeczywistych danych kontraktowych.

### 6.4 Dokumentacja

- Zaktualizowana specyfikacja OpenAPI dla zmienionych endpointów.
- Zaktualizowany schemat zdarzenia w repozytorium schematów.
- Zaktualizowany `CHANGELOG.md` z opisem zmiany i jej uzasadnieniem.

---

## 7. Zasady generowania kodu

### 7.1 Asystenci AI w development workflow

Kod generowany przez narzędzia AI (GitHub Copilot, Claude, GPT-4) podlega **identycznym** standardom przeglądu jak kod pisany ręcznie. Autor commita jest odpowiedzialny za poprawność, bezpieczeństwo i zgodność ze standardami każdej linii kodu niezależnie od jej pochodzenia.

### 7.2 Zakazane praktyki w generowanym kodzie

- Generowane sekrety, klucze lub tokeny w kodzie źródłowym.
- Wzorce obsługi błędów z `except Exception: pass`.
- Synchroniczne wywołania I/O w asynchronicznych handlerach.
- Zapytania SQL budowane przez konkatenację stringów.

### 7.3 Wymagane artefakty dla nowych komponentów

Każdy nowy serwis, agent lub moduł domenowy musi posiadać:
- Schemat Pydantic dla wszystkich danych wejściowych i wyjściowych.
- Definicję zdarzeń (jeśli emituje lub konsumuje zdarzenia).
- Testy jednostkowe pokrywające scenariusze błędów.
- Wpis w rejestrze zależności zewnętrznych (jeśli dodaje nowe).

---

## 8. Standardy dokumentacji

### 8.1 Dokumentacja techniczna

- Architecture Decision Records (ADR) dla każdej decyzji architektonicznej o istotnym wpływie.
- Format ADR: Kontekst → Decyzja → Konsekwencje → Alternatywy rozważane.
- Przechowywanie: `/docs/adr/` z numeracją sekwencyjną.

### 8.2 Dokumentacja API

- Specyfikacja OpenAPI 3.1 generowana automatycznie z FastAPI, uzupełniana ręcznie o przykłady.
- Każdy endpoint: opis, parametry, kody odpowiedzi, przykład żądania i odpowiedzi.
- Schemat zdarzeń: AsyncAPI 2.x dla wszystkich topic definitions.

### 8.3 Dokumentacja operacyjna

- Runbook dla każdego krytycznego scenariusza awaryjnego.
- Procedura rollback dla każdego wdrożenia.
- Mapa zależności serwisów aktualizowana przy każdej nowej integracji.

---

## 9. Definicja „Done" dla nowych funkcjonalności

Funkcjonalność jest uznana za ukończoną wyłącznie gdy:

- [ ] Kod przeszedł przegląd i jest zmergowany do głównej gałęzi.
- [ ] Testy jednostkowe i integracyjne przechodzą w CI/CD pipeline.
- [ ] Metryki obserwowalności są zdefiniowane i zbierane.
- [ ] Dokumentacja API jest zaktualizowana.
- [ ] Wpis ADR istnieje dla każdej decyzji architektonicznej podjętej w ramach implementacji.
- [ ] Weryfikacja bezpieczeństwa przeszła bez krytycznych wyników.
- [ ] `CHANGELOG.md` jest zaktualizowany.
- [ ] Product Owner potwierdził zgodność z wymaganiami biznesowymi.
- [ ] Funkcjonalność jest możliwa do wyłączenia bez wpływu na pozostałe serwisy.
