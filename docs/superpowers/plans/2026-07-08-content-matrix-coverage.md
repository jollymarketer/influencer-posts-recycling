# Content Matrix Coverage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the daily recycling engine cover the 9-box Ideal Customer-Led Content Matrix (Perspective/Proof/Promotion x Awareness/Education/Selection) via a deterministic quota router, 6 new post formats, a per-client asset whitelist with code guards, a persona lens, and Notion tracking.

**Architecture:** A new pure-Python module `tools/content_matrix.py` holds the box model, quota math and guards (no LLM, fully unit-testable). `tools/post_scorer.py` gains 6 new format structure blocks plus persona/asset prompt injection. `run_research.py` wires a "target box" step before format pick. Notion gets 4 new select properties that drive the quota window.

**Tech Stack:** Python 3.12, anthropic SDK (claude-haiku-4-5-20251001 for picks, claude-sonnet-4-6 for generation), Notion REST API via `tools/notion_db.py`, pytest with `unittest.mock`.

**Spec:** `docs/superpowers/specs/2026-07-08-content-matrix-coverage-design.md`

## Global Constraints

- Repo root: `C:\Users\richa\Jolly_Claude_Code\Jolly Automations\Influencer Posts Recycling` (path contains spaces — always quote). The `.links` alias serves stale reads; work on this path only.
- **Auto-deploy: every push to `master` is go-live.** Run the full suite before every push. Commit locally per task; pushing may be batched, final task pushes.
- Run tests as: `python -m pytest tests/ -q` from the repo root (conftest handles sys.path). Run one-off scripts as `PYTHONPATH="$(pwd)" python scripts/<name>.py`.
- `clients.apply_tokens` RAISES on any unresolved `[[TOKEN]]`. Every new `[[TOKEN]]` used in a template MUST be added to BOTH `clients/jolly/config.py` AND `clients/lisocon/config.py` in the same task, or module import crashes.
- String style: `tools/post_scorer.py` writes German prompt text ASCII-escaped (ae/oe/ue, "fuer", "Saetze") — match it. `clients/lisocon/config.py` uses real umlauts — match it. `clients/jolly/config.py` is ASCII-escaped — match it.
- Prompt-rule changes are advisory; enforcement needs a code backstop plus a pin test on the prompt text (project lesson from the Clay de-emphasis review).
- Generated posts: never em dash / en dash as sentence break; no fabricated client names, revenue numbers or case studies outside the pinned asset whitelist. These rules already live in the shared prompt sections — new structure blocks must not contradict them.
- No new dependencies. Existing test suite (104 tests) must stay green.
- Anthropic model ids: picks `claude-haiku-4-5-20251001`, generation `claude-sonnet-4-6` (as already used in `tools/post_scorer.py`).

---

### Task 1: Box model + effective boxes (`tools/content_matrix.py`)

**Files:**
- Create: `tools/content_matrix.py`
- Create: `tests/test_content_matrix.py`

**Interfaces:**
- Produces (later tasks rely on these exact names):
  - `JOBS = ("Perspective", "Proof", "Promotion")`
  - `STAGES = ("Awareness", "Education", "Selection")`
  - `BOX_FORMATS: dict[tuple[str, str], tuple[str, ...]]`
  - `FORMAT_TO_BOX: dict[str, tuple[str, str]]`
  - `PROMOTION_FORMATS: tuple[str, ...]`
  - `ASSET_GATED_BOXES: dict[tuple[str, str], str]` (box -> config attr name)
  - `effective_boxes(cfg) -> list[tuple[str, str]]`
  - `formats_for_box(box, cfg) -> list[str]`
  - `free_formats(cfg) -> list[str]`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_content_matrix.py`:

```python
"""Tests for the content matrix box model and quota logic. Pure functions."""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import content_matrix as cm

ALL_BOXES = [(j, s) for j in cm.JOBS for s in cm.STAGES]


def _cfg(boxes=None, proof=None, offers=None, magnets=None,
         mix=None, floor=2, cap=2):
    matrix = None
    if boxes is not None:
        matrix = {
            "mix": mix or {"Perspective": 5, "Proof": 3, "Promotion": 2},
            "selection_floor": floor,
            "promotion_cap": cap,
            "boxes": boxes,
        }
    return SimpleNamespace(
        MATRIX=matrix,
        PROOF_ASSETS=proof or [],
        OFFERS=offers or [],
        LEAD_MAGNETS=magnets or [],
    )


def test_box_model_is_complete():
    assert set(cm.BOX_FORMATS) == set(ALL_BOXES)
    # every format maps back to exactly one box
    for box, formats in cm.BOX_FORMATS.items():
        for f in formats:
            assert cm.FORMAT_TO_BOX[f] == box
    assert set(cm.PROMOTION_FORMATS) == {"Debate", "Magnet", "Offer"}


def test_effective_boxes_drops_asset_gated_boxes_without_assets():
    cfg = _cfg(boxes=ALL_BOXES)  # all 9 declared, no assets
    eff = cm.effective_boxes(cfg)
    assert ("Proof", "Selection") not in eff
    assert ("Promotion", "Education") not in eff
    assert ("Promotion", "Selection") not in eff
    assert len(eff) == 6


def test_effective_boxes_with_assets_keeps_all_nine():
    cfg = _cfg(boxes=ALL_BOXES, proof=[{"id": "a"}],
               offers=[{"id": "b"}], magnets=[{"id": "c"}])
    assert len(cm.effective_boxes(cfg)) == 9


def test_effective_boxes_respects_declared_whitelist():
    boxes = [b for b in ALL_BOXES if b != ("Promotion", "Selection")]
    cfg = _cfg(boxes=boxes, proof=[{"id": "a"}], offers=[{"id": "b"}])
    eff = cm.effective_boxes(cfg)
    assert ("Promotion", "Selection") not in eff  # declared out stays out
    assert ("Proof", "Selection") in eff


def test_effective_boxes_empty_when_matrix_missing():
    cfg = SimpleNamespace()  # tenant without MATRIX
    assert cm.effective_boxes(cfg) == []


def test_formats_for_box_and_free_formats():
    cfg = _cfg(boxes=ALL_BOXES, proof=[{"id": "a"}],
               offers=[{"id": "b"}], magnets=[{"id": "c"}])
    assert cm.formats_for_box(("Perspective", "Education"), cfg) == ["POV", "Signature"]
    assert cm.formats_for_box(("Proof", "Selection"), cfg) == ["CaseProof"]
    free = cm.free_formats(cfg)
    # free run never picks promotion formats (cap must stay deterministic)
    assert set(free) == {"Opinion", "POV", "Signature", "Story", "Comparison", "Method"}


def test_free_formats_fallback_when_matrix_missing():
    cfg = SimpleNamespace()
    assert cm.free_formats(cfg) == ["Opinion", "POV", "Signature", "Story"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_content_matrix.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.content_matrix'`

- [ ] **Step 3: Write the implementation**

Create `tools/content_matrix.py`:

```python
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
        if f not in PROMOTION_FORMATS
    ]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_content_matrix.py -q`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add tools/content_matrix.py tests/test_content_matrix.py
git commit -m "feat: content matrix box model + per-client effective boxes"
```

---

### Task 2: Quota math `pick_target_box` + `coverage_line`

**Files:**
- Modify: `tools/content_matrix.py` (append)
- Modify: `tests/test_content_matrix.py` (append)

**Interfaces:**
- Consumes: Task 1 (`effective_boxes`, `BOX_FORMATS`, `JOBS`, `STAGES`)
- Produces:
  - `pick_target_box(recent_boxes: list[tuple[str, str]], cfg) -> tuple[str, str] | None`
  - `coverage_line(recent_boxes, cfg) -> str`

**Spec rules encoded here (verbatim from the spec):** row deficient when
`actual < floor(target_share_per_10) - 1` is NOT the wording — the spec says
"actual < floor(target share * 10) - 1, i.e. under target by a full post",
with mix given per 10 as {Perspective: 5, Proof: 3, Promotion: 2}. So:
deficient row means `count(row) < mix[row] - 1`. Selection floor: fewer than
`selection_floor` Selection posts in the window. Cold start: < 5 classified
-> always None; 5-9 classified -> only the Selection floor; 10 -> full logic.
Priority: floor first, then largest row deficit (tie: order Perspective,
Proof, Promotion). Promotion targets skipped while window holds >= cap
promotion posts.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_content_matrix.py`:

```python
P, PR, PM = "Perspective", "Proof", "Promotion"
A, E, S = "Awareness", "Education", "Selection"
FULL_CFG = _cfg(boxes=ALL_BOXES, proof=[{"id": "a"}],
                offers=[{"id": "b"}], magnets=[{"id": "c"}])


def test_pick_target_none_when_matrix_missing():
    assert cm.pick_target_box([(P, A)] * 10, SimpleNamespace()) is None


def test_pick_target_none_below_five_classified():
    assert cm.pick_target_box([(P, A)] * 4, FULL_CFG) is None


def test_partial_window_enforces_only_selection_floor():
    # 6 classified, zero Selection -> floor violated -> a Selection box.
    window = [(P, A), (P, E), (P, A), (PR, A), (P, E), (P, A)]
    target = cm.pick_target_box(window, FULL_CFG)
    assert target is not None and target[1] == S
    # row with the largest deficit that owns a whitelisted Selection box:
    # counts P=5 (target 5, deficit 0), Proof=1 (deficit 2), Promo=0 (deficit 2)
    # tie Proof/Promotion -> fixed order puts Proof first.
    assert target == (PR, S)


def test_partial_window_with_floor_met_returns_none():
    # 6 classified incl. 2 Selection -> floor ok, row quotas not yet enforced.
    window = [(P, S), (PR, S), (P, A), (P, E), (P, A), (P, A)]
    assert cm.pick_target_box(window, FULL_CFG) is None


def test_floor_pick_skips_promotion_when_cap_reached():
    # zero Selection, but already 2 promotion posts -> Promotion x Selection
    # is not a valid floor target; Proof x Selection gated off (no assets).
    cfg = _cfg(boxes=ALL_BOXES)  # 6 effective boxes, only P x S has Selection
    window = [(PM, A), (PM, E), (P, A), (P, E), (P, A), (PR, A),
              (P, A), (P, E), (PR, A), (P, A)]
    assert cm.pick_target_box(window, cfg) == (P, S)


def test_full_window_row_deficit_targets_promotion():
    # P=6, Proof=4, Promo=0 -> Promotion deficient (0 < 2-1). Stage least
    # represented within Promotion boxes; all promo stages at 0 -> order A first.
    window = [(P, A), (P, E), (P, S), (P, A), (P, E), (P, S),
              (PR, A), (PR, E), (PR, A), (PR, E)]
    assert cm.pick_target_box(window, FULL_CFG) == (PM, A)


def test_full_window_balanced_returns_none():
    window = [(P, A), (P, E), (P, S), (P, A), (P, E),
              (PR, A), (PR, E), (PR, S), (PM, A), (PM, E)]
    assert cm.pick_target_box(window, FULL_CFG) is None


def test_full_window_promotion_deficit_blocked_by_cap():
    # Promotion count 2 == cap -> even though Proof fine and P over target,
    # no promotion target may be produced; here nothing else is deficient.
    window = [(P, A), (P, E), (P, S), (P, A), (P, E), (P, S),
              (PR, A), (PR, E), (PM, A), (PM, E)]
    # P=6 (no deficit possible upward), Proof=2 (2 < 3-1 is False), Promo at cap.
    assert cm.pick_target_box(window, FULL_CFG) is None


def test_coverage_line_reports_actuals_vs_targets():
    window = [(P, A)] * 6 + [(PR, E)] * 2 + [(PM, A)] * 2
    line = cm.coverage_line(window, FULL_CFG)
    assert "Perspective 6/5" in line
    assert "Proof 2/3" in line
    assert "Promotion 2/2" in line
    assert "Selection 0/2" in line
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_content_matrix.py -q`
Expected: FAIL with `AttributeError: ... has no attribute 'pick_target_box'`

- [ ] **Step 3: Write the implementation**

Append to `tools/content_matrix.py`:

```python
def _row_deficits(window: list, mix: dict) -> dict:
    """Row -> Fehlbetrag gegen Soll (nur positive Defizite)."""
    counts = {job: 0 for job in JOBS}
    for job, _stage in window:
        if job in counts:
            counts[job] += 1
    return {job: max(0, mix.get(job, 0) - counts[job]) for job in JOBS}


def pick_target_box(recent_boxes: list, cfg):
    """Deterministische Ziel-Box gegen Mix 50/30/20 + Selection-Floor +
    Promotion-Kappe ueber die letzten 10 klassifizierten Posts.

    Regeln (Spec): <5 klassifiziert -> None. 5-9 -> nur Selection-Floor.
    10 -> volle Zeilen-Quota. Zeile defizitaer wenn actual < mix[row]-1.
    Floor vor Zeilen-Defizit; Promotion-Ziele entfallen ab Kappe.
    """
    matrix = getattr(cfg, "MATRIX", None)
    boxes = effective_boxes(cfg)
    if not matrix or not boxes:
        return None

    window = [tuple(b) for b in recent_boxes[:10] if tuple(b) in BOX_FORMATS]
    if len(window) < 5:
        return None

    mix = matrix["mix"]
    floor = matrix["selection_floor"]
    cap = matrix["promotion_cap"]
    promo_count = sum(1 for job, _ in window if job == "Promotion")
    selection_count = sum(1 for _, stage in window if stage == "Selection")
    deficits = _row_deficits(window, mix)

    def _promo_ok(box):
        return box[0] != "Promotion" or promo_count < cap

    # 1) Selection-Floor zuerst.
    if selection_count < floor:
        candidates = [b for b in boxes if b[1] == "Selection" and _promo_ok(b)]
        if candidates:
            # Zeile mit groesstem Defizit zuerst, Tie-Break = feste JOBS-Ordnung.
            candidates.sort(key=lambda b: (-deficits[b[0]], JOBS.index(b[0])))
            return candidates[0]

    # 2) Zeilen-Quota erst bei vollem Fenster.
    if len(window) < 10:
        return None

    deficient = [
        job for job in JOBS
        if sum(1 for j, _ in window if j == job) < mix.get(job, 0) - 1
    ]
    deficient = [j for j in deficient if j != "Promotion" or promo_count < cap]
    if not deficient:
        return None
    target_row = max(deficient, key=lambda j: (deficits[j], -JOBS.index(j)))

    # Innerhalb der Zeile: am wenigsten bespielter Stage, Tie = STAGES-Ordnung.
    row_boxes = [b for b in boxes if b[0] == target_row]
    if not row_boxes:
        return None
    stage_counts = {s: sum(1 for j, st in window if j == target_row and st == s)
                    for s in STAGES}
    row_boxes.sort(key=lambda b: (stage_counts[b[1]], STAGES.index(b[1])))
    return row_boxes[0]


def coverage_line(recent_boxes: list, cfg) -> str:
    """Log-Zeile: Ist gegen Soll ueber das aktuelle Fenster."""
    matrix = getattr(cfg, "MATRIX", None)
    if not matrix:
        return "Matrix: aus (keine MATRIX-Config)"
    window = [tuple(b) for b in recent_boxes[:10] if tuple(b) in BOX_FORMATS]
    mix = matrix["mix"]
    parts = [
        f"{job} {sum(1 for j, _ in window if j == job)}/{mix.get(job, 0)}"
        for job in JOBS
    ]
    sel = sum(1 for _, s in window if s == "Selection")
    parts.append(f"Selection {sel}/{matrix['selection_floor']}")
    return f"Coverage ({len(window)} Posts): " + " | ".join(parts)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_content_matrix.py -q`
Expected: all pass (16 tests)

- [ ] **Step 5: Commit**

```bash
git add tools/content_matrix.py tests/test_content_matrix.py
git commit -m "feat: quota router pick_target_box + coverage log line"
```

---

### Task 3: Asset pick + numbers guard

**Files:**
- Modify: `tools/content_matrix.py` (append)
- Modify: `tests/test_content_matrix.py` (append)

**Interfaces:**
- Consumes: Task 1 (`FORMAT_ASSET_ATTR`)
- Produces:
  - `pick_asset(assets: list[dict], recent_ids: list[str]) -> dict | None` (least recently used)
  - `asset_for_format(post_format: str, cfg, recent_ids) -> dict | None`
  - `extract_figures(text: str) -> set[str]`
  - `figures_ok(text: str, asset: dict) -> bool`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_content_matrix.py`:

```python
ASSETS = [{"id": "case-a", "metric": "69% Kostensenkung"},
          {"id": "case-b", "metric": "80% Kostenreduktion"},
          {"id": "case-c", "metric": "12 Meetings in 6 Wochen"}]


def test_pick_asset_prefers_unused():
    assert cm.pick_asset(ASSETS, ["case-a", "case-b"])["id"] == "case-c"


def test_pick_asset_all_used_takes_least_recent():
    # recent_ids newest first -> case-c is the oldest use.
    assert cm.pick_asset(ASSETS, ["case-a", "case-b", "case-c"])["id"] == "case-c"


def test_pick_asset_empty_returns_none():
    assert cm.pick_asset([], []) is None


def test_asset_for_format_maps_attr():
    cfg = _cfg(boxes=ALL_BOXES, proof=ASSETS)
    assert cm.asset_for_format("CaseProof", cfg, [])["id"] == "case-a"
    assert cm.asset_for_format("Offer", cfg, []) is None      # OFFERS empty
    assert cm.asset_for_format("Opinion", cfg, []) is None    # no asset format


def test_extract_figures_normalizes():
    figs = cm.extract_figures("Wir haben 69 % gesenkt, 3,5x Pipeline, EUR 40.000 Budget.")
    assert "69%" in figs
    assert "3.5x" in figs
    assert any(f.startswith("eur40.000") or f.startswith("eur40000") for f in figs)


def test_extract_figures_ignores_plain_counts():
    # "3 Schritte" and years carry no unit -> not guarded.
    assert cm.extract_figures("In 3 Schritten seit 2024.") == set()


def test_figures_ok_accepts_whitelisted_number():
    asset = {"id": "hoermann", "claim": "Katalogproduktion", "metric": "69% Kostensenkung"}
    assert cm.figures_ok("Hoermann senkte die Kosten um 69%.", asset)


def test_figures_ok_rejects_foreign_number():
    asset = {"id": "hoermann", "metric": "69% Kostensenkung"}
    assert not cm.figures_ok("Das brachte 72% Ersparnis.", asset)


def test_figures_ok_true_when_draft_has_no_figures():
    asset = {"id": "hoermann", "metric": "69% Kostensenkung"}
    assert cm.figures_ok("Ein Post ganz ohne Zahlen mit Einheit.", asset)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_content_matrix.py -q`
Expected: FAIL with `AttributeError: ... 'pick_asset'`

- [ ] **Step 3: Write the implementation**

Append to `tools/content_matrix.py`:

```python
def pick_asset(assets: list, recent_ids: list):
    """Least-recently-used Asset: erst nie genutzte, sonst das am laengsten
    nicht genutzte (recent_ids ist neuestes-zuerst). [] -> None."""
    if not assets:
        return None
    for asset in assets:
        if asset.get("id") not in recent_ids:
            return asset
    # Alle benutzt: das mit dem aeltesten (= letzten) Auftritt in recent_ids.
    return max(assets, key=lambda a: recent_ids.index(a["id"]))


def asset_for_format(post_format: str, cfg, recent_ids: list):
    """Asset fuer ein Asset-Format aus der Mandanten-Config. None wenn das
    Format kein Asset braucht oder der Block leer ist."""
    attr = FORMAT_ASSET_ATTR.get(post_format)
    if not attr:
        return None
    return pick_asset(getattr(cfg, attr, None) or [], recent_ids or [])


# Zahlen mit Einheit: Prozent, Waehrung, Vielfache. Reine Zaehl-Zahlen
# ("3 Schritte", Jahreszahlen) sind bewusst NICHT geschuetzt.
_FIGURE_RE = re.compile(
    r"\d+(?:[.,]\d+)?\s*(?:%|prozent|percent)"
    r"|(?:€|\$|eur|usd)\s*\d+(?:[.,]\d+)*"
    r"|\d+(?:[.,]\d+)*\s*(?:€|eur|usd|dollar)"
    r"|\d+(?:[.,]\d+)?\s*(?:x\b|-fach\b|fach\b|times\b)",
    re.IGNORECASE,
)


def extract_figures(text: str) -> set:
    """Alle Einheiten-Zahlen eines Texts, normalisiert (lowercase, ohne
    Leerzeichen, Komma -> Punkt)."""
    out = set()
    for m in _FIGURE_RE.finditer(text or ""):
        out.add(re.sub(r"\s+", "", m.group(0)).replace(",", ".").lower())
    return out


def figures_ok(text: str, asset: dict) -> bool:
    """Zahlen-Guard: jede Einheiten-Zahl im Draft muss aus dem gewaehlten
    Asset stammen (alle String-Felder des Assets zaehlen als Whitelist)."""
    allowed = set()
    for value in (asset or {}).values():
        if isinstance(value, str):
            allowed |= extract_figures(value)
    return extract_figures(text) <= allowed
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_content_matrix.py -q`
Expected: all pass (25 tests)

- [ ] **Step 5: Commit**

```bash
git add tools/content_matrix.py tests/test_content_matrix.py
git commit -m "feat: LRU asset pick + numbers guard for CaseProof"
```

---

### Task 4: Client configs — MATRIX, assets, personas, new tokens

**Files:**
- Modify: `clients/jolly/config.py`
- Modify: `clients/lisocon/config.py`
- Create: `tests/test_client_matrix_config.py`

**Interfaces:**
- Consumes: Task 1 (`effective_boxes`)
- Produces (exact attribute names later tasks read):
  - `MATRIX`, `PROOF_ASSETS`, `OFFERS`, `LEAD_MAGNETS`, `CONTENT_PERSONAS` on both client configs
  - New tokens in both `TOKENS` dicts: `COMPARISON_SUBJECT_DE`, `COMPARISON_SUBJECT_EN`

**Why tokens here first:** Task 5 adds `[[COMPARISON_SUBJECT_DE]]` /
`[[COMPARISON_SUBJECT_EN]]` to prompt templates; `clients.apply_tokens`
raises on unresolved markers, so both configs must carry them BEFORE the
template change lands.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_client_matrix_config.py`:

```python
"""Client configs carry the matrix + asset + persona blocks."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import content_matrix as cm

jolly = importlib.import_module("clients.jolly.config")
lisocon = importlib.import_module("clients.lisocon.config")


def test_jolly_declares_all_nine_but_assets_gate_three():
    assert len(jolly.MATRIX["boxes"]) == 9
    # Assets leer bis Richard liefert -> 6 effektive Boxen.
    assert len(cm.effective_boxes(jolly)) == 6


def test_lisocon_excludes_promotion_selection_by_policy():
    assert ("Promotion", "Selection") not in [tuple(b) for b in lisocon.MATRIX["boxes"]]
    eff = cm.effective_boxes(lisocon)
    assert ("Proof", "Selection") in eff          # PROOF_ASSETS gefuellt
    assert ("Promotion", "Education") not in eff  # keine Lead Magnets
    assert len(eff) == 7


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_client_matrix_config.py -q`
Expected: FAIL with `AttributeError: module 'clients.jolly.config' has no attribute 'MATRIX'`

- [ ] **Step 3: Extend `clients/jolly/config.py`**

Add the two tokens inside the existing `TOKENS` dict (after the
`"SCENE_ACTOR_EN"` line, in the `--- Format-Strukturen ---` section):

```python
    "COMPARISON_SUBJECT_DE": "externe GTM-Unterstuetzung (Fractional CMO, Outbound-Agentur oder interner Hire)",
    "COMPARISON_SUBJECT_EN": "external GTM support (fractional CMO, outbound agency, or an internal hire)",
```

Append at the end of the file (after `INFLUENCERS_CSV`):

```python
# --- Content-Matrix (Spec 2026-07-08) ---------------------------------------
# 9 Boxen deklariert; Boxen mit leerem Asset-Block schaltet der Whitelist-Guard
# in tools/content_matrix.py automatisch ab (aktuell: CaseProof/Magnet/Offer).
MATRIX = {
    "mix": {"Perspective": 5, "Proof": 3, "Promotion": 2},  # Soll pro 10 Posts
    "selection_floor": 2,   # mind. 2 von 10 in der Selection-Spalte
    "promotion_cap": 2,     # max. 2 von 10 in der Promotion-Zeile
    "boxes": [(job, stage)
              for job in ("Perspective", "Proof", "Promotion")
              for stage in ("Awareness", "Education", "Selection")],
}

# Nur echte, von Richard freigegebene Zahlen. Leer = CaseProof bleibt aus.
PROOF_ASSETS: list = []

# Aktuelle Angebote mit CTA-Wortlaut. Leer = Offer-Format bleibt aus.
OFFERS: list = []

# Existierende Artefakte (PDF, Checkliste, Template). Leer = Magnet bleibt aus.
LEAD_MAGNETS: list = []

# Content-Personas (v1: Generierungs-Linse + Notion-Tracking; Quota = Phase 2).
# Wortlaut-Entwurf, Freigabe Richard ausstehend.
CONTENT_PERSONAS = [
    {
        "id": "founder-ceo",
        "label": "Founder / CEO",
        "share": "dominant",
        "pains": "Pipeline nicht planbar, Wachstum haengt am Gruender-Netzwerk, keine interne Rolle die das GTM-System denkt",
        "kpis": "qualifizierte Meetings pro Monat, CAC, Forecast-Genauigkeit, Zeit bis zum ersten planbaren Kanal",
        "vocabulary_use": "Planbarkeit, System, Engpass, Prioritaeten, Investition vs. Wette",
        "vocabulary_avoid": "Marketing-Jargon (MQL, Attribution-Modelle), Tool-Namen als Loesung",
        "scene_de": "ein Founder, der nach einem starken Quartal ploetzlich in einen leeren Pipeline-Monat laeuft",
        "scene_en": "a founder who hits an empty-pipeline month right after a strong quarter",
        "cta_style": "discovery",
    },
    {
        "id": "cro-vp-sales",
        "label": "CRO / VP Sales",
        "share": "secondary",
        "pains": "Team verfehlt Quote trotz Aktivitaet, Uebergaben zwischen Marketing und Sales reissen, Forecast auf Bauchgefuehl",
        "kpis": "Pipeline-Coverage, Conversion je Stage, Ramp-Zeit neuer Reps, Reply-to-Meeting-Rate",
        "vocabulary_use": "Coverage, Stage-Conversion, Playbook, Kadenz, Qualifizierung",
        "vocabulary_avoid": "Brand-Sprech, abstrakte Strategie-Floskeln ohne operativen Hebel",
        "scene_de": "ein VP Sales im Forecast-Call, der die Luecke zwischen Commit und Realitaet erklaeren muss",
        "scene_en": "a VP of sales in a forecast call explaining the gap between commit and reality",
        "cta_style": "discovery",
    },
]
```

- [ ] **Step 4: Extend `clients/lisocon/config.py`**

Add the two tokens inside the existing `TOKENS` dict (after the
`"SCENE_ACTOR_EN"` line):

```python
    "COMPARISON_SUBJECT_DE": "eine Lösung für mehrsprachige Dokumentproduktion (Agentur-DTP, interne Nacharbeit oder Automatisierung)",
    "COMPARISON_SUBJECT_EN": "a solution for multilingual document production (agency DTP, internal rework, or automation)",
```

Append at the end of the file (after `INFLUENCERS_CSV`):

```python
# --- Content-Matrix (Spec 2026-07-08) ---------------------------------------
# Promotion × Selection ist per Playbook AUSGESCHLOSSEN (kein Demo-CTA, kein
# Produkt-Pitch) — deklarativ, nicht nur asset-gated. Promotion × Education
# fällt automatisch weg, solange LEAD_MAGNETS leer ist.
MATRIX = {
    "mix": {"Perspective": 5, "Proof": 3, "Promotion": 2},
    "selection_floor": 2,
    "promotion_cap": 2,
    "boxes": [(job, stage)
              for job in ("Perspective", "Proof", "Promotion")
              for stage in ("Awareness", "Education", "Selection")
              if (job, stage) != ("Promotion", "Selection")],
}

# Einzige erlaubte Referenzen (Playbook), Zahlen exakt so — nie neue erfinden.
PROOF_ASSETS = [
    {"id": "hoermann", "claim": "Katalog- und Doku-Produktion automatisiert",
     "metric": "69% Kostensenkung", "context": "offizielle, freigegebene Zahl"},
    {"id": "wago", "claim": "mehrsprachige Dokumentproduktion",
     "metric": "80% Kostenreduktion bei 17 Sprachen", "context": "freigegebene Referenz"},
    {"id": "stiebel-eltron", "claim": "Dokumentproduktion über 30 Sprachen",
     "metric": "30 Sprachen im Einsatz", "context": "freigegebene Referenz"},
]

OFFERS: list = []        # bewusst leer: kein Offer-Content für lisocon
LEAD_MAGNETS: list = []  # keine Lead Magnets gebaut -> Magnet-Format aus

# Aus der PERSONA-REGEL im CONTEXT strukturiert: genau EINE Achse pro Post.
CONTENT_PERSONAS = [
    {
        "id": "kaeufer",
        "label": "Käufer/Entscheider (Marketing-/MarCom-/Doku-Leitung)",
        "share": "dominant",
        "pains": "versteckte DTP-Nacharbeit sprengt Budget und Timeline, niemand budgetiert die Layout-Kosten nach der Übersetzung",
        "kpis": "Kosten pro Sprachversion, Time-to-Market mehrsprachiger Materialien, Reklamationen wegen Layout-Fehlern",
        "vocabulary_use": "versteckte Kosten, Durchlaufzeit, ROI, Prozesskette, druckfertig",
        "vocabulary_avoid": "Toolbedienung, Feature-Details, Übersetzungsqualität als Thema",
        "scene_de": "ein Marketingleiter, der die Agentur-Rechnung liest und die DTP-Position zum ersten Mal hinterfragt",
        "scene_en": "a head of marketing reading the agency invoice and questioning the DTP line item for the first time",
        "cta_style": "reply",
    },
    {
        "id": "anwender",
        "label": "Anwender (Translation-Manager, Designer)",
        "share": "secondary",
        "pains": "Copy-Paste-Korrekturen in InDesign über Dutzende Sprachversionen, Versionschaos zwischen Übersetzern und Layout",
        "kpis": "Korrekturschleifen pro Dokument, Stunden Nacharbeit pro Sprache, Fehler nach Freigabe",
        "vocabulary_use": "Korrekturlauf, Lektorat im Browser, Versionen, Layout-Erhalt",
        "vocabulary_avoid": "Budget- und ROI-Argumente (Käufer-Achse), Preise",
        "scene_de": "eine Designerin, die zum dritten Mal denselben Umbruch in zwölf Sprachversionen fixt",
        "scene_en": "a designer fixing the same line break in twelve language versions for the third time",
        "cta_style": "reply",
    },
]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_client_matrix_config.py tests/test_content_matrix.py -q`
Expected: all pass

- [ ] **Step 6: Run the full suite (config import touches everything)**

Run: `python -m pytest tests/ -q`
Expected: all pass (104 existing + new)

- [ ] **Step 7: Commit**

```bash
git add clients/jolly/config.py clients/lisocon/config.py tests/test_client_matrix_config.py
git commit -m "feat: MATRIX config, asset blocks and content personas for jolly + lisocon"
```

---

### Task 5: Six new format structure blocks in `post_scorer.py`

**Files:**
- Modify: `tools/post_scorer.py` (extend `FORMAT_STRUCTURES` dict, lines ~311-364)
- Modify: `tests/test_format_structures.py`

**Interfaces:**
- Consumes: Task 4 tokens (`[[COMPARISON_SUBJECT_DE]]`, `[[COMPARISON_SUBJECT_EN]]`)
- Produces: `FORMAT_STRUCTURES` with 10 keys: Opinion, POV, Signature, Story, Comparison, Method, CaseProof, Debate, Magnet, Offer

**CTA policy (spec):** the DM-CTA ban stays inside every non-promotion
block's close line (existing blocks already carry "Kein DM-CTA"). Debate
keeps the ban. Magnet allows exactly one comment-CTA. Offer allows exactly
one DM/discovery CTA. No fake scarcity anywhere.

- [ ] **Step 1: Update the failing tests**

In `tests/test_format_structures.py`, replace `test_formats_defined_with_de_and_en` and add pin tests:

```python
ALL_FORMAT_KEYS = {"Opinion", "POV", "Signature", "Story",
                   "Comparison", "Method", "CaseProof", "Debate", "Magnet", "Offer"}


def test_formats_defined_with_de_and_en():
    assert set(FORMAT_STRUCTURES) == ALL_FORMAT_KEYS
    for key in FORMAT_STRUCTURES:
        assert FORMAT_STRUCTURES[key]["de"].strip()
        assert FORMAT_STRUCTURES[key]["en"].strip()


def test_comparison_injects_decision_structure():
    de, en = _format_prompts(POST, "Comparison")
    assert "Entscheidungskriterien" in de and "Red Flags" in de
    assert "red flags" in en.lower()
    assert "Kein DM-CTA" in de  # promotion ban stays outside promotion row


def test_method_injects_steps_and_pitfall():
    de, en = _format_prompts(POST, "Method")
    assert "Stolperstein" in de
    assert "pitfall" in en.lower()


def test_caseproof_pins_numbers_to_asset():
    de, en = _format_prompts(POST, "CaseProof")
    assert "CASE-ASSET" in de and "woertlich" in de
    assert "case asset" in en.lower() and "verbatim" in en.lower()


def test_debate_demands_reply_not_dm():
    de, en = _format_prompts(POST, "Debate")
    assert "Lager" in de and "Kein DM-CTA" in de
    assert "camp" in en.lower()


def test_magnet_allows_exactly_comment_cta():
    de, en = _format_prompts(POST, "Magnet")
    assert "Kommentar-CTA" in de and "LEAD-MAGNET-ASSET" in de
    assert "comment" in en.lower()


def test_offer_allows_dm_or_discovery_cta_without_scarcity():
    de, en = _format_prompts(POST, "Offer")
    assert "OFFER-ASSET" in de and "kein kuenstlicher Zeitdruck" in de
    assert "scarcity" in en.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_format_structures.py -q`
Expected: FAIL (`assert set(FORMAT_STRUCTURES) == ALL_FORMAT_KEYS`)

- [ ] **Step 3: Add the six blocks**

In `tools/post_scorer.py`, inside the `FORMAT_STRUCTURES = { ... }` literal, after the `"Story"` entry add:

```python
    "Comparison": {
        "de": """Post-Struktur (ohne explizite Benennung):
1. Hook (1-2 Saetze): Der Entscheidungs-Moment - jemand steht vor der Wahl von [[COMPARISON_SUBJECT_DE]] und waehlt nach den falschen Kriterien. Entscheidet ob jemand weiterliest.
2. Entscheidungskriterien: 3-5 harte Kriterien oder Red Flags als scanbares Artefakt (das ist das eine Artefakt dieses Posts). Jedes Kriterium konkret pruefbar, keine Allgemeinplaetze.
3. Einordnung: Wann welche Option wirklich passt - inklusive mindestens einem ehrlichen Fall, in dem die eigene Kategorie NICHT die richtige Wahl ist. Kein Wettbewerber-Bashing, keine Namen.
4. Abschluss: Offene Schleife - eine spezifische, streitbare Frage zur Entscheidungslogik oder eine Flag-Plant-Zeile. Verboten ist nur das generische "Was denkst du?". Kein DM-CTA.""",
        "en": """Post structure (without labeling it):
1. Hook (1-2 sentences): the decision moment - someone choosing [[COMPARISON_SUBJECT_EN]] using the wrong criteria. Decides whether anyone reads on.
2. Decision criteria: 3-5 hard criteria or red flags as the scannable artifact of this post. Each one concretely checkable, no platitudes.
3. Placement: when each option genuinely fits - including at least one honest case where your own category is NOT the right choice. No competitor bashing, no names.
4. Close: an open loop - a specific, arguable question about the decision logic, or a flag-plant line. Only the generic "What do you think?" is banned. No DM CTA.""",
    },
    "Method": {
        "de": """Post-Struktur (ohne explizite Benennung):
1. Hook (1-2 Saetze): Das Ergebnis oder der Engpass, den die Methode adressiert - konkret, nicht abstrakt. Entscheidet ob jemand weiterliest.
2. Methode: 3-5 nummerierte Schritte (➊ ➋ ➌) als das eine scanbare Artefakt. Jeder Schritt eine Handlung mit erkennbarem Output, keine Theorie.
3. Stolperstein: Der eine Punkt, an dem Teams in der Praxis scheitern, und wie man ihn umgeht. Ein eigener Gedanke, den der Quell-Post nicht hat. Vorher-Nachher nur qualitativ - keine erfundenen Zahlen.
4. Abschluss: Offene Schleife - eine spezifische, streitbare Frage zur Methode oder eine Flag-Plant-Zeile. Verboten ist nur das generische "Was denkst du?". Kein DM-CTA.""",
        "en": """Post structure (without labeling it):
1. Hook (1-2 sentences): the outcome or bottleneck the method addresses - concrete, not abstract. Decides whether anyone reads on.
2. Method: 3-5 numbered steps (➊ ➋ ➌) as the one scannable artifact. Each step an action with a visible output, no theory.
3. Pitfall: the one point where teams fail in practice and how to avoid it. One original thought the source post does not have. Before/after only qualitative - no invented numbers.
4. Close: an open loop - a specific, arguable question about the method, or a flag-plant line. Only the generic "What do you think?" is banned. No DM CTA.""",
    },
    "CaseProof": {
        "de": """Post-Struktur (ohne explizite Benennung):
1. Hook (1-2 Saetze): Die Ergebnis-Zahl aus dem CASE-ASSET unten, im Kontext des Problems. Entscheidet ob jemand weiterliest.
2. Ausgangslage: Wo das Unternehmen vorher stand und warum der Status quo teuer war. Konkret, ohne erfundene Details.
3. Weg: Was konkret veraendert wurde (Methode, Reihenfolge, Entscheidung) - als kurzes scanbares Artefakt. Ein eigener Gedanke, den der Quell-Post nicht hat.
4. Abschluss: Das Learning als uebertragbare Regel plus offene Schleife (streitbare Frage oder Flag-Plant-Zeile). Kein DM-CTA.
Harte Zahlen-Regel: JEDE Zahl mit Einheit (Prozent, Euro, x-fach) stammt woertlich aus dem CASE-ASSET-Block. Keine weiteren Zahlen erfinden, auch keine plausiblen. Firmenname nur wenn im Asset genannt.""",
        "en": """Post structure (without labeling it):
1. Hook (1-2 sentences): the result number from the CASE ASSET below, framed by the problem. Decides whether anyone reads on.
2. Starting point: where the company stood before and why the status quo was expensive. Concrete, no invented detail.
3. Path: what concretely changed (method, sequence, decision) - as a short scannable artifact. One original thought the source post does not have.
4. Close: the learning as a transferable rule plus an open loop (arguable question or flag-plant line). No DM CTA.
Hard numbers rule: EVERY unit-bearing number (percent, currency, x-times) is taken verbatim from the CASE ASSET block. Invent no further numbers, not even plausible ones. Company name only if the asset names it.""",
    },
    "Debate": {
        "de": """Post-Struktur (ohne explizite Benennung):
1. Hook (1-2 Saetze): Eine polarisierende Entweder-Oder-These, bei der sich beide Lager sofort angesprochen fuehlen. Entscheidet ob jemand weiterliest.
2. Zwei Lager: Beide Positionen kurz und fair in je 2-3 Saetzen - so, dass Vertreter beider Seiten sich wiedererkennen. Konkret, nicht abstrakt.
3. Eigene Position: Auf welcher Seite du stehst und der eine Beleg aus der Praxis. Ein eigener Gedanke, den der Quell-Post nicht hat.
4. Abschluss: Explizite Aufforderung, sich in den Kommentaren fuer ein Lager zu entscheiden und die Wahl zu begruenden. Das ist der Kern dieses Formats. Kein DM-CTA, keine Umfrage-Mechanik ausserhalb der Kommentare.""",
        "en": """Post structure (without labeling it):
1. Hook (1-2 sentences): a polarizing either-or thesis both camps instantly react to. Decides whether anyone reads on.
2. Two camps: both positions short and fair, 2-3 sentences each - so members of either side recognize themselves. Concrete, not abstract.
3. Your position: which camp you are in and the one proof from practice. One original thought the source post does not have.
4. Close: an explicit prompt to pick a camp in the comments and justify the pick. That prompt is the point of this format. No DM CTA, no poll mechanics outside the comments.""",
    },
    "Magnet": {
        "de": """Post-Struktur (ohne explizite Benennung):
1. Hook (1-2 Saetze): Das Problem, das das LEAD-MAGNET-ASSET unten loest - aus der Praxis, nicht als Werbetext. Entscheidet ob jemand weiterliest.
2. Substanz-Vorschau: 3-5 konkrete Punkte aus dem Artefakt als scanbares Element - genug Wert, dass der Post auch ohne Download traegt. Keine leeren Teaser.
3. Einordnung: Fuer wen das Artefakt gedacht ist und was es NICHT ist (Erwartungen ehrlich setzen). Ein eigener Gedanke, den der Quell-Post nicht hat.
4. Abschluss: Genau EIN Kommentar-CTA mit dem Keyword aus dem LEAD-MAGNET-ASSET (z.B. "Kommentiere KEYWORD, ich schicke es dir"). Kein DM-CTA daneben, kein kuenstlicher Zeitdruck, keine Follower-Bedingung.""",
        "en": """Post structure (without labeling it):
1. Hook (1-2 sentences): the problem the LEAD MAGNET ASSET below solves - from practice, not ad copy. Decides whether anyone reads on.
2. Substance preview: 3-5 concrete points from the artifact as the scannable element - enough value that the post stands without the download. No empty teasers.
3. Placement: who the artifact is for and what it is NOT (set expectations honestly). One original thought the source post does not have.
4. Close: exactly ONE comment CTA using the keyword from the LEAD MAGNET ASSET (e.g. "Comment KEYWORD and I'll send it over"). No DM CTA next to it, no fake scarcity, no follow-gate.""",
    },
    "Offer": {
        "de": """Post-Struktur (ohne explizite Benennung):
1. Hook (1-2 Saetze): Das Ergebnis, das das OFFER-ASSET unten verspricht, verankert im Problem der Zielgruppe. Kein Marktschreier-Ton. Entscheidet ob jemand weiterliest.
2. Passung: Fuer wen das Angebot gebaut ist (2-3 harte Fit-Kriterien) und fuer wen explizit nicht. Ehrlichkeit ist der Differenzierer.
3. Inhalt: Was konkret drinsteckt - 3-4 Punkte als scanbares Artefakt, Ablauf oder Bestandteile. Ein eigener Gedanke, warum JETZT der richtige Zeitpunkt ist (Markt-Logik, kein Druck).
4. Abschluss: Genau EIN CTA, woertlich aus dem OFFER-ASSET (DM oder Discovery-Call). Kein kuenstlicher Zeitdruck, keine erfundene Verknappung, keine Fake-Slots. Preise nur wenn im Asset genannt.""",
        "en": """Post structure (without labeling it):
1. Hook (1-2 sentences): the outcome the OFFER ASSET below promises, anchored in the audience's problem. No carnival-barker tone. Decides whether anyone reads on.
2. Fit: who the offer is built for (2-3 hard fit criteria) and who it is explicitly not for. Honesty is the differentiator.
3. Contents: what is concretely inside - 3-4 points as the scannable artifact, sequence or components. One original thought on why NOW is the right time (market logic, no pressure).
4. Close: exactly ONE CTA, taken verbatim from the OFFER ASSET (DM or discovery call). No fake scarcity, no invented urgency, no fake slots. Pricing only if the asset states it.""",
    },
```

(The existing `apply_tokens` re-mapping loop right below the dict handles the new `[[COMPARISON_SUBJECT_*]]` tokens automatically.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_format_structures.py tests/ -q`
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add tools/post_scorer.py tests/test_format_structures.py
git commit -m "feat: six new matrix format structure blocks (Comparison/Method/CaseProof/Debate/Magnet/Offer)"
```

---

### Task 6: `pick_format` with dynamic candidates

**Files:**
- Modify: `tools/post_scorer.py` (`VALID_FORMATS`, `PICK_FORMAT_PROMPT`, `pick_format`, lines ~446-502)
- Modify: `tests/test_pick_format.py`

**Interfaces:**
- Consumes: Task 5 (`FORMAT_STRUCTURES` keys)
- Produces: `pick_format(post: dict, recent_formats: list[str], candidates: list[str] | None = None) -> str`
  - `candidates=None` -> legacy behavior over `VALID_FORMATS` (unchanged 4-tuple)
  - `len(candidates) == 1` -> returns it WITHOUT an API call, even if it equals the most recent format (a mandatory quota box beats anti-repeat)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_pick_format.py`:

```python
def test_single_candidate_skips_llm_and_beats_anti_repeat():
    c = MagicMock()  # must not be called
    with patch.object(post_scorer, "client", c):
        assert post_scorer.pick_format(POST, ["CaseProof"], candidates=["CaseProof"]) == "CaseProof"
    c.messages.create.assert_not_called()


def test_candidates_restrict_choice():
    with patch.object(post_scorer, "client", _mock_client("Opinion")):
        result = post_scorer.pick_format(POST, [], candidates=["POV", "Signature"])
    assert result in ("POV", "Signature")  # Opinion not offered


def test_candidate_prompt_lists_only_candidates():
    c = _mock_client("POV")
    with patch.object(post_scorer, "client", c):
        post_scorer.pick_format(POST, [], candidates=["POV", "Signature"])
    prompt = c.messages.create.call_args.kwargs["messages"][0]["content"]
    assert "POV" in prompt and "Signature" in prompt and "Opinion" not in prompt
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_pick_format.py -q`
Expected: FAIL with `TypeError: pick_format() got an unexpected keyword argument 'candidates'`

- [ ] **Step 3: Implement**

In `tools/post_scorer.py` replace the `PICK_FORMAT_PROMPT` constant and `pick_format` with:

```python
# Kurzbeschreibung je Format fuer den Auswahl-Prompt.
FORMAT_PICK_DESCRIPTIONS = {
    "Opinion": "kontroverse These gegen eine gaengige Praxis.",
    "POV": "eine strukturierte Denk-Linse / ein Framework.",
    "Signature": '"Glaube vs. Realitaet" - verbreitete Annahme gegen das was wirklich zaehlt.',
    "Story": "eine konkrete Szene oder Anekdote aus der Praxis, erzaehlend statt Liste.",
    "Comparison": "Entscheidungshilfe: harte Kriterien und Red Flags fuer eine Auswahl.",
    "Method": "Schritt-fuer-Schritt-Methode mit dem typischen Stolperstein.",
    "CaseProof": "echtes Kundenergebnis, getragen von einer belegten Zahl.",
    "Debate": "polarisierende Entweder-Oder-These, die explizit zur Antwort auffordert.",
    "Magnet": "wertvolles Artefakt mit Kommentar-CTA.",
    "Offer": "konkretes Angebot mit ehrlichem naechsten Schritt.",
}

PICK_FORMAT_PROMPT = """Du waehlst das Post-Format fuer einen Recycling-Post.

Verfuegbare Formate:
{format_menu}

QUELL-POST:
{post_text}

{recent_section}

Regeln:
- Waehle das Format das am besten zum Thema des Quell-Posts passt.
- Das zuletzt genutzte Format ist verboten (nie zweimal hintereinander).
- Antworte mit EINEM Wort: {format_names}. Nichts sonst."""


def pick_format(post: dict, recent_formats: list[str],
                candidates: list[str] | None = None) -> str:
    """Waehlt das Format unter den Kandidaten: bester Topic-Fit, aber nie das
    zuletzt genutzte Format. candidates=None -> die 4 Legacy-Formate.
    Genau EIN Kandidat (Pflicht-Box) -> direkt zurueck, ohne API-Call und
    ohne Anti-Repeat (Quota schlaegt Wiederholungs-Regel).
    Faellt deterministisch zurueck und wirft nie."""
    candidates = list(candidates) if candidates else list(VALID_FORMATS)
    if len(candidates) == 1:
        return candidates[0]

    recent_formats = [f for f in recent_formats if f]
    most_recent = recent_formats[0] if recent_formats else None

    if recent_formats:
        recent_section = (
            f"Zuletzt genutzte Formate (neuestes zuerst): {', '.join(recent_formats)}. "
            f"VERBOTEN ist: {most_recent}."
        )
    else:
        recent_section = "Zuletzt genutzte Formate: keine."

    format_menu = "\n".join(
        f"- {f}: {FORMAT_PICK_DESCRIPTIONS.get(f, '')}" for f in candidates
    )
    try:
        prompt = PICK_FORMAT_PROMPT.format(
            format_menu=format_menu,
            post_text=post["post_text"][:3000],
            recent_section=recent_section,
            format_names=", ".join(candidates),
        )
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            messages=[{"role": "user", "content": prompt}],
        )
        choice = response.content[0].text.strip()
        for f in candidates:
            if f.lower() in choice.lower() and f != most_recent:
                return f
    except Exception as e:
        print(f"  Format-Pick fehlgeschlagen, Fallback: {e}")

    for f in candidates:
        if f != most_recent:
            return f
    return candidates[0]
```

`VALID_FORMATS = ("Opinion", "POV", "Signature", "Story")` stays as is.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_pick_format.py -q`
Expected: all pass (existing 5 + new 3)

- [ ] **Step 5: Commit**

```bash
git add tools/post_scorer.py tests/test_pick_format.py
git commit -m "feat: pick_format accepts box-restricted candidate lists"
```

---

### Task 7: Box-fit re-rank of the scored pool

**Files:**
- Modify: `tools/post_scorer.py` (append near `pick_format`)
- Create: `tests/test_rank_box_fit.py`

**Interfaces:**
- Consumes: Task 1 (`BOX_FORMATS` naming), Task 6 style (mocked `client`)
- Produces: `rank_box_fit(scored_posts: list[dict], box: tuple[str, str], formats: list[str], min_fit: int = 6) -> int | None`
  - Returns the index (into `scored_posts`) of the best-fitting post with fit >= `min_fit`, else `None`. Any API/parse failure -> `None`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_rank_box_fit.py`:

```python
"""Tests for the box-fit re-rank. The anthropic client is mocked."""
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import post_scorer

POSTS = [
    {"influencer": "A", "post_text": "How to compare GTM agencies."},
    {"influencer": "B", "post_text": "My morning routine."},
    {"influencer": "C", "post_text": "Buy vs build for outbound."},
]
BOX = ("Perspective", "Selection")


def _mock(reply):
    resp = MagicMock()
    resp.content = [MagicMock(text=reply)]
    c = MagicMock()
    c.messages.create.return_value = resp
    return c


def test_picks_highest_fit_at_or_above_threshold():
    reply = '[{"index": 0, "fit": 7}, {"index": 1, "fit": 2}, {"index": 2, "fit": 9}]'
    with patch.object(post_scorer, "client", _mock(reply)):
        assert post_scorer.rank_box_fit(POSTS, BOX, ["Comparison"]) == 2


def test_returns_none_when_nothing_reaches_threshold():
    reply = '[{"index": 0, "fit": 5}, {"index": 1, "fit": 1}, {"index": 2, "fit": 4}]'
    with patch.object(post_scorer, "client", _mock(reply)):
        assert post_scorer.rank_box_fit(POSTS, BOX, ["Comparison"]) is None


def test_returns_none_on_api_error():
    c = MagicMock()
    c.messages.create.side_effect = RuntimeError("down")
    with patch.object(post_scorer, "client", c):
        assert post_scorer.rank_box_fit(POSTS, BOX, ["Comparison"]) is None


def test_returns_none_on_garbage_json():
    with patch.object(post_scorer, "client", _mock("not json")):
        assert post_scorer.rank_box_fit(POSTS, BOX, ["Comparison"]) is None


def test_ignores_out_of_range_indices():
    reply = '[{"index": 99, "fit": 10}, {"index": 1, "fit": 8}]'
    with patch.object(post_scorer, "client", _mock(reply)):
        assert post_scorer.rank_box_fit(POSTS, BOX, ["Comparison"]) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_rank_box_fit.py -q`
Expected: FAIL with `AttributeError: ... 'rank_box_fit'`

- [ ] **Step 3: Implement**

Append to `tools/post_scorer.py`:

```python
RANK_BOX_FIT_PROMPT = """Du prueftst, welcher Quell-Post am besten ein bestimmtes Content-Format tragen kann.

ZIEL-BOX: {job} x {stage}
ZIEL-FORMAT(E): {formats} - {format_desc}

KANDIDATEN (nummeriert):
{numbered_posts}

Bewerte je Kandidat mit fit 0-10: Wie gut laesst sich aus DIESEM Quell-Post ein Post im Ziel-Format machen? 10 = der Quell-Post liefert die Struktur praktisch mit, 0 = passt gar nicht.

Antworte NUR mit validem JSON (kein Markdown):
[{{"index": 0, "fit": X}}, {{"index": 1, "fit": X}}, ...]"""


def rank_box_fit(scored_posts: list, box, formats: list, min_fit: int = 6):
    """Re-rankt die Top-Kandidaten auf Tauglichkeit fuer die Pflicht-Box.
    Gibt den Index des besten Posts mit fit >= min_fit zurueck, sonst None.
    Jeder Fehler -> None (Run faellt auf freien Best-Fit zurueck)."""
    if not scored_posts:
        return None
    numbered = "\n".join(
        f"[{i}] ({p['influencer']}) {p['post_text'][:400]}"
        for i, p in enumerate(scored_posts)
    )
    try:
        prompt = RANK_BOX_FIT_PROMPT.format(
            job=box[0], stage=box[1],
            formats=", ".join(formats),
            format_desc=" / ".join(FORMAT_PICK_DESCRIPTIONS.get(f, "") for f in formats),
            numbered_posts=numbered,
        )
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        ranking = json.loads(raw)
        best_index, best_fit = None, min_fit - 1
        for entry in ranking:
            idx, fit = int(entry["index"]), int(entry["fit"])
            if 0 <= idx < len(scored_posts) and fit > best_fit:
                best_index, best_fit = idx, fit
        return best_index
    except Exception as e:
        print(f"  Box-Fit-Rank fehlgeschlagen (Fallback: freier Run): {e}")
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_rank_box_fit.py -q`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add tools/post_scorer.py tests/test_rank_box_fit.py
git commit -m "feat: box-fit re-rank of scored pool for mandatory quota boxes"
```

---

### Task 8: Persona pick + persona/asset prompt blocks + generation params

**Files:**
- Modify: `tools/post_scorer.py` (persona pick, block builders, `DACH_POST_PROMPT`/`EN_POST_PROMPT` placeholders, `_format_prompts`, `generate_post_and_image_prompt`)
- Create: `tests/test_persona_and_assets.py`

**Interfaces:**
- Consumes: Task 4 (`CONTENT_PERSONAS` shape), Task 3 (`asset_for_format` output shape)
- Produces:
  - `pick_persona(post: dict, cfg, recent_personas: list[str]) -> dict | None` (None when client has no personas)
  - `persona_block(persona: dict | None, lang: str) -> str` (`lang` in {"de", "en"}; "" for None)
  - `assets_block(post_format: str, asset: dict | None, lang: str) -> str` ("" for None)
  - `_format_prompts(post, post_format, recent_infographic_types=None, assets_de="", assets_en="", persona_de="", persona_en="")`
  - `generate_post_and_image_prompt(post, post_format="Opinion", recent_infographic_types=None, assets_de="", assets_en="", persona_de="", persona_en="")` (same 6-tuple return as today)

- [ ] **Step 1: Write the failing tests**

Create `tests/test_persona_and_assets.py`:

```python
"""Persona lens + asset injection into the generation prompts. Client mocked."""
import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import post_scorer

POST = {"influencer": "Jane", "post_text": "Pipeline predictability post."}
PERSONAS = [
    {"id": "founder-ceo", "label": "Founder / CEO", "share": "dominant",
     "pains": "Pipeline nicht planbar", "kpis": "Meetings/Monat",
     "vocabulary_use": "Planbarkeit", "vocabulary_avoid": "MQL",
     "scene_de": "ein Founder im leeren Pipeline-Monat",
     "scene_en": "a founder in an empty-pipeline month", "cta_style": "discovery"},
    {"id": "cro-vp-sales", "label": "CRO / VP Sales", "share": "secondary",
     "pains": "Quote verfehlt", "kpis": "Coverage",
     "vocabulary_use": "Coverage", "vocabulary_avoid": "Brand-Sprech",
     "scene_de": "ein VP Sales im Forecast-Call",
     "scene_en": "a VP of sales in a forecast call", "cta_style": "discovery"},
]
CFG = SimpleNamespace(CONTENT_PERSONAS=PERSONAS)


def _mock(reply):
    resp = MagicMock()
    resp.content = [MagicMock(text=reply)]
    c = MagicMock()
    c.messages.create.return_value = resp
    return c


def test_pick_persona_none_without_personas():
    assert post_scorer.pick_persona(POST, SimpleNamespace(), []) is None
    assert post_scorer.pick_persona(POST, SimpleNamespace(CONTENT_PERSONAS=[]), []) is None


def test_pick_persona_llm_choice():
    with patch.object(post_scorer, "client", _mock("cro-vp-sales")):
        assert post_scorer.pick_persona(POST, CFG, [])["id"] == "cro-vp-sales"


def test_pick_persona_secondary_never_twice_in_a_row():
    with patch.object(post_scorer, "client", _mock("cro-vp-sales")):
        chosen = post_scorer.pick_persona(POST, CFG, ["cro-vp-sales"])
    assert chosen["id"] == "founder-ceo"  # falls back to dominant


def test_pick_persona_api_error_returns_dominant():
    c = MagicMock()
    c.messages.create.side_effect = RuntimeError("down")
    with patch.object(post_scorer, "client", c):
        assert post_scorer.pick_persona(POST, CFG, [])["id"] == "founder-ceo"


def test_persona_block_renders_language_specific_scene():
    de = post_scorer.persona_block(PERSONAS[0], "de")
    en = post_scorer.persona_block(PERSONAS[0], "en")
    assert "ZIEL-PERSONA" in de and "leeren Pipeline-Monat" in de
    assert "TARGET PERSONA" in en and "empty-pipeline month" in en
    assert post_scorer.persona_block(None, "de") == ""


def test_assets_block_caseproof_pins_metric():
    asset = {"id": "case-a", "claim": "Outbound-System", "metric": "12 Meetings in 6 Wochen",
             "context": "freigegeben"}
    de = post_scorer.assets_block("CaseProof", asset, "de")
    en = post_scorer.assets_block("CaseProof", asset, "en")
    assert "CASE-ASSET" in de and "12 Meetings in 6 Wochen" in de
    assert "CASE ASSET" in en
    assert post_scorer.assets_block("CaseProof", None, "de") == ""
    assert post_scorer.assets_block("Opinion", asset, "de") == ""


def test_format_prompts_inject_persona_and_assets():
    asset = {"id": "case-a", "metric": "12 Meetings in 6 Wochen"}
    de, en = post_scorer._format_prompts(
        POST, "CaseProof",
        assets_de=post_scorer.assets_block("CaseProof", asset, "de"),
        assets_en=post_scorer.assets_block("CaseProof", asset, "en"),
        persona_de=post_scorer.persona_block(PERSONAS[0], "de"),
        persona_en=post_scorer.persona_block(PERSONAS[0], "en"),
    )
    assert "12 Meetings in 6 Wochen" in de and "ZIEL-PERSONA" in de
    assert "12 Meetings in 6 Wochen" in en and "TARGET PERSONA" in en


def test_format_prompts_default_empty_blocks():
    de, en = post_scorer._format_prompts(POST, "Opinion")
    assert "ZIEL-PERSONA" not in de and "CASE-ASSET" not in de
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_persona_and_assets.py -q`
Expected: FAIL with `AttributeError: ... 'pick_persona'`

- [ ] **Step 3: Implement**

3a. In `tools/post_scorer.py`, add `{persona_block}` and `{assets_block}` to BOTH generation templates:

In `DACH_POST_PROMPT`, directly after the `KONTEXT:\n{context}` block insert a line:

```
{persona_block}
```

and directly BEFORE `{structure_block}` insert:

```
{assets_block}
```

Mirror in `EN_POST_PROMPT` (after `CONTEXT:\n{context}` and before `{structure_block}`).

3b. Append the builders:

```python
PERSONA_BLOCK_DE = """ZIEL-PERSONA fuer diesen Post (genau EINE Persona, deren Wertachse nie mit einer anderen mischen):
- Rolle: {label}
- Schmerzpunkte: {pains}
- KPIs die zaehlen: {kpis}
- Vokabular nutzen: {vocabulary_use}
- Vokabular meiden: {vocabulary_avoid}
- Typische Szene: {scene}"""

PERSONA_BLOCK_EN = """TARGET PERSONA for this post (exactly ONE persona, never mix its value axis with another):
- Role: {label}
- Pains: {pains}
- KPIs that matter: {kpis}
- Vocabulary to use: {vocabulary_use}
- Vocabulary to avoid: {vocabulary_avoid}
- Typical scene: {scene}"""


def persona_block(persona, lang: str) -> str:
    """Persona-Linse fuer den Generierungs-Prompt. None/leer -> ""."""
    if not persona:
        return ""
    template = PERSONA_BLOCK_DE if lang == "de" else PERSONA_BLOCK_EN
    return template.format(
        label=persona.get("label", ""),
        pains=persona.get("pains", ""),
        kpis=persona.get("kpis", ""),
        vocabulary_use=persona.get("vocabulary_use", ""),
        vocabulary_avoid=persona.get("vocabulary_avoid", ""),
        scene=persona.get("scene_de" if lang == "de" else "scene_en", ""),
    )


_ASSET_BLOCK_HEADERS = {
    "CaseProof": ("CASE-ASSET (einzige erlaubte Zahlenquelle, Zahlen woertlich uebernehmen)",
                  "CASE ASSET (the only allowed source of numbers, use them verbatim)"),
    "Magnet": ("LEAD-MAGNET-ASSET (dieses Artefakt bewirbt der Post, CTA-Keyword woertlich nutzen)",
               "LEAD MAGNET ASSET (the artifact this post promotes, use the CTA keyword verbatim)"),
    "Offer": ("OFFER-ASSET (dieses Angebot bewirbt der Post, CTA woertlich uebernehmen)",
              "OFFER ASSET (the offer this post promotes, use the CTA verbatim)"),
}


def assets_block(post_format: str, asset, lang: str) -> str:
    """Asset-Whitelist-Block fuer CaseProof/Magnet/Offer. Sonst ""."""
    if not asset or post_format not in _ASSET_BLOCK_HEADERS:
        return ""
    header = _ASSET_BLOCK_HEADERS[post_format][0 if lang == "de" else 1]
    lines = [f"- {k}: {v}" for k, v in asset.items() if isinstance(v, str) and v]
    return header + ":\n" + "\n".join(lines)


PICK_PERSONA_PROMPT = """Du waehlst die Ziel-Persona fuer einen LinkedIn-Post.

PERSONAS:
{persona_menu}

QUELL-POST:
{post_text}

Regel: Waehle die Persona, deren Schmerzpunkte der Quell-Post am direktesten trifft. Im Zweifel: {dominant_id}.
Antworte NUR mit der id, nichts sonst."""


def pick_persona(post: dict, cfg, recent_personas: list):
    """v1-Persona-Wahl: Best-Fit zum Quell-Post, im Zweifel dominante Persona,
    dieselbe Sekundaer-Persona nie zweimal hintereinander. Wirft nie.
    Mandant ohne CONTENT_PERSONAS -> None (statische Audience-Tokens gelten)."""
    personas = getattr(cfg, "CONTENT_PERSONAS", None) or []
    if not personas:
        return None
    by_id = {p["id"]: p for p in personas}
    dominant = next((p for p in personas if p.get("share") == "dominant"), personas[0])
    if len(personas) == 1:
        return dominant

    choice_id = dominant["id"]
    try:
        menu = "\n".join(
            f"- {p['id']}: {p['label']} | Schmerzpunkte: {p['pains']}" for p in personas
        )
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=20,
            messages=[{"role": "user", "content": PICK_PERSONA_PROMPT.format(
                persona_menu=menu,
                post_text=post["post_text"][:2000],
                dominant_id=dominant["id"],
            )}],
        )
        raw = response.content[0].text.strip().lower()
        for pid in by_id:
            if pid in raw:
                choice_id = pid
                break
    except Exception as e:
        print(f"  Persona-Pick fehlgeschlagen, Fallback dominant: {e}")

    chosen = by_id[choice_id]
    # Sekundaer-Persona nie zweimal in Folge.
    if (chosen["id"] != dominant["id"] and recent_personas
            and recent_personas[0] == chosen["id"]):
        return dominant
    return chosen
```

3c. Extend `_format_prompts` and `generate_post_and_image_prompt` signatures — both `.format(...)` calls gain the new kwargs:

```python
def _format_prompts(post: dict, post_format: str = "Opinion",
                    recent_infographic_types=None,
                    assets_de: str = "", assets_en: str = "",
                    persona_de: str = "", persona_en: str = "") -> tuple[str, str]:
    """Pure builder: returns (de_prompt, en_prompt) with the format structure,
    the infographic anti-repeat line, and optional persona/asset blocks
    injected. Unknown format keys fall back to Opinion. No API calls."""
    structures = FORMAT_STRUCTURES.get(post_format, FORMAT_STRUCTURES["Opinion"])
    de_recent, en_recent = _recent_types_lines(recent_infographic_types)
    de = DACH_POST_PROMPT.format(
        context=CLIENT_CONTEXT,
        influencer=post["influencer"],
        post_text=post["post_text"][:3000],
        structure_block=structures["de"],
        recent_types_line=de_recent,
        persona_block=persona_de,
        assets_block=assets_de,
    )
    en = EN_POST_PROMPT.format(
        context=CLIENT_CONTEXT,
        influencer=post["influencer"],
        post_text=post["post_text"][:3000],
        structure_block=structures["en"],
        recent_types_line=en_recent,
        persona_block=persona_en,
        assets_block=assets_en,
    )
    return de, en
```

In `generate_post_and_image_prompt`, add the same four kwargs and pass them through to `_format_prompts` (return tuple unchanged):

```python
def generate_post_and_image_prompt(post: dict, post_format: str = "Opinion",
                                   recent_infographic_types=None,
                                   assets_de: str = "", assets_en: str = "",
                                   persona_de: str = "", persona_en: str = "") -> tuple[str, str, str, str, str, str]:
    ...
    de_prompt, en_prompt = _format_prompts(
        post, post_format, recent_infographic_types,
        assets_de=assets_de, assets_en=assets_en,
        persona_de=persona_de, persona_en=persona_en,
    )
    # rest unchanged
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_persona_and_assets.py tests/test_format_structures.py tests/test_parse_generation.py -q`
Expected: all pass

- [ ] **Step 5: Run full suite (template placeholders touch every prompt path)**

Run: `python -m pytest tests/ -q`
Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add tools/post_scorer.py tests/test_persona_and_assets.py
git commit -m "feat: persona lens + asset whitelist blocks in generation prompts"
```

---

### Task 9: Archetype rankings for the new formats

**Files:**
- Modify: `tools/image_archetypes.py` (`select_archetype`, around line 142-170)
- Modify: `tests/test_image_archetypes.py` (append)

**Interfaces:**
- Consumes: Task 5 format names
- Produces: unchanged signature; new formats produce sensible image candidates instead of falling straight to the generic default

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_image_archetypes.py` (match the file's existing call style — inspect its existing `select_archetype` tests and mirror the argument pattern):

```python
def test_comparison_prefers_two_panel_contrast():
    assert select_archetype(
        post_format="Comparison", infographic_type="", layers_count=0,
        has_metaphor=False, has_stat=False, recent_archetypes=[],
    ) == "two_panel_contrast"


def test_caseproof_with_stat_prefers_stat_hero():
    assert select_archetype(
        post_format="CaseProof", infographic_type="", layers_count=0,
        has_metaphor=False, has_stat=True, recent_archetypes=[],
    ) == "stat_hero"


def test_debate_and_offer_prefer_statement_card():
    for fmt in ("Debate", "Offer"):
        assert select_archetype(
            post_format=fmt, infographic_type="", layers_count=0,
            has_metaphor=False, has_stat=False, recent_archetypes=[],
        ) == "statement_card"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_image_archetypes.py -q`
Expected: new tests FAIL (fall through to default archetype)

- [ ] **Step 3: Implement**

In `select_archetype`, extend the ranked-append section (after the existing `elif post_format == "POV":` branch) with:

```python
    elif post_format == "Comparison":
        ranked += ["two_panel_contrast", "structured_infographic"]
    elif post_format == "CaseProof":
        ranked += ["stat_hero", "editorial_cover"]
    elif post_format == "Method":
        ranked += ["isometric_scene", "structured_infographic"]
    elif post_format in ("Debate", "Offer"):
        ranked += ["statement_card", "editorial_cover"]
    elif post_format == "Magnet":
        ranked += ["structured_infographic", "statement_card"]
```

NOTE for the implementer: `ranked` already contains `stat_hero` when
`has_stat` is true and `two_panel_contrast` for Signature/contrast types —
the dedupe/anti-repeat logic downstream already handles duplicates. Keep the
existing branches untouched.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_image_archetypes.py -q`
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add tools/image_archetypes.py tests/test_image_archetypes.py
git commit -m "feat: image archetype preferences for the six new formats"
```

---

### Task 10: Notion — new properties, getters, seed script

**Files:**
- Modify: `tools/notion_db.py` (`update_with_draft` + new getters)
- Create: `scripts/add_matrix_properties.py`
- Create: `tests/test_notion_db_matrix.py`

**Interfaces:**
- Consumes: nothing new (mirrors existing patterns in the same file)
- Produces:
  - `update_with_draft(..., matrix_job: str = "", matrix_stage: str = "", persona: str = "", asset_id: str = "")`
  - `get_recent_boxes(limit: int = 10) -> list[tuple[str, str]]`
  - `get_recent_assets(limit: int = 5) -> list[str]`
  - `get_recent_personas(limit: int = 2) -> list[str]`
  - Notion select properties: `Matrix-Job`, `Matrix-Stage`, `Persona`, `Asset`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_notion_db_matrix.py` (mirror the mocking style used in `tests/test_notion_db_formats.py` — inspect that file first and reuse its `_notion_request` patch pattern; the code below assumes the standard `patch.object(notion_db, "_notion_request", ...)` approach):

```python
"""Matrix/persona/asset Notion plumbing. HTTP mocked via _notion_request."""
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import notion_db


def _query_response(pages):
    resp = MagicMock()
    resp.json.return_value = {"results": pages}
    resp.raise_for_status.return_value = None
    return resp


def _page(job=None, stage=None, persona=None, asset=None):
    props = {}
    if job:
        props["Matrix-Job"] = {"select": {"name": job}}
    if stage:
        props["Matrix-Stage"] = {"select": {"name": stage}}
    if persona:
        props["Persona"] = {"select": {"name": persona}}
    if asset:
        props["Asset"] = {"select": {"name": asset}}
    return {"properties": props}


def test_get_recent_boxes_pairs_job_and_stage():
    pages = [_page("Perspective", "Awareness"), _page("Proof", "Selection"),
             _page(job="Perspective")]  # incomplete row is skipped
    with patch.object(notion_db, "_notion_request", return_value=_query_response(pages)):
        boxes = notion_db.get_recent_boxes()
    assert boxes == [("Perspective", "Awareness"), ("Proof", "Selection")]


def test_get_recent_assets_and_personas():
    pages = [_page(asset="case-a", persona="founder-ceo"), _page(asset="case-b")]
    with patch.object(notion_db, "_notion_request", return_value=_query_response(pages)):
        assert notion_db.get_recent_assets() == ["case-a", "case-b"]
        assert notion_db.get_recent_personas() == ["founder-ceo"]


def test_update_with_draft_writes_matrix_properties_nonfatal():
    calls = []

    def fake_request(method, url, **kwargs):
        calls.append(kwargs.get("json", {}))
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        resp.json.return_value = {}
        return resp

    with patch.object(notion_db, "_notion_request", side_effect=fake_request), \
         patch.object(notion_db, "_fire_review_webhook", create=True) as _:
        notion_db.update_with_draft(
            page_id="p1", linkedin_draft="text", image_prompt="", image_url="",
            matrix_job="Proof", matrix_stage="Selection",
            persona="founder-ceo", asset_id="case-a",
        )
    prop_patches = [c.get("properties", {}) for c in calls]
    flat = {k: v for props in prop_patches for k, v in props.items()}
    assert flat["Matrix-Job"]["select"]["name"] == "Proof"
    assert flat["Matrix-Stage"]["select"]["name"] == "Selection"
    assert flat["Persona"]["select"]["name"] == "founder-ceo"
    assert flat["Asset"]["select"]["name"] == "case-a"
```

NOTE for the implementer: `update_with_draft` ends by firing the Make
webhook. Look at how `tests/test_notion_db_formats.py` neutralizes it (env
var unset makes it a no-op, or it patches the function) and copy that exact
approach instead of the `_fire_review_webhook` patch sketch above if the
name differs. Do not let the test hit the network.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_notion_db_matrix.py -q`
Expected: FAIL with `AttributeError: ... 'get_recent_boxes'`

- [ ] **Step 3: Implement in `tools/notion_db.py`**

3a. Add a non-fatal select-patch helper (place it right above `update_with_draft`):

```python
def _patch_select_nonfatal(page_id: str, prop: str, value: str) -> None:
    """Setzt eine Select-Property separat + non-fatal: fehlt die Property in
    Notion (noch), darf das den kritischen Status-PATCH nicht killen."""
    if not value:
        return
    try:
        r = _notion_request(
            "PATCH",
            f"{NOTION_API}/pages/{page_id}",
            headers=_headers(),
            json={"properties": {prop: {"select": {"name": value}}}},
        )
        r.raise_for_status()
        print(f"  {prop}-Property gesetzt: {value}", flush=True)
    except Exception as e:
        print(f"  {prop}-Property fehlgeschlagen (nicht kritisch): {e}", flush=True)
```

3b. Extend the `update_with_draft` signature with `matrix_job: str = ""`,
`matrix_stage: str = ""`, `persona: str = ""`, `asset_id: str = ""` and add,
directly after the existing `archetype` block (before the webhook section):

```python
    # Matrix-Tracking (Quota-Fenster des naechsten Runs) + Persona/Asset-Anti-Repeat.
    _patch_select_nonfatal(page_id, "Matrix-Job", matrix_job)
    _patch_select_nonfatal(page_id, "Matrix-Stage", matrix_stage)
    _patch_select_nonfatal(page_id, "Persona", persona)
    _patch_select_nonfatal(page_id, "Asset", asset_id)
```

(Leave the three existing inline blocks for Format / Infografik-Typ /
Bild-Variante untouched — minimal blast radius.)

3c. Add the getters after `get_recent_archetypes` (copy its query payload —
same status filter, `last_edited_time` sort):

```python
def get_recent_boxes(limit: int = 10) -> list:
    """(Matrix-Job, Matrix-Stage)-Paare der letzten N Eintraege, neuestes
    zuerst. Eintraege ohne beide Properties werden uebersprungen."""
    payload = {
        "filter": {
            "or": [
                {"property": "Status", "select": {"equals": "Posted"}},
                {"property": "Status", "select": {"equals": "Approved"}},
                {"property": "Status", "select": {"equals": "Ready to Review"}},
            ]
        },
        "sorts": [{"timestamp": "last_edited_time", "direction": "descending"}],
        "page_size": limit,
    }
    resp = _notion_request(
        "POST",
        f"{NOTION_API}/databases/{NOTION_DB_ID}/query",
        headers=_headers(),
        json=payload,
    )
    resp.raise_for_status()
    boxes = []
    for page in resp.json().get("results", []):
        props = page.get("properties", {})
        job = (props.get("Matrix-Job", {}).get("select") or {}).get("name")
        stage = (props.get("Matrix-Stage", {}).get("select") or {}).get("name")
        if job and stage:
            boxes.append((job, stage))
    return boxes


def _get_recent_select(prop: str, limit: int) -> list:
    """Werte einer Select-Property der letzten N Eintraege (neuestes zuerst)."""
    payload = {
        "filter": {
            "or": [
                {"property": "Status", "select": {"equals": "Posted"}},
                {"property": "Status", "select": {"equals": "Approved"}},
                {"property": "Status", "select": {"equals": "Ready to Review"}},
            ]
        },
        "sorts": [{"timestamp": "last_edited_time", "direction": "descending"}],
        "page_size": limit,
    }
    resp = _notion_request(
        "POST",
        f"{NOTION_API}/databases/{NOTION_DB_ID}/query",
        headers=_headers(),
        json=payload,
    )
    resp.raise_for_status()
    values = []
    for page in resp.json().get("results", []):
        name = (page.get("properties", {}).get(prop, {}).get("select") or {}).get("name")
        if name:
            values.append(name)
    return values


def get_recent_assets(limit: int = 5) -> list:
    """Asset-Ids der letzten N Eintraege (fuer das LRU-Asset-Anti-Repeat)."""
    return _get_recent_select("Asset", limit)


def get_recent_personas(limit: int = 2) -> list:
    """Persona-Ids der letzten N Eintraege (Sekundaer-Persona nie 2x in Folge)."""
    return _get_recent_select("Persona", limit)
```

3d. Create `scripts/add_matrix_properties.py` (pattern:
`scripts/add_format_property.py`):

```python
"""One-time idempotent: adds Matrix-Job / Matrix-Stage / Persona / Asset
select properties to the client's content DB. Persona/Asset options
auto-populate on first write. Run per tenant:
  PYTHONPATH="$(pwd)" python scripts/add_matrix_properties.py            # jolly
  CLIENT=lisocon PYTHONPATH="$(pwd)" python scripts/add_matrix_properties.py
Safe to run repeatedly."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools.notion_db import NOTION_API, NOTION_DB_ID, _headers, _notion_request

PROPERTIES = {
    "Matrix-Job": [
        {"name": "Perspective", "color": "blue"},
        {"name": "Proof", "color": "green"},
        {"name": "Promotion", "color": "orange"},
    ],
    "Matrix-Stage": [
        {"name": "Awareness", "color": "blue"},
        {"name": "Education", "color": "green"},
        {"name": "Selection", "color": "orange"},
    ],
    "Persona": [],  # options auto-create on first page write
    "Asset": [],    # options auto-create on first page write
}


def ensure_matrix_properties() -> None:
    r = _notion_request("GET", f"{NOTION_API}/databases/{NOTION_DB_ID}", headers=_headers())
    r.raise_for_status()
    existing = r.json().get("properties", {})
    to_add = {
        name: {"select": {"options": options}}
        for name, options in PROPERTIES.items()
        if name not in existing
    }
    if not to_add:
        print("All matrix properties already exist - nothing to do.")
        return
    r = _notion_request(
        "PATCH", f"{NOTION_API}/databases/{NOTION_DB_ID}", headers=_headers(),
        json={"properties": to_add},
    )
    r.raise_for_status()
    print(f"Created properties: {', '.join(to_add)}")


if __name__ == "__main__":
    ensure_matrix_properties()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_notion_db_matrix.py tests/test_notion_db_formats.py tests/test_notion_db_drafts.py -q`
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add tools/notion_db.py scripts/add_matrix_properties.py tests/test_notion_db_matrix.py
git commit -m "feat: Notion matrix/persona/asset properties, getters and seed script"
```

---

### Task 11: Wire everything into `run_research.py` + numbers-guard orchestration

**Files:**
- Modify: `run_research.py` (steps 4.4-7)
- Modify: `workflows/content_generation.md` (manual path rules)

**Interfaces:**
- Consumes: everything above — exact call signatures:
  - `content_matrix.pick_target_box(recent_boxes, _cfg)`, `formats_for_box`, `free_formats`, `asset_for_format`, `figures_ok`, `coverage_line`, `FORMAT_TO_BOX`
  - `post_scorer.rank_box_fit(scored[:10], target_box, box_formats)`
  - `post_scorer.pick_format(winner, recent_formats, candidates=...)`
  - `post_scorer.pick_persona(winner, _cfg, get_recent_personas())`
  - `post_scorer.persona_block/assets_block`
  - `notion_db.get_recent_boxes/get_recent_assets/get_recent_personas`
  - `update_with_draft(..., matrix_job=..., matrix_stage=..., persona=..., asset_id=...)`

There is no isolated unit test for this wiring (module does IO end-to-end);
correctness is carried by the unit-tested parts plus Step 4's import smoke
check and the observed live run. Keep the wiring thin — decisions stay in
the tested modules.

- [ ] **Step 1: Add imports**

In `run_research.py`, extend the import block:

```python
from tools.content_matrix import (
    FORMAT_TO_BOX,
    asset_for_format,
    coverage_line,
    figures_ok,
    formats_for_box,
    free_formats,
    pick_target_box,
)
```

and extend the two existing `from tools.notion_db import (...)` /
`from tools.post_scorer import (...)` blocks with
`get_recent_boxes, get_recent_assets, get_recent_personas` and
`rank_box_fit, pick_persona, persona_block, assets_block` respectively.

- [ ] **Step 2: Insert the target-box step (new Schritt 4.35, directly after the winner check in Schritt 4 and BEFORE the current "Schritt 4.5: Format waehlen" block)**

```python
    # Schritt 4.35: Matrix-Ziel-Box (Quota 50/30/20 + Selection-Floor + Promotion-Kappe).
    # Non-fatal: jeder Fehler -> freier Best-Fit-Run wie bisher.
    target_box = None
    try:
        recent_boxes = get_recent_boxes()
        print(f"  {coverage_line(recent_boxes, _cfg)}")
        target_box = pick_target_box(recent_boxes, _cfg)
    except Exception as e:
        print(f"  Matrix-Coverage laden fehlgeschlagen (nicht kritisch): {e}", file=sys.stderr)
    if target_box:
        print(f"  Pflicht-Box: {target_box[0]} x {target_box[1]}")
        box_formats = formats_for_box(target_box, _cfg)
        best_idx = rank_box_fit(scored[:10], target_box, box_formats)
        if best_idx is None:
            print("  Kein Quell-Post traegt die Pflicht-Box (Fit < 6) - Defizit bleibt offen, freier Run.")
            target_box = None
        else:
            winner = scored[:10][best_idx]
            print(f"  Box-Winner: {winner['influencer']} (Score: {winner['score']}/60)")
```

- [ ] **Step 3: Replace the format-pick line in Schritt 4.5**

Replace:

```python
    post_format = pick_format(winner, recent_formats)
```

with:

```python
    candidates = formats_for_box(target_box, _cfg) if target_box else free_formats(_cfg)
    post_format = pick_format(winner, recent_formats, candidates=candidates)
```

- [ ] **Step 4: Insert persona + asset resolution (directly after the format pick, before Schritt 4.6)**

```python
    # Persona-Linse (v1: Best-Fit + dominant-Fallback; leerer Block -> None).
    persona = None
    try:
        persona = pick_persona(winner, _cfg, get_recent_personas())
    except Exception as e:
        print(f"  Persona-Pick fehlgeschlagen (nicht kritisch): {e}", file=sys.stderr)
    if persona:
        print(f"  Persona: {persona['id']}")

    # Asset fuer CaseProof/Magnet/Offer (LRU). Whitelist-Guard garantiert:
    # asset-pflichtige Formate sind nur waehlbar, wenn der Block gefuellt ist.
    chosen_asset = None
    try:
        chosen_asset = asset_for_format(post_format, _cfg, get_recent_assets())
    except Exception as e:
        print(f"  Asset-Wahl fehlgeschlagen (nicht kritisch): {e}", file=sys.stderr)
    if chosen_asset:
        print(f"  Asset: {chosen_asset['id']}")
```

- [ ] **Step 5: Pass blocks into generation (Schritt 5) and add the numbers guard**

Replace the `generate_post_and_image_prompt(...)` call with:

```python
        linkedin_draft, en_draft, image_prompt, infographic_skeleton, sound_byte, kontext = generate_post_and_image_prompt(
            winner, post_format, recent_infographic_types=recent_infographic_types,
            assets_de=assets_block(post_format, chosen_asset, "de"),
            assets_en=assets_block(post_format, chosen_asset, "en"),
            persona_de=persona_block(persona, "de"),
            persona_en=persona_block(persona, "en"),
        )
```

Directly after the existing `en_draft` fallback block, add the guard:

```python
    # Zahlen-Guard (nur CaseProof): jede Einheiten-Zahl muss aus dem Asset
    # stammen. 1 Retry, danach Downgrade auf Method ohne Asset-Block.
    if post_format == "CaseProof" and chosen_asset:
        for attempt in ("retry", "downgrade"):
            if figures_ok(f"{linkedin_draft}\n{en_draft}", chosen_asset):
                break
            if attempt == "retry":
                print("  Zahlen-Guard verletzt - ein Retry.", file=sys.stderr)
                linkedin_draft, en_draft, image_prompt, infographic_skeleton, sound_byte, kontext = generate_post_and_image_prompt(
                    winner, post_format, recent_infographic_types=recent_infographic_types,
                    assets_de=assets_block(post_format, chosen_asset, "de"),
                    assets_en=assets_block(post_format, chosen_asset, "en"),
                    persona_de=persona_block(persona, "de"),
                    persona_en=persona_block(persona, "en"),
                )
            else:
                print("  Zahlen-Guard erneut verletzt - Downgrade auf Method.", file=sys.stderr)
                post_format = "Method"
                chosen_asset = None
                linkedin_draft, en_draft, image_prompt, infographic_skeleton, sound_byte, kontext = generate_post_and_image_prompt(
                    winner, post_format, recent_infographic_types=recent_infographic_types,
                    persona_de=persona_block(persona, "de"),
                    persona_en=persona_block(persona, "en"),
                )
        if not linkedin_draft:
            print("  FEHLER: Leerer Draft nach Guard-Behandlung.", file=sys.stderr)
            sys.exit(1)
```

- [ ] **Step 6: Write the classification in Schritt 7**

Extend the `update_with_draft(...)` call:

```python
        matrix_box = FORMAT_TO_BOX.get(post_format, ("", ""))
        update_with_draft(
            page_id=page_id,
            linkedin_draft=linkedin_draft,
            en_draft=en_draft,
            image_prompt=gen_prompt,
            image_url=image_url,
            title=winner.get("post_excerpt", "")[:60],
            influencer=winner["influencer"],
            image_failed=image_failed,
            image_error=image_error,
            infographic_skeleton=infographic_skeleton,
            post_format=post_format,
            infographic_type=infographic_type,
            archetype=gen_archetype,
            matrix_job=matrix_box[0],
            matrix_stage=matrix_box[1],
            persona=(persona or {}).get("id", ""),
            asset_id=(chosen_asset or {}).get("id", ""),
        )
```

- [ ] **Step 7: Update the manual path `workflows/content_generation.md`**

Add a new section after "## Trigger":

```markdown
## Content-Matrix-Regeln (Spec 2026-07-08, gelten auch fuer den manuellen Pfad)

- Jeder Post gehoert in genau EINE Matrix-Box (Job x Stage). Vor der Generierung
  Box + Format waehlen: Opinion (Perspective x Awareness), POV/Signature
  (Perspective x Education), Comparison (Perspective x Selection), Story
  (Proof x Awareness), Method (Proof x Education), CaseProof (Proof x Selection),
  Debate (Promotion x Awareness), Magnet (Promotion x Education), Offer
  (Promotion x Selection). Matrix-Job/Matrix-Stage-Properties in Notion setzen.
- Asset-Formate NUR mit Eintrag aus der Mandanten-Config: CaseProof braucht
  PROOF_ASSETS, Magnet LEAD_MAGNETS, Offer OFFERS. Jede Zahl mit Einheit
  (Prozent, Euro, x-fach) woertlich aus dem Asset — keine anderen Zahlen.
- CTA-Politik: Kein DM-/Angebots-CTA ausser in Magnet (genau ein Kommentar-CTA)
  und Offer (genau ein DM- oder Discovery-CTA). Kein kuenstlicher Zeitdruck.
- Genau EINE Content-Persona pro Post (CONTENT_PERSONAS des Mandanten),
  Wertachsen nie mischen. Persona-Property in Notion setzen.
- Promotion-Posts (Debate/Magnet/Offer) max. 2 von 10; Selection-Spalte
  mind. 2 von 10 (Quota macht das im Cron automatisch — manuell mitzaehlen).
```

- [ ] **Step 8: Import smoke check + full suite**

Run: `python -c "import run_research"` (from repo root)
Expected: no output, exit 0 (imports resolve; `load_client` defaults to jolly)

Run: `python -m pytest tests/ -q`
Expected: all pass

- [ ] **Step 9: Commit**

```bash
git add run_research.py workflows/content_generation.md
git commit -m "feat: wire matrix quota, persona lens, asset guard into daily pipeline"
```

---

### Task 12: Ship — suite, push (= deploy), Notion seed, verification

**Files:**
- No new files. Push + one-time scripts + live verification.

- [ ] **Step 1: Full suite, final**

Run: `python -m pytest tests/ -q`
Expected: all pass, 0 failures

- [ ] **Step 2: Push (THIS IS GO-LIVE — repo auto-deploys on master push)**

```bash
git pull --rebase && git push
```

Expected: push succeeds. (The daily pipeline also commits generated images to
master — if the push is rejected, rebase again.)

- [ ] **Step 3: Seed the Notion properties for both tenants**

```bash
PYTHONPATH="$(pwd)" python scripts/add_matrix_properties.py
CLIENT=lisocon PYTHONPATH="$(pwd)" python scripts/add_matrix_properties.py
```

Expected output per run: `Created properties: Matrix-Job, Matrix-Stage, Persona, Asset` (or "already exist" on re-run).

NOTE: needs `NOTION_TOKEN` (jolly) resp. `NOTION_TOKEN_LISOCON` + `NOTION_DB_ID` env from `.env` — run from the repo root where `.env` lives; `load_dotenv` in `tools/notion_db.py` picks it up. For lisocon also set the `NOTION_DB_ID` env the lisocon service uses (see `railway.lisocon.toml` / Railway service variables).

- [ ] **Step 4: Dry-run one pipeline pass locally against jolly (optional but recommended)**

```bash
PYTHONPATH="$(pwd)" python run_research.py
```

Expected in the log: a `Coverage (0 Posts): ...` line, `Matrix: aus` never
(jolly has MATRIX), no `Pflicht-Box` in the first runs (cold start < 5
classified posts), format picked from
`Opinion/POV/Signature/Story/Comparison/Method`, `Persona: founder-ceo` or
`cro-vp-sales`, Notion entry carries Matrix-Job/Matrix-Stage/Persona.
NOTE: this consumes one real scrape + generation (~$0.50) and writes one
real Notion entry — acceptable, it replaces that day's cron output. Skip if
the cron already ran today and Richard does not want a second entry.

- [ ] **Step 5: Report**

Summarize to Richard: what shipped, cold-start behavior (quota arms itself
after 5 classified posts), which boxes are live per tenant (jolly 6,
lisocon 7), and that CaseProof/Magnet/Offer for jolly unlock via
PROOF_ASSETS/OFFERS/LEAD_MAGNETS in `clients/jolly/config.py`.

---

## Self-Review (done at plan-writing time)

- Spec coverage: box model (T1), quota + cold start + cap (T2), asset LRU +
  numbers guard (T3), per-client MATRIX/assets/personas + policy whitelists
  (T4), 6 formats + CTA policy (T5), box-restricted format pick +
  quota-beats-anti-repeat (T6), top-10 re-rank fit>=6 with no-quality-
  sacrifice fallback (T7), persona lens v1 + prompt injection (T8), image
  archetypes for new formats (T9), Notion properties/getters/seed (T10),
  wiring + guard orchestration + manual-path rules (T11), deploy + seed +
  verification (T12). Persona quota / compatibility map: explicitly Phase 2
  (spec), not planned here.
- Placeholders: none; every code step carries full code. Two intentional
  "inspect the neighboring test file first" notes (T9 Step 1, T10 Step 1)
  direct the implementer to mirror existing call/mock patterns rather than
  guess — the target behavior and assertions are fully specified.
- Type consistency: `pick_target_box` consumes `list[tuple[str, str]]` from
  `get_recent_boxes` (T10 returns exactly that); `asset_for_format` returns
  the dict consumed by `assets_block`/`figures_ok`; `pick_persona` returns
  the dict consumed by `persona_block`; `update_with_draft` kwargs match the
  T11 call site.
