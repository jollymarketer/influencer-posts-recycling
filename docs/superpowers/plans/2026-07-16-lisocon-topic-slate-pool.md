# Lisocon Topic Slate + Persistent Candidate Pool — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the lisocon winner-per-run flow with a two-stage slate model: Mon+Thu the engine presents a 10-candidate topic slate in Notion, Jae picks, drafts are written for picked topics, images are generated only after human text approval. Non-picked candidates persist in a Supabase pool (60-day aging, 3-strike retirement) and re-compete.

**Architecture:** New `tools/topic_pool.py` (PostgREST wrapper for `blog_content_mining.topic_candidates` + `engine_meta`), new `run_slate.py` (three-phase orchestrator: images -> drafts -> slate), extensions to `tools/post_scorer.py` (per-tenant scoring model, classify fields), `tools/notion_db.py` (slate entries, status getters, archive), `tools/image_repair.py` (fill missing images on Approved rows). Everything behind `FEATURES["slate_mode"]`; jolly byte-identical.

**Tech Stack:** Python 3, Anthropic SDK, Notion REST API, Supabase PostgREST, kie.ai, pytest.

**Spec:** `docs/superpowers/specs/2026-07-16-lisocon-topic-slate-pool-design.md`

## Global Constraints

- Feature gate: `FEATURES["slate_mode"]` — default absent/False; only `clients/lisocon/config.py` sets True. Jolly behavior byte-identical.
- Scoring model per tenant: lisocon `claude-sonnet-4-6`, jolly stays `claude-haiku-4-5-20251001`.
- MIN_SCORE = 25 (same gate as run_research.py).
- Slate: 10 rows, 5 kaeufer + 5 anwender; fill from other side and mark if short.
- Pool aging 60 days; retirement at `times_slated >= 3`.
- Notion statuses added: `Themenvorschlag`, `Topic Approved`. `Posted` stays machine-only.
- Notion title rule (leak 2026-07-10): titles NEVER from influencer name or original text — only own generated text (`topic_angle_de`).
- All Notion writes for optional selects non-fatal (existing convention).
- Working dir for all commands: `Jolly Automations/Jolly Influencer Post Recycling`.
- Do NOT commit the 4 pre-existing dirty files from another session (`clients/jolly/config.py`, `clients/jolly/influencers.csv`, `clients/lisocon/config.py` hashtag hunk, `tools/post_scorer.py` pre-existing hunks). Stage selectively with `git add -p` or exact paths; for config.py/post_scorer.py ONLY stage hunks belonging to this plan.
- PAUSED=1 is set on the lisocon Railway service; pushes are deploy-inert for lisocon. Do not remove it in any task except the final rollout task.

---

### Task 1: Supabase tables `topic_candidates` + `engine_meta`

**Files:**
- Create: `scripts/setup_topic_pool_tables.sql`

**Interfaces:**
- Produces: tables `blog_content_mining.topic_candidates` and `blog_content_mining.engine_meta` reachable via PostgREST with the existing service key.

- [ ] **Step 1: Write the SQL file**

```sql
-- scripts/setup_topic_pool_tables.sql
-- Topic candidate pool for the lisocon slate model (spec 2026-07-16).
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
```

- [ ] **Step 2: Execute the SQL**

Preferred: psql via the Supabase pooler (connection string in `C:/Users/richa/Jolly_Claude_Code/.env` as `SUPABASE_DB_URL` or similar; check `.env` first). If no pooler credential exists, print the SQL and ask Richard to paste it into the Supabase SQL editor — do NOT skip verification.

Run (if pooler available): `psql "$SUPABASE_DB_URL" -f scripts/setup_topic_pool_tables.sql`

- [ ] **Step 3: Verify via PostgREST**

```bash
source .env 2>/dev/null; curl -s "$SUPABASE_URL/rest/v1/topic_candidates?select=post_url&limit=1" \
  -H "apikey: $SUPABASE_SERVICE_KEY" -H "Authorization: Bearer $SUPABASE_SERVICE_KEY" \
  -H "Accept-Profile: blog_content_mining"
```

Expected: `[]` (empty array, not an error object).

- [ ] **Step 4: Commit**

```bash
git add scripts/setup_topic_pool_tables.sql
git commit -m "feat(slate): SQL for topic_candidates + engine_meta tables"
```

---

### Task 2: `tools/topic_pool.py` — pool CRUD

**Files:**
- Create: `tools/topic_pool.py`
- Test: `tests/test_topic_pool.py`

**Interfaces:**
- Consumes: env `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` (same as `tools/supabase_db.py`).
- Produces:
  - `upsert_candidates(rows: list[dict]) -> int` — upsert on post_url, merge-duplicates. Rows carry the table's column names directly.
  - `get_pool_urls(client: str) -> set[str]` — ALL states (scrape dedup memory).
  - `get_candidates(client: str, states: list[str]) -> list[dict]` — full rows.
  - `set_state(post_urls: list[str], state: str, extra: dict | None = None) -> None`
  - `unslate_and_strike(post_urls: list[str], max_times_slated: int) -> None` — read rows, per row PATCH `times_slated += 1` and `state = 'retired' if new count >= max else 'pool'`.
  - `retire_aged(client: str, max_age_days: int) -> int` — PATCH state=retired where first_seen_at < cutoff and state in (pool, slated).
  - `get_meta(key: str) -> str` / `set_meta(key: str, value: str) -> None`

Mirror the raw-requests style and mocking conventions of `tools/supabase_db.py` / `tests/test_supabase_db.py` (MagicMock responses, monkeypatched env, assert on URL + headers `Content-Profile: blog_content_mining`).

- [ ] **Step 1: Write failing tests**

```python
# tests/test_topic_pool.py
"""Tests for the topic candidate pool wrapper. Pure, requests mocked."""
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import topic_pool


def _env(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://db.example.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "key")


def test_upsert_candidates_on_conflict_post_url(monkeypatch):
    _env(monkeypatch)
    resp = MagicMock(status_code=201)
    rows = [{"post_url": "https://x.com/p/1", "client": "lisocon", "state": "pool"}]
    with patch("tools.topic_pool.requests.post", return_value=resp) as mock_post:
        n = topic_pool.upsert_candidates(rows)
    assert n == 1
    assert "topic_candidates?on_conflict=post_url" in mock_post.call_args.args[0]
    assert mock_post.call_args.kwargs["headers"]["Content-Profile"] == "blog_content_mining"


def test_get_pool_urls_returns_all_states(monkeypatch):
    _env(monkeypatch)
    resp = MagicMock(status_code=200)
    resp.json.return_value = [{"post_url": "https://x.com/p/1"}, {"post_url": "https://x.com/p/2"}]
    with patch("tools.topic_pool.requests.get", return_value=resp) as mock_get:
        urls = topic_pool.get_pool_urls("lisocon")
    assert urls == {"https://x.com/p/1", "https://x.com/p/2"}
    params = mock_get.call_args.kwargs["params"]
    assert params["client"] == "eq.lisocon"
    assert "state" not in params  # every state counts as dedup memory


def test_get_candidates_filters_states(monkeypatch):
    _env(monkeypatch)
    resp = MagicMock(status_code=200)
    resp.json.return_value = [{"post_url": "u", "state": "pool"}]
    with patch("tools.topic_pool.requests.get", return_value=resp) as mock_get:
        rows = topic_pool.get_candidates("lisocon", ["pool", "slated"])
    assert rows[0]["post_url"] == "u"
    assert mock_get.call_args.kwargs["params"]["state"] == "in.(pool,slated)"


def test_set_state_patches_by_url_list(monkeypatch):
    _env(monkeypatch)
    resp = MagicMock(status_code=204)
    with patch("tools.topic_pool.requests.patch", return_value=resp) as mock_patch:
        topic_pool.set_state(["https://x.com/p/1"], "picked")
    body = mock_patch.call_args.kwargs["json"]
    assert body == {"state": "picked"}
    assert mock_patch.call_args.kwargs["params"]["post_url"] == 'in.("https://x.com/p/1")'


def test_unslate_and_strike_retires_at_threshold(monkeypatch):
    _env(monkeypatch)
    get_resp = MagicMock(status_code=200)
    get_resp.json.return_value = [
        {"post_url": "https://x.com/p/1", "times_slated": 2},
        {"post_url": "https://x.com/p/2", "times_slated": 0},
    ]
    patch_resp = MagicMock(status_code=204)
    with patch("tools.topic_pool.requests.get", return_value=get_resp), \
         patch("tools.topic_pool.requests.patch", return_value=patch_resp) as mock_patch:
        topic_pool.unslate_and_strike(
            ["https://x.com/p/1", "https://x.com/p/2"], max_times_slated=3)
    bodies = [c.kwargs["json"] for c in mock_patch.call_args_list]
    assert {"times_slated": 3, "state": "retired"} in bodies
    assert {"times_slated": 1, "state": "pool"} in bodies


def test_retire_aged_uses_cutoff_and_active_states(monkeypatch):
    _env(monkeypatch)
    resp = MagicMock(status_code=200)
    resp.json.return_value = [{"post_url": "u"}]
    with patch("tools.topic_pool.requests.patch", return_value=resp) as mock_patch:
        n = topic_pool.retire_aged("lisocon", max_age_days=60)
    assert n == 1
    params = mock_patch.call_args.kwargs["params"]
    assert params["client"] == "eq.lisocon"
    assert params["state"] == "in.(pool,slated)"
    assert params["first_seen_at"].startswith("lt.")
    assert mock_patch.call_args.kwargs["json"] == {"state": "retired"}


def test_meta_roundtrip(monkeypatch):
    _env(monkeypatch)
    get_resp = MagicMock(status_code=200)
    get_resp.json.return_value = [{"key": "last_slate_at_lisocon", "value": "2026-07-16"}]
    post_resp = MagicMock(status_code=201)
    with patch("tools.topic_pool.requests.get", return_value=get_resp):
        assert topic_pool.get_meta("last_slate_at_lisocon") == "2026-07-16"
    with patch("tools.topic_pool.requests.post", return_value=post_resp) as mock_post:
        topic_pool.set_meta("last_slate_at_lisocon", "2026-07-17")
    assert "engine_meta?on_conflict=key" in mock_post.call_args.args[0]
```

- [ ] **Step 2: Run tests, verify failure**

Run: `python -m pytest tests/test_topic_pool.py -v`
Expected: FAIL (ModuleNotFoundError: tools.topic_pool)

- [ ] **Step 3: Implement `tools/topic_pool.py`**

```python
"""Supabase PostgREST wrapper for the topic candidate pool (slate model).

Tables: blog_content_mining.topic_candidates + engine_meta
(scripts/setup_topic_pool_tables.sql). Same raw-requests style as
tools/supabase_db.py: service key, no ORM, custom schema headers.
"""
import os
from datetime import datetime, timedelta, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

SCHEMA = "blog_content_mining"
TABLE = "topic_candidates"
META_TABLE = "engine_meta"
TIMEOUT = 30


def _base_url() -> str:
    url = os.environ.get("SUPABASE_URL", "")
    if not url:
        raise RuntimeError("SUPABASE_URL is not set. Add it to .env.")
    return url.rstrip("/")


def _key() -> str:
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not key:
        raise RuntimeError("SUPABASE_SERVICE_KEY is not set. Add it to .env.")
    return key


def _headers_write() -> dict:
    key = _key()
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Content-Profile": SCHEMA,
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }


def _headers_read() -> dict:
    key = _key()
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Accept-Profile": SCHEMA,
    }


def _headers_patch() -> dict:
    h = _headers_write()
    h["Prefer"] = "return=representation"
    return h


def _url_in(urls: list[str]) -> str:
    quoted = ",".join(f'"{u}"' for u in urls)
    return f"in.({quoted})"


def _check(resp) -> None:
    if not (200 <= resp.status_code < 300):
        raise RuntimeError(f"Supabase {resp.status_code}: {resp.text[:300]}")


def upsert_candidates(rows: list[dict]) -> int:
    """Upsert candidate rows on post_url. Rows use table column names."""
    if not rows:
        return 0
    url = f"{_base_url()}/rest/v1/{TABLE}?on_conflict=post_url"
    resp = requests.post(url, headers=_headers_write(), json=rows, timeout=TIMEOUT)
    _check(resp)
    return len(rows)


def get_pool_urls(client: str) -> set:
    """Every known candidate URL regardless of state (scrape dedup memory)."""
    url = f"{_base_url()}/rest/v1/{TABLE}"
    params = {"select": "post_url", "client": f"eq.{client}"}
    resp = requests.get(url, headers=_headers_read(), params=params, timeout=TIMEOUT)
    _check(resp)
    return {r["post_url"] for r in resp.json()}


def get_candidates(client: str, states: list[str]) -> list[dict]:
    url = f"{_base_url()}/rest/v1/{TABLE}"
    params = {
        "select": "*",
        "client": f"eq.{client}",
        "state": f"in.({','.join(states)})",
    }
    resp = requests.get(url, headers=_headers_read(), params=params, timeout=TIMEOUT)
    _check(resp)
    return resp.json()


def set_state(post_urls: list[str], state: str, extra: dict | None = None) -> None:
    if not post_urls:
        return
    url = f"{_base_url()}/rest/v1/{TABLE}"
    params = {"post_url": _url_in(post_urls)}
    body = {"state": state, **(extra or {})}
    resp = requests.patch(url, headers=_headers_write(), params=params,
                          json=body, timeout=TIMEOUT)
    _check(resp)


def unslate_and_strike(post_urls: list[str], max_times_slated: int) -> None:
    """Slate rows that were NOT picked: +1 strike, back to pool or retired.
    Read-modify-write per row (PostgREST has no atomic increment without RPC;
    a slate is <= 10 rows, so N requests are fine)."""
    if not post_urls:
        return
    url = f"{_base_url()}/rest/v1/{TABLE}"
    params = {"select": "post_url,times_slated", "post_url": _url_in(post_urls)}
    resp = requests.get(url, headers=_headers_read(), params=params, timeout=TIMEOUT)
    _check(resp)
    for row in resp.json():
        count = int(row.get("times_slated", 0)) + 1
        state = "retired" if count >= max_times_slated else "pool"
        presp = requests.patch(
            url, headers=_headers_write(),
            params={"post_url": f'eq.{row["post_url"]}'},
            json={"times_slated": count, "state": state}, timeout=TIMEOUT)
        _check(presp)


def retire_aged(client: str, max_age_days: int) -> int:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).isoformat()
    url = f"{_base_url()}/rest/v1/{TABLE}"
    params = {
        "client": f"eq.{client}",
        "state": "in.(pool,slated)",
        "first_seen_at": f"lt.{cutoff}",
    }
    resp = requests.patch(url, headers=_headers_patch(), params=params,
                          json={"state": "retired"}, timeout=TIMEOUT)
    _check(resp)
    try:
        return len(resp.json())
    except Exception:
        return 0


def get_meta(key: str) -> str:
    url = f"{_base_url()}/rest/v1/{META_TABLE}"
    params = {"select": "key,value", "key": f"eq.{key}"}
    resp = requests.get(url, headers=_headers_read(), params=params, timeout=TIMEOUT)
    _check(resp)
    rows = resp.json()
    return rows[0]["value"] if rows else ""


def set_meta(key: str, value: str) -> None:
    url = f"{_base_url()}/rest/v1/{META_TABLE}?on_conflict=key"
    resp = requests.post(url, headers=_headers_write(),
                         json=[{"key": key, "value": value}], timeout=TIMEOUT)
    _check(resp)
```

- [ ] **Step 4: Run tests, verify pass**

Run: `python -m pytest tests/test_topic_pool.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add tools/topic_pool.py tests/test_topic_pool.py
git commit -m "feat(slate): topic_pool PostgREST wrapper (states, strikes, aging, meta)"
```

---

### Task 3: Per-tenant scoring model (`SCORING_MODEL`)

**Files:**
- Modify: `tools/post_scorer.py` (the `client.messages.create(model="claude-haiku-4-5-20251001", ...)` call inside `score_posts`, around line 1066)
- Modify: `clients/lisocon/config.py` (add `SCORING_MODEL`)
- Test: `tests/test_scoring_classify.py` (new file, shared with Task 4)

**Interfaces:**
- Produces: module constant `SCORING_MODEL = getattr(_cfg, "SCORING_MODEL", "claude-haiku-4-5-20251001")` in `tools/post_scorer.py`, used by `score_posts`.
- `clients/lisocon/config.py` gains `SCORING_MODEL = "claude-sonnet-4-6"` (Richard, 2026-07-16).

- [ ] **Step 1: Write failing tests**

```python
# tests/test_scoring_classify.py
"""Per-tenant scoring model + classify fields (slate model, spec 2026-07-16)."""
import importlib
import json
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import post_scorer

jolly = importlib.import_module("clients.jolly.config")
lisocon = importlib.import_module("clients.lisocon.config")


def test_lisocon_scoring_model_is_sonnet():
    assert lisocon.SCORING_MODEL == "claude-sonnet-4-6"


def test_jolly_has_no_scoring_model_override():
    assert getattr(jolly, "SCORING_MODEL", None) is None


def test_score_posts_uses_config_model(monkeypatch):
    fake = MagicMock()
    fake.content = [MagicMock(text=json.dumps({
        "topic_fit": 8, "icp_relevanz": 7, "recyclierbarkeit": 8,
        "einzigartigkeit": 6, "themen_diversitaet": 8, "reasoning": "ok"}))]
    with patch.object(post_scorer, "SCORING_MODEL", "claude-sonnet-4-6"), \
         patch.object(post_scorer.client.messages, "create", return_value=fake) as mock_create:
        post_scorer.score_posts([{
            "influencer": "T", "post_text": "x", "post_url": "u",
            "engagement": {"likes": 0, "comments": 0, "shares": 0}}])
    assert mock_create.call_args.kwargs["model"] == "claude-sonnet-4-6"
```

- [ ] **Step 2: Run tests, verify failure**

Run: `python -m pytest tests/test_scoring_classify.py -v`
Expected: FAIL (`lisocon.SCORING_MODEL` AttributeError; `post_scorer.SCORING_MODEL` missing)

- [ ] **Step 3: Implement**

In `tools/post_scorer.py`, near the other `_cfg`-derived module constants (top of file, after `_cfg = load_client()` equivalent):

```python
# Scoring-Modell pro Mandant (Richard 2026-07-16): lisocon scored mit Sonnet,
# jolly bleibt auf Haiku (keine stille Kostenerhoehung beim Fremd-Mandanten).
SCORING_MODEL = getattr(_cfg, "SCORING_MODEL", "claude-haiku-4-5-20251001")
```

In `score_posts`, replace the hardcoded model:

```python
            response = client.messages.create(
                model=SCORING_MODEL,
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}],
            )
```

In `clients/lisocon/config.py`, next to `IMAGE_LANGUAGE`:

```python
# Scoring-Modell (Richard 2026-07-16): Slate-Klassifikation (Persona, VoC,
# Themen-Winkel) braucht mehr Praezision als Haiku liefert.
SCORING_MODEL = "claude-sonnet-4-6"
```

CAUTION: `clients/lisocon/config.py` has an uncommitted foreign hunk (HASHTAG_LINE). Stage only your own hunk (`git add -p`).

- [ ] **Step 4: Run tests, verify pass**

Run: `python -m pytest tests/test_scoring_classify.py tests/test_poster_split.py -v`
Expected: PASS (incl. existing jolly-unchanged pins)

- [ ] **Step 5: Commit (selective staging)**

```bash
git add tests/test_scoring_classify.py
git add -p tools/post_scorer.py clients/lisocon/config.py
git commit -m "feat(slate): per-tenant SCORING_MODEL (lisocon sonnet, jolly haiku)"
```

---

### Task 4: Classify fields in scoring (`classify=True`)

**Files:**
- Modify: `tools/post_scorer.py` (`score_posts` signature + prompt assembly)
- Test: `tests/test_scoring_classify.py` (extend)

**Interfaces:**
- Produces: `score_posts(posts, recent_drafts=None, classify=False)`. With `classify=True` the prompt gains a classification block and each scored dict additionally carries `persona`, `voc_hit`, `topic_angle_de`, `matrix_job`, `matrix_stage` (strings, empty-string fallback). With `classify=False` output and prompt are byte-identical to today (jolly pin).

- [ ] **Step 1: Write failing tests (append to tests/test_scoring_classify.py)**

```python
_CLASSIFY_JSON = {
    "topic_fit": 8, "icp_relevanz": 7, "recyclierbarkeit": 8,
    "einzigartigkeit": 6, "themen_diversitaet": 8, "reasoning": "ok",
    "persona": "kaeufer", "voc_hit": "versteckte DTP-Kostenlinie",
    "topic_angle_de": "Warum jede Sprachversion ein zweites Budget frisst",
    "matrix_job": "Perspective", "matrix_stage": "Awareness",
}


def _scored_with(monkeypatch, payload, classify):
    fake = MagicMock()
    fake.content = [MagicMock(text=json.dumps(payload))]
    with patch.object(post_scorer.client.messages, "create", return_value=fake) as mc:
        out = post_scorer.score_posts([{
            "influencer": "T", "post_text": "x", "post_url": "u",
            "engagement": {"likes": 0, "comments": 0, "shares": 0}}],
            classify=classify)
    return out, mc


def test_classify_adds_fields_to_result(monkeypatch):
    out, _ = _scored_with(monkeypatch, _CLASSIFY_JSON, classify=True)
    assert out[0]["persona"] == "kaeufer"
    assert out[0]["voc_hit"] == "versteckte DTP-Kostenlinie"
    assert out[0]["topic_angle_de"].startswith("Warum")
    assert out[0]["matrix_job"] == "Perspective"
    assert out[0]["matrix_stage"] == "Awareness"


def test_classify_prompt_contains_classification_block(monkeypatch):
    _, mc = _scored_with(monkeypatch, _CLASSIFY_JSON, classify=True)
    prompt = mc.call_args.kwargs["messages"][0]["content"]
    assert "persona" in prompt and "topic_angle_de" in prompt
    assert "matrix_job" in prompt


def test_no_classify_prompt_unchanged(monkeypatch):
    base = {"topic_fit": 8, "icp_relevanz": 7, "recyclierbarkeit": 8,
            "einzigartigkeit": 6, "themen_diversitaet": 8, "reasoning": "ok"}
    _, mc = _scored_with(monkeypatch, base, classify=False)
    prompt = mc.call_args.kwargs["messages"][0]["content"]
    assert "topic_angle_de" not in prompt
    assert "matrix_job" not in prompt


def test_classify_missing_fields_fall_back_to_empty(monkeypatch):
    base = {"topic_fit": 8, "icp_relevanz": 7, "recyclierbarkeit": 8,
            "einzigartigkeit": 6, "themen_diversitaet": 8, "reasoning": "ok"}
    out, _ = _scored_with(monkeypatch, base, classify=True)
    assert out[0]["persona"] == ""
    assert out[0]["topic_angle_de"] == ""
```

- [ ] **Step 2: Run tests, verify failure**

Run: `python -m pytest tests/test_scoring_classify.py -v`
Expected: new tests FAIL (unexpected keyword `classify`)

- [ ] **Step 3: Implement in `tools/post_scorer.py`**

Module-level, next to SCORING_PROMPT:

```python
# Klassifikations-Zusatz fuer den Slate-Modus (spec 2026-07-16): Persona,
# VoC-Treffer, Themen-Winkel und Matrix-Box werden beim Einlagern in den
# Kandidaten-Pool miterhoben. Nur aktiv bei score_posts(classify=True);
# der Jolly-Pfad (classify=False) bleibt byte-identisch.
CLASSIFY_SECTION = """
Zusaetzlich klassifiziere den Post (Felder im selben JSON):
- "persona": genau eine von [[CLASSIFY_PERSONA_IDS]] — wen adressiert ein daraus
  gemachter Post staerker?
- "voc_hit": trifft das Thema einen der im KONTEXT belegten VoC-Schmerzen?
  Dann benenne ihn kurz woertlich, sonst leerer String.
- "topic_angle_de": EIN deutscher Satz — worueber unser Post gehen wuerde
  (eigenstaendiger Blickwinkel, kein Zitat des Originals).
- "matrix_job": genau eine von Perspective, Proof, Promotion.
- "matrix_stage": genau eine von Awareness, Education, Selection."""

_CLASSIFY_FIELDS = ("persona", "voc_hit", "topic_angle_de", "matrix_job", "matrix_stage")


def _classify_section() -> str:
    ids = ", ".join(p.get("id", "") for p in getattr(_cfg, "CONTENT_PERSONAS", []) or [])
    return CLASSIFY_SECTION.replace("[[CLASSIFY_PERSONA_IDS]]", ids or "kaeufer, anwender")
```

In `score_posts`:

```python
def score_posts(posts: list, recent_drafts: list[str] | None = None,
                classify: bool = False) -> list:
```

Prompt assembly inside the loop (after `prompt = SCORING_PROMPT.format(...)`):

```python
            if classify:
                prompt += _classify_section()
```

Model call `max_tokens`:

```python
                max_tokens=500 if classify else 300,
```

Result dict (after `scores = json.loads(raw)`), before building `scored.append`:

```python
            extra = {}
            if classify:
                extra = {f: str(scores.get(f, "") or "") for f in _CLASSIFY_FIELDS}
```

and merge into the result:

```python
            scored.append({
                **post,
                **extra,
                "score": total,
                "score_details": {**scores, "viralitaet": virality_score},
                "reasoning": scores.get("reasoning", ""),
            })
```

- [ ] **Step 4: Run full suite**

Run: `python -m pytest tests/ -v --timeout=120 -q`
Expected: all PASS (201 existing + new)

- [ ] **Step 5: Commit (selective staging)**

```bash
git add tests/test_scoring_classify.py
git add -p tools/post_scorer.py
git commit -m "feat(slate): classify fields (persona, voc_hit, angle, matrix box) in scoring"
```

---

### Task 5: Notion — slate entries, status getters, archive

**Files:**
- Modify: `tools/notion_db.py`
- Test: `tests/test_notion_slate.py`

**Interfaces:**
- Produces:
  - `create_slate_entry(candidate: dict, matrix_prio: bool = False) -> str` — page with Status `Themenvorschlag`; Title = `candidate["topic_angle_de"][:60]` or fallback `"Themenvorschlag"` (leak rule: never influencer/original text); properties Influencer, LinkedIn Post URL, Post Excerpt (`post_text[:300]`), Date Scraped (now), Persona, Poster (derived via `POSTER_BY_PERSONA`), Matrix-Job, Matrix-Stage (selects, non-fatal), Score (number), VoC-Treffer, Themen-Winkel (rich_text), Matrix-Prio (checkbox). Body: H2 "Original Post" + bookmark + H2 "Post Text (Original)" + excerpt paragraphs.
  - `get_pages_by_status(status: str) -> list[dict]` — each `{"page_id", "post_url", "persona", "poster", "matrix_job", "matrix_stage"}`.
  - `get_approved_missing_image() -> list[dict]` — Status=Approved AND Image is_empty; `{"page_id", "post_url"}`.
  - `archive_page(page_id: str) -> None` — PATCH `{"archived": true}`.

Follow the existing raw-requests + `_notion_request` conventions; selects via `_patch_select_nonfatal` where the property might be missing. Tests mock `_notion_request` like `tests/test_notion_db_matrix.py` does.

- [ ] **Step 1: Read `tests/test_notion_db_matrix.py` mocking pattern, write failing tests**

```python
# tests/test_notion_slate.py
"""Slate-Notion-Layer: Themenvorschlag-Zeilen, Status-Getter, Archiv."""
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import notion_db

_CAND = {
    "post_url": "https://x.com/p/1",
    "influencer": "Alice",
    "post_text": "Original body text",
    "topic_angle_de": "Warum jede Sprachversion ein zweites Budget frisst",
    "persona": "kaeufer",
    "voc_hit": "versteckte DTP-Kostenlinie",
    "matrix_job": "Perspective",
    "matrix_stage": "Awareness",
    "score_total": 41,
}


def _resp(payload, status=200):
    r = MagicMock(status_code=status)
    r.json.return_value = payload
    r.raise_for_status = MagicMock()
    return r


def test_create_slate_entry_status_and_title(monkeypatch):
    monkeypatch.setattr(notion_db, "NOTION_DB_ID", "db")
    with patch.object(notion_db, "_notion_request",
                      return_value=_resp({"id": "page-1"})) as req:
        page_id = notion_db.create_slate_entry(_CAND, matrix_prio=True)
    assert page_id == "page-1"
    body = req.call_args.kwargs["json"]
    props = body["properties"]
    assert props["Status"]["select"]["name"] == "Themenvorschlag"
    title = props["Title"]["title"][0]["text"]["content"]
    assert title.startswith("Warum jede")
    assert "Alice" not in title  # leak rule
    assert props["Score"]["number"] == 41
    assert props["Matrix-Prio"]["checkbox"] is True
    assert props["Poster"]["select"]["name"] == "Reinhard"  # kaeufer -> Reinhard


def test_create_slate_entry_title_fallback(monkeypatch):
    monkeypatch.setattr(notion_db, "NOTION_DB_ID", "db")
    cand = {**_CAND, "topic_angle_de": ""}
    with patch.object(notion_db, "_notion_request",
                      return_value=_resp({"id": "p"})) as req:
        notion_db.create_slate_entry(cand)
    title = req.call_args.kwargs["json"]["properties"]["Title"]["title"][0]["text"]["content"]
    assert title == "Themenvorschlag"


def test_get_pages_by_status_extracts_fields(monkeypatch):
    monkeypatch.setattr(notion_db, "NOTION_DB_ID", "db")
    payload = {"results": [{
        "id": "page-1",
        "properties": {
            "LinkedIn Post URL": {"url": "https://x.com/p/1"},
            "Persona": {"select": {"name": "kaeufer"}},
            "Poster": {"select": {"name": "Reinhard"}},
            "Matrix-Job": {"select": {"name": "Proof"}},
            "Matrix-Stage": {"select": {"name": "Education"}},
        }}], "has_more": False}
    with patch.object(notion_db, "_notion_request", return_value=_resp(payload)) as req:
        rows = notion_db.get_pages_by_status("Topic Approved")
    assert rows == [{"page_id": "page-1", "post_url": "https://x.com/p/1",
                     "persona": "kaeufer", "poster": "Reinhard",
                     "matrix_job": "Proof", "matrix_stage": "Education"}]
    flt = req.call_args.kwargs["json"]["filter"]
    assert flt == {"property": "Status", "select": {"equals": "Topic Approved"}}


def test_get_approved_missing_image_filter(monkeypatch):
    monkeypatch.setattr(notion_db, "NOTION_DB_ID", "db")
    payload = {"results": [], "has_more": False}
    with patch.object(notion_db, "_notion_request", return_value=_resp(payload)) as req:
        notion_db.get_approved_missing_image()
    flt = req.call_args.kwargs["json"]["filter"]
    assert {"property": "Status", "select": {"equals": "Approved"}} in flt["and"]
    assert {"property": "Image", "files": {"is_empty": True}} in flt["and"]


def test_archive_page(monkeypatch):
    with patch.object(notion_db, "_notion_request", return_value=_resp({})) as req:
        notion_db.archive_page("page-1")
    assert req.call_args.args[0] == "PATCH"
    assert req.call_args.kwargs["json"] == {"archived": True}
```

- [ ] **Step 2: Run tests, verify failure**

Run: `python -m pytest tests/test_notion_slate.py -v`
Expected: FAIL (AttributeError create_slate_entry)

- [ ] **Step 3: Implement in `tools/notion_db.py`**

Add after `create_post_entry` (uses existing `_headers`, `_notion_request`, `_rich_text_prop`, `_sanitize`, `NOTION_API`, `NOTION_DB_ID`, and `load_client` import pattern used in the module):

```python
def create_slate_entry(candidate: dict, matrix_prio: bool = False) -> str:
    """Themenvorschlag-Zeile fuer den Slate-Modus (spec 2026-07-16).
    Nur Thema-Felder, kein Draft, kein Bild. Titel-Leak-Regel: NIE
    Influencer-Name oder Original-Text — nur der eigene Themen-Winkel."""
    from clients import load_client
    cfg = load_client()
    angle = _sanitize(candidate.get("topic_angle_de", "")).strip()
    title = angle[:60] if angle else "Themenvorschlag"
    persona = candidate.get("persona", "")
    poster_map = getattr(cfg, "POSTER_BY_PERSONA", None) or {}
    poster = poster_map.get(persona, getattr(cfg, "POSTER_DEFAULT", ""))
    excerpt = _sanitize(candidate.get("post_text", ""))[:300]

    props = {
        "Title": {"title": [{"text": {"content": title}}]},
        "Status": {"select": {"name": "Themenvorschlag"}},
        "Influencer": {"rich_text": _rich_text_prop(_sanitize(candidate.get("influencer", "")))},
        "LinkedIn Post URL": {"url": candidate["post_url"]},
        "Post Excerpt": {"rich_text": _rich_text_prop(excerpt)},
        "Date Scraped": {"date": {"start": datetime.now(timezone.utc).isoformat()}},
        "Score": {"number": int(candidate.get("score_total", 0))},
        "VoC-Treffer": {"rich_text": _rich_text_prop(_sanitize(candidate.get("voc_hit", "")))},
        "Themen-Winkel": {"rich_text": _rich_text_prop(angle)},
        "Matrix-Prio": {"checkbox": bool(matrix_prio)},
    }
    for prop, value in (("Persona", persona), ("Poster", poster),
                        ("Matrix-Job", candidate.get("matrix_job", "")),
                        ("Matrix-Stage", candidate.get("matrix_stage", ""))):
        if value:
            props[prop] = {"select": {"name": value}}

    children = [
        _h2_block("Original Post"),
        {"object": "block", "type": "bookmark",
         "bookmark": {"url": candidate["post_url"]}},
        _h2_block("Post Text (Original)"),
    ] + _para_blocks(excerpt)

    resp = _notion_request(
        "POST", f"{NOTION_API}/pages", headers=_headers(),
        json={"parent": {"database_id": NOTION_DB_ID},
              "properties": props, "children": children})
    resp.raise_for_status()
    return resp.json()["id"]


def _query_db(filter_: dict) -> list[dict]:
    results, cursor = [], None
    while True:
        body = {"filter": filter_, "page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        resp = _notion_request(
            "POST", f"{NOTION_API}/databases/{NOTION_DB_ID}/query",
            headers=_headers(), json=body)
        resp.raise_for_status()
        data = resp.json()
        results.extend(data["results"])
        if not data.get("has_more"):
            break
        cursor = data["next_cursor"]
    return results


def _select_name(props: dict, name: str) -> str:
    return ((props.get(name) or {}).get("select") or {}).get("name", "") or ""


def get_pages_by_status(status: str) -> list[dict]:
    """Slate-Modus: Seiten in einem Status inkl. der Routing-Felder."""
    pages = _query_db({"property": "Status", "select": {"equals": status}})
    rows = []
    for page in pages:
        props = page.get("properties", {})
        rows.append({
            "page_id": page["id"],
            "post_url": (props.get("LinkedIn Post URL") or {}).get("url") or "",
            "persona": _select_name(props, "Persona"),
            "poster": _select_name(props, "Poster"),
            "matrix_job": _select_name(props, "Matrix-Job"),
            "matrix_stage": _select_name(props, "Matrix-Stage"),
        })
    return rows


def get_approved_missing_image() -> list[dict]:
    """Phase A des Slate-Modus: text-freigegebene Zeilen ohne Bild."""
    pages = _query_db({"and": [
        {"property": "Status", "select": {"equals": "Approved"}},
        {"property": "Image", "files": {"is_empty": True}},
    ]})
    return [{"page_id": p["id"],
             "post_url": ((p.get("properties", {}).get("LinkedIn Post URL") or {})
                          .get("url") or "")}
            for p in pages]


def archive_page(page_id: str) -> None:
    resp = _notion_request("PATCH", f"{NOTION_API}/pages/{page_id}",
                           headers=_headers(), json={"archived": True})
    resp.raise_for_status()
```

Check imports at top of notion_db.py: `datetime`/`timezone` must be imported (they already are for Date Scraped in create_post_entry — verify, add if missing).

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_notion_slate.py tests/test_notion_db_title.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/notion_db.py tests/test_notion_slate.py
git commit -m "feat(slate): notion slate entries, status getters, archive"
```

---

### Task 6: Slate selection logic (`select_slate`) + lisocon config block

**Files:**
- Create: `run_slate.py` (selection function first; orchestration in Tasks 7-9)
- Modify: `clients/lisocon/config.py` (SLATE block + feature flag)
- Test: `tests/test_slate_build.py`

**Interfaces:**
- Consumes: scored+classified candidate dicts (Task 4 shape: `score`, `persona`, plus pool columns).
- Produces:
  - `select_slate(scored: list[dict], cfg) -> list[dict]` — pure. Top `per_persona` per persona side above MIN_SCORE, sorted by score desc; if one side short, fill from the other side's next-best and set `fill_marker=True` on filled rows; total capped at `size`. Each returned dict keeps all input keys.
  - `clients/lisocon/config.py`: `FEATURES["slate_mode"] = True` and

```python
# Slate-Modus (spec 2026-07-16): 2 Slates/Woche (Mo+Do), 10 Kandidaten,
# hart quotiert 5 kaeufer + 5 anwender. Jae pickt fuer beide Poster.
SLATE = {
    "days": (0, 3),          # Mo, Do (weekday())
    "size": 10,
    "per_persona": 5,
    "max_age_days": 60,
    "max_times_slated": 3,
}
```

- [ ] **Step 1: Write failing tests**

```python
# tests/test_slate_build.py
"""select_slate: 5/5-Quota, Fill+Mark, MIN_SCORE-Gate. Pure Logik."""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from run_slate import select_slate, MIN_SCORE

CFG = SimpleNamespace(SLATE={"days": (0, 3), "size": 10, "per_persona": 5,
                             "max_age_days": 60, "max_times_slated": 3})


def _cand(url, persona, score):
    return {"post_url": url, "persona": persona, "score": score}


def test_five_five_quota():
    scored = ([_cand(f"k{i}", "kaeufer", 50 - i) for i in range(8)]
              + [_cand(f"a{i}", "anwender", 50 - i) for i in range(8)])
    slate = select_slate(scored, CFG)
    assert len(slate) == 10
    assert sum(1 for c in slate if c["persona"] == "kaeufer") == 5
    assert sum(1 for c in slate if c["persona"] == "anwender") == 5
    assert not any(c.get("fill_marker") for c in slate)


def test_fill_and_mark_when_one_side_short():
    scored = ([_cand(f"k{i}", "kaeufer", 50 - i) for i in range(2)]
              + [_cand(f"a{i}", "anwender", 40 - i) for i in range(10)])
    slate = select_slate(scored, CFG)
    assert len(slate) == 10
    kaeufer = [c for c in slate if c["persona"] == "kaeufer"]
    assert len(kaeufer) == 2
    filled = [c for c in slate if c.get("fill_marker")]
    assert len(filled) == 3  # anwender rows standing in on the kaeufer side


def test_min_score_gate():
    scored = ([_cand(f"k{i}", "kaeufer", 20) for i in range(5)]
              + [_cand(f"a{i}", "anwender", 30) for i in range(5)])
    slate = select_slate(scored, CFG)
    assert all(c["score"] >= MIN_SCORE for c in slate)
    assert all(c["persona"] == "anwender" for c in slate)


def test_sorted_by_score_within_side():
    scored = [_cand("k1", "kaeufer", 30), _cand("k2", "kaeufer", 45),
              _cand("a1", "anwender", 28), _cand("a2", "anwender", 44)]
    slate = select_slate(scored, CFG)
    kaeufer = [c for c in slate if c["persona"] == "kaeufer"]
    assert kaeufer[0]["post_url"] == "k2"
```

- [ ] **Step 2: Run tests, verify failure**

Run: `python -m pytest tests/test_slate_build.py -v`
Expected: FAIL (no module run_slate)

- [ ] **Step 3: Implement `run_slate.py` (selection only)**

```python
"""
Lisocon Slate-Modus (spec docs/superpowers/specs/2026-07-16-lisocon-topic-slate-pool-design.md).

Drei Phasen pro Cron-Lauf (Mo-Fr 07:00 UTC):
  A (immer):  Status=Approved ohne Bild -> Bild generieren
  B (immer):  Status=Topic Approved -> Draft schreiben -> Ready to Review
  C (Mo+Do):  Scrape -> Pool -> Re-Score -> 10er-Slate nach Notion

Nur aktiv bei FEATURES["slate_mode"] (lisocon). Jolly: run_research.run_daily.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

# Gleicher Score-Gate wie run_research.MIN_SCORE (dort nicht importierbar
# ohne den kompletten Daily-Import-Block zu ziehen).
MIN_SCORE = 25


def select_slate(scored: list, cfg) -> list:
    """Pure Slate-Auswahl: pro Persona-Seite Top-N ueber MIN_SCORE,
    knappe Seite wird von der anderen aufgefuellt (fill_marker=True)."""
    slate_cfg = cfg.SLATE
    per, size = slate_cfg["per_persona"], slate_cfg["size"]
    eligible = sorted((c for c in scored if c.get("score", 0) >= MIN_SCORE),
                      key=lambda c: c["score"], reverse=True)
    sides = {"kaeufer": [], "anwender": []}
    for cand in eligible:
        side = sides.get(cand.get("persona", ""))
        if side is not None and len(side) < per:
            side.append(cand)
    slate = sides["kaeufer"] + sides["anwender"]
    chosen = {c["post_url"] for c in slate}
    for cand in eligible:
        if len(slate) >= size:
            break
        if cand["post_url"] not in chosen:
            slate.append({**cand, "fill_marker": True})
            chosen.add(cand["post_url"])
    return slate[:size]
```

- [ ] **Step 4: Run tests, verify pass**

Run: `python -m pytest tests/test_slate_build.py -v`
Expected: PASS

- [ ] **Step 5: Add lisocon config block (code above in Interfaces), selective staging, commit**

```bash
git add run_slate.py tests/test_slate_build.py
git add -p clients/lisocon/config.py
git commit -m "feat(slate): select_slate quota logic + lisocon slate config"
```

---

### Task 7: Phase C — slate build orchestration

**Files:**
- Modify: `run_slate.py`
- Test: `tests/test_slate_phases.py`

**Interfaces:**
- Consumes: `tools/topic_pool.py` (Task 2), `tools/notion_db.py` (Task 5), `score_posts(classify=True)` (Task 4), existing scrapers (`scrape_new_posts`, `scrape_substack_posts`, `scrape_keyword_posts` via the same pattern as `run_research.scrape_daily_keyword_posts`), `pick_target_box`/`get_recent_boxes` (existing).
- Produces: `phase_slate(cfg, now) -> None` with this exact sequence:

1. Idempotency guard: `get_meta(f"last_slate_at_{cfg.NAME}") == now.date().isoformat()` -> print skip, return.
2. Archive previous slate: `get_pages_by_status("Themenvorschlag")` -> `archive_page` each -> `unslate_and_strike(urls, max_times_slated)`.
3. `retire_aged(cfg.NAME, max_age_days)`.
4. Scrape: dedup set = `get_existing_post_urls() | get_pool_urls(cfg.NAME)`; run the three scrapers non-fatally (same try/except style as run_daily Schritt 2).
5. Upsert new scrapes into pool (`state="pool"`, map post dict -> row like `supabase_db._to_row` plus `client`, `state`).
6. Load full active pool `get_candidates(cfg.NAME, ["pool"])`, convert rows back to scorer post shape (`{"post_url", "influencer", "post_text", "date": row["post_date"] or "", "engagement": {"likes": ..., "comments": ..., "shares": ...}}`).
7. `score_posts(pool_posts, recent_drafts=get_recent_linkedin_drafts(7), classify=True)`.
8. `select_slate(scored, cfg)`.
9. Deficit box: `target_box = pick_target_box(get_recent_boxes(), cfg)` (non-fatal, None on error). For each slate candidate `matrix_prio = target_box is not None and (c["matrix_job"], c["matrix_stage"]) == target_box`.
10. `create_slate_entry(c, matrix_prio)` per candidate (non-fatal per row).
11. Pool writeback: upsert scored fields for ALL scored candidates (`persona`, `voc_hit`, `topic_angle_de`, `matrix_job`, `matrix_stage`, `score_total=score`, `scores=score_details`, `reasoning`, `last_scored_at=now`); `set_state(slate_urls, "slated", {"last_slated_at": now.isoformat()})`.
12. `set_meta(f"last_slate_at_{cfg.NAME}", now.date().isoformat())`.

Abort rule: if any of steps 2, 3, 6 raise (Supabase down), print error and return WITHOUT building a slate from new-only posts (spec: never silently bypass the pool) and WITHOUT setting last_slate_at.

- [ ] **Step 1: Write failing tests (mock all IO at run_slate module level)**

```python
# tests/test_slate_phases.py
"""Phase C: Guard, Archiv+Strike, Pool-Abort, Slate-Schreiben."""
import os
import sys
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import run_slate

CFG = SimpleNamespace(
    NAME="lisocon",
    SLATE={"days": (0, 3), "size": 10, "per_persona": 5,
           "max_age_days": 60, "max_times_slated": 3},
    FEATURES={"slate_mode": True, "keyword_source_daily": False},
)
MON = datetime(2026, 7, 20, 7, 0, tzinfo=timezone.utc)  # Montag


def _patch_all(**overrides):
    mocks = {
        "get_meta": MagicMock(return_value=""),
        "set_meta": MagicMock(),
        "get_pages_by_status": MagicMock(return_value=[]),
        "archive_page": MagicMock(),
        "unslate_and_strike": MagicMock(),
        "retire_aged": MagicMock(return_value=0),
        "get_existing_post_urls": MagicMock(return_value=set()),
        "get_pool_urls": MagicMock(return_value=set()),
        "scrape_all_sources": MagicMock(return_value=[]),
        "upsert_candidates": MagicMock(return_value=0),
        "get_candidates": MagicMock(return_value=[]),
        "get_recent_linkedin_drafts": MagicMock(return_value=[]),
        "score_posts": MagicMock(return_value=[]),
        "get_recent_boxes": MagicMock(return_value=[]),
        "pick_target_box": MagicMock(return_value=None),
        "create_slate_entry": MagicMock(return_value="page-1"),
        "set_state": MagicMock(),
    }
    mocks.update(overrides)
    return patch.multiple(run_slate, **mocks), mocks


def test_guard_skips_second_run_same_day():
    ctx, mocks = _patch_all(get_meta=MagicMock(return_value="2026-07-20"))
    with ctx:
        run_slate.phase_slate(CFG, MON)
    mocks["scrape_all_sources"].assert_not_called()
    mocks["set_meta"].assert_not_called()


def test_previous_slate_archived_and_striked():
    prev = [{"page_id": "p1", "post_url": "u1", "persona": "kaeufer",
             "poster": "Reinhard", "matrix_job": "", "matrix_stage": ""}]
    ctx, mocks = _patch_all(get_pages_by_status=MagicMock(return_value=prev))
    with ctx:
        run_slate.phase_slate(CFG, MON)
    mocks["archive_page"].assert_called_once_with("p1")
    mocks["unslate_and_strike"].assert_called_once_with(["u1"], 3)


def test_pool_error_aborts_without_slate():
    ctx, mocks = _patch_all(
        get_candidates=MagicMock(side_effect=RuntimeError("supabase down")))
    with ctx:
        run_slate.phase_slate(CFG, MON)  # darf nicht raisen
    mocks["create_slate_entry"].assert_not_called()
    mocks["set_meta"].assert_not_called()


def test_slate_written_and_pool_updated():
    pool_row = {"post_url": "u1", "influencer": "A", "post_text": "t",
                "post_date": "2026-07-15", "likes": 1, "comments": 0, "shares": 0}
    scored = [{"post_url": "u1", "influencer": "A", "post_text": "t",
               "score": 40, "score_details": {}, "reasoning": "r",
               "persona": "kaeufer", "voc_hit": "", "topic_angle_de": "Winkel",
               "matrix_job": "Proof", "matrix_stage": "Education"}]
    ctx, mocks = _patch_all(
        get_candidates=MagicMock(return_value=[pool_row]),
        score_posts=MagicMock(return_value=scored),
        pick_target_box=MagicMock(return_value=("Proof", "Education")))
    with ctx:
        run_slate.phase_slate(CFG, MON)
    assert mocks["create_slate_entry"].call_args.kwargs.get("matrix_prio") is True \
        or mocks["create_slate_entry"].call_args.args[1] is True
    mocks["set_state"].assert_called_once()
    assert mocks["set_state"].call_args.args[0] == ["u1"]
    assert mocks["set_state"].call_args.args[1] == "slated"
    mocks["set_meta"].assert_called_once_with("last_slate_at_lisocon", "2026-07-20")
```

- [ ] **Step 2: Run tests, verify failure**

Run: `python -m pytest tests/test_slate_phases.py -v`
Expected: FAIL (phase_slate missing)

- [ ] **Step 3: Implement in `run_slate.py`**

Imports (module top, re-exported names so tests can `patch.multiple(run_slate, ...)`):

```python
from datetime import datetime, timezone

from tools.notion_db import (
    get_existing_post_urls,
    get_recent_linkedin_drafts,
    get_recent_boxes,
    get_pages_by_status,
    create_slate_entry,
    archive_page,
)
from tools.topic_pool import (
    upsert_candidates,
    get_pool_urls,
    get_candidates,
    set_state,
    unslate_and_strike,
    retire_aged,
    get_meta,
    set_meta,
)
from tools.post_scorer import score_posts
from tools.content_matrix import pick_target_box
from tools.linkedin_scraper import scrape_new_posts
from tools.linkedin_keyword_scraper import scrape_keyword_posts
from tools.substack_scraper import scrape_substack_posts
```

```python
def scrape_all_sources(cfg, existing_urls: set) -> list:
    """Alle drei Quellen, jede non-fatal (gleiches Muster wie run_daily Schritt 2)."""
    posts = []
    try:
        posts.extend(scrape_new_posts(existing_urls=existing_urls))
    except Exception as e:
        print(f"  FEHLER - LinkedIn-Scraping: {e}", file=sys.stderr)
    try:
        posts.extend(scrape_substack_posts(existing_urls=existing_urls))
    except Exception as e:
        print(f"  FEHLER - Substack-Scraping: {e}", file=sys.stderr)
    if cfg.FEATURES.get("keyword_source_daily"):
        kw = cfg.DAILY_KEYWORD_SEARCH
        try:
            seen = set(existing_urls) | {p["post_url"] for p in posts}
            posts.extend(scrape_keyword_posts(
                kw["keywords"], existing_urls=seen,
                max_posts=kw.get("max_posts", 10),
                posted_limit=kw.get("posted_limit", "week")))
        except Exception as e:
            print(f"  FEHLER - Keyword-Scraping: {e}", file=sys.stderr)
    return posts


def _post_to_pool_row(post: dict, client: str) -> dict | None:
    url = post.get("post_url")
    if not url:
        return None
    eng = post.get("engagement", {}) or {}
    date_raw = post.get("date", "")
    return {
        "post_url": url,
        "client": client,
        "source": post.get("source", "linkedin"),
        "influencer": post.get("influencer", ""),
        "post_text": post.get("post_text", ""),
        "post_date": date_raw[:10] if date_raw else None,
        "likes": int(eng.get("likes", 0) or 0),
        "comments": int(eng.get("comments", 0) or 0),
        "shares": int(eng.get("shares", 0) or 0),
        "state": "pool",
    }


def _pool_row_to_post(row: dict) -> dict:
    return {
        "post_url": row["post_url"],
        "influencer": row.get("influencer", ""),
        "post_text": row.get("post_text", ""),
        "date": row.get("post_date") or "",
        "post_excerpt": (row.get("post_text", "") or "")[:300],
        "engagement": {"likes": row.get("likes", 0),
                       "comments": row.get("comments", 0),
                       "shares": row.get("shares", 0)},
    }


def phase_slate(cfg, now) -> None:
    slate_cfg = cfg.SLATE
    meta_key = f"last_slate_at_{cfg.NAME}"
    today = now.date().isoformat()
    print(f"\nPhase C: Slate-Bau ({today}) ...")

    try:
        if get_meta(meta_key) == today:
            print("  Slate heute schon gebaut (Deploy-Re-Run) - Skip.")
            return
    except Exception as e:
        print(f"  FEHLER - Meta-Guard nicht lesbar, Abbruch: {e}", file=sys.stderr)
        return

    try:
        prev = get_pages_by_status("Themenvorschlag")
        for row in prev:
            archive_page(row["page_id"])
        unslate_and_strike([r["post_url"] for r in prev if r["post_url"]],
                           slate_cfg["max_times_slated"])
        retired = retire_aged(cfg.NAME, slate_cfg["max_age_days"])
        if retired:
            print(f"  {retired} Kandidat(en) altersbedingt retired.")
    except Exception as e:
        print(f"  FEHLER - Pool/Archiv nicht erreichbar, Abbruch (kein Slate ohne Pool): {e}",
              file=sys.stderr)
        return

    existing = set()
    try:
        existing = get_existing_post_urls()
    except Exception as e:
        print(f"  FEHLER - Notion-Dedup nicht lesbar: {e}", file=sys.stderr)
    try:
        existing |= get_pool_urls(cfg.NAME)
    except Exception as e:
        print(f"  FEHLER - Pool-Dedup nicht lesbar, Abbruch: {e}", file=sys.stderr)
        return

    new_posts = scrape_all_sources(cfg, existing)
    print(f"  Scrape: {len(new_posts)} neue Posts")
    rows = [r for r in (_post_to_pool_row(p, cfg.NAME) for p in new_posts) if r]
    try:
        upsert_candidates(rows)
        pool_rows = get_candidates(cfg.NAME, ["pool"])
    except Exception as e:
        print(f"  FEHLER - Pool nicht erreichbar, Abbruch (kein Slate ohne Pool): {e}",
              file=sys.stderr)
        return
    print(f"  Aktiver Pool: {len(pool_rows)} Kandidaten")
    if not pool_rows:
        print("  Leerer Pool - kein Slate.")
        return

    try:
        recent_drafts = get_recent_linkedin_drafts(7)
    except Exception:
        recent_drafts = []
    scored = score_posts([_pool_row_to_post(r) for r in pool_rows],
                         recent_drafts=recent_drafts, classify=True)

    slate = select_slate(scored, cfg)
    if not slate:
        print(f"  Kein Kandidat ueber Mindest-Score {MIN_SCORE} - kein Slate.")
        return

    target_box = None
    try:
        target_box = pick_target_box(get_recent_boxes(), cfg)
    except Exception as e:
        print(f"  Matrix-Coverage nicht lesbar (nicht kritisch): {e}", file=sys.stderr)

    written = []
    for cand in slate:
        prio = bool(target_box) and (cand.get("matrix_job", ""),
                                     cand.get("matrix_stage", "")) == target_box
        try:
            create_slate_entry(cand, prio)
            written.append(cand["post_url"])
        except Exception as e:
            print(f"  FEHLER - Slate-Zeile {cand['post_url']}: {e}", file=sys.stderr)

    now_iso = now.isoformat()
    try:
        upsert_candidates([{
            "post_url": c["post_url"], "client": cfg.NAME,
            "persona": c.get("persona", ""), "voc_hit": c.get("voc_hit", ""),
            "topic_angle_de": c.get("topic_angle_de", ""),
            "matrix_job": c.get("matrix_job", ""),
            "matrix_stage": c.get("matrix_stage", ""),
            "score_total": int(c.get("score", 0)),
            "scores": c.get("score_details", {}),
            "reasoning": c.get("reasoning", ""),
            "last_scored_at": now_iso,
        } for c in scored])
        set_state(written, "slated", {"last_slated_at": now_iso})
        set_meta(meta_key, today)
    except Exception as e:
        print(f"  FEHLER - Pool-Writeback: {e}", file=sys.stderr)
    print(f"  Slate geschrieben: {len(written)}/{len(slate)} Zeilen.")
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_slate_phases.py tests/test_slate_build.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add run_slate.py tests/test_slate_phases.py
git commit -m "feat(slate): phase C slate build (archive, strike, rescore, write)"
```

---

### Task 8: Phase B — drafts for picked topics

**Files:**
- Modify: `run_slate.py`
- Test: `tests/test_slate_phases.py` (extend)

**Interfaces:**
- Consumes: `get_pages_by_status("Topic Approved")`, `get_candidates`, existing generation stack (`generate_post_and_image_prompt`, `pick_format`, `formats_for_box`, `free_formats`, `figures_ok`, `asset_for_format`, `get_recent_assets`, `assets_block`, `persona_block`, `get_recent_formats`, `get_recent_infographic_types`, `parse_infographic_type`, `normalize_infographic_type`, `skeleton_signals`, `select_archetype`, `build_archetype_prompt`, `get_recent_archetypes`, `update_with_draft`, `FORMAT_TO_BOX`, `FORMAT_ASSET_ATTR`).
- Produces: `phase_drafts(cfg) -> None`:

1. `picked = get_pages_by_status("Topic Approved")`; empty -> return.
2. Load pool rows for their URLs (`get_candidates(cfg.NAME, ["slated", "picked", "pool"])`, index by post_url) — a picked row may be in any of these if a human picked late.
3. Per picked page (each error non-fatal per page, print + continue):
   - Rebuild `winner` dict via `_pool_row_to_post(row)`. Missing pool row -> print error, skip page.
   - Persona dict: match `page["persona"]` against `cfg.CONTENT_PERSONAS` by `id`; fallback dominant.
   - Format: `candidates = formats_for_box((page["matrix_job"], page["matrix_stage"]), cfg)` if both set else `free_formats(cfg)`; `post_format = pick_format(winner, get_recent_formats(), candidates=candidates)`.
   - Asset + whitelist backstop + dominant-persona-for-asset-formats: same three rules as `run_daily` (copy the logic, it is ~15 lines).
   - Generate: same `generate_post_and_image_prompt(...)` call as run_daily Schritt 5 (`persona_voice_de` included); EN disabled for lisocon so `en_draft` may be empty.
   - CaseProof figures guard: same retry->downgrade loop as run_daily.
   - Archetype + prompt: same as run_daily Schritt 6 BUT do NOT call `generate_image` — image happens in Phase A after text approval.
   - Write back: `update_with_draft(page_id=page["page_id"], linkedin_draft=..., en_draft="", image_prompt=gen_prompt, image_url="", ..., image_failed=False, ...)` with the same metadata params as run_daily Schritt 7 (post_format, infographic_type, archetype, matrix box from FORMAT_TO_BOX, persona id, poster from page, asset id, post_text, post_url).
   - `set_state([post_url], "picked")`.

Key detail: `update_with_draft` with `image_url=""` and `image_failed=False` must land on Status "Ready to Review" — verify in `tools/notion_db.py` (it does today: status = "Image Failed" if image_failed else "Ready to Review").

- [ ] **Step 1: Write failing test (append to tests/test_slate_phases.py)**

```python
def test_phase_drafts_generates_and_updates(monkeypatch):
    page = {"page_id": "p1", "post_url": "u1", "persona": "kaeufer",
            "poster": "Reinhard", "matrix_job": "Proof", "matrix_stage": "Education"}
    pool_row = {"post_url": "u1", "influencer": "A", "post_text": "t",
                "post_date": "2026-07-15", "likes": 1, "comments": 0, "shares": 0}
    gen = ("DE Draft Text", "", "img prompt", "skeleton", "soundbyte", "kontext")
    cfg = SimpleNamespace(
        NAME="lisocon", CONTENT_PERSONAS=[{"id": "kaeufer", "share": "dominant"}],
        SLATE=CFG.SLATE, FEATURES={"slate_mode": True},
        POSTER_BY_PERSONA={"kaeufer": "Reinhard"}, POSTER_DEFAULT="Reinhard",
        IMAGE_LANGUAGE="German")
    mocks = {
        "get_pages_by_status": MagicMock(return_value=[page]),
        "get_candidates": MagicMock(return_value=[pool_row]),
        "get_recent_formats": MagicMock(return_value=[]),
        "get_recent_infographic_types": MagicMock(return_value=[]),
        "get_recent_archetypes": MagicMock(return_value=[]),
        "get_recent_assets": MagicMock(return_value=[]),
        "generate_post_and_image_prompt": MagicMock(return_value=gen),
        "update_with_draft": MagicMock(),
        "set_state": MagicMock(),
    }
    with patch.multiple(run_slate, **mocks):
        run_slate.phase_drafts(cfg)
    kwargs = mocks["update_with_draft"].call_args.kwargs
    assert kwargs["page_id"] == "p1"
    assert kwargs["linkedin_draft"] == "DE Draft Text"
    assert kwargs["image_url"] == ""
    assert kwargs["image_failed"] is False
    assert kwargs["poster"] == "Reinhard"
    mocks["set_state"].assert_called_once_with(["u1"], "picked")


def test_phase_drafts_skips_page_without_pool_row():
    page = {"page_id": "p1", "post_url": "u-missing", "persona": "kaeufer",
            "poster": "Reinhard", "matrix_job": "", "matrix_stage": ""}
    cfg = SimpleNamespace(
        NAME="lisocon", CONTENT_PERSONAS=[], SLATE=CFG.SLATE,
        FEATURES={"slate_mode": True}, POSTER_BY_PERSONA=None,
        POSTER_DEFAULT="", IMAGE_LANGUAGE="German")
    mocks = {
        "get_pages_by_status": MagicMock(return_value=[page]),
        "get_candidates": MagicMock(return_value=[]),
        "update_with_draft": MagicMock(),
        "set_state": MagicMock(),
    }
    with patch.multiple(run_slate, **mocks):
        run_slate.phase_drafts(cfg)  # darf nicht raisen
    mocks["update_with_draft"].assert_not_called()
```

- [ ] **Step 2: Run, verify failure** — `python -m pytest tests/test_slate_phases.py -v` -> FAIL (phase_drafts missing)

- [ ] **Step 3: Implement `phase_drafts` in run_slate.py**

Additional imports:

```python
from tools.notion_db import (
    get_recent_formats,
    get_recent_infographic_types,
    get_recent_archetypes,
    get_recent_assets,
    update_with_draft,
)
from tools.post_scorer import (
    generate_post_and_image_prompt,
    pick_format,
    parse_infographic_type,
    normalize_infographic_type,
    persona_block,
    assets_block,
)
from tools.content_matrix import (
    FORMAT_ASSET_ATTR,
    FORMAT_TO_BOX,
    asset_for_format,
    figures_ok,
    formats_for_box,
    free_formats,
)
from tools.image_archetypes import (
    select_archetype,
    build_archetype_prompt,
    skeleton_signals,
)
```

```python
def _persona_by_id(cfg, persona_id: str) -> dict | None:
    personas = getattr(cfg, "CONTENT_PERSONAS", None) or []
    hit = next((p for p in personas if p.get("id") == persona_id), None)
    if hit:
        return hit
    return next((p for p in personas if p.get("share") == "dominant"), None)


def phase_drafts(cfg) -> None:
    print("\nPhase B: Drafts fuer gepickte Themen ...")
    try:
        picked = get_pages_by_status("Topic Approved")
    except Exception as e:
        print(f"  FEHLER - Notion nicht lesbar: {e}", file=sys.stderr)
        return
    if not picked:
        print("  Keine Picks.")
        return
    try:
        pool = {r["post_url"]: r
                for r in get_candidates(cfg.NAME, ["slated", "picked", "pool"])}
    except Exception as e:
        print(f"  FEHLER - Pool nicht lesbar: {e}", file=sys.stderr)
        return

    for page in picked:
        try:
            _draft_one(cfg, page, pool)
        except Exception as e:
            print(f"  FEHLER - Draft fuer {page['post_url']}: {e}", file=sys.stderr)


def _draft_one(cfg, page: dict, pool: dict) -> None:
    row = pool.get(page["post_url"])
    if not row:
        print(f"  Kein Pool-Kandidat fuer {page['post_url']} - Skip.", file=sys.stderr)
        return
    winner = _pool_row_to_post(row)

    persona = _persona_by_id(cfg, page.get("persona", ""))
    try:
        recent_formats = get_recent_formats()
    except Exception:
        recent_formats = []
    box = (page.get("matrix_job", ""), page.get("matrix_stage", ""))
    candidates = formats_for_box(box, cfg) if all(box) else free_formats(cfg)
    post_format = pick_format(winner, recent_formats, candidates=candidates)

    chosen_asset = None
    try:
        chosen_asset = asset_for_format(post_format, cfg, get_recent_assets())
    except Exception as e:
        print(f"  Asset-Wahl fehlgeschlagen (nicht kritisch): {e}", file=sys.stderr)
    if post_format in FORMAT_ASSET_ATTR and not chosen_asset:
        post_format = pick_format(winner, recent_formats, candidates=free_formats(cfg))
    if persona and post_format in FORMAT_ASSET_ATTR:
        personas = getattr(cfg, "CONTENT_PERSONAS", None) or []
        dominant = next((p for p in personas if p.get("share") == "dominant"), None)
        if dominant:
            persona = dominant

    try:
        recent_infographic_types = get_recent_infographic_types()
    except Exception:
        recent_infographic_types = []
    try:
        recent_archetypes = get_recent_archetypes()
    except Exception:
        recent_archetypes = []

    linkedin_draft, en_draft, image_prompt, skeleton, sound_byte, kontext = \
        generate_post_and_image_prompt(
            winner, post_format,
            recent_infographic_types=recent_infographic_types,
            assets_de=assets_block(post_format, chosen_asset, "de"),
            assets_en=assets_block(post_format, chosen_asset, "en"),
            persona_de=persona_block(persona, "de"),
            persona_en=persona_block(persona, "en"),
            persona_voice_de=(persona or {}).get("voice_de", ""),
        )
    if not linkedin_draft:
        print(f"  Leerer Draft fuer {page['post_url']} - Skip.", file=sys.stderr)
        return

    if post_format == "CaseProof" and chosen_asset:
        for attempt in ("retry", "downgrade"):
            if figures_ok(f"{linkedin_draft}\n{en_draft}", chosen_asset):
                break
            if attempt == "retry":
                linkedin_draft, en_draft, image_prompt, skeleton, sound_byte, kontext = \
                    generate_post_and_image_prompt(
                        winner, post_format,
                        recent_infographic_types=recent_infographic_types,
                        assets_de=assets_block(post_format, chosen_asset, "de"),
                        assets_en=assets_block(post_format, chosen_asset, "en"),
                        persona_de=persona_block(persona, "de"),
                        persona_en=persona_block(persona, "en"),
                    )
            else:
                post_format = "Method"
                chosen_asset = None
                linkedin_draft, en_draft, image_prompt, skeleton, sound_byte, kontext = \
                    generate_post_and_image_prompt(
                        winner, post_format,
                        recent_infographic_types=recent_infographic_types,
                        persona_de=persona_block(persona, "de"),
                        persona_en=persona_block(persona, "en"),
                    )
        if not linkedin_draft:
            print(f"  Leerer Draft nach Guard fuer {page['post_url']} - Skip.",
                  file=sys.stderr)
            return

    infographic_type = normalize_infographic_type(parse_infographic_type(skeleton))
    sig = skeleton_signals(skeleton, sound_byte)
    chosen_archetype = select_archetype(
        post_format=post_format, infographic_type=infographic_type,
        layers_count=sig["layers_count"], has_metaphor=sig["has_metaphor"],
        has_stat=sig["has_stat"], recent_archetypes=recent_archetypes)
    gen_archetype, gen_prompt, gen_ratio, gen_strip = build_archetype_prompt(
        chosen_archetype, soundbyte=sound_byte, kontext=kontext, skeleton=skeleton,
        language=getattr(cfg, "IMAGE_LANGUAGE", "English"))

    matrix_box = FORMAT_TO_BOX.get(post_format, ("", ""))
    update_with_draft(
        page_id=page["page_id"],
        linkedin_draft=linkedin_draft,
        en_draft="",
        image_prompt=gen_prompt,
        image_url="",
        title=winner.get("post_excerpt", "")[:60],
        influencer=winner["influencer"],
        image_failed=False,
        image_error="",
        infographic_skeleton=skeleton,
        post_format=post_format,
        infographic_type=infographic_type,
        archetype=gen_archetype,
        matrix_job=matrix_box[0],
        matrix_stage=matrix_box[1],
        persona=(persona or {}).get("id", ""),
        poster=page.get("poster", ""),
        asset_id=(chosen_asset or {}).get("id", ""),
        post_text=winner["post_text"],
        post_url=winner["post_url"],
    )
    set_state([page["post_url"]], "picked")
    print(f"  Draft geschrieben: {page['post_url']} ({post_format})")
```

NOTE: the `title=winner.get("post_excerpt", "")[:60]` argument mirrors run_daily Schritt 7 exactly; `update_with_draft` applies the title-leak rule internally (verify once by reading its body around `tools/notion_db.py:393` before running the test).

- [ ] **Step 4: Run** — `python -m pytest tests/test_slate_phases.py -v` -> PASS

- [ ] **Step 5: Commit**

```bash
git add run_slate.py tests/test_slate_phases.py
git commit -m "feat(slate): phase B drafts for picked topics (no image yet)"
```

---

### Task 9: Phase A — images for approved texts

**Files:**
- Modify: `tools/image_repair.py` (new function beside `repair_wrong_images`, reusing `extract_body_sections`, `_rebuild_page_body`, ASPECT_RATIO, `_NO_STRIP_ARCHETYPES`)
- Modify: `run_slate.py` (thin `phase_images(cfg)` wrapper)
- Test: `tests/test_slate_phases.py` (extend)

**Interfaces:**
- Produces: `fill_missing_images() -> int` in `tools/image_repair.py`: for each row from `get_approved_missing_image()` read body sections, take `image_prompt` (body version, uncapped), determine strip from the page's `Bild-Variante` select (same rule as repair: strip unless archetype in `_NO_STRIP_ARCHETYPES`), call `generate_image(prompt, aspect_ratio=ASPECT_RATIO, strip_marks=...)`, then `_rebuild_page_body(...)` + PATCH Image property, count successes. On image failure per row: set Status "Image Failed" via `set_post_status`, continue. Missing image_prompt in body: print, skip row (stays Approved without image; publish filter blocks it — visible in Notion).
- `run_slate.phase_images(cfg)`: calls `fill_missing_images()` non-fatally, prints count. Mirror `repair_wrong_images`'s existing body-rebuild + property-PATCH mechanics exactly — read that function fully before writing this one.

- [ ] **Step 1: Write failing test (append to tests/test_slate_phases.py)**

```python
def test_phase_images_nonfatal():
    with patch.object(run_slate, "fill_missing_images",
                      MagicMock(side_effect=RuntimeError("kie down"))):
        run_slate.phase_images(CFG)  # darf nicht raisen


def test_phase_images_reports_count(capsys):
    with patch.object(run_slate, "fill_missing_images", MagicMock(return_value=2)):
        run_slate.phase_images(CFG)
    assert "2" in capsys.readouterr().out
```

Plus in a new `tests/test_fill_missing_images.py`, mirroring the mocking style of the existing image-repair tests if present (check `ls tests/` — if no repair test exists, mock `get_approved_missing_image`, `extract_body_sections`, `generate_image`, `_rebuild_page_body`, `set_post_status`, and the property-PATCH at `tools.image_repair` module level):

```python
# tests/test_fill_missing_images.py
"""Phase A: Bilder nur fuer text-freigegebene Zeilen ohne Bild."""
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import image_repair


def test_fill_missing_images_generates_and_rebuilds():
    sections = {"image_url": "", "de_draft": "d", "en_draft": "",
                "post_text": "t", "post_url": "u", "skeleton": "s",
                "image_prompt": "prompt text"}
    with patch.object(image_repair, "get_approved_missing_image",
                      return_value=[{"page_id": "p1", "post_url": "u"}]), \
         patch.object(image_repair, "extract_body_sections", return_value=sections), \
         patch.object(image_repair, "_page_archetype", return_value="stat_hero"), \
         patch.object(image_repair, "generate_image",
                      return_value="https://img/x.png") as gen, \
         patch.object(image_repair, "_apply_new_image") as apply_mock:
        n = image_repair.fill_missing_images()
    assert n == 1
    gen.assert_called_once()
    assert gen.call_args.kwargs.get("aspect_ratio") == image_repair.ASPECT_RATIO
    apply_mock.assert_called_once()


def test_fill_missing_images_failure_sets_image_failed():
    sections = {"image_url": "", "de_draft": "d", "en_draft": "",
                "post_text": "t", "post_url": "u", "skeleton": "s",
                "image_prompt": "prompt text"}
    with patch.object(image_repair, "get_approved_missing_image",
                      return_value=[{"page_id": "p1", "post_url": "u"}]), \
         patch.object(image_repair, "extract_body_sections", return_value=sections), \
         patch.object(image_repair, "_page_archetype", return_value=""), \
         patch.object(image_repair, "generate_image",
                      side_effect=RuntimeError("kie down")), \
         patch.object(image_repair, "set_post_status") as status_mock:
        n = image_repair.fill_missing_images()
    assert n == 0
    status_mock.assert_called_once_with("p1", "Image Failed")
```

The helpers `_page_archetype(page_id) -> str` (reads the `Bild-Variante` select) and `_apply_new_image(page_id, sections, image_url)` (body rebuild + Image property PATCH) are extracted from the existing `repair_wrong_images` body — read that function first and factor the shared pieces so repair and fill use the same code path.

- [ ] **Step 2: Run, verify failure** — both new test files FAIL

- [ ] **Step 3: Implement** — read `repair_wrong_images` fully; extract `_page_archetype` + `_apply_new_image` (refactor repair to use them; behavior unchanged); implement:

```python
def fill_missing_images() -> int:
    """Phase A des Slate-Modus (spec 2026-07-16): Status=Approved ohne Bild
    -> Bild generieren. Bild ist der teuerste Schritt und laeuft deshalb
    erst NACH der Text-Freigabe."""
    from tools.notion_db import get_approved_missing_image, set_post_status
    done = 0
    for row in get_approved_missing_image():
        page_id = row["page_id"]
        try:
            sections = extract_body_sections(page_id)
            prompt = sections.get("image_prompt", "").strip()
            if not prompt:
                print(f"  Kein Image-Prompt im Body ({page_id}) - Skip.", file=sys.stderr)
                continue
            archetype = _page_archetype(page_id)
            strip = archetype not in _NO_STRIP_ARCHETYPES
            image_url = generate_image(prompt, aspect_ratio=ASPECT_RATIO,
                                       strip_marks=strip)
            _apply_new_image(page_id, sections, image_url)
            done += 1
        except Exception as e:
            print(f"  Bild fuer {page_id} fehlgeschlagen: {e}", file=sys.stderr)
            try:
                set_post_status(page_id, "Image Failed")
            except Exception as e2:
                print(f"  Status-Setzen fehlgeschlagen: {e2}", file=sys.stderr)
    return done
```

And in `run_slate.py` (import `fill_missing_images` from tools.image_repair at module top):

```python
def phase_images(cfg) -> None:
    print("\nPhase A: Bilder fuer freigegebene Texte ...")
    try:
        n = fill_missing_images()
        print(f"  {n} Bild(er) generiert.")
    except Exception as e:
        print(f"  FEHLER - Phase A: {e}", file=sys.stderr)
```

- [ ] **Step 4: Run** — `python -m pytest tests/test_fill_missing_images.py tests/test_slate_phases.py -v` -> PASS

- [ ] **Step 5: Commit**

```bash
git add tools/image_repair.py run_slate.py tests/test_fill_missing_images.py tests/test_slate_phases.py
git commit -m "feat(slate): phase A images after text approval (reuses repair path)"
```

---

### Task 10: Dispatch in run_research.py + slate-day gating

**Files:**
- Modify: `run_research.py` (main), `run_slate.py` (run_slate_mode)
- Test: `tests/test_slate_phases.py` (extend), `tests/test_run_research_schedule.py` (regression only, no edits expected)

**Interfaces:**
- Produces: `run_slate.run_slate_mode(cfg, now=None) -> None`:

```python
def run_slate_mode(cfg, now=None) -> None:
    now = now or datetime.now(timezone.utc)
    print(f"=== Slate-Modus (Client: {cfg.NAME}) — {now.strftime('%Y-%m-%d %H:%M UTC')} ===")
    phase_images(cfg)
    phase_drafts(cfg)
    if now.weekday() in tuple(cfg.SLATE.get("days", (0, 3))):
        phase_slate(cfg, now)
    else:
        print(f"\nKein Slate-Tag (weekday {now.weekday()}).")
```

- In `run_research.py` `main(now=None)`, FIRST lines of the function body:

```python
    # Slate-Modus (spec 2026-07-16): lisocon faehrt die 3-Phasen-Pipeline,
    # der Winner-Flow inkl. Wochen-Jobs bleibt Jolly-only.
    if _cfg.FEATURES.get("slate_mode"):
        from run_slate import run_slate_mode
        run_slate_mode(_cfg, now=now or datetime.now(timezone.utc))
        return
```

- [ ] **Step 1: Write failing tests (append to tests/test_slate_phases.py)**

```python
def test_run_slate_mode_weekday_gating():
    thu = datetime(2026, 7, 23, 7, 0, tzinfo=timezone.utc)   # Donnerstag
    tue = datetime(2026, 7, 21, 7, 0, tzinfo=timezone.utc)   # Dienstag
    with patch.object(run_slate, "phase_images") as pi, \
         patch.object(run_slate, "phase_drafts") as pd, \
         patch.object(run_slate, "phase_slate") as ps:
        run_slate.run_slate_mode(CFG, now=thu)
        run_slate.run_slate_mode(CFG, now=tue)
    assert pi.call_count == 2 and pd.call_count == 2
    ps.assert_called_once()          # nur Donnerstag
    assert ps.call_args.args[1] == thu


def test_run_research_dispatches_to_slate_mode(monkeypatch):
    import run_research
    monkeypatch.setattr(run_research._cfg, "FEATURES",
                        {**run_research._cfg.FEATURES, "slate_mode": True},
                        raising=False)
    called = {}
    import run_slate as rs
    monkeypatch.setattr(rs, "run_slate_mode",
                        lambda cfg, now=None: called.setdefault("yes", True))
    run_research.main(now=datetime(2026, 7, 21, 7, 0, tzinfo=timezone.utc))
    assert called.get("yes") is True
```

- [ ] **Step 2: Run, verify failure**
- [ ] **Step 3: Implement (code in Interfaces above)**
- [ ] **Step 4: Run FULL suite** — `python -m pytest tests/ -q` -> all PASS (schedule pins for jolly weekly jobs must stay green)
- [ ] **Step 5: Commit**

```bash
git add run_research.py run_slate.py tests/test_slate_phases.py
git commit -m "feat(slate): dispatch slate mode from run_research, weekday gating"
```

---

### Task 11: Notion DB setup script (properties + statuses + view hint)

**Files:**
- Create: `scripts/setup_slate_notion_props.py`

**Interfaces:**
- Produces: idempotent script that PATCHes the lisocon Notion DB: adds properties `Score` (number), `VoC-Treffer` (rich_text), `Themen-Winkel` (rich_text), `Matrix-Prio` (checkbox); appends Status select options `Themenvorschlag`, `Topic Approved` (GET schema first, append missing options WITH existing options untouched — Notion select PATCH replaces the option list, so send existing + new). Prints what it changed. Reads `NOTION_TOKEN_LISOCON`/`NOTION_DB_ID` from env like tools/notion_db.py does.

- [ ] **Step 1: Write the script**

```python
"""Einmaliges Setup der Slate-Properties in der lisocon Notion-DB
(spec 2026-07-16). Idempotent: vorhandene Properties/Optionen bleiben.
Run: CLIENT=lisocon python scripts/setup_slate_notion_props.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools.notion_db import NOTION_API, NOTION_DB_ID, _headers, _notion_request

NEW_PROPS = {
    "Score": {"number": {}},
    "VoC-Treffer": {"rich_text": {}},
    "Themen-Winkel": {"rich_text": {}},
    "Matrix-Prio": {"checkbox": {}},
}
NEW_STATUS_OPTIONS = ["Themenvorschlag", "Topic Approved"]


def main():
    resp = _notion_request("GET", f"{NOTION_API}/databases/{NOTION_DB_ID}",
                           headers=_headers())
    resp.raise_for_status()
    schema = resp.json()["properties"]

    patch_props = {}
    for name, definition in NEW_PROPS.items():
        if name not in schema:
            patch_props[name] = definition
            print(f"+ Property {name}")

    status_options = schema["Status"]["select"]["options"]
    existing_names = {o["name"] for o in status_options}
    added = [n for n in NEW_STATUS_OPTIONS if n not in existing_names]
    if added:
        # Notion ersetzt die Options-Liste beim PATCH: bestehende Optionen
        # (inkl. IDs/Farben) MUESSEN mitgesendet werden.
        patch_props["Status"] = {"select": {"options": status_options + [
            {"name": n} for n in added]}}
        for n in added:
            print(f"+ Status-Option {n}")

    if not patch_props:
        print("Nichts zu tun - Schema aktuell.")
        return
    resp = _notion_request("PATCH", f"{NOTION_API}/databases/{NOTION_DB_ID}",
                           headers=_headers(), json={"properties": patch_props})
    resp.raise_for_status()
    print("Schema aktualisiert.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it against the live DB**

Run: `CLIENT=lisocon python scripts/setup_slate_notion_props.py`
Expected: lines `+ Property Score` ... `+ Status-Option Topic Approved`, then `Schema aktualisiert.` Second run prints `Nichts zu tun`.

- [ ] **Step 3: Verify** — fetch the DB schema (Notion API or MCP) and confirm the 4 properties + 2 status options exist.

- [ ] **Step 4: Commit**

```bash
git add scripts/setup_slate_notion_props.py
git commit -m "feat(slate): notion schema setup script (props + status options)"
```

---

### Task 12: Push, Make publish filters, Notion view

No repo code. Steps:

- [ ] **Step 1: Push all commits** — `git push origin master` (lisocon deploy-inert: PAUSED=1; jolly service is cron-gated).
- [ ] **Step 2: Make scenario 9506674 "Lisocon: Content Engine Publish (Reinhard)"**: add filter condition `Image` property non-empty to the existing Status=Approved AND Poster=Reinhard filter (blueprint edit via Make MCP; verify with a GET of the blueprint afterwards; do NOT touch the "LinkedIn Post URL" dedup key mapping).
- [ ] **Step 3: Make scenario 9517006 (Jae)**: same filter addition.
- [ ] **Step 4: Notion view "Themen-Slate"**: filtered Status=Themenvorschlag, grouped by Poster, visible props: Themen-Winkel, Poster, Matrix-Job, Matrix-Stage, VoC-Treffer, Score, Matrix-Prio, LinkedIn Post URL (via Notion MCP `notion-create-view` or manually).
- [ ] **Step 5: Verify Make scenarios still valid** (`isActive`, `isinvalid=false`).

---

### Task 13: Acceptance — one manual slate run (SPEND GATE)

- [ ] **Step 1: Confirm spend with Richard** if not already granted in-session (~1 scrape + 1 pool scoring + 0 images, < 2 USD).
- [ ] **Step 2: Run locally on a simulated slate day**

```bash
CLIENT=lisocon python -c "
from datetime import datetime, timezone
import run_research
run_research.main(now=datetime.now(timezone.utc))
"
```

If today is not Mon/Thu, call `run_slate.run_slate_mode(cfg, now=<next Monday 07:00 UTC>)` instead — the guard keys on the passed `now`.

- [ ] **Step 3: Verify in Notion**: 10 Themenvorschlag rows, 5/5 split (or fill-marked), Score/VoC/Winkel/Matrix filled, titles carry no influencer names.
- [ ] **Step 4: Verify in Supabase**: `topic_candidates` rows state=slated for the 10, state=pool for the rest, `engine_meta` has today's `last_slate_at_lisocon`.
- [ ] **Step 5: Re-run the same command** — expect "Slate heute schon gebaut - Skip." (idempotency proof).
- [ ] **Step 6: Pick one candidate to Topic Approved (with Richard/test), re-run** — expect draft written, Status=Ready to Review, Image empty. Then flip to Approved, re-run — expect image generated (SPEND: 1 image), Status stays Approved with Image filled, Make would publish next slot.

---

### Task 14: Rollout (PROD GATE — explicit Richard go)

- [ ] **Step 1: Cron via GraphQL** — `serviceInstanceUpdate` for service `fd065ab8-de7b-4510-a2ab-e95bd9b17cc0` (project `94180f27-d5fe-4ed2-84b6-4c82f6197415`, env `e0cca203-6ab7-40a2-a1ec-d7f02610f5fc`): `cronSchedule: "0 7 * * 1-5"`.
- [ ] **Step 2: Delete PAUSED var** (variableDelete mutation), verify via variables query.
- [ ] **Step 3: Verify** `nextCronRunAt` is the next weekday 07:00 UTC.
- [ ] **Step 4: Fix stale comment** in `clients/lisocon/config.py` ("4 Winner/Woche ... 0 7 * * 2-5" block above SCRAPE) to describe the slate model; commit+push.
- [ ] **Step 5: Brief Jae** — short German how-to (Richard sends): Mo+Do neue Themenvorschläge in der View "Themen-Slate"; 2 pro Poster auf "Topic Approved" flippen; Drafts erscheinen am nächsten Werktag als "Ready to Review"; Text-Freigabe = "Approved"; Bild kommt danach automatisch; "Posted" nie von Hand setzen.
- [ ] **Step 6: Memory update** — update `reference_lisocon_content_engine_notion_db.md` + write new memory for the slate model.
