# Uploaded name package review — 2026-09-28

The supplied `parfum_bodymist_150k_paket(1).zip` is 6,502 bytes
(SHA-256 `e7bedf91e5759e2658edcfa25839eb0743c3ef0a5040fa3fc43b59da9f5f1bed`).
It contains a Python downloader/merger, a setup note and a Windows batch launcher.
It contains **no product CSV, TXT, database, or list of names**. The estimates
in the setup note are upstream row counts, not measured distinct fragrances
in the uploaded file. We did not execute the launcher or download its sources.

| Script source | Finding | SENLIS decision |
| --- | --- | --- |
| [TidyTuesday Parfumo data](https://github.com/rfordatascience/tidytuesday/blob/main/data/2024/2024-12-10/readme.md) | The project's own page says the dataset was scraped from Parfumo and includes its notes and product links. | No bulk app import without verified original reuse rights. |
| [doevent/perfume](https://huggingface.co/datasets/doevent/perfume/blob/main/README.md) | Its uploader labels the dataset MIT and says it holds 26K+ records, but its card does not identify the original source or grant for each product image/field. | Names can be counted as unverified review leads from a user-provided output; do not publish fields or count them as verified. |
| [anvo2/perfume-rec-assets](https://huggingface.co/datasets/anvo2/perfume-rec-assets) | Its visible rows include Fragrantica links and descriptions. The supplied script derives names from those URLs and copies the note descriptions. | Excluded from import under Fragrantica's [terms](https://www.fragrantica.com/terms-of-service.phtml). |

The script's fallback copies `Main Accords` into `all_notes` when a note pyramid
is absent. An accord is not a verified note. Its `type_hint` labels every item
that does not mention a body mist as a perfume; its deduplication prefers the
row with more note text regardless of reuse rights. These rules cannot prove
141,000 distinct, licensed, note-backed fragrances.

If the actual CSV/TXT is supplied, run `python -m service.candidate_audit
path/to/parfum_bodymist_tekil.csv`. This streaming, read-only check reports the
actual raw and distinct brand/name counts, missing identities and upstream
source categories. It adds **zero** products to the published catalogue. For
every selected product an editor must establish an independent manufacturer or
permitted source for its identity and notes before publishing it. Price offers
need their own dated variant and retailer source; photos need an explicit reuse
license and attribution.

## Subsequent actual TXT attachment

`parfum_bodymist_154154_hazir (2).txt` is a separate 43,848,684-byte TSV
(SHA-256 `c49e16f603b2f504aa6923370e94277fb56e861b542168768014dcc3d6529978`).
Its **154,154 rows** break down as follows:

| Upstream label | Rows | Review route |
| --- | ---: | --- |
| TidyTuesday-Parfumo | 59,324 | Excluded from app import pending original reuse rights |
| anvo2-perfume-rec-assets | 68,511 | Excluded: Fragrantica-derived URL and descriptions |
| doevent-perfume | 26,319 | Private name leads only; original product sources unspecified |

Normalizing brand and name yields **126,826 distinct keys across all rows**,
not 154,154 distinct perfumes. Two rows have a name consisting solely of a
symbol and lack a useful normalized key. **104,362 rows** have upstream text
in at least one note column; that is not verified note coverage. Unlike the
earlier ZIP script's fallback, this TXT has a separate `main_accords` column;
the audit did not detect an anvo2 accord copied into a note-only field.

The local editorial database now holds **26,229 distinct doevent names in a
private `external_name_leads` queue**; 90 of its rows were duplicates or failed
the lead field check. It stores only brand/name and a dataset reference, not
upstream notes, photos or a guessed body-mist type. These leads are absent from
the Android package and do not increase the ten verified product count. Inspect
them using `python -m service.editor --database PATH/TO/editorial.sqlite leads`.
An editor must verify a separate official product identity and note page using
`add-brand-product` before any record reaches the note-backed app snapshot.
