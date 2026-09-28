# Supplied note catalogue implementation plan

**Goal:** Use the user's basic brand, product name and listed scent notes without requiring an individual manufacturer check for every entry, while showing the origin and limits of those fields.

**Architecture:** Keep the existing ten editor checked entries. A streaming importer reads the supplied TSV, selects rows from the separately MIT labelled doevent dataset, rejects missing identities, empty notes and conflicting duplicate identities, then builds an indexed SQLite snapshot with source links. It leaves kind unknown unless independently established, and never imports photos, prices, reviews or accords as notes. The Android interface labels dataset records as such and uses a note similarity percentage when only note data is known. The broader uploaded TSV is audited separately; Parfumo and Fragrantica derived fields are not silently promoted by this importer.

**Tech stack:** Python 3 standard library, SQLite FTS4, Android Java 17.

**Acceptance:**
- Streaming audit reports raw rows, distinct identities, distinct note backed identities and conflicting duplicates accurately.
- A small fixture creates a searchable package containing editor entries and conflict free dataset names/notes, with stable IDs and explicit source status; rerunning is deterministic.
- No guessed type, price, photo, launch date or translated note is presented as manufacturer confirmed.
- Actual supplied TSV yields a measured import count and a package under the Android size limit.
- Android API 23/35 emulator smoke covers offline search, detail provenance and note based recommendations.

**Execution:** Audit tests and importer tests first, then code, then Android UI and matching tests, package generation, performance check and hosted CI. The public PR remains draft until the dataset provenance and final APK gates are resolved.
