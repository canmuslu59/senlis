# SENLIS commerce v5 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Start a tested, resumable scan including Trendyol and verifiable official sources, retaining TRY/EUR/USD evidence.
**Architecture:** Separate parser, discovery and durable SQLite queue/CLI modules. Existing v4 evidence supplies candidate URLs only; prices require new observations.
**Tech Stack:** Python 3.12, requests/BeautifulSoup, SQLite, GitHub Actions.
**Spec:** docs/superpowers/specs/2026-10-07-commerce-global-v5.md

## Global Constraints
- 174259 existing identities; main, identities and old campaigns unchanged.
- Serial workers; minimum 6 seconds per host; honor Retry-After; max 3 attempts.
- Immutable campaign SHA/manifest; checkpoint push failure stops the queue.
- TRY/EUR/USD stay separate with market and evidence; no inferred global absence.

## Review Focus
- Recommendations and secondary offers must not override the main product.
- Unknown bottle size, conditional prices and mismatched selected variants remain unverified.
- Dynamic pagination/caps, blocked source and unknown official sites remain incomplete.
- Lost checkpoint and stale continuation must never silently reset work.
- Foreign price/stock must not count as Turkish availability.

### Task 1: Price evidence parser
**Files:** Create tools/commerce_v5_parser.py, tests/commerce_v5/test_parser.py and compact real fixtures.
**Interfaces:** verify_page(raw, url, row, source) -> dict(reason, offers, observations); money(value,currency) -> decimal string or None.
- [ ] Write failing real-regression/negative tests for Trendyol selection, EUR/USD, brand conflict, volume, product form and conditional prices.
- [ ] Run unittest discover -s tests/commerce_v5 -v; expect missing parser assertion failure.
- [ ] Implement conservative parser with explicit reason codes and all offer dimensions.
- [ ] Run v3/v4/v5 suites; expect all green. Commit.

### Task 2: Source discovery
**Files:** Create tools/commerce_v5_sources.py, data/commerce_v5_sources.json, tests/commerce_v5/test_sources.py.
**Interfaces:** initial_tasks(rows, old_pages, registry) -> tasks; discover(task, raw, final_url, rows, registry) -> (new tasks, audit); source_for(url,brand,registry) -> source or None.
- [ ] Write failing tests for directory matching, pagination, official-link verification, unsafe URLs and missing coverage.
- [ ] Run v5 tests, confirm relevant failures, implement discovery with explicit partial/blocked reporting.
- [ ] Run all commerce suites; expect green. Commit.

### Task 3: Durable queue and workflow
**Files:** Create tools/commerce_v5_state.py, tools/commerce_full_v5.py, tools/commerce_v5_pilot.py, tests/commerce_v5/test_runner.py, .github/workflows/commerce-full-v5.yml.
**Interfaces:** Store initializes immutable scope, enqueues deterministic tasks, atomically records decisions+discovered tasks, restores cooldowns and exports products/offers. CLI prepare/worker/report operates only v5 state branch.
- [ ] Write failing integration tests for restart, duplicate work, bounded failures, hash mismatch, product coverage and separate currency summaries.
- [ ] Implement queue/checkpoints and serial workflow with recovery artifacts and a fresh 10-product gate.
- [ ] Run full commerce suite plus local real-git push/restore integration; expect green. Commit.

### Task 4: Live gate and launch
**Files:** docs/COMMERCE_V5_PROGRESS.md, docs/COMMERCE_V5_LAUNCH.json.
**Interfaces:** Reviewed v5 code -> new feature/state branches -> GitHub run and verified durable checkpoint.
- [ ] Review whole change independently; reproduce and fix important findings with tests.
- [ ] Push feature and empty state branch using lease-safe GitHub tools, then push trigger.
- [ ] Verify live 10-product gate, scan queued/running, immutable checkpoint counts and honest time estimate.
- [ ] Record evidence/run links and report concrete completion/remaining limits.
