# SENLIS

Native Turkish Android fragrance discovery app and source-attributed community service. The live implementation is under development on `feature/senlis-premium-foundation`; no APK from this branch is a complete delivery until database, Firebase and emulator checks are exercised together.

## Current implementation

- Five-step local taste profile, transparent score, favourites and private notes.
- Real perfume/body mist catalogue from four manually reviewed official brand pages, plus a conservative Open Beauty Facts import. Every displayed fact has a source link and timestamp. Unknown scent notes, price, family and intensity remain unknown. The app bundles **no fictional products**.
- PostgreSQL schema for products, field provenance, source runs, corrections, accounts, sessions, per-product ratings, product/general discussion, reports and moderation, editorial news and deduplicated deliveries.
- Daily catalogue/feed-candidate sync and hourly FCM delivery jobs. Official news headlines enter a review queue; only editor-approved, source-linked articles can be published. A day without a verified story produces no invented news push.
- Android account, real discussion, ratings, news and notification opt-in UI. API and Firebase project configuration are injected at build time; server-side FCM service-account credentials stay off the APK.

## Run locally

Python 3.11+ is required (standard library for the SQLite test path):

```sh
python -m unittest discover -s service/tests -v
python -m service.curated
python -m service.api
```

`GET http://localhost:8000/v1/health` shows catalogue count and the latest Open Beauty Facts import. Local SQLite is for development only. For PostgreSQL deployment, set `DATABASE_URL` and install `service/requirements.txt`. `render.yaml` defines a web service, a persistent paid PostgreSQL database and two scheduled jobs; review and authorize its costs, choose a Render workspace, then supply `EDITOR_TOKEN`, `SOURCE_CONTACT` (a monitored contact address) and `FIREBASE_SERVICE_ACCOUNT_JSON` as secrets. The first web start runs the idempotent official-source seed. The daily sync is rate-limited and caps initial Open Beauty Facts search pages; increasing coverage needs a permitted bulk export and reconciliation review.

Build the Android app with Gradle 8.11.1, Java 17 and Android SDK 35:

```sh
gradle :app:assembleDebug -PsenlisApiUrl=https://YOUR-DEPLOYED-SERVICE.onrender.com \
  -PfirebaseAppId=... -PfirebaseApiKey=... -PfirebaseProjectId=... -PfirebaseSenderId=...
```

The Firebase values above are Android client configuration, while the service account JSON belongs only on the server. Notification permission is requested on opt-in. A build without a live HTTPS API URL explicitly shows a connection status and cannot serve real community data.

## Editorial and source policy

The reviewed starting product source links are in `service/curated.py`. The app uses original, unbranded editorial imagery in place of brand photos. Open Beauty Facts data must retain its ODbL attribution and terms; no third-party fragrance-site scraping, speculative price, copied brand image, invented user rating or fabricated news is allowed. The news queue can be inspected with `GET /v1/editor/candidates` using `X-Editor-Token`; a verified item can be published with `POST /v1/editor/news`. Corrections and reports enter database queues, and moderation needs an editor token. A daily news notification depends on a reviewed source item being available.

The server does not yet have a public production URL or a configured Firebase project. Local tests are not evidence of live push delivery. The implementation and deployment gates are tracked in `docs/superpowers/plans/2026-09-27-senlis-live-service.md`.
