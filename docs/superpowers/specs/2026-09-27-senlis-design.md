# SENLIS product design

## Intent and success

SENLIS is an Android fragrance discovery community for Turkey. A person describes scents they enjoy, scents they avoid, perfumes they own or love, mood, occasion, intensity and budget, then sees relevant perfume and body mist suggestions with a transparent match percentage. Every fragrance has a useful detail page and, once the shared service is live, its own ratings and discussion. A general community space, editorial fragrance news and a daily scent reminder bring people back. The visual reference is a dark, photographic, warm gold editorial experience with elegant serif headings and clear Turkish copy. A usable product must have working navigation and honest data, not a sequence of photographs presented as screens.

The reference image is visual direction, not a source for product facts or trademarks. SENLIS may include all brands; it must not bias the result toward Innative ENY without disclosure. The existing `main` branch was emptied on 27 September 2026. Preserve it while developing on `feature/senlis-premium-foundation`.

## Delivery stages

1. **Native visual foundation.** Build a fresh Android application with branded welcome, five preference steps, persisted local profile, searchable seed catalogue, explainable match score, favourites, fragrance details, editable profile, and an honest community preview. Use licensed/original editorial assets and label all seed products as examples. Do not display invented prices, aggregate ratings, retailer availability or public comments. This stage is testable without a server and does not claim the full product is online.
2. **Verified catalogue service.** Add a backend with a canonical fragrance ID, variants and concentrations, source URLs, source timestamps, field-level provenance, editorial review and corrections. Import permitted Open Beauty Facts records and suitable Wikidata facts; use brand submissions or licensed feeds for notes, launches, photos and Turkish availability. Separate ODbL data and CC-BY-SA photos according to their terms; avoid scraping third-party fragrance sites. Reconcile barcode, brand, name, concentration and size; queue uncertain matches. Expose versioned paginated search/detail endpoints, incremental daily sync, correction reports, stale-field labels and a last-successful-sync dashboard. Open Beauty Facts is a cosmetics label source, not a complete authoritative scent-note database.
3. **Accounts and community.** Sign-in, profiles, per-fragrance ratings with verified author IDs and one current rating per user, threaded fragrance discussion, general rooms, reporting, moderation queue, abuse throttles and deletion controls. Public content lives on the server. Do not pass private device notes off as a shared discussion.
4. **Editorial and notifications.** Publish source-linked fragrance news through an editorial queue. Deliver one opt-in daily scent reminder and one opt-in daily news push via a scheduled server job and FCM. Deduplicate by user/day/type, respect local timezone and quiet hours, retry and record delivery attempts. On Android 13+, request notification permission at the moment the user opts in. If no verified news exists, do not fabricate an item; alert the editor and show the last valid article in-app. The daily news push goal depends on a staffed or licensed news feed.

## Match model

Candidate data has family, accord/note IDs, concentration, intensity, occasion tags and optional price. A user's positive and negative notes, families, loved products, mood, occasions, intensity and budget form a profile. An excluded note is a hard filter when the ingredient/note field is known. Calculate a 0–100 compatibility score with fixed, versioned weights: note overlap 35, family 20, loved-product similarity 15, occasion/mood 15, intensity 10, budget 5. Redistribute unknown dimensions' weights only among known dimensions. A score is displayed only when at least two independent known dimensions contribute; otherwise show “Yeterli veri yok”. A missing price never counts as within budget. Expose the contributing factors on detail and label the number as an estimate, not measured enjoyment. Collect feedback to recalibrate later without secretly changing scores.

## Stage-one screens and data

- Welcome: original jasmine portrait, SENLIS identity, one primary action, a simple skip path.
- Preferences: mood, liked notes, loved fragrances in free text, disliked notes/intensity, occasions/budget. Selections are editable later. No gender gate.
- Discover: featured editorial image, top matches, search, sample-data badge, explanation of scores.
- Fragrance detail: original unbranded image, type, family and notes, reasons for match, favourite action, clear source/example status, private note entry. No counterfeit brand bottle imagery.
- Community: an honest, visible explanation of the planned shared discussion, with no invented users or messages.
- Profile: selected preferences and privacy-friendly local reset.

Persist stage-one preferences and favourites on the device. Seed catalogue entries are generic editorial examples, rather than fabricated descriptions of named commercial products. Real brand entries arrive with the verified catalogue service.

## Quality and boundaries

Android package `com.innative.senlis.preview` for this isolated preview, so previous SENLIS signatures/installations cannot block it; production migration needs an intentional signing/package decision. Android min SDK 23, target SDK 35, Java 17 and native Views. Respect system bars and font scaling; text must remain readable on small phones. No hardcoded API keys. Stage one builds through a self-hosted Windows/X64 workflow and uploads a debug APK. Unit tests cover scoring, insufficient data, excluded notes and budget unknowns. A CI APK is a preview, not evidence that backend, push, moderation or catalogue ingestion are live.

## Research notes

Open Beauty Facts provides cosmetics product API and bulk exports, with ODbL data and separately licensed product photos. Their documentation recommends a custom User-Agent, respecting rate limits and using dumps for large imports. Wikidata provides a SPARQL endpoint but discourages large/fuzzy search queries and asks clients to respect rate limits. Android requires runtime `POST_NOTIFICATIONS` permission from API 33; exact alarm permission is restricted, so daily editorial pushes belong to a server/FCM flow rather than an exact local alarm promise.
