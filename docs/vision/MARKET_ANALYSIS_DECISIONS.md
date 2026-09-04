# Trading Research Framework

# MARKET_ANALYSIS_DECISIONS.md

> **Binding decision register.** This file was split out of
> `docs/vision/MARKET_ANALYSIS_WITH_DECISIONS.md` (now dissolved,
> originally "SPRINT 003 — Market Analysis Architecture and MVP Planning
> Note") by Sprint 055 T008, keeping former §15 "Decision Register"
> (D-001–D-036) and former §16 "Decisions Deferred Beyond Sprint 003"
> verbatim. `docs/adr/README.md` declares D-001–D-036 authoritative, so the
> register stays in `docs/vision/`, separated from the closed Sprint-003
> planning-note body that surrounded it (see
> `docs/planning/sprints/SPRINT_003.md` and
> `docs/planning/sprints/S003_WAVE0_ARCHITECTURE_CLOSURE.md` for that
> planning-note content — it already exists there in English and near-
> identical form, so Sprint 055 T008 did not duplicate it into a new file;
> see Sprint 055's T008 execution notes for the comparison).
>
> **Language note:** the decision text below is in Polish, as in the
> original document. Sprint 055 T002/T004 explicitly scoped a Polish→English
> translation of this register as **out of scope** for Sprint 055 (a
> follow-up item) — translating it here would be new prose beyond a
> verbatim move.
>
> **F5 verification (Sprint 055 T004/T008):** T002 flagged a possible
> contradiction between D-018/D-028/D-029 and the later-accepted
> `ADR-MA-012`/`ADR-MA-014`. Verified by reading both ADRs in full: **D-029
> (no multitimeframe in Sprint 003) is confirmed superseded** by
> `ADR-MA-012` (ACCEPTED, Sprint 004) — see the status annotation on D-029
> below, newly-authored per D-S055-04 since this is new prose, not a move.
> **D-018 (execution-cache-only, exact-match, in-memory) and D-028
> (sequential executor, in-memory materialization) are NOT confirmed
> superseded**: `ADR-MA-012` adds additional cache *layers*
> (`ResampleCache`, `AlignmentCache`) alongside the execution cache but does
> not change its exact-match/in-memory nature, and `ADR-MA-014` explicitly
> states it is "authorization, not implementation" for a future Polars
> `MarketFrame` bulk/lazy engine — the sequential, in-memory executor D-028
> describes remains what is actually built as of this sprint. No annotation
> is added to D-018 or D-028 for this reason; this finding is recorded here
> instead so it is not silently re-verified from scratch later.

---

## Decision Register

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

> **Sprint 055 T008 (F5 verification):** not confirmed superseded — see the
> file-level F5 note above. `ADR-MA-012` adds `ResampleCache`/
> `AlignmentCache` layers alongside this execution cache but does not
> change its in-memory, exact-match nature.

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

> **Sprint 055 T008 (F5 verification):** not confirmed superseded — see the
> file-level F5 note above. `ADR-MA-014` authorizes a future Polars
> `MarketFrame` lazy/bulk engine but is explicitly "authorization, not
> implementation"; the sequential, in-memory executor this decision
> describes remains what is actually built.

### D-029 — Multitimeframe

**Decyzja:** Sprint 003 nie implementuje multitimeframe. Model musi jednak przewidywać `source`, `computation` i `evaluation timeframe`.

**Konsekwencja:** MVP wymusza `source = computation = evaluation` i odrzuca inne konfiguracje.

> **Superseded by `ADR-MA-012` (ACCEPTED, Sprint 004).** Sprint 004
> delivered batch multitimeframe computation: `RequestResolver` resolves
> distinct source/computation/evaluation timeframe roles,
> `ResolvedComponentRequest` allows `computation_timeframe` to differ from
> `evaluation_timeframe`, and `AlignmentPolicy.LAST_CLOSED_BAR` performs
> look-ahead-safe alignment via backward `join_asof`. The `source =
> computation = evaluation` constraint this decision records no longer
> holds as a hard MVP limitation. Newly-authored annotation per Sprint 055
> D-S055-04 (this is new prose, not a moved section).

### D-030 — Resampling i alignment

**Decyzja:** resampling oraz alignment nie są odpowiedzialnością komponentu Feature/Structure/State.

**Konsekwencja:** w przyszłości będą jawnymi węzłami lub etapami planu. Ukryty resampling jest zabroniony.

> **Sprint 055 T008 note:** this constraint held — `ADR-MA-012`
> implements resampling as an explicit `ResampleNode` execution DAG entry,
> not inside component `compute()`.

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

## Decisions Deferred Beyond Sprint 003

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

> **Sprint 055 T008 note:** several of these ("pełny model multitimeframe",
> "resampling nodes", "backward as-of alignment") were subsequently
> implemented in Sprint 004 per `ADR-MA-012` — see the D-029 annotation
> above. This list is left verbatim as the original deferral record; it is
> not re-edited item-by-item since the deferral itself (as a Sprint-003-time
> statement) is historically accurate.

---

## D → ADR Cross-Reference

*(Converted by Sprint 055 T008 from former §17 "ADR Required Before
Implementation." That section framed all 11 ADRs as a gate not yet closed;
Sprint 055 T002 (finding F1) confirmed all 11 exist in `docs/adr/` and are
ACCEPTED, plus two more (`ADR-MA-012`, `ADR-MA-014`) beyond the original
list — so the "required before implementation" framing is misleading and
is replaced here with a plain cross-reference table. This table itself is
newly-authored per D-S055-04, since it restates a relationship rather than
moving prose verbatim.)*

| Decision area (from the register above) | ADR | Status |
|---|---|---|
| Market Analysis domain boundaries (D-001–D-003) | `ADR-MA-001` | ACCEPTED |
| Component and implementation identity (D-004, D-006) | `ADR-MA-002` | ACCEPTED |
| Parameter canonicalization and fingerprinting (D-007) | `ADR-MA-003` | ACCEPTED |
| `AnalysisDataView` and data ownership (D-011, D-012, D-013) | `ADR-MA-004` | ACCEPTED |
| `AnalysisResult` and output identity (D-014, D-015) | `ADR-MA-005` | ACCEPTED |
| Dependency DAG and execution planning (D-016, D-017) | `ADR-MA-006` | ACCEPTED |
| Analysis workspace and derived-data materialization | `ADR-MA-007` | ACCEPTED (see `docs/reference/ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md`) |
| Cache identity and cache scope (D-018) | `ADR-MA-008` | ACCEPTED |
| Warm-up, causality and availability (D-020, D-021, D-022) | `ADR-MA-009` | ACCEPTED |
| External analytical libraries (D-005) | `ADR-MA-010` | ACCEPTED |
| Batch versus incremental execution (D-023, D-028) | `ADR-MA-011` | ACCEPTED |
| Batch multitimeframe computation with Polars (supersedes D-029, see annotation above) | `ADR-MA-012` | ACCEPTED |
| `MarketFrame` and Polars as the committed bulk engine (Stage 4 authorization) | `ADR-MA-014` | ACCEPTED |
