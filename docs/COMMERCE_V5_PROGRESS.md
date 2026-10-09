# SDD ledger — plan: docs/superpowers/plans/2026-10-07-commerce-global-v5.md
Baseline: v4 24 + v3 35 tests green; isolated feature/commerce-global-v5-20261006 checkout.
Pre-flight: parser produces offer/observation dictionaries consumed by queue; discovery produces task/audit dictionaries atomically stored by queue. No conflicts.
Pre-flight: pilot consumes the same parser/source policy as workers; immutable code SHA pins them. No conflicts.
Authorization: user explicitly requests fixing pipeline and launching new scan, and confirms continue on 2026-10-07; routine implementation and new campaign launch are authorized.
Task 1 complete: 15 v5 tests observed RED (missing parser), then GREEN. Real sanitized Trendyol, Innative, Yes and Caudalie fixtures. Existing 59 tests remain green. Brand conflict remains a review reason; rejected price observations are retained.
Task 2 complete: 9 discovery tests RED to GREEN (24 v5 total). Trendyol public A-Z directory fetched; robot exclusions explicitly cover redirected /sr/ brand routes. New products can still be found from public product-page related links, and 3294 existing Trendyol identity URLs seed checks. Official unknowns remain explicit; dynamic official confirmation requires a reference link plus matching Organization/Brand homepage evidence.
Task 3 implementation: 16 queue/CLI/policy tests added RED to GREEN, 40 v5 total. Real git checkpoint push/readback and branch/push failure gates passed. 174259-identity plan/restore passed in 12 seconds: 19234 initial tasks, 10505 page URLs (3290 unique Trendyol URLs), 8702 unknown-official reference tasks, 26 sitemap roots and public Trendyol directory. State persists append-only events, not rewritten SQLite blobs.
Live source observations: Trendyol A-Z directory has 14699 brand links, matching 565 existing database brands. 8159 unmatched brands are explicitly outside that directory, not proved unavailable in Turkey. Caudalie US price 42.00 USD/50ml is out of stock; this does not count as Turkish availability.

## Launch verification — 2026-10-08

One independent final review of edaaf0f..21e8efc completed. Eight Important findings were reproduced before fixes, then verified in one regression pass:

1. Secondary Product identifiers cannot lend their price to the primary page.
2. Conflicting explicit ProductGroup or selected variant identifiers fail closed.
3. Same-name release editions receive scope-wide ambiguity context; an undated page cannot verify both editions.
4. Ordered event manifests bind campaign identity, every segment, event count and hash chain. Missing campaign/event manifests, missing middle/tail segments and unindexed segments require recovery. A rejected event rolls back all queue mutations.
5. Missing/blocked/partial discovery prevents complete=true, including sitemap 404s.
6. Textual member, coupon, subscription and cart-only prices remain observations.
7. Formatted TRY thousands separators cannot turn 1.234 TL into 1.23 TRY.
8. Page language does not establish the country of sale; unknown official market remains unknown.

Verification: 54 v5 + 35 v3 + 24 v4 tests pass (113 total), including real Git checkpoint push, clone, resume without a second fetch and export. Full-scope initialization previously verified 174259 identities. The 2026-10-07 live 10-product pilot found 8 verified products, 2 Trendyol checks and TRY/EUR/USD, with both negative controls passing. A fresh pilot using the final immutable code SHA is mandatory in GitHub prepare before scan workers start.

Reviewer scope rulings: source reachability and future GitHub jobs remain live checks, not code guarantees. Registry domains are curated from existing source provenance; ownership has not been independently audited for every brand. Unknown official sites require reference and homepage evidence. Checkout, shipping and purchase completion are not tested (checkout_verified=false); foreign/out-of-stock offers never imply availability in Turkey. Unchanged v3/v4 modules pass their 59 existing tests, without asserting universal legacy correctness. Robots exclusions and unknown sources remain explicit coverage limits; no bypass or guessed absence.

Publishing is authorized by the user's new-scan request and repeated continue instructions. New v5 code/data branches only; preserve main, all product identities, v3 and v4 evidence. Previous v4 input is pinned to commit 8bd19c6a4c5168b7a3412af07e77ab9c77c8caf7. Keep the existing worktree for follow-up and do not merge into main.

First GitHub launch 37798573781 (code e0b0efa3ce508551cda6a5a12070320d95d063eb) passed all 113 regression tests but correctly stopped at the live gate: 7/10 products verified and TRY/EUR/USD available; both Trendyol pages redirected to /en/select-country?cb=..., whose callback query is robot-excluded. No campaign state or full scan was initialized. Downloaded artifact 11559533111 confirms the exact redirect and policy snapshot. Trendyol's public page context identifies normal preferences countryCode=TR, storefrontId=1, language=tr. Configure only these domain-scoped, non-authentication preferences; keep all robots checks and the unchanged gate. A failing regression first reproduced the missing preference, followed by the fixed test. The next GitHub run must prove the correction live before any full-scan claim.

Confirmed live launch: run 37799951233, immutable code 15a827b3f5a10c4712a5fec934471348052df4e7. All 114 regression tests pass locally and on GitHub. Fresh pilot at 2026-10-08T15:23:36Z passes with 8/10 products, 2 Trendyol verified checks, TRY/EUR/USD, both negative controls and 26/26 HTTP requests successful. Prepare persisted 174259 product identities and the initial 19238 tasks / 10509 product URLs at 15:23:44Z; scope/tasks hashes, campaign code/run identity and event-manifest campaign hash read back successfully. Scan (1) is running and 47 serial workers are queued. These initial zero counters are separate from the pilot and will advance with the first worker checkpoint. Exact run/state links and recovery rules are in COMMERCE_V5_LAUNCH.json.

First worker checkpoint verified at 2026-10-08T15:29:18Z (commit 005878b40348552bf3deac50b8b3cedb1d11689c). All 23 durable events match segment hash, count and campaign-anchored chain. Queue: 20/20245 terminal tasks (0.099%); 11/174259 catalogue queries proven (0.0063%); product pages 0/10829 completed, with full-scan verified-price count 0 distinct from the passed pilot. Source discovery has priority, so page checks follow catalogue expansion. Three terminal discovery limits: Eyfel robots unavailable after bounded attempts, Qlife sitemap not valid XML, Golden Rose sitemap unavailable. Eda Taspinar robots retrieval is still retrying. These do not prove product absence and do not stop other sources. Early current-queue ETA is 87.67 hours from only 312.1 seconds and 20 terminal discovery tasks; it is not a reliable full-campaign forecast and excludes undiscovered pages. Existing serial budget is 48 x 90 minutes (72 hours); report preserves remaining tasks if budget is exhausted, without declaring complete.

## Nullable related-product recovery — 2026-10-09

Run 37799951233 stopped at 04:21:23 UTC in scan (9), job 113390827411.
The optional JSON-LD `isRelatedTo` field was null, causing a TypeError in
discovery after a successful Trendyol page response. Scan (1)..(8) succeeded.
Later scan slots were cancelled by fail-fast. This is a deterministic parser
edge case; rerunning the unchanged code is not a recovery.

The failed worker's final push succeeded at checkpoint
6997c5a3106bfba111cd29feb9165f893cbd27d9. Recovery artifact 11594563792
(SHA-256 08a4cccb9559a8588e7b29da56926f4d8cfec27a13b4a49711d171bc2f15fee7)
contains exactly the same campaign, manifest and summary as GitHub. All 7,641
events in 160 segments, compressed scope/tasks hashes and the manifest chain
were verified. There are no unpublished event segments.

Preserved baseline: 174259/174259 catalogue scope, 7320/18138 terminal product
pages (40.357%), 7594/27680 terminal tasks (27.435%), 10818 pending pages,
10 unresolved pages and 6 unavailable pages. Verified products: 2646; Turkish
in-stock: 2393; currencies TRY 2645, USD 1. Catalogue completeness is not price
coverage. Current-queue estimate before the stop was 35.11 hours, excluding
undiscovered pages. Terminal source restrictions remain explicit.

Can authorized the repair and continuation on 2026-10-09. The optional field
now accepts absent/null, single URL/node and lists without aborting the primary
page. Related prices remain excluded; candidates need their own verification.
The actual failing saved page now parses without a crash, but its offer remains
unverified because concentration is unproven. No identity/price gate was relaxed.

An explicit runtime revision binds the new code to the original campaign and
the verified event boundary. Campaign, scope, initial queue and all previous
events stay immutable. New events name their runtime and revision hash.
The dedicated continuation workflow shares the original concurrency group,
runs regression and recovery gates, then 40 serial worker slots from the saved
queue; it never runs prepare or initializes a second campaign. Preserve the
original launch code as provenance; use runtime_revision.json for active code.
Do not rerun the historical failed run: it contains the defective original code.

Local validation: 64 v5 + 24 v4 + 35 v3 tests pass (123 total), including a real
Git push/clone round trip, revision idempotence, stale-runtime rejection,
checkpoint tamper/loss detection, attempt/cooldown preservation and no refetch
of completed work. Continuation is not considered live until a new GitHub
checkpoint advances past 7,641 events.

Full recovered-state transition also passed locally: all 7641 events replayed,
168 existing files retained identical hashes, counters remained unchanged and
the next pending task is exactly the failed Trendyol URL with attempts=0.

Independent recovery review: no Critical or Important findings; approved for
continuation. A historical binary cannot enforce a newer sidecar, so rerunning
the original failed workflow remains prohibited. New workers reject any
unstamped post-transition events rather than accepting mixed runtimes.

## Continuation verified live — 2026-10-09 15:43:59 UTC

Active run [37900782488](https://github.com/canmuslu59/senlis/actions/runs/37900782488),
code d9a1976433016e65a4afcad7189adb6a14b65caf, passed all 123 GitHub tests and
the saved-page/resume gate. Activation commit 5fe18366df1f78c6b35ef4dd8115f5f179d34ce1
retains original campaign and all counters. The formerly crashing page is the
first post-revision event, done/success at 07:46:25 UTC, attempts=1.

Scan parts 9–13 succeeded; part 14 is active and 15–48 are queued (34 slots).
No new failed job. GitHub's aggregate run status still says queued while the
job endpoint confirms an active worker; evaluate job and checkpoint evidence.

Pinned checkpoint 07a0247437721fbb0695b500fca83c3a8550392c has 10924 events
in 252 segments: 3283 new durable events. The original 160 manifest entries
match the preserved baseline. Recomputed the entire manifest chain and verified
the first and latest new segment payload hashes/counts and runtime-revision
attribution. The current checkpoint is fresh; no restart is warranted.

Pages: 10423/19105 (54.556%), pending 8682, unresolved 240, unavailable 17.
Tasks: 10697/28647 (37.341%), pending 17950. Catalogue scope: 174259/174259,
which does not imply price completeness. Verified products: 3213 (+567 since
repair); Turkish in-stock: 2948. Currency product counts: TRY 3210, EUR 4, USD 5
(overlap possible). finished=false, complete=false.

The latest segment has 15 done events and 3 robots_disallowed events for
Trendyol /pd/ product addresses. These are source-access restrictions, not a
recurrence of the nullable parser crash. No access rules or attempt caps were
relaxed. The last worker pace estimates 106.81 hours for its pending queue;
this volatile estimate excludes undiscovered pages and now exceeds remaining
run budget. The current 34 queued slots provide approximately 49 scan hours,
so completion is not guaranteed within this run. Pending work must remain
checkpointed; never claim completion based only on catalogue scope or all
workflow jobs exiting successfully.
