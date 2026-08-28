# Leser-Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deutsche Beitraege der SWOT-Content-Maschinerie bestehen vor dem Schreiben nach Notion eine Leser-Pruefung (Schriftdeutsch, Kohaerenz, Fachlogik, Schablonen, Stimme) mit chirurgischer Reparatur und Verwerfen bei Restbefund; der Prompt verliert seine Selbstwidersprueche und ausgeschriebenen Verbote; der Bestand wird maschinell bereinigt.

**Architecture:** `tools/naturalness.py` liefert Leser-Prompt, Befund-Parser (mit Zitat-Verifikation gegen den Text) und deterministische Befunde. `tools/post_scorer.py` ersetzt `_naturalness_loop` (Vollneulauf, Note) durch `_reader_loop` (Leser, bis zu zwei chirurgische Reparaturen, Verwerfen) und zieht Soundbyte/Infografik aus dem Schreib-Prompt in einen eigenen Haiku-Call. `clients/swot/config.py` und `clients/swot/voices/*.md` verlieren Wortlaut-Verbote und Widersprueche. `tools/review_backfill.py` plus `run_review_backfill.py` lesen und bereinigen den Notion-Bestand.

**Tech Stack:** Python 3.12, pytest 9, `anthropic` SDK (Sonnet 4.6 fuer Leser und Reparatur, Haiku 4.5 fuer Teile), `requests` gegen die Notion-API, `unittest.mock.patch` auf `tools.post_scorer.client`.

**Spec:** `docs/superpowers/specs/2026-08-28-leser-gate-design.md` (Commit 48ad9a8)

## Global Constraints

- Repo: `c:\Users\richa\Jolly_Claude_Code\Jolly Automations\Jolly Influencer Post Recycling`, Branch `master`, Remote `origin`. Jeder Commit wird gepusht (Richard-Regel: Commit = Commit + Push).
- Laeufe gegen Notion oder Modell IMMER mit `CLIENT=swot` starten (Templates backen die TOKENS des Prozess-Mandanten beim Import).
- Tests laufen OHNE `CLIENT` (Basis 608 gruen; 4 vorbestehende Fehler nur unter `CLIENT=swot`, nicht anfassen).
- Kommentare im Code in ASCII-Umlauten (ae/oe/ue) wie im Repo; Prompts in `naturalness.py` mit echten Umlauten (wie `CRITIC_PROMPT` bisher), Prompts in `post_scorer.py` in ASCII (wie `GRAMMAR_CHECK_PROMPT`).
- Kein Em Dash, kein Halbgeviertstrich in Code, Prompts, Commits oder Docs.
- Modell-IDs: Leser und Reparatur `claude-sonnet-4-6`, Teile-Call `claude-haiku-4-5-20251001`.
- Notion: Status "Text freigegeben" und hoeher wird NIE beschrieben. Vor dem ersten Schreiben in den Bestand ein JSON-Backup aller Post-Texte.
- CTA-Wortlaut, verbindlich: `30 Minuten mit unseren Planungs- und Konsolidierungsexperten, kostenfrei: https://www.swot.de/demo-buchen/`
- Budget Richard 28.08.2026: 6-8 EUR gesamt. Jeder bezahlte Lauf steht als eigener Schritt mit Schaetzung im Plan; kein weiterer Lauf ohne Eintrag hier.
- `_TOPIC_REPLACEMENTS`-Anker in `tools/post_writer.py` bleiben unveraendert (Import-Assert).

---

### Task 1: Leser-Prompt, Befund-Parser, deterministische Befunde

**Files:**
- Modify: `tools/naturalness.py` (hinter `avoid_note`, vor `CRITIC_PROMPT`)
- Test: `tests/test_naturalness.py` (anhaengen)

**Interfaces:**
- Consumes: `tic_hits(text, voice)`, `long_sentences(text)`, `MAX_SENTENCE_WORDS` (bestehend)
- Produces:
  - `FINDING_ARTEN: tuple[str, ...]`, `MAX_FINDINGS = 6`
  - `reader_prompt(text: str, material: str = "", voice: str = "") -> str`
  - `parse_findings(raw: str, text: str | None = None) -> list[dict] | None` (dict-Keys `art`, `zitat`, `grund`, `vorschlag`)
  - `deterministic_findings(text: str, voice: str = "") -> list[dict]`
  - `findings_note(findings: list[dict]) -> str`

- [ ] **Step 1: Failing Tests schreiben**

An `tests/test_naturalness.py` anhaengen:

```python
def test_reader_prompt_carries_material_and_voice():
    p = nat.reader_prompt("Der Text.", material="Thema: Forecast\nKurzbeschreibung: Annahmen",
                          voice="So schreibt Robert: kurz.")
    assert "Der Text." in p
    assert "Thema: Forecast" in p and "Kurzbeschreibung: Annahmen" in p
    assert "So schreibt Robert" in p
    assert '"befunde"' in p
    assert "{max_findings}" not in p and "{voice_block}" not in p


def test_reader_prompt_without_voice_has_no_massstab_block():
    p = nat.reader_prompt("Der Text.")
    assert "MASSSTAB" not in p
    assert "Der Text." in p


def test_parse_findings_reads_json_and_caps_at_six():
    raw = 'Hier: {"befunde": [' + ",".join(
        f'{{"art": "schablone", "zitat": "Satz {i}.", "grund": "g", "vorschlag": "v"}}'
        for i in range(8)) + ']} danke'
    out = nat.parse_findings(raw)
    assert len(out) == nat.MAX_FINDINGS
    assert out[0] == {"art": "schablone", "zitat": "Satz 0.", "grund": "g", "vorschlag": "v"}


def test_parse_findings_none_on_garbage_and_empty_list_on_clean():
    assert nat.parse_findings("kein json") is None
    assert nat.parse_findings('{"note": 7}') is None
    assert nat.parse_findings('{"befunde": []}') == []


def test_parse_findings_drops_quotes_missing_from_text():
    text = "Stimmen sie nicht. Und das ist in Ordnung.\n\nDas Problem sitzt in den Annahmen."
    raw = ('{"befunde": ['
           '{"art": "schriftdeutsch", "zitat": "Stimmen sie nicht.", "grund": "Verb vorn", "vorschlag": "Tun sie nicht."},'
           '{"art": "fachlogik", "zitat": "Das steht nirgends im Text.", "grund": "x", "vorschlag": "y"},'
           '{"art": "kohaerenz", "zitat": "Und das ist in Ordnung. | Das Problem sitzt in den Annahmen.", "grund": "x", "vorschlag": "y"},'
           '{"art": "kohaerenz", "zitat": "Und das ist in Ordnung. | Frei erfunden.", "grund": "x", "vorschlag": "y"}'
           ']}')
    out = nat.parse_findings(raw, text)
    assert [f["art"] for f in out] == ["schriftdeutsch", "kohaerenz"]


def test_parse_findings_unknown_art_becomes_sonstiges_and_needs_quote():
    raw = '{"befunde": [{"art": "stil", "zitat": "A.", "grund": "g"}, {"art": "schablone", "zitat": "", "grund": "g"}]}'
    out = nat.parse_findings(raw)
    assert out == [{"art": "sonstiges", "zitat": "A.", "grund": "g", "vorschlag": ""}]


def test_deterministic_findings_wrap_tics_and_long_sentences():
    long = " ".join(["Wort"] * 30) + "."
    text = "Das ist kein Planungsproblem. Das ist ein Strukturproblem.\n" + long
    out = nat.deterministic_findings(text)
    arten = [f["art"] for f in out]
    assert "schablone" in arten and "satzlaenge" in arten
    schablone = next(f for f in out if f["art"] == "schablone")
    assert schablone["zitat"].startswith("kein Planungsproblem")
    assert '"' not in schablone["zitat"]


def test_findings_note_lists_each_finding_with_quote():
    note = nat.findings_note([
        {"art": "schriftdeutsch", "zitat": "Stimmen sie nicht.", "grund": "Verb vorn", "vorschlag": "Tun sie nicht."},
        {"art": "satzlaenge", "zitat": "Langer Satz", "grund": "ueber 25 Woerter", "vorschlag": ""},
    ])
    assert '[schriftdeutsch] "Stimmen sie nicht.": Verb vorn Vorschlag: Tun sie nicht.' in note
    assert '[satzlaenge] "Langer Satz": ueber 25 Woerter' in note
    assert note.count("\n") == 1
```

- [ ] **Step 2: Tests laufen lassen, Fehlschlag pruefen**

Run: `python -m pytest tests/test_naturalness.py -q`
Expected: 8 FAILED mit `AttributeError: module 'tools.naturalness' has no attribute 'reader_prompt'` (und analog), bestehende 11 Tests PASS.

- [ ] **Step 3: Implementierung in `tools/naturalness.py`**

Direkt vor der Zeile `CRITIC_PROMPT = """Du bist Lektor ...` einfuegen:

```python
# Leser statt Lektor (Richard 28.08.2026, Spec docs/superpowers/specs/
# 2026-08-28-leser-gate-design.md). Anlass: "Den 13-Wochen-Cashforecast baut
# man einmal auf und denkt, die Zahlen muessen stimmen. Stimmen sie nicht. Und
# das ist in Ordnung." Verberststellung, Opener gegen Text, rollierender
# Forecast "einmal" gebaut: keine der drei Stellen fiel dem Lektor auf, weil
# eine Note mittelt und elf Stilpunkte keinen Sinn pruefen. Der Leser stellt
# Fragen mit Zitatpflicht; jeder Befund ist eine Reparatur, keine Note.
# Der Leser darf Beispiel-Wortlaute tragen: er schreibt nichts ab. Verbots-
# listen mit Wortlaut gehoeren deshalb hierher, nie in den Schreib-Prompt.
FINDING_ARTEN = ("schriftdeutsch", "kohaerenz", "deckung", "fachlogik",
                 "schablone", "muendlich", "fremdstimme", "satzlaenge")
MAX_FINDINGS = 6

READER_PROMPT = """Du liest einen deutschen LinkedIn-Beitrag als strenger Fachlektor mit Controlling-Hintergrund. Du bewertest nicht, du findest Defekte und belegst jeden mit einem wörtlichen Zitat aus dem Text.
{voice_block}
MATERIAL, das der Beitrag einlösen soll:
{material}

Sieben Fragen. Jede Antwort ist entweder "nichts gefunden" oder ein Befund mit Zitat:
1. schriftdeutsch: Gibt es einen Satz, der als geschriebenes Deutsch nicht korrekt ist? Ein Aussagesatz mit dem Verb an erster Stelle, der weder Frage noch Befehl noch Bedingungssatz ist ("Stimmen sie nicht."); fehlendes Subjekt oder Verb; ein Fragment, das der Leser als abgebrochenen Nebensatz liest; eine Echo-Antwort aus der gesprochenen Sprache.
2. kohaerenz: Behauptet der erste Absatz etwas, das der Rest einschränkt, widerlegt oder nicht wieder aufgreift? Zitiere beide Stellen im Feld zitat, getrennt durch " | ".
3. deckung: Löst der Text ein, was das Material verspricht? Fehlt ein versprochener Teil, oder handelt der Text von etwas anderem?
4. fachlogik: Gibt es eine Aussage, die ein Controller oder Wirtschaftsprüfer als falsch oder unpräzise erkennt? Verfahren (etwa ein rollierender Forecast, der "einmal" gebaut wird), Fristen, Fachbegriffe, Zahlen.
5. schablone: Gibt es rhetorische Formeln? Antithese als Pointe ("kein A, sondern B", "Das ist kein X, das ist ein Y"), Negation-Negation-Korrektur ("Nicht A. Nicht B. Sondern C."), Pointen-Einzeiler als eigener Absatz, Sentenz ("Wer A, bezahlt B"), Dreier-Parallelismus, Absolution nach der Pointe ("Und das ist in Ordnung.").
6. muendlich: Füllwörter (halt, irgendwie, sozusagen, quasi, "Also," am Satzanfang), Gesprächsfloskeln, Verständnisfragen an den Leser als Floskel.
7. fremdstimme: Beratersprech und Lehnübersetzungen (Mehrwert schaffen, ganzheitlich, Hebel, orchestrieren, macht Sinn, am Ende des Tages, Ownership, Level), Kunstwörter (Übergabefähigkeit, Vertrauensereignis, Fortschreibungslogik), oder eine Passage, die die Person laut Maßstab so nie schreiben würde.

Antworte NUR mit JSON, ohne Kommentar:
{{"befunde": [{{"art": "<schriftdeutsch|kohaerenz|deckung|fachlogik|schablone|muendlich|fremdstimme>", "zitat": "<wörtlich aus dem Text>", "grund": "<ein Satz>", "vorschlag": "<so schreibt es ein Mensch>"}}]}}
Leere Liste, wenn nichts gefunden. Höchstens {max_findings} Befunde, die schwersten zuerst. Kein Befund ohne wörtliches Zitat.

TEXT:
{text}"""

_READER_VOICE_BLOCK = """
MASSSTAB für Frage 7 ist die Person, in deren Namen der Beitrag erscheint. So spricht und schreibt sie:
{voice}
"""


def reader_prompt(text: str, material: str = "", voice: str = "") -> str:
    """Leser-Prompt: Text, Material (Thema und Kurzbeschreibung oder Quell-
    Post) und das Stimmprofil als Massstab, wenn eines vorliegt."""
    voice = (voice or "").strip()
    return READER_PROMPT.format(
        text=text,
        material=(material or "").strip() or "(kein Material)",
        voice_block=_READER_VOICE_BLOCK.format(voice=voice) if voice else "",
        max_findings=MAX_FINDINGS,
    )


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def _quote_in_text(zitat: str, text: str) -> bool:
    """Jeder Zitat-Teil (bei kohaerenz durch " | " getrennt) muss woertlich im
    Text stehen, Whitespace normalisiert. Erfundene Zitate fallen raus; die
    Reparatur muss die Passage sonst nicht finden."""
    t = _norm(text)
    return all(_norm(part) in t for part in zitat.split(" | ") if _norm(part))


def parse_findings(raw: str, text: str | None = None) -> list[dict] | None:
    """Befundliste aus der Leser-Antwort. None bei unlesbarer Antwort (dann
    kein Urteil, der Text bleibt). Befunde ohne Zitat oder mit Zitat, das
    nicht im Text steht, werden verworfen. Hoechstens MAX_FINDINGS."""
    m = re.search(r"\{.*\}", raw or "", re.S)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
        items = data.get("befunde")
    except (ValueError, AttributeError):
        return None
    if not isinstance(items, list):
        return None
    out = []
    for it in items:
        if not isinstance(it, dict):
            continue
        zitat = str(it.get("zitat") or "").strip()
        if not zitat or (text is not None and not _quote_in_text(zitat, text)):
            continue
        art = str(it.get("art") or "").strip().lower()
        out.append({
            "art": art if art in FINDING_ARTEN else "sonstiges",
            "zitat": zitat[:200],
            "grund": str(it.get("grund") or "").strip()[:200],
            "vorschlag": str(it.get("vorschlag") or "").strip()[:300],
        })
    return out[:MAX_FINDINGS]


def deterministic_findings(text: str, voice: str = "") -> list[dict]:
    """Regex-Formeln und Satzlaengen als Befunde derselben Form, damit die
    Reparatur eine Liste bekommt. Die Regex-Liste waechst nicht mehr; der
    Leser ist der allgemeine Fang."""
    out = []
    for hit in tic_hits(text, voice):
        name, _, zitat = hit.partition(": ")
        out.append({"art": "schablone", "zitat": zitat.strip().strip('"'),
                    "grund": name, "vorschlag": ""})
    for s in long_sentences(text):
        out.append({"art": "satzlaenge", "zitat": s,
                    "grund": f"ueber {MAX_SENTENCE_WORDS} Woerter",
                    "vorschlag": "in zwei Saetze teilen"})
    return out


def findings_note(findings: list[dict]) -> str:
    """Befunde als Zeilen fuer den Reparatur-Prompt und das Log."""
    lines = []
    for f in findings:
        line = f"- [{f['art']}] \"{f['zitat']}\": {f['grund']}"
        if f.get("vorschlag"):
            line += f" Vorschlag: {f['vorschlag']}"
        lines.append(line)
    return "\n".join(lines)
```

- [ ] **Step 4: Tests laufen lassen**

Run: `python -m pytest tests/test_naturalness.py -q`
Expected: 19 passed.

- [ ] **Step 5: Commit**

```bash
git add tools/naturalness.py tests/test_naturalness.py
git commit -m "Leser-Prompt mit Zitatpflicht, Befund-Parser und deterministische Befunde

Sieben Fragen statt Note 1-10: Schriftdeutsch, Kohaerenz, Deckung,
Fachlogik, Schablone, Muendlichkeit, Fremdstimme. Zitate werden gegen
den Text verifiziert, erfundene Befunde fallen raus. Regex-Formeln und
Satzlaengen laufen als Befunde derselben Form mit.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
git push origin master
```

---

### Task 2: CTA in der SWOT-Config und Bestandsleser `--report`

**Files:**
- Modify: `clients/swot/config.py` (hinter `CONTENT_PLAN_DB_ID = ...`, Zeile 784)
- Create: `tools/review_backfill.py`
- Create: `run_review_backfill.py`
- Test: `tests/test_review_backfill.py`

**Interfaces:**
- Consumes: `naturalness.reader_prompt`, `naturalness.parse_findings`, `naturalness.deterministic_findings`, `naturalness.findings_note` (Task 1); `run_plan_fill.read_plan`, `run_plan_fill._title`, `_rt`, `_sel`, `_date`; `post_writer.account_voices(cfg)`; `post_scorer.client`, `post_scorer._append_cta`
- Produces:
  - `clients/swot/config.py`: `CTA_DE: str`
  - `tools/review_backfill.py`: `strip_cta(text, cta) -> str`, `plan_rows(rows) -> list[dict]` (Keys `page_id, titel, kanal, datum, kurz, text, status`), `material_for(row) -> str`, `report_markdown(results) -> str`, `read_row(row, cfg, read_fn) -> dict` (Keys `page_id, titel, kanal, datum, laenge, befunde, verdikt`)
  - `run_review_backfill.py --report --out <dir>`: schreibt `<dir>/<YYYY-MM-DD>_bestand-report.md` und `.json`

- [ ] **Step 1: Failing Tests schreiben**

`tests/test_review_backfill.py` anlegen:

```python
"""Bestandsleser: reine Funktionen, kein Netz. Modellaufruf wird injiziert."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import review_backfill as rb

CTA = "30 Minuten mit unseren Planungs- und Konsolidierungsexperten, kostenfrei: https://www.swot.de/demo-buchen/"


def _row(titel="T", kanal="LinkedIn Robert", status="Entwurf", typ="LinkedIn-Post",
         text="Ein Text.", kurz="K", datum="2026-09-10", page_id="p1"):
    return {"id": page_id, "properties": {
        "Titel": {"title": [{"plain_text": titel}]},
        "Kanal": {"select": {"name": kanal}},
        "Status": {"select": {"name": status}},
        "Typ": {"select": {"name": typ}},
        "Post-Text": {"rich_text": [{"plain_text": text}]},
        "Kurzbeschreibung": {"rich_text": [{"plain_text": kurz}]},
        "Geplant für": {"date": {"start": datum}},
    }}


def test_strip_cta_removes_trailing_cta_only():
    assert rb.strip_cta("Body.\n\n" + CTA, CTA) == "Body."
    assert rb.strip_cta("Body.\n\n" + CTA + "\n", CTA) == "Body."
    assert rb.strip_cta("Body ohne CTA.", CTA) == "Body ohne CTA."
    assert rb.strip_cta(CTA + "\n\nBody.", CTA) == CTA + "\n\nBody."


def test_plan_rows_keeps_only_linkedin_entwurf_with_text():
    rows = [
        _row(page_id="ok"),
        _row(page_id="frei", status="Text freigegeben"),
        _row(page_id="blog", typ="Blog"),
        _row(page_id="leer", text=""),
    ]
    out = rb.plan_rows(rows)
    assert [r["page_id"] for r in out] == ["ok"]
    assert out[0] == {"page_id": "ok", "titel": "T", "kanal": "LinkedIn Robert",
                      "datum": "2026-09-10", "kurz": "K", "text": "Ein Text.",
                      "status": "Entwurf"}


def test_material_for_builds_topic_material():
    m = rb.material_for({"titel": "Forecast", "kurz": "Annahmen pruefen"})
    assert m == "Thema: Forecast\nKurzbeschreibung: Annahmen pruefen"


def test_read_row_strips_cta_and_merges_findings():
    row = {"page_id": "p1", "titel": "T", "kanal": "LinkedIn Robert", "datum": "2026-09-10",
           "kurz": "K", "text": "Das ist kein Planungsproblem. Das ist ein Strukturproblem.\n\n" + CTA,
           "status": "Entwurf"}
    seen = {}

    def fake_read(text, material, voice):
        seen["text"] = text
        seen["material"] = material
        seen["voice"] = voice
        return [{"art": "schriftdeutsch", "zitat": "Das ist ein Strukturproblem.",
                 "grund": "g", "vorschlag": "v"}]

    cfg = type("Cfg", (), {"CTA_DE": CTA,
                           "ACCOUNT_VOICES": {"LinkedIn Robert": "Robert Werner Stimme"}})()
    out = rb.read_row(row, cfg, fake_read)
    assert CTA not in seen["text"]
    assert seen["material"].startswith("Thema: T")
    assert seen["voice"] == "Robert Werner Stimme"
    assert out["laenge"] == len(row["text"]) - len(CTA) - 2
    assert [f["art"] for f in out["befunde"]] == ["schriftdeutsch", "schablone"]
    assert out["verdikt"] == "befund"


def test_read_row_verdict_without_findings_and_without_judgement():
    row = {"page_id": "p1", "titel": "T", "kanal": "LinkedIn Robert", "datum": "d",
           "kurz": "K", "text": "Sauberer Text.", "status": "Entwurf"}
    cfg = type("Cfg", (), {"CTA_DE": CTA, "ACCOUNT_VOICES": {"LinkedIn Robert": "x"}})()
    assert rb.read_row(row, cfg, lambda t, m, v: [])["verdikt"] == "sauber"
    assert rb.read_row(row, cfg, lambda t, m, v: None)["verdikt"] == "kein_urteil"


def test_report_markdown_has_one_row_per_post_and_totals():
    results = [
        {"page_id": "p1", "titel": "A", "kanal": "LinkedIn Robert", "datum": "2026-09-10",
         "laenge": 1200, "verdikt": "befund",
         "befunde": [{"art": "schriftdeutsch", "zitat": "Stimmen sie nicht.", "grund": "Verb vorn", "vorschlag": "Tun sie nicht."}]},
        {"page_id": "p2", "titel": "B", "kanal": "LinkedIn Christian", "datum": "2026-09-11",
         "laenge": 900, "verdikt": "sauber", "befunde": []},
    ]
    md = rb.report_markdown(results)
    assert "| 2026-09-10 | LinkedIn Robert | A | 1200 | 1 |" in md
    assert "| 2026-09-11 | LinkedIn Christian | B | 900 | 0 |" in md
    assert "[schriftdeutsch] \"Stimmen sie nicht.\": Verb vorn Vorschlag: Tun sie nicht." in md
    assert "Beitraege: 2, mit Befund: 1, sauber: 1, kein Urteil: 0, Befunde gesamt: 1" in md
```

- [ ] **Step 2: Tests laufen lassen, Fehlschlag pruefen**

Run: `python -m pytest tests/test_review_backfill.py -q`
Expected: `ModuleNotFoundError: No module named 'tools.review_backfill'`.

- [ ] **Step 3: `CTA_DE` in `clients/swot/config.py`**

Hinter der Zeile `CONTENT_PLAN_DB_ID = "4e7b33b3-e1a3-4e3d-8024-011731d3b373"` einfuegen:

```python
# Buchungs-CTA unter jedem LinkedIn-Beitrag (Richard 28.08.2026, Wortlaut
# verbindlich). Bis dahin stand der Link nur per Notion-Handlauf auf den 51
# Bestandsposts; die Pipeline haengte nichts an. post_scorer.blanket_cta
# liest dieses Attribut, Magnet und Offer bleiben aussen vor (fuer SWOT
# ohnehin gesperrt). Blog und Kommentare bekommen keinen Link.
CTA_DE = ("30 Minuten mit unseren Planungs- und Konsolidierungsexperten, "
          "kostenfrei: https://www.swot.de/demo-buchen/")
```

- [ ] **Step 4: `tools/review_backfill.py` anlegen**

```python
"""Bestandsleser und Bestandsbereinigung fuer den SWOT-Redaktionsplan.

Anlass (Richard 28.08.2026): 51 LinkedIn-Beitraege stehen als Entwurf im
Plan, geschrieben mit Prompt-Staenden vom 20. bis 27.08. Richard liest keine
Beitraege ("dafuer werde ich nicht bezahlt"). Der Bestand wird deshalb
maschinell gelesen (Task 2, --report) und bereinigt (Task 6, --write):
Leser plus Reparatur je Zeile, Restbefund leert den Text, der Normal-Lauf
fuellt nach. Spec: docs/superpowers/specs/2026-08-28-leser-gate-design.md.

Reine Funktionen hier, Netz und Modell im Runner run_review_backfill.py.
Der Modellaufruf wird als Funktion injiziert, damit Tests ohne Netz laufen.
"""
from tools import naturalness


def strip_cta(text: str, cta: str) -> str:
    """CTA-Zeile am Textende entfernen. Der Leser sieht sie nie; die
    Reparatur haengt sie hinterher wieder an."""
    t = (text or "").rstrip()
    if cta and t.endswith(cta):
        t = t[: -len(cta)].rstrip()
    return t


def plan_rows(rows: list[dict]) -> list[dict]:
    """Zeilen des Plans, die der Bestandslauf anfasst: Typ LinkedIn-Post,
    Status Entwurf, Post-Text vorhanden. Freigegebene Zeilen bleiben immer
    aussen vor (Zusage an den Kunden)."""
    from run_plan_fill import _date, _rt, _sel, _title
    out = []
    for r in rows:
        p = r["properties"]
        text = _rt(p, "Post-Text")
        if _sel(p, "Typ") != "LinkedIn-Post" or _sel(p, "Status") != "Entwurf" or not text:
            continue
        out.append({
            "page_id": r["id"], "titel": _title(p), "kanal": _sel(p, "Kanal"),
            "datum": _date(p), "kurz": _rt(p, "Kurzbeschreibung"),
            "text": text, "status": _sel(p, "Status"),
        })
    return out


def material_for(row: dict) -> str:
    return f"Thema: {row['titel']}\nKurzbeschreibung: {row['kurz']}"


def read_row(row: dict, cfg, read_fn) -> dict:
    """Leser ueber eine Zeile. read_fn(text, material, voice) liefert die
    Befundliste des Modells oder None (kein Urteil). Deterministische
    Befunde kommen immer dazu."""
    text = strip_cta(row["text"], getattr(cfg, "CTA_DE", ""))
    voice = getattr(cfg, "ACCOUNT_VOICES", {}).get(row["kanal"], "")
    llm = read_fn(text, material_for(row), voice)
    det = naturalness.deterministic_findings(text, voice)
    befunde = (llm or []) + det
    if llm is None and not det:
        verdikt = "kein_urteil"
    else:
        verdikt = "befund" if befunde else "sauber"
    return {"page_id": row["page_id"], "titel": row["titel"], "kanal": row["kanal"],
            "datum": row["datum"], "laenge": len(text), "befunde": befunde,
            "verdikt": verdikt}


def report_markdown(results: list[dict]) -> str:
    """Bericht: eine Tabellenzeile je Beitrag, darunter die Befunde im
    Wortlaut, oben die Summen."""
    mit = sum(1 for r in results if r["verdikt"] == "befund")
    sauber = sum(1 for r in results if r["verdikt"] == "sauber")
    ohne = sum(1 for r in results if r["verdikt"] == "kein_urteil")
    gesamt = sum(len(r["befunde"]) for r in results)
    lines = [
        "# Bestandsleser SWOT-Redaktionsplan",
        "",
        f"Beitraege: {len(results)}, mit Befund: {mit}, sauber: {sauber}, "
        f"kein Urteil: {ohne}, Befunde gesamt: {gesamt}",
        "",
        "| Termin | Kanal | Titel | Zeichen ohne CTA | Befunde |",
        "|---|---|---|---|---|",
    ]
    for r in sorted(results, key=lambda x: (x["datum"], x["kanal"])):
        lines.append(f"| {r['datum']} | {r['kanal']} | {r['titel']} | {r['laenge']} | {len(r['befunde'])} |")
    lines.append("")
    for r in sorted(results, key=lambda x: (x["datum"], x["kanal"])):
        if not r["befunde"]:
            continue
        lines.append(f"## {r['datum']} {r['kanal']}: {r['titel']}")
        lines.append("")
        lines.append(naturalness.findings_note(r["befunde"]))
        lines.append("")
    return "\n".join(lines)
```

- [ ] **Step 5: `run_review_backfill.py` anlegen (nur `--report`; `--write` kommt in Task 6)**

```python
"""Bestand des SWOT-Redaktionsplans lesen und bereinigen.

    CLIENT=swot python run_review_backfill.py --report --out <Ordner>

--report liest jede Entwurf-Zeile (Typ LinkedIn-Post, Text vorhanden) mit dem
Leser aus tools/naturalness, schreibt nichts nach Notion und legt Bericht
(.md) und Rohdaten (.json) im Ausgabeordner ab. Kosten: ein Sonnet-Call je
Zeile, bei 50 Zeilen rund 1 EUR.

Siehe tools/review_backfill.py fuer die Regeln und die Spec.
"""
import argparse
import datetime as dt
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from clients import load_client
from run_plan_fill import read_plan
from tools import naturalness, review_backfill as rb
from tools.post_scorer import client


def read_with_model(text: str, material: str, voice: str):
    try:
        resp = client.messages.create(
            model="claude-sonnet-4-6", max_tokens=1024,
            messages=[{"role": "user", "content": naturalness.reader_prompt(text, material, voice)}],
        )
        return naturalness.parse_findings(resp.content[0].text, text)
    except Exception as e:
        print(f"  Leser fehlgeschlagen: {e}", flush=True)
        return None


def report(out_dir: str, cfg) -> dict:
    rows = rb.plan_rows(read_plan(cfg.CONTENT_PLAN_DB_ID))
    print(f"Entwurf-Zeilen mit Text: {len(rows)}", flush=True)
    results = []
    for i, row in enumerate(rows, 1):
        r = rb.read_row(row, cfg, read_with_model)
        results.append(r)
        print(f"  {i:2d}/{len(rows)} {r['datum']} {r['kanal']:20s} {r['verdikt']:11s} "
              f"{len(r['befunde'])} {r['titel'][:50]}", flush=True)
    os.makedirs(out_dir, exist_ok=True)
    stem = os.path.join(out_dir, dt.date.today().isoformat() + "_bestand-report")
    with open(stem + ".md", "w", encoding="utf-8") as f:
        f.write(rb.report_markdown(results))
    with open(stem + ".json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
    print(f"Bericht: {stem}.md", flush=True)
    return {"zeilen": len(rows), "befund": sum(1 for r in results if r["verdikt"] == "befund")}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report", action="store_true", help="nur lesen, Bericht schreiben")
    ap.add_argument("--out", required=True, help="Ausgabeordner fuer Bericht und Rohdaten")
    args = ap.parse_args()
    if not args.report:
        ap.error("--report angeben (Schreibmodus folgt in Task 6)")
    cfg = load_client()
    r = report(args.out, cfg)
    print(f"Fertig: {r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6: Tests laufen lassen**

Run: `python -m pytest tests/test_review_backfill.py tests/test_naturalness.py -q`
Expected: 25 passed.

- [ ] **Step 7: Vollstaendige Suite ohne CLIENT**

Run: `python -m pytest -q 2>&1 | tail -3`
Expected: alle gruen (Basis 608 plus 14 neue).

- [ ] **Step 8: Commit**

```bash
git add clients/swot/config.py tools/review_backfill.py run_review_backfill.py tests/test_review_backfill.py
git commit -m "SWOT: CTA_DE in der Pipeline, Bestandsleser als --report

Der Buchungslink stand nur per Notion-Handlauf auf den Bestandsposts,
kein Pipeline-Post haette ihn getragen. Bestandsleser liest jede
Entwurf-Zeile ohne CTA mit dem Leser aus tools/naturalness und schreibt
Bericht plus Rohdaten, nichts nach Notion.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
git push origin master
```

- [ ] **Step 9: Bezahlter Lauf 1, Bestand lesen (rund 1 EUR, im Budget)**

Run:
```bash
cd "/c/Users/richa/Jolly_Claude_Code/Jolly Automations/Jolly Influencer Post Recycling" && CLIENT=swot python run_review_backfill.py --report --out "/c/Users/richa/Jolly_Claude_Code/Clients/SWOT/Content/Pruefberichte"
```
Expected: "Entwurf-Zeilen mit Text: 50" (51 minus die eine freigegebene), Bericht unter `c:\Users\richa\Jolly_Claude_Code\Clients\SWOT\Content\Pruefberichte\2026-08-28_bestand-report.md`.

- [ ] **Step 10: Kalibrierung, Fehlalarmquote messen**

Claude (nicht Richard) liest den Bericht und klassifiziert JEDEN Befund als echt oder Fehlalarm, in einer Tabelle unter dem Bericht: `| Termin | Kanal | Art | Zitat | echt/fehlalarm | warum |`. Kriterium: Fehlalarme unter 10 Prozent aller Befunde. Darueber: `READER_PROMPT` an der Frage nachschaerfen, die die Fehlalarme erzeugt (typisch: Frage 5 flaggt jede "sondern"-Konstruktion, oder Frage 7 flaggt Kulles "nicht weil, sondern weil"), Test in Task 1 anpassen, Lauf wiederholen (weitere rund 1 EUR, im Budget eingerechnet). Ergebnis (Befunde je Post, Fehlalarmquote, Verteilung nach Art) in `c:\Users\richa\Jolly_Claude_Code\tasks\todo.md` unter Review eintragen. Das ist die Basislinie fuer Task 4 Schritt 9.

---

### Task 3: Prompt-Diaet in der SWOT-Config und den Stimmprofilen

**Files:**
- Modify: `clients/swot/config.py` (`FOCUS_TOPICS_DE` Zeile 120-124, `LANGUAGE_BANS_DE` Zeile 160-168, `load_voice_profile` Zeile 819-827)
- Modify: `clients/swot/voices/werner.md` (Abschnitt "Was er nie sagen würde")
- Modify: `clients/swot/voices/kulle.md` (Abschnitt "Was er nie sagen würde")
- Test: `tests/test_swot_prompt_diet.py`

**Interfaces:**
- Consumes: nichts Neues
- Produces: `clients.swot.config.TOKENS["LANGUAGE_BANS_DE"]` ohne Beobachterposition-Erlaubnis und ohne Glaube-Zeile; `load_voice_profile(name)` mit Schriftdeutsch-Regel im Kopf; Profile ohne ausgeschriebene Formeln

- [ ] **Step 1: Failing Tests schreiben**

`tests/test_swot_prompt_diet.py` anlegen:

```python
"""Prompt-Diaet SWOT (Spec 2026-08-28): keine Wortlaut-Verbote, keine
Selbstwidersprueche im Schreib-Prompt. Laedt die Config direkt, unabhaengig
vom Prozess-Mandanten der Test-Session."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

cfg = importlib.import_module("clients.swot.config")


def test_bans_carry_no_observer_permission_and_no_glaube_line():
    bans = cfg.TOKENS["LANGUAGE_BANS_DE"]
    assert "Erlaubt ist die Beobachterposition" not in bans
    assert "sehe ich" not in bans
    assert "Glaube" not in bans
    assert "kein Interim-CFO" in bans


def test_focus_topics_avoid_the_banned_kunstwort():
    assert "Uebergabefaehigkeit" not in cfg.TOKENS["FOCUS_TOPICS_DE"]
    assert "uebernehmen" in cfg.TOKENS["FOCUS_TOPICS_DE"]


def test_voice_head_demands_written_syntax_without_filler_wordlist():
    head = cfg.load_voice_profile("werner").split("\n")[2]
    assert "Schriftdeutsch" in head and "Verb an zweiter Stelle" in head
    assert "keine Echo-Antworten" in head
    assert "(halt, irgendwie" not in head


def test_voice_profiles_carry_no_spelled_out_formulas():
    for name in ("werner", "kulle"):
        p = cfg.load_voice_profile(name)
        assert "Das ist kein Tool-Problem" not in p
        assert "Das ist kein X-Problem" not in p
        assert "Game Changer" not in p and "Game-Changer" not in p
        assert "Kennst du das?" not in p
        assert "Was er nie sagen würde" in p


def test_cta_de_is_the_binding_wording():
    assert cfg.CTA_DE == ("30 Minuten mit unseren Planungs- und Konsolidierungsexperten, "
                          "kostenfrei: https://www.swot.de/demo-buchen/")
```

- [ ] **Step 2: Tests laufen lassen, Fehlschlag pruefen**

Run: `python -m pytest tests/test_swot_prompt_diet.py -q`
Expected: 4 FAILED (bans, focus, head, profiles), 1 passed (CTA aus Task 2).

- [ ] **Step 3: `FOCUS_TOPICS_DE` entschaerfen**

In `clients/swot/config.py` ersetzen:

```python
    "FOCUS_TOPICS_DE": (
        "Belastbarkeit der Zahlen: Datenherkunft und Schnittstellen, "
        "integrierte Planung ueber GuV, Bilanz und Liquiditaet, "
        "Forecast-Genauigkeit, Uebergabefaehigkeit des Modells, datierte Fristen"
    ),
```
durch:
```python
    "FOCUS_TOPICS_DE": (
        "Belastbarkeit der Zahlen: Datenherkunft und Schnittstellen, "
        "integrierte Planung ueber GuV, Bilanz und Liquiditaet, "
        "Forecast-Genauigkeit, ob ein Dritter das Modell uebernehmen kann, "
        "datierte Fristen"
    ),
```

- [ ] **Step 4: `LANGUAGE_BANS_DE` kuerzen**

Die letzten beiden Bullets des Strings ersetzen. Alt:

```python
- Nie in der Ich- oder Wir-Form als Teilnehmer eines Bankgespraechs, Gerichtstermins, einer Gesellschafterrunde oder eines Gremiums schreiben. SWOT ist Softwarehersteller, kein Interim-CFO und kein Berater am Tisch. Erlaubt ist die Beobachterposition: "in Einfuehrungsprojekten sehe ich", "Kunden berichten", "in der Schulung zeigt sich"
- "Glaube" ist kein Fachwort: es heisst Annahme, Hypothese oder Praemisse""",
```
Neu:
```python
- Nie in der Ich- oder Wir-Form als Teilnehmer eines Bankgespraechs, Gerichtstermins, einer Gesellschafterrunde oder eines Gremiums schreiben. SWOT ist Softwarehersteller, kein Interim-CFO und kein Berater am Tisch""",
```

Den Kommentar ueber `_HERSTELLER_POSITION` (Zeile 802-808, "Die Aufzaehlung ... stand bis 27.08.2026 woertlich hier") um einen Satz ergaenzen:

```python
# Dieselbe Phrase stand bis 28.08.2026 zusaetzlich als ERLAUBNIS in
# LANGUAGE_BANS_DE ("Erlaubt ist die Beobachterposition: ..."), zwei Regeln
# im selben Prompt gegeneinander. Jetzt weg; der Leser (tools/naturalness)
# faengt die benannte Beobachterposition als Befund.
```

- [ ] **Step 5: Profilkopf in `load_voice_profile`**

Ersetzen:

```python
        return ("\n\nSTIMMPROFIL, daran misst sich jeder Satz. Es beschreibt gesprochene "
                "Sprache: Rhythmus, Bilder, Haltung und Wortwahl uebernehmen; Fuellwoerter "
                "(halt, irgendwie, also, ne) NIE; die typischen Wendungen sind Muster, "
                "hoechstens eine davon woertlich je Beitrag.\n" + f.read().strip())
```
durch:
```python
        return ("\n\nSTIMMPROFIL, daran misst sich jeder Satz. Es beschreibt gesprochene "
                "Sprache: Rhythmus, Bilder, Haltung und Wortwahl uebernehmen. Der Satzbau "
                "bleibt Schriftdeutsch: vollstaendige Saetze, Verb an zweiter Stelle, "
                "keine Echo-Antworten, kein Fragment als Aussagesatz, keine Fuellwoerter "
                "der gesprochenen Sprache. Die typischen Wendungen sind Muster, "
                "hoechstens eine davon woertlich je Beitrag.\n" + f.read().strip())
```

Und im Kommentar darueber (Zeile 810-815) ergaenzen:
```python
# Schriftdeutsch-Regel im Kopf (28.08.2026): Werners "Kurze Hauptsaetze" im
# Profil und "Kein Stakkato" im Generik-Block widersprachen sich, das Modell
# loeste es per Echo-Fragment ("Stimmen sie nicht."). Entschieden: Rhythmus
# aus dem Profil, Syntax bleibt Schrift.
```

- [ ] **Step 6: `werner.md`, Abschnitt "Was er nie sagen würde (10)" ersetzen**

Alt (Zeilen 1-6 der Liste tragen Wortlaute), neu komplett:

```markdown
## Was er nie sagen würde (10)

1. Antithesen als Formel, die ein Problem nur umbenennen: er denkt in Fällen, nicht in Gegensatzpaaren.
2. Englische Modewörter für Wirkung: seine Anglizismen sind Werkzeugnamen (Power BI, Pain).
3. Beratersprech aus Ganzheit und Synergie: nennt er "Buzzwords" (29.07.).
4. Das große Wort für Veränderung: er sagt "da ist was in Bewegung" (05.08.).
5. Wirkungszahlen in Prozent: keine Effizienzversprechen, nur Beispielzahlen.
6. Fragenstakkato an den Leser: er fragt einmal, antwortet selbst.
7. Sie-Form: er duzt, "du" auch als "man".
8. Passiv: er redet aktiv, "der Berater muss".
9. Belehrender Ton gegenüber Finanzentscheidern: er erklärt auf Augenhöhe und prüft nach ("Nachvollziehbar bis hierher?").
10. Reine Produktwerbung ohne Erklärwert: er teilt Wissen, statt es zurückzuhalten.
```

- [ ] **Step 7: `kulle.md`, Abschnitt "Was er nie sagen würde (10)" ersetzen**

```markdown
## Was er nie sagen würde (10)

1. Meinung als Bekenntnis formuliert: er sagt "Annahme", "Hypothese", "in meinen Augen".
2. Antithesen als Formel, die ein Problem nur umbenennen: er korrigiert Ursachen mit "nicht weil, sondern weil".
3. Die Interim-CFO-Pose, mit am Tisch bei Bank oder Gericht: er verkauft Software, der Berater sitzt dort.
4. Englische Pathoswörter für Umbruch: seine Anglizismen sind operativ.
5. Beratersprech aus Mehrwert und Ganzheit: er sagt "Case" und "Fit".
6. Fragen-Stakkato an den Leser: seine Fragen sind konkret und einzeln.
7. Angstkeule mit Zeitdruck: lehnt er ab (05.08.).
8. Erfolge in der Ich-Form: Erfolge gehören dem "wir".
9. Weichmacher-Ketten: gesprochen sein Taktgeber, geschrieben Watte.
10. Verständnis-Check als Schluss: gesprochen normal, geschrieben eine Floskel.
```

- [ ] **Step 8: Tests laufen lassen**

Run: `python -m pytest tests/test_swot_prompt_diet.py tests/test_post_writer_machinery.py -q`
Expected: alle gruen.

- [ ] **Step 9: Commit**

```bash
git add clients/swot/config.py clients/swot/voices/werner.md clients/swot/voices/kulle.md tests/test_swot_prompt_diet.py
git commit -m "SWOT Prompt-Diaet: Widersprueche und Wortlaut-Verbote raus

Beobachterposition stand als Verbot in _HERSTELLER_POSITION und als
Erlaubnis in LANGUAGE_BANS_DE; FOCUS_TOPICS_DE verlangte das Kunstwort,
das der Generik-Block verbietet; Werners Kurze Hauptsaetze gegen Kein
Stakkato loeste das Modell per Echo-Fragment. Profile tragen keine
ausgeschriebenen Formeln mehr, der Profilkopf entscheidet Syntax fuer
Schrift. Was verboten bleibt, faengt der Leser.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
git push origin master
```

---

### Task 4: Generik-Zeile ohne Formeln, Infografik-Split, Messung der Diaet

**Files:**
- Modify: `tools/post_scorer.py` (Zeile 141; Zeilen 175-242 `DACH_POST_PROMPT` Ende; neue `PARTS_PROMPT` und `_parts_call`; `generate_post_and_image_prompt` Zeilen 1607-1623)
- Modify: `tests/test_format_structures.py` (`_gen_with_responses`)
- Create: `scripts/measure_diet.py`
- Test: `tests/test_parts_call.py`, `tests/test_format_structures.py`

**Interfaces:**
- Consumes: `_parse_generation_response`, `_recent_types_lines`, `client`
- Produces: `PARTS_PROMPT: str`, `_parts_call(de_draft: str, recent_infographic_types=None) -> dict` (Keys `post, soundbyte, kontext, infografik`), `_EMPTY_PARTS: dict`; `DACH_POST_PROMPT` endet mit `===POST===`-Block

- [ ] **Step 1: Failing Tests schreiben**

`tests/test_parts_call.py` anlegen:

```python
"""Infografik-Split: Soundbyte, Kontext und Skelett kommen ohne EN-Draft aus
einem eigenen Haiku-Call nach dem Text, nie mehr aus dem Schreib-Prompt."""
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import post_scorer as ps

POST = {"influencer": "Test", "post_text": "Some source post", "likes": 1, "comments": 0, "shares": 0}
PARTS = "===SOUNDBYTE===\nEin Satz.\n===KONTEXT===\nCFOs\n===INFOGRAFIK===\nTYP: Waage\nMETAPHER: keine"


def test_de_prompt_has_no_parts_sections_and_ends_with_post_marker():
    de, _ = ps._format_prompts(POST, "Opinion")
    assert "TEIL 2 - SOUND BYTE" not in de and "INFOGRAFIK-TYPEN" not in de
    assert "===SOUNDBYTE===" not in de
    assert de.rstrip().endswith("===POST===\n[LinkedIn-Post-Text auf Deutsch]")


def test_parts_prompt_carries_post_types_and_recent_line():
    p = ps.PARTS_PROMPT.format(post="Der Beitrag.", recent_types_line="- Zuletzt genutzte Typen: Iceberg.")
    assert "Der Beitrag." in p and "INFOGRAFIK-TYPEN" in p and "Zuletzt genutzte Typen" in p
    assert "===POST===" not in p and "===SOUNDBYTE===" in p


def test_without_en_draft_parts_come_from_second_call():
    calls = []

    def fake_create(**kw):
        calls.append((kw["model"], kw["messages"][0]["content"]))
        resp = MagicMock()
        resp.content = [MagicMock(text=PARTS if "BEITRAG:" in kw["messages"][0]["content"]
                                  else "===POST===\nBody.")]
        return resp

    with patch("tools.post_scorer.client") as c, \
         patch.dict(ps._cfg.FEATURES, {"grammar_check": False, "en_draft": False,
                                       "naturalness_check": False}):
        c.messages.create.side_effect = fake_create
        de, en, img, skeleton, sound, kontext = ps.generate_post_and_image_prompt(POST, "Opinion")
    # startswith: blanket_cta haengt je nach Prozess-Mandant einen CTA an.
    assert de.startswith("Body.") and en == ""
    assert sound == "Ein Satz." and kontext == "CFOs" and skeleton.startswith("TYP: Waage")
    assert [m for m, _ in calls] == ["claude-sonnet-4-6", "claude-haiku-4-5-20251001"]
    assert "Body." in calls[1][1]


def test_with_en_draft_no_parts_call():
    calls = []

    def fake_create(**kw):
        calls.append(kw["model"])
        resp = MagicMock()
        resp.content = [MagicMock(text="===POST===\nBody.\n===SOUNDBYTE===\nByte.")]
        return resp

    with patch("tools.post_scorer.client") as c, \
         patch.dict(ps._cfg.FEATURES, {"grammar_check": False, "en_draft": True,
                                       "naturalness_check": False}):
        c.messages.create.side_effect = fake_create
        de, en, *_ = ps.generate_post_and_image_prompt(POST, "Opinion")
    assert calls == ["claude-sonnet-4-6", "claude-sonnet-4-6"]
    assert en.startswith("Body.")


def test_parts_call_failure_returns_empty_parts():
    with patch("tools.post_scorer.client") as c:
        c.messages.create.side_effect = RuntimeError("down")
        parts = ps._parts_call("Text")
    assert parts == {"post": "", "soundbyte": "", "kontext": "", "infografik": ""}


def test_generic_line_carries_no_spelled_out_formulas():
    assert "kein X-Problem" not in ps.DACH_POST_PROMPT
    assert "Nicht X. Nicht Y." not in ps.DACH_POST_PROMPT
    assert "Uebergabefaehigkeit" not in ps.DACH_POST_PROMPT
    assert "keine rhetorischen Schablonen" in ps.DACH_POST_PROMPT
```

- [ ] **Step 2: Tests laufen lassen, Fehlschlag pruefen**

Run: `python -m pytest tests/test_parts_call.py -q`
Expected: 6 FAILED (`PARTS_PROMPT`/`_parts_call` fehlen, DE-Prompt enthaelt TEIL 2).

- [ ] **Step 3: Generik-Zeile 141 ersetzen**

Alt:
```
- Deutsch, wie ein Fachmensch es selbst schreibt: Verben statt Substantivierungen, keine Kunstwoerter (Uebergabefaehigkeit, Vertrauensereignis, Fortschreibungslogik), keine Lehnuebersetzungen aus dem Englischen. Keine Formeln wie "Das ist kein X-Problem, das ist ein Y-Problem", "Nicht X. Nicht Y. Sondern Z.", "X ist kein Y. Es ist ein Z.", "Wer X, bezahlt Y". Keine Pointen-Einzeiler als eigener Absatz. Der Beitrag muss nicht mit einer Frage enden
```
Neu:
```
- Deutsch, wie ein Fachmensch es selbst schreibt: Verben statt Substantivierungen, keine Kunstwoerter, keine Lehnuebersetzungen aus dem Englischen. Keine rhetorischen Schablonen: keine Antithesen in Serie, keine Pointen-Einzeiler als eigener Absatz, keine Sentenzen. Der Beitrag muss nicht mit einer Frage enden
```

- [ ] **Step 4: TEIL 2 bis 4 aus `DACH_POST_PROMPT` herausschneiden**

In `DACH_POST_PROMPT` alles ab der Zeile `---` VOR `TEIL 2 - SOUND BYTE:` (Zeile 175) bis einschliesslich `TOOL-LOGOS: keine"""` (Zeile 242) entfernen und den String so beenden:

```
[[HASHTAG_LINE_DE]]

OUTPUT-FORMAT (exakt einhalten):

===POST===
[LinkedIn-Post-Text auf Deutsch]"""
```

Direkt hinter dem Ende von `DACH_POST_PROMPT` (vor dem Kommentar `# PERSONA_DE wird erst zur Generierungszeit gefuellt`) einfuegen:

```python
# Infografik-Split (28.08.2026): Soundbyte, Kontext und Skelett standen als
# TEIL 2 bis 4 im Schreib-Prompt, 3.064 von 19.756 Zeichen, und konkurrierten
# mit dem Text um Aufmerksamkeit. Jetzt ein eigener Haiku-Call nach dem
# fertigen Text (nur ohne EN-Draft; Mandanten mit EN-Draft beziehen die
# Teile weiter aus dem EN-Call). Wortlaut der Regeln unveraendert uebernommen.
PARTS_PROMPT = """Aus dem folgenden fertigen LinkedIn-Beitrag leitest du Sound Byte, Kontext und Infografik-Skelett ab. Der Beitrag selbst ist fertig und wird nicht veraendert.

BEITRAG:
{post}

---

TEIL 2 - SOUND BYTE:

Extrahiere aus dem Beitrag einen einzigen, kurzen, praegnanten Satz als Sound Byte fuer das Bild.

Regeln:
- Kein vollstaendiges Summary des Posts, kein erklaerungsbeduerftiger Satz
- Muss sofort haengen bleiben und eine Reaktion ausloesen
- Klingt wie ein starkes Zitat oder eine provokante These
- Maximal 12 Woerter
- Auf Deutsch (da der Post auf Deutsch ist)

TEIL 3 - KONTEXT (optional):

Fuer wen ist die Aussage besonders relevant? 1-2 Woerter Zielgruppe, z.B. "CEOs, RevOps-Teams" oder leer lassen.

---

TEIL 4 - INFOGRAFIK-SKELETT:

Basierend auf dem Beitrag: Empfehle den staerksten Infografik-Typ und liefere die Keywords fuer den Canva-Aufbau.

INFOGRAFIK-TYPEN (waehle den EINEN der zur Logik des Posts am besten passt):
- Vergleichstabelle: Zwei Spalten (z.B. "Was Leute denken" vs. "Was es wirklich ist")
- Funnel/Pyramide: 3-5 Ebenen mit Hierarchie (oben = Wichtigstes oder Ausgangspunkt)
- Eisberg: Sichtbare Spitze vs. verborgene Tiefe darunter
- Framework/Kreise: Konzentrische oder verschachtelte Ebenen
- Horizontaler Vergleich: Nebeneinander, gleichwertig
- Timeline/Sequenz: geordnete Schritte oder Phasen
- 2x2-Matrix: vier Quadranten aus zwei Achsen (z.B. Aufwand vs. Wirkung)
- Flywheel/Kreislauf: ein Zyklus, in dem jede Stufe die naechste speist
- Waage/Hebel: zwei Seiten gegeneinander abgewogen (Trade-off oder Ungleichgewicht)
- Vorher/Nachher-Split: ein Zustand vs. der veraenderte Zustand, nebeneinander
- Baum/Verzweigung: eine Wurzel, die sich in Aeste oder Ergebnisse teilt

Typ-Wahl-Regeln (Output ist aktuell viel zu monoton, das beheben):
- Typ an die echte Logik des Posts koppeln: Trade-off -> Waage, Prozess -> Funnel oder Timeline, zwei Denkweisen -> Vergleichstabelle, Zyklus -> Flywheel, zwei Achsen -> 2x2-Matrix.
- Eisberg ist stark ueberstrapaziert. Nur waehlen wenn es im Post wirklich um eine sichtbare Oberflaeche geht, die eine tiefere Realitaet verbirgt, und nichts anderes besser passt.
{recent_types_line}

Regeln:
- Keywords nicht Saetze (max. 3-4 Keywords pro Ebene/Spalte)
- 3-7 Elemente total, nicht mehr
- Komplementaritaet: Wenn Infografik das Problem zeigt beschreibt der Post-Text die Loesung; wenn Infografik die Struktur zeigt erklaert der Post-Text das Warum
- Keine Tool-Logos: das Bild bleibt logofrei (AI-Render verzerrt Marken). TOOL-LOGOS immer "keine"
- Visuelle Metapher nur empfehlen wenn sie den Kerngedanken wirklich verstaerkt (z.B. Bruecke fuer das Verbinden zweier Seiten, Domino-Kette fuer Kaskaden-Effekte, Hebel fuer ueberproportionale Wirkung). Nicht erzwingen.

OUTPUT-FORMAT (exakt einhalten):

===SOUNDBYTE===
[Sound Byte, ein Satz, max. 12 Woerter]

===KONTEXT===
[Zielgruppe/Kontext oder leer]

===INFOGRAFIK===
TYP: [Typ-Name]
METAPHER: [Visuelle Metapher oder "keine"]
KOMPLEMENTARITAET: [Infografik zeigt X -> Post-Text erklaert Y]
EBENEN:
[Label 1]: [Keyword 1], [Keyword 2], [Keyword 3]
[Label 2]: [Keyword 1], [Keyword 2], [Keyword 3]
[Label 3]: [Keyword 1], [Keyword 2], [Keyword 3]
TOOL-LOGOS: keine"""

_EMPTY_PARTS = {"post": "", "soundbyte": "", "kontext": "", "infografik": ""}
```

Hinweis fuer den Umsetzer: in TEIL 2 stand bisher "Kein vollstaendiges Summary des Posts — kein erklaerungsbeduerftiger Satz" mit Em Dash und in TEIL 4 "Output ist aktuell viel zu monoton — das beheben"; beide oben bewusst mit Komma. Die Zeile `{recent_types_line}` bleibt ein Platzhalter.

- [ ] **Step 5: `_parts_call` einfuegen (hinter `_recent_types_lines`, Zeile 611)**

```python
def _parts_call(de_draft: str, recent_infographic_types=None) -> dict:
    """Soundbyte, Kontext und Infografik-Skelett aus dem fertigen DE-Text
    (Haiku). Ohne EN-Draft der einzige Lieferant dieser Teile. Fehler
    liefern leere Teile; der Text bleibt, das Bild fehlt dann."""
    de_recent, _ = _recent_types_lines(recent_infographic_types)
    try:
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=800,
            messages=[{"role": "user", "content": PARTS_PROMPT.format(
                post=de_draft, recent_types_line=de_recent)}],
        )
        return _parse_generation_response(resp.content[0].text.strip())
    except Exception as e:
        print(f"  Teile-Call fehlgeschlagen (nicht kritisch): {e}", flush=True)
        return dict(_EMPTY_PARTS)
```

- [ ] **Step 6: `generate_post_and_image_prompt` umstellen**

Alt (Zeilen 1607-1619):
```python
    if _cfg.FEATURES.get("en_draft", True):
        en_resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            messages=[{"role": "user", "content": en_prompt}],
        )
        en_parts = _parse_generation_response(en_resp.content[0].text.strip())
        en_draft = _append_cta(sanitize_generated_text(en_parts["post"]),
                               blanket_cta(post_format, "CTA_EN", persona_id))
        image_parts = en_parts
    else:
        en_draft = ""
        image_parts = de_parts
```
Neu:
```python
    if _cfg.FEATURES.get("en_draft", True):
        en_resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            messages=[{"role": "user", "content": en_prompt}],
        )
        en_parts = _parse_generation_response(en_resp.content[0].text.strip())
        en_draft = _append_cta(sanitize_generated_text(en_parts["post"]),
                               blanket_cta(post_format, "CTA_EN", persona_id))
        image_parts = en_parts
    else:
        en_draft = ""
        # Teile aus dem fertigen Text, nicht mehr aus dem Schreib-Prompt.
        image_parts = (_parts_call(de_draft, recent_infographic_types)
                       if de_draft else dict(_EMPTY_PARTS))
```

Im Docstring der Funktion den Satz "Soundbyte/Kontext/Infografik-Skelett kommen dann aus dem DE-Response (der DACH-Prompt liefert sie auf Deutsch)" ersetzen durch "Soundbyte/Kontext/Infografik-Skelett kommen dann aus einem eigenen Haiku-Call (`_parts_call`) nach dem fertigen Text".

- [ ] **Step 7: Test-Helfer `_gen_with_responses` um den Teile-Call ergaenzen**

In `tests/test_format_structures.py` die innere Funktion ersetzen:

```python
    def fake_create(**kw):
        content = kw["messages"][0]["content"]
        resp = MagicMock()
        if content.startswith("Aus dem folgenden fertigen LinkedIn-Beitrag"):
            # Teile-Call (Infografik-Split, Task 4): nicht mitzaehlen.
            resp.content = [MagicMock(text="===SOUNDBYTE===\nx\n===INFOGRAFIK===\nTYP: Waage")]
            return resp
        captured.append(content)
        resp.content = [MagicMock(text=bodies.pop(0))]
        return resp
```

- [ ] **Step 8: Tests laufen lassen**

Run: `python -m pytest tests/test_parts_call.py tests/test_format_structures.py tests/test_infographic_type_diversity.py tests/test_parse_generation.py tests/test_post_writer_machinery.py -q`
Expected: alle gruen. Faellt in `tests/test_infographic_type_diversity.py` ein Test, der die Anti-Repeat-Zeile IM DE-Prompt erwartet, dann dessen Assertion auf `ps.PARTS_PROMPT.format(post="x", recent_types_line=de)` umstellen (die Zeile lebt jetzt dort), nichts sonst aendern.

- [ ] **Step 9: Vollstaendige Suite**

Run: `python -m pytest -q 2>&1 | tail -3`
Expected: gruen.

- [ ] **Step 10: Commit**

```bash
git add tools/post_scorer.py tests/test_parts_call.py tests/test_format_structures.py tests/test_infographic_type_diversity.py
git commit -m "Generik-Zeile ohne Formel-Wortlaute, Infografik-Split in eigenen Haiku-Call

Die vier ausgeschriebenen Formeln standen im Schreib-Prompt und kamen als
Variation zurueck. TEIL 2 bis 4 (3.064 Zeichen) verlassen den Text-Call;
ohne EN-Draft liefert _parts_call sie aus dem fertigen Text.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
git push origin master
```

- [ ] **Step 11: Messskript `scripts/measure_diet.py` anlegen**

```python
"""Diaet messen: N Plan-Zeilen trocken texten (ohne Leser-Loop, ohne Notion)
und mit dem Leser aus tools/naturalness lesen. Gleiches Skript vor und nach
der Diaet, Vergleich Befunde je Post.

    CLIENT=swot python scripts/measure_diet.py --n 8 --label alt --out <Ordner>

Kosten: je Post eine Generierung, eine Grammatik, ein Leser, rund 0,10 EUR.
"""
import argparse
import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from unittest.mock import patch

from clients import load_client
from run_plan_fill import read_plan
from run_review_backfill import read_with_model
from tools import post_scorer as ps, post_writer, review_backfill as rb


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--label", required=True, help="alt oder neu")
    ap.add_argument("--out", required=True)
    ap.add_argument("--loop", action="store_true",
                    help="Leser-Loop der Pipeline einschalten (Task 5, Trockenlauf mit Log)")
    args = ap.parse_args()
    cfg = load_client()
    rows = rb.plan_rows(read_plan(cfg.CONTENT_PLAN_DB_ID))
    # Abwechselnd beide Konten, feste Reihenfolge nach Termin: gleiche Zeilen
    # in beiden Laeufen.
    rows = sorted(rows, key=lambda r: (r["datum"], r["kanal"]))[: args.n]
    from tools.monthly_plan import axis_id
    from run_plan_fill import _sel
    plan = {r["id"]: r for r in read_plan(cfg.CONTENT_PLAN_DB_ID)}
    prompt_len = len(post_writer.build_prompt("T", "K", rows[0]["kanal"],
                                              cfg.CONTENT_PERSONAS[0]["id"], cfg=cfg,
                                              band="standard", datum="2026-09-10"))
    print(f"DE-Prompt {args.label}: {prompt_len} Zeichen", flush=True)
    results = []
    with patch.dict(ps._cfg.FEATURES, {"naturalness_check": args.loop}):
        for i, row in enumerate(rows, 1):
            achse = axis_id(_sel(plan[row["page_id"]]["properties"], "Achse"))
            r = post_writer.write_post(row["titel"], row["kurz"], row["kanal"], achse,
                                       cfg=cfg, band="standard", datum=row["datum"])
            text = r["text"]
            befunde = rb.read_row({**row, "text": text}, cfg, read_with_model)["befunde"] if text else []
            results.append({"titel": row["titel"], "kanal": row["kanal"], "text": text,
                            "befunde": befunde})
            print(f"  {i}/{len(rows)} {row['kanal']:20s} Befunde {len(befunde)} "
                  f"{'(kein Text)' if not text else ''} {row['titel'][:45]}", flush=True)
    os.makedirs(args.out, exist_ok=True)
    path = os.path.join(args.out, f"{dt.date.today().isoformat()}_diaet-{args.label}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"prompt_len": prompt_len, "posts": results}, f, ensure_ascii=False, indent=1)
    gesamt = sum(len(r["befunde"]) for r in results)
    mit_text = sum(1 for r in results if r["text"])
    print(f"{args.label}: {mit_text} Texte, {gesamt} Befunde, "
          f"{gesamt / max(mit_text, 1):.2f} je Post, Prompt {prompt_len} Zeichen -> {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 12: Messung ALT (bezahlter Lauf 2a, rund 1 EUR)**

Der Alt-Stand ist Commit vor Task 3. Messung im Worktree:

```bash
cd "/c/Users/richa/Jolly_Claude_Code/Jolly Automations/Jolly Influencer Post Recycling"
ALT=$(git log --format=%H -1 --grep="Bestandsleser als --report")
git worktree add ../recycling-alt "$ALT"
cp scripts/measure_diet.py ../recycling-alt/scripts/measure_diet.py
cp .env ../recycling-alt/.env
cd ../recycling-alt && CLIENT=swot python scripts/measure_diet.py --n 8 --label alt --out "/c/Users/richa/Jolly_Claude_Code/Clients/SWOT/Content/Pruefberichte"
cd "/c/Users/richa/Jolly_Claude_Code/Jolly Automations/Jolly Influencer Post Recycling" && git worktree remove ../recycling-alt --force
```
Expected: "DE-Prompt alt: 19xxx Zeichen", 8 Texte, Befunde je Post als Zahl.

- [ ] **Step 13: Messung NEU (bezahlter Lauf 2b, rund 1 EUR)**

```bash
CLIENT=swot python scripts/measure_diet.py --n 8 --label neu --out "/c/Users/richa/Jolly_Claude_Code/Clients/SWOT/Content/Pruefberichte"
```
Expected: Prompt-Laenge deutlich unter alt (Erwartung 12.000 bis 14.000 Zeichen), Befunde je Post unter dem Alt-Wert. Beide Zahlen in `tasks/todo.md` unter Review. Liegt neu NICHT unter alt: Befunde nach Art auszaehlen, die haeufigste Art gegen den Prompt lesen und nachschaerfen (Task 3 oder Zeile 141), erneut messen (weitere rund 1 EUR). Nicht mit Task 5 weitermachen, bevor neu unter alt liegt.

- [ ] **Step 14: Commit des Messskripts**

```bash
git add scripts/measure_diet.py
git commit -m "Messskript fuer die Prompt-Diaet: N Zeilen trocken texten und lesen

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
git push origin master
```

---

### Task 5: Leser und chirurgische Reparatur in der Pipeline

**Files:**
- Modify: `tools/post_scorer.py` (`_naturalness_verdict` und `_naturalness_loop` Zeilen 1455-1497 ersetzen; Aufruf Zeilen 1600-1603)
- Modify: `tools/naturalness.py` (`NATURALNESS_MIN`, `CRITIC_PROMPT`, `_VOICE_BLOCK`, `_VOICE_ITEM`, `critic_prompt`, `parse_verdict`, `rewrite_note` entfernen; Modul-Docstring)
- Modify: `tests/test_naturalness.py` (drei Alt-Tests entfernen)
- Modify: `clients/swot/config.py` (Kommentar zu `naturalness_check`, Zeile 537-540; Kommentar Zeile 814)
- Test: `tests/test_reader_loop.py`

**Interfaces:**
- Consumes: `naturalness.reader_prompt`, `parse_findings`, `deterministic_findings`, `findings_note`; `text_gate.hard_violations`; `sanitize_generated_text`
- Produces: `MAX_FIX_ROUNDS = 2`, `FIX_PROMPT: str`, `_read_findings(text, voice, material) -> list[dict] | None`, `_all_findings(text, voice, material) -> list[dict] | None`, `_fix_passages(text, findings, cap) -> str`, `_reader_loop(de_draft, cap, voice="", material="") -> str` (Task 6 ruft `_reader_loop` fuer den Bestand)

- [ ] **Step 1: Failing Tests schreiben**

`tests/test_reader_loop.py` anlegen:

```python
"""Leser-Loop (Spec 2026-08-28): Leser, bis zu zwei chirurgische Reparaturen,
Verwerfen bei Restbefund. Modell gemockt, Teile-Call herausgefiltert."""
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import post_scorer as ps

POST = {"influencer": "Test", "post_text": "Thema: Forecast\nKurzbeschreibung: Annahmen",
        "likes": 0, "comments": 0, "shares": 0}
BAD = "Den Forecast baut man auf und denkt, die Zahlen stimmen. Stimmen sie nicht.\n\nDas Problem sitzt in den Annahmen."
GOOD = "Den Forecast baut man auf und denkt, die Zahlen stimmen. Tun sie nicht.\n\nDas Problem sitzt in den Annahmen."
FIND = '{"befunde": [{"art": "schriftdeutsch", "zitat": "Stimmen sie nicht.", "grund": "Verb vorn", "vorschlag": "Tun sie nicht."}]}'
CLEAN = '{"befunde": []}'


def _run(bodies):
    """bodies: Modellantworten in Aufrufreihenfolge (ohne Teile-Call).
    Gibt (de_draft, gesendete Prompts) zurueck."""
    captured, bodies = [], list(bodies)

    def fake_create(**kw):
        content = kw["messages"][0]["content"]
        resp = MagicMock()
        if content.startswith("Aus dem folgenden fertigen LinkedIn-Beitrag"):
            resp.content = [MagicMock(text="===SOUNDBYTE===\nx")]
            return resp
        captured.append(content)
        resp.content = [MagicMock(text=bodies.pop(0))]
        return resp

    with patch("tools.post_scorer.client") as c, \
         patch.dict(ps._cfg.FEATURES, {"grammar_check": False, "en_draft": False,
                                       "naturalness_check": True}):
        c.messages.create.side_effect = fake_create
        de, *_ = ps.generate_post_and_image_prompt(POST, "Opinion")
    return de, captured


def test_clean_text_needs_generation_and_one_read_only():
    de, sent = _run(["===POST===\n" + GOOD, CLEAN])
    assert de.startswith(GOOD)   # startswith: blanket_cta haengt je Mandant einen CTA an
    assert len(sent) == 2
    assert "Du liest einen deutschen LinkedIn-Beitrag" in sent[1]
    assert "Thema: Forecast" in sent[1]


def test_one_finding_is_fixed_surgically_then_accepted():
    de, sent = _run(["===POST===\n" + BAD, FIND, GOOD, CLEAN])
    assert de.startswith(GOOD)
    assert len(sent) == 4
    assert sent[2].startswith("Du korrigierst einen deutschen LinkedIn-Beitrag chirurgisch")
    assert '[schriftdeutsch] "Stimmen sie nicht.": Verb vorn Vorschlag: Tun sie nicht.' in sent[2]
    assert BAD in sent[2]


def test_fix_rejected_by_length_guard_discards_text():
    de, sent = _run(["===POST===\n" + BAD, FIND, "Zu kurz."])
    assert de == ""
    assert len(sent) == 3


def test_residue_after_two_rounds_discards_text():
    de, sent = _run(["===POST===\n" + BAD, FIND, BAD, FIND, BAD, FIND])
    assert de == ""
    assert len(sent) == 6


def test_unreadable_reader_answer_keeps_text():
    de, sent = _run(["===POST===\n" + GOOD, "kein json"])
    assert de.startswith(GOOD)


def test_deterministic_finding_triggers_fix_without_llm_finding():
    tic = "Das ist kein Planungsproblem. Das ist ein Strukturproblem.\n\nDer Rest ist sauber."
    fixed = "Das Planungsverfahren ist nicht das Problem, die Struktur ist es.\n\nDer Rest ist sauber."
    de, sent = _run(["===POST===\n" + tic, CLEAN, fixed, CLEAN])
    assert de.startswith(fixed)
    assert "[schablone]" in sent[2]


def test_fix_output_failing_textwache_is_rejected():
    caps = "DAS IST DIE ANTWORT DARAUF.\n\nDen Forecast baut man auf und denkt, die Zahlen stimmen. Tun sie nicht."
    de, sent = _run(["===POST===\n" + BAD, FIND, caps])
    assert de == ""
```

- [ ] **Step 2: Tests laufen lassen, Fehlschlag pruefen**

Run: `python -m pytest tests/test_reader_loop.py -q`
Expected: FAILED; der alte Loop schickt `CRITIC_PROMPT` ("Du bist Lektor") statt des Lesers, `IndexError: pop from empty list` bei mehreren Tests.

- [ ] **Step 3: `_naturalness_verdict` und `_naturalness_loop` ersetzen**

Zeilen 1455-1497 in `tools/post_scorer.py` komplett ersetzen durch:

```python
# Leser-Loop (Richard 28.08.2026, Spec docs/superpowers/specs/
# 2026-08-28-leser-gate-design.md). Ersetzt Lektor-Note plus Vollneulauf:
# der Leser liefert Befunde mit Zitat, die Reparatur aendert nur die
# zitierten Passagen, nach MAX_FIX_ROUNDS Reparaturen mit Restbefund wird
# der Text verworfen (fail-closed, wie CAPS und Ueberlaenge). Kein Lese-
# Schritt bei Jolly: was hier durchkommt, sieht der Kunde.
MAX_FIX_ROUNDS = 2

FIX_PROMPT = """Du korrigierst einen deutschen LinkedIn-Beitrag chirurgisch. Ein Lektor hat Befunde mit woertlichen Zitaten geliefert. Aendere NUR die zitierten Passagen, jede andere Zeile bleibt zeichengenau erhalten.

HARTE REGELN:
- Nur die zitierten Passagen umschreiben, so knapp wie moeglich. Kein neuer Absatz, keine Umstellung, keine Kuerzung anderswo.
- Fakten, Zahlen, Fristen und Namen bleiben; korrigiere Fachlogik nur so, wie der Befund es begruendet.
- Schriftdeutsch: vollstaendige Saetze, Verb an zweiter Stelle, keine Echo-Antworten, keine Pointen-Formeln.
- Bei "kohaerenz": passe den ersten Absatz an den Rest an, nie umgekehrt.
- Kein Kommentar, kein Markdown, keine Erklaerung: antworte NUR mit dem vollstaendigen Text.

BEFUNDE:
{befunde}

TEXT:
{text}"""


def _read_findings(text: str, voice: str = "", material: str = "") -> list[dict] | None:
    """Befunde des Lesers (Sonnet). None bei Fehler oder unlesbarer Antwort.
    Structured Output (Sonde 28.08.2026): ohne Schema schrieb das Modell erst
    eine Prosa-Analyse und lief bei 1024 Tokens ins Limit."""
    try:
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            output_config={"format": {"type": "json_schema",
                                      "schema": naturalness.READER_SCHEMA}},
            messages=[{"role": "user", "content": naturalness.reader_prompt(
                text, material=material, voice=voice)}],
        )
        return naturalness.parse_findings(resp.content[0].text, text)
    except Exception as e:
        print(f"  Leser fehlgeschlagen (nicht kritisch): {e}", flush=True)
        return None


def _all_findings(text: str, voice: str = "", material: str = "") -> list[dict] | None:
    """Leser plus deterministische Befunde. None nur, wenn der Leser kein
    Urteil liefert UND nichts Deterministisches anliegt."""
    llm = _read_findings(text, voice, material)
    det = naturalness.deterministic_findings(text, voice)
    if llm is None and not det:
        return None
    return (llm or []) + det


def _fix_passages(text: str, findings: list[dict], cap: int) -> str:
    """Ein Reparatur-Call. "" wenn die Reparatur verworfen wird: Fehler,
    Laengen-Guard (wie grammar_check) oder Textwache."""
    try:
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            messages=[{"role": "user", "content": FIX_PROMPT.format(
                befunde=naturalness.findings_note(findings), text=text)}],
        )
        fixed = sanitize_generated_text(resp.content[0].text.strip())
    except Exception as e:
        print(f"  Reparatur fehlgeschlagen (nicht kritisch): {e}", flush=True)
        return ""
    if not fixed or abs(len(fixed) - len(text)) > max(80, int(len(text) * 0.15)):
        print("  Reparatur verworfen (Laengen-Guard).", flush=True)
        return ""
    hard = text_gate.hard_violations(fixed, cap)
    if hard:
        print("  Reparatur verworfen (Textwache): " + "; ".join(hard), flush=True)
        return ""
    return fixed


def _short(findings: list[dict]) -> str:
    return "; ".join(f"{f['art']} \"{f['zitat'][:50]}\"" for f in findings)


def _reader_loop(de_draft: str, cap: int, voice: str = "", material: str = "") -> str:
    """Leser, bis zu MAX_FIX_ROUNDS chirurgische Reparaturen, Leser. Gibt ""
    zurueck, wenn danach Befunde bleiben oder eine Reparatur verworfen
    wurde. Ohne Urteil des Lesers bleibt der Text, wie er ist."""
    findings = _all_findings(de_draft, voice, material)
    if findings is None:
        print("  Leser: kein Urteil, Text bleibt", flush=True)
        return de_draft
    rounds = 0
    while findings and rounds < MAX_FIX_ROUNDS:
        rounds += 1
        print(f"  Leser: {len(findings)} Befund(e), Reparatur {rounds}: {_short(findings)}", flush=True)
        fixed = _fix_passages(de_draft, findings, cap)
        if not fixed:
            break
        de_draft = fixed
        findings = _all_findings(de_draft, voice, material)
        if findings is None:
            print("  Leser: kein Urteil nach Reparatur, Text bleibt", flush=True)
            return de_draft
    if findings:
        print(f"  Leser: Text verworfen, Restbefund: {_short(findings)}", flush=True)
        return ""
    print(f"  Leser: sauber nach {rounds} Reparatur(en)", flush=True)
    return de_draft
```

- [ ] **Step 4: Aufruf in `generate_post_and_image_prompt` umstellen**

Alt (Zeilen 1600-1603):
```python
    if de_draft and _cfg.FEATURES.get("naturalness_check"):
        de_draft, de_parts = _naturalness_loop(
            de_draft, de_parts, de_prompt, cap,
            voice=persona_voice_de or _cfg.TOKENS["PERSONA_DE"])
```
Neu:
```python
    if de_draft and _cfg.FEATURES.get("naturalness_check"):
        de_draft = _reader_loop(
            de_draft, cap,
            voice=persona_voice_de or _cfg.TOKENS["PERSONA_DE"],
            material=post["post_text"][:1500])
```
Im Docstring der Funktion den Absatz "Mit FEATURES["naturalness_check"] beurteilt danach ein deutscher Lektor (tools/naturalness) den Text; unter NATURALNESS_MIN oder bei Formel-Treffern schreibt das Modell einmal neu, die bessere Fassung bleibt." ersetzen durch: "Mit FEATURES["naturalness_check"] liest danach der Leser (tools/naturalness) den Text; Befunde werden chirurgisch repariert (hoechstens MAX_FIX_ROUNDS), bleibt ein Befund, ist de_draft ""."

- [ ] **Step 5: Alt-Lektor aus `tools/naturalness.py` entfernen**

Loeschen: `NATURALNESS_MIN = 7`, `CRITIC_PROMPT`, `_VOICE_BLOCK`, `_VOICE_ITEM`, `critic_prompt`, `parse_verdict`, `rewrite_note`. Modul-Docstring Punkt 2 ersetzen durch:

```
2. Leser (READER_PROMPT hier, Aufruf in post_scorer._reader_loop): sieben
   Fragen mit Zitatpflicht, Befundliste statt Note. Befunde werden
   chirurgisch repariert; nach zwei Runden mit Restbefund wird der Text
   verworfen. Stand 28.08.2026, Spec docs/superpowers/specs/
   2026-08-28-leser-gate-design.md. Der Lektor mit Note 1-10 (24.08. bis
   28.08.) mittelte Defekte weg: ein kaputter Opener plus neun saubere
   Absaetze ergab eine 7.
```

In `tests/test_naturalness.py` die Tests `test_critic_prompt_with_and_without_voice`, `test_parse_verdict_tolerates_prose_and_garbage`, `test_rewrite_note_carries_findings` loeschen.

- [ ] **Step 6: Kommentare in `clients/swot/config.py` nachziehen**

Zeile 537-540 (FEATURES-Kommentar) ersetzen durch:
```python
    # Leser hinter der Textwache (Richard 28.08.2026, vorher Lektor-Note seit
    # 24.08.): Befunde mit Zitat, chirurgische Reparatur, Verwerfen bei
    # Restbefund. Ein Sonnet-Call je Post, je Reparatur zwei mehr. Siehe
    # tools/naturalness.py und post_scorer._reader_loop.
```
Zeile 814 "als Massstab in den Lektor (naturalness.critic_prompt)" ersetzen durch "als Massstab in den Leser (naturalness.reader_prompt)".

- [ ] **Step 7: Tests laufen lassen**

Run: `python -m pytest tests/test_reader_loop.py tests/test_naturalness.py tests/test_format_structures.py -q`
Expected: alle gruen.

- [ ] **Step 8: Vollstaendige Suite**

Run: `python -m pytest -q 2>&1 | tail -3`
Expected: gruen. `grep -rn "critic_prompt\|parse_verdict\|rewrite_note\|NATURALNESS_MIN\|_naturalness_loop" --include=*.py .` liefert nichts.

- [ ] **Step 9: Commit**

```bash
git add tools/post_scorer.py tools/naturalness.py tests/test_reader_loop.py tests/test_naturalness.py clients/swot/config.py
git commit -m "Leser-Loop ersetzt Lektor-Note: chirurgische Reparatur, Verwerfen bei Restbefund

Kein Vollneulauf aus dem Schreib-Prompt mehr. Befunde mit Zitat werden
in hoechstens zwei Runden in der Passage repariert; bleibt ein Befund,
steht der Text nicht im Plan. Laengen-Guard und Textwache pruefen jede
Reparatur. Alt-Lektor (Note 1-10) und seine Tests entfernt.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
git push origin master
```

- [ ] **Step 10: Trockenlauf mit Log (bezahlt, rund 0,30 EUR, im Budget von Schritt 4)**

```bash
CLIENT=swot python scripts/measure_diet.py --n 3 --label loop --loop --out "/c/Users/richa/Jolly_Claude_Code/Clients/SWOT/Content/Pruefberichte"
```
Expected im Log: Zeilen "Leser: ..." je Post, mindestens einmal "Reparatur 1" oder "sauber nach 0 Reparatur(en)". Ergebnis in `tasks/todo.md` unter Review.

---

### Task 6: Bestand bereinigen (`--write`) und nachfuellen

**Files:**
- Modify: `tools/review_backfill.py` (neue Funktionen `decide_row`, `notion_props_for`)
- Modify: `run_review_backfill.py` (`--write`, `--refill-passes`, Backup, Readback)
- Test: `tests/test_review_backfill.py` (anhaengen)

**Interfaces:**
- Consumes: `post_scorer._reader_loop(text, cap, voice, material)`, `post_scorer.LENGTH_CAP`, `post_scorer._append_cta`, `text_gate.hard_violations`, `run_plan_fill._rich`, `run_plan_fill.text_fill(months, cfg)`
- Produces: `decide_row(row, cfg, loop_fn) -> dict` (Keys `page_id, titel, kanal, datum, aktion in {"unveraendert", "repariert", "geleert"}, text_neu, grund`), `notion_props_for(text_neu: str) -> dict`

- [ ] **Step 1: Failing Tests schreiben**

An `tests/test_review_backfill.py` anhaengen:

```python
def _cfg():
    return type("Cfg", (), {"CTA_DE": CTA, "ACCOUNT_VOICES": {"LinkedIn Robert": "Stimme"}})()


def _row2(text):
    return {"page_id": "p1", "titel": "T", "kanal": "LinkedIn Robert", "datum": "2026-09-10",
            "kurz": "K", "text": text, "status": "Entwurf"}


def test_decide_row_unchanged_when_loop_returns_same_text():
    body = "Sauberer Text."
    out = rb.decide_row(_row2(body + "\n\n" + CTA), _cfg(), lambda t, cap, voice, material: t)
    assert out["aktion"] == "unveraendert" and out["text_neu"] == body + "\n\n" + CTA


def test_decide_row_repaired_text_gets_cta_back():
    seen = {}

    def loop(t, cap, voice, material):
        seen.update(text=t, cap=cap, voice=voice, material=material)
        return "Repariert."

    out = rb.decide_row(_row2("Kaputt.\n\n" + CTA), _cfg(), loop)
    assert seen["text"] == "Kaputt." and seen["voice"] == "Stimme" and seen["cap"] == 2100
    assert seen["material"].startswith("Thema: T")
    assert out["aktion"] == "repariert" and out["text_neu"] == "Repariert.\n\n" + CTA


def test_decide_row_cleared_on_residue_or_hard_violation():
    out = rb.decide_row(_row2("Kaputt.\n\n" + CTA), _cfg(), lambda *a: "")
    assert out["aktion"] == "geleert" and out["text_neu"] == "" and "Restbefund" in out["grund"]
    long = "x" * 2200
    calls = []
    out = rb.decide_row(_row2(long), _cfg(), lambda *a: calls.append(1) or long)
    assert out["aktion"] == "geleert" and "Zeichen" in out["grund"]
    assert calls == []


def test_notion_props_for_text_and_for_clearing():
    assert rb.notion_props_for("Neu.") == {"Post-Text": {"rich_text": [{"text": {"content": "Neu."}}]}}
    assert rb.notion_props_for("") == {"Post-Text": {"rich_text": []}}
```

- [ ] **Step 2: Tests laufen lassen, Fehlschlag pruefen**

Run: `python -m pytest tests/test_review_backfill.py -q`
Expected: 4 FAILED mit `AttributeError: ... has no attribute 'decide_row'`.

- [ ] **Step 3: Funktionen in `tools/review_backfill.py` anhaengen**

```python
def decide_row(row: dict, cfg, loop_fn) -> dict:
    """Bereinigung einer Zeile. loop_fn(text, cap, voice, material) ist
    post_scorer._reader_loop oder ein Test-Double: gleicher Text = nichts zu
    tun, anderer Text = repariert, "" = Restbefund, Zeile wird geleert.
    Ueberlaenge oder CAPS im Bestand leeren die Zeile ohne Modellaufruf; der
    Normal-Lauf schreibt sie mit dem Cap neu."""
    from tools import text_gate
    from tools.post_scorer import LENGTH_CAP, _append_cta
    cta = getattr(cfg, "CTA_DE", "")
    cap = LENGTH_CAP["lang"]
    text = strip_cta(row["text"], cta)
    base = {"page_id": row["page_id"], "titel": row["titel"], "kanal": row["kanal"],
            "datum": row["datum"]}
    hard = text_gate.hard_violations(text, cap)
    if hard:
        return {**base, "aktion": "geleert", "text_neu": "", "grund": "; ".join(hard)}
    voice = getattr(cfg, "ACCOUNT_VOICES", {}).get(row["kanal"], "")
    neu = loop_fn(text, cap, voice, material_for(row))
    if not neu:
        return {**base, "aktion": "geleert", "text_neu": "", "grund": "Restbefund nach Reparatur"}
    if neu.strip() == text.strip():
        return {**base, "aktion": "unveraendert", "text_neu": row["text"], "grund": ""}
    return {**base, "aktion": "repariert", "text_neu": _append_cta(neu, cta), "grund": ""}


def notion_props_for(text_neu: str) -> dict:
    """Property-Patch: Text gechunkt (run_plan_fill._rich) oder leer."""
    if not text_neu:
        return {"Post-Text": {"rich_text": []}}
    from run_plan_fill import _rich
    return {"Post-Text": _rich(text_neu)}
```

- [ ] **Step 4: `--write` in `run_review_backfill.py`**

Modul-Docstring um den Schreibmodus ergaenzen:

```
    CLIENT=swot python run_review_backfill.py --write --out <Ordner> [--refill-passes 3]

--write bereinigt jede Entwurf-Zeile: Leser plus chirurgische Reparatur
(post_scorer._reader_loop), reparierte Texte gehen mit CTA zurueck nach
Notion, Restbefund oder Ueberlaenge leeren den Post-Text. Danach fuellt
run_plan_fill.text_fill die geleerten Zeilen der betroffenen Monate mit dem
neuen Prompt und dem Leser nach, bis zu --refill-passes Durchgaenge (jeder
Durchgang textet nur Zeilen ohne Text). Vor dem ersten Schreiben liegt ein
JSON-Backup aller Post-Texte im Ausgabeordner. "Text freigegeben" und hoeher
wird nie angefasst. Kosten: rund 3 EUR Bereinigung plus 1-2 EUR Nachfuellen.
```

Imports ergaenzen: `import requests`, `from run_plan_fill import _rt, read_plan, text_fill`, `from tools.monthly_plan import NOTION_API, TIMEOUT`, `from tools.post_scorer import client, _reader_loop`, `from tools.topic_ideas_db import _headers as notion_headers`.

Funktionen ergaenzen:

```python
def _backup(rows: list[dict], out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, dt.date.today().isoformat() + "_backup-post-texte.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({r["page_id"]: {"titel": r["titel"], "kanal": r["kanal"],
                                  "datum": r["datum"], "text": r["text"]} for r in rows},
                  f, ensure_ascii=False, indent=1)
    return path


def _patch_and_readback(page_id: str, text_neu: str) -> bool:
    resp = requests.patch(f"{NOTION_API}/pages/{page_id}", headers=notion_headers(),
                          json={"properties": rb.notion_props_for(text_neu)}, timeout=TIMEOUT)
    if not resp.ok:
        print(f"  Notion-Fehler {resp.status_code}: {resp.text[:160]}", flush=True)
        return False
    back = requests.get(f"{NOTION_API}/pages/{page_id}", headers=notion_headers(), timeout=TIMEOUT)
    back.raise_for_status()
    ist = _rt(back.json()["properties"], "Post-Text")
    ok = ist.strip() == text_neu.strip()
    if not ok:
        print(f"  Readback weicht ab ({len(ist)} statt {len(text_neu)} Zeichen)", flush=True)
    return ok


def write(out_dir: str, cfg, refill_passes: int) -> dict:
    rows = rb.plan_rows(read_plan(cfg.CONTENT_PLAN_DB_ID))
    print(f"Entwurf-Zeilen mit Text: {len(rows)}", flush=True)
    print(f"Backup: {_backup(rows, out_dir)}", flush=True)
    zaehler = {"unveraendert": 0, "repariert": 0, "geleert": 0, "fehler": 0}
    monate, protokoll = set(), []
    for i, row in enumerate(rows, 1):
        print(f"  {i:2d}/{len(rows)} {row['datum']} {row['kanal']:20s} {row['titel'][:50]}", flush=True)
        d = rb.decide_row(row, cfg, _reader_loop)
        protokoll.append({k: v for k, v in d.items() if k != "text_neu"})
        if d["aktion"] == "unveraendert":
            zaehler["unveraendert"] += 1
            continue
        if _patch_and_readback(d["page_id"], d["text_neu"]):
            zaehler[d["aktion"]] += 1
            if d["aktion"] == "geleert":
                monate.add(d["datum"][:7])
                print(f"    geleert: {d['grund']}", flush=True)
        else:
            zaehler["fehler"] += 1
    stem = os.path.join(out_dir, dt.date.today().isoformat() + "_bestand-write")
    with open(stem + ".json", "w", encoding="utf-8") as f:
        json.dump({"zaehler": zaehler, "zeilen": protokoll}, f, ensure_ascii=False, indent=1)
    print(f"Bereinigung: {zaehler}, Protokoll {stem}.json", flush=True)
    months = sorted((int(m[:4]), int(m[5:7])) for m in monate)
    for p in range(refill_passes):
        if not months:
            break
        print(f"Nachfuellen, Durchgang {p + 1}: {months}", flush=True)
        r = text_fill(months, cfg=cfg)
        print(f"  geschrieben {r['geschrieben']} von {r['zeilen']}", flush=True)
    offen = [r for r in rb.plan_rows_all_entwurf(read_plan(cfg.CONTENT_PLAN_DB_ID)) if not r["text"]]
    print(f"Entwurf-Zeilen ohne Text nach dem Lauf: {len(offen)}", flush=True)
    for r in offen:
        print(f"  OFFEN {r['datum']} {r['kanal']} {r['titel'][:50]}", flush=True)
    return {**zaehler, "offen": len(offen)}
```

Dazu in `tools/review_backfill.py` die Variante ohne Text-Filter (fuer den Abschluss-Check):

```python
def plan_rows_all_entwurf(rows: list[dict]) -> list[dict]:
    """Wie plan_rows, aber auch Zeilen ohne Text: der Abschluss-Check zaehlt
    Entwuerfe, die nach dem Nachfuellen leer geblieben sind."""
    from run_plan_fill import _date, _rt, _sel, _title
    out = []
    for r in rows:
        p = r["properties"]
        if _sel(p, "Typ") != "LinkedIn-Post" or _sel(p, "Status") != "Entwurf":
            continue
        out.append({"page_id": r["id"], "titel": _title(p), "kanal": _sel(p, "Kanal"),
                    "datum": _date(p), "kurz": _rt(p, "Kurzbeschreibung"),
                    "text": _rt(p, "Post-Text"), "status": _sel(p, "Status")})
    return out
```

`main()` erweitern:

```python
    ap.add_argument("--write", action="store_true", help="bereinigen und nachfuellen")
    ap.add_argument("--refill-passes", type=int, default=3)
    ...
    if args.report == args.write:
        ap.error("genau eines von --report oder --write angeben")
    cfg = load_client()
    r = report(args.out, cfg) if args.report else write(args.out, cfg, args.refill_passes)
```
(Die bisherige Zeile `if not args.report: ap.error(...)` entfaellt.)

- [ ] **Step 5: Tests laufen lassen**

Run: `python -m pytest tests/test_review_backfill.py -q`
Expected: 10 passed. Dann `python -m pytest -q 2>&1 | tail -3`: gruen.

- [ ] **Step 6: Commit**

```bash
git add tools/review_backfill.py run_review_backfill.py tests/test_review_backfill.py
git commit -m "Bestandsbereinigung --write: Reparatur zurueck, Restbefund leert, Nachfuellen

Backup vor dem ersten Schreiben, Readback je Zeile, freigegebene Zeilen
bleiben unangetastet. Geleerte Zeilen fuellt run_plan_fill.text_fill in
bis zu drei Durchgaengen mit dem neuen Prompt und dem Leser nach.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
git push origin master
```

- [ ] **Step 7: Bezahlter Lauf 4 (rund 3 EUR plus 1-2 EUR Nachfuellen, im Budget)**

```bash
cd "/c/Users/richa/Jolly_Claude_Code/Jolly Automations/Jolly Influencer Post Recycling" && CLIENT=swot python run_review_backfill.py --write --out "/c/Users/richa/Jolly_Claude_Code/Clients/SWOT/Content/Pruefberichte" 2>&1 | tee "/c/Users/richa/Jolly_Claude_Code/Clients/SWOT/Content/Pruefberichte/2026-08-28_bestand-write.log"
```
Expected: "Backup: ..." vor der ersten Zeile; Zaehler am Ende; "Entwurf-Zeilen ohne Text nach dem Lauf: 0". Bleiben OFFEN-Zeilen, einen weiteren Durchgang `CLIENT=swot python -c "from clients import load_client; from run_plan_fill import text_fill; text_fill([(2026, 9), (2026, 10), (2026, 11)], cfg=load_client())"` fahren (nur Zeilen ohne Text, rund 0,15 EUR je Zeile).

- [ ] **Step 8: Live-Read aus Notion als Abschlussbeleg**

```bash
CLIENT=swot python - <<'EOF'
from clients import load_client
from run_plan_fill import read_plan
from tools import review_backfill as rb
cfg = load_client()
rows = rb.plan_rows_all_entwurf(read_plan(cfg.CONTENT_PLAN_DB_ID))
leer = [r for r in rows if not r["text"]]
ohne_cta = [r for r in rows if r["text"] and not r["text"].rstrip().endswith(cfg.CTA_DE)]
print(f"Entwurf LinkedIn-Post: {len(rows)}, ohne Text: {len(leer)}, ohne CTA: {len(ohne_cta)}")
for r in leer + ohne_cta:
    print("  ", r["datum"], r["kanal"], r["titel"][:60])
EOF
```
Expected: "ohne Text: 0, ohne CTA: 0". Zahlen, Zaehler des Laufs und Backup-Pfad in `tasks/todo.md` unter Review.

- [ ] **Step 9: Memory, Lessons, Handover**

- `C:\Users\richa\.claude\projects\c--Users-richa-Jolly-Claude-Code\memory\project_swot_content_engine_maschinerie.md`: neuer Abschnitt "Leser-Gate 28.08.2026" mit: Loop-Semantik (Leser, 2 Reparaturen, Verwerfen), `CTA_DE` in der Pipeline, Bestandslauf-Zahlen, Basislinie alt/neu, Regel "Verbotslisten mit Wortlaut gehoeren zum Leser, nie zum Schreib-Prompt", Regel "Neue Regex in naturalness.TICS nur noch mit Begruendung, warum der Leser sie nicht faengt".
- `C:\Users\richa\.claude\projects\c--Users-richa-Jolly-Claude-Code\memory\feedback_swot_linkedin_review_kulle_2026_08_24.md`: Verweis auf den Abschnitt, ein Satz.
- `c:\Users\richa\Jolly_Claude_Code\tasks\lessons.md`: Eintrag "Prompt-Verbote mit Wortlaut leaken in den Output; Prompt-Widersprueche entstehen, wenn jede Panne eine Zeile bekommt und niemand den ganzen Prompt liest. Vor jeder neuen Prompt-Regel den gebauten Prompt messen (Zeichen, Verneinungen, Widersprueche)."
- Commit + Push im Memory-Repo (`C:\Users\richa\.claude`), Zahlen in `tasks/todo.md` Review.
