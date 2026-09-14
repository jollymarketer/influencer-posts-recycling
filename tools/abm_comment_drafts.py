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
import json
import os
import re
import sys
from datetime import datetime, timezone

from tools.apify_auth import apify_client
from dotenv import load_dotenv

from clients import load_client
from tools.anthropic_auth import LazyAnthropic
from tools.comment_drafts import draft_comment, _notify
from tools.linkedin_keyword_scraper import is_hiring_ad
from tools.linkedin_scraper import parse_post_age_hours, window_start_for
from tools.notion_db import (ABM_COMMENT_STATUS, create_comment_entry,
                             get_abm_comment_log, get_comment_target_urls)
from tools.topic_pool import get_meta, set_meta
from tools.watchlist_db import get_watchlist

load_dotenv()

# Token und Kontowache pro Mandant, siehe tools/apify_auth.py

# Jolly (14.09.2026) faehrt denselben Pfad als Tageslauf: `day` None statt
# Wochentag, `profiles_per_run` rotiert einen Ausschnitt der Watchlist je Tag
# (Apify zahlt je Post, die volle Liste taeglich kostet das Dreifache),
# `exclude_companies` sperrt eigene Kunden, `relevance_gate` laesst Haiku
# pruefen, ob der Post ein Fachbeitrag ist. lisocon bleibt beim Wochenlauf.
GATE_MODEL = "claude-haiku-4-5-20251001"


def filter_watchlist(rows: list, exclude: list | None = None) -> list:
    """Personen mit LinkedIn-URL, Prio-sortiert. exclude: Namensteile eigener
    Kunden (Firma oder Domain, ohne Gross/Klein), die nie kommentiert werden.
    HubSpot traegt auch Kundenkontakte (Jolly 14.09.2026)."""
    pat = re.compile("|".join(re.escape(e) for e in exclude), re.I) if exclude else None
    out = [r for r in rows
           if r.get("typ") == "person" and r.get("linkedin_url")
           and not (pat and pat.search(f"{r.get('company', '')} {r.get('domain', '')}"))]
    out.sort(key=lambda r: (r.get("prio") or "9", r.get("domain") or ""))
    return out


def load_watchlist(path: str, exclude: list | None = None) -> list:
    """Watchlist aus der CSV (lisocon-Format)."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        return filter_watchlist(list(csv.DictReader(f)), exclude)


def watchlist_rows(cfg, settings: dict) -> list:
    """Quelle je Mandant: settings["watchlist_source"] == "db" liest die Tabelle
    comment_watchlist (tools/watchlist_db), sonst die CSV. Prospect-Listen
    liegen seit 14.09.2026 nicht mehr im oeffentlichen Repo."""
    exclude = settings.get("exclude_companies")
    if settings.get("watchlist_source") == "db":
        return filter_watchlist(get_watchlist(cfg.NAME), exclude)
    path = settings.get("watchlist_csv") or getattr(cfg, "ABM_WATCHLIST_CSV", "")
    return load_watchlist(path, exclude)


def rotate_watchlist(rows: list, per_run: int | None, day_index: int) -> list:
    """Deterministischer Ausschnitt je Lauf (wie comment_drafts.rotate_profiles):
    der Offset wandert mit dem Tag, ueber wenige Tage kommt jede Zeile dran.
    per_run None oder 0: die ganze Liste."""
    if not rows or not per_run:
        return rows
    per_run = min(per_run, len(rows))
    start = (day_index * per_run) % len(rows)
    return [rows[(start + n) % len(rows)] for n in range(per_run)]


def fetch_watchlist_posts(rows: list, settings: dict) -> list:
    """Ein Apify-Run ueber alle Watchlist-Profile, danach harter Altersfilter.
    Rueckgabe je Post inklusive Watchlist-Zeile (Domain, Name, Prio)."""
    by_url = {r["linkedin_url"]: r for r in rows}
    if not by_url:
        return []
    max_age = settings.get("max_age_hours", 168)
    min_words = settings.get("min_words", 25)
    client = apify_client()
    run = client.actor("harvestapi/linkedin-profile-posts").call(run_input={
        "targetUrls": list(by_url),
        "maxPosts": settings.get("max_posts_per_profile", 2),
        # Exaktes Datum statt Enum: der Actor zahlt je geliefertem Post, das
        # Fenster entspricht dem Altersfilter plus Puffer (window_start_for).
        "postedLimitDate": window_start_for(max_age),
        "includeReposts": False,
        "scrapeReactions": False,
        "scrapeComments": False,
    })
    if run is None:
        return []

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
            "domain": row.get("domain", ""),
            "company": row.get("company", ""),
            "prio": row.get("prio", ""),
            "age_hours": age,
        })
    posts.sort(key=lambda p: (p["prio"] or "9", p["age_hours"]))
    return posts


GATE_PROMPT = """Du prüfst, ob ein LinkedIn-Post eines Zielkunden ein fachlicher Beitrag ist, unter dem ein Kommentar von {poster} als Praktiker Sinn ergibt.

Nicht kommentierbar: Stellenanzeige, Event- oder Messe-Werbung, Produkt-Launch ohne inhaltliche Aussage, private Anlässe (Urlaub, Jubiläum, Geburtstag, Auszeichnung), reines Weiterreichen fremder Inhalte, Sprache weder Deutsch noch Englisch.
Score 10: Fachthema mit eigener These oder Erfahrung, an die sich anknüpfen lässt. Score 0: nichts zum Anknüpfen.

POST von {name} ({title}, {company}):
---
{text}
---
Antworte NUR mit JSON: {{"kommentierbar": true oder false, "score": 0 bis 10, "grund": "<ein Satz>"}}"""

_gate_clients: dict = {}


def _gate_client(cfg):
    """Haiku-Client des Mandanten fuer das Relevanz-Gate, einmal je Prozess."""
    if cfg.NAME not in _gate_clients:
        _gate_clients[cfg.NAME] = LazyAnthropic(cfg)
    return _gate_clients[cfg.NAME]


def _parse_gate(raw: str) -> tuple[bool, int, str]:
    m = re.search(r"\{.*\}", raw or "", re.S)
    if not m:
        return False, 0, ""
    try:
        d = json.loads(m.group(0))
        return bool(d.get("kommentierbar")), int(d.get("score") or 0), str(d.get("grund") or "")[:200]
    except (ValueError, TypeError):
        return False, 0, ""


def relevance_gate(posts: list, cfg, settings: dict) -> list:
    """Nur mit settings["relevance_gate"]: Stellenanzeigen fallen ohne
    Modellaufruf, den Rest bewertet Haiku (GATE_PROMPT). Es bleiben Posts mit
    kommentierbar=true und Score >= min_relevance, absteigend nach Score,
    bei Gleichstand nach Prio und Alter. Ohne Gate: Liste unveraendert."""
    if not settings.get("relevance_gate"):
        return posts
    min_score = int(settings.get("min_relevance", 6))
    poster = settings.get("poster", "")
    kept = []
    for post in posts:
        if is_hiring_ad(post["post_text"]):
            continue
        prompt = GATE_PROMPT.format(poster=poster, name=post.get("influencer", ""),
                                    title=post.get("title", ""), company=post.get("company", ""),
                                    text=post["post_text"][:2500])
        try:
            resp = _gate_client(cfg).messages.create(
                model=GATE_MODEL, max_tokens=200,
                messages=[{"role": "user", "content": prompt}])
            ok, score, grund = _parse_gate(resp.content[0].text)
        except Exception as e:
            print(f"    Gate-Fehler (Post uebersprungen): {e}", file=sys.stderr)
            continue
        if ok and score >= min_score:
            kept.append({**post, "relevance": score, "relevance_grund": grund})
    kept.sort(key=lambda p: (-p["relevance"], p["prio"] or "9", p["age_hours"]))
    return kept


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

    daily = settings.get("day", 0) is None
    if not daily and now.weekday() != settings.get("day", 0):
        print(f"  Kein ABM-Kommentar-Tag (weekday {now.weekday()}) - Skip.")
        return 0

    # Guard je Woche (Wochenlauf) oder je Tag (Tageslauf): anders als beim
    # Influenzer-Pfad wird er nach dem SCRAPE gesetzt, nicht erst nach dem
    # ersten Entwurf. Ein leeres Ergebnis ist hier der Normalfall (deutsche
    # Industrie postet selten), und der zweite Cron-Slot desselben Tages soll
    # nicht denselben Scrape doppelt bezahlen.
    meta_key = f"last_abm_comments_at_{cfg.NAME}"
    week = (now.date().isoformat() if daily
            else f"{now.isocalendar()[0]}-W{now.isocalendar()[1]:02d}")
    try:
        if get_meta(meta_key) == week:
            print("  ABM-Kommentare in diesem Fenster schon gelaufen - Skip.")
            return 0
    except Exception as e:
        print(f"  Guard nicht lesbar, Lauf faehrt trotzdem: {e}", file=sys.stderr)

    try:
        done = get_comment_target_urls()
        log = get_abm_comment_log()
    except Exception as e:
        print(f"  FEHLER - ABM-Dedup nicht lesbar, Abbruch: {e}", file=sys.stderr)
        return 0

    rows = rotate_watchlist(watchlist_rows(cfg, settings), settings.get("profiles_per_run"),
                            now.timetuple().tm_yday)
    posts = [p for p in fetch_watchlist_posts(rows, settings) if p["post_url"] not in done]
    print(f"  {len(rows)} Watchlist-Profile gescrapt, {len(posts)} frische Posts.")
    posts = relevance_gate(posts, cfg, settings)
    if settings.get("relevance_gate"):
        print(f"  Relevanz-Gate: {len(posts)} kommentierbar.")

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
            typ = f" [{draft['typ']}]" if draft.get("typ") else ""
            wo = post.get("domain") or post.get("company") or ""
            draft["title"] = f"ABM Kommentar{typ}: {post['influencer']} ({wo})"[:250]
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
