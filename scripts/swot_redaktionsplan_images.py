"""Einmalig: Post-Bilder fuer die 12 LinkedIn-Entwuerfe im SWOT
Content-Redaktionsplan (Notion-DB im SWOT-Portal, angelegt 12.08.2026).

Freigabe Richard 12.08.2026 (~1-2 USD kie.ai fuer 12 Bilder). Die Entwuerfe
selbst liegen bereits in Notion; dieses Skript erzeugt nur die Bilder ueber
die bestehende kie.ai-Strecke (inkl. SWOT-Logo-Overlay + GitHub-Upload) und
schreibt die URLs nach .tmp/swot_images_result.json. Das Anhaengen an die
Notion-Eintraege passiert separat (Claude-Session via Notion-MCP, weil die
Engine-Integration keinen Zugriff auf das SWOT-Portal hat).

Run (Git Bash):
  cd "Jolly Automations/Jolly Influencer Post Recycling"
  CLIENT=swot python scripts/swot_redaktionsplan_images.py --slug datev   # Testbild
  CLIENT=swot python scripts/swot_redaktionsplan_images.py               # alle fehlenden
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
os.environ.setdefault("CLIENT", "swot")

from clients import apply_tokens, load_client
from tools.kieai_image import generate_image

# post_scorer NICHT importieren: der Modul-Import baut alle Prompts und
# verlangt den vollen Token-Satz (Scoring, DACH/EN-Post, Formate), den
# clients/swot erst mit dem Slate-Umbau bekommt. Fuer das Bild reicht das
# IMAGE_PROMPT_TEMPLATE, direkt aus der Quelldatei geschnitten.
import re

_SRC = open(os.path.join(ROOT, "tools", "post_scorer.py"), encoding="utf-8").read()
IMAGE_PROMPT_TEMPLATE = re.search(
    r'IMAGE_PROMPT_TEMPLATE = """(.*?)"""', _SRC, re.S).group(1)

RESULT_PATH = os.path.join(ROOT, ".tmp", "swot_images_result.json")

# Kernbotschaft/Kontext je Post, abgeleitet aus den finalen Entwuerfen in der
# Notion-DB (Content-Redaktionsplan Blog und LinkedIn, 12.08.2026).
# headline/subline sind FIX und werden woertlich gerendert: der Testlauf vom
# 12.08. hat gezeigt, dass frei komponierte Headlines an langen deutschen
# Komposita brechen ("WIRTSCHAFTSBER|" abgeschnitten). Kurz halten.
# LucaNet-Post: Bild bewusst OHNE Anbieternamen, damit es fuer Fassung A und B
# funktioniert (Namensnennung braucht Kulle-Freigabe, das Bild nicht).
POSTS = [
    {"slug": "datev", "page_id": "3ba1617b-1baf-81ce-bd64-c496e876895f",
     "headline": "Das DATEV-Aus kommt.",
     "subline": "Wohin mit den Mandaten?",
     "core": "DATEV stellt die Wirtschaftsberatung ein. Was passiert mit den Planungsmandaten der Kanzleien?",
     "context": "Kanzleien brauchen einen neuen Weg fuer Planung, Reporting und Liquiditaet. Wer jetzt plant, wechselt geordnet; wer wartet, entscheidet unter Druck."},
    {"slug": "excel", "page_id": "3ba1617b-1baf-81dd-8286-c3c06588d5ed",
     "headline": "Excel kann keiner übergeben.",
     "subline": "Wartbarkeit entscheidet.",
     "core": "Das Excel-Modell funktioniert. Solange sein Erbauer daneben sitzt.",
     "context": "Wartbarkeit ist das eigentliche Auswahlkriterium: Ein Planungsmodell muss ohne seinen Erbauer weiterleben, sonst ist es eine Abhaengigkeit."},
    {"slug": "henne-ei", "page_id": "3ba1617b-1baf-810f-b642-c91634b17509",
     "headline": "Erst Mandate oder erst Werkzeug?",
     "subline": "Das Gründer-Dilemma.",
     "core": "Das Henne-Ei-Problem der Beratungsgruendung: Das Werkzeug kostet, bevor die Mandate da sind, die es bezahlen.",
     "context": "Drei Wege fuer Gruender: Excel bis es bricht, warten auf das dritte Mandat, oder klein starten und mitwachsen."},
    {"slug": "preise", "page_id": "3ba1617b-1baf-8108-a632-e725a97ed467",
     "headline": "Preisschock bei Mandanten.",
     "subline": "Wechsel richtig planen.",
     "core": "KMU-Mandanten sind von neuen Software-Preisen verschreckt. Was ein Mandat vor dem Wechsel klaeren muss.",
     "context": "Checkliste vor dem Wechsel der Planungssoftware: Datenuebernahme, Betriebsmodell, Lizenzlogik, Uebergangszeit. Kein Anbietername im Bild."},
    {"slug": "mandate", "page_id": "3ba1617b-1baf-8138-9b40-dd852d86077a",
     "headline": "Ab fünf Mandaten lohnt es.",
     "subline": "Die ehrliche Rechnung.",
     "core": "Ab wie vielen Planungsmandaten traegt eine eigene Lizenz?",
     "context": "Bei zwei Planungen im Jahr rechnet sie sich nicht. Ab etwa fuenf Mandaten dreht sich das Bild: Die Marge entsteht in der Wiederholung."},
    {"slug": "rollen", "page_id": "3ba1617b-1baf-812e-b397-f2bde24e7b23",
     "headline": "Anwender oder Empfehler?",
     "subline": "Zwei Rollen, zwei Gespräche.",
     "core": "Eigenanwender oder Empfehler: Berater begegnen Planungssoftware in zwei Rollen.",
     "context": "Der eine kauft die Lizenz und arbeitet ueber Mandate, der andere vermittelt zum Mandanten. Beide legitim, voellig unterschiedliche Gespraeche."},
    {"slug": "sanierung", "page_id": "3ba1617b-1baf-81c1-a924-de49d0c3619d",
     "headline": "84 zu 0.",
     "subline": "Sanierung: real, aber unsichtbar.",
     "core": "84 zu 0: Sanierung ist das haeufigste Fachthema im Kundengespraech und in Stellenanzeigen unsichtbar.",
     "context": "Eigene Auswertung ueber 78 Gespraechsnotizen. Die 13-Wochen-Liquiditaetsplanung entsteht in Sanierungsfaellen bis heute meist in Excel."},
    {"slug": "datenzugang", "page_id": "3ba1617b-1baf-8142-8893-f8da3f3dcf69",
     "headline": "Erst Daten, dann Vertrag.",
     "subline": "So starten Profis.",
     "core": "Projekte scheitern nicht am Werkzeug, sondern am Datenzugang.",
     "context": "Die richtige Reihenfolge in Planungsprojekten: erst der Datenweg, dann der Vertrag, dann das Modell."},
    {"slug": "vorlagen", "page_id": "3ba1617b-1baf-8149-9a99-e9b0209247f7",
     "headline": "Vorlage schlägt Einzelbau.",
     "subline": "Skalieren mit Standard.",
     "core": "Standardvorlage schlaegt Individualmodell.",
     "context": "Das zweite Mandat kostet einen Bruchteil des ersten, jeder Kollege kann uebernehmen, Fehler werden nur einmal korrigiert: in der Vorlage."},
    {"slug": "ifrs18", "page_id": "3ba1617b-1baf-8137-bcd8-e260b1c943a4",
     "headline": "IFRS 18: 2026 zählt schon.",
     "subline": "Das Vergleichsjahr läuft.",
     "core": "IFRS 18: 2026 ist schon das Vergleichsjahr.",
     "context": "Der Standard gilt ab Geschaeftsjahr 2027, verlangt aber angepasste Vorjahreszahlen. Wer erst 2027 umstellt, baut die 2026er-Zahlen doppelt."},
    {"slug": "workshop", "page_id": "3ba1617b-1baf-8104-9362-d839f8473f49",
     "headline": "Workshop statt Demo.",
     "subline": "In zwei Tagen produktiv.",
     "core": "Workshop statt Demo: In ein bis zwei Tagen plant das erste Mandat produktiv.",
     "context": "Echte Zahlen eines echten Mandats statt Folien. Die Lizenz zaehlt keine Gesellschaften mit."},
    {"slug": "powerbi", "page_id": "3ba1617b-1baf-8110-a954-d2dd3291be06",
     "headline": "Zeigen ist nicht rechnen.",
     "subline": "Berichtswesen vs. Planung.",
     "core": "Power BI zeigt. Das Planungswerkzeug rechnet.",
     "context": "Berichtswesen und integrierte Finanzplanung (GuV, Bilanz, Liquiditaet in einem Modell) sind zwei verschiedene Aufgaben."},
]


def build_prompt(cfg, post: dict) -> str:
    prompt = apply_tokens(IMAGE_PROMPT_TEMPLATE, cfg)
    language = getattr(cfg, "IMAGE_LANGUAGE", "German")
    prompt = (prompt
              .replace("{core_message}", post["core"])
              .replace("{context}", post["context"])
              .replace("{language}", language))
    # Feste Headline statt freier Textwahl: der Testlauf brach an langen
    # deutschen Komposita ab und halluzinierte Wortmarken in die Szene.
    prompt += f"""

Mandatory text override (takes precedence over everything above):
Render EXACTLY this headline, verbatim, no changes, no truncation: "{post['headline']}"
Render EXACTLY this support line below it, verbatim: "{post['subline']}"
No other visible text anywhere in the image. Both lines must fit fully inside
the composition with comfortable margins - if in doubt, make the type smaller."""
    return prompt


def load_results() -> dict:
    if os.path.exists(RESULT_PATH):
        with open(RESULT_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_results(results: dict) -> None:
    os.makedirs(os.path.dirname(RESULT_PATH), exist_ok=True)
    with open(RESULT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", help="nur diesen Post rendern (Testlauf)")
    args = parser.parse_args()

    cfg = load_client()
    if cfg.NAME != "swot":
        sys.exit(f"CLIENT={cfg.NAME}, erwartet swot. Abbruch.")

    results = load_results()
    todo = [p for p in POSTS if (not args.slug or p["slug"] == args.slug)
            and p["slug"] not in results]
    if not todo:
        print("Nichts zu tun (alles vorhanden oder Slug unbekannt).")
        return

    for post in todo:
        print(f"\n=== {post['slug']} ===", flush=True)
        prompt = build_prompt(cfg, post)
        url = generate_image(prompt, aspect_ratio="1:1")
        results[post["slug"]] = {"page_id": post["page_id"], "url": url}
        save_results(results)
        print(f"OK {post['slug']} -> {url}", flush=True)

    print(f"\nErgebnis: {RESULT_PATH}")


if __name__ == "__main__":
    main()
