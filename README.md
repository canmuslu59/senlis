# SENLIS

Native Turkish Android fragrance discovery app. The fragrance catalogue lives on
the device. The first APK contains four real products reviewed against official
brand pages, with source links and dates. Taste choices, favourites and private
notes stay on the phone. This branch remains a development preview; live
community and news push need a SENLIS Firebase project before the final APK
can be verified end to end.

## Catalogue without a product server

`app/src/main/assets/catalogue.json` is the initial source-attributed snapshot.
The same JSON is published as `docs/catalogue.json` in the repository. The app
loads the bundled or newer validated local file, searches and scores offline,
and checks the published HTTPS file when opened after 30 days. An unavailable
network or invalid update leaves the last good catalogue usable. No taste
profile or personal note is sent in this request. The static update URL defaults
to the repository's `main` branch; a different HTTPS location can be set with
`-PsenlisCatalogUrl=...` at build time.

The editorial SQLite database is a **single curator workspace**, not a database
for each user. It stores candidate product records, source attribution and
review decisions. The exporter includes reviewed products only; unknown notes,
prices and ratings are left unknown. Open Beauty Facts candidates need a human
source check before approval. A changed source identity returns to the queue.
No fictional products, speculative prices or copied brand imagery are bundled.

`python -m service.catalogue_package --database PATH/TO/catalogue.sqlite
--output docs/catalogue.sqlite` also creates an indexed SQLite export of only
reviewed fragrances with individually sourced notes. The monthly workflow
uploads this file as a review artifact. It is a preparation for a paged Android
catalogue and is **not yet loaded by the current APK**; the Android app still
uses the four-item JSON asset. The export reports actual counts and refuses to
replace a valid package if the new source attribution is malformed.

The revised target of approximately 140,000 distinct fragrances **with sourced scent
notes** is not yet met. See [the source and scale assessment](docs/catalogue-scale-assessment.md)
for verified source counts, usage limitations and the required indexed local
catalogue migration. The present four-record JSON snapshot must not be
reported as a large catalogue.

To bootstrap and verify the snapshot locally:

```sh
python3 -m service.export_catalog --database senlis-editorial.sqlite \
  --output docs/catalogue.json --asset-output app/src/main/assets/catalogue.json --seed
python3 -m unittest discover -s service/tests -v
```

The free Windows self runner workflow `.github/workflows/monthly-catalogue.yml`
collects Open Beauty Facts candidates on the second day of each month into its
own persistent SQLite file. Set a monitored `SOURCE_CONTACT` repository secret
and install/register the runner. The workflow runs on the default branch after
merge; a manual dispatch is also available. An editor checks candidates and
their source links, approves those that are correct, and republishes the two
matching JSON files. The exporter keeps the previous timestamp when product
facts are unchanged. Publishing a new snapshot remains a review action; an
automated source import alone is never evidence that its facts are correct.

On the runner, inspect candidates with `python -m service.editor --database
PATH/TO/catalogue.sqlite products` and page with `--offset 100`. After opening
and checking the named source page, explicitly approve one by ID using
`approve-product ID --checked-url https://...`. Export with
`python -m service.export_catalog --database PATH/TO/catalogue.sqlite
--output docs/catalogue.json --asset-output app/src/main/assets/catalogue.json
--if-changed`, review the JSON diff, and publish it through a reviewed commit to
`main`. The APK is still useful offline if this process is delayed.

## Shared features

Product/general conversation and user ratings cannot synchronize between
phones through a local JSON file. Android uses Firebase Authentication and
Cloud Firestore directly for those shared records. `firestore.rules` restricts
client writes to their own account, messages, reports, corrections and ratings;
the two query indexes are in `firestore.indexes.json`. Messages and ratings are
not copied into the product catalogue. The custom HTTP service in
`service/api.py` is only a local development harness, **not** a required
catalogue server or Android dependency. A dedicated SENLIS Firebase Spark
project, email/password sign-in, Firestore and deployed rules/indexes are
required before community can be called live. Do not reuse another app's
Firebase project without its owner's decision.

The daily personal reminder is an inexact 09.00 device alarm, available without
an account. Android may defer its delivery under battery restrictions. News
in the app reads reviewed records from Firestore. A genuine news push needs an
editor-approved story, opt-in, Android permission and the self runner's FCM
delivery job; none is sent on a day without a verified item. We do not invent
daily news on quiet days. A source candidate alone cannot be published by an
Android client because the rules deny news writes.

Firebase's no-cost quotas are finite; launch traffic and moderation capacity
must be monitored. The app will never silently switch to a paid hosting plan.

The second self runner workflow `.github/workflows/daily-news.yml` polls official
news feeds daily, publishes only records already approved in the runner's SQLite,
and attempts one fresh FCM news item per opted-in user and local day. Review
candidates with `python -m service.editor --database PATH/TO/catalogue.sqlite
news`; use `publish-news ID --checked-url https://... --published-at
2026-09-27T10:00:00+00:00` only after checking the source and its actual date.
Set the dedicated `SENLIS_FIREBASE_SERVICE_ACCOUNT_JSON` repository secret for
this workflow. Keep the service account out of the APK and git. Neither the
scheduled workflows nor live messaging run until the self runner and project
are configured, the branch is merged into the default branch, and Firestore
rules/indexes are deployed. Community reports and corrections need an editor
to inspect them through `python -m service.moderate reports` and
`python -m service.moderate corrections` on the runner. Hide a reported post
with `hide-message ROOM MESSAGE_ID`, then mark its report with
`resolve-report REPORT_ID`; the phone cannot approve or hide content.

## Development

Android: Java 17, Gradle 8.11.1, SDK 35. The hosted verification workflow builds
an APK and exercises API 23/35 emulators. Build parameters for a dedicated
Firebase project are `firebaseAppId`, `firebaseApiKey`,
`firebaseProjectId` and `firebaseSenderId`.

```sh
gradle :app:assembleDebug
```

The source code for the previous experimental WSGI/PostgreSQL service remains
only for test and migration work. There is no Render deployment configuration.
The `docs/visual-preview/` images are emulator captures, not branded product
photography. An installable final APK is pending the free shared community
integration and live verification.
