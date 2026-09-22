"""Client configs carry the matrix + asset + persona blocks."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import content_matrix as cm

jolly = importlib.import_module("clients.jolly.config")
lisocon = importlib.import_module("clients.lisocon.config")


def test_jolly_declares_all_nine_magnet_still_gated():
    assert len(jolly.MATRIX["boxes"]) == 9
    # PROOF_ASSETS + OFFERS gefuellt (Richard 2026-07-09), LEAD_MAGNETS bewusst
    # leer -> 8 effektive Boxen, nur Promotion x Education bleibt zu.
    eff = cm.effective_boxes(jolly)
    assert len(eff) == 8
    assert ("Proof", "Selection") in eff
    assert ("Promotion", "Selection") in eff
    assert ("Promotion", "Education") not in eff


def test_jolly_proof_assets_pin_canonical_numbers():
    metrics = " ".join(a["metric"] for a in jolly.PROOF_ASSETS)
    assert "+70%" in metrics      # Styla SQL (Kanon Richard 2026-07-09)
    assert "+200%" in metrics     # CLAAS aktive User (Kanon, nicht +300%)
    assert "+140%" in metrics     # Buhl Reply-Rates
    assert "8%" in metrics        # Aviloo Reply-Rate
    assert len(jolly.PROOF_ASSETS) == 5 and len(jolly.OFFERS) == 1


def test_lisocon_excludes_promotion_selection_by_policy():
    assert ("Promotion", "Selection") not in [tuple(b) for b in lisocon.MATRIX["boxes"]]
    eff = cm.effective_boxes(lisocon)
    assert ("Proof", "Selection") in eff          # PROOF_ASSETS gefuellt
    # LEAD_MAGNETS gefuellt (Richard 2026-07-25: layout-check + diagnose live)
    assert ("Promotion", "Education") in eff
    assert len(eff) == 8


def test_lisocon_lead_magnets_carry_live_urls():
    urls = " ".join(m["cta"] for m in lisocon.LEAD_MAGNETS)
    assert "https://lnkd.in/dGACGzrs" in urls
    assert "https://in2go.io/diagnose/" in urls
    assert len(lisocon.LEAD_MAGNETS) == 2


def test_lisocon_proof_assets_pin_real_numbers():
    metrics = " ".join(a["metric"] for a in lisocon.PROOF_ASSETS)
    assert "69%" in metrics and "80%" in metrics and "30" in metrics


def test_personas_defined_with_dominant_first():
    for cfg in (jolly, lisocon):
        personas = cfg.CONTENT_PERSONAS
        assert personas and personas[0]["share"] == "dominant"
        for p in personas:
            for key in ("id", "label", "pains", "kpis", "vocabulary_use",
                        "vocabulary_avoid", "scene_de", "scene_en", "cta_style"):
                assert p[key], f"{cfg.NAME}:{p.get('id')} missing {key}"


def test_comparison_subject_tokens_exist_in_both_configs():
    for cfg in (jolly, lisocon):
        assert cfg.TOKENS["COMPARISON_SUBJECT_DE"]
        assert cfg.TOKENS["COMPARISON_SUBJECT_EN"]


def test_topic_fit_frage_deckt_alle_achsen():
    """Der Achsen-Deckel kann nur wirken, wenn achsenfremde Posts ueberhaupt
    topic_fit bekommen. Die Frage nennt deshalb jedes der acht Felder."""
    from clients.jolly import config as jolly_config
    frage = jolly_config.TOKENS["TOPIC_FIT_QUESTION"].lower()
    for begriff in ("outbound", "revops", "positionierung", "sales-prozess",
                    "enablement", "content", "bestandskunden", "ki im gtm"):
        assert begriff in frage, f"{begriff} fehlt in TOPIC_FIT_QUESTION"


def test_voc_block_erzwingt_keinen_rahmen_mehr():
    """Die vier VoC-Rahmen bleiben Bewertungshilfe. Harte Regeln wortgleich."""
    from clients.jolly import config as jolly_config
    doc = jolly_config.CONTEXT  # VOC-Block steht in CONTEXT, nicht im Modul-Docstring
    assert "bevorzugt in diesen Problem-Rahmen" not in doc
    assert "kein Pflicht-Rahmen" in doc
    assert 'NIE "Kaltakquise ist tot" schreiben' in doc
    assert "US-Zahlen und Dollar-Betraege nie als DACH-Fakt" in doc
    assert "NIE Anbieter- oder Agenturnamen nennen" in doc
    assert 'BIG IDEA (Content-Franchise-Dach, traegt jeden Post): "Eine Ebene frueher."' in doc
