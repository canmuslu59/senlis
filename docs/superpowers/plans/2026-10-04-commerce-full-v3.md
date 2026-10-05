# SENLIS Full Commerce v3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Start autonomous, resumable purchase-link and price discovery over all 174259 records with site delays.

**Architecture:** Dedicated v3 code and workflow on an isolated feature branch. Preserve legacy matching tests, add strict product-page extraction and globally staggered lanes, and save append-only result chunks to a data branch. A live canary gates 48 waves and a final CSV/SQLite merge.

**Tech Stack:** Python 3.12, requests, BeautifulSoup, rapidfuzz, GitHub Actions and GitHub Contents API.

**Spec:** docs/superpowers/specs/2026-10-04-commerce-full-v3.md

## Global Constraints

- All 174259 IDs are included; never replace unavailable work with not_found.
- 4 lanes, 2 workers per lane; 2.5-second host slots with at most 0.4-second jitter.
- HTTP timeouts, Retry-After, 15-minute challenge cooldown, bounded retries and five-hour soft deadlines.
- Prices require matched product-page evidence and TRY; no search-snippet or stale seed prices.
- Preserve the main branch and existing data; use a separate feature and results branch.

## Review Focus

- Multiple lanes hitting the same domain must preserve the minimum interval, including redirects.
- Currency/form/gender/short-name ambiguity must not create verified wrong prices.
- Entirely blocked providers must produce deferred work, not a successful empty full scan.
- Interrupted or repeated jobs must resume without dropping records or duplicating progress.
- One failed wave and partially missing artifacts must not create a misleading completed output.

### Task 1: Polite discovery and offer validation

**Files:** tools/commerce_v3_http.py; tools/commerce_v3_engine.py; tests/commerce_v3/test_engine.py; data/commerce_v3_seeds.json.

**Interfaces:** `PoliteClient.fetch(url, params=None)` returns response/error metadata. `Engine.discover(row)` returns a per-ID result with status and provenance.

- [x] Write and run failing tests for cross-lane slots, retry dates, private URLs, main-product JSON-LD selection, currency and variant conflicts, query normalization and challenge detection.
- [x] Implement the client, source/known-link seeds, free HTML search adapters, reviewed retailer search fallback, and page parsing.
- [x] Run `python3 -m unittest discover -s tests/commerce_v3 -v`; expected no failures. Run existing `tools/matching_regression_test.py`; expected 40 matching cases plus helpers/index pass.
- [x] Commit Task 1 with test evidence in the progress ledger.

### Task 2: Full-catalogue runner and durable resume

**Files:** tools/commerce_full_v3.py; tests/commerce_v3/test_runner.py.

**Interfaces:** CLI commands `canary`, `worker`, `merge`; atomic local JSONL/CSV summaries; GitHub data-branch chunks keyed by shard and content hash.

- [x] Write and run failing tests for complete shard coverage, immutable checkpoint replay, deferred retry, no false completion and merge preserving missing IDs.
- [x] Implement bounded worker scheduling, checkpoints, resume, progress/ETA and CSV/SQLite merge.
- [x] Run the complete new suite and a real 10-product canary. Expected: relevant live search response and at least two live page prices; report actual coverage without inheriting the manual 7/10 claim.
- [x] Commit Task 2 and record measured evidence.

### Task 3: GitHub orchestration and launch

**Files:** .github/workflows/commerce-full-v3.yml; .github/workflows/commerce-full-v3-batch.yml; tools/commerce_full_v3_trigger.txt; docs/COMMERCE_V3_RUNBOOK.md.

**Interfaces:** preflight/live canary, 48 ordered waves with 4 lanes, always-upload artifacts, final merge, result branch `data/commerce-v3-20261004`.

- [x] Validate generated workflow graph for all 192 shard IDs, correct dependencies, timeouts and upload-on-failure behavior.
- [x] Run all tests; obtain the required fresh whole-change review and fix material issues with regression tests.
- [ ] Push the authorized feature branch, verify preflight/canary and the first full wave actually start, and report the measured/estimated runtime with limits.
