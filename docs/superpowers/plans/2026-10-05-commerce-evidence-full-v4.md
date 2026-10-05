# SENLIS v4 Full Scan Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline. One fresh whole-branch review before launch.

**Goal:** Search every database row with reproducible named-source evidence and start an automatic sequential GitHub queue.
**Architecture:** Extend v4 pilot discovery into an indexed plan and a resumable deduplicated page queue; git-backed campaign evidence supports handoff across jobs.
**Tech Stack:** Python 3.12, existing pinned requests/BeautifulSoup, gzip/SQLite, GitHub Actions.
**Spec:** docs/superpowers/specs/2026-10-05-commerce-evidence-full-v4.md

## Global Constraints
174259 rows; five named sources; old v3 queue paused; main unchanged; six-second spacing; three attempts; 24 serial worker slots; snapshot and query proof persisted; no global not-found inference.

## Review Focus
- Eponymous names and legacy URL/title disagreements must not silently disappear from searches.
- Same page shared by several rows must be fetched once yet verified independently per identity.
- A timeout followed by restart must retain attempt/cooldown state and never become a no-match.
- A checkpoint push failure must not claim remote persistence or advance a later worker silently.
- Partial catalogues or mismatched campaign manifests must block full launch.

### Task 1: Verification corrections
Files: tools/commerce_v3_engine.py, tests/commerce_v4/test_evidence.py.
- [x] Reproduce category-prefix/sole-variant rejections with archived HTML and failing tests.
- [x] Narrow fixes; preserve negative form, wrong vid and multiple offer protections.
- [x] Run 49 v3/v4 tests and replay both archived target pages.

### Task 2: Indexed queue and checkpoint runner
Files: tools/commerce_full_v4.py, tools/commerce_v4_state.py, tools/commerce_evidence_v4.py; tests/commerce_v4/test_full.py.
Interfaces: CatalogueIndex(source, report, entries).search(row); build_plan(rows,catalogues); eligible(job,check,now); summarize(plan,checks); prepare/worker/report CLI.
- [x] Failing tests: index agrees with literal matching; eponymous names; dedup shared page; incomplete source rejection; retry exhaustion and cooldown skip; resumed result preservation; stats distinguish error from absence.
- [x] Implement index and all-row queries, bounded retry queue, compressed append-only check records and response evidence, transactional git persistence.
- [x] Run regression suites and an offline restart simulation over real catalogue evidence.

### Task 3: Ordered GitHub execution and launch
Files: .github/workflows/commerce-full-v4.yml, tools/commerce_full_v4_trigger.txt, docs/COMMERCE_V4_FULL_RUNBOOK.md.
- [x] Tests enforce prepare gate, max-parallel 1, 24 slots, timeouts, always checkpoint/artifact handling and old queue paused.
- [x] One independent branch review; important findings get regression tests and one fix pass.
- [ ] Push code to feature branch, create separate data branch, trigger workflow; confirm live gate and queue start.
- [ ] Record run/commit and checkpoint state with measured ETA.
