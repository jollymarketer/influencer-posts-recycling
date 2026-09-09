"""Tests fuer den Bewertungslauf mit drei Bildvarianten (run_image_eval).
Kein Notion-, kein kie.ai-Aufruf. CLIENT=swot vor dem Import wie in
test_image_fill."""
import os
import sys

os.environ["CLIENT"] = "swot"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from clients import load_client

load_client.cache_clear()

import run_image_eval


def _row(pid, status="Entwurf", kanal="LinkedIn Robert", text="Beitrag",
         bild=None, fmt="Story"):
    return {"id": pid, "properties": {
        "Titel": {"title": [{"plain_text": f"Titel {pid}"}]},
        "Status": {"select": {"name": status} if status else None},
        "Kanal": {"select": {"name": kanal} if kanal else None},
        "Post-Text": {"rich_text": [{"plain_text": text}] if text else []},
        "Format": {"select": {"name": fmt}},
        "Soundbyte": {"rich_text": [{"plain_text": "Fuenf Gesellschaften, fuenf Definitionen."}]},
        "Infografik-Skelett": {"rich_text": [{"plain_text": "TYP: Comparison table\nMETAPHER: Waage\nEBENEN:\n- links\n- rechts"}]},
        "Kurzbeschreibung": {"rich_text": [{"plain_text": "Kurz"}]},
        "Bild": {"files": bild or []},
    }}


def test_entwurf_linkedin_rows_without_image_qualify():
    rows = [
        _row("a"),
        _row("b", status="Text freigegeben"),
        _row("c", kanal="swot.de Blog"),
        _row("d", text=""),
        _row("e", bild=[{"name": "x.png"}]),
    ]
    assert [k["page_id"] for k in run_image_eval.eval_candidates(rows)] == ["a"]


def test_force_includes_rows_with_image_and_status_is_configurable():
    rows = [_row("a", bild=[{"name": "x.png"}]), _row("b", status="Text freigegeben")]
    got = run_image_eval.eval_candidates(rows, force=True)
    assert [k["page_id"] for k in got] == ["a"]
    got = run_image_eval.eval_candidates(rows, status="Text freigegeben")
    assert [k["page_id"] for k in got] == ["b"]


def test_three_distinct_archetypes_per_post():
    for fmt in ("Opinion", "POV", "Signature", "Story", "CaseProof"):
        k = run_image_eval.eval_candidates([_row("a", fmt=fmt)])[0]
        got = run_image_eval.pick_variants(k)
        assert len(got) == 3, (fmt, got)
        assert len(set(got)) == 3, (fmt, got)
        assert all(a in run_image_eval.ARCHETYPES for a in got)
