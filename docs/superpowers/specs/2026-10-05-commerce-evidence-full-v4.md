# SENLIS v4 full database catalogue scan

User authorization: 2026-10-05, prepare and immediately start a sequential full scan if ready, with site waits. The approved evidence method extends from 10 pilot targets to all 174259 immutable manifest rows. Named-source scope remains the same five catalogues, not a global Internet absence claim. Main remains unchanged.

Read all five catalogues once in a fresh live pilot. Require all ten searches proven, both negative controls rejected and the five known price-bearing canary products accepted. Fix Caudalie category-prefixed H1 and Innative sole offer variant ID narrowly; preserve brand/form/gender/volume and differing-variant rejection.

Build a token inverted index and record every row's exact source queries, catalogue hashes, and full candidate URL lists. Empty name tokens use the eponymous product name. Deduplicate page fetches across products; impose no eight-candidate cap in the full scan. Only candidate pages are fetched. Missing/partial sources block the full run.

GitHub: one prepare job, 24 sequential worker slots (max-parallel 1, fail-fast true), each up to 90 minutes script/100 minutes job, then a report job. State and raw gzip response evidence persist in a dedicated data/commerce-v4-20261005 branch every 50 pages or 5 minutes and at each worker exit. Each worker restores checkpoint state and host cooldowns; no writes to main or live database. All jobs finish quickly after no pending pages remain. New full workflow has its own trigger/concurrency group; old v3 queue stays paused.

Use >=6 seconds per-host start spacing with jitter, 25-second read timeout, at most three real attempts per page, exponential cooldown and Retry-After. Cooldown/deadline skips are not attempts. HTTP failures are never no_catalog_match; unresolved failures are reported separately. Successful page evidence and decisions are reused throughout this campaign, not fetched for each matching row.

Output: all-row gzip JSONL/CSV and compressed SQLite supplement, progress summary, source/hash/query evidence, response archives. Product search progress, page verification progress, price coverage and unresolved errors are separate counters. A finished attempt is not complete when errors remain. Readable GitHub step summaries expose remaining pages and measured ETA.
