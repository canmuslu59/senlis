# SENLIS live service implementation plan

## Scope

Deliver a real, source-attributed catalogue and shared service before the next APK. The Android client must never substitute invented commercial products, ratings, prices or news. Offline and service-error states are explicit.

## Sequence and acceptance

1. **Catalogue and database.** PostgreSQL schema, migrations, canonical product and variant IDs, source records and field provenance, sync runs, quarantined import candidates, corrections. Pull licensed Open Beauty Facts label facts with a descriptive User-Agent and controlled pace. Accept records with barcode, name, brand, relevant product type and source URL. Never infer notes, price, intensity, family or image rights from the name. Read endpoints paginate and include provenance and freshness. Tests cover duplicate barcode, rejection, provenance and empty imports.
2. **Accounts and community.** Password hashing, token sessions, account deletion, one rating per account/product, comments in product and general room, paginated reads, report and moderation hiding. Database constraints and rate caps. Tests cover ownership, duplicate ratings and hidden content.
3. **News and delivery.** Curated articles with title, link, source, verified timestamp, publication state; no fabricated feed. Daily reminder and news notification preferences in IANA time zone, a UTC scheduler, per-day/type uniqueness, quiet-hour handling and delivery receipts. FCM credentials remain server-side. If no article is approved, skip news push and surface editorial backlog. Tests cover dedup, no-article and time-zone boundaries.
4. **Android integration and release QA.** Real search/details, source links, transparent match status, account/community UI, news and opt-in notification settings. No bundled fictional catalogue. Service URL injected at build time. Test against a deployed database-backed service, emulator screenshots and hosted build before handing over one APK.

## Deployment gate

Code and migration can be reviewed without secrets. A live shared catalogue and FCM push need an authorized infrastructure workspace, database provisioning, Firebase project credentials and a trustworthy editorial publishing workflow. Do not claim the final stage complete before those are configured and exercised.
