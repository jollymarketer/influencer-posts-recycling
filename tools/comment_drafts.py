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
import re
import sys
from datetime import datetime, timezone

import anthropic
import requests
from tools.anthropic_auth import LazyAnthropic
from tools.apify_auth import apify_client
from dotenv import load_dotenv

from clients import load_client
from tools.linkedin_scraper import (load_influencers, parse_post_age_hours,
                                    window_start_for)
from tools.notion_db import create_comment_entry, get_comment_target_urls
from tools.topic_pool import get_meta, set_meta

load_dotenv()

_cfg = load_client()
# Key pro Mandant, siehe tools/anthropic_auth.py (08.09.2026)
_llm = LazyAnthropic(_cfg)
# Token und Kontowache pro Mandant, siehe tools/apify_auth.py

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

KOMMENTAR-TYPEN
Wähle den Typ, der zu diesem Post passt. Nie aus Gewohnheit Typ 1.
{types}{avoid}

HARTE REGELN
- {length_rule} Kein Absatz-Geschreibsel, keine Listen.
- {emoji_rule}{style_rules}
- Sprache: exakt die Sprache des Posts oben. Englischer Post, englischer Kommentar.
- Ein eigener konkreter Gedanke aus der Praxis, den der Post NICHT enthaelt.
  Zustimmung allein ist wertlos, Widerspruch ohne Substanz auch. Den Post nie
  nacherzaehlen. Ein Gedanke, nicht zwei.
- Mehrwert-Test: Der Kommentar enthaelt mindestens eines davon, das im Post fehlt:
  einen Test oder Handgriff, den ein Leser morgen anwenden kann; eine konkrete
  Szene mit Rolle und Handlung (wer tut was, wann); eine andere Antwort auf die
  Frage des Autors. Allgemeine Weisheiten zaehlen nicht. Die Schlussfrage des
  Autors nie nur in eigene Worte fassen.
- Keine Schablonensaetze: nicht "X stimmt, bis/solange ...", nicht "Das ist kein
  X-Problem, sondern ...", nicht "Die meisten ...", nicht "Wer X, der Y", nicht
  "Das ist der Moment/Schritt, der ...". Konkrete Rollen, Dinge und Handlungen
  statt abstrakter Woerter wie Bedarf, Fundament, Wert oder Perspektive.
- Niemals das eigene Produkt, den Firmennamen, eine Kundenreferenz, eine Zahl
  oder einen Link nennen. Kein Pitch, kein Angebot, kein Hinweis auf die eigene
  Website. Kein "bei uns sehen wir das so".
- Keine Floskeln als Einstieg: kein "Great post", "Love this", "Couldn't agree more",
  "Toller Beitrag", "Danke fürs Teilen", "Sehe ich genauso", "Absolut", "Spannend",
  kein Vorname mit Ausrufezeichen. Keine Frage nur um der Frage willen.
- Keine Gedankenstriche als Satzzeichen.
- Einfach und beim ersten Lesen verstaendlich, auch fuer jemanden, der den Post
  nur ueberflogen hat. Hoechstens {max_words} Woerter je Satz, ein Gedanke je
  Satz, keine Schachtelsaetze. Alltagswoerter statt Jargon und Bildsprache (nicht
  "finish line", "owns the context", "frame", "running the structure").
  Begriffe aus dem Post in einfachen Worten aufgreifen, nie als Etikett wie
  "the three-challenge frame from the top tier".
- Wenn eine Frage am Ende steht, dann eine, die den Autor wirklich weiterbringt.
- Antworte NUR mit dem Kommentartext. Keine Anrede, keine Signatur, keine
  Erklaerung, kein Markdown.

DAZU ZWEI KOPFZEILEN (interne Notiz, wird nicht gepostet)
Erste Zeile "TYP: " plus Nummer und Name des gewählten Typs, zum Beispiel
"TYP: 4 Eine Zeile weiterbauen". Zweite Zeile "ANSATZ: " plus 5 bis 10 Woerter, die den
Winkel des Kommentars beschreiben. Danach eine Leerzeile, dann der Kommentar."""

_AVOID_NOTE = ("\n\nNICHT diesen Typ, in diesem Lauf schon verwendet: {types}. "
               "Ein Kommentar-Lauf mit lauter gleichen Typen liest sich als Serie.")

# Nummern bleiben fest, auch wenn ein Mandant Typen sperrt: die Nummer steht in
# den Notion-Titeln alter Entwuerfe.
COMMENT_TYPES = [
    (1, "Das Datum", "eine eigene Beobachtung, die den Punkt des Posts stützt oder relativiert."),
    # Richard 23.09.2026: die woertlichen Satzmuster in Typ 2 und 8 landeten als
    # Schablone in fast jedem Entwurf ("stimmt, bis", "Anders gelesen:").
    (2, "Fehlender Fall", "die Grenze der Aussage an einem konkreten Fall zeigen, in dem sie nicht mehr gilt."),
    (3, "Widerspruch mit Substanz", "erst der Teil, der stimmt, dann die Gabelung."),
    (4, "Eine Zeile weiterbauen", "eine Zeile des Posts wörtlich aufgreifen und daran weiterdenken."),
    (5, "Die echte Frage", 'eine Frage, deren Antwort den Autor weiterbringt. Nie "würde mich interessieren".'),
    (6, "Der Beleg", "du hast das selbst erlebt; zwei Sätze, was dabei passiert ist, ohne Firma und ohne Zahl."),
    (7, "Die Korrektur", "ein sachlicher Fehler im Post. Richtig, kurz, freundlich, nur wenn du sicher bist."),
    (8, "Der Reframe", "derselbe Sachverhalt aus Sicht einer anderen Rolle, etwa Käufer statt Anbieter."),
    (9, "Der Einzeiler", "unter zwölf Wörtern, treffend oder witzig."),
]
LENGTH_RULE_DEFAULT = "2 bis 4 Saetze, nie laenger."


def _types_block(banned=()) -> str:
    return "\n".join(f"{n}. {name}: {desc}" for n, name, desc in COMMENT_TYPES
                     if name not in banned)


# Kommentar-Stil je Mandant (cfg.COMMENT_STYLE), Richard 15.09.2026 fuer Jolly:
# 30 bis 40 Woerter, Witz mit Leitplanken, konkretes Detail aus dem Post,
# Anrede spiegelt den Post, Floskeln und Pitch gemessen statt nur verboten.
# Witz nur, wenn das Relevanz-Gate den Post ausdruecklich als nicht ernst
# markiert hat (post["ernst"] is False); ohne Gate-Urteil kein Witz.
HUMOR_ON = ("- Genau ein Satz mit spürbarem Augenzwinkern: trockene Selbstironie über den "
            "Alltag in Vertrieb, Marketing oder Agenturen, sodass der Autor beim Lesen "
            "schmunzelt. Nie auf Kosten des Autors, keine Wortspiele mit Namen, kein "
            "erfundenes eigenes Erlebnis. Der fachliche Gedanke bleibt der Kern.")
HUMOR_OFF = "- Kein Witz, keine Ironie: ruhig, respektvoll, sachlich."
STYLE_RULES = """
- Greife ein konkretes Detail aus dem Post auf, ein Wort oder Beispiel, das nur in
  diesem Post steht. Wer den Kommentar liest, merkt: du hast den Post gelesen.
- Anrede spiegelt den Post: duzt der Autor seine Leser, sprich ihn mit du an.
  Sonst neutral ohne direkte Anrede. Nie Sie.
- Höchstens eine Frage, und nur, wenn sie wirklich weiterführt.
- Nie {brand} erwähnen, nie pitchen.
{humor}"""

FLOSKELN = ["spannender beitrag", "spannender post", "spannendes thema", "toller beitrag",
            "starker beitrag", "guter beitrag", "super beitrag", "danke fürs teilen",
            "danke für das teilen", "danke für den beitrag", "genau das", "sehe ich genauso",
            "sehe ich auch so", "kann ich nur unterschreiben", "absolut", "auf den punkt",
            "wichtiger punkt", "guter punkt", "great post", "love this", "couldn't agree more",
            "thanks for sharing", "spot on", "game changer", "gamechanger", "100%"]
_DU = re.compile(r"\b(du|dich|dir|dein|deine|deinen|deinem|deiner|deines|euch|euer|eure)\b", re.I)
_SIE = {"Sie", "Ihnen", "Ihr", "Ihre", "Ihren", "Ihrem", "Ihrer", "Ihres"}
_WORD = re.compile(r"\w", re.U)


def word_count(text: str) -> int:
    """Woerter ohne Emoji und lose Satzzeichen."""
    return sum(1 for w in (text or "").split() if _WORD.search(w))


def style_issues(text: str, post_text: str, style: dict) -> list[str]:
    """Messbare Verstoesse gegen cfg.COMMENT_STYLE."""
    issues = []
    low = (text or "").lower()
    lo, hi = style.get("words", (30, 40))
    n = word_count(text)
    if not lo <= n <= hi:
        issues.append(f"{n} Woerter, erlaubt sind {lo} bis {hi}")
    hits = [f for f in FLOSKELN if re.search(r"(?<!\w)" + re.escape(f) + r"(?!\w)", low)]
    if hits:
        issues.append(f"Floskel entfernen: {', '.join(hits)}")
    if text.count("?") > 1:
        issues.append("Hoechstens eine Frage")
    brands = [b for b in style.get("brand_words", []) if b.lower() in low]
    if brands:
        issues.append(f"Eigene Firma genannt ({', '.join(brands)}), kein Pitch")
    if _DU.search(text or "") and not _DU.search(post_text or ""):
        issues.append("Der Autor duzt nicht: neutral schreiben, ohne du")
    for sentence in re.split(r"(?<=[.!?])\s+", (text or "").strip()):
        if _SIE & {w.strip(".,!?:;") for w in sentence.split()[1:]}:
            issues.append("Nie Sie-Anrede")
            break
    post_words = {w.lower() for w in re.findall(r"\w{6,}", post_text or "")}
    if not post_words & {w.lower() for w in re.findall(r"\w{6,}", text or "")}:
        issues.append("Kein konkretes Detail aus dem Post aufgegriffen")
    templates = [m.group(0) for p in TEMPLATE_PATTERNS for m in [p.search(text or "")] if m]
    if templates:
        issues.append(f"Schablonensatz umschreiben: {', '.join(templates)}")
    generic = sorted(set(GENERIC_EMOJI) & set(text or ""))
    if generic:
        issues.append(f"Themen-Emoji {' '.join(generic)} ersetzen durch eines, das Stimmung traegt")
    return issues


# Richard 23.09.2026: 27 ABM-Entwuerfe "blutleer, klingt nach KI". Gemessen, nicht
# nur verboten: Schablonen aus den Typ-Beschreibungen, Aphorismen ueber "die
# meisten", Themen-Emoji als Deko.
TEMPLATE_PATTERNS = [re.compile(p, re.I) for p in (
    r"\b(stimmt|gilt|funktioniert|hilft)\b[^.!?]{0,40}\b(bis|solange)\b",
    r"\b(holds|works|stands)\b[^.!?]{0,40}\b(as long as|until)\b",
    r"\bdie meisten\b", r"\bmost (teams|people|companies|sales teams)\b",
    r"\bkein [\w-]+-?problem\b[^.!?]{0,30}\b(sondern|das ist)\b",
    r"\bnot an? [\w-]+ problem\b", r"\banders gelesen\b",
    r"\bdas ist (der|genau der) (moment|schritt|punkt)\b",
    r"\btrifft es (gut|genau|auf den punkt)\b", r"\b(spot on|nails it)\b",
)]
GENERIC_EMOJI = "🔍💡🔄🧠🧭📋📉🎯🗺"

VALUE_GATE_PROMPT = """Ein LinkedIn-Post und ein Kommentar darunter.

POST
---
{post_text}
---

KOMMENTAR
---
{comment}
---

Enthaelt der Kommentar einen konkreten Gedanken, der im Post fehlt und den der
Autor nicht selbst geschrieben haette? Zaehlt: ein Test oder Handgriff, den ein
Leser anwenden kann; eine konkrete Szene mit Rolle und Handlung; eine andere
Antwort auf die Frage des Autors. Zaehlt nicht: Zustimmung, allgemeine Weisheit,
Aphorismus, der Post oder seine Schlussfrage in anderen Worten.
Erste Zeile nur JA oder NEIN. Zweite Zeile ein Satz Begruendung."""


def value_gate(comment: str, post_text: str) -> str | None:
    """Leser-Gate nach der Generierung: None bei JA, sonst der Befund.
    Unlesbares Urteil zaehlt als NEIN (fail-closed)."""
    resp = _llm.messages.create(model=COMMENT_MODEL, max_tokens=150, messages=[{
        "role": "user",
        "content": VALUE_GATE_PROMPT.format(post_text=post_text[:4000], comment=comment)}])
    lines = resp.content[0].text.strip().splitlines() or [""]
    if lines[0].strip().upper().startswith("JA"):
        return None
    reason = " ".join(l.strip() for l in lines[1:]).strip() or "kein Urteil"
    return f"Kein eigener Mehrwert gegenueber dem Post: {reason}"

# Verstaendlichkeit (Richard 15.09.2026, Kommentar Truempi "zu kompliziert"):
# Satzlaenge und Emoji werden gemessen statt nur verlangt. Ein Nachversuch mit
# den Verstoessen als Hinweis, danach faellt der Entwurf weg.
MAX_SENTENCE_WORDS = 20
_RETRY_NOTE = ("\n\nDEIN LETZTER ENTWURF VERLETZT HARTE REGELN:\n{issues}\n"
               "Schreibe den Kommentar neu und halte alle harten Regeln ein.")


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
    by_url = {p["linkedin_url"]: p["name"] for p in profiles}
    if not by_url:
        return []
    max_age = settings.get("max_age_hours", 30)
    client = apify_client()
    run = client.actor("harvestapi/linkedin-profile-posts").call(run_input={
        "targetUrls": list(by_url),
        "maxPosts": settings.get("max_posts_per_profile", 2),
        # Exaktes Datum statt Enum postedLimit: "week" holt 168h, gefiltert wird auf
        # max_age_hours, und jeder gelieferte Post kostet 0,002 USD.
        "postedLimitDate": window_start_for(max_age),
        "includeReposts": False,
        "scrapeReactions": False,
        "scrapeComments": False,
    })
    if run is None:
        return []

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


def _split_header(raw: str) -> tuple[str, str, str]:
    """Kopfzeilen TYP und ANSATZ (beliebige Reihenfolge, beide optional) vom
    Kommentartext trennen. Fehlen sie, ist alles Kommentar."""
    typ, angle, lines = "", "", raw.strip().splitlines()
    while lines and lines[0].strip().upper().startswith(("TYP:", "ANSATZ:")):
        key, _, val = lines.pop(0).strip().partition(":")
        if key.strip().upper() == "TYP":
            typ = val.strip()
        else:
            angle = val.strip()
    return typ, angle, "\n".join(lines).strip()


def long_sentences(text: str, max_words: int = MAX_SENTENCE_WORDS) -> list[str]:
    """Saetze mit mehr als max_words Woertern (Satzende . ! ?)."""
    sentences = re.split(r"(?<=[.!?])\s+", (text or "").strip())
    return [s for s in sentences if len(s.split()) > max_words]


# Emoji je Mandant (cfg.COMMENT_EMOJI): Richard 15.09.2026 will in jedem seiner
# Kommentare genau ein passendes Emoji; lisocon und SWOT bleiben ohne.
_EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐⭕⌚-⏿]")
EMOJI_ON = ("Genau ein Emoji, das zum Inhalt passt, am Ende eines Satzes oder am Schluss, "
            "kein Emoji als erstes Zeichen. Wähle es nach dem Inhalt des Kommentars, nicht "
            "aus Gewohnheit (nicht standardmäßig 🎯). Das Emoji trägt Stimmung wie "
            "Augenzwinkern oder Seufzen, kein Themen-Symbol wie 🔍 💡 🔄 🧠.")
EMOJI_OFF = "Keine Emojis, kein Emoji als erstes Zeichen."


def emoji_count(text: str) -> int:
    return len(_EMOJI.findall(text or ""))


def comment_issues(text: str, emoji: bool = False) -> list[str]:
    """Messbare Verstoesse gegen die harten Regeln, als Hinweis fuer den Nachversuch."""
    issues = [f"Satz mit mehr als {MAX_SENTENCE_WORDS} Woertern: {s}" for s in long_sentences(text)]
    if re.search(r"—|\s–\s", text or ""):
        issues.append("Gedankenstrich als Satzzeichen, ersetze ihn durch Punkt oder Komma")
    if emoji and emoji_count(text) != 1:
        issues.append(f"Genau ein passendes Emoji noetig, gefunden: {emoji_count(text)}")
    elif emoji and _EMOJI.match(text.strip()):
        issues.append("Das Emoji steht am Anfang, es gehoert ans Satzende oder an den Schluss")
    return issues


def draft_comment(cfg, post: dict, poster: str,
                  avoid_types: list[str] | None = None) -> dict | None:
    """Ein LLM-Call pro Kommentar, ein zweiter nur bei messbaren Verstoessen
    (comment_issues, style_issues). Rueckgabe None bei leerer Antwort oder wenn
    auch der Nachversuch Verstoesse hat.
    avoid_types: Kommentar-Typen, die dieser Lauf schon vergeben hat (die
    Callsite reicht den letzten durch, damit keine Serie entsteht)."""
    style = getattr(cfg, "COMMENT_STYLE", None)
    if style:
        lo, hi = style.get("words", (30, 40))
        # Livetest 15.09.: ohne Zielwert landeten die Entwuerfe am Deckel oder darueber
        length_rule = f"{lo} bis {hi} Woerter insgesamt, Ziel etwa {(lo + hi) // 2}, 2 bis 4 Saetze."
        style_rules = STYLE_RULES.format(
            brand=" oder ".join(style.get("brand_words", [])) or "die eigene Firma",
            humor=HUMOR_ON if style.get("humor") and post.get("ernst") is False else HUMOR_OFF)
    else:
        length_rule, style_rules = LENGTH_RULE_DEFAULT, ""
    prompt = COMMENT_PROMPT.format(
        voice=_voice(cfg, poster),
        context=cfg.CONTEXT.strip(),
        influencer=post.get("influencer", "der Autor"),
        post_text=post["post_text"][:4000],
        types=_types_block((style or {}).get("banned_types", ())),
        avoid=_AVOID_NOTE.format(types=", ".join(avoid_types)) if avoid_types else "",
        length_rule=length_rule,
        style_rules=style_rules,
        max_words=MAX_SENTENCE_WORDS,
        emoji_rule=EMOJI_ON if getattr(cfg, "COMMENT_EMOJI", False) else EMOJI_OFF,
    )
    # Richard 23.09.2026: ein Nachversuch warf 9 von 17 Entwuerfen an Formregeln weg
    for attempt in range(1 + (style or {}).get("retries", 1)):
        resp = _llm.messages.create(model=COMMENT_MODEL, max_tokens=600,
                                    messages=[{"role": "user", "content": prompt}])
        typ, angle, comment = _split_header(resp.content[0].text)
        if not comment:
            return None
        issues = comment_issues(comment, emoji=getattr(cfg, "COMMENT_EMOJI", False))
        if style:
            issues += style_issues(comment, post["post_text"], style)
        # Mehrwert-Urteil nur fuer einen sonst sauberen Entwurf, spart den Call
        if style and style.get("value_gate") and not issues:
            verdict = value_gate(comment, post["post_text"])
            if verdict:
                issues.append(verdict)
        if not issues:
            break
        prompt += _RETRY_NOTE.format(issues="\n".join(f"- {s}" for s in issues))
    else:
        print(f"    Kommentar verworfen ({'; '.join(issues)[:120]}): {post.get('post_url', '')[:60]}",
              file=sys.stderr)
        return None
    label = f"Kommentar {poster} [{typ}]" if typ else f"Kommentar {poster}"
    return {
        "title": f"{label}: {angle or post.get('influencer', '')}"[:250],
        "comment": comment,
        "typ": typ,
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
    written, used_types = 0, []
    for poster, post in assign_posts(posts, posters, per_poster,
                                     total=settings.get("drafts_total")):
        try:
            draft = draft_comment(cfg, post, poster, avoid_types=used_types[-1:])
            if not draft:
                continue
            if draft.get("typ"):
                used_types.append(draft["typ"])
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
