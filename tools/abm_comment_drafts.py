"""ABM-Kommentar-Entwuerfe auf frische Posts der Watchlist (OrLI W01).

Anders als der Influencer-Pfad (tools/comment_drafts.py, Wasserloecher der
Zielgruppe) zielt dieser Pfad auf die Committee-Personen der aktiven
ABM-Konten: ein Kommentar ist auf dem Post des Ziels garantiert sichtbar,
unabhaengig von der eigenen Reichweite. Ein Lauf pro Woche ueber die volle
Watchlist, alle Entwuerfe unter dem ABM-Absender (Reinhard, Entscheidung
2026-08-06). Ablage als Notion-Zeilen mit Status "ABM Kommentar". Posten
bleibt manuell - ein Kommentar unter fremdem Namen laeuft nie automatisiert.

Obergrenzen aus dem OrLI-W01-Brief, hier erzwungen statt nur dokumentiert:
hoechstens ein Kommentar je Person in 14 Tagen, hoechstens zwei je Firma
pro Woche (Fenster = die Notion-Historie der ABM-Zeilen).

Kosten je Lauf (harvestapi, pay per event): 0-Result-Query 0,001 USD,
Post 0,002 USD. Volle Watchlist ~411 Profile, deutsche Industrie postet
selten: realistisch ~0,45 USD pro Lauf.
"""
import csv
import os
import sys
from datetime import datetime, timezone

from apify_client import ApifyClient
from dotenv import load_dotenv

from clients import load_client
from tools.comment_drafts import draft_comment, _notify
from tools.linkedin_scraper import parse_post_age_hours
from tools.notion_db import (ABM_COMMENT_STATUS, create_comment_entry,
                             get_abm_comment_log, get_comment_target_urls)
from tools.topic_pool import get_meta, set_meta

load_dotenv()

APIFY_API_KEY = os.getenv("APIFY_API_KEY")


def load_watchlist(path: str) -> list:
    """Personen-Zeilen der Watchlist mit LinkedIn-URL, Prio-sortiert."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = [r for r in csv.DictReader(f)
                if r.get("typ") == "person" and r.get("linkedin_url")]
    rows.sort(key=lambda r: (r.get("prio") or "9", r.get("domain") or ""))
    return rows


def fetch_watchlist_posts(rows: list, settings: dict) -> list:
    """Ein Apify-Run ueber alle Watchlist-Profile, danach harter Altersfilter.
    Rueckgabe je Post inklusive Watchlist-Zeile (Domain, Name, Prio)."""
    if not APIFY_API_KEY:
        raise ValueError("APIFY_API_KEY fehlt in .env")
    by_url = {r["linkedin_url"]: r for r in rows}
    if not by_url:
        return []
    client = ApifyClient(APIFY_API_KEY)
    run = client.actor("harvestapi/linkedin-profile-posts").call(run_input={
        "targetUrls": list(by_url),
        "maxPosts": settings.get("max_posts_per_profile", 2),
        "postedLimit": settings.get("posted_limit", "week"),
        "includeReposts": False,
        "scrapeReactions": False,
        "scrapeComments": False,
    })
    if run is None:
        return []

    max_age = settings.get("max_age_hours", 168)
    min_words = settings.get("min_words", 25)
    posts = []
    dataset_id = getattr(run, "default_dataset_id", None) or run["defaultDatasetId"]
    for item in client.dataset(dataset_id).iterate_items():
        text = item.get("content", "") or ""
        url = item.get("linkedinUrl", "") or ""
        if not url or len(text.split()) < min_words:
            continue
        age = parse_post_age_hours(item.get("postedAt", ""))
        if age is None or age > max_age:
            continue
        target = (item.get("query", {}) or {}).get("targetUrl", "")
        row = by_url.get(target)
        if not row:
            continue
        posts.append({
            "post_url": url,
            "post_text": text,
            "influencer": f"{row['first_name']} {row['last_name']}".strip(),
            "author_url": row["linkedin_url"],
            "domain": row["domain"],
            "prio": row.get("prio", ""),
            "age_hours": age,
        })
    posts.sort(key=lambda p: (p["prio"] or "9", p["age_hours"]))
    return posts


def apply_caps(posts: list, log: list, now, settings: dict) -> list:
    """Erzwingt die Brief-Obergrenzen gegen die Notion-Historie:
    1 Kommentar je Person in `author_dedup_days`, 2 je Firma in 7 Tagen,
    `drafts_total` als Deckel des Laufs."""
    author_days = settings.get("author_dedup_days", 14)
    domain_cap = settings.get("per_domain_per_week", 2)
    total = settings.get("drafts_total", 10)

    blocked_authors = set()
    domain_counts: dict[str, int] = {}
    for entry in log:
        age_days = (now - entry["created"]).total_seconds() / 86400
        if entry.get("author_url") and age_days <= author_days:
            blocked_authors.add(entry["author_url"])
        if entry.get("domain") and age_days <= 7:
            domain_counts[entry["domain"]] = domain_counts.get(entry["domain"], 0) + 1

    picked = []
    for post in posts:
        if len(picked) >= total:
            break
        if post["author_url"] in blocked_authors:
            continue
        if domain_counts.get(post["domain"], 0) >= domain_cap:
            continue
        picked.append(post)
        blocked_authors.add(post["author_url"])
        domain_counts[post["domain"]] = domain_counts.get(post["domain"], 0) + 1
    return picked


def run_abm_comment_drafts(cfg=None, now=None) -> int:
    """Ein Wochenlauf: volle Watchlist scrapen, Caps anwenden, Entwuerfe
    unter dem ABM-Absender ablegen. Rueckgabe: Zahl geschriebener Zeilen."""
    cfg = cfg or load_client()
    now = now or datetime.now(timezone.utc)
    settings = getattr(cfg, "ABM_COMMENT_DRAFTS", None)
    if not settings:
        return 0

    if now.weekday() != settings.get("day", 0):
        print(f"  Kein ABM-Kommentar-Tag (weekday {now.weekday()}) - Skip.")
        return 0

    # Wochen-Guard: anders als beim Influenzer-Pfad wird er nach dem SCRAPE
    # gesetzt, nicht erst nach dem ersten Entwurf. Ein leeres Ergebnis ist
    # hier der Normalfall (deutsche Industrie postet selten), und der zweite
    # Cron-Slot desselben Tages soll nicht denselben Scrape doppelt bezahlen.
    meta_key = f"last_abm_comments_at_{cfg.NAME}"
    week = f"{now.isocalendar()[0]}-W{now.isocalendar()[1]:02d}"
    try:
        if get_meta(meta_key) == week:
            print("  ABM-Kommentare diese Woche schon gelaufen - Skip.")
            return 0
    except Exception as e:
        print(f"  Wochen-Guard nicht lesbar, Lauf faehrt trotzdem: {e}", file=sys.stderr)

    try:
        done = get_comment_target_urls()
        log = get_abm_comment_log()
    except Exception as e:
        print(f"  FEHLER - ABM-Dedup nicht lesbar, Abbruch: {e}", file=sys.stderr)
        return 0

    watchlist_path = settings.get("watchlist_csv") or getattr(cfg, "ABM_WATCHLIST_CSV", "")
    rows = load_watchlist(watchlist_path)
    posts = [p for p in fetch_watchlist_posts(rows, settings) if p["post_url"] not in done]
    print(f"  {len(rows)} Watchlist-Profile gescrapt, {len(posts)} frische Posts.")

    try:
        set_meta(meta_key, week)
    except Exception as e:
        print(f"  Wochen-Guard nicht schreibbar (nicht kritisch): {e}", file=sys.stderr)

    poster = settings.get("poster", "Reinhard")
    written = 0
    for post in apply_caps(posts, log, now, settings):
        try:
            draft = draft_comment(cfg, post, poster)
            if not draft:
                continue
            draft["title"] = f"ABM Kommentar: {post['influencer']} ({post['domain']})"[:250]
            create_comment_entry(draft, status=ABM_COMMENT_STATUS, extra_props={
                "ABM-Autor": {"url": post["author_url"]},
                "ABM-Domain": {"rich_text": [{"text": {"content": post["domain"]}}]},
            })
        except Exception as e:
            print(f"    FEHLER - ABM-Kommentar zu {post['post_url'][:60]}: {e}",
                  file=sys.stderr)
            continue
        written += 1
        print(f"    OK: {poster} -> {post['influencer'][:30]} ({post['domain']})")

    print(f"  ABM-Kommentar-Entwuerfe geschrieben: {written}")
    if written:
        _notify(cfg, written)
    return written


if __name__ == "__main__":
    run_abm_comment_drafts()
