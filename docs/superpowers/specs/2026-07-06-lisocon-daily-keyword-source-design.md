# Lisocon Daily Keyword Source — Design

**Date:** 2026-07-06
**Approved:** Richard (chat, incl. ~4 EUR/Monat Apify cost)

## Goal

The lisocon daily pipeline currently sources only the curated influencer list
(LinkedIn profiles + Substack). Add LinkedIn-wide keyword search as an
additional source in Schritt 2, so trending posts on InTO core topics compete
in the same daily scoring pool.

## Architecture

- Reuse `tools/linkedin_keyword_scraper.scrape_keyword_posts` (Apify
  `harvestapi/linkedin-post-search`). It already returns the shared post dict,
  dedupes against `existing_urls`, and filters hiring ads.
- New config block in `clients/lisocon/config.py`: `DAILY_KEYWORD_SEARCH`
  (keywords, max_posts, posted_limit) plus feature flag
  `FEATURES["keyword_source_daily"] = True`.
- Jolly config does not define the flag -> `.get()` falsy -> no behavior
  change for the jolly tenant.
- `run_research.run_daily` Schritt 2b: when the flag is set, call the keyword
  scraper with `existing_urls` = Notion winner URLs + posts already scraped
  this run (in-run dedupe). Extend `new_posts`; same 0-60 scorer decides.
- Errors are non-fatal (same pattern as LinkedIn/Substack sources): a broken
  keyword scrape must never block the influencer path.
- Keyword posts are not persisted to Supabase (lisocon has
  `supabase_persist: False`; the jolly mining path is untouched).

## Parameters

- `posted_limit="week"`: matches the deliberate lisocon 7-day content pool
  (SCRAPE `max_age_hours: 168`; losers re-compete daily, only winners are
  blocked via Notion URL dedupe).
- `max_posts=10` per keyword, sort by relevance.
- No virality floor (`min_virality=0`): fresh niche posts carry little
  engagement; the scorer's engagement component weighs it instead.

## Keywords (approved 2026-07-06)

EN: multilingual technical documentation; documentation localization;
DTP localization; InDesign localization; DITA localization; CCMS
DE: Fremdsprachensatz; mehrsprachige Dokumentation; Redaktionssystem

Deliberately narrow (InTO sweet spot: docs x multilingual x layout/publishing).
Broad terms like "technical documentation" rejected as too noisy.

## Cost

9 keywords x 10 posts x $0.002 = ~$0.18/run, 4-5 runs/week -> under 4 EUR/month.
0-result queries cost $0.001 (fine for narrow keywords).

## Testing

- Unit tests for the new step-2b helper: flag off -> scraper not called
  (jolly regression guard); flag on -> posts merged, dedupe applied,
  scraper errors non-fatal.
