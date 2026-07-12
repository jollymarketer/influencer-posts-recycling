# Bilingual DE + EN Post Recycling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce both a German and a native-English LinkedIn draft per recycled post, in one Notion entry with slot labels (DE morning, EN afternoon) and one shared English image.

**Architecture:** Keep the daily cron and manual review flow unchanged. After the winner is chosen, run two LLM calls: the existing DACH prompt for the German post, and a new native-English prompt that also yields the soundbyte and infographic skeleton driving the single shared image. Store both drafts as body blocks in one Notion entry.

**Tech Stack:** Python 3, Anthropic SDK (claude-sonnet-4-6), kie.ai image API, Notion REST API, pytest 9.

---

## File Structure

- `tools/post_scorer.py` — add `EN_POST_PROMPT`, extract `_parse_generation_response` helper, change `generate_post_and_image_prompt` to two calls + 4-tuple return.
- `tools/notion_db.py` — `update_with_draft` gains `en_draft` param, appends DE + EN slot body blocks.
- `run_research.py` — unpack the 4-tuple, EN-failure placeholder, pass `en_draft`, request English infographic.
- `tests/test_parse_generation.py` — new: pure-function unit tests for the parser.

---

## Task 1: Extract the response parser into a tested helper

**Files:**
- Modify: `tools/post_scorer.py` (parsing block currently inline in `generate_post_and_image_prompt`, ~lines 484-514)
- Test: `tests/test_parse_generation.py` (create)

- [ ] **Step 1: Write the failing test**

Create `tests/test_parse_generation.py`:

```python
"""Unit tests for the LLM response parser. Pure functions, no API calls."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools.post_scorer import _parse_generation_response


def test_parses_all_four_sections():
    raw = (
        "===POST===\nHook line.\n\n#GTM #RevOps\n"
        "===SOUNDBYTE===\nOne strong line.\n"
        "===KONTEXT===\nCEOs, RevOps\n"
        "===INFOGRAFIK===\nTYP: Eisberg\nMETAPHER: iceberg"
    )
    parts = _parse_generation_response(raw)
    assert parts["post"] == "Hook line.\n\n#GTM #RevOps"
    assert parts["soundbyte"] == "One strong line."
    assert parts["kontext"] == "CEOs, RevOps"
    assert parts["infografik"] == "TYP: Eisberg\nMETAPHER: iceberg"


def test_missing_markers_fall_back_to_raw_post():
    raw = "Just a plain post with no markers."
    parts = _parse_generation_response(raw)
    assert parts["post"] == "Just a plain post with no markers."
    assert parts["soundbyte"] == ""
    assert parts["kontext"] == ""
    assert parts["infografik"] == ""


def test_post_without_kontext_still_parses_soundbyte_and_infografik():
    raw = (
        "===POST===\nBody.\n"
        "===SOUNDBYTE===\nByte.\n"
        "===INFOGRAFIK===\nTYP: Funnel"
    )
    parts = _parse_generation_response(raw)
    assert parts["post"] == "Body."
    assert parts["soundbyte"] == "Byte."
    assert parts["kontext"] == ""
    assert parts["infografik"] == "TYP: Funnel"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "Jolly Automations/Jolly Influencer Post Recycling" && python -m pytest tests/test_parse_generation.py -v`
Expected: FAIL with `ImportError: cannot import name '_parse_generation_response'`

- [ ] **Step 3: Add the helper function**

In `tools/post_scorer.py`, add this function immediately above `def generate_post_and_image_prompt` (before line 467):

```python
def _parse_generation_response(raw: str) -> dict:
    """Zerlegt eine LLM-Antwort an den ===MARKER=== in ihre Teile.
    Gibt dict mit keys post, soundbyte, kontext, infografik zurueck.
    Fehlt ===POST===, gilt der ganze Text als post (Fallback)."""
    parts = {"post": "", "soundbyte": "", "kontext": "", "infografik": ""}

    if "===POST===" in raw:
        post_part = raw.split("===POST===")[1]
        parts["post"] = (
            post_part.split("===SOUNDBYTE===")[0].strip()
            if "===SOUNDBYTE===" in post_part
            else post_part.strip()
        )
    else:
        parts["post"] = raw.strip()

    if "===SOUNDBYTE===" in raw:
        sb = raw.split("===SOUNDBYTE===")[1]
        parts["soundbyte"] = (
            sb.split("===KONTEXT===")[0].strip()
            if "===KONTEXT===" in sb
            else sb.split("===INFOGRAFIK===")[0].strip()
            if "===INFOGRAFIK===" in sb
            else sb.strip()
        )

    if "===KONTEXT===" in raw:
        kp = raw.split("===KONTEXT===")[1]
        parts["kontext"] = (
            kp.split("===INFOGRAFIK===")[0].strip()
            if "===INFOGRAFIK===" in kp
            else kp.strip()
        )

    if "===INFOGRAFIK===" in raw:
        parts["infografik"] = raw.split("===INFOGRAFIK===")[1].strip()

    return parts
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "Jolly Automations/Jolly Influencer Post Recycling" && python -m pytest tests/test_parse_generation.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add tests/test_parse_generation.py tools/post_scorer.py
git commit -m "Add tested _parse_generation_response helper"
```

---

## Task 2: Add the native-English generation prompt

**Files:**
- Modify: `tools/post_scorer.py` (add constant after `DACH_POST_PROMPT`, before line 178)

- [ ] **Step 1: Add the `EN_POST_PROMPT` constant**

In `tools/post_scorer.py`, add directly after the `DACH_POST_PROMPT` triple-quoted string ends (line 176) and before `IMAGE_PROMPT_TEMPLATE`:

```python
EN_POST_PROMPT = """You are Richard from Jolly Marketer (Fractional CMO / GTM as a Service for B2B).

CONTEXT:
{context}

Your task: recycle the following LinkedIn post by {influencer} into a high-quality, native English thought-leadership post. Write it natively in English — do NOT translate German phrasing or sentence structure. Same core thesis, your own added thought, but it must read like it was written in English from scratch.

ORIGINAL POST:
{post_text}

---

PART 1 - LINKEDIN POST (in English):

Audience: founders, CEOs, CROs, CSOs, VPs of Sales and Heads of Sales at B2B SaaS and tech companies (5-250 employees), international.

Tone:
- Write for revenue decision-makers, not for marketers.
- No jargon without explanation. If a term is needed (e.g. ICP = ideal customer profile), define it briefly on first use.
- Natural, fluid writing. Vary sentence length: short sentences for impact, longer ones for explanation and context. No choppy staccato of single-sentence lines. It should read like a smart person talking, not a bullet list.
- Focus on revenue relevance: pipeline, revenue, CAC, sales cycle, predictability.
- No buzzwords, no marketing-speak.
- First person (you are the fractional CMO speaking from practice). Light, natural use of "you" toward the reader is fine.
- The post should feel helpful and human, not AI-generated.

Content rules:
- Use the original content recognizably, but as your own practitioner's framing — not a free reinterpretation.
- Add one original thought that does not appear in the original.
- Stance of an experienced operator: operational detail, sequencing, common pitfalls, KPIs.

Post structure (without labeling it):
1. Hook (1-2 sentences): counterintuitive finding, provocative thesis, or surprising number. Decides whether anyone reads on.
2. Problem: a clear tension the audience knows. Concrete, not abstract.
3. Proof/practice: evidence from observation or patterns. Max 3-5 steps. Your own thought-leader point.
4. Close: either a principle loop (back to a larger universal truth worth restating) OR a question — only if it sparks genuine, non-obvious interest. No "What do you think?" filler. No DM CTA. Actionable content earns comments by itself.

Formatting:
- Paragraphs may be 2-4 sentences. Not every sentence is its own paragraph. Blank lines only between thematic blocks.
- Pick exactly ONE formatting element:
  * Emoji list (at least 3 equal items): e.g. 📍 for findings, 👉 for recommendations
  * Numbered list with Unicode: ➊ ➋ ➌
  * ALL-CAPS label for one central section
  * ASCII box for a key takeaway: ┌─────┐ │ takeaway │ └─────┘
- Length: ~200 words, max 3,000 characters.

Quality check (E3):
- Evidence: is each core claim backed by data or observation?
- Executable: immediately actionable without a big marketing team?
- Exclusive: at least one thought you would not find everywhere?

End the post with 4-6 relevant hashtags (#B2BSaaS, #GTM, #RevOps, #Sales, #SaaS, #Outbound, #Pipeline or similar).

---

PART 2 - SOUND BYTE:

Extract from the generated post a single short, sharp sound byte for the image.

Rules:
- Not a summary of the post — no sentence that needs explaining.
- Must stick instantly and provoke a reaction.
- Sounds like a strong quote or a provocative thesis.
- Maximum 12 words.
- In English (the post is in English).

PART 3 - CONTEXT (optional):

For whom is the statement most relevant? 1-2 words audience, e.g. "CEOs, RevOps teams", or leave blank.

---

PART 4 - INFOGRAPHIC SKELETON:

Based on the generated post: recommend the strongest infographic type and provide the keywords for the Canva build.

INFOGRAPHIC TYPES (choose only one):
- Comparison table: two columns (e.g. "What people think" vs. "What it really is")
- Funnel/pyramid: 3-5 levels with hierarchy (top = most important or starting point)
- Iceberg: visible vs. hidden depth
- Framework/circles: concentric or nested levels
- Horizontal comparison: side by side, equal weight

Rules:
- Keywords not sentences (max 3-4 keywords per level/column)
- 3-7 elements total, no more
- Complementarity: if the infographic shows the problem, the post text describes the solution; if the infographic shows the structure, the post text explains the why
- Recommend tool logos when ICP-relevant tools appear in the post (HubSpot, Smartlead, Clay, Make.com, Apollo etc.)
- Recommend a visual metaphor when one reinforces the core idea (e.g. iceberg for hidden complexity, Rubik's cube for many-layeredness)

OUTPUT FORMAT (follow exactly):

===POST===
[LinkedIn post text in English]

#Hashtag1 #Hashtag2 #Hashtag3 #Hashtag4

===SOUNDBYTE===
[Sound byte — one sentence, max 12 words]

===KONTEXT===
[Audience/context or blank]

===INFOGRAFIK===
TYP: [type name]
METAPHER: [visual metaphor or "none"]
KOMPLEMENTARITAET: [infographic shows X -> post text explains Y]
EBENEN:
[Label 1]: [keyword 1], [keyword 2], [keyword 3]
[Label 2]: [keyword 1], [keyword 2], [keyword 3]
[Label 3]: [keyword 1], [keyword 2], [keyword 3]
TOOL-LOGOS: [tool names or "none"]"""
```

- [ ] **Step 2: Verify the module still imports**

Run: `cd "Jolly Automations/Jolly Influencer Post Recycling" && python -c "from tools.post_scorer import EN_POST_PROMPT; print(len(EN_POST_PROMPT))"`
Expected: prints an integer > 1000, no exception.

- [ ] **Step 3: Commit**

```bash
git add tools/post_scorer.py
git commit -m "Add native English EN_POST_PROMPT"
```

---

## Task 3: Two-call generation, EN drives the image, 4-tuple return

**Files:**
- Modify: `tools/post_scorer.py` — replace the body of `generate_post_and_image_prompt` (lines 467-528)

**Note:** No unit test here — this function makes paid Anthropic calls and the spec rules out building an LLM mock framework. The parser it relies on is covered by Task 1. Verification is the live dry-run in Task 6.

- [ ] **Step 1: Replace the function**

In `tools/post_scorer.py`, replace the entire `generate_post_and_image_prompt` function (currently lines 467-528) with:

```python
def generate_post_and_image_prompt(post: dict) -> tuple[str, str, str, str]:
    """Generiert DE-Post (DACH-Prompt) + nativen EN-Post (EN-Prompt).
    Das Bild wird aus den EN-Teilen (Soundbyte + Infografik) gebaut.
    Gibt (de_draft, en_draft, image_prompt, infographic_skeleton) zurueck.
    """
    # --- Call 1: DE-Post (DACH-Prompt). Nur der Post-Text wird genutzt. ---
    de_prompt = DACH_POST_PROMPT.format(
        context=JOLLY_CONTEXT,
        influencer=post["influencer"],
        post_text=post["post_text"][:3000],
    )
    de_resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": de_prompt}],
    )
    de_parts = _parse_generation_response(de_resp.content[0].text.strip())
    de_draft = de_parts["post"]

    # --- Call 2: EN-Post (nativ). Liefert Soundbyte + Infografik fuers Bild. ---
    en_prompt = EN_POST_PROMPT.format(
        context=JOLLY_CONTEXT,
        influencer=post["influencer"],
        post_text=post["post_text"][:3000],
    )
    en_resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": en_prompt}],
    )
    en_parts = _parse_generation_response(en_resp.content[0].text.strip())
    en_draft = en_parts["post"]
    sound_byte = en_parts["soundbyte"]
    kontext = en_parts["kontext"]
    infographic_skeleton = en_parts["infografik"]

    # Bild-Prompt aus dem EN-Soundbyte (englischer Bildtext, fuer beide Posts).
    image_prompt = ""
    if sound_byte:
        image_prompt = IMAGE_PROMPT_TEMPLATE.format(
            core_message=sound_byte,
            context=kontext or "B2B CEOs and founders",
            language="English",
        )

    return de_draft, en_draft, image_prompt, infographic_skeleton
```

- [ ] **Step 2: Verify import + signature**

Run: `cd "Jolly Automations/Jolly Influencer Post Recycling" && python -c "import inspect; from tools.post_scorer import generate_post_and_image_prompt as f; print(inspect.signature(f))"`
Expected: prints `(post: dict) -> tuple[str, str, str, str]`, no exception.

- [ ] **Step 3: Commit**

```bash
git add tools/post_scorer.py
git commit -m "Two-call DE+EN generation; EN soundbyte drives shared image"
```

---

## Task 4: Notion entry stores both drafts with slot headings

**Files:**
- Modify: `tools/notion_db.py` — `update_with_draft` (lines 192-268), add `en_draft` param + body-block append

**Note:** No unit test — `update_with_draft` calls the live Notion API; mocking it is out of scope per the spec. Verified in the Task 6 dry-run.

- [ ] **Step 1: Add a body-block append helper**

In `tools/notion_db.py`, add directly after `_append_infographic_block` (after line 179):

```python
def _append_draft_blocks(page_id: str, de_draft: str, en_draft: str) -> None:
    """Haengt DE- und EN-Draft als Body-Bloecke mit Slot-Headings an die Seite."""
    def text_blocks(text):
        text = _sanitize(text)
        chunks = [text[i:i+1900] for i in range(0, len(text), 1900)] or [""]
        return [
            {"object": "block", "type": "paragraph",
             "paragraph": {"rich_text": [{"type": "text", "text": {"content": c}}]}}
            for c in chunks
        ]

    children = [{"object": "block", "type": "divider", "divider": {}},
                {"object": "block", "type": "heading_2",
                 "heading_2": {"rich_text": [{"type": "text",
                  "text": {"content": "LinkedIn Draft DE (Slot: Vormittag)"}}]}}]
    children += text_blocks(de_draft)
    children += [{"object": "block", "type": "divider", "divider": {}},
                 {"object": "block", "type": "heading_2",
                  "heading_2": {"rich_text": [{"type": "text",
                   "text": {"content": "LinkedIn Draft EN (Slot: Nachmittag)"}}]}}]
    children += text_blocks(en_draft)

    resp = requests.patch(
        f"{NOTION_API}/blocks/{page_id}/children",
        headers=_headers(),
        json={"children": children},
    )
    resp.raise_for_status()
```

- [ ] **Step 2: Add `en_draft` parameter to `update_with_draft`**

In `tools/notion_db.py`, change the `update_with_draft` signature (line 192-201) from:

```python
def update_with_draft(
    page_id: str,
    linkedin_draft: str,
    image_prompt: str,
    image_url: str,
    title: str = "",
    influencer: str = "",
    image_failed: bool = False,
    image_error: str = "",
    infographic_skeleton: str = "",
):
```

to (add `en_draft: str = ""` after `linkedin_draft`):

```python
def update_with_draft(
    page_id: str,
    linkedin_draft: str,
    image_prompt: str,
    image_url: str,
    en_draft: str = "",
    title: str = "",
    influencer: str = "",
    image_failed: bool = False,
    image_error: str = "",
    infographic_skeleton: str = "",
):
```

- [ ] **Step 3: Append draft blocks before the infographic block**

In `update_with_draft`, locate the trailing infographic block (lines 261-266):

```python
    if infographic_skeleton:
        try:
            _append_infographic_block(page_id, infographic_skeleton)
            print("  Infografik-Skelett in Notion geschrieben.", flush=True)
        except Exception as e:
            print(f"  Infografik-Block fehlgeschlagen (nicht kritisch): {e}", flush=True)
```

Insert this block immediately BEFORE it:

```python
    try:
        _append_draft_blocks(page_id, linkedin_draft, en_draft)
        print("  DE+EN Draft-Bloecke mit Slot-Headings geschrieben.", flush=True)
    except Exception as e:
        print(f"  Draft-Bloecke fehlgeschlagen (nicht kritisch): {e}", flush=True)

```

- [ ] **Step 4: Verify import + signature**

Run: `cd "Jolly Automations/Jolly Influencer Post Recycling" && python -c "import inspect; from tools.notion_db import update_with_draft as f; print('en_draft' in inspect.signature(f).parameters)"`
Expected: prints `True`, no exception.

- [ ] **Step 5: Commit**

```bash
git add tools/notion_db.py
git commit -m "Store DE+EN drafts as Notion body blocks with slot headings"
```

---

## Task 5: Wire the cron to the new 4-tuple

**Files:**
- Modify: `run_research.py` — step 5 unpack (line 104), EN placeholder, step 6 image language (line 120), step 7 call (lines 152-162)

**Note:** No unit test — `main()` orchestrates live scrape + paid APIs. Verified in the Task 6 dry-run.

- [ ] **Step 1: Unpack the 4-tuple + EN placeholder (step 5)**

In `run_research.py`, replace lines 103-115 (from `try:` through the three `print` lines after `if not linkedin_draft`):

Current:
```python
    try:
        linkedin_draft, image_prompt, infographic_skeleton = generate_post_and_image_prompt(winner)
    except Exception as e:
        print(f"  FEHLER bei Content-Generierung: {e}", file=sys.stderr)
        sys.exit(1)

    if not linkedin_draft:
        print("  FEHLER: Leerer LinkedIn-Draft. Kein Notion-Update.", file=sys.stderr)
        sys.exit(1)

    print(f"  Draft: {len(linkedin_draft)} Zeichen")
    print(f"  Bild-Prompt: {'OK' if image_prompt else 'leer'}")
    print(f"  Infografik-Skelett: {'OK' if infographic_skeleton else 'leer'}")
```

New:
```python
    try:
        linkedin_draft, en_draft, image_prompt, infographic_skeleton = generate_post_and_image_prompt(winner)
    except Exception as e:
        print(f"  FEHLER bei Content-Generierung: {e}", file=sys.stderr)
        sys.exit(1)

    if not linkedin_draft:
        print("  FEHLER: Leerer DE-Draft. Kein Notion-Update.", file=sys.stderr)
        sys.exit(1)

    if not en_draft:
        en_draft = "[EN-Generierung fehlgeschlagen - manuell nachziehen]"
        print("  WARNUNG: Leerer EN-Draft. Platzhalter gesetzt, DE wird gespeichert.", file=sys.stderr)

    print(f"  DE-Draft: {len(linkedin_draft)} Zeichen")
    print(f"  EN-Draft: {len(en_draft)} Zeichen")
    print(f"  Bild-Prompt: {'OK' if image_prompt else 'leer'}")
    print(f"  Infografik-Skelett: {'OK' if infographic_skeleton else 'leer'}")
```

- [ ] **Step 2: Request an English infographic image (step 6)**

In `run_research.py`, line 120, change:

```python
    infographic_prompt = build_infographic_prompt(infographic_skeleton)
```

to:

```python
    infographic_prompt = build_infographic_prompt(infographic_skeleton, language="English")
```

- [ ] **Step 3: Pass `en_draft` into the Notion update (step 7)**

In `run_research.py`, in the `update_with_draft(...)` call (lines 152-162), add the `en_draft` argument. Change:

```python
        update_with_draft(
            page_id=page_id,
            linkedin_draft=linkedin_draft,
            image_prompt=gen_prompt,
            image_url=image_url,
            title=winner.get("post_excerpt", "")[:60],
            influencer=winner["influencer"],
            image_failed=image_failed,
            image_error=image_error,
            infographic_skeleton=infographic_skeleton,
        )
```

to:

```python
        update_with_draft(
            page_id=page_id,
            linkedin_draft=linkedin_draft,
            en_draft=en_draft,
            image_prompt=gen_prompt,
            image_url=image_url,
            title=winner.get("post_excerpt", "")[:60],
            influencer=winner["influencer"],
            image_failed=image_failed,
            image_error=image_error,
            infographic_skeleton=infographic_skeleton,
        )
```

- [ ] **Step 4: Verify the module compiles**

Run: `cd "Jolly Automations/Jolly Influencer Post Recycling" && python -c "import ast; ast.parse(open('run_research.py', encoding='utf-8').read()); print('OK')"`
Expected: prints `OK`, no SyntaxError.

- [ ] **Step 5: Run the parser test suite again (regression)**

Run: `cd "Jolly Automations/Jolly Influencer Post Recycling" && python -m pytest tests/ -v`
Expected: PASS (3 passed)

- [ ] **Step 6: Commit**

```bash
git add run_research.py
git commit -m "Wire cron to DE+EN 4-tuple, EN image, en_draft to Notion"
```

---

## Task 6: Live dry-run verification (SPEND-GATED)

**Files:** none (verification only)

**Cost:** 2 Sonnet calls + 1 kie.ai image for one real run. **Get Richard's explicit spend approval before running.**

- [ ] **Step 1: Request spend approval**

Ask Richard: "Ready to run one live cron dry-run? Cost ~2 Sonnet calls + 1 kie.ai image."
Wait for explicit yes.

- [ ] **Step 2: Run the pipeline once**

Run: `cd "Jolly Automations/Jolly Influencer Post Recycling" && python run_research.py`
Expected: completes through "=== DONE ===". Watch for non-empty DE-Draft and EN-Draft character counts in the log.

- [ ] **Step 3: Verify the Notion entry**

Open the created Notion page (URL in the Make email / log). Confirm:
- One entry, status `Ready to Review` (or `Image Failed` only if the image failed).
- Body block heading `LinkedIn Draft DE (Slot: Vormittag)` with German text.
- Body block heading `LinkedIn Draft EN (Slot: Nachmittag)` with native English text (not a literal translation).
- One shared image present, English image text.
- `Infografik-Skelett (Canva)` block in English.

- [ ] **Step 4: Report result**

Summarize to Richard: DE length, EN length, image OK/failed, Notion link. If anything is off (EN looks translated, image text wrong language), note it for a follow-up fix.

---

## Self-Review Notes

- Spec coverage: decisions 1-7 all mapped — manual publish unchanged (no auto-poster task), AI invents angle (no code), native EN (Task 2+3), shared EN image (Task 3 + Task 5 step 2), one entry both drafts (Task 4), slot headings DE morning / EN afternoon (Task 4), approach A two calls (Task 3). Error handling DE-abort / EN-placeholder / image-failed (Task 5 step 1, existing logic). Parser test (Task 1). Spend-gated dry-run (Task 6).
- Type consistency: `generate_post_and_image_prompt` returns the 4-tuple `(de_draft, en_draft, image_prompt, infographic_skeleton)` in Task 3 and is unpacked in that exact order in Task 5 step 1. `update_with_draft` gains `en_draft` (Task 4) and is passed `en_draft=en_draft` (Task 5 step 3). `_parse_generation_response` keys `post/soundbyte/kontext/infografik` defined in Task 1, consumed in Task 3.
- No new Notion schema property required (EN stored as body block) — matches spec out-of-scope note.
