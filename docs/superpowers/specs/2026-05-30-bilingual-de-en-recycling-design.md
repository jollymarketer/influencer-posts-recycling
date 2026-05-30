# Design: Bilingual DE + EN Post Recycling

Date: 2026-05-30
Project: Influencer Posts Recycling
Status: Approved (brainstorming complete)

## Problem

The daily pipeline produces exactly one German LinkedIn draft per winning post,
saves it to Notion as "Ready to Review", and fires a Make email alert. Richard
wants each recycled post available in two languages, posted the same day in two
slots: German in the morning, English in the afternoon. He also wants room to
inject his own idea into the post.

## Decisions (from brainstorming)

1. Publishing stays manual, exactly as today (Notion review, Make email alert,
   Richard posts manually or via Buffer). No LinkedIn API, no auto-poster. The
   morning/afternoon split is metadata on the entry, not a scheduler.
2. The cron stays fully automatic. The AI invents its own angle as it does today.
   Richard injects his own idea during the manual edit step before posting. No
   code change is needed for the "own idea" part.
3. The English version is written natively and independently, same core thesis
   and own thought, NOT a 1:1 translation. The DACH-specific language rules are
   dropped for EN; the thought-leadership structure is otherwise the same.
4. One shared image with English text, used for both the DE and EN post. Richard
   accepted that the DE post then carries English image text (half the kie.ai
   cost vs. two images).
5. One Notion entry holds both drafts. The EN draft lives in a page-body block
   (no Notion schema change required). DE keeps its existing property + body.
6. Slot assignment: DE = morning (Vormittag), EN = afternoon (Nachmittag). Stored
   as labels in the page-body headings.
7. Generation approach A: two LLM calls (DE call + separate native EN call). The
   image is built from the EN call's soundbyte + infographic skeleton.

## Architecture & Data Flow

Steps 1-4 of `run_research.py` (scrape, score, pick winner) are unchanged.
Changes start at step 5:

```
5a. DE generation  -> existing DACH_POST_PROMPT, unchanged. Use only the post text.
5b. EN generation  -> new EN_POST_PROMPT (native English, no DACH rules).
                      Returns: EN post + EN soundbyte + EN infographic skeleton.
6.  Image          -> generated once, from the EN soundbyte / EN skeleton
                      (English image text). Existing kie.ai infographic-first logic.
7.  Notion         -> ONE entry: DE draft + EN draft + shared image
                      + EN infographic skeleton + slot labels. One Make email.
```

Order rationale: DE -> EN -> image -> Notion. The image comes after EN because
its soundbyte and skeleton are the EN call's output.

## Components & Interface Changes

### `tools/post_scorer.py`

- New constant `EN_POST_PROMPT`: same thought-leadership build as
  `DACH_POST_PROMPT`, but:
  - English language, native phrasing.
  - DACH language prohibitions removed (no "Mittelstand"/"DACH" label rules).
  - Same output markers `===POST=== / ===SOUNDBYTE=== / ===KONTEXT=== /
    ===INFOGRAFIK===` so the existing parsing logic is reused.
  - English hashtags.
- `generate_post_and_image_prompt(post)` return signature changes from
  `(linkedin_draft, image_prompt, infographic_skeleton)` to
  `(de_draft, en_draft, image_prompt, infographic_skeleton)`.
  - `de_draft` comes from the existing DACH call (post text only; its German
    soundbyte/infographic are no longer used for the image).
  - `en_draft`, `image_prompt`, `infographic_skeleton` come from the new EN call.
  - The response-parsing helper (split on `===` markers) is reused for both calls;
    if it is currently inline, extract it into a small helper so both calls share it.
- `build_infographic_prompt(skeleton, language=...)` is called with the EN
  skeleton and `language="English"`.

### `tools/notion_db.py`

- `update_with_draft(...)` gains parameter `en_draft: str = ""`.
  - DE draft: unchanged (property `LinkedIn Draft` truncated to 2000 + body block),
    body heading becomes `LinkedIn Draft DE (Slot: Vormittag)`.
  - EN draft: appended as page-body block(s) under heading
    `LinkedIn Draft EN (Slot: Nachmittag)`. No new Notion property.
  - Shared image: unchanged (`Image` property + image block).
  - Infographic skeleton block: unchanged block name `Infografik-Skelett (Canva)`,
    now carrying EN content (matches the EN image).
  - Make webhook: one email as today. Optional payload field `has_en: true` may be
    added for subject differentiation; not required.
- `create_post_entry(...)`: unchanged (stores original post).

### `run_research.py`

- Step 5: unpack the new 4-tuple from `generate_post_and_image_prompt`.
- Guard: if `de_draft` is empty -> abort with `sys.exit(1)` (as today; DE is the
  mandatory post).
- If `en_draft` is empty -> substitute placeholder
  `[EN-Generierung fehlgeschlagen - manuell nachziehen]`, keep status
  `Ready to Review`, do not abort.
- Step 6: image generation from the EN-derived prompt (existing infographic-first
  fallback logic preserved).
- Step 7: pass `en_draft` to `update_with_draft`.

## Error Handling

- DE call empty/error -> abort, no Notion update (mandatory post).
- EN call empty/error -> save DE anyway; EN block gets the failure placeholder;
  status stays `Ready to Review`. The day's post is not lost.
- Image error -> existing `Image Failed` status logic, applied to the shared image.
  Both drafts still land in Notion.

## Testing

- The project has no test harness today (only `requirements.txt`, no pytest).
- Add a single pure-function unit test for the EN response parser (splitting on
  `===POST=== / ===SOUNDBYTE=== / ===INFOGRAFIK===`). No API calls, no cost.
- Manual verification: one real cron dry-run, confirming one Notion entry with both
  drafts, slot headings, and one shared EN image. This costs 1x kie.ai + 2x Sonnet
  and requires Richard's explicit spend approval before running.
- Do NOT build an Anthropic/kie.ai mock framework (overkill for this glue change).

## Cost Note

Per run: 2 Sonnet calls instead of 1 (Sonnet is cheap, ~cents) + still 1 kie.ai
image (unchanged). Net additional cost is minimal. Spend approval required before
the live dry-run.

## Out of Scope

- Auto-publishing to LinkedIn (Buffer or API).
- A real scheduler for the morning/afternoon slots (slots are metadata only).
- A manual "own idea" injection step in code (handled in manual review/edit).
- A new searchable Notion `LinkedIn Draft EN` property (optional manual add by
  Richard; default path stores EN in the body block only).
