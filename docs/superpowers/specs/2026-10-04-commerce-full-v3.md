# SENLIS full catalogue commerce v3

User authorization: update the discovery method, start searching the whole database, add waiting between site requests to reduce timeouts, and report an average completion estimate.

Scope: every one of the 174259 manifest IDs; no Turkey-brand exclusion. Outputs retain product variants, price currency, volume, stock, source and checked time. This is a commerce sidecar keyed by product ID, preserving the existing catalogue.

Design: autonomous public web discovery plus source/known-link seeds, exact product-page verification, a polite HTTP client, durable append-only checkpoints and bounded GitHub Actions batches. No API subscription or keys are added. Search snippets never become prices. Existing 10-product observations provide URLs and identity overrides only, never reused prices.

Rate control: 4 fixed lanes, host-specific shared time slots (2.5 seconds, jitter up to 0.4 seconds) and per-host serialization within each lane. This leaves at least 2 seconds between requests to the same host across this run. Each lane has 2 workers. 429/503 Retry-After is honored; transient errors back off 30/60/120... seconds; challenge/403 responses cool down for at least 15 minutes. No CAPTCHA bypass or proxy rotation. Redirects are paced and private addresses are rejected.

Execution: 48 sequential waves, 4 shards per wave (192 shards total), each under GitHub's six-hour job limit. Each shard scans about 908 records with a five-hour soft deadline. Incomplete/blocked work stays deferred and is not counted as not-found or completed research. Records checkpoint every 50 completions or 5 minutes; rerunning resumes terminal records. Outputs also upload as artifacts. An initial live canary verifies both search relevance and product-page price extraction before the waves start.

Completion: actual workflow queued/running with its first batch observed; not a claim that 174259 searches have completed. ETA is a range based on search volume, polite throughput and the first measured rate. Report progress, remaining records and the run link.
