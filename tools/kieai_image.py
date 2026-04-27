"""
kie.ai Bildgenerierung — gpt-image-2-text-to-image
API: https://api.kie.ai
Polling alle 10 Sekunden bis Bild fertig oder Timeout (15 Min).
"""

import base64
import io
import json
import os
import sys
import time

import requests
from dotenv import load_dotenv
from PIL import Image

load_dotenv()

KIEAI_API_KEY = os.getenv("KIEAI_API_KEY", "19445902ad562e4343e93799081400b9")
KIEAI_BASE_URL = "https://api.kie.ai/api/v1"
POLL_INTERVAL_SECONDS = 10
MAX_POLL_ATTEMPTS = 90  # 90 × 10s = 15 Minuten

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = "jollymarketer/influencer-posts-recycling"
GITHUB_IMAGES_PATH = "images"

LOGO_PATH = os.path.join(os.path.dirname(__file__), "..", "Resources", "Jolly Marketer_logo_horizontal.png")
LOGO_PADDING = 28       # Abstand vom Rand in px
LOGO_MAX_WIDTH_RATIO = 0.11  # Logo nimmt max. 11% der Bildbreite ein (50% kleiner als zuvor)


def _overlay_logo(image_bytes: bytes) -> bytes:
    """Blendet das Jolly Marketer Logo unten rechts über das generierte Bild."""
    base = Image.open(io.BytesIO(image_bytes)).convert("RGBA")

    logo = Image.open(LOGO_PATH).convert("RGBA")

    max_logo_w = int(base.width * LOGO_MAX_WIDTH_RATIO)
    ratio = max_logo_w / logo.width
    logo_w = max_logo_w
    logo_h = int(logo.height * ratio)
    logo = logo.resize((logo_w, logo_h), Image.LANCZOS)

    x = base.width - logo_w - LOGO_PADDING
    y = base.height - logo_h - LOGO_PADDING

    base.paste(logo, (x, y), logo)

    out = io.BytesIO()
    base.save(out, format="PNG")
    return out.getvalue()


def _upload_to_github(image_bytes: bytes, filename: str) -> str:
    """Lädt Bild zu GitHub hoch und gibt permanente raw.githubusercontent.com URL zurück."""
    if not GITHUB_TOKEN:
        raise RuntimeError("GITHUB_TOKEN nicht gesetzt")

    path = f"{GITHUB_IMAGES_PATH}/{filename}"
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"

    content_b64 = base64.b64encode(image_bytes).decode("utf-8")

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Content-Type": "application/json",
    }

    # SHA holen falls Datei bereits existiert (sonst 422 Conflict)
    sha = None
    check = requests.get(api_url, headers=headers, timeout=30)
    if check.status_code == 200:
        sha = check.json().get("sha")

    payload = {
        "message": f"Add generated image {filename}",
        "content": content_b64,
    }
    if sha:
        payload["sha"] = sha

    resp = requests.put(api_url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()

    raw_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/master/{path}"
    print(f"  GitHub Upload: {raw_url}", flush=True)
    return raw_url


def generate_image(prompt: str, aspect_ratio: str = "3:2") -> str:
    """
    Generiert ein Bild via kie.ai gpt-image-2-text-to-image.

    Args:
        prompt: Bildgenerierungs-Prompt
        aspect_ratio: z.B. "3:2" (LinkedIn-Feed), "1:1", "16:9" (Standard: 3:2)

    Returns:
        URL des fertigen Bildes

    Raises:
        RuntimeError: Wenn Generierung fehlschlägt oder Timeout erreicht
    """
    headers = {
        "Authorization": f"Bearer {KIEAI_API_KEY}",
        "Content-Type": "application/json",
    }

    # Schritt 1: Job starten
    print("  kie.ai: Starte Bildgenerierung ...", flush=True)
    create_payload = {
        "model": "gpt-image-2-text-to-image",
        "input": {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "nsfw_checker": False,
        },
    }

    resp = requests.post(
        f"{KIEAI_BASE_URL}/jobs/createTask",
        headers=headers,
        json=create_payload,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    if data.get("code") != 200:
        raise RuntimeError(f"kie.ai Fehler beim Erstellen: {data}")

    task_id = data["data"]["taskId"]
    print(f"  kie.ai: Task ID = {task_id}", flush=True)

    # Schritt 2: Polling bis fertig
    for attempt in range(1, MAX_POLL_ATTEMPTS + 1):
        time.sleep(POLL_INTERVAL_SECONDS)
        print(f"  kie.ai: Polling #{attempt} ...", flush=True)

        poll_resp = requests.get(
            f"{KIEAI_BASE_URL}/jobs/recordInfo",
            headers=headers,
            params={"taskId": task_id},
            timeout=30,
        )
        poll_resp.raise_for_status()
        poll_data = poll_resp.json()

        if poll_data.get("code") != 200:
            raise RuntimeError(f"kie.ai Polling-Fehler: {poll_data}")

        state = poll_data["data"].get("state", "")
        print(f"  kie.ai: Status = {state}", flush=True)

        if state == "success":
            result_json_str = poll_data["data"].get("resultJson", "{}")
            result = json.loads(result_json_str)
            urls = result.get("resultUrls", [])
            if not urls:
                raise RuntimeError("kie.ai: Kein Bild in resultUrls")
            image_url = urls[0]
            print(f"  kie.ai: FERTIG -> {image_url}", flush=True)

            # Logo einblenden
            final_bytes = None
            try:
                img_bytes = requests.get(image_url, timeout=30).content
                final_bytes = _overlay_logo(img_bytes)
                os.makedirs(".tmp", exist_ok=True)
                local_path = f".tmp/generated_{task_id[:8]}.png"
                with open(local_path, "wb") as f:
                    f.write(final_bytes)
                print(f"  Logo eingeblendet -> {local_path}", flush=True)
            except Exception as e:
                print(f"  Logo-Overlay fehlgeschlagen: {e}", flush=True)

            # Permanenten Upload versuchen (mit Logo falls verfuegbar)
            upload_bytes = final_bytes if final_bytes is not None else requests.get(image_url, timeout=30).content
            filename = f"generated_{task_id[:8]}.png"

            # Versuch 1: catbox.moe (kostenlos, permanent, kein Account noetig)
            try:
                resp_catbox = requests.post(
                    "https://catbox.moe/user/api.php",
                    data={"reqtype": "fileupload"},
                    files={"fileToUpload": (filename, upload_bytes, "image/png")},
                    timeout=30,
                )
                body = resp_catbox.text.strip()
                if resp_catbox.ok and body.startswith("http"):
                    print(f"  catbox.moe Upload: {body}", flush=True)
                    return body
                print(
                    f"  catbox.moe abgelehnt (HTTP {resp_catbox.status_code}): {body[:200]} — versuche GitHub ...",
                    flush=True,
                )
            except Exception as e:
                print(f"  catbox.moe Exception: {e} — versuche GitHub ...", flush=True)

            # Versuch 2: GitHub (nur fuer oeffentliche Repos)
            try:
                permanent_url = _upload_to_github(upload_bytes, filename)
                return permanent_url
            except Exception as e2:
                print(f"  GitHub Upload fehlgeschlagen: {e2}", flush=True)

            # Letzter Fallback: kie.ai URL (kein Logo, laeuft ab)
            print(f"  Fallback: kie.ai URL (kein Logo, laeuft ab)", flush=True)
            return image_url

        elif state == "fail":
            fail_msg = poll_data["data"].get("failMsg", "Unbekannter Fehler")
            raise RuntimeError(f"kie.ai Generierung fehlgeschlagen: {fail_msg}")

        # Bei waiting / queuing / generating → weiter pollen

    raise RuntimeError(f"kie.ai Timeout nach {MAX_POLL_ATTEMPTS * POLL_INTERVAL_SECONDS}s")


if __name__ == "__main__":
    # Standalone-Test
    test_prompt = (
        "Premium editorial LinkedIn featured image about RevOps. "
        "Headline 'WAHRHEIT SCHLAEGT KOMFORT'. Deep Navy + Bright Orange accent on white. "
        "Minimum 20% negative space in the lower-right quadrant for logo overlay."
    )
    print("Teste kie.ai Bildgenerierung ...")
    try:
        url = generate_image(test_prompt)
        print(f"OK Bild-URL: {url}")
    except Exception as e:
        print(f"FEHLER: {e}", file=sys.stderr)
        sys.exit(1)
