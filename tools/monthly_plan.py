"""Monatsplan: baut aus der Themen-DB einen Monatsraster-Vorschlag fuer den
Content-Redaktionsplan (Entscheidung Richard 19.08.2026).

Ablauf: Slots aus POSTING_SCHEDULE bauen, Themen aus der Themen-DB lesen, je
Thema die Content-Achse klassifizieren (ein Batch-Call, Ergebnis wird in die
Themen-DB zurueckgeschrieben und beim naechsten Lauf wiederverwendet),
Fristen-Slots aus FRISTEN_KALENDER setzen, Rest deterministisch nach AXIS_MIX
fuellen. Geschrieben wird ausschliesslich Status "Themenvorschlag" — die
kundensichtbare Freigabe-Galerie filtert auf "Zur Freigabe" und zeigt
Vorschlaege nicht. Der Wechsel auf "Zur Freigabe" bleibt ein Handschritt nach
Richards Review.

Die Auswahl selbst ist reiner Code ohne Modellaufruf, damit sie testbar und
wiederholbar ist. Das Modell klassifiziert nur die Achse je Thema.
"""
import calendar
import json
import os
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

import anthropic
import requests
from dotenv import load_dotenv

from clients import load_client
from tools.topic_ideas_db import _db_id as topic_db_id, _headers as notion_headers

load_dotenv()

_cfg = load_client()

NOTION_API = "https://api.notion.com/v1"
TIMEOUT = 30
CLASSIFY_MODEL = getattr(_cfg, "SCORING_MODEL", "claude-haiku-4-5-20251001")

AXES = [p["id"] for p in _cfg.CONTENT_PERSONAS]
AXIS_LABEL = {p["id"]: p["label"] for p in _cfg.CONTENT_PERSONAS}


@dataclass
class Slot:
    day: date
    account: str
    kanal: str
    axis: str | None = None
    topic: dict | None = None
    frist: dict | None = None


@dataclass
class Topic:
    page_id: str
    title: str
    title_de: str
    keyword_de: str
    score: int
    axis: str | None = None
    evidence: str = ""
    raw: dict = field(default_factory=dict)


# --- Slot-Raster --------------------------------------------------------------

def build_slots(year: int, month: int) -> list[Slot]:
    """Alle Beitrags-Slots des Monats aus POSTING_SCHEDULE, chronologisch."""
    slots = []
    _, last = calendar.monthrange(year, month)
    for d in range(1, last + 1):
        day = date(year, month, d)
        for account, spec in _cfg.POSTING_SCHEDULE.items():
            if day.weekday() in spec["weekdays"]:
                slots.append(Slot(day=day, account=account, kanal=spec["kanal"]))
    return slots


# --- Fristen ------------------------------------------------------------------

def active_fristen(today: date, horizon_days: int) -> list[dict]:
    """Fristen, deren Termin binnen horizon_days liegt oder hoechstens 30 Tage
    zurueck (Rueckblick-Beitrag)."""
    out = []
    for f in _cfg.FRISTEN_KALENDER:
        deadline = date.fromisoformat(f["deadline"])
        if today - timedelta(days=30) < deadline <= today + timedelta(days=horizon_days):
            out.append({**f, "deadline_date": deadline})
    return out


# --- Auswahl (rein deterministisch, testbar) ----------------------------------

def select(slots: list[Slot], topics: list[Topic], fristen: list[dict],
           mix: dict, axis_to_account: dict) -> list[Slot]:
    """Fuellt die Slots. Reihenfolge der Regeln:
    1. Jede aktive Frist bekommt einen Slot auf einem Fristen-Konto.
    2. Jede Achse mit Themen bekommt min_per_axis Slots.
    3. Rest nach Themen-Score, dominante Achse gedeckelt (max_share).
    Ein Thema wird hoechstens einmal verwendet. Slots ohne passendes Thema
    bleiben leer (ehrlicher als Fuellmaterial)."""
    total = len(slots)
    cap = {ax: int(total * share) for ax, share in mix.get("max_share", {}).items()}
    used_per_axis: dict[str, int] = {ax: 0 for ax in AXES}
    open_slots = list(slots)
    pool = sorted([t for t in topics if t.axis in AXES], key=lambda t: -t.score)

    def take_slot(accounts: list[str]) -> Slot | None:
        for acc in accounts:
            for s in open_slots:
                if s.account == acc and s.topic is None and s.frist is None:
                    return s
        return None

    def assign(topic: Topic) -> bool:
        if topic.axis in cap and used_per_axis[topic.axis] >= cap[topic.axis]:
            return False
        s = take_slot(axis_to_account.get(topic.axis, []))
        if s is None:
            return False
        s.axis, s.topic = topic.axis, topic.__dict__
        used_per_axis[topic.axis] += 1
        pool.remove(topic)
        return True

    # 1. Fristen zuerst: fester Anlass schlaegt Score.
    for f in fristen:
        s = take_slot(axis_to_account.get("fristen", []))
        if s is not None:
            s.axis, s.frist = "fristen", f
            used_per_axis["fristen"] += 1

    # 2. Mindestbelegung je Achse.
    for ax in AXES:
        if ax == "fristen":
            continue
        while used_per_axis[ax] < mix.get("min_per_axis", 0):
            nxt = next((t for t in pool if t.axis == ax), None)
            if nxt is None or not assign(nxt):
                break

    # 3. Rest nach Score.
    for t in list(pool):
        assign(t)

    return slots


# --- Achsen-Klassifikation (ein Batch-Call, Ergebnis persistiert) -------------

_CLASSIFY_PROMPT = """Ordne jedes Thema genau EINER Achse zu. Antworte NUR mit
einem JSON-Objekt {{"<nr>": "<achsen_id>"}} ohne weiteren Text.

Achsen:
{axes}

Themen:
{topics}"""


def classify_axes(topics: list[Topic]) -> list[Topic]:
    """Setzt topic.axis fuer alle Themen ohne Achse. Ein Modellaufruf fuer den
    ganzen Batch. Unbekannte Antworten bleiben None und fallen aus der Auswahl."""
    todo = [t for t in topics if not t.axis]
    if not todo:
        return topics
    axes_block = "\n".join(
        f"- {p['id']}: {p['axis']}" for p in _cfg.CONTENT_PERSONAS
    )
    topics_block = "\n".join(
        f"{i}. {t.title_de or t.title} [Suchbegriff: {t.keyword_de}]"
        for i, t in enumerate(todo)
    )
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    resp = client.messages.create(
        model=CLASSIFY_MODEL, max_tokens=1000,
        messages=[{"role": "user", "content": _CLASSIFY_PROMPT.format(
            axes=axes_block, topics=topics_block)}],
    )
    raw = resp.content[0].text if resp.content else "{}"
    m = re.search(r"\{.*\}", raw, re.S)
    mapping = json.loads(m.group(0)) if m else {}
    for i, t in enumerate(todo):
        ax = mapping.get(str(i))
        if ax in AXES:
            t.axis = ax
    return topics


# --- Themen-DB lesen und Achse zurueckschreiben --------------------------------

def read_topics(statuses=("New", "Hub needed")) -> list[Topic]:
    rows, cursor = [], None
    while True:
        body: dict = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        resp = requests.post(f"{NOTION_API}/databases/{topic_db_id()}/query",
                             headers=notion_headers(), json=body, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        rows += data.get("results", [])
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")

    def _txt(props, key):
        return "".join(x.get("plain_text", "")
                       for x in (props.get(key, {}) or {}).get("rich_text", []))

    topics = []
    for r in rows:
        p = r.get("properties", {})
        status = ((p.get("Status", {}) or {}).get("select") or {}).get("name", "")
        if status not in statuses:
            continue
        title = "".join(x.get("plain_text", "")
                        for x in (p.get("Title", {}) or {}).get("title", []))
        axis = ((p.get("Achse", {}) or {}).get("select") or {}).get("name")
        topics.append(Topic(
            page_id=r["id"], title=title,
            title_de=_txt(p, "Suggested Title DE"),
            keyword_de=_txt(p, "Keyword DE"),
            # Rang seit 20.08.2026 ueber Fundstellen (Cluster Size), nicht mehr
            # ueber den Blog Score. Der war Modellurteil auf Jollys ICP geeicht.
            score=int((p.get("Cluster Size", {}) or {}).get("number") or 0),
            axis=axis if axis in AXES else None,
            evidence=_txt(p, "Evidence Quote"),
        ))
    return topics


def persist_axes(topics: list[Topic]) -> int:
    n = 0
    for t in topics:
        if not t.axis:
            continue
        resp = requests.patch(
            f"{NOTION_API}/pages/{t.page_id}", headers=notion_headers(),
            json={"properties": {"Achse": {"select": {"name": t.axis}}}},
            timeout=TIMEOUT)
        n += 1 if resp.ok else 0
    return n


# --- Redaktionsplan schreiben ---------------------------------------------------

def write_proposals(slots: list[Slot]) -> int:
    """Schreibt gefuellte Slots als Themenvorschlag in den Redaktionsplan.
    NIE einen anderen Status setzen: der Wechsel auf "Zur Freigabe" ist
    Richards Handschritt nach Review."""
    n = 0
    for s in slots:
        if s.topic is None and s.frist is None:
            continue
        if s.frist is not None:
            titel = s.frist["label"]
            kurz = (f"Fristen-Slot aus dem Kalender, Termin "
                    f"{s.frist['deadline']}. Achse: {AXIS_LABEL['fristen']}.")
        else:
            titel = s.topic["title_de"] or s.topic["title"]
            kurz = (f"Maschineller Themenvorschlag, Achse: "
                    f"{AXIS_LABEL[s.axis]}, {s.topic['score']} Fundstellen. "
                    f"Suchbegriff: {s.topic['keyword_de']}.")
            if s.topic.get("evidence"):
                kurz += f' Beleg: "{s.topic["evidence"][:200]}"'
        props = {
            "Titel": {"title": [{"text": {"content": titel[:200]}}]},
            "Status": {"select": {"name": "Themenvorschlag"}},
            "Typ": {"select": {"name": "LinkedIn-Post"}},
            "Kanal": {"select": {"name": s.kanal}},
            "Achse": {"select": {"name": s.axis}},
            "Geplant für": {"date": {"start": s.day.isoformat()}},
            "Kurzbeschreibung": {"rich_text": [{"text": {"content": kurz[:1900]}}]},
        }
        resp = requests.post(f"{NOTION_API}/pages", headers=notion_headers(),
                             json={"parent": {"database_id": _cfg.CONTENT_PLAN_DB_ID},
                                   "properties": props}, timeout=TIMEOUT)
        if resp.ok:
            n += 1
        else:
            print(f"  Notion-Fehler {resp.status_code}: {resp.text[:160]}")
    return n
