"""Bestandsleser und Bestandsbereinigung fuer den SWOT-Redaktionsplan.

Anlass (Richard 28.08.2026): 51 LinkedIn-Beitraege stehen als Entwurf im
Plan, geschrieben mit Prompt-Staenden vom 20. bis 27.08. Richard liest keine
Beitraege ("dafuer werde ich nicht bezahlt"). Der Bestand wird deshalb
maschinell gelesen (Task 2, --report) und bereinigt (Task 6, --write):
Leser plus Reparatur je Zeile, Restbefund leert den Text, der Normal-Lauf
fuellt nach. Spec: docs/superpowers/specs/2026-08-28-leser-gate-design.md.

Reine Funktionen hier, Netz und Modell im Runner run_review_backfill.py.
Der Modellaufruf wird als Funktion injiziert, damit Tests ohne Netz laufen.
"""
from tools import naturalness


def strip_cta(text: str, cta: str) -> str:
    """CTA-Zeile am Textende entfernen. Der Leser sieht sie nie; die
    Reparatur haengt sie hinterher wieder an."""
    t = (text or "").rstrip()
    if cta and t.endswith(cta):
        t = t[: -len(cta)].rstrip()
    return t


def plan_rows(rows: list[dict]) -> list[dict]:
    """Zeilen des Plans, die der Bestandslauf anfasst: Typ LinkedIn-Post,
    Status Entwurf, Post-Text vorhanden. Freigegebene Zeilen bleiben immer
    aussen vor (Zusage an den Kunden)."""
    from run_plan_fill import _date, _rt, _sel, _title
    out = []
    for r in rows:
        p = r["properties"]
        text = _rt(p, "Post-Text")
        if _sel(p, "Typ") != "LinkedIn-Post" or _sel(p, "Status") != "Entwurf" or not text:
            continue
        out.append({
            "page_id": r["id"], "titel": _title(p), "kanal": _sel(p, "Kanal"),
            "datum": _date(p), "kurz": _rt(p, "Kurzbeschreibung"),
            "text": text, "status": _sel(p, "Status"),
        })
    return out


def material_for(row: dict) -> str:
    return f"Thema: {row['titel']}\nKurzbeschreibung: {row['kurz']}"


def read_row(row: dict, cfg, read_fn) -> dict:
    """Leser ueber eine Zeile. read_fn(text, material, voice) liefert die
    Befundliste des Modells oder None (kein Urteil). Deterministische
    Befunde kommen immer dazu."""
    text = strip_cta(row["text"], getattr(cfg, "CTA_DE", ""))
    voice = getattr(cfg, "ACCOUNT_VOICES", {}).get(row["kanal"], "")
    llm = read_fn(text, material_for(row), voice)
    det = naturalness.deterministic_findings(text, voice)
    befunde = (llm or []) + det
    if llm is None and not det:
        verdikt = "kein_urteil"
    else:
        verdikt = "befund" if befunde else "sauber"
    return {"page_id": row["page_id"], "titel": row["titel"], "kanal": row["kanal"],
            "datum": row["datum"], "laenge": len(text), "befunde": befunde,
            "verdikt": verdikt}


def report_markdown(results: list[dict]) -> str:
    """Bericht: eine Tabellenzeile je Beitrag, darunter die Befunde im
    Wortlaut, oben die Summen."""
    mit = sum(1 for r in results if r["verdikt"] == "befund")
    sauber = sum(1 for r in results if r["verdikt"] == "sauber")
    ohne = sum(1 for r in results if r["verdikt"] == "kein_urteil")
    gesamt = sum(len(r["befunde"]) for r in results)
    lines = [
        "# Bestandsleser SWOT-Redaktionsplan",
        "",
        f"Beitraege: {len(results)}, mit Befund: {mit}, sauber: {sauber}, "
        f"kein Urteil: {ohne}, Befunde gesamt: {gesamt}",
        "",
        "| Termin | Kanal | Titel | Zeichen ohne CTA | Befunde |",
        "|---|---|---|---|---|",
    ]
    for r in sorted(results, key=lambda x: (x["datum"], x["kanal"])):
        lines.append(f"| {r['datum']} | {r['kanal']} | {r['titel']} | {r['laenge']} | {len(r['befunde'])} |")
    lines.append("")
    for r in sorted(results, key=lambda x: (x["datum"], x["kanal"])):
        if not r["befunde"]:
            continue
        lines.append(f"## {r['datum']} {r['kanal']}: {r['titel']}")
        lines.append("")
        lines.append(naturalness.findings_note(r["befunde"]))
        lines.append("")
    return "\n".join(lines)
