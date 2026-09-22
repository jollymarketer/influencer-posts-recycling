# Jolly Themenachsen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Jollys taegliche LinkedIn-Entwuerfe streuen ueber acht GTM-Themenachsen statt in drei Bloecken zu clustern.

**Architecture:** Die Achse wird an drei Stellen verankert: beim Scrapen (Keyword-Herkunft je Achse), in der Datenhaltung (nullable Spalte `axis` in `blog_content_mining.influencer_posts`, gefuellt aus der Herkunft oder per Haiku-Klassifizierer) und in der Auswahl (Deckel von 2 je Achse im Fenster der letzten 10 Notion-Posts, mit Pool-Rueckgriff). Zusaetzlich werden zwei Engstellen im Prompt geoeffnet, sonst erreichen achsenfremde Posts die Auswahl nie.

**Tech Stack:** Python 3.11, requests gegen Supabase PostgREST und die Notion-API, Anthropic Haiku (`claude-haiku-4-5-20251001`) ueber `tools/anthropic_auth.LazyAnthropic`, pytest.

**Spec:** `docs/superpowers/specs/2026-09-22-jolly-themenachsen-design.md`

## Global Constraints

- Mandant ist ausschliesslich `jolly`. SWOT und lisocon bleiben unberuehrt: `axis` wird fuer SWOT nicht geschrieben, dort traegt weiter der `source`-String die Achse und `tools/monthly_plan.py` bleibt unveraendert.
- Der Klassifizierer laeuft nur bei jolly. Zwei Sperren: Feature-Flag `axis_classifier` existiert nur in `clients/jolly/config.py` (fehlt es, No-Op) und ein direkter Aufruf mit fremdem Mandanten scheitert hart mit Klartext.
- Achsen-Schluessel, genau diese acht, genau diese Schreibweise: `outbound_maschine`, `daten_und_revops`, `positionierung_und_angebot`, `sales_prozess`, `team_und_enablement`, `inbound_und_content`, `bestand_und_expansion`, `ki_im_gtm`.
- Deckel: eine Achse mit 2 Vorkommen im Fenster der letzten 10 Notion-Posts ist gesperrt. `axis = null` gilt als frei und wird nie gesperrt.
- `MIN_SUPPORT`, `TOP_N`, `TOP_N_PER_AXIS` in `run_topic_mining.py` bleiben unberuehrt. Dieser Plan aendert den Tages-Winner-Pfad, nicht das Freitags-Mining.
- `JOLLY_KEYWORDS` darf keine zweite Wahrheit bleiben: nach Task 1 wird sie aus `KEYWORDS_BY_AXIS` abgeleitet.
- Keine Netz-Tests. Jeder Test in `tests/` arbeitet mit festen Zeilen und Monkeypatches, Muster wie `tests/test_monthly_plan.py` und `tests/test_client_scoping_supabase.py`.
- Modell fuer den Klassifizierer: `claude-haiku-4-5-20251001`. Kein anderes.
- Keine bezahlten Apify-Laeufe ohne Richards Freigabe (Task 6).
- Harte VOC-Regeln bleiben wortgleich: keine US-Zahlen als DACH-Fakt, nie "Kaltakquise ist tot", keine Anbieter- oder Agenturnamen, keine Reply-Raten-Versprechen.

## Dateien

| Datei | Verantwortung |
|---|---|
| `clients/jolly/config.py` | `KEYWORDS_BY_AXIS`, Flag `axis_classifier`, offene `TOPIC_FIT_QUESTION`, entschaerfter VOC-Block |
| `run_keyword_scrape.py` | `JOLLY_KEYWORDS` abgeleitet, Achse aus der Umkehrabbildung beim Upsert |
| `scripts/2026-09-22-add-axis-column.sql` | Migration der nullable Spalte `axis` |
| `tools/supabase_db.py` | `axis` in `_to_row`, `upsert_posts(axis=...)`, `get_unclassified_posts`, `set_axis` |
| `tools/axis_classifier.py` | Haiku-Klassifizierer, jolly-only, mit beiden Sperren |
| `scripts/backfill_axes.py` | Backfill-Einstieg plus Verteilungsbericht |
| `scripts/add_achse_property.py` | Notion-Select `Achse` idempotent anlegen |
| `tools/notion_db.py` | `get_recent_axes` |
| `tools/axis_gate.py` | reine Auswahllogik: gesperrte Achsen, freie Kandidaten |
| `run_research.py` | Deckel in Schritt 4, Pool-Rueckgriff, `Achse` schreiben |
| `tests/test_axis_gate.py` | Deckel, `null`, Pool-Rueckgriff, Leerfall |
| `tests/test_axis_classifier.py` | No-Op ohne Flag, harter Abbruch bei fremdem Mandanten |

---

### Task 1: Keyword-Zuordnung je Achse

Erste Handlung dieses Tasks ist die Tabelle an Richard, nicht der Commit. Die Auffuellung von `team_und_enablement` und `bestand_und_expansion` ist neu und nicht durch einen frueheren Lock gedeckt.

**Files:**
- Modify: `clients/jolly/config.py` (neuer Block `KEYWORDS_BY_AXIS` hinter `FEATURES`, Zeile 181)
- Modify: `run_keyword_scrape.py:20-41` (`JOLLY_KEYWORDS` abgeleitet) und `run_keyword_scrape.py:scrape_and_persist`
- Test: `tests/test_axis_keywords.py`

**Interfaces:**
- Consumes: nichts.
- Produces: `clients.jolly.config.KEYWORDS_BY_AXIS: dict[str, list[str]]`; `run_keyword_scrape.axis_for_keyword(keyword: str, cfg=None) -> str | None`; `run_keyword_scrape.JOLLY_KEYWORDS: list[str]` bleibt als Name bestehen, wird aber aus der Achsen-Abbildung abgeleitet.

- [ ] **Step 1: Tabelle vorlegen, Freigabe abwarten**

Richard bekommt exakt diese Tabelle im Chat. Bereits gelockte Begriffe sind unmarkiert, neue mit "neu" markiert. Erst nach seinem Wort weiter.

| Achse | Begriffe |
|---|---|
| `outbound_maschine` | cold email, cold email deliverability, email warmup, intent data, outbound sequence (neu), sales sequence (neu), lead list building (neu), multichannel outbound (neu) |
| `daten_und_revops` | revenue operations, revops automation, sales forecasting, crm hygiene (neu), pipeline review (neu), sales reporting (neu), deal stages (neu) |
| `positionierung_und_angebot` | ideal customer profile, fractional cmo, go-to-market strategy, account based marketing, offer design (neu), b2b positioning (neu), b2b pricing (neu) |
| `sales_prozess` | buying committee, sales discovery call (neu), sales qualification (neu), objection handling (neu), b2b negotiation (neu), deal closing (neu) |
| `team_und_enablement` | first sales hire (neu), sales onboarding (neu), sales playbook (neu), sales training b2b (neu), sales enablement (neu), sales hiring (neu) |
| `inbound_und_content` | b2b lead generation, demand generation, answer engine optimization, linkedin content strategy (neu), lead magnet (neu), b2b webinar (neu), content operations (neu) |
| `bestand_und_expansion` | customer onboarding (neu), customer retention b2b (neu), account management b2b (neu), key account management (neu), upsell cross-sell (neu), customer success playbook (neu) |
| `ki_im_gtm` | gtm engineering, ai sdr, ai personalization sales, ai agents sales (neu), ai lead research (neu), ai go to market (neu) |

Freigegeben von Richard am 22.09.2026 mit drei Korrekturen gegenueber dem ersten Entwurf: keine Abo-Metriken (`net revenue retention`, `churn signals`, `upsell expansion revenue` raus), keine US-SaaS-Org-Sprache (`sales compensation plan`, `sales ramp time` raus), `sales attribution` durch das breitere `sales reporting` ersetzt. Grund: der ICP umfasst Tech-Services und Industrie-Mittelstand, die diese Begriffe nicht sprechen. Die Achse `bestand_und_expansion` bleibt, nur anders besetzt.

- [ ] **Step 2: Failing test schreiben**

```python
# tests/test_axis_keywords.py
"""Achsen-Keywords bei jolly: acht Achsen, Umkehrabbildung eindeutig,
JOLLY_KEYWORDS ist abgeleitet. Kein Netz."""
import os
import sys

os.environ["CLIENT"] = "jolly"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from clients import load_client

import run_keyword_scrape as rks

ACHSEN = {
    "outbound_maschine", "daten_und_revops", "positionierung_und_angebot",
    "sales_prozess", "team_und_enablement", "inbound_und_content",
    "bestand_und_expansion", "ki_im_gtm",
}


def test_jolly_hat_alle_acht_achsen():
    by_axis = load_client().KEYWORDS_BY_AXIS
    assert set(by_axis) == ACHSEN


def test_jede_achse_mindestens_sechs_begriffe():
    by_axis = load_client().KEYWORDS_BY_AXIS
    dünn = {a: len(k) for a, k in by_axis.items() if len(k) < 6}
    assert not dünn, f"zu duenn besetzt: {dünn}"


def test_kein_begriff_in_zwei_achsen():
    by_axis = load_client().KEYWORDS_BY_AXIS
    alle = [k for keywords in by_axis.values() for k in keywords]
    assert len(alle) == len(set(alle))


def test_jolly_keywords_ist_abgeleitet():
    by_axis = load_client().KEYWORDS_BY_AXIS
    erwartet = {k for keywords in by_axis.values() for k in keywords}
    assert set(rks.JOLLY_KEYWORDS) == erwartet


def test_axis_for_keyword_trifft_die_achse():
    assert rks.axis_for_keyword("cold email") == "outbound_maschine"
    assert rks.axis_for_keyword("revenue operations") == "daten_und_revops"
    assert rks.axis_for_keyword("COLD EMAIL") == "outbound_maschine"
    assert rks.axis_for_keyword("völlig unbekannt") is None
```

- [ ] **Step 3: Test laufen lassen, Fehlschlag sehen**

Run: `python -m pytest tests/test_axis_keywords.py -v`
Expected: FAIL, `AttributeError` auf `KEYWORDS_BY_AXIS` beziehungsweise `axis_for_keyword`.

- [ ] **Step 4: `KEYWORDS_BY_AXIS` in jollys Config**

Direkt hinter dem `FEATURES`-Block (`clients/jolly/config.py:181`) einfuegen, mit den in Step 1 freigegebenen Begriffen:

```python
# Themenachsen (Spec 2026-09-22). Herkunft fuer run_axis_scrape.py und
# Umkehrabbildung fuer den Donnerstags-Keyword-Scrape. Einzige Wahrheit:
# run_keyword_scrape.JOLLY_KEYWORDS leitet sich hieraus ab.
KEYWORDS_BY_AXIS = {
    "outbound_maschine": [
        "cold email", "cold email deliverability", "email warmup", "intent data",
        "outbound sequence", "sales sequence", "lead list building",
        "multichannel outbound",
    ],
    "daten_und_revops": [
        "revenue operations", "revops automation", "sales forecasting",
        "crm hygiene", "pipeline review", "sales attribution", "deal stages",
    ],
    "positionierung_und_angebot": [
        "ideal customer profile", "fractional cmo", "go-to-market strategy",
        "account based marketing", "offer design", "b2b positioning", "b2b pricing",
    ],
    "sales_prozess": [
        "buying committee", "sales discovery call", "sales qualification",
        "objection handling", "b2b negotiation", "deal closing",
    ],
    "team_und_enablement": [
        "first sales hire", "sales onboarding", "sales playbook",
        "sales compensation plan", "sales enablement", "sales ramp time",
    ],
    "inbound_und_content": [
        "b2b lead generation", "demand generation", "answer engine optimization",
        "linkedin content strategy", "lead magnet", "b2b webinar",
        "content operations",
    ],
    "bestand_und_expansion": [
        "customer onboarding", "customer retention b2b", "upsell expansion revenue",
        "churn signals", "net revenue retention", "customer success playbook",
    ],
    "ki_im_gtm": [
        "gtm engineering", "ai sdr", "ai personalization sales",
        "ai agents sales", "ai lead research", "ai go to market",
    ],
}
```

- [ ] **Step 5: `JOLLY_KEYWORDS` ableiten und `axis_for_keyword` bauen**

In `run_keyword_scrape.py` die Literal-Liste `JOLLY_KEYWORDS` (Zeilen 20-41) ersetzen. Der Import von `clients.load_client` steht schon oben.

```python
def _jolly_axes() -> dict:
    """Achsen-Abbildung aus jollys Config, ohne den CLIENT der Laufzeit
    anzufassen: JOLLY_KEYWORDS ist ein Modul-Attribut und wird auch dann
    gelesen, wenn ein anderer Mandant laeuft."""
    from clients.jolly import config as jolly_config
    return jolly_config.KEYWORDS_BY_AXIS


# Gelockt 2026-06-08 mit Richard, seit 2026-09-22 abgeleitet aus
# clients/jolly/config.py KEYWORDS_BY_AXIS. Nicht wieder als Literal
# zurueckdrehen, sonst traegt die Achse eine zweite Wahrheit.
JOLLY_KEYWORDS = [k for keywords in _jolly_axes().values() for k in keywords]


def axis_for_keyword(keyword: str, cfg=None) -> str | None:
    """Umkehrung von KEYWORDS_BY_AXIS: Begriff nach Achse, ohne Ruecksicht auf
    Gross- und Kleinschreibung. Unbekannter Begriff -> None (der Klassifizierer
    holt die Zeile spaeter, keine Zuordnung auf Verdacht)."""
    by_axis = getattr(cfg, "KEYWORDS_BY_AXIS", None) if cfg else _jolly_axes()
    if not by_axis:
        return None
    ziel = keyword.strip().lower()
    for achse, keywords in by_axis.items():
        if ziel in {k.lower() for k in keywords}:
            return achse
    return None
```

- [ ] **Step 6: Test laufen lassen, gruen sehen**

Run: `python -m pytest tests/test_axis_keywords.py -v`
Expected: PASS, 5 Tests.

- [ ] **Step 7: Bestehende Keyword-Tests gegenpruefen**

Run: `python -m pytest tests/test_client_keywords_and_scoring.py tests/test_daily_keyword_source.py tests/test_axis_scrape.py tests/test_linkedin_keyword_scraper.py -v`
Expected: PASS, unveraendert. Schlaegt einer auf die Zahl 18 oder 20 an, wird die Erwartung auf `len(JOLLY_KEYWORDS)` umgestellt, nicht die Keyword-Liste beschnitten.

- [ ] **Step 8: Commit**

```bash
git add clients/jolly/config.py run_keyword_scrape.py tests/test_axis_keywords.py
git commit -F .git/COMMIT_EDITMSG_axes
```

Commit-Text (in die Datei, nie als Here-String):

```
feat(jolly): KEYWORDS_BY_AXIS mit acht Themenachsen

JOLLY_KEYWORDS wird daraus abgeleitet, axis_for_keyword liefert die
Umkehrung fuer den Donnerstags-Scrape. Keyword-Set von Richard
freigegeben 2026-09-22.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

### Task 2: Spalte `axis`, Schreibwege, Klassifizierer, Backfill

**Files:**
- Create: `scripts/2026-09-22-add-axis-column.sql`
- Create: `tools/axis_classifier.py`
- Create: `scripts/backfill_axes.py`
- Modify: `tools/supabase_db.py:66-110` (`_to_row`, `upsert_posts`), neue Leser am Dateiende
- Modify: `clients/jolly/config.py:177-181` (`FEATURES`)
- Modify: `run_keyword_scrape.py:scrape_and_persist`
- Test: `tests/test_axis_classifier.py`, Erweiterung von `tests/test_supabase_db.py`

**Interfaces:**
- Consumes: `run_keyword_scrape.axis_for_keyword(keyword, cfg=None) -> str | None` aus Task 1, `clients.jolly.config.KEYWORDS_BY_AXIS`.
- Produces:
  - `tools.supabase_db.upsert_posts(posts: list[dict], source: str, axis: str | None = None) -> int`
  - `tools.supabase_db.get_unclassified_posts(days: int, sources: tuple[str, ...] = ("linkedin", "substack"), limit: int = 500) -> list[dict]`
  - `tools.supabase_db.set_axis(post_url: str, axis: str | None) -> None`
  - `tools.axis_classifier.AXES: tuple[str, ...]`
  - `tools.axis_classifier.classify_post(post_text: str) -> str | None`
  - `tools.axis_classifier.classify_rows(rows: list[dict], cfg=None) -> dict[str, int]`

- [ ] **Step 1: Migration schreiben**

```sql
-- scripts/2026-09-22-add-axis-column.sql
-- Themenachse je Post. Nullable: "passt in keine Achse" ist ein gueltiges
-- Ergebnis und darf nicht mit "noch nicht klassifiziert" verschmelzen --
-- deshalb traegt classified_at die Unterscheidung.
alter table blog_content_mining.influencer_posts
    add column if not exists axis text,
    add column if not exists axis_classified_at timestamptz;

create index if not exists influencer_posts_axis_idx
    on blog_content_mining.influencer_posts (client, axis);
```

Anwenden ueber den Supabase-SQL-Editor oder `mcp__claude_ai_Supabase__apply_migration`. Danach mit `list_tables` belegen, dass beide Spalten stehen.

- [ ] **Step 2: Failing test fuer die Schreibwege**

An `tests/test_supabase_db.py` anhaengen:

```python
def test_to_row_traegt_die_achse():
    from tools.supabase_db import _to_row
    post = {"post_url": "https://x/1", "post_text": "t", "date": "2026-09-20T08:00:00Z"}
    row = _to_row(post, "linkedin_search:ki_im_gtm", axis="ki_im_gtm")
    assert row["axis"] == "ki_im_gtm"
    assert row["axis_classified_at"] is not None


def test_to_row_ohne_achse_laesst_die_spalte_weg():
    from tools.supabase_db import _to_row
    row = _to_row({"post_url": "https://x/2", "date": ""}, "linkedin")
    assert "axis" not in row
    assert "axis_classified_at" not in row
```

Die Spalte fehlt absichtlich statt `None` zu sein: `Prefer: resolution=merge-duplicates` wuerde eine bereits klassifizierte Zeile beim naechsten Scrape sonst auf `null` zuruecksetzen.

- [ ] **Step 3: Test laufen lassen, Fehlschlag sehen**

Run: `python -m pytest tests/test_supabase_db.py -v`
Expected: FAIL, `_to_row() got an unexpected keyword argument 'axis'`.

- [ ] **Step 4: `tools/supabase_db.py` erweitern**

`_to_row` und `upsert_posts` ersetzen:

```python
def _to_row(post: dict, source: str, axis: str | None = None) -> dict | None:
    url = post.get("post_url")
    if not url:
        return None
    eng = post.get("engagement", {}) or {}
    # Contract: post["date"] is ISO-8601 or absent (scrapers guarantee this).
    date_raw = post.get("date", "")
    post_date = date_raw[:10] if date_raw else None  # ISO -> YYYY-MM-DD
    row = {
        "client": _client_name(),
        "post_url": url,
        "source": source,
        "influencer": post.get("influencer", ""),
        "post_text": post.get("post_text", ""),
        "post_date": post_date,
        "likes": int(eng.get("likes", 0) or 0),
        "comments": int(eng.get("comments", 0) or 0),
        "shares": int(eng.get("shares", 0) or 0),
    }
    # Achse nur setzen, wenn sie bekannt ist. Ein mitgeschicktes null wuerde
    # unter resolution=merge-duplicates eine schon klassifizierte Zeile beim
    # naechsten Scrape wieder leeren.
    if axis:
        row["axis"] = axis
        row["axis_classified_at"] = datetime.now(timezone.utc).isoformat()
    return row


def upsert_posts(posts: list[dict], source: str, axis: str | None = None) -> int:
    """Upsert posts on conflict post_url. Returns rows sent. Empty list = no-op.
    `axis` setzt die Themenachse fuer ALLE Zeilen dieses Aufrufs; wer je Post
    unterschiedliche Achsen hat, ruft gruppenweise auf."""
    rows = [r for r in (_to_row(p, source, axis=axis) for p in posts) if r is not None]
    if not rows:
        return 0
    url = f"{_base_url()}/rest/v1/{TABLE}?on_conflict=client,post_url"
    resp = requests.post(url, headers=_headers_write(), json=rows, timeout=TIMEOUT)
    if not (200 <= resp.status_code < 300):
        raise RuntimeError(f"Supabase upsert {resp.status_code}: {resp.text[:300]}")
    return len(rows)
```

Am Dateiende anhaengen:

```python
def get_unclassified_posts(days: int,
                           sources: tuple = ("linkedin", "substack"),
                           limit: int = 500) -> list[dict]:
    """Zeilen dieses Mandanten ohne Achsen-Entscheidung. Filter auf
    axis_classified_at, NICHT auf axis: 'passt in keine Achse' ist als
    axis=null mit gesetztem Zeitstempel gespeichert und darf nicht in jedem
    Lauf erneut bezahlt werden."""
    since = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
    quelle = ",".join(sources)
    params = {
        "select": "post_url,post_text,source,post_date",
        "client": f"eq.{_client_name()}",
        "post_date": f"gte.{since}",
        "axis_classified_at": "is.null",
        "source": f"in.({quelle})",
        "limit": str(limit),
    }
    resp = requests.get(f"{_base_url()}/rest/v1/{TABLE}", headers=_headers_read(),
                        params=params, timeout=TIMEOUT)
    if not (200 <= resp.status_code < 300):
        raise RuntimeError(f"Supabase get {resp.status_code}: {resp.text[:300]}")
    return resp.json()


def set_axis(post_url: str, axis: str | None) -> None:
    """Achsen-Entscheidung zurueckschreiben. axis=None heisst 'passt in keine'
    und wird mit Zeitstempel festgeschrieben, damit derselbe Grenzfall nie
    zweimal klassifiziert wird."""
    params = {"client": f"eq.{_client_name()}", "post_url": f"eq.{post_url}"}
    body = {"axis": axis,
            "axis_classified_at": datetime.now(timezone.utc).isoformat()}
    resp = requests.patch(f"{_base_url()}/rest/v1/{TABLE}", headers=_headers_write(),
                          params=params, json=body, timeout=TIMEOUT)
    if not (200 <= resp.status_code < 300):
        raise RuntimeError(f"Supabase patch {resp.status_code}: {resp.text[:300]}")


def axis_distribution(days: int) -> dict:
    """{achse: anzahl} ueber das Fenster, 'null' fuer Zeilen ohne Achse.
    Belegt die Angebotsseite, damit der Deckel nicht gegen einen leeren Pool
    laeuft."""
    since = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
    params = {"select": "axis", "client": f"eq.{_client_name()}",
              "post_date": f"gte.{since}", "limit": "10000"}
    resp = requests.get(f"{_base_url()}/rest/v1/{TABLE}", headers=_headers_read(),
                        params=params, timeout=TIMEOUT)
    if not (200 <= resp.status_code < 300):
        raise RuntimeError(f"Supabase get {resp.status_code}: {resp.text[:300]}")
    zaehler = {}
    for row in resp.json():
        key = row.get("axis") or "null"
        zaehler[key] = zaehler.get(key, 0) + 1
    return zaehler
```

- [ ] **Step 5: Test laufen lassen, gruen sehen**

Run: `python -m pytest tests/test_supabase_db.py -v`
Expected: PASS.

- [ ] **Step 6: Donnerstags-Scrape schreibt die Achse**

In `run_keyword_scrape.py` `scrape_and_persist` ersetzen. Bisher ging alles in einem Upsert mit `source="linkedin_search"` und ohne Achse; jetzt wird je Begriff gescrapt und gruppenweise geschrieben.

```python
def scrape_and_persist(keywords=None, max_posts=20, posted_limit="month",
                       min_virality=5, author_keywords=AUTHOR_KEYWORDS) -> int:
    """Scrape the keyword set and upsert to Supabase (source=linkedin_search).
    Returns rows written. Reused by the CLI and by run_research's weekly cadence.

    Je Begriff ein eigener Upsert, damit die Achse aus axis_for_keyword
    mitgeht. Ohne das schrieb der Donnerstags-Lauf achsenlose Zeilen, die der
    Klassifizierer danach bezahlt nachsortieren musste, obwohl die Herkunft
    bekannt war."""
    ziel = list(keywords or client_keywords())
    gesamt = 0
    for keyword in ziel:
        posts = scrape_keyword_posts(
            [keyword], max_posts=max_posts, posted_limit=posted_limit,
            min_virality=min_virality, author_keywords=author_keywords,
        )
        if not posts:
            continue
        achse = axis_for_keyword(keyword)
        n = upsert_posts(posts, source="linkedin_search", axis=achse)
        print(f"  keyword-scrape '{keyword}': {len(posts)} posts, {n} persisted "
              f"(axis={achse or 'unbekannt'}).")
        gesamt += n
    return gesamt
```

`main()` bleibt unveraendert bis auf den Upsert-Zweig am Ende, der dieselbe Funktion benutzt:

```python
    try:
        n = scrape_and_persist(keywords=keywords, max_posts=args.max_posts,
                               posted_limit=args.posted_limit,
                               min_virality=args.min_virality,
                               author_keywords=args.author_keywords)
        print(f"  Supabase: {n} posts persisted (source=linkedin_search).")
    except Exception as e:
        print(f"  Supabase-Persist fehlgeschlagen: {e}", file=sys.stderr)
        return 1
    return 0
```

Der vorgezogene `scrape_keyword_posts`-Aufruf in `main()` (der die `--no-write`-Vorschau fuettert) bleibt bestehen und wird nur noch fuer `--no-write` gebraucht; er wird deshalb in den `--no-write`-Zweig verschoben, damit ein Schreiblauf nicht doppelt scrapt und doppelt zahlt.

- [ ] **Step 7: Failing test fuer den Klassifizierer**

```python
# tests/test_axis_classifier.py
"""Klassifizierer-Sperren: nur jolly, nur mit Flag. Kein Netz, kein Anthropic-Call."""
import os
import sys
import types

import pytest

os.environ["CLIENT"] = "jolly"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import axis_classifier


def _cfg(name, flags):
    return types.SimpleNamespace(NAME=name, FEATURES=flags)


def test_noop_ohne_flag(monkeypatch):
    def nie(*a, **k):
        raise AssertionError("classify_post darf ohne Flag nicht laufen")
    monkeypatch.setattr(axis_classifier, "classify_post", nie)
    rows = [{"post_url": "https://x/1", "post_text": "irgendwas"}]
    assert axis_classifier.classify_rows(rows, cfg=_cfg("jolly", {})) == {}


def test_harter_abbruch_bei_fremdem_mandanten():
    rows = [{"post_url": "https://x/1", "post_text": "irgendwas"}]
    with pytest.raises(SystemExit) as exc:
        axis_classifier.classify_rows(rows, cfg=_cfg("swot", {"axis_classifier": True}))
    assert "jolly" in str(exc.value)


def test_klassifiziert_und_schreibt_zurueck(monkeypatch):
    monkeypatch.setattr(axis_classifier, "classify_post", lambda text: "ki_im_gtm")
    geschrieben = []
    monkeypatch.setattr(axis_classifier, "set_axis",
                        lambda url, axis: geschrieben.append((url, axis)))
    rows = [{"post_url": "https://x/1", "post_text": "AI SDR Agenten"}]
    ergebnis = axis_classifier.classify_rows(rows, cfg=_cfg("jolly", {"axis_classifier": True}))
    assert ergebnis == {"ki_im_gtm": 1}
    assert geschrieben == [("https://x/1", "ki_im_gtm")]


def test_unbekannte_antwort_wird_null(monkeypatch):
    monkeypatch.setattr(axis_classifier, "classify_post", lambda text: "erfundene_achse")
    geschrieben = []
    monkeypatch.setattr(axis_classifier, "set_axis",
                        lambda url, axis: geschrieben.append((url, axis)))
    rows = [{"post_url": "https://x/9", "post_text": "Rezept fuer Brot"}]
    ergebnis = axis_classifier.classify_rows(rows, cfg=_cfg("jolly", {"axis_classifier": True}))
    assert ergebnis == {"null": 1}
    assert geschrieben == [("https://x/9", None)]
```

- [ ] **Step 8: Test laufen lassen, Fehlschlag sehen**

Run: `python -m pytest tests/test_axis_classifier.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'tools.axis_classifier'`.

- [ ] **Step 9: `tools/axis_classifier.py` schreiben**

```python
"""Themenachse je Post, ein Haiku-Call pro Post.

Nur fuer jolly. Zwei Sperren, beide gemessen noetig (Richard, 22.09.2026):
1. Feature-Flag `axis_classifier` existiert nur in clients/jolly/config.py.
   Fehlt es, ist der Aufruf ein No-Op -- kein stiller Fallback.
2. Direkter Aufruf mit einem anderen Mandanten scheitert hart. SWOT traegt
   seine Achse im source-String und wird von tools/monthly_plan.py gelesen;
   ein fremder Klassifizierer wuerde dort eine zweite Wahrheit anlegen.

'Passt in keine Achse' ist ein Ergebnis, nicht ein Fehlschlag: es wird als
axis=null mit Zeitstempel festgeschrieben und nie neu berechnet.
"""
import json
import sys

from clients import load_client
from tools.anthropic_auth import LazyAnthropic
from tools.supabase_db import set_axis

client = LazyAnthropic()

AXES = (
    "outbound_maschine",
    "daten_und_revops",
    "positionierung_und_angebot",
    "sales_prozess",
    "team_und_enablement",
    "inbound_und_content",
    "bestand_und_expansion",
    "ki_im_gtm",
)

PROMPT = """Ordne diesen LinkedIn-Post genau einer GTM-Themenachse zu.

Achsen:
- outbound_maschine: Sequenzen, Kanalmix, Deliverability, Listen, Trigger
- daten_und_revops: CRM-Hygiene, Forecast, Attribution, Reporting, Stage-Definition
- positionierung_und_angebot: ICP, Offer-Design, Preis, Differenzierung, Messaging
- sales_prozess: Qualifizierung, Discovery, Buying Committee, Einwaende, Verhandlung, Closing
- team_und_enablement: erster Sales-Hire, Ramp, Playbook, Provisionsmodell, fractional vs. intern
- inbound_und_content: LinkedIn-System, Content-Ops, SEO und AEO, Webinare, Lead Magnets
- bestand_und_expansion: Onboarding, Retention, Upsell, Churn-Signale, Customer Success
- ki_im_gtm: AI SDR, Agenten, Recherche-Automatisierung, GTM Engineering

Passt der Post in keine dieser Achsen, antworte mit null. Raten ist falsch:
ein Post ueber Recruiting, Persoenliches oder ein fremdes Fachgebiet ist null.

Post:
{post_text}

Antworte NUR mit JSON: {{"axis": "<achse>"}} oder {{"axis": null}}
"""


def _guard(cfg) -> bool:
    """True heisst laufen. False heisst No-Op. Fremder Mandant heisst Abbruch."""
    if cfg.NAME != "jolly":
        raise SystemExit(
            f"Abbruch: der Achsen-Klassifizierer gilt nur fuer jolly, "
            f"aufgerufen mit '{cfg.NAME}'. SWOT traegt die Achse im "
            f"source-String (tools/monthly_plan.py), lisocon hat kein "
            f"Topic-Mining. Kein stiller Fallback."
        )
    return bool(cfg.FEATURES.get("axis_classifier"))


def classify_post(post_text: str) -> str | None:
    """Eine Achse oder None. Jeder Fehler ist None: eine falsche Achse ist
    teurer als keine, weil der Deckel danach am falschen Wert sperrt."""
    text = (post_text or "").strip()
    if len(text) < 80:
        return None
    try:
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=64,
            messages=[{"role": "user", "content": PROMPT.format(post_text=text[:4000])}],
        )
        raw = resp.content[0].text.strip()
        start, end = raw.find("{"), raw.rfind("}")
        achse = json.loads(raw[start:end + 1]).get("axis")
    except Exception as e:
        print(f"  Achsen-Call fehlgeschlagen: {e}", file=sys.stderr)
        return None
    return achse if achse in AXES else None


def classify_rows(rows: list, cfg=None) -> dict:
    """Klassifiziert die uebergebenen Zeilen und schreibt jede Entscheidung
    zurueck. Gibt {achse: anzahl} zurueck, 'null' fuer 'passt in keine'."""
    cfg = cfg or load_client()
    if not _guard(cfg):
        return {}
    zaehler = {}
    for row in rows:
        url = row.get("post_url")
        if not url:
            continue
        achse = classify_post(row.get("post_text", ""))
        set_axis(url, achse)
        key = achse or "null"
        zaehler[key] = zaehler.get(key, 0) + 1
    return zaehler
```

- [ ] **Step 10: Flag in jollys Config setzen**

`clients/jolly/config.py:177-181`:

```python
FEATURES = {
    "supabase_persist": True,   # Rohdaten fuer das woechentliche Blog-Topic-Mining
    "keyword_scrape": True,     # Donnerstag: Keyword-Scrape fuer Jolly-Blog-Themen
    "topic_mining": True,       # Freitag: Blog-Topic-Clustering
    "axis_classifier": True,    # Haiku sortiert Profil-/Substack-Posts auf Themenachsen
}
```

- [ ] **Step 11: Test laufen lassen, gruen sehen**

Run: `python -m pytest tests/test_axis_classifier.py tests/test_client_module_imports.py -v`
Expected: PASS.

- [ ] **Step 12: Backfill-Skript schreiben**

```python
# scripts/backfill_axes.py
"""Achsen-Backfill fuer jollys Pool. Nur Zeilen ohne Achsen-Entscheidung.

    python scripts/backfill_axes.py --days 90 --limit 20   # Messlauf
    python scripts/backfill_axes.py --days 90              # voller Lauf
    python scripts/backfill_axes.py --report-only          # nur Verteilung

Kosten: ein Haiku-Call je Zeile. 736 Zeilen liegen unter 1 EUR (Schaetzung
Spec 2026-09-22), der Messlauf mit --limit 20 belegt das vorher.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from clients import load_client
from tools.axis_classifier import classify_rows
from tools.supabase_db import axis_distribution, get_unclassified_posts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=90)
    ap.add_argument("--limit", type=int, default=500)
    ap.add_argument("--report-only", action="store_true",
                    help="nur die Verteilung zeigen, nichts klassifizieren")
    args = ap.parse_args()

    cfg = load_client()
    print(f"Client: {cfg.NAME} | Fenster: {args.days} Tage")

    if not args.report_only:
        rows = get_unclassified_posts(args.days, limit=args.limit)
        print(f"{len(rows)} Zeilen ohne Achse. Klassifiziere ...", flush=True)
        ergebnis = classify_rows(rows, cfg=cfg)
        if not ergebnis:
            print("  Kein Lauf: FEATURES['axis_classifier'] ist nicht gesetzt.")
        for achse, n in sorted(ergebnis.items(), key=lambda x: -x[1]):
            print(f"  {achse}: {n}")

    print(f"\nVerteilung im Pool ({args.days} Tage):")
    verteilung = axis_distribution(args.days)
    summe = sum(verteilung.values()) or 1
    for achse, n in sorted(verteilung.items(), key=lambda x: -x[1]):
        print(f"  {achse}: {n} ({100 * n // summe} Prozent)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 13: Messlauf, dann voller Backfill**

Run: `python scripts/backfill_axes.py --days 90 --limit 20`
Expected: 20 Zeilen klassifiziert, Verteilung ueber mindestens drei Achsen. Kommt alles als `null` zurueck, ist der Prompt oder der Textzugriff kaputt, nicht der Pool: dann anhalten, nicht durchlaufen lassen.

Danach: `python scripts/backfill_axes.py --days 90`
Expected: die restlichen Zeilen der 90 Tage, Verteilungsbericht als Ausgangswert. Die Zahl wird in die Spec-Messsektion nachgetragen.

- [ ] **Step 14: Commit**

```bash
git add scripts/2026-09-22-add-axis-column.sql scripts/backfill_axes.py \
        tools/axis_classifier.py tools/supabase_db.py clients/jolly/config.py \
        run_keyword_scrape.py tests/test_axis_classifier.py tests/test_supabase_db.py
git commit -F .git/COMMIT_EDITMSG_axes
```

Commit-Text:

```
feat(jolly): Achsen-Spalte, Klassifizierer und Backfill

axis plus axis_classified_at in influencer_posts, nullable. Achsen-Scrape
und Donnerstags-Keyword-Scrape schreiben die Herkunft direkt, Profil- und
Substack-Zeilen bekommen sie von Haiku. Klassifizierer laeuft nur bei
jolly: Flag fehlt heisst No-Op, fremder Mandant heisst Abbruch.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

### Task 3: Deckel in der Auswahl und Pool-Rueckgriff

**Files:**
- Create: `scripts/add_achse_property.py`
- Create: `tools/axis_gate.py`
- Modify: `tools/notion_db.py` (neue `get_recent_axes` hinter `get_recent_personas`, Zeile 823)
- Modify: `run_research.py:222-260` (Deckel und Rueckgriff), `run_research.py:458-472` (Achse schreiben)
- Test: `tests/test_axis_gate.py`

**Interfaces:**
- Consumes: `tools.supabase_db.get_posts_since(days) -> list[dict]`, `tools.axis_classifier.AXES`, `tools.notion_db._patch_select_nonfatal(page_id, prop, value)`.
- Produces:
  - `tools.notion_db.get_recent_axes(limit: int = 10) -> list[str]`
  - `tools.axis_gate.blocked_axes(recent: list[str], cap: int = 2) -> set[str]`
  - `tools.axis_gate.free_candidates(posts: list[dict], blocked: set[str]) -> list[dict]`
  - `tools.axis_gate.pool_candidates(rows: list[dict], blocked: set[str], seen_urls: set[str]) -> list[dict]`
  - `tools.axis_gate.axis_of(post: dict) -> str | None`

- [ ] **Step 1: Notion-Property anlegen**

```python
# scripts/add_achse_property.py
"""One-time idempotent: adds an 'Achse' select property (acht GTM-Themenachsen)
to the Jolly Linkedin Content Creation Notion DB. Safe to run repeatedly."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools.notion_db import NOTION_API, NOTION_DB_ID, _headers, _notion_request

OPTIONEN = [
    ("outbound_maschine", "blue"),
    ("daten_und_revops", "green"),
    ("positionierung_und_angebot", "orange"),
    ("sales_prozess", "purple"),
    ("team_und_enablement", "yellow"),
    ("inbound_und_content", "pink"),
    ("bestand_und_expansion", "brown"),
    ("ki_im_gtm", "red"),
]


def ensure_achse_property() -> None:
    r = _notion_request("GET", f"{NOTION_API}/databases/{NOTION_DB_ID}", headers=_headers())
    r.raise_for_status()
    if "Achse" in r.json().get("properties", {}):
        print("Achse property already exists - nothing to do.")
        return

    payload = {"properties": {"Achse": {"select": {
        "options": [{"name": name, "color": color} for name, color in OPTIONEN]}}}}
    r = _notion_request(
        "PATCH", f"{NOTION_API}/databases/{NOTION_DB_ID}", headers=_headers(), json=payload
    )
    r.raise_for_status()
    print(f"Achse property created ({len(OPTIONEN)} Achsen).")


if __name__ == "__main__":
    ensure_achse_property()
```

Run: `python scripts/add_achse_property.py`
Expected: "Achse property created (8 Achsen)." Zweiter Lauf: "already exists".

- [ ] **Step 2: `get_recent_axes` ergaenzen**

In `tools/notion_db.py` direkt hinter `get_recent_personas` (Zeile 823):

```python
def get_recent_axes(limit: int = 10) -> list[str]:
    """Themenachsen der letzten N Eintraege (Deckel: max 2 je Achse im
    Fenster). Tolerant: fehlende Property -> []."""
    return _get_recent_select("Achse", limit)
```

`_get_recent_select` holt bereits ein Fenster von 50 und schneidet erst nach dem Filtern zu, also verkuerzen Altposts ohne `Achse` das Fenster nicht.

- [ ] **Step 3: Failing test fuer die Auswahllogik**

```python
# tests/test_axis_gate.py
"""Achsen-Deckel und Pool-Rueckgriff. Reine Logik, kein Netz."""
import os
import sys

os.environ["CLIENT"] = "jolly"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.axis_gate import axis_of, blocked_axes, free_candidates, pool_candidates


def test_zwei_vorkommen_sperren():
    recent = ["daten_und_revops", "outbound_maschine", "daten_und_revops"]
    assert blocked_axes(recent) == {"daten_und_revops"}


def test_ein_vorkommen_sperrt_nicht():
    assert blocked_axes(["daten_und_revops", "outbound_maschine"]) == set()


def test_null_wird_nie_gesperrt():
    recent = ["null", "null", "null", "daten_und_revops"]
    assert blocked_axes(recent) == set()


def test_leeres_fenster_sperrt_nichts():
    assert blocked_axes([]) == set()


def test_kandidaten_ohne_achse_bleiben_drin():
    posts = [
        {"post_url": "a", "axis": "daten_und_revops"},
        {"post_url": "b", "axis": None},
        {"post_url": "c", "axis": "ki_im_gtm"},
    ]
    frei = free_candidates(posts, {"daten_und_revops"})
    assert [p["post_url"] for p in frei] == ["b", "c"]


def test_alles_gesperrt_gibt_leere_liste():
    posts = [{"post_url": "a", "axis": "ki_im_gtm"}]
    assert free_candidates(posts, {"ki_im_gtm"}) == []


def test_pool_zieht_nur_freie_achsen_und_ueberspringt_gesehene():
    rows = [
        {"post_url": "a", "axis": "daten_und_revops", "post_text": "x" * 300},
        {"post_url": "b", "axis": "ki_im_gtm", "post_text": "x" * 300},
        {"post_url": "c", "axis": "ki_im_gtm", "post_text": "x" * 300},
        {"post_url": "d", "axis": None, "post_text": "x" * 300},
    ]
    kandidaten = pool_candidates(rows, {"daten_und_revops"}, seen_urls={"c"})
    assert [r["post_url"] for r in kandidaten] == ["b", "d"]


def test_pool_verwirft_zu_kurze_texte():
    rows = [{"post_url": "a", "axis": "ki_im_gtm", "post_text": "kurz"}]
    assert pool_candidates(rows, set(), seen_urls=set()) == []


def test_axis_of_liest_beide_schreibweisen():
    assert axis_of({"axis": "ki_im_gtm"}) == "ki_im_gtm"
    assert axis_of({"source": "linkedin_search:sales_prozess"}) == "sales_prozess"
    assert axis_of({"source": "linkedin"}) is None
    assert axis_of({}) is None
```

- [ ] **Step 4: Test laufen lassen, Fehlschlag sehen**

Run: `python -m pytest tests/test_axis_gate.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'tools.axis_gate'`.

- [ ] **Step 5: `tools/axis_gate.py` schreiben**

```python
"""Achsen-Deckel fuer die Tages-Auswahl.

Reine Funktionen, kein Netz: run_research.py holt das Fenster aus Notion und
den Pool aus Supabase und gibt beides hier hinein. Der Deckel wirkt auf der
Ausgabeseite, weil 81 Prozent von jollys Pool Profil-Scrape ohne
Achsen-Herkunft sind (gemessen 22.09.2026) -- eine Mischregel beim Scrapen
allein erreicht diese Zeilen nicht.
"""
CAP = 2
MIN_POOL_TEXT = 200

_AXIS_SOURCE_PREFIX = "linkedin_search:"


def axis_of(post: dict) -> str | None:
    """Achse einer Zeile. Spalte `axis` gewinnt, danach der source-Prefix
    (Zeilen aus run_axis_scrape.py vor dem Backfill)."""
    achse = post.get("axis")
    if achse:
        return achse
    source = post.get("source", "") or ""
    if source.startswith(_AXIS_SOURCE_PREFIX):
        rest = source[len(_AXIS_SOURCE_PREFIX):].strip()
        return rest or None
    return None


def blocked_axes(recent: list, cap: int = CAP) -> set:
    """Achsen, die im Fenster schon `cap` mal vorkommen. 'null' zaehlt nie:
    ein Post ohne Achse darf keine Achse sperren."""
    zaehler = {}
    for achse in recent:
        if not achse or achse == "null":
            continue
        zaehler[achse] = zaehler.get(achse, 0) + 1
    return {a for a, n in zaehler.items() if n >= cap}


def free_candidates(posts: list, blocked: set) -> list:
    """Kandidaten ausserhalb der gesperrten Achsen. Reihenfolge bleibt, der
    Aufrufer hat schon nach Score sortiert. axis=None gilt als frei."""
    return [p for p in posts if axis_of(p) not in blocked]


def pool_candidates(rows: list, blocked: set, seen_urls: set) -> list:
    """Supabase-Zeilen, die als Rueckgriff taugen: freie Achse, nicht schon
    gesehen, genug Text zum Scoren."""
    raus = []
    for row in rows:
        url = row.get("post_url")
        if not url or url in seen_urls:
            continue
        if axis_of(row) in blocked:
            continue
        if len(row.get("post_text", "") or "") < MIN_POOL_TEXT:
            continue
        raus.append(row)
    return raus
```

- [ ] **Step 6: Test laufen lassen, gruen sehen**

Run: `python -m pytest tests/test_axis_gate.py -v`
Expected: PASS, 9 Tests.

- [ ] **Step 7: Deckel in `run_research.py` einhaengen**

Import-Block ergaenzen (bei den `tools.notion_db`-Importen, `run_research.py:31-42`): `get_recent_axes`. Bei den Supabase-Importen (`run_research.py:81`): `from tools.supabase_db import get_posts_since, upsert_posts`. Neu: `from tools.axis_gate import axis_of, blocked_axes, free_candidates, pool_candidates`.

Zwischen Schritt 3 und der Winner-Wahl (`run_research.py:222`) einsetzen. Der bisherige `winner = scored[0] if ...`-Ausdruck wird ersetzt:

```python
    # Schritt 3.5: Achsen-Deckel. Jede Achse mit CAP Vorkommen im Fenster der
    # letzten 10 Notion-Posts ist gesperrt (Spec 2026-09-22). Non-fatal: ohne
    # Fenster laeuft der Tag wie vorher, ein leeres Fenster sperrt nichts.
    gesperrt = set()
    try:
        recent_axes = get_recent_axes(10)
        gesperrt = blocked_axes(recent_axes)
        print(f"  Achsen zuletzt: {recent_axes}")
        print(f"  Gesperrt: {sorted(gesperrt) or 'keine'}")
    except Exception as e:
        print(f"  Achsen-Fenster laden fehlgeschlagen (nicht kritisch): {e}", file=sys.stderr)

    kandidaten = free_candidates(scored, gesperrt)
    if gesperrt:
        je_achse = {}
        for p in scored:
            key = axis_of(p) or "null"
            je_achse[key] = je_achse.get(key, 0) + 1
        print(f"  Kandidaten je Achse: {je_achse}, frei: {len(kandidaten)}/{len(scored)}")

    # Schritt 3.6: Rueckgriff auf den Supabase-Pool, wenn der Deckel alles
    # wegnimmt. Zieht bis zu 7 Tage alte Posts -- das Tagesfenster ist 6-36h.
    # Bei jolly haengt kein Format an Aktualitaet, deshalb akzeptiert.
    if not kandidaten:
        print("  Deckel nimmt alle Tages-Kandidaten. Rueckgriff auf den Pool ...")
        try:
            rows = get_posts_since(7)
            seen = set(existing_urls) | {p["post_url"] for p in new_posts}
            pool = pool_candidates(rows, gesperrt, seen)
            print(f"  Pool: {len(rows)} Zeilen, {len(pool)} nach Deckel und Dedup.")
            if pool:
                pool_posts = [{"post_url": r["post_url"],
                               "post_text": r.get("post_text", ""),
                               "post_excerpt": (r.get("post_text", "") or "")[:300],
                               "influencer": r.get("influencer", ""),
                               "date": f"{r.get('post_date') or ''}T00:00:00Z",
                               "source": r.get("source", "linkedin"),
                               "axis": r.get("axis"),
                               "engagement": {"likes": r.get("likes", 0),
                                              "comments": r.get("comments", 0),
                                              "shares": r.get("shares", 0)}}
                              for r in pool]
                kandidaten = score_posts(pool_posts, recent_drafts=recent_drafts)
                for p in kandidaten[:3]:
                    print(f"  Pool [{p['score']}/{MAX_SCORE}] {p['influencer']}")
        except Exception as e:
            print(f"  Pool-Rueckgriff fehlgeschlagen (nicht kritisch): {e}", file=sys.stderr)

    if not kandidaten:
        print(f"\n  Kein Kandidat nach Achsen-Deckel (gesperrt: {sorted(gesperrt)}) "
              f"und leerer Pool. Run beendet ohne Entwurf.")
        return

    # Schritt 4: Winner waehlen
    winner = kandidaten[0] if kandidaten[0]["score"] >= MIN_SCORE else None
    if not winner:
        print(f"\n  Kein Post erreicht Mindest-Score {MIN_SCORE}/{MAX_SCORE} "
              f"(bester: {kandidaten[0]['score']}). Run beendet.")
        return
```

Die Box-Auswahl darunter (`run_research.py:243`) liest weiter aus derselben Liste, arbeitet aber auf den Kandidaten statt auf `scored`:

```python
        eligible = [p for p in kandidaten[:10] if p["score"] >= MIN_SCORE]
```

Der Rest von Schritt 4.35 bis Schritt 7 bleibt unangetastet: Matrix-Box, Format, Persona, Asset, Hook laufen unveraendert weiter.

- [ ] **Step 8: Achse in Notion schreiben**

Nach dem `update_with_draft`-Aufruf (`run_research.py:472`, direkt vor `print(f"  Done: ...")`) ergaenzen. Der Import kommt zu den `tools.notion_db`-Importen: `_patch_select_nonfatal`.

```python
        achse = axis_of(winner)
        if achse:
            _patch_select_nonfatal(page_id, "Achse", achse)
            print(f"  Achse: {achse}")
```

Non-fatal wie die anderen Selects: eine fehlende Property darf den fertigen Entwurf nicht verwerfen.

- [ ] **Step 9: Volle Testsuite**

Run: `python -m pytest tests/ -q`
Expected: PASS. Die Tests fuer Format, Persona und Matrix (`tests/test_pick_format.py`, `tests/test_persona_and_assets.py`, `tests/test_content_matrix.py`, `tests/test_rank_box_fit.py`) bleiben unveraendert gruen, weil der Deckel vor ihnen greift und ihre Eingaben nicht umbaut.

- [ ] **Step 10: Trockenlauf gegen Notion und Supabase**

Run: `python -c "from tools.notion_db import get_recent_axes; print(get_recent_axes(10))"`
Expected: eine Liste, direkt nach Task 3 noch leer (`[]`), weil erst neue Entwuerfe die Property fuellen. Eine Ausnahme hier heisst, die Property fehlt oder heisst anders.

- [ ] **Step 11: Commit**

```bash
git add scripts/add_achse_property.py tools/axis_gate.py tools/notion_db.py \
        run_research.py tests/test_axis_gate.py
git commit -F .git/COMMIT_EDITMSG_axes
```

Commit-Text:

```
feat(jolly): Achsen-Deckel und Pool-Rueckgriff in der Tages-Auswahl

Notion-Select Achse, get_recent_axes(10), max 2 je Achse im Fenster.
Nimmt der Deckel alle Tages-Kandidaten, scort run_research den
Supabase-Pool der letzten 7 Tage auf freien Achsen nach; ist auch der
leer, endet der Lauf ohne Entwurf und protokolliert die Sperre.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

### Task 4: Rahmen oeffnen

Ohne diesen Task wirkt der Deckel nicht: achsenfremde Posts bekommen bei `topic_fit` so wenig, dass sie `MIN_SCORE` nie erreichen und nie in die Auswahl kommen.

**Files:**
- Modify: `clients/jolly/config.py:29-31` (VOC-Anweisung), `clients/jolly/config.py:65` (`TOPIC_FIT_QUESTION`)
- Test: `tests/test_client_matrix_config.py` (Erweiterung)

**Interfaces:**
- Consumes: `clients.jolly.config.KEYWORDS_BY_AXIS` aus Task 1 (die acht Achsen als Text in der Frage).
- Produces: nichts Aufrufbares. `TOKENS["TOPIC_FIT_QUESTION"]` bleibt ein String, nur breiter.

- [ ] **Step 1: Failing test schreiben**

An `tests/test_client_matrix_config.py` anhaengen:

```python
def test_topic_fit_frage_deckt_alle_achsen():
    """Der Achsen-Deckel kann nur wirken, wenn achsenfremde Posts ueberhaupt
    topic_fit bekommen. Die Frage nennt deshalb jedes der acht Felder."""
    import os
    os.environ["CLIENT"] = "jolly"
    from clients import load_client
    load_client.cache_clear()
    cfg = load_client()
    frage = cfg.TOKENS["TOPIC_FIT_QUESTION"].lower()
    for begriff in ("outbound", "revops", "positionierung", "sales-prozess",
                    "enablement", "content", "bestandskunden", "ki"):
        assert begriff in frage, f"{begriff} fehlt in TOPIC_FIT_QUESTION"


def test_voc_block_erzwingt_keinen_rahmen_mehr():
    import os
    os.environ["CLIENT"] = "jolly"
    from clients import load_client
    load_client.cache_clear()
    cfg = load_client()
    doc = cfg.__doc__ or ""
    assert "generierte" not in doc.split("VOC-EVIDENZ")[1].split("BIG IDEA")[0].lower() \
        or "bevorzugt in diesen Problem-Rahmen" not in doc
    # Harte VOC-Regeln bleiben wortgleich stehen.
    assert 'NIE "Kaltakquise ist tot" schreiben' in doc
    assert "US-Zahlen und Dollar-Betraege nie als DACH-Fakt" in doc
    assert "NIE Anbieter- oder Agenturnamen nennen" in doc
```

- [ ] **Step 2: Test laufen lassen, Fehlschlag sehen**

Run: `python -m pytest tests/test_client_matrix_config.py -v`
Expected: FAIL im ersten neuen Test, "enablement fehlt in TOPIC_FIT_QUESTION".

- [ ] **Step 3: `TOPIC_FIT_QUESTION` umformulieren**

`clients/jolly/config.py:65` ersetzen:

```python
    "TOPIC_FIT_QUESTION": "Passt das Thema in eines dieser acht GTM-Felder: Outbound-Maschine (Sequenzen, Kanalmix, Deliverability, Listen, Trigger), Daten und RevOps (CRM, Forecast, Attribution, Reporting), Positionierung und Angebot (ICP, Offer, Preis, Messaging), Sales-Prozess (Qualifizierung, Discovery, Buying Committee, Einwaende, Closing), Team und Enablement (erster Sales-Hire, Ramp, Playbook, Provision), Inbound und Content (LinkedIn, Content-Ops, SEO und AEO, Lead Magnets), Bestandskunden und Expansion (Onboarding, Retention, Upsell, Churn), KI im GTM (AI SDR, Agenten, Recherche-Automatisierung, GTM Engineering)? Ein konkreter Tipp oder eine Anleitung aus einem dieser Felder zaehlt voll, auch ohne Strategie-Rahmen.",
```

- [ ] **Step 4: VOC-Anweisung entschaerfen**

`clients/jolly/config.py:29-31`. Alt:

```
VOC-EVIDENZ (Run 1 2026-07, 157 verifizierte Praktiker-Zitate): die belegten Kaufprobleme des ICP.
Posts, die auf eines davon einzahlen, bei topic_fit und icp_relevanz hoeher bewerten; generierte
Posts bevorzugt in diesen Problem-Rahmen setzen:
```

Neu:

```
VOC-EVIDENZ (Run 1 2026-07, 157 verifizierte Praktiker-Zitate): die belegten Kaufprobleme des ICP.
Sie sind Bewertungshilfe, kein Pflicht-Rahmen (Richard 22.09.2026): ein Post, der auf eines davon
einzahlt, ist stark, aber ein konkreter Tipp aus einem anderen GTM-Feld ist nicht schwaecher und
darf NICHT in einen dieser Rahmen gebogen werden. Die harten Regeln darunter gelten unveraendert:
```

`BIG IDEA` bleibt Wort fuer Wort stehen: das Franchise-Dach traegt weiter jeden Post, es schreibt nur kein Thema mehr vor. `FEINDBILD` bleibt unveraendert, es haengt an den vier Rahmen und greift nur, wenn einer davon gespielt wird.

- [ ] **Step 5: Test laufen lassen, gruen sehen**

Run: `python -m pytest tests/test_client_matrix_config.py tests/test_copy_rules.py tests/test_scoring_classify.py -v`
Expected: PASS.

- [ ] **Step 6: Volle Suite**

Run: `python -m pytest tests/ -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add clients/jolly/config.py tests/test_client_matrix_config.py
git commit -F .git/COMMIT_EDITMSG_axes
```

Commit-Text:

```
feat(jolly): TOPIC_FIT_QUESTION auf acht Achsen, VOC-Rahmen nicht mehr Pflicht

Ohne das erreicht ein achsenfremder Post MIN_SCORE nie und der Deckel
sperrt gegen eine leere Kandidatenliste. Harte VOC-Regeln und BIG IDEA
bleiben wortgleich.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

### Task 5: Achsen-Scrape messen und freigeben

**Files:**
- Modify: keine Code-Datei. `run_axis_scrape.py` liest `KEYWORDS_BY_AXIS` schon per `getattr` und braucht nach Task 1 keine Aenderung.
- Modify: `docs/superpowers/specs/2026-09-22-jolly-themenachsen-design.md` (Kostensektion mit der gemessenen Zahl)

**Interfaces:**
- Consumes: `run_axis_scrape.run(axes=None, max_posts, min_virality, posted_limit, write, cfg) -> dict`.
- Produces: nichts.

- [ ] **Step 1: Trockenlauf ohne Kosten**

Run: `python run_axis_scrape.py --axes team_und_enablement --max-posts 5 --no-write`
Expected: Ausgabe "=== team_und_enablement: 6 Begriffe, max 5/Begriff, Boden 5 ===" und eine Post-Zahl. Das ist ein bezahlter Apify-Lauf, aber der kleinste sinnvolle: 6 Begriffe mal 5 Posts.

Vor diesem Lauf den Apify-Budget-Guard beachten: geschaetzte Kosten nennen, Freigabe von Richard einholen (Regel "Geldausgaben genehmigen", Schwelle 1 EUR).

- [ ] **Step 2: Hochrechnung und Freigabe**

Aus der Post-Zahl des Messlaufs die Kosten fuer alle acht Achsen hochrechnen: etwa 54 Begriffe mal `--max-posts`. Die Zahl geht mit der Hochrechnung an Richard. Ohne seine Freigabe kein voller Lauf.

- [ ] **Step 3: Erster voller Achsen-Scrape**

Run: `python run_axis_scrape.py --min-virality 2`
Expected: acht Bloecke, je Achse eine Zeilenzahl, Summe am Ende. `--min-virality 2` statt 5, weil Apify jeden gelieferten Post abrechnet und der Filter erst danach greift: ein niedriger Boden holt mehr aus demselben bezahlten Material.

- [ ] **Step 4: Verteilung nachlesen**

Run: `python scripts/backfill_axes.py --days 30 --report-only`
Expected: alle acht Achsen vertreten. Eine Achse bei 0 heisst, ihre Begriffe liefern auf LinkedIn nichts: dann Begriffe nachschaerfen, nicht den Deckel senken.

- [ ] **Step 5: Kostensektion der Spec nachtragen und committen**

```bash
git add docs/superpowers/specs/2026-09-22-jolly-themenachsen-design.md
git commit -F .git/COMMIT_EDITMSG_axes
```

Commit-Text:

```
docs: gemessene Apify-Kosten des Achsen-Scrapes nachgetragen

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

### Task 6: Nachmessen

**Files:**
- Modify: `docs/superpowers/specs/2026-09-22-jolly-themenachsen-design.md` (Messsektion)

**Interfaces:**
- Consumes: `tools.notion_db.get_recent_axes(limit)` aus Task 3, `tools.supabase_db.axis_distribution(days)` aus Task 2.
- Produces: nichts.

- [ ] **Step 1: Ausgabeseite zaehlen, sobald 10 neue Entwuerfe stehen**

Run: `python -c "from tools.notion_db import get_recent_axes; from collections import Counter; print(Counter(get_recent_axes(10)))"`
Expected: keine Achse ueber 2, mindestens 5 der 8 Achsen vertreten. Das ist das Erfolgskriterium der Spec.

- [ ] **Step 2: Angebotsseite gegenlesen**

Run: `python scripts/backfill_axes.py --days 30 --report-only`
Expected: die Verteilung des Pools. Reisst die Ausgabeseite das Kriterium, zeigt dieser Bericht, ob der Pool oder die Auswahl die Ursache ist.

- [ ] **Step 3: Ergebnis in die Spec und committen**

Zahlen mit Datum in die Messsektion der Spec, dann:

```bash
git add docs/superpowers/specs/2026-09-22-jolly-themenachsen-design.md
git commit -F .git/COMMIT_EDITMSG_axes
```

Commit-Text:

```
docs: Achsen-Verteilung nach 10 Posts gemessen

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

## Self-Review

**Spec-Abdeckung:** Teil A der Spec liegt in Task 1 und Task 2 (KEYWORDS_BY_AXIS, abgeleitete JOLLY_KEYWORDS, Spalte `axis`, drei Schreibwege, Klassifizierer mit beiden Sperren). Teil B liegt in Task 3 (Notion-Select, `get_recent_axes`, Deckel, Pool-Rueckgriff, Lauf-Ende ohne Entwurf). Teil C liegt in Task 4. Die Messsektion liegt in Task 2 Step 13 (Backfill der 90 Tage) und Task 6. Die Kostensektion liegt in Task 5. Alle sechs Punkte der Spec-Reihenfolge haben einen Task.

**Offene Luecke gegen die Spec, bewusst:** die Spec nennt "Die 40 handklassifizierten Drafts laufen durch denselben Klassifizierer". Der Klassifizierer liest Supabase-Zeilen, die Drafts liegen in Notion und sind eigener Text, nicht Quell-Posts. Der Ausgangswert bleibt deshalb die Handklassifikation vom 22.09.2026, die in der Spec-Tabelle steht; ein zweiter Durchlauf desselben Materials durch Haiku waere ein neuer Zahlenstand ohne neuen Erkenntniswert. Task 6 vergleicht die neuen 10 Posts gegen die Handtabelle.

**Typ-Konsistenz:** `axis_of`, `blocked_axes`, `free_candidates`, `pool_candidates` heissen in Task 3 ueberall gleich. `upsert_posts(posts, source, axis=None)` wird in Task 2 definiert und in Task 2 Step 6 mit genau dieser Signatur gerufen. `axis_for_keyword` wird in Task 1 definiert und in Task 2 Step 6 importiert; der Import gehoert in denselben Modulkopf (`run_keyword_scrape.py` definiert die Funktion selbst, also kein Import noetig). `set_axis(post_url, axis)` wird in Task 2 definiert und im selben Task in `classify_rows` gerufen.

**Reihenfolge-Abhaengigkeit:** Task 2 Step 6 ruft `axis_for_keyword` aus Task 1. Task 3 Step 7 liest `axis` aus Zeilen, die Task 2 gefuellt hat; laeuft Task 3 vor dem Backfill, ist jede Achse `None`, der Deckel sperrt nichts und der Lauf verhaelt sich wie heute. Kein harter Bruch, aber Task 2 gehoert vor Task 3.
