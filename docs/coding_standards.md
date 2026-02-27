# /docs/coding_standards.md

**Klasyfikacja:** Wewnętrzna — Technical Leadership
**Wersja:** 1.0.0
**Status:** Obowiązujący
**Ostatnia aktualizacja:** 2026-02-27

---

## 1. Standardy kodu Python

### 1.1 Wersja języka i interpreter

- Python ≥ 3.11 dla wszystkich serwisów. Funkcjonalności 3.11: `tomllib`, ulepszone error messages, `Self` type, `StrEnum`.
- Interpreter: CPython. Zakaz używania PyPy, Cython ani innych implementacji bez jawnego ADR.
- Formatowanie: `ruff format` (zastępuje `black`). Konfiguracja w `pyproject.toml`.
- Linting: `ruff check` z zestawami reguł: `E`, `F`, `I`, `N`, `UP`, `S`, `B`, `C4`, `DTZ`, `T20`, `SIM`.
- Type checking: `mypy --strict` dla nowych modułów. Istniejące moduły: `mypy` bez `--strict` z progresywnym dodawaniem adnotacji.

### 1.2 Konfiguracja pyproject.toml (standard)

```toml
[tool.ruff]
target-version = "py311"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "S", "B", "C4", "DTZ", "T20", "SIM"]
ignore = ["S101"]  # allow assert in tests

[tool.mypy]
python_version = "3.11"
strict = true
ignore_missing_imports = false

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

### 1.3 Zakazy bezwzględne

- `from module import *` — zawsze importy jawne.
- `eval()`, `exec()`, `compile()` — zakaz bezwarunkowy. Zastępnik: AST, pydantic parsing.
- `os.system()`, `subprocess.shell=True` — zakaz. Zastępnik: `subprocess.run([...], shell=False)`.
- `pickle` do serializacji danych nieufanych.
- `assert` w kodzie produkcyjnym (poza testami) do walidacji — zastępnik: jawne warunki z wyjątkami.
- Mutowalne wartości domyślne jako argumenty funkcji: `def f(data: list = [])` → `def f(data: list | None = None)`.

---

## 2. Wymóg type hints

### 2.1 Zakres obowiązku

Type hints są obowiązkowe dla:
- Wszystkich sygnatur funkcji i metod (argumenty i zwracany typ).
- Atrybutów klas (z wyjątkiem prywatnych atrybutów inicjalizowanych dynamicznie).
- Zmiennych modułowych i stałych.

### 2.2 Standardy annotacji

```python
# POPRAWNIE
from __future__ import annotations
from collections.abc import Sequence, Mapping, AsyncIterator
from typing import TypeVar, Generic, Protocol

T = TypeVar("T")

def process_chunks(
    chunks: Sequence[str],
    metadata: Mapping[str, str],
    *,
    max_tokens: int = 512,
) -> list[ProcessedChunk]:
    ...

async def stream_response(query: str) -> AsyncIterator[str]:
    ...

# BŁĘDNIE — nie używać
from typing import List, Dict, Optional, Tuple  # deprecated w Python 3.9+
def process(data: List[str]) -> Dict[str, int]: ...  # zamiast list[str], dict[str, int]
def get(value: Optional[str]) -> None: ...  # zamiast str | None
```

### 2.3 Specjalne przypadki

- `Any` — dozwolone wyłącznie przy integracji z bibliotekami bez stubs, z komentarzem uzasadniającym.
- `cast()` — dozwolone przy deasercji typów z zewnętrznych API, z komentarzem.
- `TypedDict` — preferowany nad `dict[str, Any]` dla ustrukturyzowanych słowników.

---

## 3. Obowiązkowa walidacja Pydantic

### 3.1 Zakres stosowania

Pydantic (v2) jest jedynym dopuszczalnym mechanizmem walidacji danych na granicach systemu:
- Żądania i odpowiedzi HTTP (FastAPI schema).
- Schematy zdarzeń Redpanda (payload zdarzenia).
- Dane wyjściowe LLM (structured output).
- Dane wczytywane z bazy danych do warstwy domenowej.
- Konfiguracja serwisu (BaseSettings).

### 3.2 Konwencje modeli Pydantic

```python
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic import ConfigDict
from uuid import UUID
from datetime import datetime

class ContractClause(BaseModel):
    model_config = ConfigDict(
        frozen=True,           # Immutable — wartości nie można zmienić po walidacji
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    clause_id: UUID
    clause_type: ClauseType  # Enum, nie raw string
    content: str = Field(min_length=1, max_length=10_000)
    page_number: int = Field(ge=1)
    confidence_score: float = Field(ge=0.0, le=1.0)
    extracted_at: datetime

    @field_validator("content")
    @classmethod
    def content_must_not_be_whitespace_only(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Clause content cannot be whitespace only")
        return v
```

### 3.3 Zakaz raw dict jako granicy systemu

```python
# BŁĘDNIE
def process_event(event: dict) -> dict:
    user_id = event["user_id"]  # Brak walidacji, brak type safety

# POPRAWNIE
def process_event(event: QueryRequestedEvent) -> QueryProcessedEvent:
    user_id = event.user_id  # Zwalidowane przez Pydantic przy deserializacji
```

---

## 4. Format logowania strukturalnego

### 4.1 Standard

Wszystkie logi są emitowane w formacie JSON (structured logging). Zakaz używania `print()` w kodzie produkcyjnym. Biblioteka: `structlog` skonfigurowana z `JSONRenderer`.

### 4.2 Konfiguracja structlog (standard serwisu)

```python
import structlog

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.ExceptionRenderer(),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger(__name__)
```

### 4.3 Obowiązkowe pola w każdym logu

```python
# Przy inicjalizacji obsługi żądania — bindowanie kontekstu
structlog.contextvars.bind_contextvars(
    correlation_id=request.headers["X-Correlation-ID"],
    user_id=authenticated_user.id,
    tenant_id=authenticated_user.tenant_id,
    service="query-service",
    version=settings.app_version,
)

# Użycie w kodzie
logger.info(
    "query.retrieval.completed",
    chunks_retrieved=len(chunks),
    similarity_threshold=settings.retrieval_threshold,
    duration_ms=elapsed_ms,
)
```

### 4.4 Poziomy logowania — definicje

| Poziom | Kiedy używać |
|---|---|
| `DEBUG` | Szczegóły implementacyjne, wartości zmiennych (wyłącznie w dev) |
| `INFO` | Normalne zdarzenia biznesowe — start operacji, sukces, wynik |
| `WARNING` | Zdarzenia nieoczekiwane, które nie powodują błędu — retry, fallback, cache miss |
| `ERROR` | Nieobsłużony błąd w obrębie operacji — operacja zakończona niepowodzeniem |
| `CRITICAL` | Awaria serwisu lub utrata danych — wymaga natychmiastowej interwencji |

Zakaz używania `WARNING` dla zdarzeń normalnych i `ERROR` dla warunków oczekiwanych (np. 404).

---

## 5. Zarządzanie zmiennymi środowiskowymi

### 5.1 Pydantic BaseSettings jako standard

```python
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Aplikacja
    app_name: str = "deal-desk-copilot-query-service"
    app_version: str = Field(..., description="Semantic version z pyproject.toml")
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False

    # Baza danych
    database_url: SecretStr = Field(..., description="PostgreSQL DSN")
    db_pool_size: int = Field(default=10, ge=1, le=100)
    db_max_overflow: int = Field(default=20, ge=0, le=100)

    # Azure OpenAI
    azure_openai_endpoint: str = Field(..., description="Azure OpenAI endpoint URL")
    azure_openai_api_key: SecretStr = Field(..., description="Azure OpenAI API key")
    azure_openai_deployment_name: str = Field(..., description="Model deployment name")

    # Redpanda
    redpanda_bootstrap_servers: str = Field(..., description="Comma-separated brokers")

settings = Settings()
```

### 5.2 Hierarchia konfiguracji

Priorytety (od najwyższego):
1. Zmienne środowiskowe systemu operacyjnego.
2. Plik `.env` (tylko środowisko lokalne — nie commitowany do repozytorium).
3. Wartości domyślne w `BaseSettings`.

Produkcja: wyłącznie zmienne środowiskowe wstrzykiwane przez Azure Key Vault jako env vars w AKS Pod spec. Zakaz pliku `.env` w produkcji.

### 5.3 Nazewnictwo zmiennych środowiskowych

Format: `{SERWIS}_{KOMPONENT}_{PARAMETR}` w UPPER_SNAKE_CASE.

Przykłady:
- `QUERY_SERVICE_DATABASE_URL`
- `DOCUMENT_PROCESSOR_AZURE_OPENAI_API_KEY`
- `AUDIT_SERVICE_RETENTION_DAYS`

---

## 6. Separacja konfiguracji

### 6.1 Typy konfiguracji

| Typ | Gdzie | Przykład |
|---|---|---|
| Secrets | Azure Key Vault → env vars | API keys, DB passwords |
| Parametry środowiskowe | Env vars | Database URL, service endpoints |
| Parametry biznesowe | Database (tabela `config`) | Progi similarity, budżety tokenów |
| Parametry deploymentu | Helm values / K8s ConfigMap | Replica count, resource limits |
| Stałe kodowe | `constants.py` w module | Enum values, regex patterns |

### 6.2 Zakaz konfiguracji w kodzie

```python
# BŁĘDNIE
OPENAI_API_KEY = "sk-abc123..."
DATABASE_URL = "postgresql://user:pass@localhost/db"
SIMILARITY_THRESHOLD = 0.75  # Hardcoded — nie można zmienić bez deployu

# POPRAWNIE
# W settings.py:
similarity_threshold: float = Field(
    default=0.75,
    ge=0.0,
    le=1.0,
    description="Minimum cosine similarity for retrieval. Override via env var."
)
```

---

## 7. Strategia dependency injection

### 7.1 Framework

FastAPI Depends() jako mechanizm DI dla warstwy API. Dla logiki domenowej: konstruktor injection (nie service locator, nie global state).

### 7.2 Wzorzec implementacji

```python
# interfaces.py (domena)
from abc import ABC, abstractmethod

class DocumentRepository(ABC):
    @abstractmethod
    async def get_by_id(self, doc_id: UUID) -> Document | None: ...

    @abstractmethod
    async def save(self, document: Document) -> None: ...

# postgres_repository.py (infrastruktura)
class PostgresDocumentRepository(DocumentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, doc_id: UUID) -> Document | None:
        ...

# dependencies.py (FastAPI wiring)
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with async_session_factory() as session:
        yield session

async def get_document_repository(
    session: AsyncSession = Depends(get_db_session),
) -> DocumentRepository:
    return PostgresDocumentRepository(session)

# routes.py
@router.get("/documents/{doc_id}")
async def get_document(
    doc_id: UUID,
    repo: DocumentRepository = Depends(get_document_repository),
) -> DocumentResponse:
    ...
```

### 7.3 Zakaz global state

```python
# BŁĘDNIE
_db_session: AsyncSession | None = None  # Global mutable state

def get_session() -> AsyncSession:
    global _db_session
    if _db_session is None:
        _db_session = create_session()
    return _db_session

# POPRAWNIE — lifecycle management przez FastAPI lifespan
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with create_session_factory() as factory:
        app.state.session_factory = factory
        yield
```

---

## 8. Konwencje struktury folderów

### 8.1 Struktura repozytorium (monorepo)

```
deal-desk-copilot/
├── docs/                          # Dokumentacja architektoniczna
│   ├── adr/                       # Architecture Decision Records
│   └── *.md                       # Dokumenty techniczne
├── services/                      # Serwisy mikrousługowe
│   ├── api_gateway/
│   ├── document_processor/
│   ├── query_service/
│   ├── agent_orchestrator/
│   └── audit_service/
├── shared/                        # Współdzielone pakiety (NIE logika domenowa)
│   ├── schemas/                   # Schematy zdarzeń Pydantic
│   ├── middleware/                # FastAPI middleware
│   └── observability/             # Konfiguracja structlog, Prometheus
├── infrastructure/                # Docker, Kubernetes, Terraform
│   ├── docker/
│   ├── k8s/
│   └── terraform/
└── tests/                         # Testy e2e i integracyjne cross-service
```

### 8.2 Struktura pojedynczego serwisu

```
services/query_service/
├── pyproject.toml
├── Dockerfile
├── src/
│   └── query_service/
│       ├── __init__.py
│       ├── main.py                # FastAPI app factory + lifespan
│       ├── settings.py            # BaseSettings
│       ├── constants.py           # Stałe, enum values
│       ├── domain/
│       │   ├── __init__.py
│       │   ├── models.py          # Domain entities (Pydantic, frozen)
│       │   ├── services.py        # Business logic (pure functions lub classes)
│       │   ├── interfaces.py      # Abstract repositories i external ports
│       │   └── exceptions.py     # Domain exceptions
│       ├── infrastructure/
│       │   ├── __init__.py
│       │   ├── postgres/
│       │   │   ├── models.py      # SQLAlchemy ORM models
│       │   │   └── repository.py  # Concrete implementations
│       │   ├── redpanda/
│       │   │   ├── consumer.py
│       │   │   └── producer.py
│       │   └── openai/
│       │       └── client.py
│       └── api/
│           ├── __init__.py
│           ├── dependencies.py    # FastAPI Depends()
│           ├── routes/
│           │   ├── query.py
│           │   └── health.py
│           └── middleware.py
└── tests/
    ├── unit/
    │   └── domain/
    ├── integration/
    │   └── infrastructure/
    └── conftest.py
```

---

## 9. Strategia testowania

### 9.1 Piramida testów

| Poziom | Zakres | Narzędzie | Cel pokrycia |
|---|---|---|---|
| Unit | Logika domenowa, pure functions | pytest | ≥ 80% dla `domain/` |
| Integration | Adaptery z rzeczywistymi zależnościami | pytest + Docker | Wszystkie ścieżki krytyczne |
| E2E | Pełny przepływ przez API | pytest + httpx | Happy path + primary failure modes |
| Contract | Zgodność schematów zdarzeń | pact lub schemathesis | Wszystkie schematy zdarzeń |

### 9.2 Konwencje testów

```python
# Naming: test_{co_testujemy}_when_{warunek}_then_{oczekiwany_wynik}
async def test_retrieval_service_when_no_documents_indexed_then_returns_empty_context():
    # Arrange
    repo = InMemoryChunkRepository(chunks=[])
    service = RetrievalService(repository=repo, threshold=0.75)

    # Act
    result = await service.retrieve(query_embedding=sample_embedding, top_k=5)

    # Assert
    assert result.chunks == []
    assert result.has_context is False

# Fixtures w conftest.py — nie w metodach testowych
@pytest.fixture
def sample_document() -> Document:
    return Document(
        document_id=UUID("550e8400-e29b-41d4-a716-446655440000"),
        title="Test Contract",
        tenant_id=UUID("7c9e6679-7425-40de-944b-e07fc1f90ae7"),
    )
```

### 9.3 Wymagania dla mocków i fixtures

- Zakaz `unittest.mock.patch` jako dekoratora na poziomie testu — preferowany `pytest-mock` z `mocker` fixture.
- In-memory implementacje interfejsów domenowych (nie `MagicMock`) dla testów jednostkowych logiki.
- `MagicMock` dopuszczalny wyłącznie dla bibliotek zewnętrznych bez interfejsu domenowego.
- Dane testowe: fabryki danych (`factory_boy` lub własne `Builder` klasy) — nie statyczne słowniki.

---

## 10. Filozofia obsługi błędów

### 10.1 Hierarchia wyjątków

```python
# exceptions.py (base)
class DealDeskError(Exception):
    """Bazowy wyjątek platformy."""
    def __init__(self, message: str, error_code: str) -> None:
        super().__init__(message)
        self.error_code = error_code

class DomainError(DealDeskError):
    """Naruszenie reguły domenowej — błąd klienta."""

class InfrastructureError(DealDeskError):
    """Awaria infrastruktury — błąd serwisu."""

class ExternalServiceError(InfrastructureError):
    """Awaria zewnętrznego serwisu (LLM, blob storage)."""

class ValidationError(DomainError):
    """Nieprawidłowe dane wejściowe."""

class AuthorizationError(DomainError):
    """Brak uprawnień do zasobu."""

class ResourceNotFoundError(DomainError):
    """Zasób nie istnieje."""

class GovernanceViolationError(DomainError):
    """Naruszenie polityki governance (injection attempt, schema violation)."""
```

### 10.2 Zasady obsługi wyjątków

```python
# BŁĘDNIE — połknięcie wyjątku
try:
    result = await llm_client.complete(prompt)
except Exception:
    pass  # ZAKAZ BEZWZGLĘDNY

# BŁĘDNIE — zbyt szerokie łapanie
try:
    result = await process_document(doc)
except Exception as e:
    logger.error("Error", error=str(e))
    raise

# POPRAWNIE — wyjątek specyficzny, logowanie z kontekstem, re-raise lub transformacja
try:
    embedding = await openai_client.embed(text)
except openai.RateLimitError as e:
    logger.warning(
        "openai.rate_limit_exceeded",
        retry_after=e.retry_after,
        chunk_id=chunk_id,
    )
    raise ExternalServiceError(
        message=f"OpenAI rate limit exceeded, retry after {e.retry_after}s",
        error_code="OPENAI_RATE_LIMIT",
    ) from e
```

### 10.3 Mapowanie wyjątków na HTTP responses (FastAPI)

```python
@app.exception_handler(ResourceNotFoundError)
async def not_found_handler(request: Request, exc: ResourceNotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"error_code": exc.error_code, "message": str(exc)},
    )

@app.exception_handler(AuthorizationError)
async def authorization_handler(request: Request, exc: AuthorizationError) -> JSONResponse:
    return JSONResponse(status_code=403, content={"error_code": exc.error_code})

@app.exception_handler(GovernanceViolationError)
async def governance_handler(request: Request, exc: GovernanceViolationError) -> JSONResponse:
    # Governance violations są logowane jako WARNING z pełnym kontekstem
    logger.warning("governance.violation", error_code=exc.error_code)
    return JSONResponse(status_code=400, content={"error_code": exc.error_code})
```

### 10.4 Zasada: błędy są wartościami w logice domenowej

Dla operacji z przewidywalnym niepowodzeniem (retrieval bez wyników, validation failure) preferuj zwracanie Result type zamiast wyjątku:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class RetrievalResult:
    chunks: list[RetrievedChunk]
    has_context: bool
    refusal_reason: str | None = None  # Ustawione gdy has_context=False

# Użycie — brak wyjątku dla normalnego "brak wyników"
result = await retrieval_service.retrieve(query_embedding)
if not result.has_context:
    return QueryResponse(answer=None, refusal_reason=result.refusal_reason)
```
