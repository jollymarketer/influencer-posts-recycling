"""Image-Repair: Eintraege mit Status "Image Wrong" neu bebildern.

GTM-Call Jae 2026-07-09: der Notion-Status "Image wrong" (Schreibweise exakt
wie in der Lisocon-DB, kleines w) bedeutet
"Bild falsch, Text ok" (im Gegensatz zu "Image Failed" = kein Bild erzeugt).
Der Repair-Pass liest den vollstaendigen Image Prompt aus dem Page-Body
(die Property ist auf 2000 UTF-16-Units gekappt, der Body nicht),
generiert das Bild neu und baut den Body in Template-Reihenfolge wieder auf.
Texte bleiben unveraendert. Laeuft als Schritt 1.5 im Daily-Run (non-fatal).
"""
import sys

from tools.kieai_image import generate_image
from tools.notion_db import (
    NOTION_API,
    NOTION_DB_ID,
    _headers,
    _notion_request,
    _rebuild_page_body,
    get_approved_missing_image,
    set_post_status,
)

# Bild-Regeln: LinkedIn-Square immer 1:1 (siehe memory feedback_image_generation).
ASPECT_RATIO = "1:1"

# Nur die Infografik behaelt ihre Marks (strip wuerde Diagramm-Linien zerstoeren);
# muss ARCHETYPES in tools/image_archetypes.py entsprechen.
_NO_STRIP_ARCHETYPES = {"structured_infographic"}

_SECTION_BY_HEADING = (
    ("LinkedIn Draft DE", "de_draft"),
    ("LinkedIn Draft EN", "en_draft"),
    ("Post Text", "post_text"),
    ("Infografik-Skelett", "skeleton"),
    ("Image Prompt", "image_prompt"),
)


def _plain_text(rich_text: list) -> str:
    return "".join(rt.get("plain_text", "") for rt in rich_text)


def _page_blocks(page_id: str) -> list:
    blocks, cursor = [], None
    while True:
        url = f"{NOTION_API}/blocks/{page_id}/children?page_size=100"
        if cursor:
            url += f"&start_cursor={cursor}"
        resp = _notion_request("GET", url, headers=_headers())
        resp.raise_for_status()
        data = resp.json()
        blocks.extend(data["results"])
        if not data.get("has_more"):
            break
        cursor = data["next_cursor"]
    return blocks


def extract_body_sections(page_id: str) -> dict:
    """Liest die Review-Template-Sektionen aus dem Page-Body zurueck.
    Paragraph-Chunks (UTF-16-Splitting in _para_blocks) werden ohne Separator
    wieder zusammengesetzt, da sie aus EINEM Text mit \n im Content stammen."""
    sections = {"image_url": "", "de_draft": "", "en_draft": "",
                "post_text": "", "post_url": "", "skeleton": "", "image_prompt": ""}
    current = None
    for b in _page_blocks(page_id):
        btype = b.get("type")
        if btype == "heading_2":
            title = _plain_text(b["heading_2"]["rich_text"])
            current = next((key for prefix, key in _SECTION_BY_HEADING
                            if title.startswith(prefix)), None)
        elif btype == "image":
            img = b["image"]
            url = img.get("external", {}).get("url") or img.get("file", {}).get("url", "")
            if url and not sections["image_url"]:
                sections["image_url"] = url
        elif btype == "bookmark":
            if not sections["post_url"]:
                sections["post_url"] = b["bookmark"].get("url", "")
        elif btype == "paragraph" and current:
            sections[current] += _plain_text(b["paragraph"]["rich_text"])
    return sections


def _query_pages_by_status(statuses: tuple) -> list:
    pages, cursor = [], None
    payload = {"filter": {"or": [
        {"property": "Status", "select": {"equals": s}} for s in statuses
    ]}}
    while True:
        body = dict(payload)
        if cursor:
            body["start_cursor"] = cursor
        resp = _notion_request("POST", f"{NOTION_API}/databases/{NOTION_DB_ID}/query",
                               headers=_headers(), json=body)
        resp.raise_for_status()
        data = resp.json()
        pages.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        cursor = data["next_cursor"]
    return pages


def _archetype_of(page: dict) -> str:
    sel = (page.get("properties", {}).get("Bild-Variante", {}).get("select") or {})
    return sel.get("name", "")


def regenerate_page_image(page_id: str, sections: dict, strip_marks: bool = True,
                          status: str = "Ready to Review") -> str:
    """Generiert das Bild aus dem gespeicherten Image Prompt neu, baut den Body
    mit unveraenderten Texten wieder auf und setzt Image-Property + Status
    (Default 'Ready to Review'; Phase A des Slate-Modus uebergibt 'Approved',
    damit die Text-Freigabe erhalten bleibt). Gibt die neue Bild-URL zurueck.
    Raises wenn kein Image Prompt vorhanden ist oder die Generierung scheitert."""
    prompt = sections["image_prompt"].strip()
    if not prompt:
        raise ValueError(f"Kein Image Prompt im Body von {page_id} - Repair nicht moeglich.")

    image_url = generate_image(prompt, aspect_ratio=ASPECT_RATIO, strip_marks=strip_marks)

    _rebuild_page_body(page_id, image_url=image_url,
                       de_draft=sections["de_draft"], en_draft=sections["en_draft"],
                       post_text=sections["post_text"], post_url=sections["post_url"],
                       skeleton=sections["skeleton"], image_prompt=prompt)

    resp = _notion_request(
        "PATCH", f"{NOTION_API}/pages/{page_id}", headers=_headers(),
        json={"properties": {
            "Status": {"select": {"name": status}},
            "Image": {"files": [{"name": "featured-image.jpg", "type": "external",
                                 "external": {"url": image_url}}]},
        }},
    )
    resp.raise_for_status()
    return image_url


def fill_missing_images() -> int:
    """Phase A des Slate-Modus (spec 2026-07-16): Status=Approved ohne Bild
    -> Bild generieren. Bild ist der teuerste Schritt und laeuft deshalb
    erst NACH der Text-Freigabe. Status bleibt Approved (Publish-Filter
    verlangt Image non-empty). Fehler pro Zeile -> Status 'Image Failed'."""
    done = 0
    for row in get_approved_missing_image():
        page_id = row["page_id"]
        try:
            sections = extract_body_sections(page_id)
            strip = row.get("archetype", "") not in _NO_STRIP_ARCHETYPES
            url = regenerate_page_image(page_id, sections, strip_marks=strip,
                                        status="Approved")
            print(f"  Bild generiert: {page_id} -> {url}", flush=True)
            done += 1
        except Exception as e:
            print(f"  Bild fuer {page_id} fehlgeschlagen: {e}", file=sys.stderr, flush=True)
            try:
                set_post_status(page_id, "Image Failed")
            except Exception as e2:
                print(f"  Status-Setzen fehlgeschlagen: {e2}", file=sys.stderr, flush=True)
    return done


def repair_wrong_images(statuses: tuple = ("Image wrong",)) -> int:
    """Repariert alle Eintraege mit den gegebenen Status. Fehler pro Page sind
    non-fatal (naechste Page laeuft weiter). Gibt die Anzahl Reparaturen zurueck."""
    pages = _query_pages_by_status(statuses)
    if not pages:
        return 0
    repaired = 0
    for page in pages:
        page_id = page["id"]
        try:
            sections = extract_body_sections(page_id)
            strip = _archetype_of(page) not in _NO_STRIP_ARCHETYPES
            url = regenerate_page_image(page_id, sections, strip_marks=strip)
            print(f"  Image-Repair OK: {page_id} -> {url}", flush=True)
            repaired += 1
        except Exception as e:
            print(f"  Image-Repair fehlgeschlagen fuer {page_id} (nicht kritisch): {e}",
                  file=sys.stderr, flush=True)
    return repaired
