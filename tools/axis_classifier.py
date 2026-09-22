"""Themenachse je Post, ein Haiku-Call pro Post.

Nur fuer jolly. Zwei Sperren, beide gemessen noetig (Richard, 22.09.2026):
1. Feature-Flag `axis_classifier` existiert nur in clients/jolly/config.py.
   Fehlt es, ist der Aufruf ein No-Op -- kein stiller Fallback.
2. Direkter Aufruf mit einem anderen Mandanten scheitert hart. SWOT traegt
   seine Achse im source-String und wird von tools/monthly_plan.py gelesen;
   ein fremder Klassifizierer wuerde dort eine zweite Wahrheit anlegen.

'Passt in keine Achse' ist ein Ergebnis, nicht ein Fehlschlag: es wird als
axis=null mit Zeitstempel festgeschrieben und nie neu berechnet.
"""
import json
import sys

from clients import load_client
from tools.anthropic_auth import LazyAnthropic
from tools.supabase_db import set_axis

client = LazyAnthropic()

AXES = (
    "outbound_maschine",
    "daten_und_revops",
    "positionierung_und_angebot",
    "sales_prozess",
    "team_und_enablement",
    "inbound_und_content",
    "bestand_und_expansion",
    "ki_im_gtm",
)

PROMPT = """Ordne diesen LinkedIn-Post genau einer GTM-Themenachse zu.

Achsen:
- outbound_maschine: Sequenzen, Kanalmix, Deliverability, Listen, Trigger
- daten_und_revops: CRM-Hygiene, Forecast, Reporting, Stage-Definition
- positionierung_und_angebot: ICP, Offer-Design, Preis, Differenzierung, Messaging
- sales_prozess: Qualifizierung, Discovery, Buying Committee, Einwaende, Verhandlung, Closing
- team_und_enablement: erster Sales-Hire, Onboarding, Playbook, Training, Hiring
- inbound_und_content: LinkedIn-System, Content-Ops, SEO und AEO, Webinare, Lead Magnets
- bestand_und_expansion: Kunden-Onboarding, Retention, Account Management, Upsell
- ki_im_gtm: AI SDR, Agenten, Recherche-Automatisierung, GTM Engineering

Passt der Post in keine dieser Achsen, antworte mit null. Raten ist falsch:
ein Post ueber Recruiting, Persoenliches oder ein fremdes Fachgebiet ist null.

Post:
{post_text}

Antworte NUR mit JSON: {{"axis": "<achse>"}} oder {{"axis": null}}
"""


def _guard(cfg) -> bool:
    """True heisst laufen. False heisst No-Op. Fremder Mandant heisst Abbruch."""
    if cfg.NAME != "jolly":
        raise SystemExit(
            f"Abbruch: der Achsen-Klassifizierer gilt nur fuer jolly, "
            f"aufgerufen mit '{cfg.NAME}'. SWOT traegt die Achse im "
            f"source-String (tools/monthly_plan.py), lisocon hat kein "
            f"Topic-Mining. Kein stiller Fallback."
        )
    return bool(cfg.FEATURES.get("axis_classifier"))


def classify_post(post_text: str) -> str | None:
    """Eine Achse oder None. Jeder Fehler ist None: eine falsche Achse ist
    teurer als keine, weil der Deckel danach am falschen Wert sperrt."""
    text = (post_text or "").strip()
    if len(text) < 80:
        return None
    try:
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=64,
            messages=[{"role": "user", "content": PROMPT.format(post_text=text[:4000])}],
        )
        raw = resp.content[0].text.strip()
        start, end = raw.find("{"), raw.rfind("}")
        achse = json.loads(raw[start:end + 1]).get("axis")
    except Exception as e:
        print(f"  Achsen-Call fehlgeschlagen: {e}", file=sys.stderr)
        return None
    return achse if achse in AXES else None


def classify_rows(rows: list, cfg=None) -> dict:
    """Klassifiziert die uebergebenen Zeilen und schreibt jede Entscheidung
    zurueck. Gibt {achse: anzahl} zurueck, 'null' fuer 'passt in keine'."""
    cfg = cfg or load_client()
    if not _guard(cfg):
        return {}
    zaehler = {}
    for row in rows:
        url = row.get("post_url")
        if not url:
            continue
        achse = classify_post(row.get("post_text", ""))
        set_axis(url, achse)
        key = achse or "null"
        zaehler[key] = zaehler.get(key, 0) + 1
    return zaehler
