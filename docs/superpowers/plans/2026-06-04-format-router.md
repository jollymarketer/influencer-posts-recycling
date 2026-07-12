# Format Router Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rotate each daily recycled post across three structures (Opinion / POV / Signature "Glaube vs. Realität") via an LLM best-fit + anti-repeat router, tracked in a Notion Format property.

**Architecture:** Additive. `post_scorer.py` gains `FORMAT_STRUCTURES`, a pure prompt builder `_format_prompts`, and `pick_format`. The two prompt templates get a `{structure_block}` placeholder. `notion_db.py` gains `get_recent_formats` and a non-fatal Format-property write inside `update_with_draft`. `run_research.py` picks the format between winner-selection and generation and threads it through. A one-time idempotent setup script creates the Notion property.

**Tech Stack:** Python 3, anthropic SDK (Claude Haiku for the picker, Sonnet for generation), Notion REST API, pytest with `unittest.mock`.

---

## File Structure

- Modify: `tools/post_scorer.py` — add `FORMAT_STRUCTURES`, `_format_prompts`, `pick_format`, `PICK_FORMAT_PROMPT`; refactor `DACH_POST_PROMPT` / `EN_POST_PROMPT` to use `{structure_block}`; change `generate_post_and_image_prompt` signature.
- Modify: `tools/notion_db.py` — add `get_recent_formats`; add non-fatal Format write to `update_with_draft`.
- Modify: `run_research.py` — wire `get_recent_formats` + `pick_format` + thread `post_format`.
- Create: `scripts/add_format_property.py` — one-time idempotent Notion schema setup.
- Create: `tests/test_format_structures.py` — pure builder tests.
- Create: `tests/test_pick_format.py` — router tests (client mocked).
- Create: `tests/test_notion_db_formats.py` — Notion read/write tests (`_notion_request` mocked).

---

## Task 1: Format structures + prompt injection

**Files:**
- Modify: `tools/post_scorer.py`
- Test: `tests/test_format_structures.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_format_structures.py`:

```python
"""Tests for format structure injection. Pure functions, no API calls."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools.post_scorer import FORMAT_STRUCTURES, _format_prompts

POST = {"influencer": "Jane Doe", "post_text": "Some source post about pipeline."}


def test_three_formats_defined_with_de_and_en():
    assert set(FORMAT_STRUCTURES) == {"Opinion", "POV", "Signature"}
    for key in FORMAT_STRUCTURES:
        assert FORMAT_STRUCTURES[key]["de"].strip()
        assert FORMAT_STRUCTURES[key]["en"].strip()


def test_opinion_injects_contrarian_structure():
    de, en = _format_prompts(POST, "Opinion")
    assert "Gegenposition" in de
    assert "contrarian" in en.lower()


def test_pov_injects_framework_structure():
    de, en = _format_prompts(POST, "POV")
    assert "Denk-Linse" in de
    assert "lens" in en.lower()


def test_signature_injects_belief_vs_reality_structure():
    de, en = _format_prompts(POST, "Signature")
    assert "glauben" in de.lower()
    assert "Vergleichstabelle" in de
    assert "belief" in en.lower()


def test_unknown_format_falls_back_to_opinion():
    de_known, _ = _format_prompts(POST, "Opinion")
    de_unknown, _ = _format_prompts(POST, "Nonsense")
    assert "Gegenposition" in de_unknown  # same as Opinion block


def test_post_text_and_influencer_present_in_prompt():
    de, en = _format_prompts(POST, "POV")
    assert "Jane Doe" in de and "Jane Doe" in en
    assert "Some source post" in de and "Some source post" in en
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_format_structures.py -v`
Expected: FAIL with `ImportError: cannot import name 'FORMAT_STRUCTURES'`.

- [ ] **Step 3: Refactor templates and add structures**

In `tools/post_scorer.py`, in `DACH_POST_PROMPT`, REPLACE the block:

```
Post-Struktur (ohne explizite Benennung):
1. Hook (1-2 Saetze): Kontraintuitiver Befund, provokante These oder ueberraschende Zahl. Entscheidet ob jemand weiterliest.
2. Problem: Klares Spannungsfeld das die Zielgruppe kennt. Konkret, nicht abstrakt.
3. Proof/Praxis: Belege aus Beobachtung oder Mustern. Max 3-5 Schritte. Eigener Thought-Leader-Gedanke.
4. Abschluss: Entweder Principle-Loop (loop zurueck zu einer groesseren universellen Wahrheit — etwas das schon bekannt ist aber es wieder wert ist zu sagen) ODER eine Frage — nur wenn sie genuines nicht-offensichtliches Interesse weckt. Kein "Was denkst du?"-Filler. Kein DM-CTA. Actionable content erzeugt Kommentare automatisch.
```

with the single line:

```
{structure_block}
```

In `EN_POST_PROMPT`, REPLACE the block:

```
Post structure (without labeling it):
1. Hook (1-2 sentences): counterintuitive finding, provocative thesis, or surprising number. Decides whether anyone reads on.
2. Problem: a clear tension the audience knows. Concrete, not abstract.
3. Proof/practice: evidence from observation or patterns. Max 3-5 steps. Your own thought-leader point.
4. Close: either a principle loop (back to a larger universal truth worth restating) OR a question — only if it sparks genuine, non-obvious interest. No "What do you think?" filler. No DM CTA. Actionable content earns comments by itself.
```

with the single line:

```
{structure_block}
```

Then add, after the `EN_POST_PROMPT` definition (before `IMAGE_PROMPT_TEMPLATE`):

```python
FORMAT_STRUCTURES = {
    "Opinion": {
        "de": """Post-Struktur (ohne explizite Benennung):
1. Hook (1-2 Saetze): Eine kontroverse These oder ein Gegen-Befund zu einer gaengigen Praxis. Entscheidet ob jemand weiterliest.
2. Spannung: Was die meisten Teams glauben oder tun - und warum das in der Praxis nicht traegt. Konkret, nicht abstrakt.
3. Position: Deine Gegenposition als erfahrener Praktiker, begruendet aus Beobachtung. Max 3-5 Belege oder Schritte. Ein eigener Gedanke der im Original nicht vorkommt.
4. Abschluss: Principle-Loop zurueck zu einer groesseren Wahrheit. Kein "Was denkst du?"-Filler, kein DM-CTA.""",
        "en": """Post structure (without labeling it):
1. Hook (1-2 sentences): a contrarian thesis or counter-finding against a common practice. Decides whether anyone reads on.
2. Tension: what most teams believe or do - and why it does not hold up in practice. Concrete, not abstract.
3. Position: your contrarian take as an experienced operator, reasoned from observation. Max 3-5 proofs or steps. One original thought not in the source.
4. Close: principle loop back to a larger truth. No "What do you think?" filler, no DM CTA.""",
    },
    "POV": {
        "de": """Post-Struktur (ohne explizite Benennung):
1. Hook (1-2 Saetze): Benenne eine Denk-Linse oder ein Reframe das die Zielgruppe so noch nicht hatte. Entscheidet ob jemand weiterliest.
2. Framework: 2-4 benannte Bestandteile eines Modells, mit dem man das Problem klarer sieht. Konkret, nicht abstrakt.
3. Anwendung: Wie man die Linse in der Praxis nutzt. Max 3-5 Schritte. Ein eigener Gedanke der im Original nicht vorkommt.
4. Abschluss: Principle-Loop zurueck zu einer groesseren Wahrheit. Kein "Was denkst du?"-Filler, kein DM-CTA.""",
        "en": """Post structure (without labeling it):
1. Hook (1-2 sentences): name a lens or reframe the audience did not have yet. Decides whether anyone reads on.
2. Framework: 2-4 named parts of a model that makes the problem clearer. Concrete, not abstract.
3. Application: how to use the lens in practice. Max 3-5 steps. One original thought not in the source.
4. Close: principle loop back to a larger truth. No "What do you think?" filler, no DM CTA.""",
    },
    "Signature": {
        "de": """Post-Struktur (ohne explizite Benennung):
1. Hook (1-2 Saetze): "Was Founder/Sales-Teams glauben:" - die verbreitete Annahme, zugespitzt. Entscheidet ob jemand weiterliest.
2. Realitaet: Was tatsaechlich das Ergebnis treibt - im Kontrast zur Annahme. Konkret, nicht abstrakt.
3. Kontraste: 2-4 Glaube-gegen-Realitaet-Paare, je knapp. Ein eigener Gedanke der im Original nicht vorkommt.
4. Abschluss: Das Operating-Principle das aus den Kontrasten folgt. Kein "Was denkst du?"-Filler, kein DM-CTA.
Hinweis fuer die Infografik weiter unten: Bevorzuge die Vergleichstabelle (Glaube vs. Realitaet).""",
        "en": """Post structure (without labeling it):
1. Hook (1-2 sentences): "What founders/sales teams believe:" - the common assumption, sharpened. Decides whether anyone reads on.
2. Reality: what actually drives the outcome, in contrast to the assumption. Concrete, not abstract.
3. Contrasts: 2-4 belief-vs-reality pairs, each tight. One original thought not in the source.
4. Close: the operating principle that follows from the contrasts. No "What do you think?" filler, no DM CTA.
Note for the infographic section below: prefer the comparison table (belief vs. reality).""",
    },
}


def _format_prompts(post: dict, post_format: str = "Opinion") -> tuple[str, str]:
    """Pure builder: returns (de_prompt, en_prompt) with the format structure
    injected. Unknown format keys fall back to Opinion. No API calls."""
    structures = FORMAT_STRUCTURES.get(post_format, FORMAT_STRUCTURES["Opinion"])
    de = DACH_POST_PROMPT.format(
        context=JOLLY_CONTEXT,
        influencer=post["influencer"],
        post_text=post["post_text"][:3000],
        structure_block=structures["de"],
    )
    en = EN_POST_PROMPT.format(
        context=JOLLY_CONTEXT,
        influencer=post["influencer"],
        post_text=post["post_text"][:3000],
        structure_block=structures["en"],
    )
    return de, en
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_format_structures.py -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/post_scorer.py tests/test_format_structures.py
git commit -m "feat(format-router): add 3 format structures + pure prompt builder"
```

---

## Task 2: generate_post_and_image_prompt uses the builder

**Files:**
- Modify: `tools/post_scorer.py:622-666` (`generate_post_and_image_prompt`)
- Test: `tests/test_format_structures.py` (extend)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_format_structures.py`:

```python
from unittest.mock import MagicMock, patch


def test_generate_threads_format_into_de_prompt():
    captured = []

    def fake_create(**kw):
        captured.append(kw["messages"][0]["content"])
        resp = MagicMock()
        resp.content = [MagicMock(text="===POST===\nBody.\n===SOUNDBYTE===\nByte.")]
        return resp

    with patch("tools.post_scorer.client") as c:
        c.messages.create.side_effect = fake_create
        from tools.post_scorer import generate_post_and_image_prompt
        generate_post_and_image_prompt(POST, "Signature")

    # First call is the DE prompt; it must carry the Signature structure.
    assert "Vergleichstabelle" in captured[0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_format_structures.py::test_generate_threads_format_into_de_prompt -v`
Expected: FAIL — `generate_post_and_image_prompt` does not accept a second positional arg yet (TypeError).

- [ ] **Step 3: Update the function**

In `tools/post_scorer.py`, change the signature and the two prompt builds:

```python
def generate_post_and_image_prompt(post: dict, post_format: str = "Opinion") -> tuple[str, str, str, str]:
    """Generiert DE-Post (DACH-Prompt) + nativen EN-Post (EN-Prompt).
    Das Bild wird aus den EN-Teilen (Soundbyte + Infografik) gebaut.
    post_format waehlt den Struktur-Block (Opinion/POV/Signature).
    Gibt (de_draft, en_draft, image_prompt, infographic_skeleton) zurueck.
    """
    de_prompt, en_prompt = _format_prompts(post, post_format)

    de_resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": de_prompt}],
    )
    de_draft = _parse_generation_response(de_resp.content[0].text.strip())["post"]

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

    image_prompt = ""
    if sound_byte:
        image_prompt = IMAGE_PROMPT_TEMPLATE.format(
            core_message=sound_byte,
            context=kontext or "B2B CEOs and founders",
            language="English",
        )

    return de_draft, en_draft, image_prompt, infographic_skeleton
```

(Removes the old inline `DACH_POST_PROMPT.format(...)` / `EN_POST_PROMPT.format(...)` calls; everything else identical.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_format_structures.py tests/test_parse_generation.py -v`
Expected: PASS (all).

- [ ] **Step 5: Commit**

```bash
git add tools/post_scorer.py tests/test_format_structures.py
git commit -m "feat(format-router): generate_post_and_image_prompt threads post_format"
```

---

## Task 3: pick_format router

**Files:**
- Modify: `tools/post_scorer.py` (add `PICK_FORMAT_PROMPT`, `VALID_FORMATS`, `pick_format`)
- Test: `tests/test_pick_format.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_pick_format.py`:

```python
"""Tests for pick_format. The anthropic client is mocked — no API calls."""
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import post_scorer

POST = {"influencer": "Jane", "post_text": "A post about cold email reply rates."}


def _mock_client(reply_text):
    resp = MagicMock()
    resp.content = [MagicMock(text=reply_text)]
    c = MagicMock()
    c.messages.create.return_value = resp
    return c


def test_returns_llm_choice_when_allowed():
    with patch.object(post_scorer, "client", _mock_client("POV")):
        assert post_scorer.pick_format(POST, ["Opinion"]) == "POV"


def test_never_returns_most_recent_even_if_llm_picks_it():
    # LLM disobeys and returns the forbidden (most recent) format.
    with patch.object(post_scorer, "client", _mock_client("Opinion")):
        result = post_scorer.pick_format(POST, ["Opinion"])
    assert result != "Opinion"
    assert result in ("POV", "Signature")


def test_empty_recent_returns_valid_format():
    with patch.object(post_scorer, "client", _mock_client("Signature")):
        assert post_scorer.pick_format(POST, []) == "Signature"


def test_unrecognized_llm_output_falls_back_without_raising():
    with patch.object(post_scorer, "client", _mock_client("banana")):
        result = post_scorer.pick_format(POST, ["POV"])
    assert result in ("Opinion", "Signature")  # valid, and != most recent


def test_api_exception_falls_back():
    c = MagicMock()
    c.messages.create.side_effect = RuntimeError("api down")
    with patch.object(post_scorer, "client", c):
        result = post_scorer.pick_format(POST, ["Signature"])
    assert result in ("Opinion", "POV")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_pick_format.py -v`
Expected: FAIL with `AttributeError: module 'tools.post_scorer' has no attribute 'pick_format'`.

- [ ] **Step 3: Add the router**

In `tools/post_scorer.py`, after `FORMAT_STRUCTURES` / `_format_prompts`, add:

```python
VALID_FORMATS = ("Opinion", "POV", "Signature")

PICK_FORMAT_PROMPT = """Du waehlst das Post-Format fuer einen Recycling-Post.

Verfuegbare Formate:
- Opinion: kontroverse These gegen eine gaengige Praxis.
- POV: eine strukturierte Denk-Linse / ein Framework.
- Signature: "Glaube vs. Realitaet" - verbreitete Annahme gegen das was wirklich zaehlt.

QUELL-POST:
{post_text}

{recent_section}

Regeln:
- Waehle das Format das am besten zum Thema des Quell-Posts passt.
- Das zuletzt genutzte Format ist verboten (nie zweimal hintereinander).
- Antworte mit EINEM Wort: Opinion, POV oder Signature. Nichts sonst."""


def pick_format(post: dict, recent_formats: list[str]) -> str:
    """Waehlt Opinion/POV/Signature: bester Topic-Fit, aber nie das zuletzt
    genutzte Format. Faellt deterministisch zurueck und wirft nie."""
    most_recent = recent_formats[0] if recent_formats else None

    if recent_formats:
        recent_section = (
            f"Zuletzt genutzte Formate (neuestes zuerst): {', '.join(recent_formats)}. "
            f"VERBOTEN ist: {most_recent}."
        )
    else:
        recent_section = "Zuletzt genutzte Formate: keine."

    try:
        prompt = PICK_FORMAT_PROMPT.format(
            post_text=post["post_text"][:3000],
            recent_section=recent_section,
        )
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            messages=[{"role": "user", "content": prompt}],
        )
        choice = response.content[0].text.strip()
        for f in VALID_FORMATS:
            if f.lower() in choice.lower() and f != most_recent:
                return f
    except Exception as e:
        print(f"  Format-Pick fehlgeschlagen, Fallback: {e}")

    # Deterministic fallback: first valid format that is not the most recent.
    for f in VALID_FORMATS:
        if f != most_recent:
            return f
    return "Opinion"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_pick_format.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/post_scorer.py tests/test_pick_format.py
git commit -m "feat(format-router): add pick_format router (best-fit + anti-repeat)"
```

---

## Task 4: Notion Format read + write

**Files:**
- Modify: `tools/notion_db.py` (`update_with_draft` add `post_format` param + non-fatal write; add `get_recent_formats`)
- Test: `tests/test_notion_db_formats.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_notion_db_formats.py`:

```python
"""Tests for Format property read/write. _notion_request mocked."""
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import notion_db


def test_update_with_draft_writes_format_property(monkeypatch):
    monkeypatch.setenv("NOTION_TOKEN", "tok")
    monkeypatch.setattr(notion_db, "MAKE_REVIEW_WEBHOOK", "", raising=False)
    resp = MagicMock(status_code=200)
    resp.json.return_value = {"id": "page1"}
    resp.raise_for_status.return_value = None
    with patch("tools.notion_db._notion_request", return_value=resp) as m:
        notion_db.update_with_draft(
            page_id="p1", linkedin_draft="DE", image_prompt="", image_url="",
            post_format="Signature",
        )
    # Some _notion_request call must carry the Format select.
    found = None
    for call in m.call_args_list:
        props = call.kwargs.get("json", {}).get("properties", {})
        if "Format" in props:
            found = props["Format"]
    assert found == {"select": {"name": "Signature"}}


def test_update_with_draft_omits_format_when_blank(monkeypatch):
    monkeypatch.setenv("NOTION_TOKEN", "tok")
    monkeypatch.setattr(notion_db, "MAKE_REVIEW_WEBHOOK", "", raising=False)
    resp = MagicMock(status_code=200)
    resp.json.return_value = {"id": "page1"}
    resp.raise_for_status.return_value = None
    with patch("tools.notion_db._notion_request", return_value=resp) as m:
        notion_db.update_with_draft(
            page_id="p1", linkedin_draft="DE", image_prompt="", image_url="",
        )
    for call in m.call_args_list:
        props = call.kwargs.get("json", {}).get("properties", {})
        assert "Format" not in props


def test_format_write_failure_is_non_fatal(monkeypatch):
    monkeypatch.setenv("NOTION_TOKEN", "tok")
    monkeypatch.setattr(notion_db, "MAKE_REVIEW_WEBHOOK", "", raising=False)
    ok = MagicMock(status_code=200)
    ok.json.return_value = {"id": "page1"}
    ok.raise_for_status.return_value = None
    bad = MagicMock(status_code=400)
    bad.raise_for_status.side_effect = Exception("no such property Format")

    def route(method, url, **kw):
        # The Format-only PATCH carries exactly {"Format": ...} in properties.
        props = kw.get("json", {}).get("properties", {})
        if list(props.keys()) == ["Format"]:
            return bad
        return ok

    with patch("tools.notion_db._notion_request", side_effect=route):
        # Must not raise despite the Format write failing.
        notion_db.update_with_draft(
            page_id="p1", linkedin_draft="DE", image_prompt="", image_url="",
            post_format="POV",
        )


def test_get_recent_formats_parses_selects():
    page = lambda name: {"properties": {"Format": {"select": {"name": name}}}}
    resp = MagicMock()
    resp.json.return_value = {"results": [page("POV"), page("Opinion")]}
    resp.raise_for_status.return_value = None
    with patch("tools.notion_db._notion_request", return_value=resp):
        assert notion_db.get_recent_formats(3) == ["POV", "Opinion"]


def test_get_recent_formats_skips_missing_property():
    resp = MagicMock()
    resp.json.return_value = {"results": [{"properties": {}}, {"properties": {"Format": {"select": None}}}]}
    resp.raise_for_status.return_value = None
    with patch("tools.notion_db._notion_request", return_value=resp):
        assert notion_db.get_recent_formats(3) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_notion_db_formats.py -v`
Expected: FAIL — `get_recent_formats` missing and `update_with_draft` rejects `post_format` kwarg.

- [ ] **Step 3: Implement read + write**

In `tools/notion_db.py`, change the `update_with_draft` signature to add `post_format`:

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
    post_format: str = "",
):
```

Then, immediately AFTER the main page PATCH succeeds (after the line `result = resp.json()` near the webhook section), add a SEPARATE non-fatal Format write so a missing-property error never breaks the critical Status PATCH:

```python
    # Format-Property separat + non-fatal schreiben: faellt die Property in Notion
    # (noch) nicht existiert, darf das den kritischen Status-PATCH oben nicht killen.
    if post_format:
        try:
            fr = _notion_request(
                "PATCH",
                f"{NOTION_API}/pages/{page_id}",
                headers=_headers(),
                json={"properties": {"Format": {"select": {"name": post_format}}}},
            )
            fr.raise_for_status()
            print(f"  Format-Property gesetzt: {post_format}", flush=True)
        except Exception as e:
            print(f"  Format-Property fehlgeschlagen (nicht kritisch): {e}", flush=True)
```

(Place this block before the `_append_draft_blocks` try-block, after `result = resp.json()`.)

Then add `get_recent_formats` after `get_recent_linkedin_drafts`:

```python
def get_recent_formats(limit: int = 3) -> list[str]:
    """Gibt die Format-Werte der letzten N Eintraege zurueck (fuer den
    Anti-Repeat-Check im Format-Router). Tolerant: fehlende Property -> []."""
    payload = {
        "filter": {
            "or": [
                {"property": "Status", "select": {"equals": "Posted"}},
                {"property": "Status", "select": {"equals": "Approved"}},
                {"property": "Status", "select": {"equals": "Ready to Review"}},
            ]
        },
        "sorts": [{"timestamp": "last_edited_time", "direction": "descending"}],
        "page_size": limit,
    }
    resp = _notion_request(
        "POST",
        f"{NOTION_API}/databases/{NOTION_DB_ID}/query",
        headers=_headers(),
        json=payload,
    )
    resp.raise_for_status()
    results = resp.json().get("results", [])

    formats = []
    for page in results:
        props = page.get("properties", {})
        sel = props.get("Format", {}).get("select") or {}
        name = sel.get("name")
        if name:
            formats.append(name)
    return formats
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_notion_db_formats.py tests/test_notion_db_drafts.py -v`
Expected: PASS (existing draft tests still green, 5 new tests pass).

- [ ] **Step 5: Commit**

```bash
git add tools/notion_db.py tests/test_notion_db_formats.py
git commit -m "feat(format-router): persist + read Notion Format property (non-fatal)"
```

---

## Task 5: One-time Notion schema setup script

**Files:**
- Create: `scripts/add_format_property.py`

- [ ] **Step 1: Write the script**

Create `scripts/add_format_property.py`:

```python
"""One-time idempotent: adds a 'Format' select property (Opinion/POV/Signature)
to the Jolly Influencer Post Recycling Notion DB. Safe to run repeatedly."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools.notion_db import NOTION_API, NOTION_DB_ID, _headers, _notion_request


def ensure_format_property() -> None:
    r = _notion_request("GET", f"{NOTION_API}/databases/{NOTION_DB_ID}", headers=_headers())
    r.raise_for_status()
    if "Format" in r.json().get("properties", {}):
        print("Format property already exists - nothing to do.")
        return

    payload = {
        "properties": {
            "Format": {
                "select": {
                    "options": [
                        {"name": "Opinion", "color": "blue"},
                        {"name": "POV", "color": "green"},
                        {"name": "Signature", "color": "orange"},
                    ]
                }
            }
        }
    }
    r = _notion_request(
        "PATCH", f"{NOTION_API}/databases/{NOTION_DB_ID}", headers=_headers(), json=payload
    )
    r.raise_for_status()
    print("Format property created (Opinion / POV / Signature).")


if __name__ == "__main__":
    ensure_format_property()
```

- [ ] **Step 2: Run the script against live Notion**

Run: `python scripts/add_format_property.py`
Expected: prints `Format property created (Opinion / POV / Signature).` (or `already exists` on re-run). This is a schema-only call — no credit cost, no records touched.

- [ ] **Step 3: Verify idempotency**

Run again: `python scripts/add_format_property.py`
Expected: prints `Format property already exists - nothing to do.`

- [ ] **Step 4: Commit**

```bash
git add scripts/add_format_property.py
git commit -m "chore(format-router): idempotent Notion Format property setup script"
```

---

## Task 6: Wire the pipeline

**Files:**
- Modify: `run_research.py` (imports + Step 4.5 + Step 5 + Step 7)

- [ ] **Step 1: Add imports**

In `run_research.py`, change the `tools.notion_db` import to add `get_recent_formats`:

```python
from tools.notion_db import (
    get_existing_post_urls,
    get_recent_linkedin_drafts,
    get_recent_formats,
    create_post_entry,
    update_with_draft,
)
```

And the `tools.post_scorer` import to add `pick_format`:

```python
from tools.post_scorer import score_posts, generate_post_and_image_prompt, build_infographic_prompt, pick_format
```

- [ ] **Step 2: Pick the format between Step 4 and Step 5**

In `run_daily`, directly AFTER the winner print line
`print(f"\nSchritt 4: Winner = {winner['influencer']} (Score: {winner['score']}/60)")`
and BEFORE `# Schritt 5`, insert:

```python
    # Schritt 4.5: Format waehlen (best-fit + anti-repeat, Pierre-Herubel Format-Varietaet)
    try:
        recent_formats = get_recent_formats()
    except Exception as e:
        print(f"  Recent-Formate laden fehlgeschlagen (nicht kritisch): {e}", file=sys.stderr)
        recent_formats = []
    post_format = pick_format(winner, recent_formats)
    print(f"  Format gewaehlt: {post_format} (zuletzt: {recent_formats[:3]})")
```

- [ ] **Step 3: Thread format into generation**

Change the generation call:

```python
        linkedin_draft, en_draft, image_prompt, infographic_skeleton = generate_post_and_image_prompt(winner, post_format)
```

- [ ] **Step 4: Thread format into the Notion save**

In the `update_with_draft(...)` call in Step 7, add the `post_format` argument:

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
            post_format=post_format,
        )
```

- [ ] **Step 5: Run the full test suite**

Run: `python -m pytest -q`
Expected: all tests PASS (existing + new). No import errors from `run_research.py`.

- [ ] **Step 6: Commit**

```bash
git add run_research.py
git commit -m "feat(format-router): wire pick_format into daily pipeline"
```

---

## Task 7: Final verification

- [ ] **Step 1: Run the complete suite once more**

Run: `python -m pytest -q`
Expected: green.

- [ ] **Step 2: Smoke-check imports**

Run: `python -c "import run_research; import tools.post_scorer; import tools.notion_db; print('imports ok')"`
Expected: `imports ok`.

- [ ] **Step 3: Report**

Summarize: tests green, Notion property live (from Task 5), pipeline wired. Note that the Railway deploy is a separate manual step for Richard (deploy = `railway up`, per project norms — do NOT deploy without asking).

---

## Notes for the implementer

- Do NOT run the live daily pipeline (`python run_research.py`) as a test — it scrapes, calls paid Sonnet, generates a kie.ai image, and writes Notion. The unit tests + import smoke-check are the verification. A live end-to-end run is Richard's call.
- The Format property write is deliberately a SECOND PATCH, separate from the Status PATCH, so a missing-property error degrades gracefully instead of killing the draft save.
- `_format_prompts` is pure (no API) so the structure logic is unit-testable without mocking the anthropic client.
