# Content Matrix Coverage — Design

Date: 2026-07-08
Status: Approved (design approved by Richard; open inputs listed at the end)

## Problem

The engine covers roughly 3.5 of the 9 boxes of the Ideal Customer-Led Content
Matrix (Douwe Wester): 3 content jobs (Perspective / Proof / Promotion) times
3 buyer stages (Awareness / Education / Selection).

- All 4 existing formats (Opinion, POV, Signature, Story) live in the
  Perspective row (Story partially Proof x Awareness, but generic patterns
  only — the no-fabrication rule blocks real cases and none are stored).
- The Selection column is empty: no comparison, red-flag, case-study or
  objection-handling format exists.
- The Proof row has no real client data to draw from; the Promotion row is
  actively banned by the shared prompt rule "no DM CTA".
- Neither scoring, format routing, nor Notion tracking knows the matrix.
  Coverage follows whatever influencers post, which skews to
  Perspective x Awareness/Education.

Result: the engine is a very good Perspective generator that never fills the
boxes that convert (Proof x Selection, Promotion x Education/Selection).

## Decisions (Richard, 2026-07-08)

1. Model: **Recycling + assets.** Every post stays a recycled post; the router
   bends it into a target box. Proof content may only cite a client asset
   whitelist. Boxes a client cannot serve are excluded per client.
2. Steering: **Quota with best-fit.** A coverage tracker over the last 10
   posts computes deficits against a target mix; the most underserved box
   becomes the mandatory target of the next run. Never force a weak post.
3. Promotion row fully enabled for Jolly (lead-magnet CTAs, offer posts,
   discovery CTAs), hard-capped via the mix. Lisocon stays restricted.
4. Assets live in `clients/<name>/config.py` (versioned, numbers pinned).
5. Target mix: rows 50 / 30 / 20 (Perspective / Proof / Promotion),
   Selection-column floor 2 of 10, Promotion cap 2 of 10.

## Scope

Additive change, same architecture as the format router. Touches:

- `tools/content_matrix.py` — NEW: box model, format-to-box map, quota logic
- `tools/post_scorer.py` — 6 new format structure blocks, box-fit re-rank
  prompt, asset injection, numbers guard
- `tools/notion_db.py` — Matrix-Job / Matrix-Stage / Asset properties,
  `get_recent_boxes`, `get_recent_assets`
- `run_research.py` — wiring (target box step, asset pick, property writes)
- `clients/jolly/config.py`, `clients/lisocon/config.py` — MATRIX config,
  PROOF_ASSETS / OFFERS / LEAD_MAGNETS, new format tokens
- `scripts/add_matrix_properties.py` — one-time idempotent Notion schema setup
- `workflows/content_generation.md` — manual path gets the same rules
- `tests/` — TDD coverage

## The matrix model

### Box-to-format map

| Box | Format | Status |
| --- | --- | --- |
| Perspective x Awareness | Opinion | existing |
| Perspective x Education | POV, Signature | existing |
| Perspective x Selection | Comparison | new |
| Proof x Awareness | Story | existing |
| Proof x Education | Method | new |
| Proof x Selection | CaseProof | new |
| Promotion x Awareness | Debate | new |
| Promotion x Education | Magnet | new |
| Promotion x Selection | Offer | new |

6 new formats. Each is a DE+EN structure block in `FORMAT_STRUCTURES`, same
build as the existing four. All shared rules (tone, language bans, E3 check,
output contract `===POST===` etc.) stay unchanged; only the structure block
and the CTA policy swap.

### New formats

- **Comparison** (Perspective x Selection): decision criteria, red flags,
  "what to look for in X", buy vs build vs hire, objection handling. Never
  names competitors negatively (client tokens keep enforcing this; for
  lisocon the status-quo-as-enemy rule stays).
- **Method** (Proof x Education): step-by-step breakdown or before/after
  logic of a method, operator detail. Asset optional; without an asset it
  argues from pattern observation, never invented specifics.
- **CaseProof** (Proof x Selection): recycled frame carried by exactly ONE
  entry from PROOF_ASSETS (real, pinned numbers). Asset mandatory.
- **Debate** (Promotion x Awareness): lightweight — a sharply arguable thesis
  whose whole point is the explicit reply prompt. No DM CTA.
- **Magnet** (Promotion x Education): a save-worthy artifact in the post plus
  a comment-CTA on one entry from LEAD_MAGNETS. Asset mandatory.
- **Offer** (Promotion x Selection): one entry from OFFERS with a clear DM or
  discovery CTA. No fake scarcity, no invented pricing. Asset mandatory.

### CTA policy per format

The current blanket "Kein DM-CTA" moves from the shared rules into the
structure blocks: it stays hard for all Perspective and Proof formats and for
Debate; Magnet allows exactly one comment-CTA; Offer allows exactly one DM or
discovery CTA.

## Quota logic (`tools/content_matrix.py`)

Pure Python, no LLM, fully unit-testable.

- `pick_target_box(recent_boxes, client_matrix) -> box | None`
  - `recent_boxes`: last 10 (job, stage) tuples from Notion (status filter as
    today: Posted / Approved / Ready to Review).
  - Row deficits vs mix 50/30/20, Selection floor 2/10, Promotion cap 2/10.
  - Priority: Selection floor violation first, then largest row deficit.
    Promotion targets are skipped while the window already holds >= cap
    promotion posts.
  - A row counts as deficient when actual < floor(target share * 10) - 1,
    i.e. under target by a full post. Floor violation: fewer than 2 Selection
    posts in the window. Nothing deficient -> `None` (free best-fit run).
  - Cold start (fewer than 10 classified posts): only the Selection floor is
    enforced once >= 5 posts are classified; before that always `None`.
- Promotion formats (Debate, Magnet, Offer) are ONLY selectable when the
  tracker targets them. In free runs the router picks among the client's
  whitelisted non-promotion formats — this makes the cap deterministic.
- Client whitelist is computed at config load: declared box whitelist MINUS
  boxes whose required asset list is missing or empty (deterministic guard,
  no prompt trust).

## Source selection under a mandatory box

1. Score the daily pool as today (6 dimensions, MIN_SCORE 25 unchanged).
2. Take the top 10 scored posts, one Haiku call ranks their fitness to carry
   the target box's format (0-10 each).
3. Pick the best post with fit >= 6. If none reaches 6 (or the needed asset
   is unavailable), the deficit stays open, the run falls back to free
   best-fit and logs the miss. No quality sacrifice, no forced posts.

Cost: +1 Haiku call per run, only when a mandatory box is set.

## Asset layer

New per-client config blocks, exactly like lisocon's SOCIAL PROOF block today
but structured:

```python
PROOF_ASSETS = [
    {"id": "hoermann", "claim": "...", "metric": "69% Kostensenkung",
     "context": "offiziell freigegeben"},
]
OFFERS = [
    {"id": "icp-sprint", "name": "...", "promise": "...", "cta": "dm"},
]
LEAD_MAGNETS = [
    {"id": "...", "name": "...", "artifact": "...", "cta": "comment"},
]
```

Guards (lesson from the Clay de-emphasis review: prompt policy is advisory,
enforcement needs a code backstop + pin tests):

- **Whitelist guard**: empty/missing asset block -> dependent boxes drop out
  of the client whitelist at load time.
- **Numbers guard**: CaseProof drafts are regex-checked — every percentage,
  currency amount and "x-fach/x times" figure must appear verbatim in the
  asset whitelist. One retry on violation, then downgrade to Method.
- **Asset anti-repeat**: least-recently-used pick via the new Notion Asset
  property, so the same case number does not run every two weeks.
- The existing no-fabrication prompt text stays in all formats.

## Notion

- New select properties **Matrix-Job** (Perspective/Proof/Promotion) and
  **Matrix-Stage** (Awareness/Education/Selection), plus **Asset** (select,
  asset id). Written non-fatally like Format / Infografik-Typ today.
- `get_recent_boxes(limit=10)`, `get_recent_assets(limit=5)` with the same
  status filter as the existing getters.
- Seed script `scripts/add_matrix_properties.py`, idempotent, same pattern as
  `add_format_property.py`.
- Each run logs actual coverage of the last 10 posts vs target.

## Multi-tenant

- **jolly**: all 9 boxes declared; until Richard supplies PROOF_ASSETS,
  OFFERS and LEAD_MAGNETS the guards keep CaseProof, Magnet and Offer off.
  Comparison, Method and Debate work immediately (no assets required).
- **lisocon**: Promotion x Selection off (playbook: no demo CTA, no product
  pitch), Magnet off (no lead magnets exist), Debate on (reply prompt only),
  CaseProof on with Hörmann (69% Kostensenkung), WAGO (80% Kostenreduktion,
  17 Sprachen), Stiebel Eltron (30 Sprachen) as pinned PROOF_ASSETS. All
  existing hard rules (never prices, enemy = status quo, InTO never the hero)
  stay via the existing tokens.
- New clients: fill the config pattern (MATRIX + assets + tokens), done.

## Supersedes

The format-router spec (2026-06-04) excluded Case Study formats because the
recycler would fabricate proof. This design lifts that exclusion the safe
way: proof numbers come only from the pinned per-client whitelist, enforced
by the numbers guard.

## Out of scope

- Native LinkedIn polls (UI-only feature) and carousel/PDF documents — the
  engine renders a single image; Debate/Magnet work text-first.
- Auto-publishing; review stays human-gated in Notion.
- Retro-classification of historical posts (optional later; tracker starts
  cold and converges within 10 posts).
- Changes to blog topic mining / JBA bridge.

## Test plan

- Unit: quota math (deficits, floor, cap, cold start, cap-block), whitelist
  guard (missing assets -> boxes off), numbers guard (foreign figure ->
  retry -> downgrade), format structure pin tests (all 6 new blocks, DE+EN),
  `get_recent_boxes` parsing, promotion-only-when-targeted rule.
- Integration: dry run against a fake pool asserting the full chain
  (deficit -> target box -> re-rank -> asset pick -> property writes).
- Existing suite (104 green) must stay green.

## Rollout

1. Jolly first. NOTE: this repo auto-deploys on master push — merge is go-live.
2. Observe one week of runs (coverage log line).
3. Then enable the lisocon whitelist.
4. `workflows/content_generation.md` (manual path) is updated in the same
   change — it was the unprotected path once before.

## Open inputs (Richard)

Blocking only the asset-gated formats, nothing else:

- Jolly PROOF_ASSETS: case studies with approved, exact numbers.
- Jolly OFFERS: current offer(s), e.g. ICP sprint, with CTA wording.
- Jolly LEAD_MAGNETS: existing downloadable artifacts, if any.
