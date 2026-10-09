# Resume the existing v5 campaign after the nullable related-products failure

Authorized by Can on 2026-10-09: fix and continue. No new campaign or scope.

1. Reproduce `isRelatedTo: null` with a real-shaped Product offer. Normalize only
   the optional discovery field; related offers remain inadmissible as prices.
2. Keep campaign, scope, initial tasks and all 160 existing event segments intact.
   Add a runtime revision bound to the verified campaign hash, checkpoint commit,
   7,641-event boundary and exact old/new code commits. Reject unapproved runtime
   changes, corrupt boundaries, lost revisions and incorrectly attributed events.
3. Before activation, replay the saved failing page against the real scope. On
   continuation, preserve finished work, attempt caps, host blocks and cooldowns.
4. Run the v3/v4/v5 regression suites and replay the verified recovery archive.
5. Publish a dedicated continuation workflow using the existing concurrency group.
   Validate and persist the revision, then run 40 serial worker slots. Never call
   `prepare`, the old trigger, a campaign initializer or an unchanged-code rerun.
6. Verify fresh progress past the durable checkpoint before reporting resumed.

Recovered run: 37799951233; failed job: 113390827411. Recovery artifact
11594563792 matches durable checkpoint 6997c5a3106bfba111cd29feb9165f893cbd27d9.
Scope/tasks hashes, every event segment and manifest head were verified before
this repair. No unpublished event segment exists in that recovery archive.
