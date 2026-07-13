"""
Notion DB Interface für Jolly Influencer Post Recycling.
DB-ID kommt aus NOTION_DB_ID (Env) oder dem Default des aktiven Clients.
Direkte Notion API (kein MCP) — für Python-Scripts und Railway.
"""

import os
import time
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

from clients import load_client

load_dotenv()

_cfg = load_client()

# Pro Mandant eigener Token/Webhook moeglich (z.B. NOTION_TOKEN_LISOCON), damit
# lokale Runs mit gesetztem Jolly-.env nicht in die falsche DB/Notification laufen.
NOTION_TOKEN = os.getenv(getattr(_cfg, "NOTION_TOKEN_ENV", "NOTION_TOKEN")) or os.getenv("NOTION_TOKEN")
NOTION_DB_ID = os.getenv("NOTION_DB_ID") or _cfg.NOTION_DB_ID_DEFAULT
NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"

# Without a timeout a stalled connection blocks the Railway cron indefinitely.
NOTION_TIMEOUT = 30
NOTION_HTTP_MAX_ATTEMPTS = 2
NOTION_HTTP_BACKOFF_SECONDS = 3


def _headers():
    return {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }


def _notion_request(method: str, url: str, **kwargs) -> requests.Response:
    """Notion HTTP call with a default timeout and one retry on network errors / 5xx.

    Does not call raise_for_status — callers keep their own .ok / .json handling.
    """
    kwargs.setdefault("timeout", NOTION_TIMEOUT)
    last_exc = None
    for attempt in range(1, NOTION_HTTP_MAX_ATTEMPTS + 1):
        try:
            resp = requests.request(method, url, **kwargs)
            if resp.status_code >= 500 and attempt < NOTION_HTTP_MAX_ATTEMPTS:
                time.sleep(NOTION_HTTP_BACKOFF_SECONDS * attempt)
                continue
            return resp
        except requests.RequestException as e:
            last_exc = e
            if attempt < NOTION_HTTP_MAX_ATTEMPTS:
                time.sleep(NOTION_HTTP_BACKOFF_SECONDS * attempt)
                continue
            raise
    raise last_exc  # type: ignore[misc]


def get_existing_post_urls() -> set:
    """Gibt alle bereits in Notion gespeicherten Post-URLs zurück (für Duplikat-Filterung)."""
    urls = set()
    has_more = True
    start_cursor = None

    while has_more:
        payload = {"page_size": 100}
        if start_cursor:
            payload["start_cursor"] = start_cursor

        resp = _notion_request(
            "POST",
            f"{NOTION_API}/databases/{NOTION_DB_ID}/query",
            headers=_headers(),
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

        for page in data.get("results", []):
            props = page.get("properties", {})
            # "New" = page created but update_with_draft never completed (partial write).
            # Skip it for dedup so the post is re-picked and finished on a later run,
            # instead of being suppressed forever as a bare URL-only entry.
            status = (props.get("Status", {}).get("select") or {}).get("name")
            if status == "New":
                continue
            url_prop = props.get("LinkedIn Post URL", {})
            url = url_prop.get("url")
            if url:
                urls.add(url)

        has_more = data.get("has_more", False)
        start_cursor = data.get("next_cursor")

    return urls


def _sanitize(text: str) -> str:
    """Entfernt Steuerzeichen und Null-Bytes die Notion ablehnt."""
    import re
    # Null-Bytes und andere ungueltige Steuerzeichen entfernen (ausser \n, \t)
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text or "")


def _utf16_len(text: str) -> int:
    # Notion misst content.length in UTF-16 Code Units: Astral-Zeichen
    # (Emoji, 𝗯𝗼𝗹𝗱-Unicode aus LinkedIn-Posts) zaehlen 2, Python-Slicing 1.
    return sum(2 if ord(c) > 0xFFFF else 1 for c in text)


def _utf16_chunks(text: str, limit: int = 1900) -> list:
    chunks, cur, cur_len = [], [], 0
    for ch in text:
        w = 2 if ord(ch) > 0xFFFF else 1
        if cur_len + w > limit and cur:
            chunks.append("".join(cur))
            cur, cur_len = [], 0
        cur.append(ch)
        cur_len += w
    if cur:
        chunks.append("".join(cur))
    return chunks


def _utf16_truncate(text: str, limit: int = 2000) -> str:
    if _utf16_len(text) <= limit:
        return text
    return _utf16_chunks(text, limit)[0]


def _rich_text_prop(text: str) -> list:
    # Notion erlaubt max 2000 UTF-16 Units PRO text-Element, aber mehrere
    # Elemente pro rich_text-Property. Frueher wurde hart truncated -> Drafts
    # >2000 Zeichen verloren CTA + Satzende in der Property (Client-Feedback
    # Buettner 2026-07-13, 2x Disapproved). Jetzt chunken statt abschneiden.
    return [{"text": {"content": chunk}} for chunk in _utf16_chunks(text, 2000)]


def create_post_entry(
    influencer: str,
    post_url: str,
    post_text: str,
    post_date: str,
    status: str = "Ready to Review",
    linkedin_draft: str = "",
    image_prompt: str = "",
    image_url: str = "",
    title_hook: str = "",
) -> str:
    """
    Erstellt einen vollstaendigen Eintrag in der Notion DB.
    Schreibt Original-Text + LinkedIn-Draft in den Seiteninhalt.
    Gibt die Notion Page ID zurueck.
    """
    post_text = _sanitize(post_text)
    linkedin_draft = _sanitize(linkedin_draft)
    image_prompt = _sanitize(image_prompt)
    influencer = _sanitize(influencer)

    # Titel NIE aus Influencer-Name oder Original-Text bauen (Leak 2026-07-10):
    # der Notion-Titel wurde in Make als LinkedIn-Bild-Medien-Titel gemappt und
    # hat Original-Autor + Original-Wortlaut unsichtbar in Notification-Kacheln
    # und den LinkedIn-Suchindex geleakt. Nur der eigene Draft-Hook (ohnehin
    # oeffentlicher Post-Text) oder ein neutraler Fallback sind erlaubt; die
    # Quelle steht weiterhin in der Influencer-Property.
    hook = _sanitize(title_hook).strip().splitlines()[0] if title_hook.strip() else ""
    title = f"{hook[:60].strip()}..." if hook else f"Recycling-Post {post_date}"
    excerpt = post_text[:300]

    def text_blocks(text):
        return [
            {"object": "block", "type": "paragraph",
             "paragraph": {"rich_text": [{"type": "text", "text": {"content": chunk}}]}}
            for chunk in _utf16_chunks(text)
        ]

    page_children = [
        {"object": "block", "type": "heading_2",
         "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Original Post"}}]}},
        {"object": "block", "type": "bookmark",
         "bookmark": {"url": post_url}},
        {"object": "block", "type": "heading_2",
         "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Post Text (Original)"}}]}},
        *text_blocks(post_text),
    ]

    if linkedin_draft:
        page_children += [
            {"object": "block", "type": "divider", "divider": {}},
            {"object": "block", "type": "heading_2",
             "heading_2": {"rich_text": [{"type": "text", "text": {"content": "LinkedIn Draft (Ready to Post)"}}]}},
            *text_blocks(linkedin_draft),
        ]

    if image_url:
        page_children += [
            {"object": "block", "type": "heading_2",
             "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Generated Image"}}]}},
            {"object": "block", "type": "image",
             "image": {"type": "external", "external": {"url": image_url}}},
        ]

    payload = {
        "parent": {"database_id": NOTION_DB_ID},
        "properties": {
            "Title": {"title": [{"text": {"content": title}}]},
            "Influencer": {"rich_text": [{"text": {"content": influencer}}]},
            "LinkedIn Post URL": {"url": post_url},
            "Post Excerpt": {"rich_text": [{"text": {"content": excerpt}}]},
            "Status": {"select": {"name": status}},
            "Date Scraped": {"date": {"start": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")}},
            "LinkedIn Draft": {"rich_text": _rich_text_prop(linkedin_draft)} if linkedin_draft else {},
            "Image Prompt": {"rich_text": _rich_text_prop(image_prompt)} if image_prompt else {},
            "Image": {"files": [{"name": "featured-image.jpg", "type": "external", "external": {"url": image_url}}]} if image_url else {},
        },
        "children": page_children,
    }

    # Leere Properties entfernen
    payload["properties"] = {k: v for k, v in payload["properties"].items() if v}

    resp = _notion_request(
        "POST",
        f"{NOTION_API}/pages",
        headers=_headers(),
        json=payload,
    )
    if not resp.ok:
        print(f"  Notion API Fehler {resp.status_code}: {resp.text[:500]}", flush=True)
    resp.raise_for_status()
    page_id = resp.json()["id"]
    return page_id


MAKE_REVIEW_WEBHOOK = os.getenv(getattr(_cfg, "MAKE_WEBHOOK_ENV", "MAKE_REVIEW_WEBHOOK"), "")
NOTION_PAGE_BASE_URL = "https://www.notion.so/"


def _append_infographic_block(page_id: str, skeleton: str) -> None:
    """Haengt das Infografik-Skelett als neuen Block an die Notion-Seite an."""
    skeleton = _sanitize(skeleton)
    chunks = _utf16_chunks(skeleton)
    children = [
        {"object": "block", "type": "divider", "divider": {}},
        {"object": "block", "type": "heading_2",
         "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Infografik-Skelett (Canva)"}}]}},
    ]
    for chunk in chunks:
        children.append({
            "object": "block", "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": chunk}}]},
        })
    resp = _notion_request(
        "PATCH",
        f"{NOTION_API}/blocks/{page_id}/children",
        headers=_headers(),
        json={"children": children},
    )
    resp.raise_for_status()


def _h2_block(text: str) -> dict:
    return {"object": "block", "type": "heading_2",
            "heading_2": {"rich_text": [{"type": "text", "text": {"content": text}}]}}


def _para_blocks(text: str) -> list:
    return [
        {"object": "block", "type": "paragraph",
         "paragraph": {"rich_text": [{"type": "text", "text": {"content": c}}]}}
        for c in _utf16_chunks(_sanitize(text))
    ]


_DIVIDER_BLOCK = {"object": "block", "type": "divider", "divider": {}}


def _rebuild_page_body(page_id: str, image_url: str, de_draft: str, en_draft: str,
                       post_text: str, post_url: str, skeleton: str,
                       image_prompt: str) -> None:
    """Ersetzt den kompletten Page-Body durch die Review-Template-Reihenfolge
    (Richard 2026-07-08): Bild -> DE-Draft -> EN-Draft -> Original ->
    Infografik-Skelett -> Image Prompt ganz unten."""
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
    for b in blocks:
        resp = _notion_request("DELETE", f"{NOTION_API}/blocks/{b['id']}", headers=_headers())
        resp.raise_for_status()

    children = []
    if image_url:
        children += [_h2_block("Generated Image"),
                     {"object": "block", "type": "image",
                      "image": {"type": "external", "external": {"url": image_url}}},
                     _DIVIDER_BLOCK]
    # Ohne EN-Draft (FEATURES["en_draft"]=False) entfaellt die EN-Sektion und
    # das Slot-Label (Vormittag/Nachmittag-Modell gilt nur im DE+EN-Betrieb).
    de_heading = "LinkedIn Draft DE (Slot: Vormittag)" if en_draft else "LinkedIn Draft DE"
    children += [_h2_block(de_heading), *_para_blocks(de_draft), _DIVIDER_BLOCK]
    if en_draft:
        children += [_h2_block("LinkedIn Draft EN (Slot: Nachmittag)"), *_para_blocks(en_draft), _DIVIDER_BLOCK]
    children += [_h2_block("Original Post"),
                 {"object": "block", "type": "bookmark", "bookmark": {"url": post_url}},
                 _h2_block("Post Text (Original)"), *_para_blocks(post_text)]
    if skeleton:
        children += [_DIVIDER_BLOCK, _h2_block("Infografik-Skelett (Canva)"), *_para_blocks(skeleton)]
    if image_prompt:
        children += [_DIVIDER_BLOCK, _h2_block("Image Prompt"), *_para_blocks(image_prompt)]

    for i in range(0, len(children), 100):  # Notion-Limit: 100 Blocks pro Append
        resp = _notion_request("PATCH", f"{NOTION_API}/blocks/{page_id}/children",
                               headers=_headers(), json={"children": children[i:i + 100]})
        resp.raise_for_status()


def _append_draft_blocks(page_id: str, de_draft: str, en_draft: str) -> None:
    """Haengt DE- und EN-Draft als Body-Bloecke mit Slot-Headings an die Seite."""
    def text_blocks(text):
        text = _sanitize(text)
        chunks = _utf16_chunks(text) or [""]
        return [
            {"object": "block", "type": "paragraph",
             "paragraph": {"rich_text": [{"type": "text", "text": {"content": c}}]}}
            for c in chunks
        ]

    de_heading = "LinkedIn Draft DE (Slot: Vormittag)" if en_draft else "LinkedIn Draft DE"
    children = [{"object": "block", "type": "divider", "divider": {}},
                {"object": "block", "type": "heading_2",
                 "heading_2": {"rich_text": [{"type": "text",
                  "text": {"content": de_heading}}]}}]
    children += text_blocks(de_draft)
    if en_draft:
        children += [{"object": "block", "type": "divider", "divider": {}},
                     {"object": "block", "type": "heading_2",
                      "heading_2": {"rich_text": [{"type": "text",
                       "text": {"content": "LinkedIn Draft EN (Slot: Nachmittag)"}}]}}]
        children += text_blocks(en_draft)

    resp = _notion_request(
        "PATCH",
        f"{NOTION_API}/blocks/{page_id}/children",
        headers=_headers(),
        json={"children": children},
    )
    resp.raise_for_status()


def set_post_status(page_id: str, status: str) -> None:
    """Setzt den Status eines Notion-Eintrags (z.B. 'Skipped', 'New')."""
    resp = _notion_request(
        "PATCH",
        f"{NOTION_API}/pages/{page_id}",
        headers=_headers(),
        json={"properties": {"Status": {"select": {"name": status}}}},
    )
    resp.raise_for_status()


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


def update_with_draft(
    page_id: str,
    linkedin_draft: str,
    image_prompt: str,
    image_url: str,
    en_draft: str = "",
    title: str = "",
    influencer: str = "",
    image_failed: bool = False,
    image_error: str = "",
    infographic_skeleton: str = "",
    post_format: str = "",
    infographic_type: str = "",
    archetype: str = "",
    matrix_job: str = "",
    matrix_stage: str = "",
    persona: str = "",
    poster: str = "",
    asset_id: str = "",
    post_text: str = "",
    post_url: str = "",
):
    """
    Aktualisiert einen Notion-Eintrag mit dem generierten LinkedIn-Post + Bild-URL.
    Setzt Status auf 'Ready to Review' (oder 'Image Failed' falls Bildgenerierung
    fehlgeschlagen ist) und feuert den Make-Webhook fuer die E-Mail-Benachrichtigung.
    Mit post_text + post_url wird der Page-Body komplett in Review-Template-
    Reihenfolge neu aufgebaut (Bild -> Drafts -> Original -> Skelett -> Prompt);
    ohne bleibt das alte Append-Verhalten.
    Raises ValueError wenn linkedin_draft leer ist.
    """
    if not linkedin_draft:
        raise ValueError(f"update_with_draft: linkedin_draft ist leer fuer page_id={page_id}")

    status_name = "Image Failed" if image_failed else "Ready to Review"
    properties = {
        "Status": {"select": {"name": status_name}},
    }
    if linkedin_draft:
        properties["LinkedIn Draft"] = {
            "rich_text": _rich_text_prop(linkedin_draft)
        }
    if en_draft:
        properties["LinkedIn Draft EN"] = {
            "rich_text": _rich_text_prop(en_draft)
        }
    if image_prompt:
        # Bei Image-Failure haengen wir die letzte Fehlermeldung an, damit
        # Richard im Notion-Page sofort sieht WARUM (statt nur in Railway-Logs).
        prompt_payload = image_prompt
        if image_failed and image_error:
            prompt_payload = f"[IMAGE FAILED] {image_error[:400]}\n\n{image_prompt}"
        properties["Image Prompt"] = {
            "rich_text": _rich_text_prop(prompt_payload)
        }
    if image_url:
        properties["Image"] = {
            "files": [{"name": "featured-image.jpg", "type": "external", "external": {"url": image_url}}]
        }

    payload = {"properties": properties}

    resp = _notion_request(
        "PATCH",
        f"{NOTION_API}/pages/{page_id}",
        headers=_headers(),
        json=payload,
    )
    resp.raise_for_status()
    result = resp.json()

    # Format-Property separat + non-fatal schreiben: existiert die Property in
    # Notion (noch) nicht, darf das den kritischen Status-PATCH oben nicht killen.
    if post_format:
        try:
            fr = _notion_request(
                "PATCH",
                f"{NOTION_API}/pages/{page_id}",
                headers=_headers(),
                json={"properties": {"Format": {"select": {"name": post_format}}}},
            )
            fr.raise_for_status()
            print(f"  Format-Property gesetzt: {post_format}", flush=True)
        except Exception as e:
            print(f"  Format-Property fehlgeschlagen (nicht kritisch): {e}", flush=True)

    # Infografik-Typ separat + non-fatal (wie Format): treibt das Anti-Repeat im
    # naechsten Run via get_recent_infographic_types. Fehlt die Property in Notion,
    # darf das den kritischen Status-PATCH oben nicht killen.
    if infographic_type:
        try:
            ir = _notion_request(
                "PATCH",
                f"{NOTION_API}/pages/{page_id}",
                headers=_headers(),
                json={"properties": {"Infografik-Typ": {"select": {"name": infographic_type}}}},
            )
            ir.raise_for_status()
            print(f"  Infografik-Typ-Property gesetzt: {infographic_type}", flush=True)
        except Exception as e:
            print(f"  Infografik-Typ-Property fehlgeschlagen (nicht kritisch): {e}", flush=True)

    # Bild-Variante separat + non-fatal (wie Format/Infografik-Typ): treibt das
    # Anti-Repeat des Bild-Archetyps im naechsten Run via get_recent_archetypes.
    if archetype:
        try:
            ar = _notion_request(
                "PATCH",
                f"{NOTION_API}/pages/{page_id}",
                headers=_headers(),
                json={"properties": {"Bild-Variante": {"select": {"name": archetype}}}},
            )
            ar.raise_for_status()
            print(f"  Bild-Variante-Property gesetzt: {archetype}", flush=True)
        except Exception as e:
            print(f"  Bild-Variante-Property fehlgeschlagen (nicht kritisch): {e}", flush=True)

    # Matrix-Tracking (Quota-Fenster des naechsten Runs) + Persona/Asset-Anti-Repeat.
    _patch_select_nonfatal(page_id, "Matrix-Job", matrix_job)
    _patch_select_nonfatal(page_id, "Matrix-Stage", matrix_stage)
    _patch_select_nonfatal(page_id, "Persona", persona)
    # Poster (Persona-Split, GTM-Call Jae 2026-07-09): wer den Post published;
    # Make routet darueber auf den jeweiligen LinkedIn-Account.
    _patch_select_nonfatal(page_id, "Poster", poster)
    _patch_select_nonfatal(page_id, "Asset", asset_id)

    # Make-Webhook feuern → E-Mail-Alert an Richard.
    # image_failed-Flag steht im Payload, damit die Make-Scenario spaeter
    # einen anderen Subject-Prefix setzen kann (z.B. "[Bild fehlt]").
    if not MAKE_REVIEW_WEBHOOK:
        print("  Make-Webhook uebersprungen: MAKE_REVIEW_WEBHOOK nicht gesetzt", flush=True)
    else:
        try:
            notion_url = f"{NOTION_PAGE_BASE_URL}{page_id.replace('-', '')}"
            webhook_payload = {
                "title": title or page_id,
                "influencer": influencer,
                "notion_url": notion_url,
                "image_failed": image_failed,
                "status": status_name,
            }
            requests.post(MAKE_REVIEW_WEBHOOK, json=webhook_payload, timeout=10)
            print(f"  Make-Webhook gefeuert: {status_name} Alert", flush=True)
        except Exception as e:
            print(f"  Make-Webhook fehlgeschlagen (nicht kritisch): {e}", flush=True)

    if post_text and post_url:
        try:
            _rebuild_page_body(page_id, image_url=image_url, de_draft=linkedin_draft,
                               en_draft=en_draft, post_text=post_text, post_url=post_url,
                               skeleton=infographic_skeleton, image_prompt=image_prompt)
            print("  Page-Body in Template-Reihenfolge geschrieben.", flush=True)
        except Exception as e:
            print(f"  Body-Rebuild fehlgeschlagen (nicht kritisch): {e}", flush=True)
        return result

    try:
        _append_draft_blocks(page_id, linkedin_draft, en_draft)
        print("  DE+EN Draft-Bloecke mit Slot-Headings geschrieben.", flush=True)
    except Exception as e:
        print(f"  Draft-Bloecke fehlgeschlagen (nicht kritisch): {e}", flush=True)

    if infographic_skeleton:
        try:
            _append_infographic_block(page_id, infographic_skeleton)
            print("  Infografik-Skelett in Notion geschrieben.", flush=True)
        except Exception as e:
            print(f"  Infografik-Block fehlgeschlagen (nicht kritisch): {e}", flush=True)

    return result


def get_recent_linkedin_drafts(limit: int = 7) -> list[str]:
    """
    Gibt die LinkedIn-Draft-Texte der letzten N geposteten Eintraege zurueck.
    Wird fuer Themen-Diversitaets-Check im Scoring verwendet.
    """
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
    results = resp.json().get("results", [])

    drafts = []
    for page in results:
        props = page.get("properties", {})
        draft_prop = props.get("LinkedIn Draft", {})
        rich_text = draft_prop.get("rich_text", [])
        text = "".join(rt.get("plain_text", "") for rt in rich_text).strip()
        if text:
            drafts.append(text[:500])  # nur Anfang fuer Token-Effizienz
    return drafts


def get_recent_formats(limit: int = 3) -> list[str]:
    """Gibt die Format-Werte der letzten N Eintraege zurueck (fuer den
    Anti-Repeat-Check im Format-Router). Tolerant: fehlende Property -> []."""
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
    results = resp.json().get("results", [])

    formats = []
    for page in results:
        props = page.get("properties", {})
        sel = props.get("Format", {}).get("select") or {}
        name = sel.get("name")
        if name:
            formats.append(name)
    return formats


def get_recent_infographic_types(limit: int = 4) -> list[str]:
    """Gibt die Infografik-Typ-Werte der letzten N Eintraege zurueck (neuestes zuerst),
    fuer das Anti-Repeat des Infografik-Typs im Generierungs-Prompt. Tolerant:
    fehlende Property -> []."""
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
    results = resp.json().get("results", [])

    types = []
    for page in results:
        props = page.get("properties", {})
        sel = props.get("Infografik-Typ", {}).get("select") or {}
        name = sel.get("name")
        if name:
            types.append(name)
    return types


def get_recent_archetypes(limit: int = 3) -> list[str]:
    """Gibt die Bild-Varianten (Bild-Archetyp) der letzten N Eintraege zurueck
    (neuestes zuerst), fuer das Anti-Repeat des Bild-Archetyps im Selektor.
    Tolerant: fehlende Property -> []."""
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
    results = resp.json().get("results", [])

    archetypes = []
    for page in results:
        props = page.get("properties", {})
        sel = props.get("Bild-Variante", {}).get("select") or {}
        name = sel.get("name")
        if name:
            archetypes.append(name)
    return archetypes


def get_recent_boxes(limit: int = 10) -> list[tuple[str, str]]:
    """(Matrix-Job, Matrix-Stage)-Paare der letzten N Eintraege, neuestes
    zuerst. Eintraege ohne beide Properties werden uebersprungen. Holt ein
    breiteres Fenster (50) und schneidet ERST NACH dem Filtern zu, damit
    Seiten ohne die Property das Fenster nicht verkuerzen."""
    payload = {
        "filter": {
            "or": [
                {"property": "Status", "select": {"equals": "Posted"}},
                {"property": "Status", "select": {"equals": "Approved"}},
                {"property": "Status", "select": {"equals": "Ready to Review"}},
            ]
        },
        "sorts": [{"timestamp": "last_edited_time", "direction": "descending"}],
        "page_size": 50,
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
    return boxes[:limit]


def _get_recent_select(prop: str, limit: int) -> list[str]:
    """Werte einer Select-Property der letzten N Eintraege (neuestes zuerst).
    Holt ein breiteres Fenster (50) und schneidet ERST NACH dem Filtern zu,
    damit Seiten ohne die Property das Fenster nicht verkuerzen."""
    payload = {
        "filter": {
            "or": [
                {"property": "Status", "select": {"equals": "Posted"}},
                {"property": "Status", "select": {"equals": "Approved"}},
                {"property": "Status", "select": {"equals": "Ready to Review"}},
            ]
        },
        "sorts": [{"timestamp": "last_edited_time", "direction": "descending"}],
        "page_size": 50,
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
    return values[:limit]


def get_recent_assets(limit: int = 5) -> list[str]:
    """Asset-Ids der letzten N Eintraege (fuer das LRU-Asset-Anti-Repeat)."""
    return _get_recent_select("Asset", limit)


def get_recent_personas(limit: int = 2) -> list[str]:
    """Persona-Ids der letzten N Eintraege (Sekundaer-Persona nie 2x in Folge)."""
    return _get_recent_select("Persona", limit)


def get_entry_by_url(post_url: str) -> dict | None:
    """Gibt den Notion-Eintrag für eine bestimmte Post-URL zurück."""
    payload = {
        "filter": {
            "property": "LinkedIn Post URL",
            "url": {"equals": post_url}
        }
    }
    resp = _notion_request(
        "POST",
        f"{NOTION_API}/databases/{NOTION_DB_ID}/query",
        headers=_headers(),
        json=payload,
    )
    resp.raise_for_status()
    results = resp.json().get("results", [])
    return results[0] if results else None


def get_entry_by_page_id(page_id: str) -> dict:
    """Gibt einen Notion-Eintrag anhand seiner Page ID zurück."""
    resp = _notion_request(
        "GET",
        f"{NOTION_API}/pages/{page_id}",
        headers=_headers(),
    )
    resp.raise_for_status()
    return resp.json()


if __name__ == "__main__":
    print("Teste Notion-Verbindung ...")
    if not NOTION_TOKEN:
        print("✗ NOTION_TOKEN fehlt in .env")
    else:
        urls = get_existing_post_urls()
        print(f"OK - {len(urls)} Posts bereits in DB")
