# Hook-Katalog und Hook-Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Jeder neue Post traegt eine Hook-Formel aus einem festen Katalog (deterministische Rotation, Select "Hook" in Notion); ein monatlicher CLI-Audit joint den nativen LinkedIn-Export mit den Notion-Zeilen, schreibt Bericht als Markdown, Notion-Seite und Mail und fuellt STOP/DO-MORE-Familien in `engine_meta`, die die Rotation liest.

**Architecture:** Zwei neue Module (`tools/hooks.py` Katalog und Rotation, `tools/hook_audit.py` Parser, Join, Metriken, Bericht, Steuerung), ein neuer Runner `run_hook_audit.py`, kleine Eingriffe in `post_scorer` (Hook-Zeile ersetzt Zeile 1 der Formatstruktur), `notion_db` (Hook lesen und schreiben, Audit-Seite), `text_gate` (140-Zeichen-Hinweis), `system_check` (weicher Befund), `run_research` (Hook waehlen, Erinnerung montags). Kein neuer Modellaufruf.

**Tech Stack:** Python 3.11, stdlib (`csv`, `json`, `statistics`, `re`, `datetime`), Notion REST ueber `tools/notion_db._notion_request`, Supabase `engine_meta` ueber `tools/topic_pool.get_meta/set_meta`, pytest mit `monkeypatch` und `unittest.mock.patch`. Keine neuen Abhaengigkeiten.

**Spec:** `docs/superpowers/specs/2026-09-14-hook-katalog-und-audit-design.md`

## Global Constraints

- Kein Netz in Tests. Alle Notion-, Supabase- und Webhook-Aufrufe werden gemockt (`patch("tools.notion_db._notion_request")`, `monkeypatch.setattr(tools.topic_pool, "get_meta", ...)`).
- Datei-Edits nur mit dem Edit-Tool, nie per Shell-Heredoc (Backslashes in Regex, CRLF).
- Commit-Message ueber `git commit -F <datei>`; Abschluss jeder Message: `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`. Nach jedem Commit `git push origin master`.
- Kein Modellaufruf in Rotation und Audit. Steuerung nur bei offenem Gate: 5 Posts je Familie, 2 auswertbare Familien, STOP unter 0,6 des Gesamtmedians, DO MORE ueber 1,4, Verfall 60 Tage.
- Zahlenformeln (`number_reveal`, `time_anchor`, `receipt`) nur in Asset-Formaten (`content_matrix.FORMAT_ASSET_ATTR`: CaseProof, Magnet, Offer).
- Spec-Abweichung, festgehalten in Task 11: die Dimension "Laengenband" entfaellt. Es gibt keine Notion-Property dafuer, Jolly faehrt keine `LENGTH_ROTATION`.
- Notion-Tabellen entstehen als REST-`table`-Bloecke. Das Attribut "fit page width" kennt die REST-API nicht; die Seite wird so gebaut, dass jede Tabelle hoechstens fuenf Spalten hat.
- Alle Print-Ausgaben deutsch, ASCII-Umschrift wie im Bestand (`ae`, `oe`, `ue`) in Code-Kommentaren und Logs; Prompt-Texte fuer das Modell mit echten Umlauten.

---

## File Structure

| Datei | Verantwortung |
| --- | --- |
| `tools/hooks.py` (neu) | Katalog `HOOKS`, `HOOKS_BY_FORMAT`, `HOOK_FAMILIES`, `hook_line`, `inject_hook`, `load_steering`, `pick_hook` |
| `tools/hook_audit.py` (neu) | `read_export`, `window_days`, `join_rows`, `enrich`, `aggregate_by`, `gate_open`, `steering_from`, `render_markdown`, `audit_overdue`, `run_audit` |
| `run_hook_audit.py` (neu) | CLI: Export finden, Audit fahren, Markdown, Notion, Mail, `engine_meta` |
| `scripts/add_hook_property.py` (neu) | Seed des Selects "Hook" (idempotent) |
| `tools/post_scorer.py` | `_format_prompts(hook_id=)`, `generate_post_and_image_prompt(hook_id=)` |
| `tools/notion_db.py` | `ENGAGEMENT_DIMENSIONS` + "Hook", `get_recent_hooks`, `update_with_draft(hook=)`, `create_audit_page` |
| `tools/text_gate.py` | 140-Zeichen-Hinweis in `shape_notes` |
| `tools/system_check.py` | weicher Befund fuer "Hook" |
| `run_research.py` | `pick_hook` im Winner-Flow, Erinnerung montags |
| `workflows/research_phase.md`, `workflows/hook_audit.md` (neu) | SOP und Self-Improvement-Log |
| Tests: `tests/test_hooks.py`, `tests/test_hooks_prompt.py`, `tests/test_notion_db_hooks.py`, `tests/test_hook_audit.py`, `tests/test_hook_audit_report.py`, `tests/test_run_hook_audit.py`; Ergaenzungen in `tests/test_text_gate.py`, `tests/test_system_check.py` | |

---

### Task 1: Katalog `tools/hooks.py`

**Files:**
- Create: `tools/hooks.py`
- Test: `tests/test_hooks.py`

**Interfaces:**
- Produces: `HOOKS: dict[str, dict]` mit Schluesseln `name`, `family`, `template_de`, `template_en`, `trap_de`; `HOOKS_BY_FORMAT: dict[str, tuple[str, ...]]`; `HOOK_FAMILIES: dict[str, tuple[str, ...]]`; `NUMBER_HOOKS: frozenset[str]`; `family_of(hook_id: str) -> str`.

- [ ] **Step 1: Failing Test schreiben**

```python
"""Hook-Katalog: gepinnt wie die Formatstrukturen. Kein Netz."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import hooks
from tools.content_matrix import FORMAT_ASSET_ATTR
from tools.post_scorer import FORMAT_STRUCTURES


def test_catalog_has_seventeen_complete_entries():
    assert len(hooks.HOOKS) == 17
    for hid, h in hooks.HOOKS.items():
        assert hid == hid.lower() and " " not in hid
        for key in ("name", "family", "template_de", "template_en", "trap_de"):
            assert h[key].strip(), f"{hid} ohne {key}"


def test_every_format_has_hooks_and_every_hook_a_family():
    assert set(hooks.HOOKS_BY_FORMAT) == set(FORMAT_STRUCTURES)
    for fmt, ids in hooks.HOOKS_BY_FORMAT.items():
        assert ids, fmt
        assert all(i in hooks.HOOKS for i in ids), fmt
    in_families = [i for ids in hooks.HOOK_FAMILIES.values() for i in ids]
    assert sorted(in_families) == sorted(hooks.HOOKS)
    for hid, h in hooks.HOOKS.items():
        assert hooks.family_of(hid) == h["family"]
        assert hid in hooks.HOOK_FAMILIES[h["family"]]


def test_number_hooks_only_in_asset_formats():
    for fmt, ids in hooks.HOOKS_BY_FORMAT.items():
        if fmt not in FORMAT_ASSET_ATTR:
            assert not (set(ids) & hooks.NUMBER_HOOKS), fmt


def test_signature_keeps_its_own_single_formula():
    assert hooks.HOOKS_BY_FORMAT["Signature"] == ("assumption",)
```

- [ ] **Step 2: Test laufen lassen, erwartet FAIL**

Run: `python -m pytest tests/test_hooks.py -v -p no:cacheprovider`
Expected: FAIL mit `ModuleNotFoundError: No module named 'tools.hooks'`

- [ ] **Step 3: Katalog schreiben**

```python
"""Hook-Katalog mit Rotation (Spec docs/superpowers/specs/
2026-09-14-hook-katalog-und-audit-design.md).

Anlass: Repo-Vergleich mit Jakeschincariol/linkedin-agent-skill (14.09.2026).
Bis dahin war der Hook Zeile 1 jeder Formatstruktur, eine Anweisung je Format;
ob Sonnet daraus Zahl, Frage, Dialogzeile oder Behauptung baute, entschied das
Modell je Lauf. Ohne ID gab es nichts, woran sich Ergebnisse festmachen liessen.

Der Katalog traegt 16 der 21 Formeln des Repos, deutsch gefasst, plus die
eigene Formel "assumption" fuer Signature. Je Formel eine Falle (wie die
Formel misslingt), sie steht mit im Prompt. Weggelassen: Permission Slip
(US-Coach-Ton), Callout (Verachtung fuer das Publikum), Good vs Great (ist
unser Signature), Curiosity Gap (Clickbait), Pattern Interrupt (Einwort-Zeile,
kollidiert mit der Pointen-Regel der Textwache).

Familien buendeln Formeln fuer die Steuerung: bei rund 20 Posts im Monat auf
17 Formeln oeffnet das Stichproben-Gate je Formel erst nach Monaten, je
Familie nach etwa sechs Wochen. Kein Modellaufruf in diesem Modul.
"""
import json
import re
from datetime import date, datetime, timedelta

STEERING_MAX_AGE_DAYS = 60

HOOKS = {
    "contrarian": {
        "name": "Contrarian Take", "family": "These",
        "template_de": "Alle sagen {gängiger Rat}. Nach {konkrete Erfahrung} halte ich das für falsch.",
        "template_en": "Everyone says {common advice}. After {specific experience}, I think that is wrong.",
        "trap_de": "Widerspruch gegen etwas, das ohnehin niemand glaubt.",
    },
    "unpopular_rule": {
        "name": "Unpopular Rule", "family": "These",
        "template_de": "Ich mache {verbreitete Praxis} nicht. Nie. Der Grund:",
        "template_en": "I do not {widely accepted practice}. Ever. Here is why.",
        "trap_de": "Eine Regel, die der Autor selbst bricht.",
    },
    "myth_bust": {
        "name": "Myth Bust", "family": "These",
        "template_de": "{Gängige Erklärung} ist nicht der Grund, warum {schlechtes Ergebnis} passiert.",
        "template_en": "{Popular explanation} is not why {bad outcome} is happening to you.",
        "trap_de": "Den wahren Grund nie nennen.",
    },
    "warning": {
        "name": "Warning", "family": "These",
        "template_de": "{Gängige Praxis} kostet still {etwas, das der Leser wirklich will}.",
        "template_en": "{Common practice} is quietly costing you {specific thing they care about}.",
        "trap_de": "Angst ohne Ausweg.",
    },
    "assumption": {
        "name": "Annahme", "family": "These",
        "template_de": "Was {Zielgruppe} annehmen: {die verbreitete Annahme, zugespitzt}.",
        "template_en": "What {audience} assume: {the common assumption, sharpened}.",
        "trap_de": "Eine Annahme, die in der Zielgruppe niemand hat.",
    },
    "number_reveal": {
        "name": "Number Reveal", "family": "Zahl",
        "template_de": "{Ergebniszahl aus dem Asset} in {Zeitraum}. Was dabei wirklich passiert ist.",
        "template_en": "{Result number from the asset} in {period}. Here is what actually happened.",
        "trap_de": "Die Zahl im zweiten Satz vergraben.",
    },
    "time_anchor": {
        "name": "Time Anchor", "family": "Zahl",
        "template_de": "{Aufgabe} hat früher {lange Dauer} gedauert. Heute {kurze Dauer}.",
        "template_en": "{Task} used to take {long time}. It now takes {short time}.",
        "trap_de": "Unglaubwürdiges Verhältnis: fünf Stunden zu zwanzig Minuten trägt, fünf Stunden zu acht Sekunden nicht.",
    },
    "receipt": {
        "name": "Receipt", "family": "Zahl",
        "template_de": "{Harte Zahl aus dem Asset}. {Ein Satz Kontext}.",
        "template_en": "{Hard number from the asset}. {One sentence of context}.",
        "trap_de": "Beleg ohne Geschichte dahinter.",
    },
    "before_after": {
        "name": "Before/After", "family": "Zahl",
        "template_de": "{Zeitpunkt} war {Ausgangslage}. Heute {Ergebnis}. Der Unterschied war {ein einziger Hebel}.",
        "template_en": "{Time ago} it was {low state}. Today {high state}. The difference was {one thing}.",
        "trap_de": "Drei Hebel statt einem.",
    },
    "cold_open": {
        "name": "Story Cold Open", "family": "Szene",
        "template_de": "\"{Ein gesprochener Satz}\"\n\n{Wer ihn sagte, wann, und warum er zählte}.",
        "template_en": "\"{Line of dialogue}\"\n\n{Who said it, when, and why it mattered}.",
        "trap_de": "Ein Satz, den so niemand sagt.",
    },
    "mistake": {
        "name": "Mistake Confession", "family": "Szene",
        "template_de": "{Konkreter Preis} hat mich {ein Fehler} gekostet.",
        "template_en": "{Specific cost} is what {one mistake} cost me.",
        "trap_de": "Falsche Bescheidenheit, und ein Preis ohne Beleg: Zahlen nur aus Quellpost oder Asset, sonst ohne Zahl.",
    },
    "walk_away": {
        "name": "Walk-Away", "family": "Szene",
        "template_de": "Ich habe {etwas Wertvolles} {gekündigt, gestrichen, abgesagt}. {Ergebnis}.",
        "template_en": "I {fired, quit, deleted, cancelled} {valuable thing}. {Result}.",
        "trap_de": "Nicht nennen, was es gekostet hat.",
    },
    "question_trap": {
        "name": "Question Trap", "family": "Frage",
        "template_de": "{Konkrete Situation mit echtem Preis}. Was tun?",
        "template_en": "{Specific scenario with a real cost}. What do you do?",
        "trap_de": "Eine Frage mit offensichtlicher Antwort.",
    },
    "comparison": {
        "name": "Comparison", "family": "Frage",
        "template_de": "{Teure Option} gegen {günstige Option}. {Überraschendes Urteil}.",
        "template_en": "{Expensive option} vs {cheap option}. {Surprising verdict}.",
        "trap_de": "Unfairer Vergleich: einräumen, was die teure Option besser kann.",
    },
    "direct_value": {
        "name": "Direct Value", "family": "Gabe",
        "template_de": "Hier ist genau {Artefakt}, mit dem {konkretes Ergebnis} entstand. Zum Mitnehmen.",
        "template_en": "Here is the exact {artifact} used to {specific outcome}. Steal it.",
        "trap_de": "Das Artefakt hinter einem Gate verstecken statt im Post zu geben.",
    },
    "list_promise": {
        "name": "List Promise", "family": "Gabe",
        "template_de": "{N} Dinge, die mir vor {Meilenstein} niemand gesagt hat.",
        "template_en": "{N} things I wish someone had told me before {milestone}.",
        "trap_de": "N über zehn.",
    },
    "insider_secret": {
        "name": "Insider Secret", "family": "Gabe",
        "template_de": "Nach {N} Jahren {Tätigkeit}: der Teil, der in keiner {Stellenanzeige, Schulung, Pitch} steht.",
        "template_en": "After {N} years {doing thing}, here is the part nobody puts in the {job posting, course, pitch}.",
        "trap_de": "Allgemeinwissen als Geheimnis verkaufen.",
    },
}

# Zahlenformeln brauchen eine belegte Zahl; die liefert nur ein Asset
# (content_matrix.FORMAT_ASSET_ATTR). Der Zahlen-Guard bleibt unveraendert.
NUMBER_HOOKS = frozenset({"number_reveal", "time_anchor", "receipt"})

HOOKS_BY_FORMAT = {
    "Opinion": ("contrarian", "unpopular_rule", "myth_bust", "warning"),
    "POV": ("insider_secret", "myth_bust", "before_after"),
    "Signature": ("assumption",),
    "Story": ("cold_open", "mistake", "walk_away"),
    "Comparison": ("comparison", "warning"),
    "Method": ("direct_value", "list_promise"),
    "CaseProof": ("number_reveal", "time_anchor", "receipt"),
    "Debate": ("question_trap", "contrarian"),
    "Magnet": ("direct_value", "warning"),
    "Offer": ("before_after", "number_reveal"),
}

HOOK_FAMILIES = {}
for _hid, _h in HOOKS.items():
    HOOK_FAMILIES.setdefault(_h["family"], ())
    HOOK_FAMILIES[_h["family"]] = HOOK_FAMILIES[_h["family"]] + (_hid,)


def family_of(hook_id: str) -> str:
    return HOOKS.get(hook_id, {}).get("family", "")
```

- [ ] **Step 4: Test laufen lassen, erwartet PASS**

Run: `python -m pytest tests/test_hooks.py -v -p no:cacheprovider`
Expected: 4 passed

- [ ] **Step 5: Commit**

Commit-Message-Datei `.tmp/commitmsg.txt`:

```
feat(hooks): Hook-Katalog mit 17 Formeln in fuenf Familien

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
```

```bash
git add tools/hooks.py tests/test_hooks.py
git commit -F .tmp/commitmsg.txt
git push origin master
```

---

### Task 2: Rotation und Steuerung lesen (`pick_hook`, `load_steering`)

**Files:**
- Modify: `tools/hooks.py` (ans Ende anhaengen)
- Test: `tests/test_hooks.py`

**Interfaces:**
- Consumes: `HOOKS`, `HOOKS_BY_FORMAT` aus Task 1.
- Produces: `load_steering(raw: str, today: date) -> dict` (leer bei Alter ueber `STEERING_MAX_AGE_DAYS`, unlesbarem JSON oder fehlendem `as_of`); `pick_hook(fmt: str, recent: list[str], steering: dict | None = None) -> str`.

- [ ] **Step 1: Failing Tests anhaengen**

```python
from datetime import date


def test_pick_hook_takes_the_longest_unused_candidate():
    # recent: neueste zuerst. warning nie genutzt -> zuerst dran.
    assert hooks.pick_hook("Opinion", ["contrarian", "myth_bust", "unpopular_rule"]) == "warning"
    # alle genutzt: der am laengsten zurueckliegende (unpopular_rule, Index 3)
    assert hooks.pick_hook("Opinion", ["contrarian", "myth_bust", "warning", "unpopular_rule"]) == "unpopular_rule"


def test_pick_hook_tie_falls_back_to_catalog_order_and_signature_is_fixed():
    assert hooks.pick_hook("Opinion", []) == "contrarian"
    assert hooks.pick_hook("Signature", ["assumption"]) == "assumption"
    assert hooks.pick_hook("Unbekannt", []) == "contrarian"   # Rueckfall Opinion


def test_pick_hook_stop_blocks_family_but_never_the_whole_format():
    st = {"stop": ["These"], "do_more": [], "as_of": "2026-10-05", "n": 20}
    assert hooks.pick_hook("Debate", [], st) == "question_trap"       # contrarian (These) gesperrt
    assert hooks.pick_hook("Opinion", [], st) == "contrarian"          # nur These -> STOP ignoriert


def test_pick_hook_do_more_halves_the_wait():
    st = {"stop": [], "do_more": ["Szene"], "as_of": "2026-10-05", "n": 20}
    # cold_open lief vor 2 Posts, walk_away vor 3. Ohne Steuerung gewinnt walk_away.
    recent = ["mistake", "cold_open", "walk_away"]
    assert hooks.pick_hook("Story", recent) == "walk_away"
    # Mit DO MORE Szene zaehlt jeder Abstand doppelt, alle drei sind Szene:
    # Reihenfolge bleibt. Gegenprobe mit einer fremden Familie im Format:
    st2 = {"stop": [], "do_more": ["Frage"], "as_of": "2026-10-05", "n": 20}
    # Comparison: comparison (Frage) vor 1 Post, warning (These) vor 2 Posts.
    assert hooks.pick_hook("Comparison", ["comparison", "warning"]) == "warning"
    assert hooks.pick_hook("Comparison", ["comparison", "warning"], st2) == "comparison"


def test_load_steering_expires_after_sixty_days_and_survives_garbage():
    raw = '{"stop": ["These"], "do_more": [], "as_of": "2026-09-01", "n": 12}'
    assert hooks.load_steering(raw, date(2026, 10, 1))["stop"] == ["These"]
    assert hooks.load_steering(raw, date(2026, 11, 15)) == {}
    assert hooks.load_steering("", date(2026, 10, 1)) == {}
    assert hooks.load_steering("kein json", date(2026, 10, 1)) == {}
    assert hooks.load_steering('{"stop": []}', date(2026, 10, 1)) == {}
```

- [ ] **Step 2: Tests laufen lassen, erwartet FAIL**

Run: `python -m pytest tests/test_hooks.py -v -p no:cacheprovider`
Expected: 5 neue FAIL mit `AttributeError: module 'tools.hooks' has no attribute 'pick_hook'`

- [ ] **Step 3: Implementieren (ans Ende von `tools/hooks.py`)**

```python
def load_steering(raw: str, today: date) -> dict:
    """Steuerlisten aus engine_meta["hook_steering_<client>"]. Leer, wenn
    das JSON unlesbar ist, as_of fehlt oder aelter als STEERING_MAX_AGE_DAYS
    ist: ein alter Befund darf nicht ewig weitersteuern."""
    try:
        data = json.loads(raw or "")
        as_of = date.fromisoformat(str(data["as_of"]))
    except (ValueError, KeyError, TypeError):
        return {}
    if today - as_of > timedelta(days=STEERING_MAX_AGE_DAYS):
        return {}
    return {"stop": list(data.get("stop") or []),
            "do_more": list(data.get("do_more") or []),
            "as_of": as_of.isoformat(), "n": int(data.get("n") or 0)}


def pick_hook(fmt: str, recent: list[str], steering: dict | None = None) -> str:
    """Deterministische Rotation: der am laengsten nicht genutzte Kandidat des
    Formats. recent sind die letzten Hook-IDs aus Notion, neueste zuerst.
    STOP sperrt Familien, sperrt es alle Kandidaten des Formats, gilt es
    fuer dieses Format nicht (Log). DO-MORE-Familien zaehlen ihren Abstand
    doppelt, sie kommen also doppelt so oft dran. Gleichstand: Katalogreihe."""
    cands = HOOKS_BY_FORMAT.get(fmt) or HOOKS_BY_FORMAT["Opinion"]
    steering = steering or {}
    stop, do_more = set(steering.get("stop", [])), set(steering.get("do_more", []))
    allowed = [h for h in cands if family_of(h) not in stop]
    if not allowed:
        print(f"  Hook-Steuerung: STOP sperrt alle Formeln von {fmt}, ignoriert.", flush=True)
        allowed = list(cands)

    def age(h: str) -> int:
        try:
            posts_since = recent.index(h) + 1
        except ValueError:
            posts_since = len(recent) + len(cands) + 1
        return posts_since * (2 if family_of(h) in do_more else 1)

    return max(allowed, key=lambda h: (age(h), -cands.index(h)))
```

- [ ] **Step 4: Tests laufen lassen, erwartet PASS**

Run: `python -m pytest tests/test_hooks.py -v -p no:cacheprovider`
Expected: 9 passed

- [ ] **Step 5: Commit**

```
feat(hooks): deterministische Rotation mit STOP/DO-MORE-Steuerung

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
```

```bash
git add tools/hooks.py tests/test_hooks.py
git commit -F .tmp/commitmsg.txt
git push origin master
```

---

### Task 3: Hook-Zeile in den Prompt

**Files:**
- Modify: `tools/hooks.py` (`hook_line`, `inject_hook`)
- Modify: `tools/post_scorer.py:692-740` (`_format_prompts`), `tools/post_scorer.py:1783-1830` (`generate_post_and_image_prompt`)
- Test: `tests/test_hooks_prompt.py`

**Interfaces:**
- Produces: `hooks.hook_line(hook_id: str, lang: str) -> str`; `hooks.inject_hook(structure: str, hook_id: str, lang: str) -> str` (ersetzt genau die Zeile, die mit `1. Hook` beginnt; ohne Treffer oder ohne hook_id unveraendert); `_format_prompts(..., hook_id: str = "")`; `generate_post_and_image_prompt(..., hook_id: str = "")`.

- [ ] **Step 1: Failing Tests schreiben**

```python
"""Hook-Zeile ersetzt Zeile 1 der Formatstruktur. Kein Netz."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import hooks
from tools import post_scorer as ps

POST = {"influencer": "Anna", "post_text": "Quelle " * 30}


def test_hook_line_carries_name_template_and_trap():
    line = hooks.hook_line("contrarian", "de")
    assert line.startswith("1. Hook (1-2 Sätze), Formel Contrarian Take: ")
    assert "Alle sagen" in line and "Falle: Widerspruch" in line
    assert line.endswith("Entscheidet, ob jemand weiterliest.")
    en = hooks.hook_line("contrarian", "en")
    assert en.startswith("1. Hook (1-2 sentences), formula Contrarian Take: ")
    assert "Everyone says" in en and "Trap: " in en


def test_inject_hook_replaces_only_the_hook_line():
    de = ps.FORMAT_STRUCTURES["Opinion"]["de"]
    out = hooks.inject_hook(de, "warning", "de")
    assert out.count("\n") == de.count("\n")
    assert "Formel Warning" in out
    assert "kontroverse These" not in out
    rest_alt = "\n".join(de.splitlines()[2:])
    assert rest_alt in out
    assert hooks.inject_hook(de, "", "de") == de
    assert hooks.inject_hook("keine Struktur", "warning", "de") == "keine Struktur"


def test_format_prompts_take_the_hook_in_both_languages():
    de, en = ps._format_prompts(POST, "Opinion", hook_id="myth_bust")
    assert "Formel Myth Bust" in de and "Gängige Erklärung" in de
    assert "formula Myth Bust" in en and "Popular explanation" in en
    de0, _ = ps._format_prompts(POST, "Opinion")
    assert "Formel Myth Bust" not in de0 and "kontroverse These" in de0


def test_kurz_band_has_no_hook_line_and_stays_untouched():
    de, _ = ps._format_prompts(POST, "Opinion", band="kurz", hook_id="myth_bust")
    assert "Formel Myth Bust" not in de and "These in einem Satz" in de
```

- [ ] **Step 2: Tests laufen lassen, erwartet FAIL**

Run: `python -m pytest tests/test_hooks_prompt.py -v -p no:cacheprovider`
Expected: FAIL mit `AttributeError: ... 'hook_line'`

- [ ] **Step 3: `hook_line` und `inject_hook` in `tools/hooks.py` anhaengen**

```python
_HOOK_LINE_RE = re.compile(r"(?m)^1\. Hook[^\n]*$")


def hook_line(hook_id: str, lang: str) -> str:
    """Zeile 1 der Formatstruktur fuer diese Formel, mit Falle."""
    h = HOOKS[hook_id]
    if lang == "en":
        return (f"1. Hook (1-2 sentences), formula {h['name']}: {h['template_en']} "
                f"Trap: {h['trap_de']} Decides whether anyone reads on.")
    return (f"1. Hook (1-2 Sätze), Formel {h['name']}: {h['template_de']} "
            f"Falle: {h['trap_de']} Entscheidet, ob jemand weiterliest.")


def inject_hook(structure: str, hook_id: str, lang: str) -> str:
    """Ersetzt genau die Zeile "1. Hook ..." der Struktur. Ohne hook_id oder
    ohne Hook-Zeile (Kurzform) bleibt die Struktur, wie sie ist."""
    if not hook_id or hook_id not in HOOKS:
        return structure
    # Lambda statt Ersetzungsstring: so bleiben Backslashes und Klammern der
    # Vorlage unangetastet.
    return _HOOK_LINE_RE.sub(lambda m: hook_line(hook_id, lang), structure, count=1)
```

Hinweis: `trap_de` steht auch in der EN-Zeile, der Katalog fuehrt bewusst nur eine Falle; das Modell versteht die deutsche Falle im englischen Prompt.

- [ ] **Step 4: `_format_prompts` und `generate_post_and_image_prompt` erweitern**

In `tools/post_scorer.py`, Import ergaenzen (Zeile 15):

```python
from tools import hooks, naturalness, text_gate
```

`_format_prompts`: Parameter `hook_id: str = ""` nach `avoid_phrases` anfuegen. Die zwei Strukturstellen ersetzen:

```python
        structure_block=_client_structure(hooks.inject_hook(structures["de"], hook_id, "de")),
```

und

```python
        structure_block=hooks.inject_hook(structures["en"], hook_id, "en"),
```

Docstring-Zusatz in `_format_prompts`: `hook_id waehlt die Hook-Formel (tools/hooks), sie ersetzt Zeile 1 der Struktur; leer laesst die Formatzeile stehen.`

`generate_post_and_image_prompt`: Parameter `hook_id: str = ""` nach `avoid_phrases` anfuegen und beim Aufruf von `_format_prompts` durchreichen (`hook_id=hook_id`).

- [ ] **Step 5: Tests laufen lassen, erwartet PASS**

Run: `python -m pytest tests/test_hooks_prompt.py tests/test_format_structures.py -v -p no:cacheprovider`
Expected: alle passed (die bestehenden Struktur-Tests bleiben gruen, weil ohne hook_id nichts ersetzt wird)

- [ ] **Step 6: Commit**

```
feat(hooks): Hook-Formel ersetzt Zeile 1 der Formatstruktur im DE- und EN-Prompt

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
```

```bash
git add tools/hooks.py tools/post_scorer.py tests/test_hooks_prompt.py
git commit -F .tmp/commitmsg.txt
git push origin master
```

---

### Task 4: Notion liest und schreibt "Hook", Seed-Skript, System-Check

**Files:**
- Modify: `tools/notion_db.py:395-500` (`update_with_draft`), `tools/notion_db.py:604-636` (neben `get_recent_formats`), `tools/notion_db.py:952` (`ENGAGEMENT_DIMENSIONS`)
- Create: `scripts/add_hook_property.py`
- Modify: `tools/system_check.py:35-45` und `tools/system_check.py:150-175` (`check_notion`)
- Test: `tests/test_notion_db_hooks.py`, `tests/test_system_check.py` (anhaengen)

**Interfaces:**
- Produces: `notion_db.get_recent_hooks(limit: int = 20) -> list[str]` (neueste zuerst, Status Posted/Posting/Approved/Ready to Review); `update_with_draft(..., hook: str = "")`; `ENGAGEMENT_DIMENSIONS` enthaelt `"Hook"`, also traegt `get_published_rows()[i]["dims"]["Hook"]` die Formel; `system_check.SOFT_NOTION_PROPS = ("Hook",)`.

- [ ] **Step 1: Failing Tests schreiben**

`tests/test_notion_db_hooks.py`:

```python
"""Hook-Property lesen und schreiben. _notion_request gemockt."""
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import notion_db


def _resp(payload):
    r = MagicMock(status_code=200)
    r.json.return_value = payload
    r.raise_for_status.return_value = None
    return r


def test_update_with_draft_writes_hook_non_fatal(monkeypatch):
    monkeypatch.setenv("NOTION_TOKEN", "tok")
    monkeypatch.setattr(notion_db, "MAKE_REVIEW_WEBHOOK", "", raising=False)
    with patch("tools.notion_db._notion_request", return_value=_resp({"id": "p1"})) as m:
        notion_db.update_with_draft(page_id="p1", linkedin_draft="DE", image_prompt="",
                                    image_url="", hook="warning")
    found = [c.kwargs.get("json", {}).get("properties", {}).get("Hook")
             for c in m.call_args_list]
    assert {"select": {"name": "warning"}} in found


def test_update_with_draft_survives_missing_hook_property(monkeypatch):
    monkeypatch.setenv("NOTION_TOKEN", "tok")
    monkeypatch.setattr(notion_db, "MAKE_REVIEW_WEBHOOK", "", raising=False)

    def fake(method, url, headers=None, json=None, **kw):
        if json and "Hook" in (json.get("properties") or {}):
            raise RuntimeError("property missing")
        return _resp({"id": "p1"})

    with patch("tools.notion_db._notion_request", side_effect=fake):
        notion_db.update_with_draft(page_id="p1", linkedin_draft="DE", image_prompt="",
                                    image_url="", hook="warning")   # darf nicht werfen


def test_get_recent_hooks_returns_newest_first_and_skips_blank(monkeypatch):
    monkeypatch.setenv("NOTION_TOKEN", "tok")
    pages = {"results": [
        {"properties": {"Hook": {"select": {"name": "warning"}}}},
        {"properties": {"Hook": {"select": None}}},
        {"properties": {"Hook": {"select": {"name": "cold_open"}}}},
    ]}
    with patch("tools.notion_db._notion_request", return_value=_resp(pages)) as m:
        assert notion_db.get_recent_hooks(limit=20) == ["warning", "cold_open"]
    assert m.call_args.kwargs["json"]["page_size"] == 20


def test_hook_is_an_engagement_dimension():
    assert "Hook" in notion_db.ENGAGEMENT_DIMENSIONS
```

An `tests/test_system_check.py` anhaengen:

```python
def test_hook_property_is_soft_and_names_the_seed_script():
    from tools import system_check as sc
    assert "Hook" in sc.SOFT_NOTION_PROPS
    assert "Hook" not in sc.CORE_NOTION_PROPS
    out = sc.soft_notion_findings(present={"Status", "Format"})
    assert len(out) == 1 and out[0]["severity"] == sc.SOFT and not out[0]["ok"]
    assert "scripts/add_hook_property.py" in out[0]["detail"]
    assert sc.soft_notion_findings(present={"Hook"})[0]["ok"]
```

- [ ] **Step 2: Tests laufen lassen, erwartet FAIL**

Run: `python -m pytest tests/test_notion_db_hooks.py tests/test_system_check.py -v -p no:cacheprovider`
Expected: neue Tests FAIL (`TypeError: unexpected keyword 'hook'`, `AttributeError: get_recent_hooks`, `SOFT_NOTION_PROPS`)

- [ ] **Step 3: `notion_db.py` erweitern**

`ENGAGEMENT_DIMENSIONS` (Zeile 952):

```python
ENGAGEMENT_DIMENSIONS = ("Format", "Persona", "Bild-Variante", "Infografik-Typ",
                         "Matrix-Job", "Matrix-Stage", "Poster", "Hook")
```

`update_with_draft`: Parameter `hook: str = ""` nach `post_url` anfuegen. Direkt nach dem Format-Block (nach Zeile ~477) einfuegen:

```python
    # Hook-Formel separat + non-fatal (wie Format): treibt die Rotation im
    # naechsten Run via get_recent_hooks und ist der Join-Schluessel des
    # Hook-Audits (tools/hook_audit). Fehlt die Property, laeuft der Post ohne.
    if hook:
        try:
            hr = _notion_request(
                "PATCH",
                f"{NOTION_API}/pages/{page_id}",
                headers=_headers(),
                json={"properties": {"Hook": {"select": {"name": hook}}}},
            )
            hr.raise_for_status()
            print(f"  Hook-Property gesetzt: {hook}", flush=True)
        except Exception as e:
            print(f"  Hook-Property fehlgeschlagen (nicht kritisch): {e}", flush=True)
```

Nach `get_recent_formats` einfuegen:

```python
def get_recent_hooks(limit: int = 20) -> list[str]:
    """Hook-Formeln der letzten N Eintraege, neueste zuerst, fuer die
    Rotation (tools/hooks.pick_hook). Tolerant: fehlende Property -> []."""
    payload = {
        "filter": {
            "or": [
                {"property": "Status", "select": {"equals": "Posted"}},
                {"property": "Status", "select": {"equals": "Posting"}},
                {"property": "Status", "select": {"equals": "Approved"}},
                {"property": "Status", "select": {"equals": "Ready to Review"}},
            ]
        },
        "sorts": [{"timestamp": "last_edited_time", "direction": "descending"}],
        "page_size": limit,
    }
    resp = _notion_request("POST", f"{NOTION_API}/databases/{NOTION_DB_ID}/query",
                           headers=_headers(), json=payload)
    resp.raise_for_status()
    out = []
    for page in resp.json().get("results", []):
        name = _select_name(page.get("properties", {}), "Hook")
        if name:
            out.append(name)
    return out
```

- [ ] **Step 4: Seed-Skript `scripts/add_hook_property.py`**

```python
"""Einmalig, idempotent: legt das Select "Hook" mit allen Katalog-IDs
(tools/hooks.HOOKS) in der Content-DB des Mandanten an. Mehrfach ausfuehrbar;
fehlende Optionen werden ergaenzt. Aufruf: CLIENT=jolly python scripts/add_hook_property.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools.hooks import HOOKS
from tools.notion_db import NOTION_API, NOTION_DB_ID, _headers, _notion_request


def ensure_hook_property() -> None:
    r = _notion_request("GET", f"{NOTION_API}/databases/{NOTION_DB_ID}", headers=_headers())
    r.raise_for_status()
    existing = r.json().get("properties", {}).get("Hook")
    have = {o["name"] for o in ((existing or {}).get("select") or {}).get("options", [])}
    missing = [h for h in HOOKS if h not in have]
    if existing and not missing:
        print("Hook-Property vollstaendig - nichts zu tun.")
        return
    options = [{"name": n} for n in sorted(have | set(HOOKS))]
    r = _notion_request("PATCH", f"{NOTION_API}/databases/{NOTION_DB_ID}", headers=_headers(),
                        json={"properties": {"Hook": {"select": {"options": options}}}})
    r.raise_for_status()
    print(f"Hook-Property gesetzt, {len(missing)} Optionen ergaenzt: {', '.join(missing)}")


if __name__ == "__main__":
    ensure_hook_property()
```

- [ ] **Step 5: `system_check.py` erweitern**

Nach `ABM_COMMENT_NOTION_PROPS` (Zeile ~45):

```python
# Weiche Properties: fehlen sie, laeuft der Post ohne (non-fatal geschrieben),
# der Check nennt nur das Seed-Skript. "Hook" seit 14.09.2026 (tools/hooks).
SOFT_NOTION_PROPS = ("Hook",)
SOFT_NOTION_SEEDS = {"Hook": "scripts/add_hook_property.py"}


def soft_notion_findings(present: set) -> list:
    """Ein weicher Befund je SOFT_NOTION_PROPS-Eintrag."""
    return [_result(f"notion:property:{p}", p in present, SOFT,
                    "vorhanden" if p in present
                    else f"fehlt, anlegen mit: python {SOFT_NOTION_SEEDS[p]}")
            for p in SOFT_NOTION_PROPS]
```

In `check_notion` (Zeile 166-171) die Rueckgabeliste erweitern; `present` ist dort schon die Menge der Property-Namen:

```python
    return [
        _result("notion:db", True, HARD, f"erreichbar ({len(present)} Properties)"),
        _result("notion:properties", not missing, HARD,
                "vollstaendig" if not missing else f"fehlen: {', '.join(missing)}"),
        *soft_notion_findings(present),
    ]
```

Pruefen, dass `run_system_check` weiche Befunde (`SOFT`) nicht als NO-GO wertet (so behandelt es heute schon `KIEAI_API_KEY`).

- [ ] **Step 6: Tests laufen lassen, erwartet PASS**

Run: `python -m pytest tests/test_notion_db_hooks.py tests/test_system_check.py tests/test_notion_db_formats.py tests/test_engagement_stats.py -v -p no:cacheprovider`
Expected: alle passed

- [ ] **Step 7: Seed einmal ausfuehren (Jolly-DB, Richard hat das Notion-Token in .env)**

Run: `python scripts/add_hook_property.py`
Expected: `Hook-Property gesetzt, 17 Optionen ergaenzt: ...`. Zweiter Lauf: `Hook-Property vollstaendig - nichts zu tun.`

- [ ] **Step 8: Commit**

```
feat(notion): Select "Hook" lesen, schreiben und seeden; weicher System-Check-Befund

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
```

```bash
git add tools/notion_db.py tools/system_check.py scripts/add_hook_property.py tests/test_notion_db_hooks.py tests/test_system_check.py
git commit -F .tmp/commitmsg.txt
git push origin master
```

---

### Task 5: `run_research.py` waehlt den Hook

**Files:**
- Modify: `run_research.py:225-270` (nach dem Asset-Backstop), `run_research.py:300-312` (Generierung), `run_research.py:433-450` (Notion-Update)
- Test: `tests/test_run_research_hook.py`

**Interfaces:**
- Consumes: `hooks.pick_hook`, `hooks.load_steering`, `notion_db.get_recent_hooks`, `topic_pool.get_meta`.
- Produces: `run_research.choose_hook(cfg, post_format: str, today: date) -> str` (reine Wrapper-Funktion, damit sie testbar ist).

- [ ] **Step 1: Failing Test schreiben**

```python
"""Hook-Wahl im Winner-Flow: Rotation aus Notion plus Steuerung aus engine_meta.
Alles gemockt, kein Netz."""
import os
import sys
from datetime import date
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import run_research as rr


def test_choose_hook_uses_recent_hooks_and_steering(monkeypatch):
    monkeypatch.setattr(rr, "get_recent_hooks", lambda limit=20: ["contrarian", "warning"])
    monkeypatch.setattr(rr, "get_meta", lambda key: '{"stop": ["These"], "do_more": [], "as_of": "2026-10-01", "n": 10}')
    cfg = SimpleNamespace(NAME="jolly")
    # Debate: contrarian (These) gesperrt -> question_trap
    assert rr.choose_hook(cfg, "Debate", date(2026, 10, 5)) == "question_trap"


def test_choose_hook_survives_notion_and_meta_failures(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("down")
    monkeypatch.setattr(rr, "get_recent_hooks", boom)
    monkeypatch.setattr(rr, "get_meta", boom)
    assert rr.choose_hook(SimpleNamespace(NAME="jolly"), "Opinion", date(2026, 10, 5)) == "contrarian"
```

- [ ] **Step 2: Test laufen lassen, erwartet FAIL**

Run: `python -m pytest tests/test_run_research_hook.py -v -p no:cacheprovider`
Expected: FAIL mit `AttributeError: module 'run_research' has no attribute 'choose_hook'`

- [ ] **Step 3: Implementieren**

Imports in `run_research.py` ergaenzen: `get_recent_hooks` in das bestehende mehrzeilige `from tools.notion_db import (...)` (Zeile 31) aufnehmen; die zwei anderen Zeilen neu daneben (`tools.topic_pool` ist dort noch nicht importiert):

```python
from tools.hooks import HOOKS, load_steering, pick_hook
from tools.topic_pool import get_meta
```

Funktion auf Modulebene (vor `run_daily`):

```python
def choose_hook(cfg, post_format: str, today) -> str:
    """Hook-Formel fuer diesen Post: Rotation ueber die letzten 20 Hooks aus
    Notion plus Steuerlisten aus engine_meta (tools/hooks). Beide Quellen
    sind nicht kritisch: ohne sie laeuft die Rotation ab Katalogreihe."""
    try:
        recent = get_recent_hooks(limit=20)
    except Exception as e:
        print(f"  Recent-Hooks laden fehlgeschlagen (nicht kritisch): {e}", file=sys.stderr)
        recent = []
    try:
        steering = load_steering(get_meta(f"hook_steering_{cfg.NAME}"), today)
    except Exception as e:
        print(f"  Hook-Steuerung nicht lesbar (nicht kritisch): {e}", file=sys.stderr)
        steering = {}
    hook_id = pick_hook(post_format, recent, steering)
    print(f"  Hook: {hook_id} ({HOOKS[hook_id]['name']}), zuletzt: {recent[:3]}, "
          f"Steuerung: STOP {steering.get('stop', [])} DO MORE {steering.get('do_more', [])}")
    return hook_id
```

In `run_daily`, direkt nach dem Block "Asset-Formate (CaseProof/Magnet/Offer) fahren immer die dominante Persona" (das Format steht danach endgueltig fest):

```python
    # Schritt 4.7: Hook-Formel (Rotation, Spec 2026-09-14). Nach dem
    # Asset-Backstop, weil der das Format noch aendern kann.
    hook_id = choose_hook(_cfg, post_format, datetime.now(timezone.utc).date())
```

Alle drei Aufrufe von `generate_post_and_image_prompt` in `run_daily` (Zeilen ~304, ~334, ~345) bekommen `hook_id=hook_id,`. Der Aufruf `update_with_draft` (Zeile ~433) bekommt `hook=hook_id,`.

- [ ] **Step 4: Tests laufen lassen, erwartet PASS**

Run: `python -m pytest tests/test_run_research_hook.py tests/test_run_research_schedule.py tests/test_daily_keyword_source.py -v -p no:cacheprovider`
Expected: alle passed

- [ ] **Step 5: Gesamtsuite**

Run: `python -m pytest -q -p no:cacheprovider`
Expected: alle passed (Baseline vor diesem Plan: 746)

- [ ] **Step 6: Commit**

```
feat(research): Hook-Formel je Post waehlen und nach Notion schreiben

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
```

```bash
git add run_research.py tests/test_run_research_hook.py
git commit -F .tmp/commitmsg.txt
git push origin master
```

---

### Task 6: Textwache, 140 Zeichen fuer Zeile 1

**Files:**
- Modify: `tools/text_gate.py` (`shape_notes`)
- Test: `tests/test_text_gate.py` (anhaengen)

**Interfaces:**
- Produces: `text_gate.MAX_FIRST_LINE_CHARS = 140`; `shape_notes` liefert zusaetzlich `"Erste Zeile {n} Zeichen, mobil bricht LinkedIn bei etwa 140: Hook kuerzen"`.

- [ ] **Step 1: Failing Test anhaengen**

```python
def test_shape_notes_flag_a_first_line_over_140_chars():
    lang = "A" * 150 + "."
    text = "\n\n" + lang + "\n\nZweiter Absatz."
    assert any("Erste Zeile 151 Zeichen" in n for n in tg.shape_notes(text))
    assert not any("Erste Zeile" in n for n in tg.shape_notes("Kurz.\n\n" + lang))
```

- [ ] **Step 2: Test laufen lassen, erwartet FAIL**

Run: `python -m pytest tests/test_text_gate.py -v -p no:cacheprovider -k first_line`
Expected: FAIL (assert False)

- [ ] **Step 3: Implementieren**

Konstante neben `MIN_SENTENCE_CV`:

```python
MAX_FIRST_LINE_CHARS = 140   # mobiler Schnitt "mehr anzeigen" (Repo-Vergleich 14.09.2026)
```

Am Ende von `shape_notes` vor `return out`:

```python
    first = next((l.strip() for l in text.splitlines() if l.strip()), "")
    if len(first) > MAX_FIRST_LINE_CHARS:
        out.append(f"Erste Zeile {len(first)} Zeichen, mobil bricht LinkedIn bei etwa "
                   f"{MAX_FIRST_LINE_CHARS}: Hook kuerzen")
```

- [ ] **Step 4: Tests laufen lassen, erwartet PASS**

Run: `python -m pytest tests/test_text_gate.py -v -p no:cacheprovider`
Expected: alle passed, auch die Kalibrierung an Kulles Schreibproben

- [ ] **Step 5: Commit**

```
feat(gate): Hinweis bei erster Zeile ueber 140 Zeichen

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
```

```bash
git add tools/text_gate.py tests/test_text_gate.py
git commit -F .tmp/commitmsg.txt
git push origin master
```

---

### Task 7: Export-Parser und Join (`tools/hook_audit.py`, Teil 1)

**Files:**
- Create: `tools/hook_audit.py`
- Test: `tests/test_hook_audit.py`

**Interfaces:**
- Consumes: `engagement_readback.extract_ids`, `hooks.family_of`.
- Produces: `read_export(path: str) -> dict[str, dict]` (Objekt-ID -> `{"id", "url", "date", "engagements", "impressions"}`); `window_days(path: str) -> int | None`; `join_rows(export: dict, rows: list[dict]) -> dict` mit Schluesseln `joined: list[dict]`, `unmatched_export: list[str]`, `rows_without_hook: int`, `rows_without_url: int`; jede gejointe Zeile traegt `id`, `impressions`, `export_engagements`, `hook`, `family`, `weekday`, plus alle Felder der Notion-Zeile.

- [ ] **Step 1: Failing Tests schreiben**

```python
"""Hook-Audit: Export-Parser, Join, Metriken, Gate, Steuerung. Kein Netz.
Fixture ist die echte Export-Datei (Live-Form)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import hook_audit as ha

ROOT = os.path.dirname(os.path.dirname(__file__))
EXPORT = os.path.join(ROOT, "Resources", "analytics", "top_posts_2025-08-20_2026-08-19.csv")


def test_read_export_joins_both_blocks_by_object_id():
    data = ha.read_export(EXPORT)
    assert len(data) == 50
    row = data["7430202667907428352"]
    assert row["impressions"] == 7132 and row["engagements"] == 20
    assert row["date"] == "2026-02-26"
    assert all(r["impressions"] is not None for r in data.values())


def test_window_days_reads_the_filename():
    assert ha.window_days(EXPORT) == 364
    assert ha.window_days("top_posts_2026-09-01_2026-09-28.csv") == 27
    assert ha.window_days("irgendwas.csv") is None


def _row(url, hook="", likes=5, comments=1, shares=0, fmt="Opinion", posted="2026-06-19"):
    return {"page_id": url, "live_url": url, "posted_at": posted,
            "likes": likes, "comments": comments, "shares": shares,
            "dims": {"Hook": hook, "Format": fmt, "Persona": "founder-gf"}}


A, B, C = "7430000000000000111", "7430000000000000222", "7430000000000000333"   # 19-stellig wie echte Objekt-IDs


def test_join_counts_every_denominator():
    export = {A: {"id": A, "url": f"u/{A}", "date": "2026-06-19", "engagements": 9, "impressions": 900},
              B: {"id": B, "url": f"u/{B}", "date": "2026-06-20", "engagements": 3, "impressions": 300}}
    rows = [_row(f"https://www.linkedin.com/posts/x-{A}-abc", hook="warning"),
            _row(f"https://www.linkedin.com/posts/x-{C}-abc", hook=""),
            _row("", hook="warning")]
    out = ha.join_rows(export, rows)
    assert [r["id"] for r in out["joined"]] == [A]
    assert out["joined"][0]["impressions"] == 900
    assert out["joined"][0]["family"] == "These"
    assert out["joined"][0]["weekday"] == "Fr"
    assert out["unmatched_export"] == [B]
    assert out["rows_without_hook"] == 1 and out["rows_without_url"] == 1
```

- [ ] **Step 2: Tests laufen lassen, erwartet FAIL**

Run: `python -m pytest tests/test_hook_audit.py -v -p no:cacheprovider`
Expected: FAIL mit `ModuleNotFoundError: tools.hook_audit`

- [ ] **Step 3: Implementieren**

```python
"""Hook-Audit: nativer LinkedIn-Export plus Notion-Readback, ausgewertet je
Hook-Familie, Hook, Format, Persona und Wochentag (Spec docs/superpowers/
specs/2026-09-14-hook-katalog-und-audit-design.md).

Datenlage: Impressions gibt es nur aus dem Export (Top 50 des Fensters, bei
28 Tagen alles), Likes/Kommentare/Shares aus dem Readback. Der Join laeuft
ueber die LinkedIn-Objekt-ID in der URL. Kein Modellaufruf; alle Aussagen
tragen n, unter dem Gate gibt es keine Aussage.
"""
import csv
import os
import re
import statistics
from datetime import date, datetime

from tools.engagement_readback import extract_ids
from tools.hooks import family_of

_FILE_RE = re.compile(r"top_posts_(\d{4}-\d{2}-\d{2})_(\d{4}-\d{2}-\d{2})\.csv$")
WEEKDAYS = ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")


def _int(v) -> int | None:
    try:
        return int(str(v).replace(".", "").replace(",", "").strip())
    except ValueError:
        return None


def _iso(us_date: str) -> str:
    """6/19/2026 -> 2026-06-19; unbekanntes Format bleibt stehen."""
    try:
        return datetime.strptime(us_date.strip(), "%m/%d/%Y").date().isoformat()
    except ValueError:
        return us_date.strip()


def read_export(path: str) -> dict:
    """Zweiblockiges Layout des nativen Exports: links URL, Datum,
    Engagements; rechts (ab Spalte 4) URL, Datum, Impressions. Beide
    Bloecke werden ueber die Objekt-ID zusammengefuehrt."""
    out = {}
    with open(path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.reader(fh)
        next(reader, None)
        for cells in reader:
            cells = list(cells) + [""] * 7
            for url, when, value, key in ((cells[0], cells[1], cells[2], "engagements"),
                                          (cells[4], cells[5], cells[6], "impressions")):
                ids = extract_ids(url)
                if not ids:
                    continue
                pid = sorted(ids)[0]
                row = out.setdefault(pid, {"id": pid, "url": url, "date": _iso(when),
                                           "engagements": None, "impressions": None})
                row[key] = _int(value)
    return out


def window_days(path: str) -> int | None:
    m = _FILE_RE.search(os.path.basename(path))
    if not m:
        return None
    a, b = (date.fromisoformat(x) for x in m.groups())
    return (b - a).days


def join_rows(export: dict, rows: list) -> dict:
    """Notion-Zeilen (notion_db.get_published_rows) mit dem Export joinen.
    Zaehlt jeden Nenner: Export ohne Notion-Treffer (manuelle Posts),
    Notion ohne Hook (Bestand vor Rollout), Notion ohne URL."""
    joined, seen, no_hook, no_url = [], set(), 0, 0
    for row in rows:
        hook = (row.get("dims") or {}).get("Hook", "")
        if not hook:
            no_hook += 1
        ids = extract_ids(row.get("live_url", ""))
        if not ids:
            no_url += 1
            continue
        hit = next((export[i] for i in ids if i in export), None)
        if not hit:
            continue
        seen.add(hit["id"])
        posted = (row.get("posted_at") or hit["date"] or "")[:10]
        try:
            weekday = WEEKDAYS[date.fromisoformat(posted).weekday()]
        except ValueError:
            weekday = ""
        joined.append({**row, "id": hit["id"], "impressions": hit["impressions"],
                       "export_engagements": hit["engagements"], "hook": hook,
                       "family": family_of(hook), "weekday": weekday})
    return {"joined": joined, "unmatched_export": sorted(set(export) - seen),
            "rows_without_hook": no_hook, "rows_without_url": no_url}
```

- [ ] **Step 4: Tests laufen lassen, erwartet PASS**

Run: `python -m pytest tests/test_hook_audit.py -v -p no:cacheprovider`
Expected: 3 passed. Faellt `read_export` an der echten Datei, erst die Datei mit `head -3` pruefen (Header muss `Post URL,Post Publish Date,Engagements,,Post URL,Post Publish Date,Impressions` sein), dann den Parser anpassen, nie den Test.

- [ ] **Step 5: Commit**

```
feat(audit): Export-Parser und Join ueber die LinkedIn-Objekt-ID

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
```

```bash
git add tools/hook_audit.py tests/test_hook_audit.py
git commit -F .tmp/commitmsg.txt
git push origin master
```

---

### Task 8: Metriken, Aggregation, Gate, Steuerung (`tools/hook_audit.py`, Teil 2)

**Files:**
- Modify: `tools/hook_audit.py`
- Test: `tests/test_hook_audit.py` (anhaengen)

**Interfaces:**
- Produces: `enrich(joined: list[dict]) -> list[dict]` (fuegt `er`, `comment_ratio`, `reach_index`, `score` hinzu; `None` wo nicht rechenbar); `aggregate_by(rows, key: str, metric: str) -> list[dict]` (Zellen `{"value", "n", "median"}` absteigend nach Median, nur Zeilen mit Metrik); `gate_open(cells, min_n=5, min_cells=2) -> bool`; `steering_from(rows, today: date) -> dict` (`{"stop", "do_more", "as_of", "n"}`, leer bei geschlossenem Gate oder ohne Impressions); Konstanten `MIN_POSTS_PER_CELL = 5`, `MIN_CELLS = 2`, `STOP_FACTOR = 0.6`, `DO_MORE_FACTOR = 1.4`.

- [ ] **Step 1: Failing Tests anhaengen**

```python
from datetime import date


def _j(hook, family, likes, comments, shares, impressions, fmt="Opinion"):
    return {"hook": hook, "family": family, "likes": likes, "comments": comments,
            "shares": shares, "impressions": impressions, "export_engagements": None,
            "dims": {"Format": fmt, "Persona": "founder-gf"}, "weekday": "Di"}


def test_enrich_computes_rates_and_handles_gaps():
    rows = ha.enrich([_j("warning", "These", 10, 2, 1, 1000),
                      _j("cold_open", "Szene", 0, 0, 0, None),
                      _j("cold_open", "Szene", 0, 4, 0, 500)])
    assert rows[0]["er"] == 0.013 and rows[0]["comment_ratio"] == 0.2 and rows[0]["score"] == 17
    assert rows[1]["er"] is None and rows[1]["reach_index"] is None
    assert rows[2]["comment_ratio"] is None                      # Likes 0
    assert rows[0]["reach_index"] == round(1000 / 750, 2)         # Median der Impressions 750


def test_aggregate_by_uses_median_and_skips_missing_metric():
    rows = ha.enrich([_j("warning", "These", 10, 0, 0, 1000), _j("warning", "These", 30, 0, 0, 1000),
                      _j("cold_open", "Szene", 5, 0, 0, None)])
    cells = ha.aggregate_by(rows, "family", "er")
    assert [(c["value"], c["n"]) for c in cells] == [("These", 2)]
    assert cells[0]["median"] == 0.02


def test_steering_needs_open_gate_and_thresholds():
    these = [_j("warning", "These", 2, 0, 0, 1000) for _ in range(5)]      # ER 0.002
    szene = [_j("cold_open", "Szene", 40, 0, 0, 1000) for _ in range(5)]  # ER 0.04
    frage = [_j("comparison", "Frage", 10, 0, 0, 1000) for _ in range(5)] # ER 0.01
    out = ha.steering_from(ha.enrich(these + szene + frage), date(2026, 10, 5))
    assert out["stop"] == ["These"] and out["do_more"] == ["Szene"]
    assert out["as_of"] == "2026-10-05" and out["n"] == 15
    # Gate zu: vier Posts je Familie
    assert ha.steering_from(ha.enrich(these[:4] + szene[:4]), date(2026, 10, 5)) == {}
    # Ohne Impressions keine Steuerung
    ohne = [dict(r, impressions=None) for r in these + szene]
    assert ha.steering_from(ha.enrich(ohne), date(2026, 10, 5)) == {}
```

- [ ] **Step 2: Tests laufen lassen, erwartet FAIL**

Run: `python -m pytest tests/test_hook_audit.py -v -p no:cacheprovider`
Expected: 3 neue FAIL (`AttributeError: enrich`)

- [ ] **Step 3: Implementieren (an `tools/hook_audit.py` anhaengen)**

```python
MIN_POSTS_PER_CELL = 5
MIN_CELLS = 2
STOP_FACTOR = 0.6
DO_MORE_FACTOR = 1.4
WEIGHTS = {"likes": 1, "comments": 2, "shares": 3}


def enrich(joined: list) -> list:
    """Metriken je Post. Engagement-Rate aus Readback-Zahlen, ersatzweise aus
    den Export-Engagements; Comment-Ratio nur mit Likes; Reach-Index gegen den
    Median der Impressions dieses Berichts (kein Follower-Stand noetig)."""
    impressions = [r["impressions"] for r in joined if r.get("impressions")]
    median_impr = statistics.median(impressions) if impressions else None
    out = []
    for r in joined:
        likes, comments, shares = (int(r.get(k) or 0) for k in ("likes", "comments", "shares"))
        measured = any(r.get(k) is not None for k in ("likes", "comments", "shares"))
        engagements = (likes + comments + shares) if measured else r.get("export_engagements")
        impr = r.get("impressions")
        er = round(engagements / impr, 4) if impr and engagements is not None else None
        out.append({**r,
                    "er": er,
                    "comment_ratio": round(comments / likes, 2) if likes else None,
                    "reach_index": round(impr / median_impr, 2) if impr and median_impr else None,
                    "score": sum(int(r.get(k) or 0) * w for k, w in WEIGHTS.items()) if measured else None})
    return out


def _value(row: dict, key: str) -> str:
    if key in row:
        return row[key] or ""
    return (row.get("dims") or {}).get(key, "") or ""


def aggregate_by(rows: list, key: str, metric: str) -> list:
    """Zellen {value, n, median} je Auspraegung von key, absteigend nach
    Median; Zeilen ohne Metrik oder ohne Wert zaehlen nicht."""
    groups = {}
    for r in rows:
        v, m = _value(r, key), r.get(metric)
        if v and m is not None:
            groups.setdefault(v, []).append(m)
    cells = [{"value": v, "n": len(ms), "median": round(statistics.median(ms), 4)}
             for v, ms in groups.items()]
    cells.sort(key=lambda c: (c["median"], c["n"]), reverse=True)
    return cells


def gate_open(cells: list, min_n: int = MIN_POSTS_PER_CELL, min_cells: int = MIN_CELLS) -> bool:
    return len([c for c in cells if c["n"] >= min_n]) >= min_cells


def steering_from(rows: list, today: date) -> dict:
    """STOP/DO-MORE-Familien aus der Engagement-Rate. Leer ohne Impressions
    oder bei geschlossenem Gate. Schwellen gegen den Median aller Posts."""
    rated = [r for r in rows if r.get("er") is not None]
    cells = [c for c in aggregate_by(rated, "family", "er") if c["n"] >= MIN_POSTS_PER_CELL]
    if not rated or not gate_open(cells):
        return {}
    overall = statistics.median(r["er"] for r in rated)
    best, worst = cells[0], cells[-1]
    return {"stop": [worst["value"]] if worst["median"] < overall * STOP_FACTOR else [],
            "do_more": [best["value"]] if best["median"] > overall * DO_MORE_FACTOR else [],
            "as_of": today.isoformat(), "n": len(rated)}
```

- [ ] **Step 4: Tests laufen lassen, erwartet PASS**

Run: `python -m pytest tests/test_hook_audit.py -v -p no:cacheprovider`
Expected: 6 passed

- [ ] **Step 5: Commit**

```
feat(audit): Engagement-Rate, Comment-Ratio, Reach-Index, Gate und Steuerung

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
```

```bash
git add tools/hook_audit.py tests/test_hook_audit.py
git commit -F .tmp/commitmsg.txt
git push origin master
```

---

### Task 9: Bericht rendern (Markdown) und Notion-Seite

**Files:**
- Modify: `tools/hook_audit.py` (`build_report`, `render_markdown`)
- Modify: `tools/notion_db.py` (`create_audit_page`, `_table_block`)
- Test: `tests/test_hook_audit_report.py`

**Interfaces:**
- Produces: `build_report(client: str, month: str, export_path: str | None, join: dict, rows: list[dict], steering: dict) -> dict` mit Schluesseln `client`, `month`, `head: list[str]`, `warnings: list[str]`, `top: list[dict]`, `bottom: list[dict]`, `tables: list[dict]` (je `{"title", "header", "rows"}`), `claims: list[str]`, `steering: dict`; `render_markdown(report: dict) -> str`; `notion_db.create_audit_page(title: str, report: dict) -> str` (Page-ID; Status "Audit").
- Dimensionen in fester Reihenfolge: `DIMENSIONS = (("Hook-Familie", "family"), ("Hook", "hook"), ("Format", "Format"), ("Persona", "Persona"), ("Wochentag", "weekday"))`.

- [ ] **Step 1: Failing Tests schreiben**

```python
"""Berichtsaufbau und Notion-Seite des Hook-Audits. Kein Netz."""
import os
import sys
from datetime import date
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import hook_audit as ha
from tools import notion_db


def _j(hook, family, likes, impressions, first="Erste Zeile", fmt="Opinion"):
    return {"hook": hook, "family": family, "likes": likes, "comments": 1, "shares": 0,
            "impressions": impressions, "export_engagements": None, "first_line": first,
            "dims": {"Format": fmt, "Persona": "founder-gf"}, "weekday": "Di"}


def _report(rows, steering=None):
    join = {"joined": rows, "unmatched_export": ["9"], "rows_without_hook": 2, "rows_without_url": 0}
    return ha.build_report("jolly", "2026-09", "top_posts_2026-09-01_2026-09-28.csv",
                           join, ha.enrich(rows), steering or {})


def test_report_order_denominators_and_claims_with_n():
    rows = [_j("warning", "These", 2, 1000), _j("cold_open", "Szene", 40, 1000)]
    rep = _report(rows)
    assert any("Export-Zeilen: 3" in h for h in rep["head"])            # 2 gejoint + 1 ohne Treffer
    assert any("ohne Notion-Treffer: 1" in h for h in rep["head"])
    assert any("ohne Hook: 2" in h for h in rep["head"])
    assert any("unter 20 Posts" in w for w in rep["warnings"])
    assert [t["title"] for t in rep["tables"]] == ["Hook-Familie", "Hook", "Format", "Persona", "Wochentag"]
    assert rep["top"][0]["hook"] == "cold_open" and rep["bottom"][0]["hook"] == "warning"
    assert rep["claims"] == ["Keine Aussage: Gate geschlossen (5 Posts je Zelle, 2 Zellen), n=2."]
    assert rep["steering"] == {}


def test_report_warns_on_wide_window_and_missing_export():
    rows = [_j("warning", "These", 2, 1000)]
    join = {"joined": rows, "unmatched_export": [], "rows_without_hook": 0, "rows_without_url": 0}
    weit = ha.build_report("jolly", "2026-08", "top_posts_2025-08-20_2026-08-19.csv", join, ha.enrich(rows), {})
    assert any("364 Tage" in w for w in weit["warnings"])
    ohne = ha.build_report("jolly", "2026-08", None, join, ha.enrich(rows), {})
    assert any("kein Export" in w for w in ohne["warnings"])


def test_markdown_has_all_blocks_in_order():
    md = ha.render_markdown(_report([_j("warning", "These", 2, 1000), _j("cold_open", "Szene", 40, 1000)]))
    pos = [md.index(h) for h in ("# Hook-Audit jolly 2026-09", "## Nenner", "## Top 5", "## Bottom 5",
                                 "## Hook-Familie", "## Wochentag", "## Was die Daten sagen", "## STOP und DO MORE")]
    assert pos == sorted(pos)
    assert "| n |" in md


def test_create_audit_page_writes_status_and_tables(monkeypatch):
    monkeypatch.setenv("NOTION_TOKEN", "tok")
    rep = _report([_j("warning", "These", 2, 1000), _j("cold_open", "Szene", 40, 1000)])
    resp = MagicMock(status_code=200, ok=True)
    resp.json.return_value = {"id": "audit1", "url": "https://notion.so/audit1"}
    resp.raise_for_status.return_value = None
    with patch("tools.notion_db._notion_request", return_value=resp) as m:
        assert notion_db.create_audit_page("Hook-Audit 2026-09", rep) == "audit1"
    body = m.call_args_list[0].kwargs["json"]
    assert body["properties"]["Status"] == {"select": {"name": "Audit"}}
    tables = [b for b in body["children"] if b["type"] == "table"]
    assert len(tables) == 5 and tables[0]["table"]["has_column_header"] is True
    assert tables[0]["table"]["table_width"] <= 5
```

- [ ] **Step 2: Tests laufen lassen, erwartet FAIL**

Run: `python -m pytest tests/test_hook_audit_report.py -v -p no:cacheprovider`
Expected: FAIL (`AttributeError: build_report`)

- [ ] **Step 3: `build_report` und `render_markdown` anhaengen**

```python
DIMENSIONS = (("Hook-Familie", "family"), ("Hook", "hook"), ("Format", "Format"),
              ("Persona", "Persona"), ("Wochentag", "weekday"))
MIN_POSTS_PER_MONTH = 20


def _fmt(v) -> str:
    return "" if v is None else f"{v:g}"


def build_report(client: str, month: str, export_path: str | None, join: dict,
                 rows: list, steering: dict) -> dict:
    """Berichtsstruktur in fester Reihenfolge (Spec 3.7). Alle Nenner oben,
    jede Aussage mit n, unter dem Gate keine Aussage."""
    n_joined = len(rows)
    head = [f"Export-Zeilen: {n_joined + len(join['unmatched_export'])}",
            f"Notion-Zeilen gejoint: {n_joined}",
            f"Export ohne Notion-Treffer: {len(join['unmatched_export'])}",
            f"Notion ohne Hook: {join['rows_without_hook']}",
            f"Notion ohne URL: {join['rows_without_url']}"]
    warnings = []
    if export_path is None:
        warnings.append("kein Export: Reichweiten-Spalten leer, keine Steuerung")
    else:
        days = window_days(export_path)
        if days is not None and days > 35:
            warnings.append(f"Export-Fenster {days} Tage: Top 50 deckt nicht alle Posts")
    if n_joined < MIN_POSTS_PER_MONTH:
        warnings.append(f"unter {MIN_POSTS_PER_MONTH} Posts im Monat (n={n_joined})")
    metric = "er" if any(r.get("er") is not None for r in rows) else "score"
    ranked = sorted((r for r in rows if r.get(metric) is not None),
                    key=lambda r: r[metric], reverse=True)
    tables = []
    for title, key in DIMENSIONS:
        cells = aggregate_by(rows, key, metric)
        cr = {c["value"]: c["median"] for c in aggregate_by(rows, key, "comment_ratio")}
        ri = {c["value"]: c["median"] for c in aggregate_by(rows, key, "reach_index")}
        tables.append({"title": title,
                       "header": [title, "n", "Median ER" if metric == "er" else "Median Score",
                                  "Comment-Ratio", "Reach-Index"],
                       "rows": [[c["value"], str(c["n"]), _fmt(c["median"]),
                                 _fmt(cr.get(c["value"])), _fmt(ri.get(c["value"]))] for c in cells]})
    claims = []
    for title, key in DIMENSIONS[:-1]:                       # Wochentag nur bei Bedarf
        cells = [c for c in aggregate_by(rows, key, metric) if c["n"] >= MIN_POSTS_PER_CELL]
        if gate_open(cells):
            claims.append(f"{title}: {cells[0]['value']} vor {cells[-1]['value']} "
                          f"(Median {_fmt(cells[0]['median'])} gegen {_fmt(cells[-1]['median'])}, "
                          f"n={sum(c['n'] for c in cells)}).")
    if not claims:
        claims.append(f"Keine Aussage: Gate geschlossen ({MIN_POSTS_PER_CELL} Posts je Zelle, "
                      f"{MIN_CELLS} Zellen), n={n_joined}.")
    return {"client": client, "month": month, "head": head, "warnings": warnings,
            "metric": metric, "top": ranked[:5], "bottom": list(reversed(ranked[-5:])),
            "tables": tables, "claims": claims, "steering": steering}


def _post_line(r: dict, metric: str) -> str:
    first = (r.get("first_line") or "").strip()[:80]
    return (f"{first} | {r.get('hook', '')} | {_value(r, 'Format')} | "
            f"{metric} {_fmt(r.get(metric))} | Likes {r.get('likes') or 0} "
            f"Kommentare {r.get('comments') or 0} Impressions {r.get('impressions') or ''}")


def render_markdown(rep: dict) -> str:
    out = [f"# Hook-Audit {rep['client']} {rep['month']}", "", "## Nenner", ""]
    out += [f"- {h}" for h in rep["head"]]
    if rep["warnings"]:
        out += ["", "Warnungen:", ""] + [f"- {w}" for w in rep["warnings"]]
    for title, key in (("Top 5", "top"), ("Bottom 5", "bottom")):
        out += ["", f"## {title}", ""] + [f"{i + 1}. {_post_line(r, rep['metric'])}"
                                          for i, r in enumerate(rep[key])]
    for t in rep["tables"]:
        out += ["", f"## {t['title']}", "", "| " + " | ".join(t["header"]) + " |",
                "| " + " | ".join("---" for _ in t["header"]) + " |"]
        out += ["| " + " | ".join(r) + " |" for r in t["rows"]]
    out += ["", "## Was die Daten sagen", ""] + [f"{i + 1}. {c}" for i, c in enumerate(rep["claims"])]
    st = rep["steering"]
    out += ["", "## STOP und DO MORE", ""]
    if st:
        out += [f"- STOP: {', '.join(st['stop']) or 'keine'}",
                f"- DO MORE: {', '.join(st['do_more']) or 'keine'}",
                f"- Stand {st['as_of']}, n={st['n']}, Schwellen {STOP_FACTOR} und {DO_MORE_FACTOR} des Gesamtmedians"]
    else:
        out += ["- Gate geschlossen, keine Steuerung."]
    return "\n".join(out) + "\n"
```

Hinweis zu `first_line`: `get_published_rows` liefert keinen Drafttext. Task 10 ergaenzt die Zeile aus der Property "LinkedIn Draft" (erste nichtleere Zeile), siehe dort. Fehlt sie, bleibt das Feld leer.

- [ ] **Step 4: `create_audit_page` in `tools/notion_db.py` (nach `_DIVIDER_BLOCK`)**

```python
def _table_block(header: list, rows: list) -> dict:
    """Notion-REST-Tabelle. "fit page width" kennt die REST-API nicht; die
    Spaltenzahl bleibt deshalb bei hoechstens fuenf."""
    def row(cells):
        return {"object": "block", "type": "table_row",
                "table_row": {"cells": [[{"type": "text", "text": {"content": str(c)[:200]}}]
                                        for c in cells]}}
    return {"object": "block", "type": "table",
            "table": {"table_width": len(header), "has_column_header": True,
                      "has_row_header": False, "children": [row(header)] + [row(r) for r in rows[:90]]}}


def create_audit_page(title: str, report: dict) -> str:
    """Hook-Audit als Seite in der Content-DB, Status "Audit". Der Make-
    Publisher filtert auf Approved und sieht sie nie. Gibt die Page-ID zurueck."""
    children = [_h2_block("Nenner"), *_para_blocks("\n".join(report["head"]))]
    if report["warnings"]:
        children += _para_blocks("Warnungen: " + "; ".join(report["warnings"]))
    for heading, key in (("Top 5", "top"), ("Bottom 5", "bottom")):
        lines = [f"{i + 1}. {(r.get('first_line') or '')[:80]} | {r.get('hook', '')} | "
                 f"{report['metric']} {r.get(report['metric'])}" for i, r in enumerate(report[key])]
        children += [_h2_block(heading), *_para_blocks("\n".join(lines) or "keine")]
    for t in report["tables"]:
        children += [_h2_block(t["title"]), _table_block(t["header"], t["rows"] or [["keine"] + [""] * 4])]
    children += [_h2_block("Was die Daten sagen"), *_para_blocks("\n".join(report["claims"]))]
    st = report["steering"]
    children += [_h2_block("STOP und DO MORE"),
                 *_para_blocks(f"STOP: {', '.join(st['stop']) or 'keine'}; DO MORE: "
                               f"{', '.join(st['do_more']) or 'keine'}; Stand {st['as_of']}, n={st['n']}"
                               if st else "Gate geschlossen, keine Steuerung.")]
    payload = {"parent": {"database_id": NOTION_DB_ID},
               "properties": {"title": {"title": [{"text": {"content": title[:200]}}]},
                              "Status": {"select": {"name": "Audit"}}},
               "children": children[:100]}
    resp = _notion_request("POST", f"{NOTION_API}/pages", headers=_headers(), json=payload)
    resp.raise_for_status()
    return resp.json()["id"]
```

- [ ] **Step 5: Tests laufen lassen, erwartet PASS**

Run: `python -m pytest tests/test_hook_audit_report.py tests/test_hook_audit.py -v -p no:cacheprovider`
Expected: alle passed

- [ ] **Step 6: Commit**

```
feat(audit): Bericht als Markdown und Notion-Seite mit Status "Audit"

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
```

```bash
git add tools/hook_audit.py tools/notion_db.py tests/test_hook_audit_report.py
git commit -F .tmp/commitmsg.txt
git push origin master
```

---

### Task 10: Runner `run_hook_audit.py`, Mail, `engine_meta`, Erinnerung

**Files:**
- Create: `run_hook_audit.py`
- Modify: `tools/hook_audit.py` (`audit_overdue`, `newest_export`, `first_lines`, `notify`)
- Modify: `tools/notion_db.py` (`get_published_rows` liefert `first_line`)
- Modify: `run_research.py:500-530` (`main`, Montags-Erinnerung)
- Test: `tests/test_run_hook_audit.py`

**Interfaces:**
- Produces: `hook_audit.newest_export(folder: str) -> str | None`; `hook_audit.audit_overdue(last_iso: str, now: datetime, max_days: int = 35) -> bool`; `hook_audit.notify(webhook: str, payload: dict) -> None` (stiller Skip ohne URL); `hook_audit.run_audit(cfg, export_path: str | None, today: date, write_notion: bool, send_mail: bool) -> dict` (gibt den Bericht zurueck, Nebenwirkungen: Markdown-Datei, Notion-Seite, Mail, `engine_meta`-Eintraege); `run_research.remind_hook_audit(cfg, now)`.
- `get_published_rows()[i]["first_line"]`: erste nichtleere Zeile der Property "LinkedIn Draft" (rich_text, `plain_text` zusammengesetzt), sonst "".

- [ ] **Step 1: Failing Tests schreiben**

```python
"""Runner-Logik des Hook-Audits: Export finden, Faelligkeit, Nebenwirkungen.
Alles gemockt, kein Netz, keine Datei ausserhalb tmp_path."""
import os
import sys
from datetime import date, datetime, timezone
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import hook_audit as ha


def test_newest_export_picks_the_latest_end_date(tmp_path):
    for name in ("top_posts_2026-07-01_2026-07-28.csv", "top_posts_2026-08-01_2026-08-28.csv", "notizen.txt"):
        (tmp_path / name).write_text("x", encoding="utf-8")
    assert ha.newest_export(str(tmp_path)).endswith("2026-08-28.csv")
    assert ha.newest_export(str(tmp_path / "leer")) is None


def test_audit_overdue_after_35_days_or_never():
    now = datetime(2026, 10, 12, tzinfo=timezone.utc)
    assert ha.audit_overdue("", now)
    assert ha.audit_overdue("2026-09-01", now)
    assert not ha.audit_overdue("2026-09-20", now)


def test_notify_skips_without_webhook(monkeypatch):
    calls = []
    monkeypatch.setattr(ha.requests, "post", lambda *a, **k: calls.append(a))
    ha.notify("", {"x": 1})
    assert calls == []
    ha.notify("https://hook", {"x": 1})
    assert len(calls) == 1


def test_run_audit_writes_markdown_meta_and_steering(tmp_path, monkeypatch):
    pid = "7430000000000000111"   # 19-stellig wie echte Objekt-IDs
    rows = [{"page_id": "p", "live_url": f"https://l/x-{pid}-y", "posted_at": "2026-09-02",
             "likes": 10, "comments": 1, "shares": 0, "first_line": "Hook A",
             "dims": {"Hook": "warning", "Format": "Opinion", "Persona": "founder-gf"}}]
    export = tmp_path / "top_posts_2026-09-01_2026-09-28.csv"
    export.write_text("Post URL,Post Publish Date,Engagements,,Post URL,Post Publish Date,Impressions\n"
                      f"https://l/x-{pid}-y,9/2/2026,11,,https://l/x-{pid}-y,9/2/2026,1000\n", encoding="utf-8")
    meta = {}
    monkeypatch.setattr(ha, "get_published_rows", lambda: rows)
    monkeypatch.setattr(ha, "set_meta", lambda k, v: meta.__setitem__(k, v))
    monkeypatch.setattr(ha, "REPORT_DIR", str(tmp_path))
    cfg = SimpleNamespace(NAME="jolly")
    rep = ha.run_audit(cfg, str(export), date(2026, 10, 5), write_notion=False, send_mail=False)
    assert rep["month"] == "2026-09"
    assert (tmp_path / "hook_audit_2026-09.md").read_text(encoding="utf-8").startswith("# Hook-Audit jolly 2026-09")
    assert meta["last_hook_audit_jolly"] == "2026-10-05"
    assert "hook_steering_jolly" not in meta        # Gate zu, nichts geschrieben
```

- [ ] **Step 2: Tests laufen lassen, erwartet FAIL**

Run: `python -m pytest tests/test_run_hook_audit.py -v -p no:cacheprovider`
Expected: FAIL (`AttributeError: newest_export`)

- [ ] **Step 3: `tools/hook_audit.py` ergaenzen**

Imports oben ergaenzen:

```python
import json
import sys
from datetime import timedelta

import requests

from tools.notion_db import create_audit_page, get_published_rows
from tools.topic_pool import get_meta, set_meta

REPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Resources", "analytics")
```

Funktionen anhaengen:

```python
def newest_export(folder: str) -> str | None:
    """Export-Datei mit dem juengsten <bis>-Datum im Namen."""
    try:
        names = [n for n in os.listdir(folder) if _FILE_RE.search(n)]
    except FileNotFoundError:
        return None
    if not names:
        return None
    return os.path.join(folder, max(names, key=lambda n: _FILE_RE.search(n).group(2)))


def audit_overdue(last_iso: str, now: datetime, max_days: int = 35) -> bool:
    """Wahr, wenn der letzte Audit fehlt oder aelter als max_days ist."""
    try:
        last = date.fromisoformat((last_iso or "")[:10])
    except ValueError:
        return True
    return now.date() - last > timedelta(days=max_days)


def notify(webhook: str, payload: dict) -> None:
    """Make-Webhook; ohne URL stiller Skip, Fehler nicht kritisch."""
    if not webhook:
        return
    try:
        requests.post(webhook, json=payload, timeout=15)
    except Exception as e:
        print(f"  Audit-Mail fehlgeschlagen (nicht kritisch): {e}", file=sys.stderr)


def run_audit(cfg, export_path: str | None, today: date,
              write_notion: bool = True, send_mail: bool = True) -> dict:
    """Ein Audit-Lauf: Export lesen, Notion joinen, Bericht bauen, Markdown
    immer schreiben, Notion und Mail obendrauf, engine_meta setzen. Der Monat
    im Titel ist der Monat des <bis>-Datums der Export-Datei, ohne Export der
    Vormonat von today."""
    export = read_export(export_path) if export_path else {}
    m = _FILE_RE.search(os.path.basename(export_path)) if export_path else None
    month = m.group(2)[:7] if m else (today.replace(day=1) - timedelta(days=1)).isoformat()[:7]
    rows = get_published_rows()
    join = join_rows(export, rows) if export else {
        "joined": [dict(r, id="", impressions=None, export_engagements=None,
                        hook=(r.get("dims") or {}).get("Hook", ""),
                        family=family_of((r.get("dims") or {}).get("Hook", "")), weekday="")
                   for r in rows],
        "unmatched_export": [], "rows_without_hook": sum(1 for r in rows if not (r.get("dims") or {}).get("Hook")),
        "rows_without_url": 0}
    enriched = enrich(join["joined"])
    steering = steering_from(enriched, today) if export else {}
    report = build_report(cfg.NAME, month, export_path, join, enriched, steering)
    os.makedirs(REPORT_DIR, exist_ok=True)
    md_path = os.path.join(REPORT_DIR, f"hook_audit_{month}.md")
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(render_markdown(report))
    print(f"  Bericht: {md_path}")
    notion_url = ""
    if write_notion:
        try:
            page_id = create_audit_page(f"Hook-Audit {month}", report)
            notion_url = f"https://www.notion.so/{page_id.replace('-', '')}"
            print(f"  Notion-Seite: {notion_url}")
        except Exception as e:
            print(f"  Notion-Seite fehlgeschlagen (nicht kritisch): {e}", file=sys.stderr)
    if send_mail:
        notify(os.environ.get("MAKE_AUDIT_WEBHOOK", ""),
               {"client": cfg.NAME, "month": month, "notion_url": notion_url,
                "summary": "\n".join(report["claims"] + report["warnings"])})
    try:
        set_meta(f"last_hook_audit_{cfg.NAME}", today.isoformat())
        if steering:
            set_meta(f"hook_steering_{cfg.NAME}", json.dumps(steering))
            print(f"  Steuerung geschrieben: {steering}")
    except Exception as e:
        print(f"  engine_meta nicht schreibbar (nicht kritisch): {e}", file=sys.stderr)
    return report
```

- [ ] **Step 4: `get_published_rows` liefert `first_line`**

In `tools/notion_db.py`, im `rows.append({...})` von `get_published_rows` (Zeile ~977) den Schluessel ergaenzen:

```python
            "first_line": next((l.strip() for l in "".join(
                t.get("plain_text", "") for t in (props.get("LinkedIn Draft") or {}).get("rich_text", [])
            ).splitlines() if l.strip()), ""),
```

- [ ] **Step 5: Runner `run_hook_audit.py`**

```python
"""Hook-Audit von Hand nach dem LinkedIn-Export (Spec 2026-09-14).

    python run_hook_audit.py                       juengste Export-Datei unter Resources/analytics
    python run_hook_audit.py --export <pfad>       bestimmte Datei
    python run_hook_audit.py --no-notion --no-mail nur Markdown
    python run_hook_audit.py --clear-steering      STOP/DO-MORE-Listen leeren

Mandant ueber CLIENT (Default jolly). Ohne Export-Datei laeuft der Bericht
mit Comment-Ratio und Score, ohne Reichweite und ohne Steuerung.
"""
import argparse
import sys
from datetime import date

from dotenv import load_dotenv

load_dotenv()

from clients import load_client
from tools import hook_audit
from tools.topic_pool import set_meta


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--export", default=None)
    ap.add_argument("--no-notion", action="store_true")
    ap.add_argument("--no-mail", action="store_true")
    ap.add_argument("--clear-steering", action="store_true")
    args = ap.parse_args(argv)
    cfg = load_client()
    if args.clear_steering:
        set_meta(f"hook_steering_{cfg.NAME}", "")
        print(f"Steuerung fuer {cfg.NAME} geleert.")
        return 0
    export = args.export or hook_audit.newest_export(hook_audit.REPORT_DIR)
    if export and not hook_audit.window_days(export):
        print(f"Dateiname ohne Fenster, erwartet top_posts_<von>_<bis>.csv: {export}", file=sys.stderr)
        return 1
    print(f"Hook-Audit {cfg.NAME}, Export: {export or 'keiner'}")
    report = hook_audit.run_audit(cfg, export, date.today(),
                                  write_notion=not args.no_notion, send_mail=not args.no_mail)
    print("\n".join(report["claims"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6: Montags-Erinnerung in `run_research.py`**

Funktion auf Modulebene:

```python
def remind_hook_audit(cfg, now) -> None:
    """Montags: liegt der letzte Hook-Audit ueber 35 Tage zurueck oder fehlt,
    geht eine Erinnerung ueber MAKE_AUDIT_WEBHOOK. Kein Bericht mit halben
    Daten; der Audit selbst laeuft lokal nach dem Export (run_hook_audit.py)."""
    if now.weekday() != 0 or not getattr(cfg, "ENGAGEMENT_READBACK", None):
        return
    try:
        last = get_meta(f"last_hook_audit_{cfg.NAME}")
    except Exception as e:
        print(f"  Audit-Stand nicht lesbar (nicht kritisch): {e}", file=sys.stderr)
        return
    if hook_audit.audit_overdue(last, now):
        print(f"  Hook-Audit faellig (letzter: {last or 'nie'}), Erinnerung.")
        hook_audit.notify(os.environ.get("MAKE_AUDIT_WEBHOOK", ""),
                          {"client": cfg.NAME, "reminder": True, "last_audit": last})
```

Import ergaenzen: `from tools import hook_audit`. In `main`, nach dem Readback-Block und vor dem Donnerstags-Job:

```python
    print("\n=== Hook-Audit-Erinnerung ===")
    try:
        remind_hook_audit(_cfg, now or datetime.now(timezone.utc))
    except Exception as e:
        print(f"  Erinnerung fehlgeschlagen (nicht kritisch): {e}", file=sys.stderr)
```

- [ ] **Step 7: Tests laufen lassen, erwartet PASS**

Run: `python -m pytest tests/test_run_hook_audit.py tests/test_hook_audit.py tests/test_hook_audit_report.py tests/test_engagement_readback_wiring.py -v -p no:cacheprovider`
Expected: alle passed

- [ ] **Step 8: Trockenlauf auf der vorhandenen 12-Monats-Datei (Netz zu Notion, lesend; keine Seite, keine Mail)**

Run: `python run_hook_audit.py --export Resources/analytics/top_posts_2025-08-20_2026-08-19.csv --no-notion --no-mail`
Expected: Bericht `Resources/analytics/hook_audit_2026-08.md` mit Nenner-Block, Warnung "Export-Fenster 364 Tage", Claims mit "Gate geschlossen" oder Aussagen mit n. `engine_meta` bekommt `last_hook_audit_jolly`. Datei ansehen, Nenner gegen die Zeilenzahl der CSV (50) pruefen.

- [ ] **Step 9: Gesamtsuite und Commit**

Run: `python -m pytest -q -p no:cacheprovider`
Expected: alle passed

```
feat(audit): Runner run_hook_audit.py, Mail, engine_meta und Montags-Erinnerung

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
```

```bash
git add run_hook_audit.py tools/hook_audit.py tools/notion_db.py run_research.py tests/test_run_hook_audit.py Resources/analytics/hook_audit_2026-08.md
git commit -F .tmp/commitmsg.txt
git push origin master
```

---

### Task 11: Workflow-Doku, Spec-Nachtrag, .env.example

**Files:**
- Create: `workflows/hook_audit.md`
- Modify: `workflows/research_phase.md` (Abschnitt zur Formatwahl, Self-Improvement-Log), `docs/superpowers/specs/2026-09-14-hook-katalog-und-audit-design.md` (Nachtrag), `.env.example` (`MAKE_AUDIT_WEBHOOK=`), `tasks/todo.md`

- [ ] **Step 1: `workflows/hook_audit.md` schreiben**

```markdown
# Workflow: Hook-Audit (monatlich, lokal)

## Ziel
Wirkung je Hook-Familie, Hook, Format, Persona und Wochentag aus dem nativen LinkedIn-Export plus Readback. Bericht als Markdown, Notion-Seite (Status "Audit") und Mail. Bei offenem Gate STOP/DO-MORE-Familien in `engine_meta`, die `tools/hooks.pick_hook` liest.

## Trigger
Richard hat den LinkedIn-Export gezogen (Analytics, Content, Export, Fenster 28 Tage) und die CSV unter `Resources/analytics/top_posts_<von>_<bis>.csv` abgelegt. Railway erinnert montags per Mail, wenn der letzte Audit ueber 35 Tage zurueckliegt.

## Inputs
- Export-CSV (zweiblockig: Engagements links, Impressions rechts)
- Notion-Zeilen mit Status Posted/Posting (Hook, Format, Persona, Likes, Kommentare, Shares, Poster-URL)
- `MAKE_AUDIT_WEBHOOK` in `.env` (optional, sonst keine Mail)

## Ausfuehrung
1. `python run_hook_audit.py` (Mandant ueber `CLIENT`, Default jolly)
2. Bericht lesen: `Resources/analytics/hook_audit_<Monat>.md`, Notion-Seite "Hook-Audit <Monat>"
3. Bei Bedarf Steuerung leeren: `python run_hook_audit.py --clear-steering`

## Output
Markdown, Notion-Seite, Mail, `engine_meta["last_hook_audit_<client>"]`, bei offenem Gate `engine_meta["hook_steering_<client>"]` (Verfall 60 Tage).

## Edge Cases
- Fenster ueber 35 Tage: Warnung, Top 50 deckt nicht alles.
- Kein Export: Bericht mit Comment-Ratio und Score, keine Steuerung.
- Export-Zeilen ohne Notion-Treffer sind manuelle Posts, sie stehen im Nenner.
- Unter 20 Posts im Monat steht die Warnung oben; Gate 5 je Zelle, 2 Zellen.

## Self-Improvement Log
### 2026-09-14
- Angelegt nach Spec `docs/superpowers/specs/2026-09-14-hook-katalog-und-audit-design.md`.
```

- [ ] **Step 2: `workflows/research_phase.md` ergaenzen**

Im Abschnitt zur Formatwahl einen Absatz:

```markdown
Nach dem Format waehlt `run_research.choose_hook` die Hook-Formel (`tools/hooks`, Rotation ueber die letzten 20 Hooks aus Notion, Steuerung aus `engine_meta`). Die Formel ersetzt Zeile 1 der Formatstruktur im Prompt und landet als Select "Hook" in Notion. Seed bei neuer DB: `python scripts/add_hook_property.py`.
```

Im Self-Improvement-Log ein Eintrag `### 2026-09-14` mit drei Zeilen: Hook-Katalog eingefuehrt, Montags-Erinnerung an den Hook-Audit, Laengenband entfaellt als Dimension.

- [ ] **Step 3: Spec-Nachtrag anhaengen**

```markdown
## 9. Nachtrag 14.09.2026 (Plan)

- Dimension "Laengenband" entfaellt: keine Notion-Property, Jolly faehrt keine LENGTH_ROTATION.
- Notion-Tabellen als REST-table-Bloecke; "fit page width" kennt die REST-API nicht, deshalb hoechstens fuenf Spalten.
- Erste Zeile je Post fuer Top/Bottom kommt aus der Property "LinkedIn Draft" (get_published_rows liefert first_line).
```

- [ ] **Step 4: `.env.example` um `MAKE_AUDIT_WEBHOOK=` ergaenzen, `tasks/todo.md` um den Plan-Status**

- [ ] **Step 5: Gesamtsuite und Commit**

Run: `python -m pytest -q -p no:cacheprovider`
Expected: alle passed

```
docs(audit): Workflow hook_audit.md, research_phase.md und Spec-Nachtrag

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
```

```bash
git add workflows/hook_audit.md workflows/research_phase.md docs/superpowers/specs/2026-09-14-hook-katalog-und-audit-design.md .env.example tasks/todo.md
git commit -F .tmp/commitmsg.txt
git push origin master
```

---

## Self-Review

- Spec-Abdeckung: 3.1 Katalog (Task 1), 3.2 Rotation und Steuerung lesen (Task 2, 5), Prompt-Zeile (Task 3), 3.3 Notion inkl. Seed und System-Check (Task 4), 3.4 Textwache (Task 6), 3.5 Parser (Task 7), 3.6 Join und Metriken (Task 7, 8), 3.7 Bericht und Ablage (Task 9, 10), 3.8 Steuerung schreiben (Task 8, 10), 3.9 Runner und Erinnerung (Task 10), Abschnitt 5 Tests (je Task), Abschnitt 6 Reihenfolge (Tasks 1-5, dann 7-9, dann 10). Abweichung Laengenband dokumentiert (Task 11).
- Typen: `pick_hook(fmt, recent, steering)` in Task 2 und 5 gleich; `update_with_draft(hook=)` in Task 4 und 5; `get_published_rows` traegt `dims["Hook"]` (Task 4) und `first_line` (Task 10), beides von Task 7 und 9 konsumiert; `steering_from` liefert dasselbe JSON, das `load_steering` liest.
- Offene Bedingung ausserhalb des Codes: Richard baut das Make-Szenario fuer `MAKE_AUDIT_WEBHOOK` (Payload: `client`, `month`, `notion_url`, `summary` fuer den Bericht; `client`, `reminder`, `last_audit` fuer die Erinnerung) und legt die Option "Audit" im Status-Select an, falls Notion sie beim ersten Schreiben nicht automatisch erzeugt (Select-Optionen entstehen beim Schreiben eines neuen Werts automatisch, wenn die Integration Schreibrechte hat).
