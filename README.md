# SENLIS

Native Turkish Android fragrance discovery app. The fragrance catalogue lives on
the device. The development APK contains ten real products reviewed against official
brand pages, with source links and dates. Taste choices, favourites and private
notes stay on the phone. This branch remains a development preview; live
community and news push need a SENLIS Firebase project before the final APK
can be verified end to end.

## Catalogue without a product server

`app/src/main/assets/catalogue.sqlite` is the initial indexed, source-attributed
snapshot. The same file is published as `docs/catalogue.sqlite` in the
repository. Android installs and verifies the local SQLite file, then searches
and scores offline with bounded result pages. On opening after 30 days it
checks for a newer reviewed HTTPS snapshot. An unavailable network or invalid
update leaves the last good catalogue usable. No taste profile or personal note
is sent in this request. The static update URL defaults to the repository's
`main` branch; a different HTTPS location can be set with
`-PsenlisIndexUrl=...` at build time. The JSON export is retained for human
review and comparison, but Android no longer parses it as its working catalog.

The editorial SQLite database is a **single curator workspace**, not a database
for each user. It stores candidate product records, source attribution and
review decisions. The exporter includes reviewed products only; unknown notes,
prices and ratings are left unknown unless separately verified. Open Beauty Facts candidates need a human
source check before approval. A changed source identity returns to the queue.
No fictional products, speculative prices or copied brand imagery are bundled.
Product names are discovered through Open Beauty Facts and checked official
brand pages. Systematically collecting names from Fragrantica, even when notes
and images would come from elsewhere, is outside this pipeline under its terms.

`python -m service.catalogue_package --database PATH/TO/catalogue.sqlite
--output docs/catalogue.sqlite` exports only reviewed fragrances with
individually sourced notes. The monthly workflow uploads it for manual review.
It reports actual counts and refuses to replace a valid package if attribution
is malformed. After review, publish the same package to `docs/` and the Android
asset on the default branch. The current package contains **ten** products.

The revised target of approximately 141,000 distinct fragrances **with sourced scent
notes** is not yet met. See [the source and scale assessment](docs/catalogue-scale-assessment.md)
for verified source counts and usage limitations. The present ten-record
SQLite package must not be
reported as a large catalogue.

The uploaded package and subsequent 154,154-row TXT were
[audited](docs/uploaded-name-package-assessment.md). The original ZIP contains
only a downloader; the TXT's 154,154 rows normalize to 126,826 brand/name keys.
The improved audit counts 85,805 distinct names with note text and 14,391
identities whose duplicate note lists conflict. These are data-set claims, not
individually manufacturer-confirmed notes. A local experimental exporter now
builds a 26,194-record, 202,591-note, 38 MB package from the ten checked
products and the conflict-filtered `doevent/perfume` portion of the user file.
Its `unknown` type is not guessed from the text, its notes are visibly
dataset-listed, and neither photos nor prices are copied. The **bundled APK
still contains ten products**; the larger package awaits Android device checks
and the source decision before it can replace the published snapshot.

To reproduce the local package from the supplied file:

```sh
DATABASE_URL=/path/to/editorial.sqlite python3 -m service.curated
python3 -m service.supplied_catalogue /path/to/parfum_bodymist_154154_hazir.txt \\
  --database /path/to/editorial.sqlite --output /path/to/senlis-supplied-preview.sqlite
```

Parfumo/Fragrantica-derived rows are excluded from this import while their
reuse conditions are unresolved. The
read-only tool `python -m service.candidate_audit PATH/TO/FILE` measures the
actual file. With `--stage-doevent --database PATH/TO/editorial.sqlite`, it
stores only eligible names in a **private review queue**. The actual TXT yielded
26,229 distinct private leads in the earlier editorial queue. Separately, the
experimental dataset-labelled package uses available note text without
pretending that every field was independently checked. Its third source lacks
original field-level provenance, so errors can be reported and corrected.

To bootstrap and verify the snapshot locally:

```sh
python3 -m service.export_catalog --database senlis-editorial.sqlite \
  --output docs/catalogue.json --asset-output app/src/main/assets/catalogue.json --seed
python3 -m service.catalogue_package --database senlis-editorial.sqlite \
  --output docs/catalogue.sqlite
cp docs/catalogue.sqlite app/src/main/assets/catalogue.sqlite
python3 -m unittest discover -s service/tests -v
```

The free Windows self runner workflow `.github/workflows/monthly-catalogue.yml`
collects Open Beauty Facts candidates on the second day of each month into its
own persistent SQLite file. Set a monitored `SOURCE_CONTACT` repository secret
and install/register the runner. The workflow runs on the default branch after
merge; a manual dispatch is also available. An editor checks candidates and
their source links, approves those that are correct, and republishes the
reviewed JSON and matching SQLite package. The JSON exporter keeps the previous timestamp when product
facts are unchanged. Publishing a new snapshot remains a review action; an
automated source import alone is never evidence that its facts are correct.

On the runner, inspect candidates with `python -m service.editor --database
PATH/TO/catalogue.sqlite products` and page with `--offset 100`. After opening
and checking the named source page, explicitly approve one by ID using
`approve-product ID --checked-url https://...`. After independently checking
the scent notes on an official brand or reusable source page, add them with
`verify-notes ID --checked-url https://brand.example/product --source-name Brand
--note Gül --note Misk`. The command rejects Open Beauty Facts and Fragrantica
as scent-note sources; an INCI ingredient list or a copied community pyramid
does not become a checked note claim. Export with
`python -m service.export_catalog --database PATH/TO/catalogue.sqlite
--output docs/catalogue.json --asset-output app/src/main/assets/catalogue.json
--if-changed`, review the JSON diff, and publish it through a reviewed commit to
`main` together with the reviewed SQLite file copied to the Android asset.
The APK is still useful offline if this process is delayed.

An editor can add a product found directly on a manufacturer's page with
`add-brand-product --name '...' --brand '...' --kind perfume
--checked-url https://brand.example/product --note '...'` (repeat `--note`).
The human-checked URL and each note remain in the database. Verified prices
can be recorded with `record-offer ID --retailer '...' --checked-url
https://shop.example/product --amount-minor 129900 --currency TRY --country TR
--variant '90 ml' --observed-at 2026-09-28T10:00:00+00:00`. This represents a
dated offer for one variant, not a timeless product price. Offers older than
30 days are excluded from the next SQLite export and hidden on the device when
they expire; recheck them before each publication. The example numbers and
domains in this command are documentation placeholders, not catalogue records.

`record-photo ID --image-url https://images.example/asset.jpg --checked-url
https://images.example/asset --license-name '...' --license-url
https://images.example/license --attribution '...'` records an image only when
the editor has checked explicit app reuse rights for that asset. Search engine
thumbnails and Fragrantica images are not accepted as rights evidence. The app
loads licensed HTTPS images with an editorial illustration as a fallback and
links the credit and license. The current package has **zero** licensed product
photos and **zero** current price observations; we do not invent either.

## Shared features

Product/general conversation and user ratings cannot synchronize between
phones through a local catalogue file. Android uses Firebase Authentication and
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
