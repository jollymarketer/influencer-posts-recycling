# Lisocon Topic Slate + Persistent Candidate Pool

Date: 2026-07-16
Status: approved by Richard (chat, 2026-07-16)
Tenant: lisocon only, feature-gated. Jolly keeps the existing winner-per-run flow byte-identically.

## Problem

Target output is 4 posts/week for Reinhard + 4 for Jae. The engine produces exactly 1 winner
per run and discards ranks 2-10 after scoring them. Scaling by adding runs multiplies scrape
cost and review mails. Additionally the expensive image step runs before any human has seen
the text, so rejected drafts burn image spend.

## Decisions (from the brainstorming session)

1. Two slate runs per week (Mon + Thu), each presenting a top-10 candidate slate.
2. Jae picks topics for both posters.
3. Model A, three stages / two gates: topic pick -> draft -> text approval -> image.
   The image (most expensive, slowest step) is only generated for approved texts.
4. Single Notion DB, status-driven. No separate slate DB.
5. Candidates that are not picked persist in Supabase and re-compete against new posts.
6. Pool aging: 60 days. Auto-retirement after 3 slate appearances without a pick
   ("3 strikes"). No explicit reject gesture for topics.
7. Slate is hard-quotiert: 5 kaeufer + 5 anwender candidates. If one persona side has
   fewer than 5 candidates above MIN_SCORE, fill from the other side and mark the row.
8. One daily cron run Mon-Fri 07:00 UTC with three phases; scrape+slate only Mon+Thu.
9. Scoring model becomes a per-tenant config value: lisocon uses claude-sonnet-4-6,
   jolly stays on claude-haiku-4-5 (no silent cost increase for the jolly tenant).

## Data model: Supabase `topic_candidates`

New table in the existing `blog_content_mining` schema, accessed via the same raw-PostgREST
style as `tools/supabase_db.py` (service key, custom schema, no RLS concern). The existing
`influencer_posts` table (jolly blog mining) is untouched.

Columns:

- `post_url` text primary key
- `client` text (always "lisocon" for now; keyed for multi-tenant reuse)
- `source` text (linkedin | keyword | substack)
- `influencer` text
- `post_text` text
- `post_date` date
- `likes` / `comments` / `shares` int (frozen at scrape time, never re-scraped)
- `persona` text (kaeufer | anwender)
- `matrix_job` text, `matrix_stage` text
- `voc_hit` text (which of the 5 VoC pains the topic hits, empty if none)
- `topic_angle_de` text (one-sentence German angle: what the post would be about)
- `score_total` int, `scores` jsonb (sub-scores), `reasoning` text
- `state` text: pool | slated | picked | posted | retired
- `times_slated` int default 0
- `first_seen_at` timestamptz, `last_scored_at` timestamptz, `last_slated_at` timestamptz

State machine:

- new scrape -> `pool`
- slate build -> `slated`
- next slate build, not picked -> back to `pool`, `times_slated += 1`
- picked in Notion (Topic Approved) -> `picked`
- published -> `posted`
- `times_slated >= 3` or `first_seen_at` older than 60 days -> `retired`

`retired` and `posted` rows are kept (dedup memory), just never eligible again.

A small `engine_meta` key/value row (or column on a meta table) stores `last_slate_at`
per client for the slate idempotency guard.

## Scoring changes

The scoring call gains three JSON output fields: `persona`, `voc_hit`, `topic_angle_de`.
Every candidate is fully classified at ingest; `pick_persona` and `PERSONA_BALANCE_WINDOW`
are no longer used for lisocon (balance now emerges from the 5/5 slate quota). VoC becomes
a visible per-candidate field instead of living implicitly inside topic_fit.

On slate days the whole active pool (`state = pool`) is re-scored together with the newly
scraped posts. Rationale: the themen_diversitaet criterion depends on what was recently
posted; a frozen two-week-old score lies. Engagement numbers stay frozen from scrape time.

Model: new config value `SCORING_MODEL` per tenant. lisocon = `claude-sonnet-4-6`
(Richard, 2026-07-16), jolly = `claude-haiku-4-5-20251001` (unchanged).

## Notion lifecycle

Two new Status options: **Themenvorschlag** (slate row: topic fields only, no draft, no
image) and **Topic Approved** (Jae's pick gesture).

Full lifecycle:
Themenvorschlag -> Topic Approved (Jae) -> Ready to Review (engine wrote draft)
-> Approved (human text approval) -> engine generates image -> Posting/Posted (Make).

Disapproved remains a text-stage-only gesture. Topic rows have no reject gesture; not
touching a Themenvorschlag means "not this week" (pool, 3-strike counter applies).
Non-picked slate rows are archived by the engine at the next slate build (Notion archive;
the candidate itself lives on in Supabase).

New properties: `Score` (number), `VoC-Treffer` (rich_text), `Themen-Winkel` (rich_text),
`Matrix-Prio` (checkbox, marks the currently deficient quota box). Existing properties
Persona, Poster, Matrix-Job, Matrix-Stage are filled on slate rows too.

Mis-flip safety (incident 2026-07-13): a Themenvorschlag accidentally flipped straight to
Approved has no draft; the existing Make route 3 (draft missing -> Disapproved) catches it.
Additionally the publish filters gain an image-present condition (see Make section).

## Engine flow: one cron, three phases

Cron `0 7 * * 1-5` (Mon-Fri 07:00 UTC) on the existing `lisocon-content-engine` Railway
service, set via GraphQL serviceInstanceUpdate (railway.lisocon.toml stays cron-free by
design). Every run:

- **Phase A (always):** Notion rows with Status=Approved and empty Image -> generate image
  (kie.ai + vision check + logo overlay, unchanged), fill Image property. Only now is the
  row publishable.
- **Phase B (always):** rows with Status=Topic Approved -> Sonnet draft + grammar check +
  numbers guard (CaseProof) as today -> Ready to Review, review-mail webhook fires.
  Pool state -> picked.
- **Phase C (Mon+Thu only):** scrape (profiles, keywords, substack) -> pool upsert ->
  re-score pool + new -> build slate: top 5 kaeufer + top 5 anwender above MIN_SCORE,
  mark the deficient matrix box (Matrix-Prio), write 10 Themenvorschlag rows to Notion,
  pool state -> slated, archive the previous slate and increment `times_slated` on
  non-picked candidates, apply retirement (3 strikes / 60 days). If one persona side
  has fewer than 5 eligible candidates, fill from the other side and mark the row.

Idempotency guard for Phase C: Railway executes the startCommand on every deploy (this is
why the PAUSED guard exists). Before building a slate the engine checks `last_slate_at`
in Supabase; if a slate was already built today, skip. Phases A and B are naturally
idempotent (they only process rows sitting in their trigger status).

Feature gate: `FEATURES["slate_mode"] = True` only in `clients/lisocon/config.py`.
Default False; jolly runs the winner flow unchanged.

Latency envelope: each gate costs at most one working day. Slate Mon -> pick Mon ->
draft Tue -> text approval Tue -> image Wed -> publish Wed/Thu.

## Jae's working surface

Jae keeps working in the one known Notion DB. Mon+Thu there are 10 Themenvorschlag rows;
visible per candidate: Themen-Winkel (one German sentence), Poster, Matrix box, VoC-Treffer,
Score, source link, excerpt. Expected gesture: flip 2 per section (2 Reinhard + 2 Jae) to
Topic Approved. Untouched rows stay in the pool.

No code enforces the 2/2 pick. Over-picking grows the queue; the publish caps
(1/day/poster) regulate outflow. Deliberate YAGNI.

Recommended (not required): a filtered Notion view "Themen-Slate" (Status=Themenvorschlag,
grouped by Poster), and a slate-ready notification to Jae via the existing webhook
mechanism. A short German how-to for Jae is part of the rollout.

## Make changes (minimal)

Both publish scenarios (9506674 Reinhard, 9517006 Jae) gain an additional filter condition:
Image is not empty. Otherwise a text-approved row whose image is still pending (or failed)
would publish without an image / crash the ShareImage module. No other Make changes; the
review-mail scenario and the status guard (9517865) run unchanged. The guard invariant
(Posted only machine-set, in one PATCH with URL + checkbox + date) stays intact.

## Error handling

- Image failure: Status=Image Failed as today, row waits for a human. No auto-retry beyond
  the existing JOB_MAX_ATTEMPTS=2.
- Supabase unreachable on a slate day: Phase C aborts (no slate built from new-only posts,
  which would silently bypass the pool); Phases A and B still run. Error goes to the
  Railway log.
- Scoring failure on individual candidates: skip the candidate, not the run.
- Notion write failures on slate rows: non-fatal per row, logged; the slate may be shorter
  than 10.

## Testing

Repo convention: TDD, pin tests (suite currently 201 green). New pin tests:

- slate quota 5/5 incl. fill-and-mark case
- 3-strike retirement and 60-day aging
- state transitions (pool/slated/picked/posted/retired)
- weekday dispatch (Phase C only Mon+Thu) and slate idempotency guard
- persona/voc_hit/topic_angle_de fields present in scoring JSON
- SCORING_MODEL per tenant (lisocon Sonnet, jolly Haiku)
- feature gate: jolly behavior byte-identical with slate_mode absent/False

## Rollout

Order:

1. Set PAUSED=1 on the lisocon service BEFORE the first push. Every push to master
   deploys and executes one engine run; during implementation each push would otherwise
   trigger an unauthorized live run of the old winner flow (~1 USD + one draft each).
2. Create Supabase table + grants.
3. Code behind the feature gate (multiple commits/pushes are now inert).
4. Add Notion properties + status options; build the "Themen-Slate" view.
5. Extend both Make publish filters (image present).
6. One manual slate run locally as the acceptance test, with Richard watching
   (~1 scrape + 1 pool scoring, < 2 USD, needs explicit spend approval).
7. Remove PAUSED, set cron `0 7 * * 1-5` via GraphQL.
8. Brief Jae (short German how-to).

Migration: the 3 existing Approved Reinhard rows (from 2026-07-06, pre VoC hardening) have
images already and keep publishing unchanged under the new filters (Richard, 2026-07-16:
let them run, no re-read against the VoC red lines).

Estimated running cost: 2 scrapes/week, Sonnet re-scoring ~150 candidates 2x/week
(~5-7 USD/month), 8 Sonnet drafts + 8 images/week at full utilization. Total roughly
18-25 USD/month versus ~4 today. All spend gated on Richard's explicit go.

## Open questions

1. Slate-ready notification target for Jae (mail address / channel) — needed at rollout
   step 8, not blocking implementation. Until decided, the existing review-mail webhook
   (to Richard) is the only notification.
