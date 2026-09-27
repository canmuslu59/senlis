# SENLIS

Native Android preview for a Turkish fragrance discovery community. This branch is the first visual and recommendation slice based on the supplied luxury editorial reference.

## What works in this preview

- Original photographic welcome screen and five editable preference steps.
- Local profile and favourites, search, fragrance detail, private notes, transparent estimated match score.
- Six **fictional editorial examples** of perfume/body mist profiles, deliberately labeled as such. There are no fabricated brand product pages, prices, public ratings, news or conversations.
- The separate application ID `com.innative.senlis.preview` installs alongside older SENLIS builds, avoiding their debug/release signing conflict.

## Next delivery slices

1. Curated, licensed and source-attributed live catalogue with daily import and review queue.
2. Account system, product ratings/comments, general rooms and moderation.
3. Source-linked editorial news and opt-in daily reminder/news push via a scheduled backend and FCM.

The design and implementation plan are in `docs/superpowers/`. The catalogue must show a per-field source and update date and allow correction reports. Open Beauty Facts may supply label/barcode information, but it cannot by itself establish a comprehensive note pyramid or current Turkish prices.

## Build

On the configured Windows/X64 self-hosted runner, pushing `feature/senlis-premium-foundation` runs the pure-Java match tests and `gradle :app:assembleDebug`, then uploads `SENLIS-v0.5.0-preview.apk`. The preview is signed with the runner's debug key. No backend credentials are needed for this stage.
