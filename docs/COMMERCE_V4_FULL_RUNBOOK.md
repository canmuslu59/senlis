# SENLIS — Full evidence campaign

Scope: every one of the 174259 database identities is searched in applicable catalogues from Perfume Point, Yes Parfümeri, Caudalie, MAD and INNATIVE. This is named-source coverage, not a global Internet search. The old v3 queue remains paused.

The prepare job reruns the 10-product live gate, requires five known correct price identities and both negative controls, then saves source snapshots, all-row query proofs and the deduplicated page queue. Partial source catalogues block launch. Matrix workers are serial (`max-parallel: 1`); part numbers are labels, and each worker takes the next pending work from the latest shared checkpoint, so matrix dispatch order is immaterial.

There are 24 worker slots of at most 90 script minutes (100 job minutes), then an export job. Jobs return immediately when all pages have reached a final outcome. One successful run should take about 12–18 hours at the observed 6867-page workload. The maximum scheduled worker budget is 36 hours; rate limits and repeated outages can leave explicit unresolved entries.

Same-host requests are paced on 6-second slots with jitter. Timeouts and HTTP throttles retain evidence, wait according to cooldown/Retry-After, and get up to three real attempts. A skipped cooldown is not an attempt. Failed pages never become catalogue absence. Every candidate URL is recorded and checked without the pilot's eight-page cap.

State: branch `data/commerce-v4-20261005`, folder `data/commerce_v4/20261005`. Git checkpoints occur every 50 page records or 5 minutes, on worker exit, and before/after export. Compressed page bodies are saved with their SHA-256 identifiers. Reuse of responses is bounded to this campaign and original timestamps remain attached to each accepted offer.

`summary.json` is the current checkpoint: search proofs, candidate coverage, completed/pending page counts, unresolved errors, verified-price products, and a measured remaining-time estimate. `finished` means no scheduled page attempts remain; `complete` also requires zero unresolved pages. The report job fails visibly when pending or unresolved pages remain, while still publishing partial results.

Outputs: `results.jsonl.gz`, `results.csv.gz`, `commerce_v4.sqlite.gz`, all-row `queries.jsonl.gz`, `pages.jsonl.gz`, immutable source evidence in `bootstrap/`, HTTP event log and raw gzip responses, append-only page decisions in `checks/`. This is a database supplement; app main/live data are not overwritten.

To resume a failed scan job, rerun that job at the same workflow commit; it reads the latest data branch checkpoint. Campaign code and plan hashes are checked. A new code version requires a new campaign identifier/branch rather than silently mixing methods. Do not reinitialize an existing campaign.

A failed checkpoint push raises a fatal worker error and fail-fast stops the remaining matrix. Ordinary HTTP failures are recorded/retried inside a successful worker. This prevents restarting from stale remote state after a broken persistence handoff.

Verified legacy manifest repair: 132 chunk-boundary rows contain a duplicated next row appended to source_url/extra CSV columns. Repair is allowed only when all four extra values match the separately present next ID and its appended ID suffix matches. All IDs 1..174259 are present; no identity is dropped. Repairs are listed in manifest_repairs.json; unexplained overflow blocks launch.

Deferred minor: successful bootstrap pages can be requested once again when the full worker queue starts. Worker-to-worker successful-page reuse is durable; bootstrap and worker evidence retain their distinct timestamps.
