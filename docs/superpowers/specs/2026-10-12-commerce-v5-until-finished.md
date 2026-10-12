# Continue the preserved SENLIS v5 queue until it drains

Can authorized this continuation on 2026-10-12: “bu işi bitirene kadar sıraya koyalım”.

The successful run 37900782488 exhausted its 40 serial slots. The durable state at
000f21a6a1e469f7fd2e92c03e633854a06fa3bf still contains 2202 pending tasks,
1602 pending product pages, 21856 events, and 3982 verified-price products.

Use rolling 90-minute worker runs, not another fixed number of slots. Each
successful checkpoint dispatches exactly one successor when tasks_pending > 0.
The first push is a validation/bootstrap run, so automatic dispatch can be
verified immediately. Every run shares the existing concurrency group. A failed
worker, failed push, invalid lineage or ambiguous dispatch stops the chain.

Run the unchanged scanner at d9a1976433016e65a4afcad7189adb6a14b65caf in its own
verified checkout. New orchestration lives separately. Preserve the original
campaign and runtime revision, all 174259 identities, attempts, cooldowns and
terminal restrictions. No prepare, new campaign, v3/v4 rerun, or main changes.

When pending reaches zero, export the database and stop even if complete=false;
source access/discovery gaps remain explicit. Large generated exports must be
stored as verified, reconstructable chunks before Git push exceeds its file
limit. Evidence and queue files are never split or deleted by this helper.

Add a silent hourly safety watcher for transient GitHub failures only. It may
retry one necessary failed job per check, at most four attempts, only after
checking published state and any recovery artifacts. No blind retry or reset of
blocked sources. Normal progress produces no notifications.
