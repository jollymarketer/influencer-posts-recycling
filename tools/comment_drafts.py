"""Kommentar-Entwuerfe auf frische Influencer-Posts.

Die Engine scrapt die Wasserloecher der Zielgruppe ohnehin schon, aber Reinhard
und Jae tauchen dort nie auf: eigene Posts ohne Netzwerk-Aktivitaet erreichen
niemanden. Dieser Schritt zieht die frischesten Posts eines rotierenden
Profil-Ausschnitts und legt fertige Kommentare als Notion-Zeilen (Status
"Kommentar") ab. Posten bleibt manuell - ein Kommentar unter fremdem Namen
laeuft nie automatisiert.

Kadenz: `days` schaltet die Lauftage (leer = taeglich), `drafts_total` deckelt
die Entwuerfe pro Lauf ueber alle Poster hinweg. Kosten: ein Apify-Run pro
Lauftag ueber `profiles_per_day` Profile mit `max_posts_per_profile` Posts
(Rotation deckt die volle Liste in wenigen Lauftagen).
"""
import os
import sys
from datetime import datetime, timezone

import anthropic
import requests
from apify_client import ApifyClient
from dotenv import load_dotenv

from clients import load_client
from tools.linkedin_scraper import load_influencers, parse_post_age_hours
from tools.notion_db import create_comment_entry, get_comment_target_urls
from tools.topic_pool import get_meta, set_meta

load_dotenv()

_cfg = load_client()
_llm = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
APIFY_API_KEY = os.getenv("APIFY_API_KEY")

COMMENT_MODEL = "claude-sonnet-4-6"

COMMENT_PROMPT = """Du schreibst einen LinkedIn-Kommentar unter einen fremden Post.

WER DU BIST
{voice}

KONTEXT DEINES UNTERNEHMENS (nur als Hintergrundwissen, NICHT als Werbeflaeche)
{context}

DER FREMDE POST von {influencer}
---
{post_text}
---

AUFGABE
Schreibe genau EINEN Kommentar, den {influencer} und seine Leser als echten
fachlichen Beitrag lesen, nicht als getarnte Werbung.

HARTE REGELN
- 2 bis 4 Saetze, nie laenger. Kein Absatz-Geschreibsel, keine Listen, keine Emojis.
- Sprache: exakt die Sprache des Posts oben. Englischer Post, englischer Kommentar.
- Ein eigener konkreter Gedanke aus der Praxis, den der Post NICHT enthaelt.
  Zustimmung allein ist wertlos, Widerspruch ohne Substanz auch.
- Niemals das eigene Produkt, den Firmennamen, eine Kundenreferenz, eine Zahl
  oder einen Link nennen. Kein Pitch, kein Angebot, kein Hinweis auf die eigene
  Website. Kein "bei uns sehen wir das so".
- Keine Floskeln: kein "Great post", kein "Couldn't agree more", kein "Danke fuers
  Teilen", keine Frage nur um der Frage willen.
- Keine Gedankenstriche als Satzzeichen.
- Wenn eine Frage am Ende steht, dann eine, die den Autor wirklich weiterbringt.
- Antworte NUR mit dem Kommentartext. Keine Anrede, keine Signatur, keine
  Erklaerung, kein Markdown.

DAZU EINE UEBERSCHRIFT
Gib in der ersten Zeile "ANSATZ: " plus 5 bis 10 Woerter aus, die den Winkel des
Kommentars beschreiben (interne Notiz, wird nicht gepostet). Danach eine
Leerzeile, dann der Kommentar."""


def rotate_profiles(influencers: list, per_day: int, day_index: int) -> list:
    """Deterministischer Ausschnitt der Profil-Liste. Der Offset waechst mit dem
    Tag, damit ueber wenige Tage jedes Profil drankommt."""
    pool = [i for i in influencers if i.get("linkedin_url")]
    if not pool or per_day <= 0:
        return []
    per_day = min(per_day, len(pool))
    start = (day_index * per_day) % len(pool)
    return [pool[(start + n) % len(pool)] for n in range(per_day)]


def fetch_fresh_posts(profiles: list, settings: dict) -> list:
    """Ein Apify-Run fuer alle Profile des Tages, danach harter Altersfilter."""
    if not APIFY_API_KEY:
        raise ValueError("APIFY_API_KEY fehlt in .env")
    by_url = {p["linkedin_url"]: p["name"] for p in profiles}
    if not by_url:
        return []
    client = ApifyClient(APIFY_API_KEY)
    run = client.actor("harvestapi/linkedin-profile-posts").call(run_input={
        "targetUrls": list(by_url),
        "maxPosts": settings.get("max_posts_per_profile", 2),
        # "week" ist der belegte Enum-Wert; das echte Fenster setzt max_age_hours.
        "postedLimit": settings.get("posted_limit", "week"),
        "includeReposts": False,
        "scrapeReactions": False,
        "scrapeComments": False,
    })
    if run is None:
        return []

    max_age = settings.get("max_age_hours", 30)
    posts = []
    for item in client.dataset(run.default_dataset_id).iterate_items():
        text = item.get("content", "") or ""
        url = item.get("linkedinUrl", "") or ""
        if not url or len(text.split()) < 40:
            continue
        age = parse_post_age_hours(item.get("postedAt", ""))
        if age is None or age > max_age:
            continue
        target = (item.get("query", {}) or {}).get("targetUrl", "")
        posts.append({
            "post_url": url,
            "post_text": text,
            "influencer": by_url.get(target) or (item.get("author", {}) or {}).get("name", ""),
            "age_hours": age,
            "engagement": item.get("engagement", {}) or {},
        })
    posts.sort(key=lambda p: p["age_hours"])
    return posts


def assign_posts(posts: list, posters: list, per_poster: int,
                 total: int | None = None) -> list:
    """Verteilt die frischesten Posts abwechselnd auf die Poster. Ein Post wird
    nur einmal vergeben: zwei Kommentare derselben Firma unter einem Post lesen
    sich als Kampagne.

    `total` ist der bindende Deckel des Laufs ueber alle Poster hinweg: liegt
    per_poster x Poster darunter, gewinnt `total` und per_poster wird
    angehoben. Sonst wuerde eine unbemerkt zu kleine per_poster-Zahl den
    Wunsch-Deckel still aushebeln (Fall 10.08.2026: drafts_total 5, aber
    drafts_per_poster 1 bei 2 Postern = 2 Entwuerfe). Ohne `total` bleibt es
    bei per_poster x Poster (Jolly-Pfad unveraendert)."""
    queue, assignments = list(posts), []
    slots = per_poster * len(posters)
    if total is not None:
        if slots < total:
            print(f"    Hinweis: drafts_per_poster {per_poster} x {len(posters)} Poster "
                  f"< drafts_total {total} - Deckel gewinnt.", file=sys.stderr)
        slots = total
    for idx in range(slots):
        if not queue:
            break
        assignments.append((posters[idx % len(posters)], queue.pop(0)))
    return assignments


def poster_rotation(posters: list, days, now) -> list:
    """Poster-Reihenfolge dieses Laufs.

    Bei gedeckelter Gesamtzahl (drafts_total) bekommt sonst immer derselbe
    Poster den Kommentar. Der Startindex wandert deshalb mit dem Lauf-Slot:
    ISO-Woche x Zahl der Lauftage + Position des heutigen Tages. Ueber
    tm_yday zu rotieren reicht nicht - Mo/Mi/Fr liegen alle auf geraden
    Abstaenden und wuerden bei zwei Postern nie wechseln."""
    if not posters:
        return posters
    slots = tuple(days) if days else ()
    if slots and now.weekday() in slots:
        index = now.isocalendar()[1] * len(slots) + slots.index(now.weekday())
    else:
        index = now.timetuple().tm_yday
    shift = index % len(posters)
    return posters[shift:] + posters[:shift]


def _voice(cfg, poster: str) -> str:
    """Autorenstimme des Posters aus der Persona-Config."""
    poster_map = getattr(cfg, "POSTER_BY_PERSONA", None) or {}
    persona_id = next((p for p, name in poster_map.items() if name == poster), "")
    for persona in getattr(cfg, "CONTENT_PERSONAS", None) or []:
        if persona.get("id") == persona_id and persona.get("voice_de"):
            return persona["voice_de"]
    return cfg.TOKENS.get("PERSONA_DE", "")


def draft_comment(cfg, post: dict, poster: str) -> dict | None:
    """Ein LLM-Call pro Kommentar. Rueckgabe None bei leerer Antwort."""
    prompt = COMMENT_PROMPT.format(
        voice=_voice(cfg, poster),
        context=cfg.CONTEXT.strip(),
        influencer=post.get("influencer", "der Autor"),
        post_text=post["post_text"][:4000],
    )
    resp = _llm.messages.create(model=COMMENT_MODEL, max_tokens=600,
                                messages=[{"role": "user", "content": prompt}])
    raw = resp.content[0].text.strip()
    angle, comment = "", raw
    if raw.upper().startswith("ANSATZ:"):
        head, _, rest = raw.partition("\n")
        angle = head.split(":", 1)[1].strip()
        comment = rest.strip()
    if not comment:
        return None
    return {
        "title": f"Kommentar {poster}: {angle or post.get('influencer', '')}"[:250],
        "comment": comment,
        "poster": poster,
        "target_url": post["post_url"],
        "influencer": post.get("influencer", ""),
        "excerpt": post["post_text"][:300],
    }


def _notify(cfg, count: int) -> None:
    """Kommentar-Queue-Mail via Make. Ohne MAKE_COMMENT_WEBHOOK stiller Skip."""
    url = os.environ.get("MAKE_COMMENT_WEBHOOK", "")
    if not url:
        return
    try:
        requests.post(url, json={
            "count": count,
            "date": datetime.now(timezone.utc).date().isoformat(),
            "view_url": getattr(cfg, "COMMENT_VIEW_URL", ""),
        }, timeout=15)
    except Exception as e:
        print(f"  Kommentar-Benachrichtigung fehlgeschlagen (nicht kritisch): {e}",
              file=sys.stderr)


def run_comment_drafts(cfg=None, now=None) -> int:
    """Ein Lauf: rotierender Profil-Ausschnitt, frische Posts, Kommentar-
    Entwuerfe bis zum Deckel. Rueckgabe: Zahl geschriebener Zeilen."""
    cfg = cfg or _cfg
    now = now or datetime.now(timezone.utc)
    settings = getattr(cfg, "COMMENT_DRAFTS", None)
    if not settings:
        print("  Kommentar-Entwuerfe nicht konfiguriert - Skip.")
        return 0

    # Wochentags-Gate vor jedem Kostenpunkt: ohne `days` bleibt es taeglich.
    days = settings.get("days")
    if days and now.weekday() not in tuple(days):
        print(f"  Kein Kommentar-Tag (weekday {now.weekday()}) - Skip.")
        return 0

    # Tages-Guard (analog last_slate_at_<client>): der Cron faehrt zwei Slots
    # pro Tag, Kommentar-Entwuerfe sollen nur einmal entstehen. Bewusst NICHT
    # fatal: ist Supabase nicht lesbar, laufen die Entwuerfe lieber doppelt als
    # gar nicht. Gesetzt wird der Guard erst nach dem ersten geschriebenen
    # Entwurf, damit ein leerer Morgenlauf den Mittagslauf nicht verbrennt.
    meta_key = f"last_comments_at_{cfg.NAME}"
    today = now.date().isoformat()
    try:
        if get_meta(meta_key) == today:
            print("  Kommentar-Entwuerfe heute schon gebaut - Skip.")
            return 0
    except Exception as e:
        print(f"  Tages-Guard nicht lesbar, Lauf faehrt trotzdem: {e}", file=sys.stderr)

    try:
        done = get_comment_target_urls()
    except Exception as e:
        print(f"  FEHLER - Kommentar-Dedup nicht lesbar, Abbruch: {e}", file=sys.stderr)
        return 0

    profiles = rotate_profiles(load_influencers(), settings.get("profiles_per_day", 12),
                               now.timetuple().tm_yday)
    posts = [p for p in fetch_fresh_posts(profiles, settings) if p["post_url"] not in done]
    print(f"  {len(profiles)} Profile rotiert, {len(posts)} frische Posts uebrig.")
    if not posts:
        return 0

    posters = poster_rotation(
        settings.get("posters") or [getattr(cfg, "POSTER_DEFAULT", "")], days, now)
    per_poster = settings.get("drafts_per_poster", 3)
    written = 0
    for poster, post in assign_posts(posts, posters, per_poster,
                                     total=settings.get("drafts_total")):
        try:
            draft = draft_comment(cfg, post, poster)
            if not draft:
                continue
            create_comment_entry(draft)
        except Exception as e:
            print(f"    FEHLER - Kommentar zu {post['post_url'][:60]}: {e}",
                  file=sys.stderr)
            continue
        written += 1
        print(f"    OK: {poster} -> {post.get('influencer', '')[:30]}")

    print(f"  Kommentar-Entwuerfe geschrieben: {written}")
    if written:
        try:
            set_meta(meta_key, today)
        except Exception as e:
            print(f"  Tages-Guard nicht schreibbar (nicht kritisch): {e}", file=sys.stderr)
        _notify(cfg, written)
    return written


if __name__ == "__main__":
    run_comment_drafts()
