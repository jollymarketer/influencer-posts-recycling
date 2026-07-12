# Design: Blog-Topic-Mining aus Influencer-Scrape (Option A)

Date: 2026-06-02
Project: Jolly Influencer Post Recycling
Status: Approved (design), pending implementation plan

## Problem

The daily influencer-scrape pipeline scores all scraped posts in-memory and
persists only the single daily winner to Notion (`run_research.py:81,93`).
Every non-winning post is discarded. These discarded posts carry signal about
emerging B2B themes that would make good Jolly Marketer blog topics, but that
signal is thrown away each day.

The Jolly Blogging Agent (separate project) needs a topic source. Its Notion
queue is currently empty. This feature mines blog-topic candidates from the
already-paid-for influencer scrape, with zero additional Apify cost.

## Decisions (locked)

| Decision | Choice |
|----------|--------|
| Output destination | Own, decoupled Topic-Ideas Notion DB (not the Blogging Agent queue) |
| Raw-post store | Supabase, schema `blog_content_mining` |
| Trigger | Hook into existing daily Railway run; cluster on Friday (weekday 4, UTC) |
| Clustering method | Single-pass LLM (Claude), one call/week |
| Filter | Blog-Score threshold 70, max 5 themes/week (Top-5) |

## Non-Goals

- No auto-feed into the Blogging Agent generation queue (human promotes manually).
- No embedding/vector clustering (volume does not justify it).
- No separate Railway service (clustering runs inside the daily entrypoint).
- No change to the existing daily winner/draft/image flow.

## Architecture

All changes live in the Jolly Influencer Post Recycling repo (own git). Two parts.

### Part A — Persist all scraped posts (every daily run)

New `tools/supabase_db.py`: minimal REST wrapper over PostgREST, raw `requests`
in the same style as `tools/notion_db.py`. Reads `SUPABASE_URL` +
`SUPABASE_SERVICE_KEY` from `.env`. Targets schema `blog_content_mining` via
PostgREST `Accept-Profile` / `Content-Profile` headers.

Functions:
- `upsert_posts(posts: list[dict]) -> int` — upsert on conflict `post_url`,
  returns count written.
- `get_posts_since(days: int) -> list[dict]` — read posts with
  `post_date >= now - days`, for the weekly clustering window.

New Supabase table `blog_content_mining.influencer_posts`:

```sql
create schema if not exists blog_content_mining;

create table if not exists blog_content_mining.influencer_posts (
    post_url    text primary key,
    source      text not null,            -- 'linkedin' | 'substack'
    influencer  text,
    post_text   text,
    post_date   date,
    likes       integer default 0,
    comments    integer default 0,
    shares      integer default 0,
    scraped_at  timestamptz not null default now()
);

create index if not exists influencer_posts_post_date_idx
    on blog_content_mining.influencer_posts (post_date);
```

Hook in `run_research.py` after Schritt 2 (scrape), before scoring: call
`upsert_posts(new_posts)` with ALL posts (winners + losers). Wrapped in
try/except, non-fatal: a Supabase failure logs a warning and the daily
winner/draft/image flow continues unaffected.

### Part B — Weekly clustering (Friday)

New `tools/topic_clusterer.py`:
- `cluster_topics(posts: list[dict], recent_idea_titles: list[str]) -> list[ThemeCandidate]`
- One Claude call. Input: all posts from the 7-day window, each compacted to
  `influencer + post_text[:500] + engagement`.
- Prompt instructs Claude to group posts into 3-8 themes. Per theme:
  - `theme_label`
  - `support_count` (how many posts back the theme)
  - `sample_influencers`
  - `blog_score` 0-100, weighted across: SEO/search intent, evergreen
    potential, cluster support depth, fit to Jolly B2B-DACH ICP
  - `suggested_title_en`, `suggested_title_de`, `keyword_en`, `keyword_de`
- Themes whose label/title matches any `recent_idea_titles` are excluded
  (week-over-week dedup, same pattern as `get_recent_linkedin_drafts`).

New `tools/topic_ideas_db.py`:
- `get_recent_idea_titles(limit: int) -> list[str]` — read recent theme titles
  from the Topic-Ideas Notion DB for dedup.
- `write_candidates(candidates: list[ThemeCandidate]) -> int` — write each
  candidate as a Notion page.

New Topic-Ideas Notion DB (created once via a setup script, pattern mirrors the
Blogging Agent `create_notion_db.py`). Properties:
- `Title` (title) — theme label
- `Suggested Title EN` (rich_text)
- `Suggested Title DE` (rich_text)
- `Keyword EN` (rich_text)
- `Keyword DE` (rich_text)
- `Blog Score` (number)
- `Cluster Size` (number)
- `Source Influencers` (rich_text)
- `Supporting Posts` (rich_text) — newline-joined post URLs
- `Status` (select: New / Promoted / Rejected)
- `Created` (created_time)

New entrypoint `run_topic_mining.py`:
1. `get_posts_since(7)` from Supabase.
2. If `< 2` posts: log + skip.
3. `get_recent_idea_titles()` from Notion.
4. `cluster_topics(posts, recent_idea_titles)`.
5. Filter `blog_score >= 70`, sort desc, take Top-5.
6. `write_candidates(...)` to Notion.
Standalone-runnable for manual trigger and testing.

Trigger in `run_research.py` `main()`. CAUTION: `main()` has early `return`
statements (no new posts at line 77, no winner at line 97). The Friday trigger
must NOT sit after those, or clustering is skipped on quiet days. Refactor:
extract the daily logic into `run_daily()` (keeps its early returns), then have
`main()` call `run_daily()` and afterwards unconditionally evaluate the Friday
branch:

```python
def main():
    run_daily()                                  # may return early internally
    if datetime.now(timezone.utc).weekday() == 4:  # Friday, UTC
        try:
            run_topic_mining()
        except Exception as e:
            print(f"  Topic-Mining fehlgeschlagen (nicht kritisch): {e}", file=sys.stderr)
```

Clustering reads from Supabase, so it runs regardless of whether today's scrape
found posts or produced a winner.

## Data Flow

```
Daily (Tue-Fri 07:00 UTC cron):
  scrape  ->  upsert ALL posts to Supabase  ->  (existing) score/winner/Notion-draft

Friday additionally:
  read 7d Supabase  ->  Claude cluster+score  ->  dedup vs recent ideas
    ->  filter score>=70, Top-5  ->  Topic-Ideas Notion DB
    ->  (manual) Richard reviews, promotes winners into Blogging Agent
```

## Error Handling

- Persistence failure: log warning, continue. Never blocks daily winner flow.
- Clustering failure: log warning, continue. Daily run already succeeded.
- Empty 7-day window or `< 2` posts: skip clustering, log.
- Claude returns unparseable output: log, write nothing, do not crash.

## Testing (TDD, all mocked, no network/no spend)

- `supabase_db`: mock `requests` — upsert payload shape, on_conflict, dedup,
  `get_posts_since` params.
- Persist hook: all posts passed through, non-fatal on Supabase error.
- `topic_clusterer`: mock Claude response — theme parsing, score-threshold
  filter (>=70), Top-5 cap, recent-title dedup, `<2` posts skip.
- `topic_ideas_db`: mock Notion — property mapping, recent-title read.
- Friday branch: weekday gate (Friday triggers, other days skip).

## Cost

- Persistence: free (Supabase REST).
- Clustering: 1 Claude call/week, ~$0.10-0.40.
- Apify: zero additional (reuses the daily scrape).
- First real clustering run is the first spend; approval will be requested then.

## One-Time Setup (requires Richard / approval)

1. Add `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` to the Influencer `.env` and the
   Railway service env.
2. Create `blog_content_mining` schema + `influencer_posts` table in Supabase
   (DDL above), applied via Supabase SQL editor or CLI.
3. Create the Topic-Ideas Notion DB, share it with the integration, put its DB
   id in `.env` (`TOPIC_IDEAS_DB_ID`).
4. `requirements.txt`: no new dependencies (requests + anthropic already present).

## Open Items For The Plan

- Confirm the Claude model for clustering (Haiku cheap vs Sonnet better
  grouping quality). Default proposal: Sonnet for grouping quality, revisit if
  cost matters.
- Confirm dedup matching strategy for recent idea titles (exact vs fuzzy).
  Default proposal: case-insensitive substring/normalized match, kept simple.
