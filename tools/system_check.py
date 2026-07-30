"""Phase 0: GO/NO-GO-Check vor jedem Pipeline-Lauf.

Warum: Fehlt einer Abhaengigkeit die Env-Variable oder ist ein Token tot,
beendet sich der Cron trotzdem mit Exit 0 und Railway meldet SUCCESS - der
Lauf hat aber nichts getan. Der Check prueft jede Abhaengigkeit, BEVOR die
Pipeline startet, und bricht bei harten Fehlern laut ab (Exit 1).

Nur lesende, kostenlose Aufrufe. Insbesondere NICHT: Apify-Actor starten
(kostet), kie.ai-Task anlegen (kostet), Make-Webhook feuern (loest eine
echte Mail aus).

Direkt aufrufbar:  python tools/system_check.py        (Exit 1 bei NO-GO)
                   CLIENT=lisocon python tools/system_check.py
"""
import os
import sys

import requests
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from clients import load_client

load_dotenv()

TIMEOUT = 20

HARD = "hard"
SOFT = "soft"

# Properties, die der Code in die Notion-DB schreibt. Fehlt eine, schlaegt der
# Write zur Laufzeit fehl - meist erst nach Scrape, Scoring und Bildgenerierung.
CORE_NOTION_PROPS = (
    "Status", "LinkedIn Post URL", "LinkedIn Draft", "Image Prompt", "Image",
    "Influencer", "Post Excerpt", "Date Scraped", "Format", "Infografik-Typ",
    "Bild-Variante", "Matrix-Job", "Matrix-Stage", "Persona", "Asset",
)
EN_NOTION_PROPS = ("LinkedIn Draft EN",)
SLATE_NOTION_PROPS = ("Score", "Themen-Winkel", "VoC-Treffer", "Matrix-Prio", "Poster")
READBACK_NOTION_PROPS = ("Likes", "Kommentare", "Shares", "Engagement-Stand",
                         "Date Posted", "Poster",
                         "Posted URL (Reinhard)", "Posted URL (Jae)")
COMMENT_NOTION_PROPS = ("Kommentar-Ziel", "Poster")

APIFY_ACTORS = ("harvestapi~linkedin-profile-posts",)
APIFY_KEYWORD_ACTOR = "harvestapi~linkedin-post-search"


def _result(name: str, ok: bool, severity: str, detail: str) -> dict:
    return {"name": name, "ok": ok, "severity": severity, "detail": detail}


# --- Pure Logik (testbar ohne Netz) -----------------------------------------

def required_notion_props(cfg) -> tuple:
    """Property-Namen, die dieser Mandant wirklich braucht. Faehigkeiten, die
    der Mandant nicht fahrt, werden nicht eingefordert - sonst meldet der
    Check Luecken, die niemanden stoeren."""
    props = list(CORE_NOTION_PROPS)
    features = getattr(cfg, "FEATURES", None) or {}
    if features.get("en_draft", True):
        props += list(EN_NOTION_PROPS)
    if features.get("slate_mode"):
        props += list(SLATE_NOTION_PROPS)
    if getattr(cfg, "ENGAGEMENT_READBACK", None):
        props += list(READBACK_NOTION_PROPS)
    if getattr(cfg, "COMMENT_DRAFTS", None):
        props += list(COMMENT_NOTION_PROPS)
    return tuple(dict.fromkeys(props))


def uses_supabase(cfg) -> bool:
    """Supabase haengt nicht nur an `supabase_persist`. Der Slate-Modus haelt
    Kandidaten-Pool und Tages-Guard dort (tools/topic_pool.py) und bricht ohne
    Pool ab. lisocon faehrt supabase_persist=False und trotzdem den Pool: ohne
    diese Weiche blieb ausgerechnet die Abhaengigkeit ungeprueft, deren Ausfall
    den Slate garantiert still verschluckt."""
    features = getattr(cfg, "FEATURES", None) or {}
    return bool(features.get("supabase_persist") or features.get("slate_mode"))


def supabase_table(cfg) -> str:
    """Die Tabelle, die dieser Mandant wirklich liest - eine erreichbare
    Fremdtabelle beweist fuer den Slate-Pfad nichts."""
    features = getattr(cfg, "FEATURES", None) or {}
    return "topic_candidates" if features.get("slate_mode") else "influencer_posts"


def required_env(cfg) -> list:
    """(Env-Name, Severity)-Paare fuer diesen Mandanten."""
    features = getattr(cfg, "FEATURES", None) or {}
    env = [
        (getattr(cfg, "NOTION_TOKEN_ENV", "NOTION_TOKEN"), HARD),
        ("ANTHROPIC_API_KEY", HARD),
        ("APIFY_API_KEY", HARD),
        ("KIEAI_API_KEY", SOFT),
        (getattr(cfg, "MAKE_WEBHOOK_ENV", "MAKE_REVIEW_WEBHOOK"), SOFT),
    ]
    if features.get("slate_mode"):
        env.append(("MAKE_SLATE_WEBHOOK", SOFT))
    if uses_supabase(cfg):
        # Im Slate-Modus ist eine fehlende Supabase-Env ein harter Fehler: ohne
        # Pool bricht phase_slate ab und der Lauf tut nichts. Beim Jolly-Mining
        # ist Supabase eine Nebenwirkung und bleibt weich.
        severity = HARD if features.get("slate_mode") else SOFT
        env += [("SUPABASE_URL", severity), ("SUPABASE_SERVICE_KEY", severity)]
    return env


def evaluate(results: list) -> tuple:
    """(go, zeilen) - go ist False, sobald ein harter Check fehlschlaegt."""
    go = all(r["ok"] for r in results if r["severity"] == HARD)
    lines = []
    for r in results:
        mark = "OK  " if r["ok"] else ("FAIL" if r["severity"] == HARD else "WARN")
        lines.append(f"  [{mark}] {r['name']}: {r['detail']}")
    hard_fails = [r["name"] for r in results if not r["ok"] and r["severity"] == HARD]
    lines.append(f"  ==> {'GO' if go else 'NO-GO'}"
                 + (f" (harte Fehler: {', '.join(hard_fails)})" if hard_fails else ""))
    return go, lines


# --- Checks mit Netz ---------------------------------------------------------

def check_env(cfg) -> list:
    out = []
    for name, severity in required_env(cfg):
        # Der Notion-Token faellt auf NOTION_TOKEN zurueck (siehe notion_db).
        value = os.getenv(name) or (os.getenv("NOTION_TOKEN") if "NOTION_TOKEN" in name else "")
        out.append(_result(f"env:{name}", bool(value), severity,
                           "gesetzt" if value else "FEHLT"))
    db_id = os.getenv("NOTION_DB_ID") or getattr(cfg, "NOTION_DB_ID_DEFAULT", None)
    out.append(_result("env:NOTION_DB_ID", bool(db_id), HARD,
                       db_id or "FEHLT (weder Env noch Client-Default)"))
    return out


def check_notion(cfg) -> list:
    token = os.getenv(getattr(cfg, "NOTION_TOKEN_ENV", "NOTION_TOKEN")) or os.getenv("NOTION_TOKEN")
    db_id = os.getenv("NOTION_DB_ID") or getattr(cfg, "NOTION_DB_ID_DEFAULT", None)
    if not token or not db_id:
        return [_result("notion", False, HARD, "Token oder DB-ID fehlt - Check uebersprungen")]
    try:
        resp = requests.get(
            f"https://api.notion.com/v1/databases/{db_id}",
            headers={"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28"},
            timeout=TIMEOUT)
    except requests.RequestException as e:
        return [_result("notion", False, HARD, f"nicht erreichbar: {e}")]
    if resp.status_code != 200:
        return [_result("notion", False, HARD,
                        f"HTTP {resp.status_code} auf DB {db_id} ({resp.text[:120]})")]
    present = set(resp.json().get("properties", {}))
    missing = [p for p in required_notion_props(cfg) if p not in present]
    return [
        _result("notion:db", True, HARD, f"erreichbar ({len(present)} Properties)"),
        _result("notion:properties", not missing, HARD,
                "vollstaendig" if not missing else f"fehlen: {', '.join(missing)}"),
    ]


def check_apify(cfg) -> list:
    token = os.getenv("APIFY_API_KEY")
    if not token:
        return [_result("apify", False, HARD, "APIFY_API_KEY fehlt - Check uebersprungen")]
    out = []
    try:
        resp = requests.get("https://api.apify.com/v2/users/me",
                            headers={"Authorization": f"Bearer {token}"}, timeout=TIMEOUT)
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            out.append(_result("apify:token", True, HARD,
                               f"gueltig (User {data.get('username', '?')})"))
        else:
            out.append(_result("apify:token", False, HARD, f"HTTP {resp.status_code}"))
            return out
    except requests.RequestException as e:
        return [_result("apify:token", False, HARD, f"nicht erreichbar: {e}")]

    actors = list(APIFY_ACTORS)
    if (getattr(cfg, "FEATURES", None) or {}).get("keyword_source_daily"):
        actors.append(APIFY_KEYWORD_ACTOR)
    for actor in actors:
        try:
            r = requests.get(f"https://api.apify.com/v2/acts/{actor}",
                             headers={"Authorization": f"Bearer {token}"}, timeout=TIMEOUT)
            out.append(_result(f"apify:{actor}", r.status_code == 200, HARD,
                               "verfuegbar" if r.status_code == 200 else f"HTTP {r.status_code}"))
        except requests.RequestException as e:
            out.append(_result(f"apify:{actor}", False, HARD, f"nicht erreichbar: {e}"))
    return out


def check_anthropic(cfg) -> list:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return [_result("anthropic", False, HARD, "ANTHROPIC_API_KEY fehlt - Check uebersprungen")]
    model = getattr(cfg, "SCORING_MODEL", "claude-haiku-4-5-20251001")
    try:
        resp = requests.get(f"https://api.anthropic.com/v1/models/{model}",
                            headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
                            timeout=TIMEOUT)
    except requests.RequestException as e:
        return [_result("anthropic", False, HARD, f"nicht erreichbar: {e}")]
    if resp.status_code == 200:
        return [_result("anthropic", True, HARD, f"Key gueltig, Modell {model} verfuegbar")]
    return [_result("anthropic", False, HARD,
                    f"HTTP {resp.status_code} fuer Modell {model} ({resp.text[:120]})")]


def check_kieai(cfg) -> list:
    """Bildgenerierung ist in der Pipeline non-fatal, daher SOFT. Ein nicht
    eindeutiges Ergebnis (Netzfehler, unerwarteter Status) wird als 'unbekannt'
    gemeldet und nie als Ablehnung - ein Fehlversuch ist keine Messung."""
    key = os.getenv("KIEAI_API_KEY")
    if not key:
        return [_result("kieai", False, SOFT, "KIEAI_API_KEY fehlt - Posts entstehen ohne Bild")]
    try:
        resp = requests.get("https://api.kie.ai/api/v1/chat/credit",
                            headers={"Authorization": f"Bearer {key}"}, timeout=TIMEOUT)
    except requests.RequestException as e:
        return [_result("kieai", True, SOFT, f"unbekannt (nicht erreichbar: {e})")]
    if resp.status_code in (401, 403):
        return [_result("kieai", False, SOFT, f"Key abgelehnt (HTTP {resp.status_code})")]
    if resp.status_code != 200:
        return [_result("kieai", True, SOFT, f"unbekannt (HTTP {resp.status_code})")]
    body = resp.json()
    credits = body.get("data")
    if isinstance(credits, (int, float)):
        return [_result("kieai", credits > 0, SOFT, f"{credits:g} Credits")]
    return [_result("kieai", True, SOFT, f"unbekannt (Antwort {str(body)[:80]})")]


def check_supabase(cfg) -> list:
    """Fehlende Env meldet bereits check_env mit der richtigen Haerte. Die
    Erreichbarkeit bleibt hier bewusst SOFT: ein Netzfehler ist ein
    Fehlversuch, keine Messung, und darf den Lauf nicht abwerten."""
    if not uses_supabase(cfg):
        return []
    url, key = os.getenv("SUPABASE_URL", ""), os.getenv("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        return [_result("supabase", False, SOFT, "URL oder Service-Key fehlt")]
    table = supabase_table(cfg)
    try:
        resp = requests.get(f"{url.rstrip('/')}/rest/v1/{table}",
                            headers={"apikey": key, "Authorization": f"Bearer {key}",
                                     "Accept-Profile": "blog_content_mining"},
                            params={"select": "post_url", "limit": 1}, timeout=TIMEOUT)
    except requests.RequestException as e:
        return [_result(f"supabase:{table}", True, SOFT,
                        f"unbekannt (nicht erreichbar: {e})")]
    return [_result(f"supabase:{table}", resp.status_code == 200, SOFT,
                    "Tabelle lesbar" if resp.status_code == 200
                    else f"HTTP {resp.status_code} ({resp.text[:100]})")]


def collect(cfg) -> list:
    results = []
    results += check_env(cfg)
    results += check_notion(cfg)
    results += check_apify(cfg)
    results += check_anthropic(cfg)
    results += check_kieai(cfg)
    results += check_supabase(cfg)
    return results


def run_system_check(cfg=None, strict: bool = True) -> bool:
    """Phase 0. Gibt GO/NO-GO zurueck. strict=True (Default im Cron): bei
    NO-GO wirft der Aufrufer ab - lieber kein Lauf als ein halber."""
    cfg = cfg or load_client()
    print(f"\nPhase 0: System-Check (Client: {cfg.NAME}) ...")
    results = collect(cfg)
    go, lines = evaluate(results)
    for line in lines:
        print(line, file=sys.stderr if not go else sys.stdout)
    return go


if __name__ == "__main__":
    sys.exit(0 if run_system_check() else 1)
