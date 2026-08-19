"""
LinkedIn Post Scraper via Apify
Actor: harvestapi/linkedin-profile-posts
- Scrapt Posts der letzten Woche
- Filtert auf Posts, die 1-5 Tage alt sind (Engagement hat Zeit zu akkumulieren)
- Extrahiert Engagement-Metriken fuer Viralitaets-Scoring
"""

import csv
import os
import sys
from datetime import datetime, timezone, timedelta

from tools.apify_auth import apify_client
from dotenv import load_dotenv

from clients import load_client
from tools.topic_pool import get_meta, set_meta

load_dotenv()

# Windows-Default cp1252 kann viele Influencer-Namen (Alić, Trümpi, Nordström, ...)
# nicht encoden — beim print() crasht das Skript. UTF-8 erzwingen.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Token und Kontowache pro Mandant, siehe tools/apify_auth.py
_cfg = load_client()
INFLUENCERS_CSV = _cfg.INFLUENCERS_CSV

# Kadenz-Parameter pro Mandant (clients/<name>/config.py, SCRAPE-Block).
# Jolly daily: Filter 6-36h, max 3 Posts/Profil. Lisocon weekly: 6-168h, max 10.
# Mindest-Alter 6h: sonst werden frische Posts gefiltert, bevor Engagement reifen konnte.
# Das Apify-Fetch-Fenster (postedLimitDate, s. fetch_window_start) MUSS > MAX_AGE_HOURS
# sein, sonst faellt ein Post, der beim letzten Run zu jung (also gefiltert) war, beim
# naechsten Run aus dem Fetch-Fenster und wird nie gesehen.
MIN_AGE_HOURS = _cfg.SCRAPE["min_age_hours"]
MAX_AGE_HOURS = _cfg.SCRAPE["max_age_hours"]
MAX_POSTS_PER_PROFILE = _cfg.SCRAPE["max_posts_per_profile"]

# Puffer auf das Fetch-Fenster, damit ein verspaeteter Cron-Lauf keinen Post verliert.
FETCH_BUFFER_HOURS = 4

# Profile pro Apify-Run. targetUrls nimmt eine Liste, maxPosts gilt laut Actor-Schema
# "per each profile or company" — Buendeln aendert also nichts an der Abrechnung, spart
# aber Actor-Starts und Laufzeit (78 sequentielle Runs = ~8 Min). Klein genug, dass ein
# fehlgeschlagener Run nur einen Teil der Liste kostet, nicht die ganze.
BATCH_SIZE = 20

# Zeitmarke des letzten vollstaendigen Laufs (engine_meta). Schluessel pro Mandant,
# weil alle Mandanten dieselbe Supabase-Instanz teilen.
WATERMARK_KEY = f"last_scrape_at_{os.getenv('CLIENT', 'jolly').strip().lower()}"

# Kleiner Aufschlag auf die Zeitmarke gegen Uhrzeit-Drift zwischen Railway und Apify.
WATERMARK_BUFFER_HOURS = 1


def load_influencers():
    influencers = []
    with open(INFLUENCERS_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            influencers.append({
                "name": row["Name"].strip(),
                "linkedin_url": row["LinkedIn URL"].strip(),
            })
    return influencers


def read_watermark() -> datetime | None:
    """Startzeit des letzten vollstaendigen Laufs, oder None wenn unbekannt."""
    try:
        raw = get_meta(WATERMARK_KEY)
    except Exception as e:
        print(f"  Zeitmarke nicht lesbar, nutze Standardfenster: {e}", file=sys.stderr)
        return None
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def write_watermark(started_at: datetime) -> None:
    """Zeitmarke auf die Startzeit dieses Laufs setzen. Nicht kritisch: schlaegt das
    fehl, faellt der naechste Lauf auf das breitere Standardfenster zurueck."""
    try:
        set_meta(WATERMARK_KEY, started_at.strftime("%Y-%m-%dT%H:%M:%S.000Z"))
    except Exception as e:
        print(f"  Zeitmarke nicht gespeichert (nicht kritisch): {e}", file=sys.stderr)


def fetch_window_start(now: datetime | None = None) -> str:
    """Frueheste Post-Zeit, die der Actor liefern soll, als ISO-8601-String.

    Apify rechnet pro geliefertem Post ab (0,002 USD). Mit dem Enum postedLimit
    war das schmalste Fenster "24h" zu eng (ein Post, der beim letzten Lauf mit
    <6h gefiltert wurde, faellt sonst aus dem Fetch-Fenster) und "week" mit 168h
    viel zu weit: bei MAX_AGE_HOURS=36 wurden ~4 von 5 gelieferten Posts sofort
    vom Altersfilter verworfen und trotzdem bezahlt. postedLimitDate nimmt ein
    exaktes Datum und schneidet dieselben Posts serverseitig ab.

    Zwei Grenzen, die engere gewinnt:

    1. Obergrenze MAX_AGE_HOURS + FETCH_BUFFER_HOURS. Alles Aeltere wuerde der
       Altersfilter ohnehin verwerfen, waere aber bezahlt. Gilt auch als Fallback,
       solange keine Zeitmarke existiert.
    2. Zeitmarke des letzten Laufs minus MIN_AGE_HOURS. Weiter zurueck muss das
       Fenster nicht reichen: alles Aeltere hat der letzte Lauf schon gesehen und
       bezahlt. Nur die Posts, die er als zu jung verworfen hat, muessen erneut
       hinein — daher der Abzug von MIN_AGE_HOURS.

    Gemessen 10.-17.08.: bei festem 40h-Fenster und taeglichem Cron wurden 42 von
    425 gelieferten Posts ein zweites Mal geliefert und bezahlt, nur um danach am
    Duplikat-Filter zu scheitern. Grenze 2 schneidet diese Ueberlappung weg.
    """
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=MAX_AGE_HOURS + FETCH_BUFFER_HOURS)
    mark = read_watermark()
    if mark:
        cutoff = max(cutoff, mark - timedelta(hours=MIN_AGE_HOURS + WATERMARK_BUFFER_HOURS))
    return _window_iso(cutoff)


def _window_iso(cutoff: datetime) -> str:
    return cutoff.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def window_start_for(max_age_hours: float, now: datetime | None = None) -> str:
    """postedLimitDate fuer einen Aufrufer mit eigenem Altersfilter (Kommentar-Pfade).

    Ohne Zeitmarke, weil dort das Fenster ohnehin dem Laufabstand entspricht. Ersetzt
    das Enum postedLimit: dessen schmalster brauchbarer Wert "week" holt 168h, waehrend
    z.B. der Kommentar-Pfad auf 72h filtert. Gemessen 18.07.-17.08.2026: von 342
    gelieferten Posts lagen 178 ausserhalb des 72h-Filters — bezahlt und sofort
    verworfen. FETCH_BUFFER_HOURS haelt das Fenster echt groesser als den Filter.
    """
    now = now or datetime.now(timezone.utc)
    return _window_iso(now - timedelta(hours=max_age_hours + FETCH_BUFFER_HOURS))


def profile_key(url: str) -> str:
    """Vergleichbarer Schluessel aus einer LinkedIn-Profil-URL (Query und / weg)."""
    return url.split("?")[0].rstrip("/").lower()


def target_url_of(item) -> str:
    """Die Eingabe-URL, aus der dieses Item stammt. Der Actor spiegelt sie in
    item["query"]["targetUrl"] — ohne sie waere im Sammel-Run nicht zuordenbar,
    zu welchem Influencer ein Post gehoert."""
    query = item.get("query")
    if isinstance(query, dict):
        return profile_key(query.get("targetUrl", "") or "")
    return ""


def author_name_of(item) -> str:
    author = item.get("author")
    if isinstance(author, dict):
        return author.get("name") or ""
    return ""


def scrape_posts_for_batch(client, profile_urls, max_posts=3, window_start=None):
    """Ein Apify-Run fuer mehrere Profile. maxPosts gilt laut Actor-Schema pro
    Profil, das Buendeln aendert die Abrechnung also nicht."""
    run_input = {
        "targetUrls": list(profile_urls),
        "maxPosts": max_posts,
        "postedLimitDate": window_start or fetch_window_start(),
        "includeQuotePosts": True,
        "includeReposts": False,
        "scrapeReactions": False,
        "scrapeComments": False,
    }
    run = client.actor("harvestapi/linkedin-profile-posts").call(run_input=run_input)
    if run is None:
        return []
    items = list(client.dataset(run.default_dataset_id).iterate_items())
    return items


def parse_post_age_hours(posted_at) -> float | None:
    """Gibt das Alter des Posts in Stunden zurueck. None wenn nicht parsbar."""
    if not posted_at:
        return None
    try:
        if isinstance(posted_at, dict):
            # Millisekunden-Timestamp
            if "timestamp" in posted_at:
                ts_ms = posted_at["timestamp"]
                post_dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
            elif "date" in posted_at:
                post_dt = datetime.fromisoformat(posted_at["date"].replace("Z", "+00:00"))
            else:
                return None
        elif isinstance(posted_at, str):
            post_dt = datetime.fromisoformat(posted_at.replace("Z", "+00:00"))
        else:
            return None
        now = datetime.now(timezone.utc)
        age_hours = (now - post_dt).total_seconds() / 3600
        return age_hours
    except Exception:
        return None


def extract_engagement(item) -> dict:
    """Extrahiert Engagement-Metriken aus dem Apify-Response-Item."""
    eng = item.get("engagement", {})
    if isinstance(eng, dict):
        return {
            "likes": eng.get("likes", 0) or 0,
            "comments": eng.get("comments", 0) or 0,
            "shares": eng.get("shares", 0) or 0,
        }
    return {"likes": 0, "comments": 0, "shares": 0}


def extract_post_data(item, influencer_name):
    post_url = item.get("linkedinUrl", "")
    post_text = item.get("content", "")
    posted_at = item.get("postedAt", "")

    if not post_url or not post_text:
        return None

    # Mindestlaenge: Posts unter 50 Woertern sind kein verwertbarer Content
    if len(post_text.split()) < 50:
        return None

    # Alter berechnen
    age_hours = parse_post_age_hours(posted_at)

    # Datum fuer Notion
    if isinstance(posted_at, dict):
        date_str = posted_at.get("date", datetime.now(timezone.utc).isoformat())
    else:
        date_str = str(posted_at) if posted_at else datetime.now(timezone.utc).isoformat()

    engagement = extract_engagement(item)

    return {
        "influencer": influencer_name,
        "post_url": post_url,
        "post_text": post_text,
        "post_excerpt": post_text[:300],
        "date": date_str,
        "age_hours": age_hours,
        "engagement": engagement,
    }


def scrape_new_posts(existing_urls: set) -> list:
    """
    Scrapt neue Posts fuer alle Influencer.
    Filtert auf Posts die 1-5 Tage alt sind (optimale Viralitaets-Messung).
    existing_urls: Set von Post-URLs die bereits in Notion vorhanden sind.
    """

    started_at = datetime.now(timezone.utc)
    client = apify_client()
    influencers = [i for i in load_influencers() if i["linkedin_url"]]
    name_by_url = {profile_key(i["linkedin_url"]): i["name"] for i in influencers}
    urls = [i["linkedin_url"] for i in influencers]

    # Einmal lesen: das Fenster muss ueber alle Batches identisch sein, sonst
    # bekommen spaetere Batches ein minimal anderes Fenster als fruehere.
    window_start = fetch_window_start(started_at)

    new_posts = []
    failed_batches = 0

    for start in range(0, len(urls), BATCH_SIZE):
        batch = urls[start:start + BATCH_SIZE]
        print(f"  Scraping Profile {start + 1}-{start + len(batch)} von {len(urls)} ...",
              flush=True)
        try:
            items = scrape_posts_for_batch(client, batch, max_posts=MAX_POSTS_PER_PROFILE,
                                           window_start=window_start)
        except Exception as e:
            failed_batches += 1
            print(f"    FEHLER bei Batch ab {batch[0]}: {e}", file=sys.stderr)
            continue

        for item in items:
            name = name_by_url.get(target_url_of(item)) or author_name_of(item)
            post = extract_post_data(item, name)
            if not post:
                continue
            if post["post_url"] in existing_urls:
                continue

            # Altersfilter: nur Posts aus dem 1-5-Tage-Fenster
            age = post.get("age_hours")
            if age is not None and not (MIN_AGE_HOURS <= age <= MAX_AGE_HOURS):
                continue

            new_posts.append(post)
            eng = post["engagement"]
            print(
                f"    OK: {post['post_url'][:70]} "
                f"| {eng['likes']} Likes, {eng['comments']} Comments"
            )

    # Zeitmarke nur bei vollstaendigem Lauf setzen. Nach einem Teilausfall bleibt
    # sie stehen, der naechste Lauf faellt auf das breitere Standardfenster zurueck
    # und holt die Profile des ausgefallenen Batches nach.
    if failed_batches:
        print(f"  {failed_batches} Batch(es) fehlgeschlagen, Zeitmarke bleibt stehen.",
              file=sys.stderr)
    else:
        write_watermark(started_at)

    return new_posts


if __name__ == "__main__":
    posts = scrape_new_posts(existing_urls=set())
    print(f"\nGesamt neue Posts: {len(posts)}")
    for p in posts:
        eng = p.get("engagement", {})
        print(f"  [{p.get('age_hours', '?'):.0f}h alt | {eng.get('likes', 0)} Likes] "
              f"{p['influencer']}: {p['post_excerpt'][:60]}...")
