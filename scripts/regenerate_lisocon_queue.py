"""One-time: Lisocon-Bestands-Queue auf den Stand des GTM-Calls 2026-07-09 bringen.

Pro Page (alle ausser Posted/Approved/Skipped):
- Bild aus dem gespeicherten Image Prompt neu generieren (InTO-Logo-Overlay
  kommt aus der aktuellen Pipeline via LOGO_FILE) - fixt das Jolly-Logo-Problem
- DE-Draft: sanitize (Markdown-Sternchen, Dashes) + Grammar-Check + CTA
  www.in2go.io nachruesten (nur wenn noch nicht vorhanden)
- EN-Draft entfernen (Body-Sektion + Property) - 100% Deutsch
- Poster-Property aus der Persona ableiten (kaeufer=Reinhard, anwender=Jae)
- Status -> "Ready to Review" (raeumt auch Jaes Image-Failed-Markierungen auf)

Run: CLIENT=lisocon NOTION_DB_ID=<lisocon-db> python scripts/regenerate_lisocon_queue.py [--dry-run]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from clients import load_client
from tools.image_repair import extract_body_sections, _query_pages_by_status, _archetype_of, _NO_STRIP_ARCHETYPES, ASPECT_RATIO
from tools.kieai_image import generate_image
from tools.notion_db import (
    NOTION_API,
    _headers,
    _notion_request,
    _rebuild_page_body,
    _utf16_truncate,
)
from tools.post_scorer import sanitize_generated_text, grammar_check, _append_cta

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

_cfg = load_client()

SKIP_STATUSES = {"Posted", "Posting", "Approved"}
# Schreibweisen exakt wie in der Lisocon-DB ("Image wrong" mit kleinem w);
# Notion beantwortet Select-Filter mit unbekannter Option mit 400.
PROCESS_STATUSES = ("New", "Ready to Review", "Image Failed", "Image wrong", "Disapproved")


def _title_of(page: dict) -> str:
    for prop in page.get("properties", {}).values():
        if prop.get("type") == "title":
            return "".join(rt.get("plain_text", "") for rt in prop["title"])
    return page["id"]


def _status_of(page: dict) -> str:
    sel = (page.get("properties", {}).get("Status", {}).get("select") or {})
    return sel.get("name", "")


def _persona_of(page: dict) -> str:
    sel = (page.get("properties", {}).get("Persona", {}).get("select") or {})
    return sel.get("name", "")


def main(dry_run: bool = False):
    if _cfg.NAME != "lisocon":
        sys.exit("Abbruch: CLIENT=lisocon setzen (dieses Script ist Lisocon-spezifisch).")

    pages = _query_pages_by_status(PROCESS_STATUSES)
    print(f"{len(pages)} Pages in der Queue (Status in {PROCESS_STATUSES}).\n")

    grammar_report = []
    for page in pages:
        page_id = page["id"]
        title = _title_of(page)
        status = _status_of(page)
        if status in SKIP_STATUSES:
            continue
        print(f"--- {title} [{status}] ({page_id})")

        sections = extract_body_sections(page_id)
        de = sections["de_draft"].strip()
        if not de:
            print("    WARNUNG: kein DE-Draft im Body gefunden - Page uebersprungen.")
            continue

        # Text-Pass: sanitize -> Grammar -> CTA (idempotent).
        de_clean = sanitize_generated_text(de)
        de_fixed = grammar_check(de_clean)
        if de_fixed != de_clean:
            grammar_report.append((title, de_clean, de_fixed))
            print("    Grammar-Check: Korrekturen uebernommen.")
        cta = getattr(_cfg, "CTA_DE", "")
        if cta and "in2go.io" not in de_fixed:
            de_fixed = _append_cta(de_fixed, cta)
            print("    CTA nachgeruestet.")

        # Bild neu generieren (aktuelle Pipeline = InTO-Logo-Overlay).
        prompt = sections["image_prompt"].strip()
        image_url = ""
        if prompt:
            if dry_run:
                print("    [dry-run] wuerde Bild neu generieren.")
                image_url = sections["image_url"]
            else:
                strip = _archetype_of(page) not in _NO_STRIP_ARCHETYPES
                try:
                    image_url = generate_image(prompt, aspect_ratio=ASPECT_RATIO, strip_marks=strip)
                    print(f"    Bild neu: {image_url}")
                except Exception as e:
                    image_url = sections["image_url"]
                    print(f"    WARNUNG: Bildgenerierung fehlgeschlagen, altes Bild bleibt: {e}")
        else:
            print("    WARNUNG: kein Image Prompt im Body - Bild bleibt/fehlt weiter.")
            image_url = sections["image_url"]

        poster = getattr(_cfg, "POSTER_BY_PERSONA", {}).get(
            _persona_of(page), getattr(_cfg, "POSTER_DEFAULT", ""))

        if dry_run:
            print(f"    [dry-run] Body-Rebuild ohne EN, Status->Ready to Review, Poster={poster}")
            continue

        _rebuild_page_body(page_id, image_url=image_url, de_draft=de_fixed, en_draft="",
                           post_text=sections["post_text"], post_url=sections["post_url"],
                           skeleton=sections["skeleton"], image_prompt=prompt)

        props = {
            "Status": {"select": {"name": "Ready to Review"}},
            "LinkedIn Draft": {"rich_text": [{"text": {"content": _utf16_truncate(de_fixed)}}]},
            "LinkedIn Draft EN": {"rich_text": []},
        }
        if image_url:
            props["Image"] = {"files": [{"name": "featured-image.jpg", "type": "external",
                                         "external": {"url": image_url}}]}
        if poster:
            props["Poster"] = {"select": {"name": poster}}
        resp = _notion_request("PATCH", f"{NOTION_API}/pages/{page_id}",
                               headers=_headers(), json={"properties": props})
        resp.raise_for_status()
        print(f"    OK: Ready to Review, Poster={poster or '-'}")

    print(f"\n=== Fertig. Grammar-Korrekturen: {len(grammar_report)} Page(s) ===")
    for title, before, after in grammar_report:
        print(f"\n## {title}")
        b_lines, a_lines = before.splitlines(), after.splitlines()
        for i, (bl, al) in enumerate(zip(b_lines, a_lines)):
            if bl != al:
                print(f"  - {bl}")
                print(f"  + {al}")


if __name__ == "__main__":
    main(dry_run="--dry-run" in sys.argv)
