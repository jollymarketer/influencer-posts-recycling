# Format Router — Design

Date: 2026-06-04
Status: Approved

## Problem

The recycler rewrites one scraped winner per day into a DACH-German + English
thought-leadership post. Every post uses the SAME fixed structure
(Hook -> Problem -> Proof -> Close). The output is structurally identical day
after day, which produces format fatigue for the audience.

Source insight: Pierre Herubel, "How to influence buyers with LinkedIn." The
article's first distribution pillar is **variety of formats** — different post
structures prevent fatigue and serve different buyer-journey moments. The
infographic-drives-saves idea from the same author is already implemented
(`post_scorer.py`, `build_infographic_prompt`); this design adds the format
variety pillar.

## Goal

Rotate the generated post across THREE distinct structures instead of one,
choosing the best-fitting structure per winner while never repeating the
immediately previous one.

## Scope

Additive change. No flow rewrite. Touches 3 files + 1 new Notion property +
1 one-time setup script.

- `tools/post_scorer.py` — format definitions, structure injection, `pick_format`
- `tools/notion_db.py` — write Format property, `get_recent_formats`
- `run_research.py` — wiring
- `scripts/add_format_property.py` — one-time idempotent Notion schema setup
- `tests/` — TDD coverage

Explicitly OUT of scope: Backstory and Case Study formats. Both require Richard's
real lived experience / real client results. The recycler rewrites OTHER people's
posts, so generating those formats would fabricate proof — violates the
no-fabrication rule. Only stance/framework formats (no invented proof) are built.

## The three formats

All three keep the EXISTING shared rules unchanged: tone, hard language bans
(no "Mittelstand", max one "DACH", etc.), E3 quality check, formatting rules,
hashtags, and the output contract (`===POST===` / `===SOUNDBYTE===` /
`===KONTEXT===` / `===INFOGRAFIK===`). Only the "Post-Struktur" block swaps.

### Opinion
- Hook: provocative thesis / contrarian claim against a common practice
- Tension: what most teams believe or do, and why it is flawed
- Position: own contrarian take, reasoned from practice
- Close: principle loop

### POV
- Hook: name a lens / reframe
- Framework: 2-4 named parts of a mental model
- Application: how to use it
- Close: principle loop

### Signature — "Glaube vs. Realität"
- Hook: "Was [Persona] glaubt:" — the belief
- Realität: what actually drives the outcome
- 2-4 belief <-> reality contrasts
- Close: the operating principle
- Soft-steers the Part-4 infographic recommendation toward the comparison table
  (Vergleichstabelle), which already exists. Soft, not forced.

## Router: pick_format

New function in `post_scorer.py`.

Signature: `pick_format(post: dict, recent_formats: list[str]) -> str`

- Model: `claude-haiku-4-5-20251001` (cheap, same model as scorer).
- Input to prompt: winner post text (truncated to 3000 chars) + the recent
  format list.
- Rule: EXCLUDE the most recently used format (no back-to-back repeat). From the
  remaining formats, pick the best topic fit. If `recent_formats` is empty, pick
  the best topic fit among all three.
- Returns one of the canonical keys: `"Opinion"`, `"POV"`, `"Signature"`.
- Robustness: if the LLM returns anything unrecognized, fall back to the first
  format not equal to the most recent (deterministic), or `"Opinion"` if no
  recent. Never raise — a bad pick must not block the daily run.

Edge note: only 3 formats exist. With perfect even distribution one repeats
after 3 posts. Accepted — the goal is variety, not unpredictability. The only
hard guarantee is "never the same structure twice in a row."

## Notion property "Format"

- New select property named `Format`, options: `Opinion`, `POV`, `Signature`.
- Created once via `scripts/add_format_property.py` (idempotent: checks whether
  the property already exists before PATCHing the database schema).
- `update_with_draft` writes the chosen format into the property. Wrapped
  non-fatal, same pattern as the infographic block — a Notion write failure must
  not break the run.
- New `get_recent_formats(limit: int = 3) -> list[str]` reads the Format select
  from the most recent entries (same status filter + sort as
  `get_recent_linkedin_drafts`). Tolerant: if the property is missing or empty on
  a page, that page contributes nothing; an entirely missing property yields
  `[]`, and the router fallback handles it.

## Wiring (run_research.py)

Between Step 4 (winner chosen) and Step 5 (generation):

```
recent_formats = get_recent_formats()          # non-fatal: [] on error
fmt = pick_format(winner, recent_formats)       # never raises
print(f"  Format gewaehlt: {fmt}")
```

Then thread `fmt` through:
- `generate_post_and_image_prompt(winner, fmt)` — injects the structure block
- `update_with_draft(..., post_format=fmt)` — persists it

`get_recent_formats` call is wrapped so any failure degrades to `[]` (router
still works), consistent with how `get_recent_linkedin_drafts` is treated.

## Structure injection (post_scorer.py)

Refactor: extract the current inline "Post-Struktur" block out of
`DACH_POST_PROMPT` and `EN_POST_PROMPT` into a `{structure_block}` placeholder.
Define a `FORMAT_STRUCTURES` mapping: `format_key -> {"de": ..., "en": ...}`.
`generate_post_and_image_prompt(post, post_format)` formats the prompt with the
selected block. Default `post_format="Opinion"` keeps the function callable
without a format (back-compat for any direct callers / tests).

## Tests (TDD)

`pick_format`:
- recent=["Opinion"] -> never returns "Opinion"
- recent=[] -> returns a valid format (no crash)
- unrecognized LLM output -> deterministic fallback, never raises
- (LLM call mocked)

Structure injection:
- each of the 3 keys yields a prompt containing its distinct structure text
- DE and EN both injected

Notion:
- `update_with_draft` payload includes the `Format` select when `post_format` set
- `get_recent_formats` parses select values from a mocked query response
- missing Format property in response -> `[]`
- (`requests` mocked)

## Risks / accepted trade-offs

- Topic-format mismatch: mitigated by best-fit selection, not forced rotation.
- 3-format ceiling: one structure recurs every ~3 posts. Accepted.
- Notion schema dependency: handled by idempotent setup script + non-fatal
  write + tolerant read.
