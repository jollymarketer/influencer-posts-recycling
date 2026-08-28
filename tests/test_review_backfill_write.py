"""Schreibpfad der Bestandsbereinigung (run_review_backfill.write). Kein Netz,
kein Modell: Notion-Calls, Entscheidung je Zeile und Nachfuellen sind gemockt.
Der Pfad hatte bis zum Abschluss-Review 28.08.2026 keinen einzigen Test,
obwohl er als einziger kundensichtbare Texte leert."""
import json
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import run_review_backfill as rrb
from tools import post_scorer as ps


def _row(page_id="p1", titel="T", text="Ein Text."):
    return {"id": page_id, "properties": {
        "Titel": {"title": [{"plain_text": titel}]},
        "Kanal": {"select": {"name": "LinkedIn Robert"}},
        "Status": {"select": {"name": "Entwurf"}},
        "Typ": {"select": {"name": "LinkedIn-Post"}},
        "Post-Text": {"rich_text": [{"plain_text": text}]},
        "Kurzbeschreibung": {"rich_text": [{"plain_text": "K"}]},
        "Geplant für": {"date": {"start": "2026-09-10"}},
    }}


def _cfg():
    return type("Cfg", (), {"CONTENT_PLAN_DB_ID": "db", "CTA_DE": "",
                            "ACCOUNT_VOICES": {"LinkedIn Robert": "Stimme"}})()


def _entscheidung(aktion, text_neu, page_id="p1"):
    return {"page_id": page_id, "titel": "T", "kanal": "LinkedIn Robert",
            "datum": "2026-09-10", "aktion": aktion, "text_neu": text_neu, "grund": ""}


class _Resp:
    """Minimale requests-Antwort fuer PATCH und GET."""

    def __init__(self, payload=None):
        self.ok = True
        self.status_code = 200
        self.text = ""
        self._payload = payload or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        pass


def _notion_double(readback):
    """PATCH sammelt die geschriebenen rich_text-Bloecke, GET liest zurueck,
    was readback(zuletzt geschriebener Block) liefert."""
    geschrieben = []

    def fake_patch(url, headers=None, json=None, timeout=None):
        geschrieben.append(json["properties"]["Post-Text"]["rich_text"])
        return _Resp()

    def fake_get(url, headers=None, timeout=None):
        ist = readback(geschrieben[-1])
        return _Resp({"properties": {"Post-Text": {"rich_text": [{"plain_text": ist}]}}})

    return fake_patch, fake_get, geschrieben


def _protokoll(tmp_path):
    pfad = next(tmp_path.glob("*_bestand-write.json"))
    return json.loads(pfad.read_text(encoding="utf-8"))


def test_repaired_row_with_diverging_readback_is_cleared(tmp_path):
    # Zweimal abweichender Readback: der reparierte Text steht nicht sicher in
    # Notion, also wird die Zeile geleert statt halb geschrieben zu bleiben.
    fake_patch, fake_get, geschrieben = _notion_double(
        lambda block: "" if not block else "Etwas ganz anderes.")
    with patch.object(rrb, "read_plan", return_value=[_row()]), \
         patch.object(rrb.rb, "decide_row", return_value=_entscheidung("repariert", "Repariert.")), \
         patch.object(rrb, "notion_headers", return_value={}), \
         patch.object(rrb, "text_fill") as nachfuellen, \
         patch("run_review_backfill.requests") as req, \
         patch("run_review_backfill.time.sleep"):
        req.patch.side_effect = fake_patch
        req.get.side_effect = fake_get
        r = rrb.write(str(tmp_path), _cfg(), refill_passes=1)
    assert r["geleert"] == 1 and r["repariert"] == 0 and r["fehler"] == 0
    assert geschrieben[-1] == []
    zeilen = _protokoll(tmp_path)["zeilen"]
    assert [z["aktion"] for z in zeilen] == ["geleert"]
    assert zeilen[0]["grund"] == "Readback-Abweichung, geleert"
    assert nachfuellen.called is True


def test_exception_in_one_row_counts_fehler_and_continues(tmp_path):
    # Leser-Ausfall in Zeile 1: als fehler gezaehlt, Zeile unangetastet, der
    # Lauf geht weiter, und beide Zeilen stehen im Protokoll auf der Platte.
    def decide(row, cfg, loop_fn):
        if row["page_id"] == "p1":
            raise ps.ReaderUnavailable("API weg")
        return _entscheidung("unveraendert", "Ein Text.", page_id="p2")

    fake_patch, fake_get, geschrieben = _notion_double(lambda block: "")
    with patch.object(rrb, "read_plan", return_value=[_row("p1"), _row("p2")]), \
         patch.object(rrb.rb, "decide_row", side_effect=decide), \
         patch.object(rrb, "notion_headers", return_value={}), \
         patch.object(rrb, "text_fill"), \
         patch("run_review_backfill.requests") as req, \
         patch("run_review_backfill.time.sleep"):
        req.patch.side_effect = fake_patch
        req.get.side_effect = fake_get
        r = rrb.write(str(tmp_path), _cfg(), refill_passes=0)
    assert r["fehler"] == 1 and r["unveraendert"] == 1
    assert geschrieben == []
    zeilen = _protokoll(tmp_path)["zeilen"]
    assert [z["page_id"] for z in zeilen] == ["p1", "p2"]
    assert zeilen[0]["aktion"] == "fehler" and "API weg" in zeilen[0]["grund"]


def test_refill_passes_zero_never_refills(tmp_path):
    # Default seit 28.08.2026: Nachfuellen kostet Modell-Budget und braucht
    # eine eigene Freigabe, auch wenn dieser Lauf Zeilen geleert hat.
    fake_patch, fake_get, _ = _notion_double(lambda block: "")
    with patch.object(rrb, "read_plan", return_value=[_row()]), \
         patch.object(rrb.rb, "decide_row", return_value=_entscheidung("geleert", "")), \
         patch.object(rrb, "notion_headers", return_value={}), \
         patch.object(rrb, "text_fill") as nachfuellen, \
         patch("run_review_backfill.requests") as req, \
         patch("run_review_backfill.time.sleep"):
        req.patch.side_effect = fake_patch
        req.get.side_effect = fake_get
        r = rrb.write(str(tmp_path), _cfg(), refill_passes=0)
    assert r["geleert"] == 1
    assert nachfuellen.called is False
