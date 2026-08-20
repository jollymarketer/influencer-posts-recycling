"""Topic-Ideas Notion DB layer: write blog-topic candidates, read recent titles
for week-over-week dedup. Uses the classic Notion databases API (2022-06-28),
consistent with tools/notion_db.py.
"""
import os

import requests
from dotenv import load_dotenv

from clients import load_client
from tools.notion_db import _utf16_truncate
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
    """Mandanten-Default schlaegt die Env-Variable. Bewusst umgekehrt zu
    tools/notion_db.py: TOPIC_IDEAS_DB_ID ist EINE globale Variable und stand
    bis 19.08.2026 auf Jollys Blog Pipeline. Bei Env-Vorrang haette ein
    lokaler Lauf mit CLIENT=swot seine Themen dort hineingeschrieben, dasselbe
    Muster wie die Apify-Cross-Billing-Luecke. Nicht auf Env-Vorrang
    zurueckdrehen."""
    cfg = load_client()
    if hasattr(cfg, "TOPIC_IDEAS_DB_ID_DEFAULT"):
        # Gesetzt heisst gesetzt, auch wenn der Wert None ist. Ein Mandant ohne
        # eigene Themen-DB (lisocon) muss abbrechen und darf NICHT auf die
        # globale Env-Variable durchfallen.
        db = cfg.TOPIC_IDEAS_DB_ID_DEFAULT or ""
    else:
        db = os.getenv("TOPIC_IDEAS_DB_ID", "")
    if not db:
        raise RuntimeError(
            f"Keine Topic-Ideas-DB fuer CLIENT={getattr(cfg, 'NAME', '?')}. "
            "TOPIC_IDEAS_DB_ID_DEFAULT in der Client-Config setzen."
        )
    return db


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_token()}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }


def _rt(text: str) -> dict:
    return {"rich_text": [{"text": {"content": _utf16_truncate(text or "", 1990)}}]}


def write_candidates(candidates: list[ThemeCandidate], achse: str | None = None) -> int:
    """Create one Notion page per candidate. Returns count written.

    achse setzt die Select-Spalte "Achse" (SWOT, seit 20.08.2026). Wird je Achse
    getrennt geclustert, kennt der Aufrufer die Herkunft; ohne den Wert kaeme
    die Zeile ohne Achse an und der Monatsplan koennte sie nicht mischen.
    """
    if not candidates:
        return 0
    written = 0
    for c in candidates:
        # Page title = human-readable article title (was the internal snake_case
        # theme_label) so the Notion pick-view is legible; theme_label is the
        # fallback only when a candidate has no suggested title.
        display_title = c.suggested_title_de or c.suggested_title_en or c.theme_label
        props = {
            "Title": {"title": [{"text": {"content": _utf16_truncate(display_title, 1990)}}]},
            "Suggested Title EN": _rt(c.suggested_title_en),
            "Suggested Title DE": _rt(c.suggested_title_de),
            "Keyword EN": _rt(c.keyword_en),
            "Keyword DE": _rt(c.keyword_de),
            "Cluster Size": {"number": c.support_count},
            "Source Influencers": _rt(", ".join(c.sample_influencers)),
            "Supporting Posts": _rt("\n".join(c.supporting_post_urls)),
            # Verbatim source sentence backing any title number (Gate A provenance).
            "Evidence Quote": _rt(c.evidence_quote),
            "Status": {"select": {"name": "Hub needed"}},
            "Type": {"select": {"name": "Spoke"}},
            "Language DE": {"checkbox": True},
            "Language EN": {"checkbox": True},
            "Deep Research": {"checkbox": True},
        }
        if achse:
            props["Achse"] = {"select": {"name": achse}}
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
