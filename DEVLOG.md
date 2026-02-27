# 📓 Devlog — Konrad

Automatyczne dzienne podsumowania pracy z projektów.

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
