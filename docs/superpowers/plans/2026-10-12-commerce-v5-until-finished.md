# SENLIS v5 rolling queue implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Drain the existing pending queue automatically without fixed-slot exhaustion.

**Architecture:** A separate controller validates the pinned scanner and published checkpoint, runs one paced worker, and dispatches a successor only after success. The bootstrap only validates and dispatches; the terminal handoff exports and stops.

**Tech Stack:** Python standard library, unchanged v5 runtime, GitHub Actions and REST dispatch.

**Spec:** docs/superpowers/specs/2026-10-12-commerce-v5-until-finished.md

## Global Constraints

- Runtime d9a1976433016e65a4afcad7189adb6a14b65caf; data/commerce-v5-20261007; scope 174259.
- Feature branch only; same campaign, identities, evidence, attempt caps and cooldowns.
- Global concurrency senlis-commerce-global-v5; cancel-in-progress false.
- Finished with gaps is terminal; never equate catalogue completeness with prices.

## Review Focus

- Ambiguous dispatch response: do not repeat POST automatically or spawn duplicates.
- Changed branch/code or checkpoint rollback: fail before scanning or dispatch.
- All remaining work in cooldown: preserve it without resetting attempts.
- Finished but incomplete source coverage: export and stop, not loop forever.
- Growing database exports: reconstructable chunks below Git's file-size ceiling.

### Task 1: Controller, workflow, and operational record

**Files:** Create tools/commerce_v5_queue.py, tests/commerce_v5_queue/test_queue.py,
.github/workflows/commerce-queue-v5.yml, tools/commerce_v5_queue_trigger.txt;
append docs/COMMERCE_V5_PROGRESS.md.

**Interfaces:** Controller CLI `scan|handoff --runtime PATH --state PATH`; exported
`queue_action(summary)`, `verify_progress(before, after)`,
`pack_exports(root, limit, chunk_size)` and `dispatch_next(api, context)`.

- [x] Write failing tests for inconsistent summaries, growing/preserved queue,
  zero pending with gaps, export round trip, duplicate handoff, ambiguous POST,
  and invalid controller/runtime/checkpoint guards.
- [x] Run `python -m unittest discover -s tests/commerce_v5_queue -q`; expect missing controller failure.
- [x] Implement the controller and separate-checkout workflow, pinned runtime,
  serial execution, success-only handoff and recovery artifacts.
- [x] Run new tests and existing v3/v4/v5 suites; expect all pass. Validate YAML.
- [x] Review the change independently and fix consequential findings.
- [ ] Commit and publish the authorized feature-branch trigger with a ref lease.
- [ ] Verify bootstrap success, dispatched worker running and advancing durable
  events. Update the existing SENLIS watcher to this workflow and runtime.

Execution is already authorized by Can's queue-until-finished instruction.
