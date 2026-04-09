"""
Notion DB Interface für Influencer Posts Recycling.
DB ID: 778bd719db9147ff994ddbf8a4ecac34
Direkte Notion API (kein MCP) — für Python-Scripts und Railway.
"""

import os
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DB_ID = os.getenv("NOTION_DB_ID", "778bd719db9147ff994ddbf8a4ecac34")
NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


def _headers():
    return {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }


def get_existing_post_urls() -> set:
    """Gibt alle bereits in Notion gespeicherten Post-URLs zurück (für Duplikat-Filterung)."""
    urls = set()
    has_more = True
    start_cursor = None

    while has_more:
        payload = {"page_size": 100}
        if start_cursor:
            payload["start_cursor"] = start_cursor

        resp = requests.post(
            f"{NOTION_API}/databases/{NOTION_DB_ID}/query",
            headers=_headers(),
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

        for page in data.get("results", []):
            props = page.get("properties", {})
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


def create_post_entry(
    influencer: str,
    post_url: str,
    post_text: str,
    post_date: str,
    status: str = "Ready to Review",
    linkedin_draft: str = "",
    image_prompt: str = "",
    image_url: str = "",
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

    title = f"{influencer} – {post_text[:60].strip()}..."
    excerpt = post_text[:300]

    def text_blocks(text):
        chunks = [text[i:i+1900] for i in range(0, len(text), 1900)]
        return [
            {"object": "block", "type": "paragraph",
             "paragraph": {"rich_text": [{"type": "text", "text": {"content": chunk}}]}}
            for chunk in chunks
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
            "LinkedIn Draft": {"rich_text": [{"text": {"content": linkedin_draft[:2000]}}]} if linkedin_draft else {},
            "Image Prompt": {"rich_text": [{"text": {"content": image_prompt[:2000]}}]} if image_prompt else {},
            "Image": {"files": [{"name": "featured-image.jpg", "type": "external", "external": {"url": image_url}}]} if image_url else {},
        },
        "children": page_children,
    }

    # Leere Properties entfernen
    payload["properties"] = {k: v for k, v in payload["properties"].items() if v}

    resp = requests.post(
        f"{NOTION_API}/pages",
        headers=_headers(),
        json=payload,
    )
    if not resp.ok:
        print(f"  Notion API Fehler {resp.status_code}: {resp.text[:500]}", flush=True)
    resp.raise_for_status()
    page_id = resp.json()["id"]
    return page_id


MAKE_REVIEW_WEBHOOK = "https://hook.eu2.make.com/wbqkg1cmho8n1qmvdg9hv621nqniuxkg"
NOTION_PAGE_BASE_URL = "https://www.notion.so/"


def set_post_status(page_id: str, status: str) -> None:
    """Setzt den Status eines Notion-Eintrags (z.B. 'Skipped', 'New')."""
    resp = requests.patch(
        f"{NOTION_API}/pages/{page_id}",
        headers=_headers(),
        json={"properties": {"Status": {"select": {"name": status}}}},
    )
    resp.raise_for_status()


def update_with_draft(
    page_id: str,
    linkedin_draft: str,
    image_prompt: str,
    image_url: str,
    title: str = "",
    influencer: str = "",
):
    """
    Aktualisiert einen Notion-Eintrag mit dem generierten LinkedIn-Post + Bild-URL.
    Setzt Status auf 'Ready to Review' und feuert den Make-Webhook fuer die E-Mail-Benachrichtigung.
    Raises ValueError wenn linkedin_draft leer ist.
    """
    if not linkedin_draft:
        raise ValueError(f"update_with_draft: linkedin_draft ist leer fuer page_id={page_id}")

    properties = {
        "Status": {
            "select": {"name": "Ready to Review"}
        },
    }
    if linkedin_draft:
        properties["LinkedIn Draft"] = {
            "rich_text": [{"text": {"content": linkedin_draft[:2000]}}]
        }
    if image_prompt:
        properties["Image Prompt"] = {
            "rich_text": [{"text": {"content": image_prompt[:2000]}}]
        }
    if image_url:
        properties["Image"] = {
            "files": [{"name": "featured-image.jpg", "type": "external", "external": {"url": image_url}}]
        }

    payload = {"properties": properties}

    resp = requests.patch(
        f"{NOTION_API}/pages/{page_id}",
        headers=_headers(),
        json=payload,
    )
    resp.raise_for_status()
    result = resp.json()

    # Make-Webhook feuern → E-Mail-Alert an Richard
    try:
        notion_url = f"{NOTION_PAGE_BASE_URL}{page_id.replace('-', '')}"
        webhook_payload = {
            "title": title or page_id,
            "influencer": influencer,
            "notion_url": notion_url,
        }
        requests.post(MAKE_REVIEW_WEBHOOK, json=webhook_payload, timeout=10)
        print(f"  Make-Webhook gefeuert: Ready to Review Alert", flush=True)
    except Exception as e:
        print(f"  Make-Webhook fehlgeschlagen (nicht kritisch): {e}", flush=True)

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
    resp = requests.post(
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


def get_entry_by_url(post_url: str) -> dict | None:
    """Gibt den Notion-Eintrag für eine bestimmte Post-URL zurück."""
    payload = {
        "filter": {
            "property": "LinkedIn Post URL",
            "url": {"equals": post_url}
        }
    }
    resp = requests.post(
        f"{NOTION_API}/databases/{NOTION_DB_ID}/query",
        headers=_headers(),
        json=payload,
    )
    resp.raise_for_status()
    results = resp.json().get("results", [])
    return results[0] if results else None


def get_entry_by_page_id(page_id: str) -> dict:
    """Gibt einen Notion-Eintrag anhand seiner Page ID zurück."""
    resp = requests.get(
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
