# SENLIS source-preserving research database

Snapshot built on 2026-09-28 from the user's 43,848,684-byte TSV, SHA-256
`c49e16f603b2f504aa6923370e94277fb56e861b542168768014dcc3d6529978`.
The database is a **private research/staging artifact**, not the Android app
catalogue. Every upstream row and its source label/URL are retained for review.
It does not copy images, prices, user reviews, or descriptions into the app.

| Measure | Actual count |
| --- | ---: |
| Input rows | 154,154 |
| Repeated header rows quarantined | 10 |
| Other rows lacking a usable identity | 2 |
| Exact usable brand/name spellings | 135,387 |
| Conservative case/space normalized candidate groups | 131,604 |
| Candidate groups with at least one listed note | 88,485 |
| Groups with one nonconflicting note set | 76,042 |
| Groups with disagreeing source note sets | 12,443 |
| Groups without listed notes | 43,119 |
| Raw observations with parsed note text | 104,353 |
| Source-specific parsed note claims | 968,605 |
| Independently verified products imported by this builder | 0 |

The note-backed **candidate** group count is 62.8% of the requested 141,000;
the nonconflicting candidate count is 53.9%. Neither number establishes that
every group is a distinct physical fragrance or that its notes can be
republished. The gap to 141,000 is at least 52,515 candidate note-backed
groups; using only nonconflicting groups, it is 64,958. Brand/name alone can
still group differently formulated releases and split the same fragrance by
spelling, so those gaps are directional rather than launch counts.

The source breakdown is 59,324 TidyTuesday/Parfumo rows, 68,511
anvo2/Fragrantica-derived rows, and 26,319 doevent dataset rows. Those rows
are **not** additive fragrances. Parfumo and Fragrantica subsets need original
source reuse review before any publication. The doevent dataset is marked MIT
by its uploader, but the origin of individual note fields is unspecified.
Its URL points to the dataset, not an individual product. This research build
does not claim that any upstream license applies to copied third-party fields.

## Rebuild and inspect

```sh
python3 -m service.research_database /path/to/supplied.txt \
  --output /path/to/senlis-research-catalogue.sqlite

sqlite3 /path/to/senlis-research-catalogue.sqlite 'PRAGMA integrity_check;'
sqlite3 /path/to/senlis-research-catalogue.sqlite \
  'SELECT note_status,count(*) FROM identity_groups GROUP BY note_status;'
```

The builder hashes its exact input, creates a new SQLite file, checks both
integrity and foreign keys, then atomically replaces the prior output. A bad
input does not overwrite a good output. Repeating a complete monthly snapshot
rebuilds the same source claims and group IDs; it does not infer removals from
an incomplete fetch. A future source collector must keep its own retrieval
timestamp and source-specific permission state. The current upload has no
per-product observation date, so no such date was invented.

`observations` stores every original row, with the literal note columns,
accords and source URL. `observation_notes` stores separately parsed notes;
accords never become notes. The 33 doevent rows with prose in pyramid columns
use only their separate `all_notes` field. `identity_groups` stores conservative
case/space candidates: punctuation survives so Commodity `Book`, `Book-` and
`Book+` remain separate. Groups with disagreeing note lists have a null
`representative_observation_id`; nothing unions their lists. The selected row
for a nonconflicting group remains a **dataset-listed claim**, not a verified
product note list. `identity_search` is an FTS4 index for private review.

The shipped Android catalogue still contains ten hand-checked products. Its
schema and source rules are separate from this private research database.
For fresh source acquisition, prefer direct, permitted brand feeds or reviewed
product pages with their own source URLs. Open Beauty Facts supplies identity
and barcode candidates, not marketing scent notes; its INCI ingredients cannot
fill this gap. The Aromo-derived research release is an additional lead, but
its identifiable product data and reuse permission have not been established.
