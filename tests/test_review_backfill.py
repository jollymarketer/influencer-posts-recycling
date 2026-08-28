"""Bestandsleser: reine Funktionen, kein Netz. Modellaufruf wird injiziert."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import review_backfill as rb

CTA = "30 Minuten mit unseren Planungs- und Konsolidierungsexperten, kostenfrei: https://www.swot.de/demo-buchen/"


def _row(titel="T", kanal="LinkedIn Robert", status="Entwurf", typ="LinkedIn-Post",
         text="Ein Text.", kurz="K", datum="2026-09-10", page_id="p1"):
    return {"id": page_id, "properties": {
        "Titel": {"title": [{"plain_text": titel}]},
        "Kanal": {"select": {"name": kanal}},
        "Status": {"select": {"name": status}},
        "Typ": {"select": {"name": typ}},
        "Post-Text": {"rich_text": [{"plain_text": text}]},
        "Kurzbeschreibung": {"rich_text": [{"plain_text": kurz}]},
        "Geplant für": {"date": {"start": datum}},
    }}


def test_strip_cta_removes_trailing_cta_only():
    assert rb.strip_cta("Body.\n\n" + CTA, CTA) == "Body."
    assert rb.strip_cta("Body.\n\n" + CTA + "\n", CTA) == "Body."
    assert rb.strip_cta("Body ohne CTA.", CTA) == "Body ohne CTA."
    assert rb.strip_cta(CTA + "\n\nBody.", CTA) == CTA + "\n\nBody."


def test_plan_rows_keeps_only_linkedin_entwurf_with_text():
    rows = [
        _row(page_id="ok"),
        _row(page_id="frei", status="Text freigegeben"),
        _row(page_id="blog", typ="Blog"),
        _row(page_id="leer", text=""),
    ]
    out = rb.plan_rows(rows)
    assert [r["page_id"] for r in out] == ["ok"]
    assert out[0] == {"page_id": "ok", "titel": "T", "kanal": "LinkedIn Robert",
                      "datum": "2026-09-10", "kurz": "K", "text": "Ein Text.",
                      "status": "Entwurf"}


def test_material_for_builds_topic_material():
    m = rb.material_for({"titel": "Forecast", "kurz": "Annahmen pruefen"})
    assert m == "Thema: Forecast\nKurzbeschreibung: Annahmen pruefen"


def test_read_row_strips_cta_and_merges_findings():
    row = {"page_id": "p1", "titel": "T", "kanal": "LinkedIn Robert", "datum": "2026-09-10",
           "kurz": "K", "text": "Das ist kein Planungsproblem. Das ist ein Strukturproblem.\n\n" + CTA,
           "status": "Entwurf"}
    seen = {}

    def fake_read(text, material, voice):
        seen["text"] = text
        seen["material"] = material
        seen["voice"] = voice
        return [{"art": "schriftdeutsch", "zitat": "Das ist ein Strukturproblem.",
                 "grund": "g", "vorschlag": "v"}]

    cfg = type("Cfg", (), {"CTA_DE": CTA,
                           "ACCOUNT_VOICES": {"LinkedIn Robert": "Robert Werner Stimme"}})()
    out = rb.read_row(row, cfg, fake_read)
    assert CTA not in seen["text"]
    assert seen["material"].startswith("Thema: T")
    assert seen["voice"] == "Robert Werner Stimme"
    assert out["laenge"] == len(row["text"]) - len(CTA) - 2
    assert [f["art"] for f in out["befunde"]] == ["schriftdeutsch", "schablone"]
    assert out["verdikt"] == "befund"


def test_read_row_verdict_without_findings_and_without_judgement():
    row = {"page_id": "p1", "titel": "T", "kanal": "LinkedIn Robert", "datum": "d",
           "kurz": "K", "text": "Sauberer Text.", "status": "Entwurf"}
    cfg = type("Cfg", (), {"CTA_DE": CTA, "ACCOUNT_VOICES": {"LinkedIn Robert": "x"}})()
    assert rb.read_row(row, cfg, lambda t, m, v: [])["verdikt"] == "sauber"
    assert rb.read_row(row, cfg, lambda t, m, v: None)["verdikt"] == "kein_urteil"


def test_report_markdown_has_one_row_per_post_and_totals():
    results = [
        {"page_id": "p1", "titel": "A", "kanal": "LinkedIn Robert", "datum": "2026-09-10",
         "laenge": 1200, "verdikt": "befund",
         "befunde": [{"art": "schriftdeutsch", "zitat": "Stimmen sie nicht.", "grund": "Verb vorn", "vorschlag": "Tun sie nicht."}]},
        {"page_id": "p2", "titel": "B", "kanal": "LinkedIn Christian", "datum": "2026-09-11",
         "laenge": 900, "verdikt": "sauber", "befunde": []},
    ]
    md = rb.report_markdown(results)
    assert "| 2026-09-10 | LinkedIn Robert | A | 1200 | 1 |" in md
    assert "| 2026-09-11 | LinkedIn Christian | B | 900 | 0 |" in md
    assert "[schriftdeutsch] \"Stimmen sie nicht.\": Verb vorn Vorschlag: Tun sie nicht." in md
    assert "Beitraege: 2, mit Befund: 1, sauber: 1, kein Urteil: 0, Befunde gesamt: 1" in md


def _cfg():
    return type("Cfg", (), {"CTA_DE": CTA, "ACCOUNT_VOICES": {"LinkedIn Robert": "Stimme"}})()


def _row2(text):
    return {"page_id": "p1", "titel": "T", "kanal": "LinkedIn Robert", "datum": "2026-09-10",
            "kurz": "K", "text": text, "status": "Entwurf"}


def test_decide_row_unchanged_when_loop_returns_same_text():
    body = "Sauberer Text."
    out = rb.decide_row(_row2(body + "\n\n" + CTA), _cfg(), lambda t, cap, voice, material: t)
    assert out["aktion"] == "unveraendert" and out["text_neu"] == body + "\n\n" + CTA


def test_decide_row_repaired_text_gets_cta_back():
    seen = {}

    def loop(t, cap, voice, material):
        seen.update(text=t, cap=cap, voice=voice, material=material)
        return "Repariert."

    out = rb.decide_row(_row2("Kaputt.\n\n" + CTA), _cfg(), loop)
    assert seen["text"] == "Kaputt." and seen["voice"] == "Stimme" and seen["cap"] == 2100
    assert seen["material"].startswith("Thema: T")
    assert out["aktion"] == "repariert" and out["text_neu"] == "Repariert.\n\n" + CTA


def test_decide_row_cleared_on_residue_or_hard_violation():
    out = rb.decide_row(_row2("Kaputt.\n\n" + CTA), _cfg(), lambda *a: "")
    assert out["aktion"] == "geleert" and out["text_neu"] == "" and "Restbefund" in out["grund"]
    long = "x" * 2200
    calls = []
    out = rb.decide_row(_row2(long), _cfg(), lambda *a: calls.append(1) or long)
    assert out["aktion"] == "geleert" and "Zeichen" in out["grund"]
    assert calls == []


def test_notion_props_for_text_and_for_clearing():
    assert rb.notion_props_for("Neu.") == {"Post-Text": {"rich_text": [{"text": {"content": "Neu."}}]}}
    assert rb.notion_props_for("") == {"Post-Text": {"rich_text": []}}
