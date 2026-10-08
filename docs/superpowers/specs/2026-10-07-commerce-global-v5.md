# SENLIS commerce v5

The user authorizes a new scan of the existing 174259 identities, adding Trendyol, official brand sites where verifiable, and original TRY/EUR/USD offers. Main, product identities and v3/v4 campaigns remain unchanged.

## Design
- Dedicated v5 code/state branches; immutable campaign code and manifest hashes. Durable, serial queue checkpoints every 5 minutes/50 reads, fail closed on push errors, bounded per-page attempts and persisted host cooldowns. Successful pages never refetched on resume.
- Read public Trendyol product pages and its public A-Z brand directory/brand catalogues. Respect access blocks; no CAPTCHA evasion or hidden marketplace API assumptions. Discover actual brand links from directory/product data, never invent brand IDs. Search pages forbidden by robots are not the crawl mechanism.
- Recheck the previous catalogue URLs and existing direct commercial source URLs with fresh HTTP evidence. Crawl verified official sitemap roots. For other brands attempt official-link discovery from existing reference pages, accepting only explicit official-site links with matching homepage brand identity. Unknown/blocked official discovery is disclosed per brand, never silently marked covered.
- Parse main Product/ProductGroup, explicit selected Shopify variants and Trendyol primary product state. Protect identity, concentration, product form, bottle size and seller. Preserve rejected price observations and specific rejection reasons. Conflicting brand metadata remains review-required, never blindly overridden.
- Store decimal amount, currency, market, seller, source URL, volume, stock, time and response hash. Best offers grouped by currency/market; no exchange conversion, no cross-currency minimum. Conditional/member/cart prices cannot become ordinary verified prices.
- Queue all existing identities. Report catalogue-query coverage, discovery task progress, page progress, price products, in-stock products, currency counts, unavailable pages and blocked/unknown brand coverage separately. Terminal 404 is unavailable, not a runner failure. complete only when tasks are terminal and coverage has no blocked/partial discoveries; absence outside searched sources is never proven.
- Launch gated by tests and a fresh 10-product pilot including Trendyol, official TRY/EUR/USD pages and negative controls. Source blocks do not erase successful results. If a required source's live gate fails, stop before full scan and report evidence.

## Limits
Official website confirmation is conservative. A source directory/catalogue query does not prove worldwide absence. Caps (100 maps per source, 500 catalogue pages, 200000 discovered URLs per source) cause explicit incomplete status, never false success. Initial serial queue: 48 x 90-minute workers; any remaining work remains resumable, not declared done.
