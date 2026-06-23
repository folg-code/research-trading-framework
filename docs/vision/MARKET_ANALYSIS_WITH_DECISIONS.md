# Trading Research Framework

# SPRINT 003 — Market Analysis Architecture and MVP Planning Note

> **Related:** For derived analytical data, workspace, result store, consumer views, and
> `AnalysisFrame` assembly see [`ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md`](ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md).
> Where the two documents conflict on workspace or derived-data topics, the workspace
> document takes precedence (it is the newer specification).

## 1. Purpose

Sprint 003 dotyczy jednego z najbardziej krytycznych obszarów frameworka: **Market Analysis**.

Warstwa ta będzie odpowiadać za wydajne, reużywalne i deterministyczne obliczanie:

- Market Features,
- Market Structures,
- Market States,
- zależności między komponentami,
- cache,
- lineage,
- metadata dotyczących warm-up, causalności i dostępności wyników.

Ze względu na wpływ tej warstwy na cały dalszy rozwój frameworka, implementacja nie powinna rozpocząć się przed zamknięciem kluczowych decyzji architektonicznych i wykonaniem technicznego proof of concept.

---

## 2. Strategic Context

Market Analysis będzie wykorzystywane przez:

- Signal Research,
- Strategy Research,
- Backtesting,
- Walk Forward Analysis,
- Monte Carlo,
- Strategy Execution,
- przyszłe Market Models,
- przyszłe Signal Models,
- analizy multitimeframe,
- komponenty użytkownika.

Błędy popełnione na tym poziomie mogą prowadzić do:

- powielania obliczeń,
- nadmiernego kopiowania danych,
- niekontrolowanego zużycia pamięci,
- błędów look-ahead,
- trudności z cache,
- niezgodności między bibliotekami,
- problemów z reprodukowalnością,
- konieczności przebudowy fundamentów w kolejnych sprintach.

Dlatego głównym celem nie jest stworzenie katalogu wskaźników, lecz zaprojektowanie stabilnych kontraktów i engine'u wykonawczego.

---

## 3. Sprint Goal

> Zaprojektować i zaimplementować minimalny, deterministyczny Market Analysis Engine, który potrafi rejestrować komponenty, rozwiązywać zależności, budować DAG, deduplikować wspólne obliczenia, wykonywać analizę batchową, zarządzać execution cache oraz zwracać wyniki z pełnym identity i lineage.

Sprint ma potwierdzić architekturę przez jeden kompletny vertical slice wykorzystujący zewnętrzną bibliotekę analityczną lub adapter obliczeniowy.

---

## 4. Core Architectural Principles

### 4.1. Market Analysis nie jest Market Model

Market Analysis dostarcza:

- Feature,
- Structure,
- State.

Market Model jest deklaratywną kompozycją tych elementów i należy do warstwy Strategy.

```text
Market Data
    ↓
Market Analysis
    ├── Features
    ├── Structures
    └── States
          ↓
Market Model
          ↓
Strategy
```

### 4.2. Semantyka jest oddzielona od implementacji

Komponent opisuje znaczenie analityczne:

```text
volatility.atr
```

Implementacja opisuje sposób wykonania:

```text
talib.atr
numpy.atr
custom.incremental_atr
```

TA-Lib lub inna biblioteka nie definiuje kontraktu frameworka. Jest tylko backendem wykonawczym.

### 4.3. Komponenty nie pobierają danych samodzielnie

Komponent analityczny nie może:

- otwierać plików Parquet,
- korzystać bezpośrednio z repository,
- pobierać danych od providera,
- wybierać instrumentu,
- rozszerzać zakresu danych,
- wykonywać ukrytego resamplingu.

Market Analysis korzysta z danych wyłącznie przez kontrakty Data Module.

### 4.4. Zależności są jawne

Komponent deklaruje osobno:

- zależności od surowych pól danych,
- zależności od innych komponentów.

Ukryte wywoływanie innych analiz wewnątrz `compute()` jest niedozwolone.

### 4.5. Input jest read-only

Komponent nie może mutować współdzielonego datasetu.

Wyniki są zwracane jako oddzielne obiekty.

### 4.6. MVP jest batchowe i single-timeframe

Pierwsza wersja:

- działa batchowo,
- wykonuje obliczenia sekwencyjnie,
- materializuje wynik w pamięci,
- nie implementuje multitimeframe,
- nie implementuje incremental execution,
- nie implementuje persistent cache.

Architektura nie może jednak blokować tych rozszerzeń w przyszłości.

---

## 5. Component Categories

Pierwsza wersja systemu powinna obsługiwać trzy kategorie:

```text
Feature
Structure
State
```

### Feature

Przykłady:

- ATR,
- RSI,
- returns,
- realized volatility,
- volume statistics.

### Structure

Przykłady:

- swing points,
- pivots,
- session ranges,
- liquidity levels,
- structural highs and lows.

### State

Przykłady:

- high volatility,
- low volatility,
- compression,
- bullish structure,
- bearish structure.

Ogólne operacje techniczne, takie jak `shift`, `rolling`, `diff`, `clip` lub `fillna`, nie powinny być publicznymi komponentami, chyba że posiadają samodzielne znaczenie analityczne lub istotną reużywalność.

---

## 6. Required Domain Contracts

Sprint powinien ustabilizować co najmniej następujące pojęcia:

```text
ComponentId
ComponentVersion
ImplementationId
ImplementationVersion
ComponentKind
ComponentRequest
ParameterSchema
ComponentDependency
DataDependency
OutputId
OutputSchema
AnalysisContext
AnalysisResult
ComputationIdentity
Lineage
HistoryRequirement
Causality
AvailabilityMetadata
```

### 6.1. ComponentRequest

Request opisuje intencję użytkownika lub innego komponentu.

```python
ComponentRequest(
    component_id="volatility.atr",
    parameters={"period": 14},
)
```

Request nie powinien zawierać:

- ścieżki do pliku,
- DataFrame,
- cache key,
- lineage,
- fizycznej wersji biblioteki.

### 6.2. ComputationIdentity

Computation identity opisuje faktyczne obliczenie.

Powinno uwzględniać co najmniej:

- component id,
- component version,
- implementation id,
- implementation version,
- znormalizowane parametry,
- dataset identity,
- timeframe,
- zakres danych,
- dependency identities.

`ComponentRequest` i `ComputationIdentity` są różnymi pojęciami.

### 6.3. Parameter Schema

Każdy komponent posiada typowany i walidowany schemat parametrów.

Parametry muszą być:

- deterministyczne,
- serializowalne,
- kanonizowane,
- możliwe do fingerprintowania,
- uzupełnione o wartości domyślne przed obliczeniem fingerprintu.

### 6.4. AnalysisResult

Wynik nie może być tylko pojedynczą serią.

Powinien obsługiwać:

- jeden lub wiele outputów,
- output schema,
- computation identity,
- lineage,
- valid range,
- warm-up metadata,
- availability metadata,
- diagnostics.

---

## 7. Dependency Graph and Execution Model

### 7.1. DAG

Węzłem DAG-u jest znormalizowany request obliczeniowy, a nie sama nazwa komponentu.

```text
ATR(14) != ATR(50)
```

Planner odpowiada za:

- rozwinięcie zależności,
- walidację requestów,
- wybór implementacji,
- deduplikację,
- wykrywanie cykli,
- topological sort,
- przygotowanie deterministycznego planu wykonania.

### 7.2. Lazy Execution

Engine oblicza wyłącznie:

- komponenty jawnie zażądane,
- ich wymagane zależności.

### 7.3. Shared Computation

Jeżeli dwa modele lub komponenty wymagają tego samego obliczenia, powinno ono zostać wykonane tylko raz w ramach jednego planu.

Przykład:

```text
Model A → ATR(14)
Model B → ATR(14)
```

wynik:

```text
ATR(14) wykonany jeden raz
```

Deduplikacja odbywa się po resolved computation identity.

---

## 8. Cache Strategy

### 8.1. Sprint Scope

Sprint 003 powinien wdrożyć wyłącznie:

- execution cache,
- exact-match reuse,
- cache in-memory,
- cache ograniczony do pojedynczego execution planu.

### 8.2. Out of Scope

Poza sprintem pozostają:

- persistent cache,
- cache między procesami,
- partial range reuse,
- prefix reuse,
- incremental append,
- chunk-level cache,
- DuckDB/Parquet result store.

Identity musi jednak zostać zaprojektowane tak, aby persistent cache można było dodać później bez zmiany podstawowych kontraktów.

---

## 9. Warm-up, Causality and Availability

### 9.1. Warm-up

Komponent powinien jawnie deklarować wymaganie historii:

```python
history_requirement(parameters) -> HistoryRequirement
```

Engine rozróżnia:

- requested range,
- computation range,
- returned range.

Komponent nie pobiera samodzielnie wcześniejszych danych.

### 9.2. Causality

Każdy komponent deklaruje jedną z kategorii:

```text
Causal
Delayed
Retrospective
```

Przykłady:

- ATR — causal,
- confirmed pivot — delayed,
- centered moving average — retrospective.

### 9.3. Availability

Model powinien rozróżniać:

- observation timestamp,
- computation timestamp,
- availability timestamp.

W pierwszym sprincie system może działać wyłącznie w single-timeframe, ale kontrakt nie powinien zakładać, że każda wartość jest dostępna dokładnie w timestampie obserwacji.

---

## 10. Data Contract and Performance

### 10.1. Data Boundary

Market Analysis otrzymuje `Published DatasetRef` i korzysta z warstwy dostępu Data Module.

Komponent nie zna:

- providera,
- storage,
- filesystemu,
- struktury katalogów,
- sposobu materializacji danych.

### 10.2. Analysis Data View

Należy zaprojektować lekki kontrakt widoku danych, który:

- udostępnia kolumny i indeks czasu,
- wspiera read-only access,
- pozwala unikać pełnych kopii,
- nie wiąże domeny na stałe z pandas,
- nie blokuje NumPy, Arrow lub Polars.

### 10.3. Performance Rules

MVP powinno przestrzegać następujących zasad:

- brak pełnych kopii datasetu per komponent,
- brak mutacji wejścia,
- materializacja wyłącznie outputów,
- sekwencyjne wykonanie,
- `float64` jako domyślny dtype dla researchu,
- deterministyczny plan wykonania,
- pomijalny narzut registry/planner/executor względem właściwych obliczeń.

---

## 11. External Libraries

### 11.1. Role of TA-Lib and Similar Libraries

Biblioteki zewnętrzne mogą dostarczać implementacje obliczeń:

```text
TA-Lib
NumPy
pandas
Polars
custom implementations
```

Nie powinny definiować kontraktów domenowych frameworka.

### 11.2. Optional Dependencies

TA-Lib i podobne biblioteki powinny być zależnościami opcjonalnymi.

Przykład:

```text
framework[talib]
framework[polars]
framework[analysis-all]
```

Brak opcjonalnego backendu nie może uniemożliwiać uruchomienia całego frameworka.

### 11.3. Registry Policy

Registry powinno wspierać:

- jedną lub wiele implementacji komponentu,
- implementację domyślną,
- jawny wybór backendu,
- priorytety,
- konflikt rejestracji,
- brak wymaganej zależności.

---

## 12. Recommended Vertical Slice

Vertical slice powinien testować pełny przepływ oraz zależności komponentowe.

Rekomendowany przykład:

```text
Published DatasetRef
    ↓
True Range Feature
    ↓
ATR Feature
    ↓
Volatility State
```

Przykład zależności:

```text
TrueRange
ATR(14)
HighVolatilityState
```

Ten slice powinien potwierdzić:

- raw data dependencies,
- component dependencies,
- registry,
- implementation resolution,
- DAG,
- cycle detection,
- topological sort,
- shared computation,
- execution cache,
- multi-output result contract,
- warm-up metadata,
- lineage,
- integration z `DatasetRef`.

ATR może korzystać z adaptera TA-Lib lub NumPy. Celem nie jest ręczne przepisywanie wskaźnika, lecz potwierdzenie kontraktów.

---

## 13. Technical Spike Before Contract Freeze

Przed finalnym zamrożeniem kontraktu danych należy wykonać mały benchmark techniczny.

### 13.1. Backends

Porównać co najmniej:

- NumPy,
- pandas,
- TA-Lib,
- opcjonalnie Polars.

### 13.2. Operations

Przetestować:

- ATR,
- EMA,
- rolling maximum,
- kilka niezależnych komponentów,
- współdzieloną zależność.

### 13.3. Dataset

Benchmark powinien używać danych zbliżonych do rzeczywistego obciążenia:

```text
NQ 1m
co najmniej 1 rok
preferowane 5–7 lat
```

### 13.4. Metrics

Mierzyć:

- wall-clock time,
- peak memory,
- koszt konwersji danych,
- koszt kopiowania,
- koszt adaptera,
- narzut registry/planner/executor,
- korzyść z reuse wspólnych zależności.

Kod spike'a nie musi wejść do produkcyjnego modułu.

---

## 14. Sprint Scope

### In Scope

- identity contracts,
- parameter contracts,
- request and result contracts,
- component protocol,
- implementation protocol,
- registry,
- dependency resolution,
- DAG,
- cycle detection,
- topological planning,
- sequential batch executor,
- execution cache,
- lineage,
- warm-up metadata,
- causality metadata,
- one external-library adapter,
- one component depending on another component,
- integration test from `DatasetRef` to final analysis result,
- contract test suite.

### Out of Scope

- complete indicator library,
- persistent cache,
- parallel execution,
- distributed execution,
- incremental execution,
- live state management,
- multitimeframe execution,
- automatic resampling,
- timeframe alignment,
- backward as-of joins,
- strategy composition,
- Market Model implementation,
- Signal Model implementation,
- GPU execution,
- final backend standardization.

---

## 15. Proposed Work Waves

### Wave 0 — Architecture Closure

- confirm domain boundaries,
- confirm component categories,
- confirm request/result contracts,
- confirm identity model,
- confirm cache scope,
- confirm warm-up and causality model,
- confirm single-timeframe constraint.

### Wave 1 — Identity and Core Contracts

- `ComponentId`,
- `ComponentVersion`,
- `ImplementationId`,
- `ImplementationVersion`,
- parameter canonicalization,
- `ComponentRequest`,
- `ComponentKind`,
- `AnalysisContext`,
- `AnalysisResult`,
- `HistoryRequirement`,
- `Causality`,
- `Lineage`.

### Wave 2 — Registry and Dependency Planner

- component registration,
- implementation resolution,
- dependency expansion,
- request normalization,
- cycle detection,
- topological sort,
- deterministic execution plan.

### Wave 3 — Executor and Cache

- sequential executor,
- read-only data view,
- dependency result injection,
- execution cache,
- output validation,
- error hierarchy.

### Wave 4 — Vertical Slice

- True Range Feature,
- ATR adapter,
- Volatility State,
- dependency reuse,
- lineage verification,
- warm-up verification.

### Wave 5 — Integration and Contract Tests

- `DatasetRef` integration,
- contract tests for adapters,
- deterministic identity tests,
- input immutability tests,
- output schema validation,
- cache reuse tests,
- cycle detection tests.

### Wave 6 — Documentation and Review

- update architecture documents,
- add ADR decisions,
- update `CURRENT_STATUS.md`,
- update technical debt and problem registry,
- close sprint review.

---

## 16. Definition of Ready

Sprint implementacyjny może rozpocząć się dopiero, gdy:

- granica Market Analysis została zatwierdzona,
- Feature / Structure / State zostały zdefiniowane,
- semantic identity i implementation identity są rozdzielone,
- request i computation identity są rozdzielone,
- parameter canonicalization jest określona,
- result contract obsługuje wiele outputów,
- dependency model jest jawny,
- warm-up i causality są częścią kontraktu,
- zakres cache MVP jest zamknięty,
- single-timeframe limitation jest jawna,
- technical spike nie wykazał krytycznych problemów z kopiowaniem lub konwersją danych,
- vertical slice został dokładnie określony.

---

## 17. Definition of Done

Sprint uznaje się za ukończony, gdy:

- komponenty mogą być rejestrowane i rozwiązywane przez registry,
- planner buduje deterministyczny DAG,
- cykle są wykrywane i raportowane,
- wspólne zależności są deduplikowane,
- executor wykonuje plan batchowo i sekwencyjnie,
- execution cache zapobiega powtórnym obliczeniom,
- wynik zawiera identity i lineage,
- komponent deklaruje warm-up i causality,
- wejściowy dataset nie jest mutowany,
- działa vertical slice `DatasetRef → True Range → ATR → Volatility State`,
- adapter zewnętrznej biblioteki przechodzi contract tests,
- dokumentacja architektoniczna i status projektu zostały zaktualizowane.

---

## 18. Main Risks

### Overengineering

Ryzyko stworzenia zbyt abstrakcyjnego engine'u przed potwierdzeniem realnych przypadków użycia.

**Mitigation:** minimalny vertical slice i techniczny spike.

### Premature Backend Lock-in

Ryzyko trwałego związania domeny z pandas lub TA-Lib.

**Mitigation:** neutralne kontrakty i adaptery backendowe.

### Hidden Copies

Ryzyko kopiowania dużych datasetów przy każdym komponencie.

**Mitigation:** read-only data view i benchmark pamięci.

### Incorrect Identity

Ryzyko użycia błędnego wyniku z cache.

**Mitigation:** rozdzielenie request identity, semantic identity i resolved computation identity.

### Look-ahead

Ryzyko używania wyników dostępnych dopiero w przyszłości.

**Mitigation:** causalność, confirmation delay i availability metadata od początku.

### Excessive DAG Granularity

Ryzyko tworzenia osobnego węzła dla każdej prostej operacji technicznej.

**Mitigation:** publiczny komponent tylko wtedy, gdy ma znaczenie analityczne lub reużywalność.

---

## 19. Key Decisions Summary

1. Market Analysis dostarcza Features, Structures i States.
2. Market Model i Signal Model pozostają deklaratywnymi kompozycjami wyższego poziomu.
3. Komponent semantyczny jest oddzielony od implementacji.
4. Zewnętrzne biblioteki są adapterami, nie fundamentem domeny.
5. Zależności są jawne i tworzą DAG.
6. Request i computation identity są różnymi pojęciami.
7. Input jest read-only.
8. Wynik jest ustandaryzowany i może zawierać wiele outputów.
9. Warm-up, causality i availability są częścią kontraktu.
10. MVP działa batchowo, sekwencyjnie i single-timeframe.
11. Cache MVP jest exact-match execution cache in-memory.
12. Multitimeframe, persistent cache i incremental execution są projektowane na przyszłość, ale nie implementowane w tym sprincie.
13. Sprint buduje engine i kontrakty, nie bibliotekę wskaźników.
14. Vertical slice musi zawierać przynajmniej jedną zależność komponentową.
15. Kontrakt danych musi zostać potwierdzony benchmarkiem przed zamrożeniem.

---

## 20. Final Recommendation

Sprint 003 powinien rozpocząć się od krótkiego etapu architecture closure i technical spike, a dopiero później przejść do implementacji.

Nie należy rozpoczynać od ręcznego implementowania ATR, RSI lub innych wskaźników.

Najważniejszym produktem sprintu powinien być stabilny i mierzalny Market Analysis Engine, do którego w przyszłości będzie można bezpiecznie podłączać:

- TA-Lib,
- NumPy,
- Polars,
- własne komponenty użytkownika,
- komponenty batchowe,
- komponenty incremental,
- analizy multitimeframe,
- trwały cache wyników.

## 15. Decision Register

Poniższe decyzje obowiązują dla Sprintu 003, chyba że zostaną jawnie zmienione w ADR przed rozpoczęciem implementacji.

### D-001 — Granica domeny

**Decyzja:** Market Analysis odpowiada za `Feature`, `Structure` i `State`. Nie odpowiada za Market Model, Signal Model, Strategy ani logikę wejścia/wyjścia.

**Konsekwencja:** komponent analityczny nie generuje decyzji tradingowych i nie zna strategii.

### D-002 — Kategorie komponentów

**Decyzja:** publiczne kategorie MVP to `Feature`, `Structure` i `State`.

**Konsekwencja:** ogólne operacje techniczne, takie jak `shift`, `rolling`, `clip` i `fillna`, pozostają detalami implementacji, o ile nie mają niezależnej wartości analitycznej i reużywalności.

### D-003 — Granularność komponentów

**Decyzja:** osobnym komponentem jest element, który posiada samodzielne znaczenie analityczne i spełnia co najmniej jedno z kryteriów: jest reużywalny, kosztowny, zależny od innych komponentów lub opłacalny do osobnego cache.

**Konsekwencja:** nie rozbijamy każdego wskaźnika na mikrowęzły. `True Range` może być osobnym komponentem, ale `shift(1)` nie.

### D-004 — Semantyka i implementacja

**Decyzja:** `ComponentId` opisuje semantykę, a `ImplementationId` sposób wykonania.

```text
component_id: volatility.atr
implementation_id: talib.atr
```

**Konsekwencja:** wiele implementacji może realizować ten sam komponent semantyczny, ale nie współdzielą automatycznie tego samego cache.

### D-005 — Biblioteki zewnętrzne

**Decyzja:** TA-Lib i podobne biblioteki są opcjonalnymi backendami, nie częścią domenowego kontraktu.

**Konsekwencja:** brak TA-Lib nie może blokować działania frameworka; adaptery będą instalowane jako extras.

### D-006 — Request a identity wykonania

**Decyzja:** `ComponentRequest` opisuje intencję, a `ComputationIdentity` faktyczne, rozwiązane wykonanie.

**Konsekwencja:** request nie zawiera fizycznej wersji biblioteki, dataset fingerprintu ani cache key. Te elementy powstają dopiero po rozwiązaniu requestu.

### D-007 — Parametry

**Decyzja:** każdy komponent posiada typowany, walidowany i immutable schemat parametrów. Surowy `dict[str, Any]` jest dopuszczalny wyłącznie na granicy API.

**Konsekwencja:** fingerprint parametrów powstaje po walidacji, uzupełnieniu wartości domyślnych i kanonizacji.

### D-008 — Zależności

**Decyzja:** zależności od danych i innych komponentów są deklarowane jawnie i oddzielnie.

**Konsekwencja:** komponent nie może ukrywać wywołań innych komponentów wewnątrz `compute()`.

### D-009 — Zależności dynamiczne

**Decyzja:** zależności mogą zależeć od parametrów, ale muszą być deterministyczne.

**Konsekwencja:** planner rozwija zależności po walidacji parametrów.

### D-010 — Registry

**Decyzja:** registry może przechowywać wiele implementacji tego samego `ComponentId` i rozwiązuje implementację według jawnego wyboru albo polityki domyślnej.

**Konsekwencja:** konflikt domyślnej implementacji jest błędem konfiguracji, a nie cichym wyborem.

### D-011 — Kontrakt danych

**Decyzja:** komponent nie otrzymuje repository, ścieżki do pliku ani `DatasetRef`. Otrzymuje read-only `AnalysisDataView` przygotowany przez engine.

**Konsekwencja:** engine odpowiada za materializację danych, wybór kolumn i zakres obliczeniowy.

### D-012 — Neutralność technologiczna

**Decyzja:** domenowy kontrakt nie zależy bezpośrednio od pandas, Polars ani TA-Lib.

**Konsekwencja:** MVP może wykorzystywać NumPy/pandas w adapterach, ale publiczny kontrakt musi pozwalać na inne reprezentacje bez przebudowy domeny.

### D-013 — Mutowalność

**Decyzja:** input jest read-only, a komponenty batchowe są stateless.

**Konsekwencja:** komponent nie dopisuje kolumn do wspólnego DataFrame i nie przechowuje stanu między uruchomieniami.

### D-014 — Wynik

**Decyzja:** komponent zwraca `AnalysisResult`, który obsługuje jeden lub wiele outputów.

**Konsekwencja:** wynik zawiera output schema, identity, lineage, valid range, warm-up, availability metadata i diagnostics.

### D-015 — Nazwy outputów

**Decyzja:** output ma stabilny semantyczny `OutputId`; nazwy typu `atr_14` są wyłącznie aliasami prezentacyjnymi.

**Konsekwencja:** parametry nie są kodowane jako jedyne identity kolumny.

### D-016 — DAG

**Decyzja:** planner i executor są oddzielnymi elementami. Węzłem DAG-u jest rozwiązane obliczenie, nie sama nazwa komponentu.

**Konsekwencja:** `ATR(14)` i `ATR(50)` są różnymi węzłami; identyczne zależności są deduplikowane.

### D-017 — Lazy execution

**Decyzja:** engine wykonuje tylko jawnie zażądane komponenty i ich zależności.

**Konsekwencja:** rejestracja komponentu nie powoduje jego obliczenia.

### D-018 — Cache MVP

**Decyzja:** Sprint 003 implementuje wyłącznie exact-match execution cache in-memory w ramach pojedynczego planu.

**Konsekwencja:** brak persistent cache, reuse zakresów, chunk cache i cache między procesami.

### D-019 — Tożsamość datasetu

**Decyzja:** identity wejścia pochodzi z opublikowanego `DatasetRef` i kontraktu Data Module, nie ze ścieżki do pliku.

**Konsekwencja:** analiza nie tworzy własnej, niezależnej definicji tożsamości danych.

### D-020 — Warm-up

**Decyzja:** każdy komponent deklaruje `HistoryRequirement`; engine rozszerza zakres wejściowy i przycina wynik do zakresu żądanego.

**Konsekwencja:** adapter nie pobiera sam wcześniejszych danych i nie ukrywa warm-up.

### D-021 — Causalność

**Decyzja:** komponent deklaruje jedną z kategorii: `Causal`, `Delayed`, `Retrospective`.

**Konsekwencja:** workflow może odrzucić komponent niedopuszczalny w backteście lub execution.

### D-022 — Dostępność wyniku

**Decyzja:** kontrakt przewiduje `available_at`, nawet jeżeli MVP działa single-timeframe.

**Konsekwencja:** nie zakładamy, że timestamp obserwacji zawsze jest równy momentowi dostępności wyniku.

### D-023 — Batch i incremental

**Decyzja:** Sprint 003 implementuje wyłącznie `BatchAnalysisComponent`. Przyszły incremental execution będzie osobnym kontraktem wykonawczym opartym na tej samej semantyce komponentu.

**Konsekwencja:** nie rozbudowujemy `compute()` o stan live.

### D-024 — Determinizm

**Decyzja:** komponenty batchowe są deterministyczne domyślnie.

**Konsekwencja:** komponent niedeterministyczny wymaga jawnego seed, dodatkowego identity i może zostać wyłączony z cache.

### D-025 — Walidacja wyniku

**Decyzja:** executor waliduje długość, indeks, output schema i podstawowe typy wyniku.

**Konsekwencja:** adapter nie jest traktowany jako bezwarunkowo zaufany.

### D-026 — Lineage

**Decyzja:** lineage jest obowiązkową częścią rezultatu.

**Konsekwencja:** zapisujemy dataset identity, component identity, implementation identity, parametry, dependency identities, engine version i czas wykonania.

### D-027 — Dtype

**Decyzja:** domyślnym dtype dla obliczeń researchowych w MVP jest `float64`.

**Konsekwencja:** `float32` może zostać wprowadzone dopiero po benchmarkach i z jawną polityką tolerancji numerycznej.

### D-028 — Model wykonania

**Decyzja:** executor MVP jest sekwencyjny i materializuje wyniki w pamięci.

**Konsekwencja:** brak multiprocessing, distributed execution, lazy arrays i streamingu wyników w Sprint 003.

### D-029 — Multitimeframe

**Decyzja:** Sprint 003 nie implementuje multitimeframe. Model musi jednak przewidywać `source`, `computation` i `evaluation timeframe`.

**Konsekwencja:** MVP wymusza `source = computation = evaluation` i odrzuca inne konfiguracje.

### D-030 — Resampling i alignment

**Decyzja:** resampling oraz alignment nie są odpowiedzialnością komponentu Feature/Structure/State.

**Konsekwencja:** w przyszłości będą jawnymi węzłami lub etapami planu. Ukryty resampling jest zabroniony.

### D-031 — User-defined components

**Decyzja:** komponenty użytkownika korzystają z tego samego kontraktu co komponenty core.

**Konsekwencja:** nie powstaje osobny uproszczony engine dla `user_data`.

### D-032 — Publiczne API

**Decyzja:** publiczne API MVP obejmuje request, parameter schema, component protocol, result schema, registry interface i facade engine'u.

**Konsekwencja:** reprezentacja DAG-u, implementacja cache i wewnętrzne adaptery pozostają prywatne.

### D-033 — Testy kontraktowe

**Decyzja:** każdy adapter musi przejść wspólny contract test suite.

**Konsekwencja:** testujemy determinizm, identity, immutability inputu, output schema, warm-up, lineage i zgodność indeksu.

### D-034 — Zgodność implementacji

**Decyzja:** różne implementacje tego samego komponentu nie muszą być bitowo identyczne, ale muszą spełniać zdefiniowany kontrakt semantyczny i tolerancje numeryczne.

**Konsekwencja:** reference datasets oraz tolerancje są częścią testów adapterów.

### D-035 — Vertical slice

**Decyzja:** minimalny vertical slice to `True Range → ATR → Volatility State` z wejściem pochodzącym z `DatasetRef`.

**Konsekwencja:** sprint testuje zarówno raw data dependencies, jak i component dependencies. Pojedynczy ATR bez zależności jest niewystarczający.

### D-036 — Benchmark przed zamrożeniem data view

**Decyzja:** przed finalnym zamrożeniem `AnalysisDataView` wykonujemy spike porównujący NumPy, pandas, TA-Lib i opcjonalnie Polars.

**Konsekwencja:** kontrakt danych nie jest zatwierdzany wyłącznie na podstawie estetyki API.

---

## 16. Decisions Deferred Beyond Sprint 003

Poniższe decyzje są świadomie odłożone:

- format persistent cache,
- polityka partial-range reuse,
- incremental state storage,
- równoległe wykonanie DAG-u,
- distributed execution,
- chunked execution,
- finalny backend kolumnowy,
- GPU support,
- pełny model multitimeframe,
- resampling nodes,
- backward as-of alignment,
- strategia łączenia wyników wielu timeframe'ów,
- Market Model execution,
- Signal Model execution.

Odłożenie tych tematów nie oznacza, że kontrakty mogą je blokować. Oznacza jedynie, że nie będą implementowane ani w pełni rozstrzygane w Sprint 003.

---

## 17. ADR Required Before Implementation

Przed rozpoczęciem prac implementacyjnych należy zatwierdzić co najmniej:

```text
ADR-MA-001 — Market Analysis domain boundaries
ADR-MA-002 — Component and implementation identity
ADR-MA-003 — Parameter canonicalization and fingerprinting
ADR-MA-004 — AnalysisDataView and data ownership
ADR-MA-005 — AnalysisResult and output identity
ADR-MA-006 — Dependency DAG and execution planning
ADR-MA-007 — Analysis workspace and derived data materialization (see ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md)
ADR-MA-008 — Cache identity and cache scope
ADR-MA-009 — Warm-up, causality and availability
ADR-MA-010 — External analytical libraries
ADR-MA-011 — Batch versus incremental execution
```

ADR mogą być krótkie, ale każdy powinien zawierać:

- kontekst,
- przyjętą decyzję,
- odrzucone alternatywy,
- konsekwencje,
- warunki ponownego otwarcia decyzji.

---

## 18. Entry Criteria for Sprint 003 Implementation

Sprint może wejść w implementację dopiero, gdy:

- wszystkie decyzje D-001–D-036 są zaakceptowane albo jawnie oznaczone jako otwarte,
- ADR wymagane dla Wave 1 są zatwierdzone,
- `AnalysisDataView` zostało sprawdzone w spike'u,
- ustalono minimalny benchmark dataset,
- ustalono reference outputs dla vertical slice,
- ustalono sposób pozyskania identity z `DatasetRef`,
- zakres sprintu został rozpisany na PR-y,
- `CURRENT_STATUS.md` i roadmapa zostały zaktualizowane.

---

## 19. Recommended PR Breakdown

```text
PR 1 — Market Analysis ADR and domain contracts
PR 2 — Identity, parameters and request contracts
PR 3 — Result, lineage, warm-up and causality contracts
PR 4 — Registry and implementation resolution
PR 5 — Dependency planner, DAG and cycle detection
PR 6 — Sequential executor and execution cache
PR 7 — AnalysisDataView integration with Data Module
PR 8 — True Range adapter and contract tests
PR 9 — ATR adapter and shared dependency reuse
PR 10 — Volatility State and full vertical slice
PR 11 — Benchmark report, documentation and sprint closure
```

Każdy PR trafia do brancha sprintowego, a dopiero ukończony branch sprintowy jest mergowany do `main`.

---

## 20. Definition of Ready

Sprint 003 jest gotowy do rozpoczęcia, gdy:

- cel sprintu jest jednoznaczny,
- decyzje architektoniczne są zapisane,
- brak otwartych pytań blokujących kontrakty,
- benchmark potwierdza wykonalność data contract,
- vertical slice jest zdefiniowany,
- zakres in/out jest zamrożony,
- PR-y i kolejność zależności są ustalone.

---

## 21. Definition of Done

Sprint 003 jest ukończony, gdy framework potrafi przeprowadzić deterministyczny przepływ:

```text
Published DatasetRef
    ↓
AnalysisDataView
    ↓
ComponentRequest
    ↓
Implementation Resolution
    ↓
Dependency DAG
    ↓
Sequential Execution
    ↓
Shared Computation and Execution Cache
    ↓
AnalysisResult
    ↓
Identity, Lineage, Warm-up and Availability Metadata
```

oraz gdy działa vertical slice:

```text
True Range
    ↓
ATR
    ↓
Volatility State
```

z pełnymi testami kontraktowymi, integracyjnymi i benchmarkiem narzutu engine'u.
