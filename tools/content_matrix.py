"""Content-Matrix-Modell (Douwe Wester: 3 Jobs x 3 Stages = 9 Boxen).

Reine Python-Logik ohne LLM: Box-Modell, Mandanten-Whitelist, Quota-Mathe,
Asset-Auswahl und Zahlen-Guard. Spec:
docs/superpowers/specs/2026-07-08-content-matrix-coverage-design.md
"""
import re

JOBS = ("Perspective", "Proof", "Promotion")
STAGES = ("Awareness", "Education", "Selection")

# Box -> Formate. Reihenfolge der Formate = deterministische Fallback-Ordnung.
BOX_FORMATS = {
    ("Perspective", "Awareness"): ("Opinion",),
    ("Perspective", "Education"): ("POV", "Signature"),
    ("Perspective", "Selection"): ("Comparison",),
    ("Proof", "Awareness"): ("Story",),
    ("Proof", "Education"): ("Method",),
    ("Proof", "Selection"): ("CaseProof",),
    ("Promotion", "Awareness"): ("Debate",),
    ("Promotion", "Education"): ("Magnet",),
    ("Promotion", "Selection"): ("Offer",),
}

FORMAT_TO_BOX = {f: box for box, formats in BOX_FORMATS.items() for f in formats}

PROMOTION_FORMATS = tuple(
    f for box, formats in BOX_FORMATS.items() if box[0] == "Promotion" for f in formats
)

# Boxen, die nur mit gefuelltem Asset-Block laufen duerfen (Whitelist-Guard).
ASSET_GATED_BOXES = {
    ("Proof", "Selection"): "PROOF_ASSETS",
    ("Promotion", "Education"): "LEAD_MAGNETS",
    ("Promotion", "Selection"): "OFFERS",
}

# Format -> Asset-Config-Attribut (fuer die Asset-Injektion in den Prompt).
FORMAT_ASSET_ATTR = {
    "CaseProof": "PROOF_ASSETS",
    "Magnet": "LEAD_MAGNETS",
    "Offer": "OFFERS",
}

# Legacy-Formate: Verhalten ohne MATRIX-Config (Mandant ohne Matrix-Feature).
LEGACY_FORMATS = ("Opinion", "POV", "Signature", "Story")


def effective_boxes(cfg) -> list:
    """Deklarierte Boxen minus Boxen, deren Asset-Block leer ist.
    Mandant ohne MATRIX -> [] (Matrix-Feature aus)."""
    matrix = getattr(cfg, "MATRIX", None)
    if not matrix:
        return []
    boxes = []
    for box in matrix.get("boxes", []):
        box = tuple(box)
        attr = ASSET_GATED_BOXES.get(box)
        if attr and not getattr(cfg, attr, None):
            continue
        boxes.append(box)
    return boxes


def formats_for_box(box, cfg) -> list:
    """Kandidaten-Formate einer Ziel-Box (nur wenn die Box effektiv erlaubt ist)."""
    if tuple(box) not in effective_boxes(cfg):
        return []
    return list(BOX_FORMATS[tuple(box)])


def free_formats(cfg) -> list:
    """Format-Kandidaten fuer einen freien Best-Fit-Run: alle Formate der
    effektiven Boxen MINUS Promotion (Promotion nur via Quota-Ziel, damit die
    Kappe deterministisch haelt). Ohne MATRIX -> die 4 Legacy-Formate."""
    boxes = effective_boxes(cfg)
    if not boxes:
        return list(LEGACY_FORMATS)
    return [
        f
        for box in boxes
        for f in BOX_FORMATS[box]
        if f not in PROMOTION_FORMATS and f not in FORMAT_ASSET_ATTR
    ]
