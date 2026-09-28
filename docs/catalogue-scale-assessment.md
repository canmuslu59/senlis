# Approximately 141,000 fragrances: source and delivery assessment

Research checked on 2026-09-28. The revised target is **approximately 141,000
distinct perfumes or body mists with a real, attributed scent note for each**.
Bottle sizes, concentration variants, brands, ingredient molecules, user reviews
and note vocabulary entries do not increase the perfume count. We have not met
this requirement; the currently bundled catalogue has four source-checked
fragrances. No synthetic records or guessed note pyramids may fill the gap.

| Source | What is actually available | Fit for the requirement |
| --- | --- | --- |
| [Official brand product pages](https://soldejaneiro.com/products/brazilian-crush-cheirosa-62-perfume-mist) | First-party descriptions of individual fragrances and their notes, checked product by product. | Good evidence for individual records, but a large-scale, reusable catalogue and approximately 141,000 verified note lists are not supplied as a free export. |
| [Open Beauty Facts](https://github.com/openfoodfacts/openbeautyfacts) | Open cosmetics product and INCI ingredient data, under ODbL. Its [API](https://openfoodfacts.github.io/documentation/docs/Product-Opener/api/tutorials/scanning-cosmetics-pet-food-and-other-products/) and exports can supply candidate identities and barcodes. | INCI ingredients are **not** advertised top/heart/base scent notes. Candidate products cannot satisfy the note requirement until their note facts are independently checked. Respect attribution and share-alike when publishing OBF-derived records. |
| [Parfica's provenance-gated open export](https://github.com/parfica/parfica-open-data) | 237 matched OBF fragrances and 760 note-vocabulary rows in the checked README. Its maintainers explicitly withhold note pyramids from the free export. | Useful taxonomy and limited identities, not an approximately 141,000 product-note dataset. |
| [FragDB v5.16](https://github.com/FragDB/fragrance-database) | The vendor lists 140,230 actual fragrances, 2,606 note-vocabulary rows and 154,400+ **combined** CSV rows; the freely available sample is 10 records per file. [Full data and updates are sold](https://fragdb.net/). | Neither 154,400 combined rows nor a 10-record sample meet the requirement or the zero-cost constraint. |
| [ParfumDB](https://www.parfumdb.net/parfumo) | The vendor lists 230,835 fragrances with a note schema; [full access is sold](https://parfumdb.net/purchase), with only a free sample. | Numerically large enough, but conflicts with the requested entirely free data path. Note coverage and redistribution rights would also need an actual licensed-file audit. |
| [Fragrantica Türkiye](https://www.fragrantica.tr/) | The Turkish site itself displays approximately 141,000 perfumes and links to [Fragrantica's service terms](https://www.fragrantica.com/terms-of-service.phtml). Its footer says not to copy without written permission. The terms restrict automated extraction and dataset creation without prior written consent. | It can inform individual research questions, but its displayed count does not grant us a reusable dataset. Visiting items one by one and writing their notes into our own text file still builds a dataset from the site; using its bottle images in our app also needs an appropriate right to reuse them. No Fragrantica-derived import or image download is enabled. |

The current monthly runner collects OBF **candidates** and the reviewer exports
approved product identities. It never derives scent notes from INCI. Four
hand-checked official-brand entries already have attributed notes. Android
now bundles an indexed SQLite package, with paged search and local detail
lookups, but the dataset remains only four records. The earlier JSON export
is a human-readable review aid.

## Acceptance gates for a large catalogue

1. Establish sources with explicit app reuse and update rights; audit real
   file, including distinct products, note presence, field provenance and
   duplicates. Record those counts in the release manifest.
2. Keep product identity, variants, note claims and attribution separate.
   Reject a record from the note-backed count if its note list is missing or its
   source cannot be traced. Never turn an INCI list into a marketing note list.
3. Export indexed SQLite for on-device search, detail and matching rather than
   loading every product as JSON. The app bundles a versioned package and
   accepts monthly validated replacements over static HTTPS, preserving the
   last known good local copy if integrity checks fail. Test large real package
   download size and storage before launch.
4. Benchmark install size, storage, migration and search on low-end Android
   devices with the actual dataset. Count and provenance checks run before a
   release is labeled as meeting the approximate 141,000 target.

The zero-cost, source-backed path can grow from official-brand and OBF
candidate review plus explicitly reusable community-contributed facts. No
source checked today supplies approximately 141,000 distinct note-backed products freely as
a ready-to-import file. Therefore the large-catalogue launch gate remains blocked
until such a source is established or the free/launch-count constraint changes.

For product pictures, prefer images made or licensed by SENLIS, a brand press
kit with explicit app reuse rights, or images with an applicable open license
and attribution. A photo merely visible on a perfume website is not thereby
licensed for copying into the APK or our site.
