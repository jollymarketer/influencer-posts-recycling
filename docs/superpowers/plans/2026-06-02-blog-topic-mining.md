# Blog-Topic-Mining Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist all scraped influencer posts to Supabase and mine weekly blog-topic candidates from them into a Topic-Ideas Notion DB, reusing the existing daily scrape at zero extra Apify cost.

**Architecture:** Two additions to the Influencer Posts Recycling repo. (A) A daily persistence hook upserts every scraped post (winners + losers) into Supabase schema `blog_content_mining`. (B) On Fridays the daily entrypoint runs a single-pass Claude clustering job that reads the last 7 days from Supabase, scores themes, and writes the top candidates (score >= 70, Top-5) to a decoupled Topic-Ideas Notion DB for manual review.

**Tech Stack:** Python 3.11, `requests` (Supabase PostgREST + Notion REST), `anthropic` (Claude Sonnet `claude-sonnet-4-6`), pytest + `unittest.mock`.

**Locked defaults:** Clustering model = `claude-sonnet-4-6`. Recent-title dedup = case-insensitive normalized substring match. Filter = `blog_score >= 70`, Top-5.

Spec: `docs/superpowers/specs/2026-06-02-blog-topic-mining-design.md`

---

## File Structure

| File | Responsibility | New/Modify |
|------|----------------|------------|
| `tools/supabase_db.py` | PostgREST wrapper for `blog_content_mining` schema: upsert/read posts | Create |
| `tools/topic_clusterer.py` | Build prompt, call Claude once, parse + filter theme candidates | Create |
| `tools/topic_ideas_db.py` | Read recent idea titles + write candidates to Topic-Ideas Notion DB | Create |
| `run_topic_mining.py` | Weekly entrypoint: load 7d posts -> cluster -> filter -> write | Create |
| `scripts/create_topic_ideas_db.py` | One-time: create the Topic-Ideas Notion DB under a parent page | Create |
| `scripts/blog_content_mining_schema.sql` | DDL for schema + table (applied manually) | Create |
| `run_research.py` | Add persistence hook + extract `run_daily()` + Friday trigger | Modify |
| `tests/test_supabase_db.py` | Tests for supabase_db | Create |
| `tests/test_topic_clusterer.py` | Tests for clustering parse/filter/dedup | Create |
| `tests/test_topic_ideas_db.py` | Tests for Notion property mapping | Create |
| `tests/test_topic_mining_flow.py` | Tests for entrypoint orchestration + Friday gate | Create |
| `.env.example` | Add SUPABASE_* + TOPIC_IDEAS_DB_ID | Modify |

Shared data type `ThemeCandidate` is defined once in `tools/topic_clusterer.py` and imported by `topic_ideas_db.py` and `run_topic_mining.py`.

---

## Task 1: Supabase PostgREST wrapper

**Files:**
- Create: `tools/supabase_db.py`
- Test: `tests/test_supabase_db.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_supabase_db.py
"""Tests for the Supabase PostgREST wrapper. Pure, requests mocked."""
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import supabase_db


def _post(url="https://x.com/p/1", influencer="Alice", text="body"):
    return {
        "post_url": url,
        "influencer": influencer,
        "post_text": text,
        "date": "2026-06-01T10:00:00+00:00",
        "engagement": {"likes": 5, "comments": 2, "shares": 1},
    }


def test_upsert_posts_maps_rows_and_source(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://db.example.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "key")
    resp = MagicMock(status_code=201)
    with patch("tools.supabase_db.requests.post", return_value=resp) as mock_post:
        count = supabase_db.upsert_posts([_post()], source="linkedin")
    assert count == 1
    body = mock_post.call_args.kwargs["json"]
    assert body[0]["post_url"] == "https://x.com/p/1"
    assert body[0]["source"] == "linkedin"
    assert body[0]["likes"] == 5
    assert body[0]["comments"] == 2
    assert body[0]["shares"] == 1
    assert body[0]["post_date"] == "2026-06-01"
    assert "on_conflict=post_url" in mock_post.call_args.args[0]
    assert mock_post.call_args.kwargs["headers"]["Content-Profile"] == "blog_content_mining"


def test_upsert_posts_skips_rows_without_url(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://db.example.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "key")
    resp = MagicMock(status_code=201)
    with patch("tools.supabase_db.requests.post", return_value=resp) as mock_post:
        count = supabase_db.upsert_posts([_post(), {"influencer": "NoUrl"}], source="linkedin")
    assert count == 1
    assert len(mock_post.call_args.kwargs["json"]) == 1


def test_upsert_posts_empty_is_noop(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://db.example.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "key")
    with patch("tools.supabase_db.requests.post") as mock_post:
        count = supabase_db.upsert_posts([], source="linkedin")
    assert count == 0
    mock_post.assert_not_called()


def test_get_posts_since_builds_gte_filter(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://db.example.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "key")
    rows = [{"post_url": "u", "post_text": "t"}]
    resp = MagicMock(status_code=200)
    resp.json.return_value = rows
    with patch("tools.supabase_db.requests.get", return_value=resp) as mock_get:
        out = supabase_db.get_posts_since(7)
    assert out == rows
    params = mock_get.call_args.kwargs["params"]
    assert params["select"] == "*"
    assert params["post_date"].startswith("gte.")
    assert mock_get.call_args.kwargs["headers"]["Accept-Profile"] == "blog_content_mining"


def test_missing_key_raises(monkeypatch):
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    monkeypatch.setenv("SUPABASE_URL", "https://db.example.co")
    import pytest
    with pytest.raises(RuntimeError):
        supabase_db.upsert_posts([_post()], source="linkedin")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_supabase_db.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.supabase_db'`

- [ ] **Step 3: Write the implementation**

```python
# tools/supabase_db.py
"""Supabase PostgREST wrapper for the blog_content_mining schema.

Mirrors the raw-requests style of tools/notion_db.py. Reads SUPABASE_URL and
SUPABASE_SERVICE_KEY from .env. The service-role key bypasses RLS; this is
internal tooling only.
"""
import os
from datetime import datetime, timedelta, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

SCHEMA = "blog_content_mining"
TABLE = "influencer_posts"
TIMEOUT = 30


def _base_url() -> str:
    return os.environ.get("SUPABASE_URL", "").rstrip("/")


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


def _to_row(post: dict, source: str) -> dict | None:
    url = post.get("post_url")
    if not url:
        return None
    eng = post.get("engagement", {}) or {}
    date_raw = post.get("date", "")
    post_date = date_raw[:10] if date_raw else None  # ISO -> YYYY-MM-DD
    return {
        "post_url": url,
        "source": source,
        "influencer": post.get("influencer", ""),
        "post_text": post.get("post_text", ""),
        "post_date": post_date,
        "likes": int(eng.get("likes", 0) or 0),
        "comments": int(eng.get("comments", 0) or 0),
        "shares": int(eng.get("shares", 0) or 0),
    }


def upsert_posts(posts: list[dict], source: str) -> int:
    """Upsert posts on conflict post_url. Returns rows sent. Empty list = no-op."""
    rows = [r for r in (_to_row(p, source) for p in posts) if r is not None]
    if not rows:
        return 0
    url = f"{_base_url()}/rest/v1/{TABLE}?on_conflict=post_url"
    resp = requests.post(url, headers=_headers_write(), json=rows, timeout=TIMEOUT)
    if not (200 <= resp.status_code < 300):
        raise RuntimeError(f"Supabase upsert {resp.status_code}: {resp.text[:300]}")
    return len(rows)


def get_posts_since(days: int) -> list[dict]:
    """Return all posts with post_date >= now - days."""
    since = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
    url = f"{_base_url()}/rest/v1/{TABLE}"
    params = {"select": "*", "post_date": f"gte.{since}"}
    resp = requests.get(url, headers=_headers_read(), params=params, timeout=TIMEOUT)
    if not (200 <= resp.status_code < 300):
        raise RuntimeError(f"Supabase get {resp.status_code}: {resp.text[:300]}")
    return resp.json()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_supabase_db.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add tools/supabase_db.py tests/test_supabase_db.py
git commit -m "feat(mining): Supabase wrapper for blog_content_mining posts"
```

---

## Task 2: Supabase schema DDL (applied manually)

**Files:**
- Create: `scripts/blog_content_mining_schema.sql`

- [ ] **Step 1: Write the DDL file**

```sql
-- scripts/blog_content_mining_schema.sql
-- Apply via Supabase SQL editor or `supabase db execute`. One-time.
create schema if not exists blog_content_mining;

create table if not exists blog_content_mining.influencer_posts (
    post_url    text primary key,
    source      text not null,            -- 'linkedin' | 'substack'
    influencer  text,
    post_text   text,
    post_date   date,
    likes       integer default 0,
    comments    integer default 0,
    shares      integer default 0,
    scraped_at  timestamptz not null default now()
);

create index if not exists influencer_posts_post_date_idx
    on blog_content_mining.influencer_posts (post_date);

-- PostgREST exposes non-public schemas only if listed. Add the schema:
--   Dashboard -> Settings -> API -> Exposed schemas -> add "blog_content_mining"
-- (or set db.schemas in config). Required for the REST wrapper to reach it.
```

- [ ] **Step 2: Commit (no test — manual DDL)**

```bash
git add scripts/blog_content_mining_schema.sql
git commit -m "chore(mining): blog_content_mining schema DDL"
```

> MANUAL SETUP (do not skip before first real run): apply this DDL in Supabase
> and add `blog_content_mining` to the exposed schemas. Without the exposed-schema
> step PostgREST returns 404 / "schema must be one of the following".

---

## Task 3: Daily persistence hook in run_research.py

**Files:**
- Modify: `run_research.py` (after Schritt 2 scrape block, around line 75)
- Test: `tests/test_topic_mining_flow.py` (persistence portion)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_topic_mining_flow.py
"""Tests for persistence hook + Friday trigger + mining orchestration."""
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import run_research


def test_persist_scraped_posts_tags_source_and_is_nonfatal():
    li = [{"post_url": "a", "influencer": "A"}]
    ss = [{"post_url": "b", "influencer": "B"}]
    with patch("run_research.upsert_posts") as mock_up:
        run_research.persist_scraped_posts(li, ss)
    # called once per source
    sources = {c.kwargs.get("source") or c.args[1] for c in mock_up.call_args_list}
    assert sources == {"linkedin", "substack"}


def test_persist_scraped_posts_swallows_errors():
    with patch("run_research.upsert_posts", side_effect=RuntimeError("db down")):
        # must not raise
        run_research.persist_scraped_posts([{"post_url": "a"}], [])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_topic_mining_flow.py::test_persist_scraped_posts_tags_source_and_is_nonfatal -v`
Expected: FAIL with `AttributeError: module 'run_research' has no attribute 'persist_scraped_posts'`

- [ ] **Step 3: Add the import and function to run_research.py**

Add to the imports block (after the `from tools.kieai_image import generate_image` line):

```python
from tools.supabase_db import upsert_posts
```

Add this function above `def main():`:

```python
def persist_scraped_posts(linkedin_posts: list, substack_posts: list) -> None:
    """Upsert ALL scraped posts (winners + losers) to Supabase. Non-fatal:
    a failure here must never block the daily winner/draft flow."""
    for posts, source in ((linkedin_posts, "linkedin"), (substack_posts, "substack")):
        if not posts:
            continue
        try:
            n = upsert_posts(posts, source=source)
            print(f"  Supabase: {n} {source}-Posts persistiert.")
        except Exception as e:
            print(f"  Supabase-Persist {source} fehlgeschlagen (nicht kritisch): {e}", file=sys.stderr)
```

- [ ] **Step 4: Wire the hook into the scrape flow**

In `main()` (later renamed `run_daily()` in Task 8), the scrape block builds
`linkedin_posts` and `substack_posts` then merges into `new_posts`. Immediately
after both scrapes complete and before `if not new_posts:` (currently line ~75),
add:

```python
    # Persist ALL scraped posts (winners + losers) for weekly blog-topic mining.
    persist_scraped_posts(linkedin_posts if "linkedin_posts" in dir() else [],
                          substack_posts if "substack_posts" in dir() else [])
```

NOTE: `linkedin_posts` / `substack_posts` are assigned inside their try blocks.
To make them always defined, initialize them at the top of the scrape section:
change the scrape block to start with `linkedin_posts = []` and
`substack_posts = []` before the try/except blocks, then the hook simplifies to:

```python
    persist_scraped_posts(linkedin_posts, substack_posts)
```

Apply the simpler form: add `linkedin_posts = []` and `substack_posts = []`
initializers at the start of Schritt 2, and call `persist_scraped_posts(linkedin_posts, substack_posts)` after the scrape try/except blocks, before the `if not new_posts:` guard.

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_topic_mining_flow.py -k persist -v`
Expected: PASS (2 passed)

- [ ] **Step 6: Run full suite to confirm no regression**

Run: `python -m pytest -v`
Expected: PASS (existing parse tests + new tests)

- [ ] **Step 7: Commit**

```bash
git add run_research.py tests/test_topic_mining_flow.py
git commit -m "feat(mining): persist all scraped posts to Supabase (non-fatal hook)"
```

---

## Task 4: Topic clusterer (single-pass Claude)

**Files:**
- Create: `tools/topic_clusterer.py`
- Test: `tests/test_topic_clusterer.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_topic_clusterer.py
"""Tests for topic clustering. Claude client mocked — no API calls."""
import json
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import topic_clusterer
from tools.topic_clusterer import ThemeCandidate, _parse_clusters, filter_candidates


def _raw(themes):
    return json.dumps(themes)


SAMPLE = [
    {
        "theme_label": "AI SDR adoption",
        "support_count": 4,
        "sample_influencers": ["Alice", "Bob"],
        "blog_score": 82,
        "suggested_title_en": "Why AI SDRs Fail Without RevOps",
        "suggested_title_de": "Warum AI-SDRs ohne RevOps scheitern",
        "keyword_en": "ai sdr",
        "keyword_de": "ai sdr",
        "supporting_post_urls": ["https://x/1", "https://x/2"],
    },
    {
        "theme_label": "Cold email deliverability",
        "support_count": 2,
        "sample_influencers": ["Cara"],
        "blog_score": 55,
        "suggested_title_en": "Deliverability in 2026",
        "suggested_title_de": "Zustellbarkeit 2026",
        "keyword_en": "email deliverability",
        "keyword_de": "zustellbarkeit",
        "supporting_post_urls": ["https://x/3"],
    },
]


def test_parse_clusters_plain_json():
    out = _parse_clusters(_raw(SAMPLE))
    assert len(out) == 2
    assert isinstance(out[0], ThemeCandidate)
    assert out[0].theme_label == "AI SDR adoption"
    assert out[0].blog_score == 82


def test_parse_clusters_strips_code_fence():
    fenced = "```json\n" + _raw(SAMPLE) + "\n```"
    out = _parse_clusters(fenced)
    assert len(out) == 2


def test_parse_clusters_bad_json_returns_empty():
    assert _parse_clusters("not json at all") == []


def test_filter_candidates_threshold_and_topn():
    cands = _parse_clusters(_raw(SAMPLE))
    out = filter_candidates(cands, threshold=70, top_n=5, recent_titles=[])
    assert len(out) == 1  # only score 82 passes >= 70
    assert out[0].theme_label == "AI SDR adoption"


def test_filter_candidates_dedup_case_insensitive_substring():
    cands = _parse_clusters(_raw(SAMPLE))
    out = filter_candidates(
        cands, threshold=50, top_n=5,
        recent_titles=["why ai sdrs fail without revops"],
    )
    labels = [c.theme_label for c in out]
    assert "AI SDR adoption" not in labels  # deduped by recent title match
    assert "Cold email deliverability" in labels


def test_filter_candidates_topn_caps_after_sort():
    many = []
    for i in range(10):
        t = dict(SAMPLE[0])
        t["blog_score"] = 70 + i
        t["theme_label"] = f"Theme {i}"
        t["suggested_title_en"] = f"Title {i}"
        many.append(t)
    cands = _parse_clusters(_raw(many))
    out = filter_candidates(cands, threshold=70, top_n=5, recent_titles=[])
    assert len(out) == 5
    assert out[0].blog_score == 79  # highest first


def test_cluster_topics_returns_empty_for_too_few_posts():
    out = topic_clusterer.cluster_topics([{"post_text": "x"}], recent_titles=[])
    assert out == []


def test_cluster_topics_calls_claude_and_parses():
    posts = [{"influencer": "A", "post_text": "p", "engagement": {"likes": 1, "comments": 0, "shares": 0}}] * 3
    fake = MagicMock()
    fake.content = [MagicMock(text=_raw(SAMPLE))]
    with patch("tools.topic_clusterer.client") as mock_client:
        mock_client.messages.create.return_value = fake
        out = topic_clusterer.cluster_topics(posts, recent_titles=[])
    assert mock_client.messages.create.called
    assert mock_client.messages.create.call_args.kwargs["model"] == "claude-sonnet-4-6"
    assert len(out) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_topic_clusterer.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.topic_clusterer'`

- [ ] **Step 3: Write the implementation**

```python
# tools/topic_clusterer.py
"""Single-pass Claude clustering of accumulated influencer posts into
blog-topic candidates. One API call per weekly run.
"""
import json
import os
import re
from dataclasses import dataclass, field

import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 4096
MIN_POSTS = 2
EXCERPT_LEN = 500


@dataclass
class ThemeCandidate:
    theme_label: str
    support_count: int
    sample_influencers: list[str]
    blog_score: int
    suggested_title_en: str
    suggested_title_de: str
    keyword_en: str
    keyword_de: str
    supporting_post_urls: list[str] = field(default_factory=list)


SYSTEM_PROMPT = (
    "You are a B2B content strategist for Jolly Marketer, a Berlin-based B2B "
    "RevOps/GTM agency serving the DACH market (B2B SaaS, tech services, "
    "industrial SMEs). You cluster LinkedIn/Substack posts into blog-topic "
    "themes for jollymarketer.com and score each theme's blog potential."
)


def _build_user_prompt(posts: list[dict], recent_titles: list[str]) -> str:
    lines = []
    for p in posts:
        eng = p.get("engagement") or {}
        likes = eng.get("likes", p.get("likes", 0))
        comments = eng.get("comments", p.get("comments", 0))
        text = (p.get("post_text") or "")[:EXCERPT_LEN]
        url = p.get("post_url", "")
        lines.append(
            f"- influencer={p.get('influencer','')} likes={likes} comments={comments} "
            f"url={url}\n  {text}"
        )
    posts_block = "\n".join(lines)
    avoid = "; ".join(recent_titles) if recent_titles else "(none)"
    return (
        f"Here are influencer posts from the last 7 days:\n\n{posts_block}\n\n"
        f"Group them into 3-8 blog-topic themes. AVOID themes that duplicate any "
        f"of these recently-suggested titles: {avoid}.\n\n"
        "For each theme return an object with EXACTLY these keys:\n"
        "  theme_label (string), support_count (int = how many posts back it), "
        "sample_influencers (array of strings), blog_score (int 0-100 weighing "
        "SEO/search intent, evergreen potential, cluster support depth, and fit "
        "to Jolly B2B-DACH ICP), suggested_title_en, suggested_title_de, "
        "keyword_en, keyword_de, supporting_post_urls (array of the source URLs).\n\n"
        "Return ONLY a JSON array of these objects. No prose, no code fence."
    )


def _parse_clusters(raw: str) -> list[ThemeCandidate]:
    text = raw.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return []
    if not isinstance(data, list):
        return []
    out = []
    for d in data:
        if not isinstance(d, dict):
            continue
        try:
            out.append(ThemeCandidate(
                theme_label=str(d.get("theme_label", "")).strip(),
                support_count=int(d.get("support_count", 0) or 0),
                sample_influencers=list(d.get("sample_influencers", []) or []),
                blog_score=int(d.get("blog_score", 0) or 0),
                suggested_title_en=str(d.get("suggested_title_en", "")).strip(),
                suggested_title_de=str(d.get("suggested_title_de", "")).strip(),
                keyword_en=str(d.get("keyword_en", "")).strip(),
                keyword_de=str(d.get("keyword_de", "")).strip(),
                supporting_post_urls=list(d.get("supporting_post_urls", []) or []),
            ))
        except (ValueError, TypeError):
            continue
    return out


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower()).strip()


def filter_candidates(
    candidates: list[ThemeCandidate],
    *,
    threshold: int,
    top_n: int,
    recent_titles: list[str],
) -> list[ThemeCandidate]:
    """Drop below-threshold themes, dedup against recent titles (case-insensitive
    normalized substring either direction), sort by score desc, cap at top_n."""
    recent_norm = [_norm(t) for t in recent_titles if t]

    def is_dupe(c: ThemeCandidate) -> bool:
        for cand_text in (_norm(c.theme_label), _norm(c.suggested_title_en), _norm(c.suggested_title_de)):
            if not cand_text:
                continue
            for r in recent_norm:
                if cand_text in r or r in cand_text:
                    return True
        return False

    kept = [c for c in candidates if c.blog_score >= threshold and not is_dupe(c)]
    kept.sort(key=lambda c: c.blog_score, reverse=True)
    return kept[:top_n]


def cluster_topics(posts: list[dict], recent_titles: list[str]) -> list[ThemeCandidate]:
    """One Claude call clustering posts into theme candidates. Returns [] if too
    few posts or on unparseable output. Caller applies filter_candidates()."""
    if len(posts) < MIN_POSTS:
        return []
    resp = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _build_user_prompt(posts, recent_titles)}],
    )
    raw = resp.content[0].text if resp.content else ""
    return _parse_clusters(raw)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_topic_clusterer.py -v`
Expected: PASS (8 passed)

- [ ] **Step 5: Commit**

```bash
git add tools/topic_clusterer.py tests/test_topic_clusterer.py
git commit -m "feat(mining): single-pass Claude topic clusterer + score/dedup filter"
```

---

## Task 5: Topic-Ideas Notion DB layer

**Files:**
- Create: `tools/topic_ideas_db.py`
- Test: `tests/test_topic_ideas_db.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_topic_ideas_db.py
"""Tests for the Topic-Ideas Notion DB layer. requests mocked."""
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import topic_ideas_db
from tools.topic_clusterer import ThemeCandidate


def _cand():
    return ThemeCandidate(
        theme_label="AI SDR adoption",
        support_count=4,
        sample_influencers=["Alice", "Bob"],
        blog_score=82,
        suggested_title_en="Why AI SDRs Fail Without RevOps",
        suggested_title_de="Warum AI-SDRs ohne RevOps scheitern",
        keyword_en="ai sdr",
        keyword_de="ai sdr",
        supporting_post_urls=["https://x/1", "https://x/2"],
    )


def test_write_candidates_maps_properties(monkeypatch):
    monkeypatch.setenv("NOTION_TOKEN", "tok")
    monkeypatch.setenv("TOPIC_IDEAS_DB_ID", "db123")
    resp = MagicMock(status_code=200)
    resp.json.return_value = {"id": "page1"}
    resp.ok = True
    with patch("tools.topic_ideas_db.requests.post", return_value=resp) as mock_post:
        n = topic_ideas_db.write_candidates([_cand()])
    assert n == 1
    payload = mock_post.call_args.kwargs["json"]
    props = payload["properties"]
    assert props["Title"]["title"][0]["text"]["content"] == "AI SDR adoption"
    assert props["Suggested Title EN"]["rich_text"][0]["text"]["content"] == "Why AI SDRs Fail Without RevOps"
    assert props["Blog Score"]["number"] == 82
    assert props["Cluster Size"]["number"] == 4
    assert props["Status"]["select"]["name"] == "New"
    assert "https://x/1" in props["Supporting Posts"]["rich_text"][0]["text"]["content"]


def test_write_candidates_empty_is_noop(monkeypatch):
    monkeypatch.setenv("NOTION_TOKEN", "tok")
    monkeypatch.setenv("TOPIC_IDEAS_DB_ID", "db123")
    with patch("tools.topic_ideas_db.requests.post") as mock_post:
        n = topic_ideas_db.write_candidates([])
    assert n == 0
    mock_post.assert_not_called()


def test_get_recent_idea_titles_extracts_titles(monkeypatch):
    monkeypatch.setenv("NOTION_TOKEN", "tok")
    monkeypatch.setenv("TOPIC_IDEAS_DB_ID", "db123")
    resp = MagicMock(status_code=200)
    resp.json.return_value = {
        "results": [
            {"properties": {"Title": {"title": [{"plain_text": "Theme A"}]},
                            "Suggested Title EN": {"rich_text": [{"plain_text": "Title A"}]}}},
        ],
        "has_more": False,
    }
    resp.raise_for_status = MagicMock()
    with patch("tools.topic_ideas_db.requests.post", return_value=resp):
        titles = topic_ideas_db.get_recent_idea_titles(limit=20)
    assert "Theme A" in titles
    assert "Title A" in titles
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_topic_ideas_db.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.topic_ideas_db'`

- [ ] **Step 3: Write the implementation**

```python
# tools/topic_ideas_db.py
"""Topic-Ideas Notion DB layer: write blog-topic candidates, read recent titles
for week-over-week dedup. Uses the classic Notion databases API (2022-06-28),
consistent with tools/notion_db.py.
"""
import os

import requests
from dotenv import load_dotenv

from tools.topic_clusterer import ThemeCandidate

load_dotenv()

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
TIMEOUT = 30


def _token() -> str:
    tok = os.getenv("NOTION_TOKEN", "")
    if not tok:
        raise RuntimeError("NOTION_TOKEN is not set.")
    return tok


def _db_id() -> str:
    db = os.getenv("TOPIC_IDEAS_DB_ID", "")
    if not db:
        raise RuntimeError("TOPIC_IDEAS_DB_ID is not set.")
    return db


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_token()}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }


def _rt(text: str) -> dict:
    return {"rich_text": [{"text": {"content": (text or "")[:1990]}}]}


def write_candidates(candidates: list[ThemeCandidate]) -> int:
    """Create one Notion page per candidate. Returns count written."""
    if not candidates:
        return 0
    written = 0
    for c in candidates:
        props = {
            "Title": {"title": [{"text": {"content": c.theme_label[:1990]}}]},
            "Suggested Title EN": _rt(c.suggested_title_en),
            "Suggested Title DE": _rt(c.suggested_title_de),
            "Keyword EN": _rt(c.keyword_en),
            "Keyword DE": _rt(c.keyword_de),
            "Blog Score": {"number": c.blog_score},
            "Cluster Size": {"number": c.support_count},
            "Source Influencers": _rt(", ".join(c.sample_influencers)),
            "Supporting Posts": _rt("\n".join(c.supporting_post_urls)),
            "Status": {"select": {"name": "New"}},
        }
        payload = {"parent": {"database_id": _db_id()}, "properties": props}
        resp = requests.post(f"{NOTION_API}/pages", headers=_headers(), json=payload, timeout=TIMEOUT)
        if not resp.ok:
            print(f"  Topic-Idea Notion-Fehler {resp.status_code}: {resp.text[:300]}", flush=True)
            continue
        written += 1
    return written


def get_recent_idea_titles(limit: int = 30) -> list[str]:
    """Return recent theme labels + EN titles for dedup."""
    payload = {
        "sorts": [{"timestamp": "created_time", "direction": "descending"}],
        "page_size": limit,
    }
    resp = requests.post(
        f"{NOTION_API}/databases/{_db_id()}/query",
        headers=_headers(), json=payload, timeout=TIMEOUT,
    )
    resp.raise_for_status()
    titles: list[str] = []
    for page in resp.json().get("results", []):
        props = page.get("properties", {})
        title_rt = props.get("Title", {}).get("title", [])
        t = "".join(x.get("plain_text", "") for x in title_rt).strip()
        if t:
            titles.append(t)
        en_rt = props.get("Suggested Title EN", {}).get("rich_text", [])
        en = "".join(x.get("plain_text", "") for x in en_rt).strip()
        if en:
            titles.append(en)
    return titles
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_topic_ideas_db.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add tools/topic_ideas_db.py tests/test_topic_ideas_db.py
git commit -m "feat(mining): Topic-Ideas Notion DB layer (write candidates + recent titles)"
```

---

## Task 6: Topic-Ideas Notion DB setup script (one-time, manual)

**Files:**
- Create: `scripts/create_topic_ideas_db.py`

- [ ] **Step 1: Write the script**

```python
# scripts/create_topic_ideas_db.py
"""One-time: create the Topic-Ideas Notion DB under a parent page.

Usage:
    python scripts/create_topic_ideas_db.py <parent_page_id>

Prints the new database id. Put it in .env as TOPIC_IDEAS_DB_ID and share the
parent page with the integration first.
"""
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/create_topic_ideas_db.py <parent_page_id>")
        return 1
    parent_page_id = sys.argv[1]
    headers = {
        "Authorization": f"Bearer {os.environ['NOTION_TOKEN']}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }
    payload = {
        "parent": {"type": "page_id", "page_id": parent_page_id},
        "title": [{"type": "text", "text": {"content": "Blog Topic Ideas (mined)"}}],
        "properties": {
            "Title": {"title": {}},
            "Suggested Title EN": {"rich_text": {}},
            "Suggested Title DE": {"rich_text": {}},
            "Keyword EN": {"rich_text": {}},
            "Keyword DE": {"rich_text": {}},
            "Blog Score": {"number": {}},
            "Cluster Size": {"number": {}},
            "Source Influencers": {"rich_text": {}},
            "Supporting Posts": {"rich_text": {}},
            "Status": {"select": {"options": [
                {"name": "New", "color": "blue"},
                {"name": "Promoted", "color": "green"},
                {"name": "Rejected", "color": "red"},
            ]}},
        },
    }
    resp = requests.post(f"{NOTION_API}/databases", headers=headers, json=payload, timeout=30)
    if not resp.ok:
        print(f"Notion error {resp.status_code}: {resp.text[:500]}")
        return 1
    db_id = resp.json()["id"]
    print(f"Created DB. Set in .env:\nTOPIC_IDEAS_DB_ID={db_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Commit (no automated test — one-time manual script)**

```bash
git add scripts/create_topic_ideas_db.py
git commit -m "chore(mining): one-time Topic-Ideas Notion DB creation script"
```

> MANUAL SETUP: share a Notion parent page with the integration, run this script
> with that page id, copy `TOPIC_IDEAS_DB_ID` into `.env` + Railway env.

---

## Task 7: Weekly mining entrypoint

**Files:**
- Create: `run_topic_mining.py`
- Test: `tests/test_topic_mining_flow.py` (mining orchestration portion)

- [ ] **Step 1: Add the failing tests to tests/test_topic_mining_flow.py**

```python
# append to tests/test_topic_mining_flow.py
import run_topic_mining
from tools.topic_clusterer import ThemeCandidate


def _cand(score, label="T"):
    return ThemeCandidate(
        theme_label=label, support_count=3, sample_influencers=["A"],
        blog_score=score, suggested_title_en="t", suggested_title_de="t",
        keyword_en="k", keyword_de="k", supporting_post_urls=["u"],
    )


def test_mining_skips_when_too_few_posts():
    with patch("run_topic_mining.get_posts_since", return_value=[{"post_url": "a"}]), \
         patch("run_topic_mining.cluster_topics") as mock_cluster, \
         patch("run_topic_mining.write_candidates") as mock_write:
        run_topic_mining.run_topic_mining()
    mock_cluster.assert_not_called()
    mock_write.assert_not_called()


def test_mining_filters_and_writes_top5():
    posts = [{"post_url": str(i)} for i in range(5)]
    cands = [_cand(90, "A"), _cand(50, "B"), _cand(75, "C")]
    with patch("run_topic_mining.get_posts_since", return_value=posts), \
         patch("run_topic_mining.get_recent_idea_titles", return_value=[]), \
         patch("run_topic_mining.cluster_topics", return_value=cands), \
         patch("run_topic_mining.write_candidates") as mock_write:
        run_topic_mining.run_topic_mining()
    written = mock_write.call_args.args[0]
    labels = [c.theme_label for c in written]
    assert labels == ["A", "C"]  # 90 and 75 pass >=70, sorted desc; 50 dropped
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_topic_mining_flow.py -k mining -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'run_topic_mining'`

- [ ] **Step 3: Write the entrypoint**

```python
# run_topic_mining.py
"""Weekly blog-topic mining: read last 7 days of scraped posts from Supabase,
cluster into themes via Claude, write the top candidates to the Topic-Ideas
Notion DB. Run standalone or triggered from run_research.py on Fridays.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from tools.supabase_db import get_posts_since
from tools.topic_clusterer import cluster_topics, filter_candidates
from tools.topic_ideas_db import get_recent_idea_titles, write_candidates

WINDOW_DAYS = 7
SCORE_THRESHOLD = 70
TOP_N = 5


def run_topic_mining() -> None:
    print("=== Blog Topic Mining ===")
    posts = get_posts_since(WINDOW_DAYS)
    print(f"  {len(posts)} Posts im {WINDOW_DAYS}-Tage-Fenster.")
    if len(posts) < 2:
        print("  Zu wenige Posts (<2). Skip.")
        return
    recent_titles = get_recent_idea_titles(limit=30)
    candidates = cluster_topics(posts, recent_titles=recent_titles)
    print(f"  Claude lieferte {len(candidates)} Roh-Themen.")
    top = filter_candidates(
        candidates, threshold=SCORE_THRESHOLD, top_n=TOP_N, recent_titles=recent_titles
    )
    print(f"  {len(top)} Themen nach Filter (>= {SCORE_THRESHOLD}, Top-{TOP_N}).")
    n = write_candidates(top)
    print(f"  {n} Themen-Kandidaten in Notion geschrieben.")


if __name__ == "__main__":
    run_topic_mining()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_topic_mining_flow.py -k mining -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add run_topic_mining.py tests/test_topic_mining_flow.py
git commit -m "feat(mining): weekly topic-mining entrypoint"
```

---

## Task 8: Friday trigger refactor in run_research.py

**Files:**
- Modify: `run_research.py` (rename `main` body to `run_daily`, add `main` wrapper)
- Test: `tests/test_topic_mining_flow.py` (Friday gate portion)

- [ ] **Step 1: Add the failing tests**

```python
# append to tests/test_topic_mining_flow.py
from datetime import datetime, timezone


class _FixedDate(datetime):
    _wd = 0
    @classmethod
    def now(cls, tz=None):
        # 2026-06-05 is a Friday (weekday 4); 2026-06-03 is Wednesday (2)
        base = datetime(2026, 6, 5 if cls._wd == 4 else 3, tzinfo=tz or timezone.utc)
        return base


def test_main_runs_mining_on_friday(monkeypatch):
    monkeypatch.setattr(run_research, "run_daily", MagicMock())
    monkeypatch.setattr(run_research, "run_topic_mining", MagicMock())
    _FixedDate._wd = 4
    monkeypatch.setattr(run_research, "datetime", _FixedDate)
    run_research.main()
    run_research.run_topic_mining.assert_called_once()


def test_main_skips_mining_on_non_friday(monkeypatch):
    monkeypatch.setattr(run_research, "run_daily", MagicMock())
    monkeypatch.setattr(run_research, "run_topic_mining", MagicMock())
    _FixedDate._wd = 2
    monkeypatch.setattr(run_research, "datetime", _FixedDate)
    run_research.main()
    run_research.run_topic_mining.assert_not_called()


def test_main_mining_failure_is_nonfatal(monkeypatch):
    monkeypatch.setattr(run_research, "run_daily", MagicMock())
    monkeypatch.setattr(run_research, "run_topic_mining", MagicMock(side_effect=RuntimeError("boom")))
    _FixedDate._wd = 4
    monkeypatch.setattr(run_research, "datetime", _FixedDate)
    run_research.main()  # must not raise
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_topic_mining_flow.py -k main -v`
Expected: FAIL (`run_research.run_daily` does not exist yet, or `run_topic_mining` not imported)

- [ ] **Step 3: Refactor run_research.py**

1. Add import near the other tool imports:

```python
from run_topic_mining import run_topic_mining
```

2. Rename the existing `def main():` to `def run_daily():` (keep its entire body, including its internal early `return` statements, unchanged except for the persistence hook already added in Task 3).

3. Add a new `main()` below `run_daily()`:

```python
def main():
    run_daily()
    if datetime.now(timezone.utc).weekday() == 4:  # Friday, UTC
        print("\n=== Freitag: starte Blog-Topic-Mining ===")
        try:
            run_topic_mining()
        except Exception as e:
            print(f"  Topic-Mining fehlgeschlagen (nicht kritisch): {e}", file=sys.stderr)
```

4. The `if __name__ == "__main__": main()` block stays unchanged (still calls `main`).

NOTE: `datetime` and `timezone` are already imported at the top of run_research.py (line 20). No new datetime import needed.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_topic_mining_flow.py -k main -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Run the full suite**

Run: `python -m pytest -v`
Expected: PASS (all tests across all files)

- [ ] **Step 6: Commit**

```bash
git add run_research.py tests/test_topic_mining_flow.py
git commit -m "feat(mining): Friday trigger via run_daily/main split (non-fatal)"
```

---

## Task 9: Env + docs wiring

**Files:**
- Modify: `.env.example`

- [ ] **Step 1: Add the new keys to .env.example**

Append:

```
# Supabase (blog topic mining — schema blog_content_mining)
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
# Topic-Ideas Notion DB (created via scripts/create_topic_ideas_db.py)
TOPIC_IDEAS_DB_ID=
```

- [ ] **Step 2: Commit**

```bash
git add .env.example
git commit -m "docs(mining): document Supabase + Topic-Ideas env keys"
```

---

## Final Verification (before declaring done)

- [ ] Run full suite: `python -m pytest -v` — all green.
- [ ] Confirm `requirements.txt` needs no change (uses `requests` + `anthropic` already present). If a future run shows `dotenv` missing in any new module, it is already in requirements via `python-dotenv`.
- [ ] List MANUAL setup still owed before first live run (these are spend/infra, NOT part of the coded plan):
  1. Apply `scripts/blog_content_mining_schema.sql` in Supabase + expose schema.
  2. Add `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` to local `.env` + Railway service env.
  3. Run `scripts/create_topic_ideas_db.py <parent_page_id>`, set `TOPIC_IDEAS_DB_ID` in `.env` + Railway.
  4. First real `python run_topic_mining.py` is the first Claude spend (~$0.10-0.40) — request approval, then run once manually to validate output before relying on the Friday cron.

---

## Self-Review

**Spec coverage:**
- Persist all posts to Supabase (`blog_content_mining`) → Task 1 + 3. ✓
- Supabase table DDL → Task 2. ✓
- Single-pass Claude clustering + scoring → Task 4. ✓
- Score>=70 + Top-5 filter → Task 4 (`filter_candidates`) + Task 7. ✓
- Recent-title dedup → Task 4 + Task 5 (`get_recent_idea_titles`). ✓
- Topic-Ideas Notion DB + write → Task 5 + Task 6. ✓
- Weekly entrypoint → Task 7. ✓
- Friday trigger surviving early returns → Task 8 (`run_daily`/`main` split). ✓
- Error handling non-fatal (persist + cluster) → Task 3, Task 8. ✓
- `<2` posts skip → Task 4 (`cluster_topics`) + Task 7. ✓
- Env wiring → Task 9. ✓

**Placeholder scan:** No TBD/TODO; every code step shows full code. ✓

**Type consistency:** `ThemeCandidate` defined once in `topic_clusterer.py`, imported by `topic_ideas_db.py` and `run_topic_mining.py`. `filter_candidates(threshold=, top_n=, recent_titles=)` signature consistent across Task 4/7. `upsert_posts(posts, source)` consistent Task 1/3. `cluster_topics(posts, recent_titles)` consistent Task 4/7. ✓
