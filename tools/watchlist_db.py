"""Watchlist fuer Kommentar-Entwuerfe in Supabase (blog_content_mining.
comment_watchlist, Migration db/migrations/2026-09-14_comment_watchlist.sql).

Anlass 14.09.2026: das Repo ist oeffentlich, Prospect-Listen liegen deshalb
nicht als CSV im Repo. Lesen und Schreiben ueber PostgREST mit den Headern
aus tools/topic_pool (Schema-Profile, Service-Key). Kein Modellaufruf.
"""
import requests

from tools.topic_pool import TIMEOUT, _base_url, _check, _headers_read, _headers_write

TABLE = "comment_watchlist"
COLUMNS = ("prio", "typ", "domain", "company", "persona", "first_name", "last_name",
           "title", "linkedin_url", "source", "active_at")
PAGE = 1000
CHUNK = 500


def get_watchlist(client: str) -> list[dict]:
    """Alle Zeilen eines Mandanten, Prio-sortiert. PostgREST liefert hoechstens
    1000 je Antwort, deshalb seitenweise ueber den Range-Header."""
    url = f"{_base_url()}/rest/v1/{TABLE}"
    out, start = [], 0
    while True:
        headers = {**_headers_read(), "Range-Unit": "items", "Range": f"{start}-{start + PAGE - 1}"}
        resp = requests.get(url, headers=headers, timeout=TIMEOUT,
                            params={"select": ",".join(COLUMNS), "client": f"eq.{client}",
                                    "order": "prio.asc,last_name.asc"})
        _check(resp)
        rows = resp.json()
        for r in rows:
            r["prio"] = str(r.get("prio") or "")
        out.extend(rows)
        if len(rows) < PAGE:
            return out
        start += PAGE


def upsert_watchlist(client: str, rows: list[dict]) -> int:
    """Upsert je (client, linkedin_url) in Bloecken. Rueckgabe: Zahl gesendeter Zeilen."""
    url = f"{_base_url()}/rest/v1/{TABLE}?on_conflict=client,linkedin_url"
    sent = 0
    for i in range(0, len(rows), CHUNK):
        payload = []
        for r in rows[i:i + CHUNK]:
            if not r.get("linkedin_url"):
                continue
            payload.append({"client": client,
                            "prio": int(r.get("prio") or 9),
                            "typ": r.get("typ") or "person",
                            "domain": r.get("domain") or "",
                            "company": r.get("company") or "",
                            "persona": r.get("persona") or "",
                            "first_name": r.get("first_name") or "",
                            "last_name": r.get("last_name") or "",
                            "title": r.get("title") or "",
                            "linkedin_url": r["linkedin_url"],
                            "source": r.get("source") or "",
                            "active_at": r.get("active_at")})
        if not payload:
            continue
        resp = requests.post(url, headers=_headers_write(), json=payload, timeout=TIMEOUT)
        _check(resp)
        sent += len(payload)
    return sent
