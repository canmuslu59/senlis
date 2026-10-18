# SENLIS Commerce v5 — Closed permanently

Closed on 2026-10-18 by owner instruction. Commerce v5 must not be resumed.

## Preserved data

- Canonical data branch: `data/commerce-v5-20261007`
- Frozen safety snapshot: `archive/commerce-v5-final-20261018`
- Snapshot commit: `ef2eb6f600a7dfdd0c890f89327dc697a96673b6`
- Snapshot timestamp: 2026-10-18T20:56:49Z

Snapshot summary:
- Scope: 174,259 products
- Tasks: 44,848 / 47,763 completed (93.897%)
- Pending tasks: 2,915
- Pages: 35,902 / 38,221 completed (93.933%)
- Verified-price products: 4,859
- In-stock products: 4,616
- Turkey in-stock products: 4,615

## Shutdown action

The following Commerce v5 execution paths were deliberately removed from
`feature/commerce-global-v5-20261006`:

- `.github/workflows/commerce-queue-v5.yml`
- `.github/workflows/commerce-resume-v5.yml`
- `.github/workflows/commerce-full-v5.yml`

Scanner/runtime code and accumulated data were intentionally retained for auditability.
Do not restore or run the Commerce v5 workflows unless the repository owner explicitly reverses this decision.
