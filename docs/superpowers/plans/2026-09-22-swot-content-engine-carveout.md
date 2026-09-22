# SWOT Content Engine Carve-out Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Den SWOT-Mandanten der LinkedIn Content Creation Engine als eigenstaendiges Repo `swot-linkedin-content-engine` herauslösen, das SWOT auf eigenen Konten (Anthropic, Apify, kie.ai, Supabase, Notion) betreibt, inklusive Datenmigration und einmaliger Uebergabe ueber ein privates GitHub-Repo.

**Architecture:** Kopie des Multi-Tenant-Motors ohne Jolly- und Lisocon-Anteile, Tenant-Loader bleibt mit Default `swot`. Einziger Motor-Umbau: Bild-Upload nach Supabase Storage statt GitHub, neuer Einstieg `run_comment_drafts.py`, Env-Namen ohne `_SWOT`-Suffix, DB-IDs nur aus der Env. Die Migration (Supabase-Zeilen, Bilder, Notion-Kopien) laeuft ueber Einmalskripte, die im Jolly-Quellrepo unter `scripts/swot_carveout/` liegen und NIE ins Zielrepo wandern.

**Tech Stack:** Python 3.12, requests, python-dotenv, anthropic 0.84.0, apify-client 3.0.2, pillow, feedparser, pytest. Supabase PostgREST + Storage REST, Notion REST API 2022-06-28, Git, GitHub CLI `gh`.

**Spec:** `C:\Users\richa\Jolly_Claude_Code\Jolly Automations\Jolly Linkedin Content Creation\docs\superpowers\specs\2026-09-22-swot-content-engine-carveout-design.md`

## Global Constraints

- Quellrepo (nur lesen, bis auf `scripts/swot_carveout/` und diesen Plan): `C:\Users\richa\Jolly_Claude_Code\Jolly Automations\Jolly Linkedin Content Creation`. Dort liegen fremde uncommittete Aenderungen einer Parallelsession: nur eigene Dateien per explizitem Pfad committen, nie `git add -A`.
- Zielrepo: `C:\Users\richa\Jolly_Claude_Code\Clients\SWOT\swot-linkedin-content-engine`. GitHub `jollymarketer/swot-linkedin-content-engine`, privat. Vor der Uebergabe genau EIN Commit (`git log --oneline | wc -l` = 1). Zwischen-Commits sind lokal erlaubt und werden in Task 14 zu einem Orphan-Commit zusammengefasst, bevor je gepusht wird.
- Env-Namen im Zielrepo: `ANTHROPIC_API_KEY`, `APIFY_API_KEY`, `KIEAI_API_KEY`, `NOTION_TOKEN`, `NOTION_DB_ID`, `TOPIC_IDEAS_DB_ID`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `MAKE_REVIEW_WEBHOOK` (optional). Nichts anderes. `APIFY_ACCOUNT = "kueswot"` bleibt.
- `NOTION_DB_ID` ist im Zielrepo die Redaktionsplan-Kopie. `CONTENT_PLAN_DB_ID` in `clients/swot/config.py` liest denselben Env-Wert (`os.getenv("NOTION_DB_ID", "")`). Grund: Kommentar-Dedup (`get_comment_target_urls`) und Kommentar-Zeilen laufen ueber `NOTION_DB_ID`, der Redaktionsplan hat die Property `Kommentar-Ziel` bereits.
- Bild-URLs: ausschliesslich `<SUPABASE_URL>/storage/v1/object/public/post-images/<yyyy-mm>/<dateiname>.png`. Kein GitHub, kein catbox, kein kie.ai-Fallback. Upload-Fehler bricht den Lauf ab.
- Verbotene Strings im Zielrepo (Verifikation 7.2): `grep -ri "richa\|Jolly_Claude_Code\|lisocon\|sonocrete\|jollymarketer\|_SWOT\|obsidian" --exclude-dir=.git` = 0 Treffer.
- Datei-Edits nur per Edit/Write-Tool, nie per Bash-Heredoc (CRLF/Backslash-Mangling). Commit-Messages per `git commit -F <datei>`.
- Secrets nie ausgeben. Kein Send an Externe, kein Push vor Task 14.
- Kosten: Task 13 (Probe-Laeufe) verursacht einen kie.ai-Bildlauf (~0,10 USD) und einen Apify-Lauf (~0,05 USD) plus wenige Sonnet-Calls. Bereits im Spec freigegeben (Verifikation 7.4 und 7.5). Sonst keine Ausgaben.
- Loeschungen im Jolly-Bestand (Task 15) erst nach schriftlicher Bestaetigung von SWOT.

---

## Dateiuebersicht

Zielrepo (neu oder geaendert gegenueber der Kopie):

- `clients/__init__.py`: Default `swot`.
- `run_keyword_scrape.py`: Default `swot`.
- `clients/swot/config.py`: `_TOKEN_ENV`-Zeilen weg, `TOPIC_IDEAS_DB_ID_DEFAULT` weg, `CONTENT_PLAN_DB_ID` aus Env, Kommentare bereinigt.
- `tools/kieai_image.py`: `_upload_to_storage`, GitHub/catbox geloescht, Logo-Default `swot_logo.png`.
- `tools/comment_drafts.py`: `run_comment_drafts(cfg=None, now=None, force=False, writer=None)`.
- `run_comment_drafts.py`: neu, CLI mit `--force`, Schreiber `create_plan_comment_entry`.
- `tools/system_check.py`: `check_storage`, Docstring ohne Railway/lisocon.
- `scripts/revision_next.py`: Protokoll nach `workspace/pruefberichte/`.
- `db/schema.sql`, `db/storage.sql`: neu.
- `README.md`, `SETUP.md`, `.env.example`, `.gitignore`, `.gitlab-ci.yml`, `docs/migration-2026-09.md`: neu.
- `tests/test_image_storage_upload.py`, `tests/test_client_default.py`, `tests/test_run_comment_drafts.py`, `tests/test_system_check_storage.py`: neu. `tests/test_image_upload_branch.py`: geloescht. Weitere Tests: angepasst oder geloescht (Task 1, 3).

Quellrepo (Jolly, nur Migrationswerkzeug):

- `scripts/swot_carveout/copy_supabase_rows.py`
- `scripts/swot_carveout/migrate_images.py`
- `scripts/swot_carveout/rewrite_notion_image_urls.py`
- `scripts/swot_carveout/readback.py`

---

### Task 1: Zielrepo anlegen, Kopie mit Ausschlussliste, Testbaseline

**Files:**
- Create: `C:\Users\richa\Jolly_Claude_Code\Clients\SWOT\swot-linkedin-content-engine\` (Kopie)
- Create: `swot-linkedin-content-engine\.gitignore`
- Delete (im Ziel): siehe Schritt 3

**Interfaces:**
- Produces: das Zielrepo als lauffaehige Kopie. Alle folgenden Tasks arbeiten dort. Arbeitsverzeichnis fuer alle Bash-Befehle ab jetzt: `cd "C:/Users/richa/Jolly_Claude_Code/Clients/SWOT/swot-linkedin-content-engine"`, sofern nicht anders genannt.

- [ ] **Step 1: Ziel pruefen, dann kopieren**

```bash
test ! -e "C:/Users/richa/Jolly_Claude_Code/Clients/SWOT/swot-linkedin-content-engine" && echo "frei"
SRC="C:/Users/richa/Jolly_Claude_Code/Jolly Automations/Jolly Linkedin Content Creation"
DST="C:/Users/richa/Jolly_Claude_Code/Clients/SWOT/swot-linkedin-content-engine"
mkdir -p "$DST"
cd "$SRC" && cp -r clients tools tests workflows db scripts Resources requirements.txt \
  run_axis_scrape.py run_image_eval.py run_image_fill.py run_keyword_scrape.py \
  run_monthly_plan.py run_plan_fill.py run_review_backfill.py run_source_scrape.py \
  run_topic_mining.py run_verworfen_sync.py "$DST/"
```

Erwartet: "frei" vor dem Kopieren. Bricht der Test ab, existiert der Ordner schon: STOP, Richard fragen.

- [ ] **Step 2: Jolly-only-Anteile im Ziel loeschen**

```bash
cd "$DST"
rm -rf clients/jolly clients/lisocon clients/sonocrete clients/__pycache__ clients/swot/__pycache__
rm -rf tools/__pycache__ tests/__pycache__ scripts/__pycache__ .pytest_cache
rm -f tools/abm_comment_drafts.py tools/jolly_watchlist.py tools/jolly_watchlist_competitors.py \
      tools/watchlist_db.py tools/engagement_readback.py tools/engagement_stats.py
rm -rf Resources/analytics Resources/transcriptions
ls Resources
```

Erwartet: `ls Resources` zeigt neben `swot_logo.png` weitere Logos. Alle anderen Logos loeschen:

```bash
cd "$DST/Resources" && ls | grep -v "^swot_logo.png$" | xargs -r rm -f && ls
```

Erwartet: genau `swot_logo.png`.

- [ ] **Step 3: scripts/ auf die drei SWOT-Skripte reduzieren, db/migrations entfernen**

```bash
cd "$DST/scripts" && ls | grep -v -E "^(add_plan_fill_properties.py|revision_next.py|measure_diet.py)$" | xargs -r rm -rf && ls
cd "$DST" && rm -rf db/migrations && ls db 2>/dev/null; echo "db leer ok"
```

Erwartet: `scripts/` enthaelt genau drei Dateien. `db/` ist leer oder fehlt (wird in Task 10 gefuellt).

- [ ] **Step 4: `.gitignore` schreiben**

Datei `.gitignore`:

```gitignore
# Secrets
.env
.env.local
.env.*.local
*.pem
*.key

# Python
__pycache__/
*.py[cod]
*.egg-info/
.pytest_cache/
.ruff_cache/
.coverage
.venv/
venv/

# OS / IDE
.DS_Store
Thumbs.db
.vscode/
.idea/

# Laufartefakte
.tmp/
*.log
workspace/_tmp/

# Claude Code / KI-Tooling
.claude/
.cursorrules

# Datenregel: Pruefberichte und Laufprotokolle bleiben lokal, der Bestand
# lebt in Notion und Supabase.
workspace/pruefberichte/
```

- [ ] **Step 5: Git initialisieren und Testbaseline messen**

```bash
cd "$DST" && git init -b main && python -m pytest -q -p no:cacheprovider 2>&1 | tail -15
```

Erwartet: Sammelfehler (`ImportError`/`ModuleNotFoundError`) in Tests, die `run_research`, `run_slate`, `tools.abm_comment_drafts`, `tools.jolly_watchlist`, `tools.watchlist_db`, `tools.engagement_*`, `clients.jolly`, `clients.lisocon` importieren. Liste der betroffenen Dateien notieren.

- [ ] **Step 6: Tests loeschen, die entfernte Module oder fremde Mandanten testen**

Startliste (endgueltig entscheidet der Sammellauf aus Schritt 5):

```bash
cd "$DST/tests" && rm -f test_abm_comment_drafts.py test_abm_daily_jolly.py test_client_module_imports.py \
  test_comment_cadence.py test_daily_keyword_source.py test_distribution_loop.py \
  test_engagement_readback_wiring.py test_engagement_stats.py test_mining_brief.py \
  test_persona_magnet_binding.py test_poster_split.py test_rescore_floor.py \
  test_run_research_hook.py test_run_research_schedule.py test_slate_build.py \
  test_slate_phases.py test_watchlist_db.py test_image_upload_branch.py
cd "$DST" && python -m pytest -q -p no:cacheprovider 2>&1 | tail -15
```

Fuer jede weitere rote Datei: Ursache lesen. Importiert sie ein geloeschtes Modul oder `clients.jolly`/`clients.lisocon`: loeschen. Prueft sie Motor-Logik mit Fake-Config und faellt nur wegen `CLIENT`-Default `jolly`: stehen lassen, sie wird in Task 2 gruen. Ergebnis (Zahl gruen, Zahl rot, Liste der roten) in `$TEMP/task1_baseline.txt` festhalten.

- [ ] **Step 7: Lokaler Zwischen-Commit**

```bash
cd "$DST" && printf 'chore: initial copy of the SWOT tenant from the multi-tenant engine\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>\n' > "$TEMP/msg.txt"
git add -A && git commit -q -F "$TEMP/msg.txt" && git log --oneline
```

Erwartet: ein Commit. (`git add -A` ist hier erlaubt: frisches Repo, nur eigene Dateien.)

---

### Task 2: Tenant-Loader Default `swot`

**Files:**
- Modify: `clients/__init__.py:1-19`
- Modify: `run_keyword_scrape.py:75`
- Test: `tests/test_client_default.py`

**Interfaces:**
- Produces: `clients.load_client()` liefert ohne gesetzte `CLIENT`-Env `clients.swot.config`.

- [ ] **Step 1: Failing Test schreiben**

Datei `tests/test_client_default.py`:

```python
"""Ohne CLIENT-Env laedt der Loader den SWOT-Mandanten. Subprozess, weil
load_client() gecached ist und die Env im selben Prozess nicht umschaltbar ist."""
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run(code: str, env_overrides: dict) -> str:
    env = {k: v for k, v in os.environ.items() if k != "CLIENT"}
    env.update(env_overrides)
    proc = subprocess.run([sys.executable, "-c", code], cwd=REPO, env=env,
                          capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stderr[-800:]
    return proc.stdout.strip()


def test_load_client_defaults_to_swot():
    out = _run("from clients import load_client; print(load_client().NAME)", {})
    assert out == "swot"


def test_keyword_scrape_module_defaults_to_swot():
    out = _run("import run_keyword_scrape as k; print(k._CLIENT)", {})
    assert out == "swot"


def test_explicit_client_env_still_wins():
    out = _run("from clients import load_client; print(load_client().NAME)", {"CLIENT": "swot"})
    assert out == "swot"
```

- [ ] **Step 2: Test laufen lassen, Fehlschlag sehen**

Run: `python -m pytest tests/test_client_default.py -q -p no:cacheprovider`
Erwartet: FAIL, `ModuleNotFoundError: No module named 'clients.jolly'` im stderr.

- [ ] **Step 3: Loader und Keyword-Scrape aendern**

`clients/__init__.py` Zeile 1 und 18:

```python
"""Client-Registry: die Env-Variable CLIENT waehlt den Mandanten (Default: swot).
```

```python
    name = os.getenv("CLIENT", "swot").strip().lower()
```

`run_keyword_scrape.py` Zeile 75:

```python
_CLIENT = os.getenv("CLIENT", "swot").strip().lower()
```

- [ ] **Step 4: Tests gruen**

Run: `python -m pytest tests/test_client_default.py -q -p no:cacheprovider`
Erwartet: 3 passed.

Run: `python -m pytest -q -p no:cacheprovider 2>&1 | tail -5`
Erwartet: weniger rote Tests als in `$TEMP/task1_baseline.txt`. Verbleibende rote Tests notieren, sie gehoeren zu Task 3 (Env-Namen) oder Task 4 (Bild-Upload).

- [ ] **Step 5: Commit**

```bash
printf 'feat: tenant loader defaults to swot\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>\n' > "$TEMP/msg.txt"
git add clients/__init__.py run_keyword_scrape.py tests/test_client_default.py && git commit -q -F "$TEMP/msg.txt"
```

---

### Task 3: Env-Namen ohne `_SWOT`, DB-IDs nur aus der Env

**Files:**
- Modify: `clients/swot/config.py:675-693` (Token-Env-Block), `:740-746` (DB-Defaults), `:818-824` (`CONTENT_PLAN_DB_ID`)
- Modify: `tests/test_apify_auth.py` (Assertion auf `APIFY_API_TOKEN_SWOT`), `tests/test_anthropic_auth.py`, `tests/test_kieai_token_env.py::test_swot_config_declares_own_token_env`
- Test: `tests/test_swot_env_names.py`

**Interfaces:**
- Consumes: `tools.apify_auth.token_env_name(cfg)`, `tools.anthropic_auth.token_env_name(cfg)`, `tools.kieai_image._api_key(cfg)` (Defaults `APIFY_API_KEY`, `ANTHROPIC_API_KEY`, `KIEAI_API_KEY`, sobald die Config kein `*_TOKEN_ENV` mehr setzt); `tools.topic_ideas_db._db_id()` liest `TOPIC_IDEAS_DB_ID` aus der Env, sobald `TOPIC_IDEAS_DB_ID_DEFAULT` als Attribut fehlt.
- Produces: `cfg.CONTENT_PLAN_DB_ID == os.getenv("NOTION_DB_ID", "")`; `cfg.APIFY_ACCOUNT == "kueswot"` bleibt.

- [ ] **Step 1: Failing Test schreiben**

Datei `tests/test_swot_env_names.py`:

```python
"""Das SWOT-Repo liest die Standard-Env-Namen. Kein _SWOT-Suffix, keine
Notion-IDs im Code."""
import importlib
import inspect
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import anthropic_auth, apify_auth, kieai_image


def _cfg():
    return importlib.import_module("clients.swot.config")


def test_token_env_names_are_the_plain_defaults(monkeypatch):
    cfg = _cfg()
    assert apify_auth.token_env_name(cfg) == "APIFY_API_KEY"
    assert anthropic_auth.token_env_name(cfg) == "ANTHROPIC_API_KEY"
    monkeypatch.setenv("KIEAI_API_KEY", "k")
    assert kieai_image._api_key(cfg) == "k"


def test_apify_account_guard_stays():
    assert _cfg().APIFY_ACCOUNT == "kueswot"


def test_no_notion_ids_in_config_source():
    src = inspect.getsource(_cfg())
    assert "TOPIC_IDEAS_DB_ID_DEFAULT" not in src
    assert "4e7b33b3" not in src and "3c11617b" not in src
    assert _cfg().NOTION_DB_ID_DEFAULT is None


def test_content_plan_db_id_comes_from_notion_db_id_env(monkeypatch):
    monkeypatch.setenv("NOTION_DB_ID", "abc-123")
    cfg = importlib.reload(_cfg())
    assert cfg.CONTENT_PLAN_DB_ID == "abc-123"
```

- [ ] **Step 2: Fehlschlag sehen**

Run: `python -m pytest tests/test_swot_env_names.py -q -p no:cacheprovider`
Erwartet: FAIL in allen vier Tests ausser `test_apify_account_guard_stays`.

- [ ] **Step 3: `clients/swot/config.py` aendern**

Block Zeilen 675-693 ersetzen durch:

```python
# Apify-Konto "kueswot": tools/apify_auth.py prueft den Kontonamen vor dem
# ersten Lauf, damit ein Token eines fremden Kontos nie still laeuft.
APIFY_ACCOUNT = "kueswot"
```

(`APIFY_TOKEN_ENV`, `KIEAI_TOKEN_ENV`, `ANTHROPIC_TOKEN_ENV` und ihre Kommentare fallen weg.)

Zeilen 740-746 ersetzen durch:

```python
# Redaktionsplan-DB und Themen-DB kommen aus der Env (NOTION_DB_ID,
# TOPIC_IDEAS_DB_ID). Keine IDs im Code.
NOTION_DB_ID_DEFAULT = None
```

Zeilen 818-824 ersetzen durch:

```python
# Content-Redaktionsplan Blog und LinkedIn (kundensichtbar). Dieselbe DB wie
# NOTION_DB_ID: Kommentar-Entwuerfe und ihr Dedup (Property "Kommentar-Ziel")
# laufen ueber NOTION_DB_ID, Monatsplan, Text und Bild ueber diesen Namen.
# Der Monatsplan schreibt ausschliesslich Status "Entwurf"; die Stufen
# "Text freigegeben" und "Freigegeben" setzt die Redaktion von Hand.
CONTENT_PLAN_DB_ID = os.getenv("NOTION_DB_ID", "")
```

Pruefen, dass `import os` oben in `config.py` existiert (Zeile mit `INFLUENCERS_CSV = os.path.join(...)` beweist es).

- [ ] **Step 4: Alte Tests auf die neuen Namen anpassen**

`tests/test_kieai_token_env.py`: Funktion `test_swot_config_declares_own_token_env` loeschen.
`tests/test_apify_auth.py`: den Test, der `swot.APIFY_TOKEN_ENV == "APIFY_API_TOKEN_SWOT"` prueft (um Zeile 120), loeschen. Tests mit `_Cfg(APIFY_TOKEN_ENV="APIFY_API_TOKEN_SWOT")` (Fake-Config, Zeilen 56-71) bleiben, sie testen den Mechanismus, nicht SWOT. Den String `APIFY_API_TOKEN_SWOT` dort trotzdem in `APIFY_API_TOKEN_KUNDE` umbenennen (Verifikations-Grep auf `_SWOT`).
`tests/test_anthropic_auth.py`: `ANTHROPIC_API_KEY_SWOT` in `ANTHROPIC_API_KEY_KUNDE` umbenennen (Zeilen 30-31), `NAME="jolly"` in `NAME="x"`.
`tests/test_kieai_token_env.py`: `KIEAI_API_KEY_SWOT` in `KIEAI_API_KEY_KUNDE`, `NAME="jolly"` in `NAME="x"`.

- [ ] **Step 5: Tests gruen**

Run: `python -m pytest tests/test_swot_env_names.py tests/test_apify_auth.py tests/test_anthropic_auth.py tests/test_kieai_token_env.py -q -p no:cacheprovider`
Erwartet: alle passed.

Run: `grep -rn "_SWOT" --include=*.py . | grep -v "\.git/"`
Erwartet: 0 Zeilen.

- [ ] **Step 6: Commit**

```bash
printf 'feat: read plain env names and Notion DB ids from the environment\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>\n' > "$TEMP/msg.txt"
git add clients/swot/config.py tests/ && git commit -q -F "$TEMP/msg.txt"
```

---

### Task 4: Bild-Upload nach Supabase Storage

**Files:**
- Modify: `tools/kieai_image.py:65-79` (Konstanten), `:366-400` (`_upload_to_github` loeschen), `:576-607` (Upload-Zweig in `_run_kie_job`)
- Test: `tests/test_image_storage_upload.py`

**Interfaces:**
- Consumes: `tools.supabase_db._base_url()`, `tools.supabase_db._key()` (werfen `RuntimeError` bei fehlender Env).
- Produces: `_upload_to_storage(image_bytes: bytes, filename: str, now: datetime | None = None) -> str` gibt `f"{SUPABASE_URL}/storage/v1/object/public/{STORAGE_BUCKET}/{yyyy-mm}/{filename}"` zurueck. `STORAGE_BUCKET = "post-images"`. `_run_kie_job` gibt nur noch diese URL zurueck oder wirft.

- [ ] **Step 1: Failing Test schreiben**

Datei `tests/test_image_storage_upload.py`:

```python
"""Genau ein Upload-Pfad: Supabase Storage. Kein GitHub, kein catbox, kein
kie.ai-Fallback. Jede Bild-URL beginnt mit SUPABASE_URL."""
import inspect
import os
import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import kieai_image


def test_module_has_no_foreign_hosts():
    src = inspect.getsource(kieai_image)
    assert "githubusercontent" not in src
    assert "catbox" not in src
    assert "GITHUB_" not in src
    assert not hasattr(kieai_image, "_upload_to_github")


def test_upload_returns_public_url_under_supabase_url(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://xyz.supabase.co/")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "k")
    resp = MagicMock(status_code=200, ok=True, text="")
    with patch.object(kieai_image.requests, "post", return_value=resp) as post:
        url = kieai_image._upload_to_storage(
            b"png", "generated_abc12345.png",
            now=datetime(2026, 10, 3, tzinfo=timezone.utc))
    assert url == "https://xyz.supabase.co/storage/v1/object/public/post-images/2026-10/generated_abc12345.png"
    called_url = post.call_args.args[0]
    assert called_url == "https://xyz.supabase.co/storage/v1/object/post-images/2026-10/generated_abc12345.png"
    headers = post.call_args.kwargs["headers"]
    assert headers["Authorization"] == "Bearer k"
    assert headers["Content-Type"] == "image/png"
    assert headers["x-upsert"] == "true"
    assert post.call_args.kwargs["data"] == b"png"


def test_upload_failure_raises_instead_of_falling_back(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://xyz.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "k")
    resp = MagicMock(status_code=403, ok=False, text="denied")
    with patch.object(kieai_image.requests, "post", return_value=resp):
        with pytest.raises(RuntimeError, match="403"):
            kieai_image._upload_to_storage(b"png", "x.png")


def test_missing_supabase_env_raises(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="SUPABASE_URL"):
        kieai_image._upload_to_storage(b"png", "x.png")


def test_logo_default_is_swot():
    assert os.path.basename(kieai_image.LOGO_PATH) == "swot_logo.png"
```

- [ ] **Step 2: Fehlschlag sehen**

Run: `python -m pytest tests/test_image_storage_upload.py -q -p no:cacheprovider`
Erwartet: FAIL, `AttributeError: module 'tools.kieai_image' has no attribute '_upload_to_storage'` und `assert "githubusercontent" not in src` schlaegt fehl.

- [ ] **Step 3: Konstanten ersetzen (Zeilen 65-79)**

Den Block von `GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")` bis einschliesslich `GITHUB_IMAGES_BRANCH = "images"` ersetzen durch:

```python
# Bild-Hosting: Supabase Storage im eigenen Projekt, Bucket public read.
# Pfad <yyyy-mm>/<dateiname>.png, damit der Bucket nach Monat browsbar bleibt.
STORAGE_BUCKET = "post-images"
```

Logo-Zeilen 78-79 ersetzen durch:

```python
# Mandanten-Logo (LOGO_FILE in clients/<name>/config.py).
LOGO_PATH = os.path.join(os.path.dirname(__file__), "..", "Resources",
                         getattr(load_client(), "LOGO_FILE", "swot_logo.png"))
```

Import ergaenzen (nach `from tools import anthropic_auth`):

```python
from tools.supabase_db import _base_url as _supabase_url, _key as _supabase_key
from datetime import datetime, timezone
```

`import base64` entfernen, falls nach Schritt 4 unbenutzt (`grep -n "base64\." tools/kieai_image.py`).

- [ ] **Step 4: `_upload_to_github` durch `_upload_to_storage` ersetzen (Zeilen 366-400)**

```python
def _upload_to_storage(image_bytes: bytes, filename: str, now: datetime | None = None) -> str:
    """Laedt das Bild in den Supabase-Storage-Bucket und gibt die oeffentliche
    URL zurueck. Genau ein Upload-Pfad: schlaegt er fehl, wirft die Funktion,
    ein Bild mit fremder oder ablaufender URL entsteht nie."""
    base = _supabase_url()
    key = _supabase_key()
    now = now or datetime.now(timezone.utc)
    object_path = f"{now:%Y-%m}/{filename}"
    resp = requests.post(
        f"{base}/storage/v1/object/{STORAGE_BUCKET}/{object_path}",
        headers={"Authorization": f"Bearer {key}", "apikey": key,
                 "Content-Type": "image/png", "x-upsert": "true"},
        data=image_bytes, timeout=60)
    if not resp.ok:
        raise RuntimeError(
            f"Storage-Upload fehlgeschlagen (HTTP {resp.status_code}): {resp.text[:200]}")
    url = f"{base}/storage/v1/object/public/{STORAGE_BUCKET}/{object_path}"
    print(f"  Storage-Upload: {url}", flush=True)
    return url
```

- [ ] **Step 5: Upload-Zweig in `_run_kie_job` ersetzen (Zeilen 576-607)**

Alles von `# Permanenten Upload versuchen (mit Logo falls verfuegbar)` bis einschliesslich `return image_url` (der kie.ai-Fallback) ersetzen durch:

```python
            # Genau ein Upload-Pfad. Ein Fehler hier bricht die Bildgenerierung
            # ab; die aufrufende Zeile bleibt ohne Bild (run_image_fill faengt
            # die Exception je Zeile).
            upload_bytes = final_bytes if final_bytes is not None else img_bytes
            filename = f"generated_{task_id[:8]}.png"
            return _upload_to_storage(upload_bytes, filename)
```

Modul-Docstring und Kommentar ueber dem Logo-Overlay pruefen: kein Wort mehr zu GitHub, catbox, Railway.

- [ ] **Step 6: Tests gruen**

Run: `python -m pytest tests/test_image_storage_upload.py tests/test_kieai_retry.py tests/test_kieai_token_env.py tests/test_image_text_readback.py tests/test_image_archetypes.py -q -p no:cacheprovider`
Erwartet: alle passed. Faellt `test_kieai_retry.py`, weil es `_upload_to_github` patcht: dort `_upload_to_github` durch `_upload_to_storage` ersetzen, Rueckgabewert beliebige URL.

Run: `grep -rn "githubusercontent\|catbox\|GITHUB_TOKEN" --include=*.py --include=*.md . | grep -v "\.git/"`
Erwartet: 0 Zeilen.

- [ ] **Step 7: Commit**

```bash
printf 'feat: upload generated images to Supabase Storage only\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>\n' > "$TEMP/msg.txt"
git add tools/kieai_image.py tests/ && git commit -q -F "$TEMP/msg.txt"
```

---

### Task 5: `system_check` prueft den Storage-Bucket

**Files:**
- Modify: `tools/system_check.py:1-14` (Docstring), `:288-296` (`collect`)
- Test: `tests/test_system_check_storage.py`

**Interfaces:**
- Consumes: `tools.system_check._result(name, ok, severity, detail)`, `uses_supabase(cfg)`, `HARD`, `SOFT`, `TIMEOUT`.
- Produces: `check_storage(cfg) -> list` mit Ergebnisname `storage:post-images`. HARD, weil ohne Bucket jeder Bildlauf abbricht.

- [ ] **Step 1: Failing Test schreiben**

Datei `tests/test_system_check_storage.py`:

```python
import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import system_check as sc


def _cfg():
    return SimpleNamespace(NAME="swot", FEATURES={"supabase_persist": True})


def test_storage_check_is_hard_and_reads_bucket(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://xyz.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "k")
    resp = MagicMock(status_code=200, json=lambda: {"name": "post-images", "public": True})
    with patch.object(sc.requests, "get", return_value=resp) as get:
        [r] = sc.check_storage(_cfg())
    assert get.call_args.args[0] == "https://xyz.supabase.co/storage/v1/bucket/post-images"
    assert r["name"] == "storage:post-images"
    assert r["ok"] is True and r["severity"] == sc.HARD


def test_storage_check_fails_when_bucket_is_not_public(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://xyz.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "k")
    resp = MagicMock(status_code=200, json=lambda: {"name": "post-images", "public": False})
    with patch.object(sc.requests, "get", return_value=resp):
        [r] = sc.check_storage(_cfg())
    assert r["ok"] is False and "public" in r["detail"]


def test_storage_check_fails_when_bucket_missing(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://xyz.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "k")
    resp = MagicMock(status_code=404, json=lambda: {}, text="not found")
    with patch.object(sc.requests, "get", return_value=resp):
        [r] = sc.check_storage(_cfg())
    assert r["ok"] is False and r["severity"] == sc.HARD


def test_storage_check_is_part_of_collect():
    assert "check_storage" in sc.collect.__code__.co_names
```

Vor dem Schreiben pruefen, wie `_result` das Dict baut (`sed -n 40,60p tools/system_check.py`): Schluesselnamen (`name`, `ok`, `severity`, `detail`) im Test an die echte Funktion anpassen.

- [ ] **Step 2: Fehlschlag sehen**

Run: `python -m pytest tests/test_system_check_storage.py -q -p no:cacheprovider`
Erwartet: FAIL, `AttributeError: ... has no attribute 'check_storage'`.

- [ ] **Step 3: `check_storage` einbauen (vor `def collect`)**

```python
def check_storage(cfg) -> list:
    """Bucket fuer Post-Bilder. HARD: ohne oeffentlichen Bucket bricht jeder
    Bildlauf ab, und Notion zeigt nur Bilder, die ohne Login ladbar sind."""
    if not uses_supabase(cfg):
        return []
    url, key = os.getenv("SUPABASE_URL", ""), os.getenv("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        return [_result("storage:post-images", False, HARD, "URL oder Service-Key fehlt")]
    try:
        resp = requests.get(f"{url.rstrip('/')}/storage/v1/bucket/post-images",
                            headers={"apikey": key, "Authorization": f"Bearer {key}"},
                            timeout=TIMEOUT)
    except requests.RequestException as e:
        return [_result("storage:post-images", True, HARD,
                        f"unbekannt (nicht erreichbar: {e})")]
    if resp.status_code != 200:
        return [_result("storage:post-images", False, HARD,
                        f"Bucket fehlt (HTTP {resp.status_code}): {resp.text[:100]}")]
    if not resp.json().get("public"):
        return [_result("storage:post-images", False, HARD,
                        "Bucket ist nicht public, Bilder waeren in Notion unsichtbar")]
    return [_result("storage:post-images", True, HARD, "Bucket lesbar und public")]
```

In `collect` nach `results += check_supabase(cfg)`:

```python
    results += check_storage(cfg)
```

Modul-Docstring Zeilen 1-14: Saetze mit Railway und `CLIENT=lisocon` streichen. Neuer Schluss:

```
Direkt aufrufbar:  python tools/system_check.py        (Exit 1 bei NO-GO)
```

- [ ] **Step 4: Tests gruen**

Run: `python -m pytest tests/test_system_check_storage.py tests/test_system_check.py -q -p no:cacheprovider`
Erwartet: alle passed. Faellt `test_system_check.py` wegen `KIEAI_API_KEY`-Erwartungen nicht, gut; faellt es wegen `jolly_like`-Fake-Config: Fake-Config ist erlaubt, nur den Bezeichner `jolly_like` in `plain_like` umbenennen (Grep-Regel gilt fuer `lisocon`, `jollymarketer`, nicht fuer `jolly`, trotzdem sauber halten).

- [ ] **Step 5: Commit**

```bash
printf 'feat: system check verifies the public post-images bucket\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>\n' > "$TEMP/msg.txt"
git add tools/system_check.py tests/ && git commit -q -F "$TEMP/msg.txt"
```

---

### Task 6: `run_comment_drafts.py` mit Redaktionsplan-Schreiber und `--force`

**Files:**
- Modify: `tools/comment_drafts.py:409-425` (Signatur, Wochentags-Gate, Schreiber)
- Create: `run_comment_drafts.py`
- Test: `tests/test_run_comment_drafts.py`

**Interfaces:**
- Consumes: `tools.comment_drafts.run_comment_drafts`, `tools.notion_db.NOTION_API`, `tools.notion_db._headers()`, `tools.notion_db._notion_request(method, url, headers=..., json=...)`, `tools.notion_db._rich_text_prop(text)`, `tools.notion_db._sanitize(text)`, `tools.notion_db.NOTION_DB_ID`.
- Produces: `run_comment_drafts(cfg=None, now=None, force=False, writer=None) -> int`. `writer(draft: dict) -> str` (Notion-Page-ID). `run_comment_drafts.create_plan_comment_entry(draft: dict) -> str` schreibt eine Redaktionsplan-Zeile: `Titel`, `Status` = `Kommentar-Vorschlag`, `Typ` = `LinkedIn-Kommentar`, `Kanal` = `LinkedIn <Poster>`, `Kommentar-Ziel` = URL, `Post-Text` = Kommentar, `Kurzbeschreibung` = Influencer plus Auszug, `Gescraped am` = jetzt.

Redaktionsplan-Properties (gemessen 2026-09-22 an der Quell-DB): `Titel` (title), `Status` (select: Entwurf, Text freigegeben, Text+Bild, Freigegeben, Gepostet, Verworfen, Kommentar-Vorschlag), `Typ` (select: LinkedIn-Post, Blog-Artikel, LinkedIn-Kommentar), `Kanal` (select: LinkedIn Christian, LinkedIn Robert, LinkedIn Inga, LinkedIn Unternehmensseite, swot.de Blog), `Kommentar-Ziel` (url), `Post-Text`, `Kurzbeschreibung`, `Erster Kommentar` (rich_text), `Gescraped am`, `Geplant für` (date), `Bild` (files), `Achse`, `Format`, `Bezug` (select).

- [ ] **Step 1: Failing Test schreiben**

Datei `tests/test_run_comment_drafts.py`:

```python
"""run_comment_drafts: Wochentags-Gate, --force, Schreiber in den
Redaktionsplan mit Typ LinkedIn-Kommentar."""
import os
import sys
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import run_comment_drafts as rcd
from tools import comment_drafts as cd


def _cfg():
    return SimpleNamespace(NAME="swot", COMMENT_DRAFTS={
        "profiles_per_day": 1, "max_posts_per_profile": 1, "max_age_hours": 72,
        "posters": ["Christian"], "days": (0, 2, 4),
        "drafts_per_poster": 5, "drafts_total": 5})


def _tuesday():
    return datetime(2026, 10, 6, 9, 0, tzinfo=timezone.utc)   # weekday() == 1


def test_weekday_gate_skips_off_days():
    with patch.object(cd, "get_meta") as gm:
        assert cd.run_comment_drafts(_cfg(), now=_tuesday()) == 0
    gm.assert_not_called()


def test_force_bypasses_weekday_and_daily_guard():
    post = {"post_url": "https://li/1", "post_text": "t", "influencer": "X"}
    draft = {"title": "Kommentar Christian: X", "comment": "c", "typ": "",
             "poster": "Christian", "target_url": "https://li/1",
             "influencer": "X", "excerpt": "t"}
    writer = MagicMock(return_value="page-1")
    with patch.object(cd, "get_meta", return_value=_tuesday().date().isoformat()), \
         patch.object(cd, "set_meta"), \
         patch.object(cd, "get_comment_target_urls", return_value=set()), \
         patch.object(cd, "load_influencers", return_value=[{"linkedin_url": "u"}]), \
         patch.object(cd, "fetch_fresh_posts", return_value=[post]), \
         patch.object(cd, "draft_comment", return_value=draft), \
         patch.object(cd, "_notify"):
        n = cd.run_comment_drafts(_cfg(), now=_tuesday(), force=True, writer=writer)
    assert n == 1
    writer.assert_called_once_with(draft)


def test_plan_writer_builds_redaktionsplan_row():
    draft = {"title": "Kommentar Christian: X", "comment": "Guter Punkt.",
             "poster": "Christian", "target_url": "https://li/1",
             "influencer": "Max Muster", "excerpt": "Original-Auszug"}
    resp = MagicMock()
    resp.json.return_value = {"id": "page-9"}
    with patch.object(rcd, "NOTION_DB_ID", "db-1"), \
         patch.object(rcd, "_notion_request", return_value=resp) as req:
        assert rcd.create_plan_comment_entry(draft) == "page-9"
    body = req.call_args.kwargs["json"]
    props = body["properties"]
    assert body["parent"] == {"database_id": "db-1"}
    assert props["Typ"] == {"select": {"name": "LinkedIn-Kommentar"}}
    assert props["Status"] == {"select": {"name": "Kommentar-Vorschlag"}}
    assert props["Kanal"] == {"select": {"name": "LinkedIn Christian"}}
    assert props["Kommentar-Ziel"] == {"url": "https://li/1"}
    assert props["Post-Text"]["rich_text"][0]["text"]["content"] == "Guter Punkt."
    assert "Max Muster" in props["Kurzbeschreibung"]["rich_text"][0]["text"]["content"]


def test_cli_passes_force(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["run_comment_drafts.py", "--force"])
    with patch.object(rcd, "run_comment_drafts", return_value=2) as run:
        assert rcd.main() == 0
    assert run.call_args.kwargs["force"] is True
    assert run.call_args.kwargs["writer"] is rcd.create_plan_comment_entry
```

- [ ] **Step 2: Fehlschlag sehen**

Run: `python -m pytest tests/test_run_comment_drafts.py -q -p no:cacheprovider`
Erwartet: FAIL, `ModuleNotFoundError: No module named 'run_comment_drafts'`.

- [ ] **Step 3: `tools/comment_drafts.py` anpassen**

Signatur und Gate (ab Zeile 409) ersetzen:

```python
def run_comment_drafts(cfg=None, now=None, force: bool = False, writer=None) -> int:
    """Ein Lauf: rotierender Profil-Ausschnitt, frische Posts, Kommentar-
    Entwuerfe bis zum Deckel. Rueckgabe: Zahl geschriebener Zeilen.
    force=True uebergeht Wochentags-Gate und Tages-Guard (Testlauf).
    writer(draft) -> page_id schreibt die Zeile; Default create_comment_entry."""
    cfg = cfg or _cfg
    now = now or datetime.now(timezone.utc)
    write_row = writer or create_comment_entry
    settings = getattr(cfg, "COMMENT_DRAFTS", None)
    if not settings:
        print("  Kommentar-Entwuerfe nicht konfiguriert - Skip.")
        return 0

    # Wochentags-Gate vor jedem Kostenpunkt: ohne `days` bleibt es taeglich.
    days = settings.get("days")
    if not force and days and now.weekday() not in tuple(days):
        print(f"  Kein Kommentar-Tag (weekday {now.weekday()}) - Skip.")
        return 0
```

Tages-Guard: die Zeile `if get_meta(meta_key) == today:` wird zu `if not force and get_meta(meta_key) == today:`.

Schreibaufruf: `create_comment_entry(draft)` in der Schleife wird zu `write_row(draft)`.

- [ ] **Step 4: `run_comment_drafts.py` anlegen**

```python
"""Kommentar-Entwuerfe fuer den Redaktionsplan (Mo, Mi, Fr).

    python run_comment_drafts.py            # nur an Lauftagen aus COMMENT_DRAFTS["days"]
    python run_comment_drafts.py --force    # Gate und Tages-Guard uebergehen (Testlauf)

Jeder Entwurf wird eine Zeile mit Typ "LinkedIn-Kommentar" und Status
"Kommentar-Vorschlag" im Redaktionsplan (NOTION_DB_ID). Die Redaktion
kommentiert von Hand und setzt den Status weiter.
Kosten je Lauf: ein Apify-Lauf ueber die rotierten Profile plus ein
Anthropic-Call je Entwurf.
"""
import argparse
import sys
from datetime import datetime, timezone

from clients import load_client
from tools.comment_drafts import run_comment_drafts
from tools.notion_db import (NOTION_API, NOTION_DB_ID, _headers, _notion_request,
                             _rich_text_prop, _sanitize)


def create_plan_comment_entry(draft: dict) -> str:
    """Kommentar-Entwurf als Redaktionsplan-Zeile. Property-Namen sind die des
    Redaktionsplans, nicht der Recycling-DB (dafuer steht create_comment_entry)."""
    title = _sanitize(draft.get("title", ""))[:200] or "Kommentar"
    kurz = _sanitize(
        f"Kommentar unter einem Beitrag von {draft.get('influencer', '')}. "
        f"Auszug: {draft.get('excerpt', '')[:300]}")
    props = {
        "Titel": {"title": [{"text": {"content": title}}]},
        "Status": {"select": {"name": "Kommentar-Vorschlag"}},
        "Typ": {"select": {"name": "LinkedIn-Kommentar"}},
        "Kommentar-Ziel": {"url": draft.get("target_url", "")},
        "Post-Text": {"rich_text": _rich_text_prop(_sanitize(draft.get("comment", "")))},
        "Kurzbeschreibung": {"rich_text": _rich_text_prop(kurz)},
        "Gescraped am": {"date": {"start": datetime.now(timezone.utc).isoformat()}},
    }
    if draft.get("poster"):
        props["Kanal"] = {"select": {"name": f"LinkedIn {draft['poster']}"}}
    resp = _notion_request("POST", f"{NOTION_API}/pages", headers=_headers(),
                           json={"parent": {"database_id": NOTION_DB_ID}, "properties": props})
    resp.raise_for_status()
    return resp.json()["id"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true",
                    help="Wochentags-Gate und Tages-Guard uebergehen (Testlauf)")
    args = ap.parse_args()
    cfg = load_client()
    n = run_comment_drafts(cfg, now=datetime.now(timezone.utc), force=args.force,
                           writer=create_plan_comment_entry)
    print(f"\nKommentar-Entwuerfe geschrieben: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Vorher pruefen, dass `_rich_text_prop` und `_sanitize` in `tools/notion_db.py` so heissen (`grep -n "def _rich_text_prop\|def _sanitize\|def _headers\|def _notion_request" tools/notion_db.py`). Weichen Namen ab, im Skript und Test anpassen.

- [ ] **Step 5: Tests gruen**

Run: `python -m pytest tests/test_run_comment_drafts.py -q -p no:cacheprovider`
Erwartet: 4 passed.

Run: `python -m pytest -q -p no:cacheprovider 2>&1 | tail -5`
Erwartet: keine neuen roten Tests. Bestehende Tests, die `run_comment_drafts(cfg, now)` positional aufrufen, bleiben kompatibel.

- [ ] **Step 6: Commit**

```bash
printf 'feat: add run_comment_drafts entry point writing to the Redaktionsplan\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>\n' > "$TEMP/msg.txt"
git add run_comment_drafts.py tools/comment_drafts.py tests/test_run_comment_drafts.py && git commit -q -F "$TEMP/msg.txt"
```

---

### Task 7: `revision_next.py` Protokollpfad im Repo

**Files:**
- Modify: `scripts/revision_next.py:1-30` (Docstring), `:198-201` (Pfad)
- Test: `tests/test_revision_next_protocol_path.py`

**Interfaces:**
- Produces: `scripts.revision_next.default_protokoll_pfad() -> str` = `<repo>/workspace/pruefberichte/revision_next-protokoll.json`.

- [ ] **Step 1: Failing Test**

Datei `tests/test_revision_next_protocol_path.py`:

```python
import importlib.util
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)


def _load():
    spec = importlib.util.spec_from_file_location(
        "revision_next", os.path.join(REPO, "scripts", "revision_next.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_protocol_lands_inside_the_repo():
    pfad = _load().default_protokoll_pfad()
    assert pfad == os.path.join(REPO, "workspace", "pruefberichte", "revision_next-protokoll.json")
```

Laedt das Modul beim Import Netz oder Notion (Modulebene), den Test stattdessen als Subprozess mit `python -c "import sys; sys.path.insert(0,'scripts'); import revision_next; print(revision_next.default_protokoll_pfad())"` schreiben.

- [ ] **Step 2: Fehlschlag sehen**

Run: `python -m pytest tests/test_revision_next_protocol_path.py -q -p no:cacheprovider`
Erwartet: FAIL, `AttributeError: ... 'default_protokoll_pfad'`.

- [ ] **Step 3: Pfadfunktion einbauen**

Vor `def main` (oder der Funktion, die `args.protokoll` liest):

```python
def default_protokoll_pfad() -> str:
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(repo, "workspace", "pruefberichte", "revision_next-protokoll.json")
```

Zeilen 198-201 ersetzen:

```python
    pfad = args.protokoll or default_protokoll_pfad()
```

Docstring: die drei Beispielbefehle ohne `CLIENT=swot`, letzter Absatz:

```
Schreibt ein Protokoll nach workspace/pruefberichte/ (gitignored) zum
Auflisten der Ergebnisse.
```

- [ ] **Step 4: Test gruen und Commit**

Run: `python -m pytest tests/test_revision_next_protocol_path.py -q -p no:cacheprovider`
Erwartet: 1 passed.

```bash
printf 'fix: revision_next writes its protocol inside the repo\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>\n' > "$TEMP/msg.txt"
git add scripts/revision_next.py tests/test_revision_next_protocol_path.py && git commit -q -F "$TEMP/msg.txt"
```

---

### Task 8: Docstrings, Config-Kommentare, Grep-Gate

**Files:**
- Modify: alle `*.py` mit `CLIENT=swot` in Docstrings (run_axis_scrape, run_image_eval, run_image_fill, run_monthly_plan, run_plan_fill, run_review_backfill, run_source_scrape, run_verworfen_sync, scripts/add_plan_fill_properties.py, scripts/measure_diet.py, tools/discover_voices.py, tools/topic_ideas_db.py, tests/test_image_eval.py, tests/test_image_fill.py, tests/test_monthly_plan.py)
- Modify: `clients/swot/config.py` (Kommentare), `workflows/*.md`, `tools/*.py` (Railway-, lisocon-, Obsidian-Hinweise in Kommentaren)
- Test: `tests/test_no_foreign_references.py`

**Interfaces:**
- Produces: Grep-Gate als Test, damit der Zustand nicht zurueckrutscht.

- [ ] **Step 1: Failing Test schreiben**

Datei `tests/test_no_foreign_references.py`:

```python
"""Verifikation 7.2 des Specs als Test: keine Jolly-Pfade, fremden Mandanten
oder alten Env-Namen im Repo."""
import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATTERN = re.compile(r"richa|Jolly_Claude_Code|lisocon|sonocrete|jollymarketer|_SWOT|obsidian",
                     re.IGNORECASE)
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".tmp", "workspace", ".venv"}


def test_no_foreign_references():
    hits = []
    for root, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            if name.endswith((".png", ".jpg", ".pyc")):
                continue
            path = os.path.join(root, name)
            with open(path, encoding="utf-8", errors="ignore") as fh:
                for i, line in enumerate(fh, 1):
                    if PATTERN.search(line):
                        hits.append(f"{os.path.relpath(path, REPO)}:{i}: {line.strip()[:80]}")
    assert not hits, "\n".join(hits[:40])
```

Hinweis: `_SWOT` mit `re.IGNORECASE` faengt auch `_swot` in Bezeichnern wie `last_comments_at_swot`. Solche Treffer sind falsch positiv. Die Regel des Specs ist case-sensitiv fuer `_SWOT`: Pattern deshalb zweiteilen: `re.compile(r"richa|Jolly_Claude_Code|lisocon|sonocrete|jollymarketer|obsidian", re.I)` und `re.compile(r"_SWOT")` ohne Flag, beide pruefen.

- [ ] **Step 2: Fehlschlag sehen, Trefferliste als Arbeitsliste**

Run: `python -m pytest tests/test_no_foreign_references.py -q -p no:cacheprovider 2>&1 | head -60`
Erwartet: FAIL mit Trefferliste. Zusaetzlich die volle Liste:

```bash
grep -rniE "richa|Jolly_Claude_Code|lisocon|sonocrete|jollymarketer|obsidian" --exclude-dir=.git --exclude-dir=__pycache__ . > "$TEMP/task8_hits.txt"; grep -rn "_SWOT" --exclude-dir=.git . >> "$TEMP/task8_hits.txt"; wc -l "$TEMP/task8_hits.txt"
```

- [ ] **Step 3: Treffer abarbeiten, Regeln je Typ**

- `CLIENT=swot python ...` in Docstrings: `CLIENT=swot ` streichen, Befehl bleibt.
- Kommentare in `clients/swot/config.py` mit `Clients/SWOT/...`, `Obsidian`, `notion.so/...`-Task-URLs: den Pfad- oder URL-Teil streichen, die inhaltliche Aussage (Datum, Entscheidung, Messung) bleibt. Beispiel Zeile 323 `see Clients/SWOT/Branding/...` wird zu `measured 09.09.2026`. Konfigurationswerte bleiben unveraendert (Test `test_swot_env_names.py` und die bestehenden Config-Tests sichern das).
- `lisocon`/`jolly` in Erklaerkommentaren des Motors (z.B. `tools/topic_ideas_db.py:31-34`, `run_keyword_scrape.py:82-85`, `tools/supabase_db.py:28-30`, `tools/notion_db.py:19-20`, `tools/system_check.py:130-132`): Satz so umformulieren, dass die Regel ohne den Mandantennamen steht ("ein Mandant ohne eigene KEYWORDS" statt "lisocon").
- `richa` in Pfaden: nur in Kommentaren moeglich, Pfad streichen.
- `jollymarketer` und `githubusercontent`: nach Task 4 nur noch in Doku moeglich, streichen.
- `tests/`: Testnamen und Fake-Configs mit `lisocon` in `kunde_b` umbenennen, Logik unveraendert.
- `workflows/*.md`: Absaetze zu Railway, `run_research`, Slate, Lisocon streichen; Befehle auf die Tabelle in Spec Abschnitt 6 bringen.

Jeden Treffer nach der Aenderung erneut greppen, bis `wc -l` = 0.

- [ ] **Step 4: Gate gruen, ganze Suite gruen**

Run: `python -m pytest -q -p no:cacheprovider 2>&1 | tail -5`
Erwartet: 0 failed. Zahl der Tests notieren (kommt ins README, Task 10).

- [ ] **Step 5: Commit**

```bash
printf 'chore: remove multi-tenant and Jolly-internal references from docs and comments\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>\n' > "$TEMP/msg.txt"
git add -A && git commit -q -F "$TEMP/msg.txt"
```

---

### Task 9: `db/schema.sql` und `db/storage.sql`

**Files:**
- Create: `db/schema.sql`
- Create: `db/storage.sql`

**Interfaces:**
- Consumes: Spaltenlisten aus `scripts/blog_content_mining_schema.sql` (influencer_posts), `scripts/setup_topic_pool_tables.sql` (topic_candidates, engine_meta), `db/migrations/2026-08-19_*.sql` und `2026-09-14_comment_watchlist.sql` im Quellrepo, sowie `tools/topic_decisions_db.py:108-128` (topic_decisions-Spalten).
- Produces: idempotente DDL fuer fuenf Tabellen und einen Bucket. Wird in Task 11 im SWOT-Projekt ausgefuehrt.

- [ ] **Step 1: Ist-Schema aus dem Jolly-Projekt auslesen (Readback statt Raten)**

Im Quellrepo-Ordner, mit `SUPABASE_DB_URL` aus `C:\Users\richa\Jolly_Claude_Code\.env` (psycopg ist installiert):

```bash
cd "C:/Users/richa/Jolly_Claude_Code/Jolly Automations/Jolly Linkedin Content Creation" && python - <<'PY'
import os, psycopg
from dotenv import load_dotenv
load_dotenv("C:/Users/richa/Jolly_Claude_Code/.env")
with psycopg.connect(os.environ["SUPABASE_DB_URL"]) as c, c.cursor() as cur:
    cur.execute("""select table_name, column_name, data_type, is_nullable, column_default
                   from information_schema.columns where table_schema='blog_content_mining'
                   order by table_name, ordinal_position""")
    for r in cur.fetchall(): print(r)
    cur.execute("""select conrelid::regclass, conname, pg_get_constraintdef(oid)
                   from pg_constraint where connamespace='blog_content_mining'::regnamespace""")
    for r in cur.fetchall(): print(r)
    cur.execute("""select indexdef from pg_indexes where schemaname='blog_content_mining'""")
    for r in cur.fetchall(): print(r[0])
PY
```

Ausgabe nach `$TEMP/jolly_schema.txt` sichern. Die DDL unten gegen diese Ausgabe abgleichen und Abweichungen (Spaltentypen, Defaults, Indizes) in die Datei uebernehmen. Die Ausgabe ist die Wahrheit, der Entwurf unten der Startpunkt.

- [ ] **Step 2: `db/schema.sql` schreiben**

```sql
-- SWOT LinkedIn Content Engine: Datenschema.
-- Einmalig im Supabase-Projekt ausfuehren (SQL Editor). Idempotent.
-- Danach: Dashboard -> Settings -> API -> Exposed schemas -> "blog_content_mining"
-- eintragen, sonst erreicht der REST-Wrapper das Schema nicht.

create schema if not exists blog_content_mining;

create table if not exists blog_content_mining.influencer_posts (
    client      text not null default 'swot',
    post_url    text not null,
    source      text not null,
    influencer  text,
    post_text   text,
    post_date   date,
    likes       integer default 0,
    comments    integer default 0,
    shares      integer default 0,
    scraped_at  timestamptz not null default now(),
    primary key (client, post_url)
);
create index if not exists influencer_posts_post_date_idx
    on blog_content_mining.influencer_posts (post_date);
create index if not exists influencer_posts_client_date_idx
    on blog_content_mining.influencer_posts (client, post_date);

create table if not exists blog_content_mining.topic_candidates (
    post_url        text primary key,
    client          text not null,
    source          text not null default '',
    influencer      text not null default '',
    post_text       text not null default '',
    post_date       date,
    likes           int  not null default 0,
    comments        int  not null default 0,
    shares          int  not null default 0,
    persona         text not null default '',
    matrix_job      text not null default '',
    matrix_stage    text not null default '',
    voc_hit         text not null default '',
    topic_angle_de  text not null default '',
    score_total     int  not null default 0,
    scores          jsonb,
    reasoning       text not null default '',
    state           text not null default 'pool',
    times_slated    int  not null default 0,
    first_seen_at   timestamptz not null default now(),
    last_scored_at  timestamptz,
    last_slated_at  timestamptz
);
create index if not exists topic_candidates_client_state_idx
    on blog_content_mining.topic_candidates (client, state);

create table if not exists blog_content_mining.engine_meta (
    key   text primary key,
    value text not null default ''
);

create table if not exists blog_content_mining.topic_decisions (
    notion_page_id     text primary key,
    client             text not null default 'swot',
    batch_date         date,
    theme_label        text not null default '',
    title_de           text not null default '',
    title_en           text not null default '',
    keyword_de         text not null default '',
    keyword_en         text not null default '',
    cluster_size       integer,
    source_influencers text not null default '',
    parent_hub_url     text not null default '',
    classification     text,
    status             text,
    decision           text not null default 'pending',
    decision_source    text not null default '',
    decided_at         timestamptz,
    learn              boolean not null default true,
    last_synced_at     timestamptz
);
create index if not exists topic_decisions_client_decision_idx
    on blog_content_mining.topic_decisions (client, decision);

create table if not exists blog_content_mining.comment_watchlist (
    client        text        not null,
    linkedin_url  text        not null,
    prio          smallint    not null default 9,
    typ           text        not null default 'person',
    domain        text        not null default '',
    company       text        not null default '',
    persona       text        not null default '',
    first_name    text        not null default '',
    last_name     text        not null default '',
    title         text        not null default '',
    source        text        not null default '',
    active_at     timestamptz,
    updated_at    timestamptz not null default now(),
    primary key (client, linkedin_url)
);
create index if not exists comment_watchlist_client_prio
    on blog_content_mining.comment_watchlist (client, prio);
```

Spaltenliste von `topic_decisions` und `influencer_posts` gegen `$TEMP/jolly_schema.txt` abgleichen und korrigieren.

- [ ] **Step 3: `db/storage.sql` schreiben**

```sql
-- Bucket fuer Post-Bilder. Public read, damit Notion die Bilder ohne Login
-- laedt. Schreiben nur mit dem Service-Key (tools/kieai_image.py).
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('post-images', 'post-images', true, 10485760, array['image/png', 'image/jpeg'])
on conflict (id) do update set public = true;
```

- [ ] **Step 4: Syntax pruefen und Commit**

Run: `python -c "import sqlparse" 2>/dev/null || echo "kein sqlparse, Syntaxpruefung in Task 11 gegen die echte DB"`

```bash
printf 'feat: add database schema and storage bucket definitions\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>\n' > "$TEMP/msg.txt"
git add db/schema.sql db/storage.sql && git commit -q -F "$TEMP/msg.txt"
```

---

### Task 10: README, SETUP, `.env.example`, `.gitlab-ci.yml`, Workflows

**Files:**
- Create: `README.md`, `SETUP.md`, `.env.example`, `.gitlab-ci.yml`
- Modify: `workflows/content_generation.md`, `workflows/keyword_scrape.md`, `workflows/research_phase.md` (bereits in Task 8 bereinigt; hier Befehle abgleichen)
- Modify: `requirements.txt` (Docstring-Kommentar, sonst unveraendert)

**Interfaces:**
- Consumes: Testzahl aus Task 8 Schritt 4.

- [ ] **Step 1: `.env.example`**

```dotenv
# Anthropic (Texte, Leser, Reparatur, Kommentare, Themenwahl)
ANTHROPIC_API_KEY=

# Apify (LinkedIn-Scraping). Konto muss "kueswot" sein, tools/apify_auth.py prueft das.
APIFY_API_KEY=

# kie.ai (Bildgenerierung)
KIEAI_API_KEY=

# Notion: interne Integration mit Zugriff auf den Teamspace des Redaktionsplans
NOTION_TOKEN=
# Redaktionsplan-DB (Content-Redaktionsplan Blog und LinkedIn)
NOTION_DB_ID=
# Themen-DB (Topic Ideas)
TOPIC_IDEAS_DB_ID=

# Supabase: Projekt-URL und Service-Key (Settings -> API)
SUPABASE_URL=
SUPABASE_SERVICE_KEY=

# Optional: Make-Webhook fuer eine Review-Mail nach jedem Schreiblauf. Leer = keine Mail.
MAKE_REVIEW_WEBHOOK=
```

- [ ] **Step 2: `README.md`**

```markdown
# SWOT LinkedIn Content Engine

Erzeugt den monatlichen Redaktionsplan, Beitragstexte, Bilder und Kommentar-Vorschlaege fuer die LinkedIn-Konten und den Blog von SWOT. Quelle der Themen sind oeffentliche LinkedIn-Beitraege ausgewaehlter Profile, die wöchentlich gescrapt und in Supabase abgelegt werden. Ziel aller Schreiblaeufe ist der Redaktionsplan in Notion.

## Betreiber

| Baustein | Konto | Verantwortlich |
|---|---|---|
| Code | GitLab (git.swot.de) | SWOT |
| Anthropic, Apify (kueswot), kie.ai | SWOT-Konten | SWOT |
| Supabase (Daten und Bilder) | SWOT-Projekt | SWOT |
| Notion (Redaktionsplan, Themen-DB) | Workspace von SWOT | SWOT |
| Laeufe | CLI oder GitLab-Schedules | SWOT |

Jolly Marketer hat nach der Uebergabe keine Rolle im Betrieb.

## Laeufe

| Lauf | Befehl | Rhythmus | Voraussetzung |
|---|---|---|---|
| Quellen-Scrape | `python run_source_scrape.py` | woechentlich | keine |
| Achsen-Scrape | `python run_axis_scrape.py` | woechentlich | keine |
| Topic-Mining | `python run_topic_mining.py` | woechentlich, nach Scrape | keine |
| Monatsplan | `python run_monthly_plan.py --month YYYY-MM --write` | monatlich | Themen-DB gesichtet |
| Plan fuellen | `python run_plan_fill.py --months YYYY-MM --write` | nach Monatsplan | keine |
| Bild | `python run_image_fill.py --write` | auf Zuruf | Zeilen mit Status "Text freigegeben" |
| Kommentare | `python run_comment_drafts.py` | Mo, Mi, Fr | keine |
| Verworfen-Sync | `python run_verworfen_sync.py --write` | woechentlich | keine |

Jeder Lauf ohne `--write` ist ein Trockenlauf. Vor dem ersten Lauf: `python tools/system_check.py` muss GO melden.

## Freigabekette im Redaktionsplan

Entwurf (Maschine) -> Text freigegeben (Redaktion) -> Text+Bild (Maschine) -> Freigegeben (Redaktion) -> Gepostet. Kommentar-Vorschlaege stehen mit Typ "LinkedIn-Kommentar" in derselben DB.

## Setup

Siehe SETUP.md. Tests: `python -m pytest` (N Tests, Stand 2026-09-22).
```

`N` durch die Zahl aus Task 8 ersetzen. Keine Trennlinien (`---`) im Dokument.

- [ ] **Step 3: `SETUP.md`**

```markdown
# Setup

## Voraussetzungen

- Python 3.12
- Git
- Konten: Anthropic, Apify (Konto "kueswot"), kie.ai, Supabase-Projekt, Notion-Workspace mit interner Integration

## Installation

    git clone <GitLab-URL> swot-linkedin-content-engine
    cd swot-linkedin-content-engine
    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt
    copy .env.example .env

`.env` fuellen, siehe Variablen in `.env.example`. Die Datei ist gitignored.

## Supabase einmalig

1. SQL Editor: Inhalt von `db/schema.sql` ausfuehren.
2. SQL Editor: Inhalt von `db/storage.sql` ausfuehren.
3. Settings -> API -> Exposed schemas: `blog_content_mining` eintragen.
4. Settings -> API: URL und Service-Key in `.env` (`SUPABASE_URL`, `SUPABASE_SERVICE_KEY`).

## Notion einmalig

1. Integration unter notion.so/my-integrations (intern, Rechte: Inhalte lesen, aktualisieren, einfuegen).
2. Der Teamspace mit dem Redaktionsplan und der Themen-DB muss fuer die Integration freigegeben sein.
3. Datenbank-IDs (32 Hex-Zeichen aus der URL) in `.env`: `NOTION_DB_ID` = Redaktionsplan, `TOPIC_IDEAS_DB_ID` = Themen-DB.

Der Redaktionsplan braucht diese Properties: Titel, Status, Typ, Kanal, Achse, Format, Bezug, Geplant für, Gescraped am, Kurzbeschreibung, Post-Text, Soundbyte, Infografik-Skelett, Bild, Kommentar-Ziel.

## Erster Lauf

    python tools/system_check.py
    python run_monthly_plan.py --month 2026-11

Der zweite Befehl ist ein Trockenlauf und schreibt nichts.

## Apify-Konto wechseln

`clients/swot/config.py` enthaelt `APIFY_ACCOUNT = "kueswot"`. Der Guard in `tools/apify_auth.py` bricht ab, wenn der Token zu einem anderen Konto gehoert. Bei Kontowechsel den Wert anpassen.

## GitLab-Schedules

`.gitlab-ci.yml` enthaelt drei Jobs als Vorlage. Variablen aus `.env` als CI/CD-Variablen (masked) anlegen, dann Schedules unter CI/CD -> Schedules aktivieren.
```

- [ ] **Step 4: `.gitlab-ci.yml`**

```yaml
# Schedule-Vorlage. Aktivierung unter CI/CD -> Schedules mit der Variable
# JOB=scrape | comments | verworfen. Alle Env-Variablen aus .env.example als
# maskierte CI/CD-Variablen anlegen.
image: python:3.12

before_script:
  - pip install -q -r requirements.txt

.scheduled:
  rules:
    - if: $CI_PIPELINE_SOURCE == "schedule"

scrape_and_mining:
  extends: .scheduled
  rules:
    - if: $CI_PIPELINE_SOURCE == "schedule" && $JOB == "scrape"
  script:
    - python tools/system_check.py
    - python run_source_scrape.py
    - python run_axis_scrape.py
    - python run_topic_mining.py

comments:
  extends: .scheduled
  rules:
    - if: $CI_PIPELINE_SOURCE == "schedule" && $JOB == "comments"
  script:
    - python tools/system_check.py
    - python run_comment_drafts.py

verworfen_sync:
  extends: .scheduled
  rules:
    - if: $CI_PIPELINE_SOURCE == "schedule" && $JOB == "verworfen"
  script:
    - python tools/system_check.py
    - python run_verworfen_sync.py --write
```

- [ ] **Step 5: Workflows abgleichen**

Jede der drei Dateien unter `workflows/` oeffnen. Befehle muessen mit der README-Tabelle uebereinstimmen. Abschnitte zu Laeufen, die es im Repo nicht gibt (`run_research.py`, `run_slate.py`, Railway-Cron), sind seit Task 8 weg; pruefen mit `grep -n "run_research\|run_slate\|railway" workflows/*.md` = 0 Zeilen.

- [ ] **Step 6: Commit**

```bash
printf 'docs: add README, SETUP, env template and GitLab schedule template\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>\n' > "$TEMP/msg.txt"
git add README.md SETUP.md .env.example .gitlab-ci.yml workflows/ && git commit -q -F "$TEMP/msg.txt"
python -m pytest -q -p no:cacheprovider 2>&1 | tail -3
```

Erwartet: 0 failed (das Grep-Gate aus Task 8 prueft auch die neuen Dokumente).

---

### Task 11: Migration Supabase (Schema, Bucket, Zeilen)

**Files:**
- Create (Quellrepo): `scripts/swot_carveout/copy_supabase_rows.py`
- Create (Quellrepo): `scripts/swot_carveout/readback.py`
- Create (Zielrepo): `docs/migration-2026-09.md` (wird in Task 12 und 13 ergaenzt)

**Interfaces:**
- Consumes: Jolly-Projekt via `SUPABASE_URL`/`SUPABASE_SERVICE_KEY` aus der Content-Engine-`.env`; SWOT-Projekt via `SUPABASE_URL`/`SUPABASE_SERVICE_ROLE_KEY` aus `C:\Users\richa\Jolly_Claude_Code\Clients\SWOT\swot-outbound-engine\.env`.
- Produces: fuenf Tabellen im SWOT-Projekt mit den `swot`-Zeilen; Readback-Tabelle.

Ist-Stand Jolly-Projekt (gemessen 2026-09-22, `client = 'swot'`): influencer_posts 404, topic_candidates 0, topic_decisions 50, comment_watchlist 0, engine_meta 1 Schluessel (`last_scrape_at_swot`).

- [ ] **Step 1: Schema und Bucket im SWOT-Projekt anlegen**

Weg 1: Supabase-MCP. `mcp__claude_ai_Supabase__list_projects` aufrufen, Projekt mit Ref-Praefix `wpnh` identifizieren, dann `mcp__claude_ai_Supabase__apply_migration` mit `name="blog_content_mining_schema"` und dem Inhalt von `db/schema.sql`, danach `apply_migration` mit `name="post_images_bucket"` und `db/storage.sql`. Danach im MCP `execute_sql`: `select table_name from information_schema.tables where table_schema='blog_content_mining' order by 1;` und `select id, public from storage.buckets where id='post-images';`.

Weg 2 (wenn das MCP das Projekt nicht listet): Richard bekommt beide SQL-Dateien mit Pfad genannt und fuehrt sie im SQL Editor aus. STOP bis Rueckmeldung.

Erwartet: fuenf Tabellen, Bucket `post-images` mit `public = true`. Exposed schemas: `blog_content_mining` eintragen (Dashboard, nur Richard). Readback per REST:

```bash
cd "C:/Users/richa/Jolly_Claude_Code/Jolly Automations/Jolly Linkedin Content Creation" && python - <<'PY'
import os, requests
from dotenv import dotenv_values
sw = dotenv_values("C:/Users/richa/Jolly_Claude_Code/Clients/SWOT/swot-outbound-engine/.env")
url, key = sw["SUPABASE_URL"].rstrip("/"), sw["SUPABASE_SERVICE_ROLE_KEY"]
h = {"apikey": key, "Authorization": f"Bearer {key}", "Accept-Profile": "blog_content_mining", "Prefer": "count=exact", "Range": "0-0"}
for t in ["influencer_posts", "topic_candidates", "engine_meta", "topic_decisions", "comment_watchlist"]:
    r = requests.get(f"{url}/rest/v1/{t}", headers=h, params={"select": "*"}, timeout=30)
    print(t, r.status_code, r.headers.get("content-range"))
r = requests.get(f"{url}/storage/v1/bucket/post-images", headers={"apikey": key, "Authorization": f"Bearer {key}"}, timeout=30)
print("bucket", r.status_code, r.json().get("public"))
PY
```

Erwartet: fuenfmal HTTP 200 mit `*/0`, `bucket 200 True`. Ein 404/406 auf den Tabellen heisst: Schema nicht exposed, zurueck zu Richard.

- [ ] **Step 2: `copy_supabase_rows.py` schreiben (Quellrepo)**

Datei `scripts/swot_carveout/copy_supabase_rows.py`:

```python
"""Einmalig: swot-Zeilen aus dem Jolly-Supabase in das SWOT-Projekt kopieren.

    python scripts/swot_carveout/copy_supabase_rows.py            # Trockenlauf, zaehlt nur
    python scripts/swot_carveout/copy_supabase_rows.py --write    # kopiert per Upsert

Quelle: SUPABASE_URL / SUPABASE_SERVICE_KEY aus der Content-Engine-.env.
Ziel:   SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY aus der Outbound-Engine-.env von SWOT.
Idempotent (Upsert auf den Primaerschluessel). Schreibt nie in die Quelle.
"""
import argparse
import os
import sys

import requests
from dotenv import dotenv_values

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SWOT_ENV = "C:/Users/richa/Jolly_Claude_Code/Clients/SWOT/swot-outbound-engine/.env"
SCHEMA = "blog_content_mining"
TABLES = {  # tabelle: (filter-params, on_conflict)
    "influencer_posts": ({"client": "eq.swot"}, "client,post_url"),
    "topic_candidates": ({"client": "eq.swot"}, "post_url"),
    "topic_decisions": ({"client": "eq.swot"}, "notion_page_id"),
    "comment_watchlist": ({"client": "eq.swot"}, "client,linkedin_url"),
    "engine_meta": ({"key": "like.*swot*"}, "key"),
}


def _conn(path: str, key_name: str) -> tuple[str, str]:
    env = dotenv_values(path)
    url, key = (env.get("SUPABASE_URL") or "").rstrip("/"), env.get(key_name) or ""
    if not url or not key:
        sys.exit(f"{path}: SUPABASE_URL oder {key_name} fehlt")
    return url, key


def _headers(key: str, write: bool = False) -> dict:
    h = {"apikey": key, "Authorization": f"Bearer {key}"}
    if write:
        h.update({"Content-Profile": SCHEMA, "Content-Type": "application/json",
                  "Prefer": "resolution=merge-duplicates,return=minimal"})
    else:
        h["Accept-Profile"] = SCHEMA
    return h


def fetch_all(url: str, key: str, table: str, params: dict) -> list[dict]:
    rows, offset = [], 0
    while True:
        r = requests.get(f"{url}/rest/v1/{table}", headers=_headers(key),
                         params={**params, "select": "*", "limit": 1000, "offset": offset}, timeout=60)
        r.raise_for_status()
        batch = r.json()
        rows += batch
        if len(batch) < 1000:
            return rows
        offset += 1000


def count(url: str, key: str, table: str, params: dict) -> int:
    r = requests.get(f"{url}/rest/v1/{table}", headers={**_headers(key), "Prefer": "count=exact", "Range": "0-0"},
                     params={**params, "select": "*"}, timeout=60)
    r.raise_for_status()
    return int(r.headers["content-range"].split("/")[1])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    src_url, src_key = _conn(os.path.join(ROOT, ".env"), "SUPABASE_SERVICE_KEY")
    dst_url, dst_key = _conn(SWOT_ENV, "SUPABASE_SERVICE_ROLE_KEY")
    if src_url == dst_url:
        sys.exit("Quelle und Ziel sind dasselbe Projekt. Abbruch.")
    print(f"{'Tabelle':20s} {'Quelle':>7s} {'Ziel vorher':>12s} {'Ziel nachher':>13s}")
    for table, (params, on_conflict) in TABLES.items():
        src_n = count(src_url, src_key, table, params)
        before = count(dst_url, dst_key, table, params)
        after = before
        if args.write and src_n:
            rows = fetch_all(src_url, src_key, table, params)
            for i in range(0, len(rows), 500):
                r = requests.post(f"{dst_url}/rest/v1/{table}", headers=_headers(dst_key, write=True),
                                  params={"on_conflict": on_conflict}, json=rows[i:i + 500], timeout=120)
                if not r.ok:
                    sys.exit(f"{table}: HTTP {r.status_code} {r.text[:300]}")
            after = count(dst_url, dst_key, table, params)
        print(f"{table:20s} {src_n:7d} {before:12d} {after:13d}")
    if not args.write:
        print("\nTrockenlauf. Mit --write kopieren.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 3: Trockenlauf, dann Schreiblauf, dann Readback**

```bash
cd "C:/Users/richa/Jolly_Claude_Code/Jolly Automations/Jolly Linkedin Content Creation"
python scripts/swot_carveout/copy_supabase_rows.py
python scripts/swot_carveout/copy_supabase_rows.py --write
python scripts/swot_carveout/copy_supabase_rows.py
```

Erwartet Zeile fuer Zeile: Quelle = Ziel nachher (404, 0, 50, 0, 1). Der dritte Aufruf (Trockenlauf) ist der unabhaengige Readback: `Ziel vorher` = `Quelle`.

- [ ] **Step 4: Migrationsprotokoll anlegen (Zielrepo)**

Datei `docs/migration-2026-09.md` im Zielrepo:

```markdown
# Migrationsprotokoll September 2026

Uebernahme des SWOT-Mandanten aus der Multi-Tenant-Engine in dieses Repo. Jeder Schritt mit Readback.

## 1. Supabase Schema

Datum: 2026-09-DD. Ausgefuehrt: `db/schema.sql`, `db/storage.sql`.

| Tabelle | vorhanden | Zeilen nach Schema |
|---|---|---|
| influencer_posts | ja | 0 |
| topic_candidates | ja | 0 |
| engine_meta | ja | 0 |
| topic_decisions | ja | 0 |
| comment_watchlist | ja | 0 |

Bucket `post-images`: vorhanden, public.

## 2. Supabase Zeilen

| Tabelle | Quelle | Ziel |
|---|---|---|
| influencer_posts | 404 | 404 |
| topic_candidates | 0 | 0 |
| engine_meta (Schluessel mit swot) | 1 | 1 |
| topic_decisions | 50 | 50 |
| comment_watchlist | 0 | 0 |

## 3. Bilder

(Task 12)

## 4. Notion

(Task 12)

## 5. Cutover

(Task 13)
```

Zahlen aus dem echten Readback eintragen, nicht aus diesem Plan.

- [ ] **Step 5: Commits (beide Repos)**

Zielrepo:

```bash
cd "C:/Users/richa/Jolly_Claude_Code/Clients/SWOT/swot-linkedin-content-engine"
printf 'docs: migration protocol, Supabase steps\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>\n' > "$TEMP/msg.txt"
git add docs/migration-2026-09.md && git commit -q -F "$TEMP/msg.txt"
```

Quellrepo (nur eigene Pfade, fremde Aenderungen der Parallelsession nicht anfassen):

```bash
cd "C:/Users/richa/Jolly_Claude_Code/Jolly Automations/Jolly Linkedin Content Creation"
git status --short | head
printf 'chore(swot-carveout): one-off Supabase row copy tool\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>\n' > "$TEMP/msg.txt"
git add scripts/swot_carveout/copy_supabase_rows.py && git commit -q -F "$TEMP/msg.txt" && git push origin master
```

---

### Task 12: Migration Bilder und Notion

Voraussetzung (Richard, per Notion-UI): Redaktionsplan-DB (`4e7b33b3-e1a3-4e3d-8024-011731d3b373`) und Topic-Ideas-DB (`3c11617b-1baf-81f2-b521-d4bab7bc8656`) unter die Seite "Linkedin Content Engine" (`3e36b49c-cad0-8096-b851-e8ac6879da98`) im Workspace von SWOT duplizieren. Ohne die beiden Kopien-IDs STOP. Ist-Stand Quelle (2026-09-22): Redaktionsplan 17 Zeilen, 30 Bild-Dateien, alle 30 auf `raw.githubusercontent.com`; Topic Ideas 50 Zeilen.

**Files:**
- Create (Quellrepo): `scripts/swot_carveout/migrate_images.py`
- Create (Quellrepo): `scripts/swot_carveout/rewrite_notion_image_urls.py`
- Modify (Zielrepo): `docs/migration-2026-09.md` Abschnitte 3 und 4

**Interfaces:**
- Consumes: `NOTION_TOKEN_SWOT` aus der Content-Engine-`.env` (SWOT-Integration), `NOTION_TOKEN` (Jolly, nur lesen), SWOT-Supabase wie Task 11.
- Produces: `migrate_images.py` schreibt `$TEMP/swot_image_map.json` (`{alte_url: neue_url}`); `rewrite_notion_image_urls.py` liest die Map und patcht die Kopie.

- [ ] **Step 1: Kopien-IDs von Richard holen und Zugriff pruefen**

```bash
cd "C:/Users/richa/Jolly_Claude_Code/Jolly Automations/Jolly Linkedin Content Creation" && python - <<'PY'
import os, requests
from dotenv import dotenv_values
tok = dotenv_values(".env")["NOTION_TOKEN_SWOT"]
h = {"Authorization": f"Bearer {tok}", "Notion-Version": "2022-06-28"}
r = requests.post("https://api.notion.com/v1/search", headers=h, json={"filter": {"property": "object", "value": "database"}}, timeout=30)
for d in r.json().get("results", []):
    print(d["id"], "".join(t["plain_text"] for t in d["title"]))
PY
```

Erwartet: zwei Datenbanken mit den Titeln der Kopien. IDs als `PLAN_COPY_ID` und `TOPICS_COPY_ID` notieren.

- [ ] **Step 2: `migrate_images.py` (Quellrepo)**

```python
"""Einmalig: alle Bild-URLs des Jolly-Redaktionsplans (raw.githubusercontent.com)
herunterladen und in den SWOT-Bucket post-images laden.

    python scripts/swot_carveout/migrate_images.py            # zaehlt, laedt nichts
    python scripts/swot_carveout/migrate_images.py --write    # laedt hoch

Ergebnis: $TEMP/swot_image_map.json  {alte_url: neue_url}. Pfad im Bucket:
migrated-2026-09/<dateiname aus der alten URL>. Idempotent (x-upsert).
"""
import argparse
import json
import os
import sys
from urllib.parse import urlparse

import requests
from dotenv import dotenv_values

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SWOT_ENV = "C:/Users/richa/Jolly_Claude_Code/Clients/SWOT/swot-outbound-engine/.env"
PLAN_DB = "4e7b33b3-e1a3-4e3d-8024-011731d3b373"
BUCKET, PREFIX = "post-images", "migrated-2026-09"
MAP_PATH = os.path.join(os.environ.get("TEMP", "."), "swot_image_map.json")


def notion_rows(token: str, db: str) -> list[dict]:
    h = {"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28"}
    rows, cur = [], None
    while True:
        body = {"page_size": 100, **({"start_cursor": cur} if cur else {})}
        j = requests.post(f"https://api.notion.com/v1/databases/{db}/query", headers=h, json=body, timeout=60).json()
        rows += j["results"]
        if not j.get("has_more"):
            return rows
        cur = j["next_cursor"]


def image_urls(rows: list[dict]) -> list[str]:
    urls = []
    for r in rows:
        for f in (r["properties"].get("Bild") or {}).get("files", []):
            u = f.get("external", {}).get("url") or f.get("file", {}).get("url", "")
            if u and u not in urls:
                urls.append(u)
    return urls


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    jolly_token = dotenv_values(os.path.join(ROOT, ".env"))["NOTION_TOKEN"]
    sw = dotenv_values(SWOT_ENV)
    dst, key = sw["SUPABASE_URL"].rstrip("/"), sw["SUPABASE_SERVICE_ROLE_KEY"]
    urls = image_urls(notion_rows(jolly_token, PLAN_DB))
    gh = [u for u in urls if "githubusercontent" in u]
    print(f"Bild-URLs: {len(urls)}, davon GitHub: {len(gh)}, andere: {len(urls) - len(gh)}")
    for u in urls:
        if u not in gh:
            print("  nicht-GitHub, bleibt:", u[:100])
    mapping = {}
    for u in gh:
        name = os.path.basename(urlparse(u).path)
        new = f"{dst}/storage/v1/object/public/{BUCKET}/{PREFIX}/{name}"
        mapping[u] = new
        if not args.write:
            continue
        img = requests.get(u, timeout=60)
        img.raise_for_status()
        up = requests.post(f"{dst}/storage/v1/object/{BUCKET}/{PREFIX}/{name}",
                           headers={"Authorization": f"Bearer {key}", "apikey": key,
                                    "Content-Type": "image/png", "x-upsert": "true"},
                           data=img.content, timeout=120)
        if not up.ok:
            sys.exit(f"Upload {name}: HTTP {up.status_code} {up.text[:200]}")
        chk = requests.head(new, timeout=30)
        print(f"  {name}: {len(img.content)} B, public HEAD {chk.status_code}")
    with open(MAP_PATH, "w", encoding="utf-8") as fh:
        json.dump(mapping, fh, indent=1)
    print(f"Map: {MAP_PATH} ({len(mapping)} Eintraege)")
    if not args.write:
        print("Trockenlauf. Mit --write hochladen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 3: Bilder migrieren und zaehlen**

```bash
cd "C:/Users/richa/Jolly_Claude_Code/Jolly Automations/Jolly Linkedin Content Creation"
python scripts/swot_carveout/migrate_images.py
python scripts/swot_carveout/migrate_images.py --write
python - <<'PY'
import requests
from dotenv import dotenv_values
sw = dotenv_values("C:/Users/richa/Jolly_Claude_Code/Clients/SWOT/swot-outbound-engine/.env")
url, key = sw["SUPABASE_URL"].rstrip("/"), sw["SUPABASE_SERVICE_ROLE_KEY"]
r = requests.post(f"{url}/storage/v1/object/list/post-images", headers={"Authorization": f"Bearer {key}", "apikey": key},
                  json={"prefix": "migrated-2026-09", "limit": 1000}, timeout=60)
print("Objekte im Bucket:", len(r.json()))
PY
```

Erwartet: `Objekte im Bucket` = Zahl der eindeutigen GitHub-URLs (Stand 22.09.: 30, wenn keine URL doppelt vorkommt; die Map-Groesse ist die Referenz). Jede HEAD-Zeile 200.

- [ ] **Step 4: `rewrite_notion_image_urls.py` (Quellrepo)**

```python
"""Einmalig: Bild-Properties der Redaktionsplan-KOPIE im SWOT-Workspace auf die
Supabase-URLs umschreiben. Quelle der Zuordnung: $TEMP/swot_image_map.json.

    python scripts/swot_carveout/rewrite_notion_image_urls.py --db <PLAN_COPY_ID>            # Trockenlauf
    python scripts/swot_carveout/rewrite_notion_image_urls.py --db <PLAN_COPY_ID> --write

Schreibt NUR in die angegebene DB und bricht ab, wenn sie die Jolly-Original-ID ist.
Umgeschrieben werden die Property "Bild" und Bild-Bloecke im Seitenkoerper.
"""
import argparse
import json
import os
import sys

import requests
from dotenv import dotenv_values

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
JOLLY_PLAN_DB = "4e7b33b3-e1a3-4e3d-8024-011731d3b373"
MAP_PATH = os.path.join(os.environ.get("TEMP", "."), "swot_image_map.json")
API = "https://api.notion.com/v1"


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"}


def rows(token: str, db: str) -> list[dict]:
    out, cur = [], None
    while True:
        body = {"page_size": 100, **({"start_cursor": cur} if cur else {})}
        r = requests.post(f"{API}/databases/{db}/query", headers=_h(token), json=body, timeout=60)
        r.raise_for_status()
        j = r.json()
        out += j["results"]
        if not j.get("has_more"):
            return out
        cur = j["next_cursor"]


def blocks(token: str, page_id: str) -> list[dict]:
    out, cur = [], None
    while True:
        params = {"page_size": 100, **({"start_cursor": cur} if cur else {})}
        r = requests.get(f"{API}/blocks/{page_id}/children", headers=_h(token), params=params, timeout=60)
        r.raise_for_status()
        j = r.json()
        out += j["results"]
        if not j.get("has_more"):
            return out
        cur = j["next_cursor"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    if args.db.replace("-", "") == JOLLY_PLAN_DB.replace("-", ""):
        sys.exit("Das ist die Jolly-Original-DB. Abbruch.")
    token = dotenv_values(os.path.join(ROOT, ".env"))["NOTION_TOKEN_SWOT"]
    with open(MAP_PATH, encoding="utf-8") as fh:
        mapping = json.load(fh)
    props_changed = blocks_changed = unknown = 0
    for page in rows(token, args.db):
        files = (page["properties"].get("Bild") or {}).get("files", [])
        new_files, touched = [], False
        for f in files:
            u = f.get("external", {}).get("url") or f.get("file", {}).get("url", "")
            if u in mapping:
                new_files.append({"name": f.get("name", "post-image.png"), "type": "external",
                                  "external": {"url": mapping[u]}})
                touched = True
            else:
                if "githubusercontent" in u:
                    unknown += 1
                    print(f"  UNBEKANNT (nicht in Map): {u[:100]}")
                new_files.append(f)
        if touched:
            props_changed += 1
            if args.write:
                r = requests.patch(f"{API}/pages/{page['id']}", headers=_h(token),
                                   json={"properties": {"Bild": {"files": new_files}}}, timeout=60)
                r.raise_for_status()
        for b in blocks(token, page["id"]):
            if b.get("type") != "image":
                continue
            u = b["image"].get("external", {}).get("url", "")
            if u in mapping:
                blocks_changed += 1
                if args.write:
                    r = requests.patch(f"{API}/blocks/{b['id']}", headers=_h(token),
                                       json={"image": {"external": {"url": mapping[u]}}}, timeout=60)
                    r.raise_for_status()
    print(f"Seiten mit Bild-Property umgeschrieben: {props_changed}, Bild-Bloecke: {blocks_changed}, unbekannte GitHub-URLs: {unknown}")
    if not args.write:
        print("Trockenlauf. Mit --write schreiben.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Trockenlauf, Schreiblauf, Readback**

```bash
cd "C:/Users/richa/Jolly_Claude_Code/Jolly Automations/Jolly Linkedin Content Creation"
python scripts/swot_carveout/rewrite_notion_image_urls.py --db <PLAN_COPY_ID>
python scripts/swot_carveout/rewrite_notion_image_urls.py --db <PLAN_COPY_ID> --write
python - <<'PY'
import os, sys, requests
from dotenv import dotenv_values
sys.argv = ["x"]
tok = dotenv_values(".env")["NOTION_TOKEN_SWOT"]
h = {"Authorization": f"Bearer {tok}", "Notion-Version": "2022-06-28"}
def n_rows(db):
    rows, cur = [], None
    while True:
        j = requests.post(f"https://api.notion.com/v1/databases/{db}/query", headers=h, json={"page_size": 100, **({"start_cursor": cur} if cur else {})}, timeout=60).json()
        rows += j["results"]
        if not j.get("has_more"): return rows
        cur = j["next_cursor"]
plan = n_rows("<PLAN_COPY_ID>"); topics = n_rows("<TOPICS_COPY_ID>")
gh = sum(1 for r in plan for f in (r["properties"].get("Bild") or {}).get("files", []) if "githubusercontent" in (f.get("external", {}).get("url") or ""))
print("plan rows", len(plan), "topic rows", len(topics), "github-urls", gh)
PY
```

Erwartet: `unbekannte GitHub-URLs: 0` im Trockenlauf; Readback `plan rows 17 topic rows 50 github-urls 0` (Zeilenzahlen gleich Quelle, Stand 22.09.). Weicht die Zeilenzahl ab, hat die Duplikation nicht alles kopiert: STOP, Richard.

- [ ] **Step 6: Protokoll ergaenzen, Commits**

`docs/migration-2026-09.md` Abschnitte 3 und 4 mit den gemessenen Zahlen fuellen (Bild-URLs in Notion, Objekte im Bucket, Zeilen Quelle/Ziel je DB, GitHub-URLs nach Umschreibung = 0) und die Datenbank-IDs der Kopien NICHT eintragen (kommen in die `.env` von SWOT, nicht ins Repo).

```bash
cd "C:/Users/richa/Jolly_Claude_Code/Clients/SWOT/swot-linkedin-content-engine"
printf 'docs: migration protocol, images and Notion\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>\n' > "$TEMP/msg.txt"
git add docs/migration-2026-09.md && git commit -q -F "$TEMP/msg.txt"
cd "C:/Users/richa/Jolly_Claude_Code/Jolly Automations/Jolly Linkedin Content Creation"
printf 'chore(swot-carveout): image migration and Notion URL rewrite tools\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>\n' > "$TEMP/msg.txt"
git add scripts/swot_carveout/migrate_images.py scripts/swot_carveout/rewrite_notion_image_urls.py && git commit -q -F "$TEMP/msg.txt" && git push origin master
```

---

### Task 13: Echtlauf-Verifikation gegen die SWOT-Konten

**Files:**
- Create (lokal, gitignored): Zielrepo `.env`
- Modify: `docs/migration-2026-09.md` Abschnitt 5

**Interfaces:**
- Consumes: alles aus Task 1 bis 12.

- [ ] **Step 1: Zielrepo-`.env` fuellen (Werte nie ausgeben)**

Werte per Python aus den Quellen zusammensetzen, nicht per Hand tippen:

```bash
cd "C:/Users/richa/Jolly_Claude_Code/Clients/SWOT/swot-linkedin-content-engine" && python - <<'PY'
from dotenv import dotenv_values
src = dotenv_values("C:/Users/richa/Jolly_Claude_Code/Jolly Automations/Jolly Linkedin Content Creation/.env")
sw = dotenv_values("C:/Users/richa/Jolly_Claude_Code/Clients/SWOT/swot-outbound-engine/.env")
vals = {
    "ANTHROPIC_API_KEY": src["ANTHROPIC_API_KEY_SWOT"],
    "APIFY_API_KEY": src["APIFY_API_TOKEN_SWOT"],
    "KIEAI_API_KEY": src["KIEAI_API_KEY_SWOT"],
    "NOTION_TOKEN": src["NOTION_TOKEN_SWOT"],
    "NOTION_DB_ID": "<PLAN_COPY_ID>",
    "TOPIC_IDEAS_DB_ID": "<TOPICS_COPY_ID>",
    "SUPABASE_URL": sw["SUPABASE_URL"],
    "SUPABASE_SERVICE_KEY": sw["SUPABASE_SERVICE_ROLE_KEY"],
    "MAKE_REVIEW_WEBHOOK": "",
}
missing = [k for k, v in vals.items() if v is None]
assert not missing, missing
with open(".env", "w", encoding="utf-8", newline="\n") as fh:
    fh.write("".join(f"{k}={v}\n" for k, v in vals.items()))
print("geschrieben:", ", ".join(vals))
PY
git status --short | grep -c "^?? .env$" ; echo "(0 = .env ist gitignored, korrekt)"
```

- [ ] **Step 2: System-Check**

Run: `python tools/system_check.py`
Erwartet: Ausgabe endet mit `GO`. Zeilen fuer notion, apify (Konto kueswot), anthropic, kieai, supabase:influencer_posts, storage:post-images alle ok. Bei NO-GO: die genannte Zeile beheben (meist Exposed schemas oder Teamspace-Freigabe), nicht weiter.

- [ ] **Step 3: Trockenlauf Monatsplan**

Run: `python run_monthly_plan.py --month 2026-11`
Erwartet: Slots werden gelistet, keine Notion-Writes (kein `--write`).

- [ ] **Step 4: Echtlauf Bild (Verifikation 7.4, kostet ~0,10 USD)**

Vorbedingung: mindestens eine Zeile der Kopie mit Status "Text freigegeben" und ohne Bild. Gibt es keine, eine bestehende Zeile mit Text in der Kopie per API auf "Text freigegeben" setzen und das im Protokoll vermerken.

Run: `python run_image_fill.py --write --limit 1`
Erwartet: `Storage-Upload: https://<swot-projekt>.supabase.co/storage/v1/object/public/post-images/2026-09/generated_....png` und `generiert 1`. Dann:

```bash
python - <<'PY'
import requests, re, subprocess
out = open(".tmp/last_image_url.txt").read().strip() if False else None
PY
```

Stattdessen die URL aus der Laufausgabe kopieren und pruefen:

```bash
curl -s -o /dev/null -w "%{http_code} %{content_type}\n" "<URL aus der Ausgabe>"
```

Erwartet: `200 image/png` ohne Login-Header. In der Notion-Kopie: Zeile hat Status "Text+Bild" und die Supabase-URL in "Bild".

- [ ] **Step 5: Echtlauf Kommentare (Verifikation 7.5, kostet ~0,05 USD Apify plus Sonnet)**

Run: `python run_comment_drafts.py --force`
Erwartet: `Kommentar-Entwuerfe geschrieben: N` mit N >= 1 (Messung 10.08.: 1 bis 2 realistisch; N = 0 mit Meldung "frische Posts uebrig: 0" ist ein Angebotsproblem, kein Fehler: dann Lauf mit `max_age_hours` 168 in einer temporaeren Kopie der Config wiederholen, nicht committen). Readback: Zeile in der Kopie mit Typ "LinkedIn-Kommentar", Status "Kommentar-Vorschlag", Kanal "LinkedIn Christian", gefuelltes "Kommentar-Ziel".

- [ ] **Step 6: Frischer Clone-Test (Verifikation 7.1, lokal vor GitHub)**

```bash
rm -rf "$TEMP/clone-test" && git clone -q "C:/Users/richa/Jolly_Claude_Code/Clients/SWOT/swot-linkedin-content-engine" "$TEMP/clone-test" && cd "$TEMP/clone-test" && python -m venv .venv && .venv/Scripts/pip install -q -r requirements.txt && .venv/Scripts/python -m pytest -q -p no:cacheprovider 2>&1 | tail -3
grep -ri "richa\|Jolly_Claude_Code\|lisocon\|sonocrete\|jollymarketer\|obsidian" --exclude-dir=.git . | wc -l; grep -r "_SWOT" --exclude-dir=.git . | wc -l
```

Erwartet: `N passed`, beide Grep-Zaehler 0. `pytest` hier laeuft ohne `.env` (Clone hat keine): Tests duerfen keine Env brauchen; faellt einer deshalb, ist das ein Testfehler, im Zielrepo beheben (monkeypatch), erneut clonen.

- [ ] **Step 7: Protokoll Abschnitt 5 und Commit**

Abschnitt 5 von `docs/migration-2026-09.md`:

```markdown
## 5. Cutover-Vorbereitung (Jolly-seitig, 2026-09-DD)

| Pruefung | Ergebnis |
|---|---|
| tools/system_check.py | GO |
| run_monthly_plan.py --month 2026-11 (Trockenlauf) | ok |
| run_image_fill.py --write --limit 1 | 1 Bild, URL unter SUPABASE_URL, HTTP 200 ohne Login |
| run_comment_drafts.py --force | N Zeilen, Typ LinkedIn-Kommentar |
| pytest im frischen Clone | N passed |
| Grep auf fremde Referenzen | 0 |

Offen: SWOT setzt eigene .env, faehrt system_check und den Trockenlauf des Monatsplans, bestaetigt schriftlich. Erst danach loescht Jolly den SWOT-Mandanten im Quellrepo, die swot-Zeilen im Jolly-Supabase und archiviert die Jolly-Notion-DBs.
```

```bash
cd "C:/Users/richa/Jolly_Claude_Code/Clients/SWOT/swot-linkedin-content-engine"
printf 'docs: migration protocol, verification runs\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>\n' > "$TEMP/msg.txt"
git add docs/migration-2026-09.md && git commit -q -F "$TEMP/msg.txt"
```

---

### Task 14: Ein Commit, privates GitHub-Repo, Push

**Files:**
- Zielrepo: Git-Historie

- [ ] **Step 1: Arbeitsbaum sauber, Historie zu einem Orphan-Commit zusammenfassen**

```bash
cd "C:/Users/richa/Jolly_Claude_Code/Clients/SWOT/swot-linkedin-content-engine"
git status --short | wc -l
git log --oneline | wc -l
```

Erwartet: 0 offene Aenderungen; mehrere lokale Commits. Dann (noch nie gepusht, deshalb erlaubt):

```bash
printf 'Initial commit: SWOT LinkedIn Content Engine\n\nStandalone engine for the SWOT editorial plan: scraping, topic mining,\nmonthly plan, post writing, image generation (Supabase Storage) and\ncomment drafts. Carved out of the Jolly multi-tenant engine on 2026-09-22.\nMigration protocol: docs/migration-2026-09.md\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>\n' > "$TEMP/msg.txt"
git checkout -q --orphan handover && git add -A && git commit -q -F "$TEMP/msg.txt" && git branch -D main && git branch -m main
git log --oneline | wc -l; git ls-files | grep -c "^\.env$"; git ls-files | wc -l
```

Erwartet: `1`, dann `0` (keine `.env` getrackt), dann die Dateizahl.

- [ ] **Step 2: Privates GitHub-Repo anlegen und pushen**

```bash
gh repo create jollymarketer/swot-linkedin-content-engine --private --source . --remote origin --push
gh repo view jollymarketer/swot-linkedin-content-engine --json visibility,defaultBranchRef -q '.visibility + " " + .defaultBranchRef.name'
git log origin/main --oneline | wc -l
```

Erwartet: `PRIVATE main`, `1`.

- [ ] **Step 3: Verifikation 7.1 gegen GitHub**

```bash
rm -rf "$TEMP/clone-gh" && git clone -q https://github.com/jollymarketer/swot-linkedin-content-engine.git "$TEMP/clone-gh" && cd "$TEMP/clone-gh" && python -m venv .venv && .venv/Scripts/pip install -q -r requirements.txt && .venv/Scripts/python -m pytest -q -p no:cacheprovider 2>&1 | tail -2 && git log --oneline | wc -l
```

Erwartet: `N passed` (gleiche Zahl wie README), `1`.

- [ ] **Step 4: Uebergabe-Info fuer Richard**

Im Chat: Repo-URL, Testzahl, die drei Dinge, die SWOT selbst tut (Import nach git.swot.de, `.env` mit eigenen Werten, Exposed schema und Teamspace-Freigabe sind schon gesetzt), und der Hinweis, dass Task 15 auf SWOTs schriftliche Bestaetigung wartet. `NOTION_DB_ID`/`TOPIC_IDEAS_DB_ID` der Kopien an SWOT per Mail, nicht im Repo.

---

### Task 15: Cutover im Jolly-Bestand (erst nach schriftlicher Bestaetigung von SWOT)

**Files:**
- Quellrepo: `clients/swot/` loeschen, `tests/` mit `swot`-Bezug anpassen, `scripts/swot_*.py`, `scripts/revision_next.py`, `scripts/measure_diet.py`, `scripts/add_plan_fill_properties.py`, `run_monthly_plan.py`, `run_plan_fill.py`, `run_image_fill.py`, `run_image_eval.py`, `run_review_backfill.py`, `run_verworfen_sync.py` (SWOT-only Einstiege) pruefen
- Jolly-Supabase: `swot`-Zeilen
- Jolly-Notion: beide DBs archivieren

Dieser Task startet NICHT automatisch. Bedingung: Mail oder Notion-Kommentar von SWOT, dass `system_check` GO meldet und der Trockenlauf des Monatsplans lief. Ohne diesen Beleg STOP.

- [ ] **Step 1: Vorher-Zaehlung und Backup**

```bash
cd "C:/Users/richa/Jolly_Claude_Code/Jolly Automations/Jolly Linkedin Content Creation"
python scripts/swot_carveout/copy_supabase_rows.py   # Trockenlauf = Zaehlung Quelle vs Ziel
mkdir -p "C:/Users/richa/Jolly_Claude_Code/Clients/SWOT/_archive/content-engine-tenant-2026-09" && cp -r clients/swot "C:/Users/richa/Jolly_Claude_Code/Clients/SWOT/_archive/content-engine-tenant-2026-09/"
```

Erwartet: Quelle = Ziel in jeder Zeile (sonst STOP, nichts loeschen).

- [ ] **Step 2: Loeschung im Jolly-Supabase (Richard bestaetigt im Chat je Tabelle)**

Fuer jede Tabelle mit `swot`-Zeilen: `DELETE ... WHERE client = 'swot'` beziehungsweise `DELETE FROM engine_meta WHERE key LIKE '%swot%'` ueber `SUPABASE_DB_URL` (psycopg), davor `SELECT count(*)` mit demselben WHERE, danach erneut. Zahlen ins Protokoll (Quellrepo-Commit-Message, nicht ins Zielrepo: das ist uebergeben).

- [ ] **Step 3: Jolly-Repo aufraeumen**

`clients/swot/` loeschen, `pytest` laufen lassen, jeden roten Test mit SWOT-Bezug auf den verbleibenden Mandanten umstellen oder loeschen. SWOT-only-Einstiege (`run_monthly_plan.py` und die anderen aus der Dateiliste) bleiben, wenn Lisocon oder Jolly sie nutzen; sonst nach `_archive/` (Loeschvorstufe, Go je Ordner von Richard). Commit nur eigener Pfade, Push.

- [ ] **Step 4: Jolly-Notion**

Beide Original-DBs (Redaktionsplan `4e7b33b3...`, Topic Ideas `3c11617b...`) archivieren (Notion-UI, Richard). Readback: Suche ueber die Jolly-Integration findet sie nicht mehr.

---

## Self-Review

Spec-Abdeckung:

- 3 Zielrepo, 3.1 Layout, 3.2 Ausschluesse: Task 1, 9, 10, 14.
- 4.1 Loader-Default: Task 2. 4.2 Env-Namen und DB-IDs: Task 3. 4.3 Storage-Upload mit Test: Task 4. 4.4 `run_comment_drafts.py` mit `--force`: Task 6. 4.5 `revision_next`: Task 7. 4.6 `review_backfill` unveraendert: kein Task, bewusst. 4.7 Config-Kommentare: Task 8. 4.8 `system_check` Bucket: Task 5. 4.9 Docstrings: Task 8.
- 5.1 bis 5.3: Task 11, 12. 5.4 Notion: Task 12 (Duplikation durch Richard als Vorbedingung). 5.5 Cutover: Task 13 (Jolly-seitig), Task 15 (nach SWOT-Bestaetigung).
- 6 Betrieb: README-Tabelle, `.gitlab-ci.yml`, `.env.example` in Task 10.
- 7.1 bis 7.7: Task 13 (7.1 lokal, 7.3, 7.4, 7.5), Task 8 (7.2 als Test), Task 11 bis 13 (7.6), Task 14 (7.1 gegen GitHub, 7.7).
- 8 Risiken: URL-Umschreiber Pflicht (Task 12 Schritt 5 bricht bei unbekannten URLs nicht ab, meldet sie aber; Readback verlangt 0). Apify-Guard im SETUP.md (Task 10).

Abweichung vom Spec, bewusst: `CONTENT_PLAN_DB_ID` liest `NOTION_DB_ID` statt einer eigenen Env-Variable, weil die `.env.example`-Liste des Specs (Abschnitt 6) keine `CONTENT_PLAN_DB_ID` enthaelt und Kommentar-Dedup ueber `NOTION_DB_ID` auf dieselbe DB zeigen muss. Steht in den Global Constraints.

Typ-Konsistenz: `run_comment_drafts(cfg=None, now=None, force=False, writer=None)` in Task 6 Interfaces, Code und Test identisch. `_upload_to_storage(image_bytes, filename, now=None)` in Task 4 Test und Code identisch. `check_storage(cfg) -> list` mit Ergebnisname `storage:post-images` in Task 5 Test und Code identisch. `default_protokoll_pfad()` in Task 7 Test und Code identisch.

Platzhalter: `<PLAN_COPY_ID>`, `<TOPICS_COPY_ID>`, `<URL aus der Ausgabe>`, `N`, `DD` sind Laufzeitwerte, die erst waehrend der Ausfuehrung entstehen; jeder ist im jeweiligen Schritt benannt.
