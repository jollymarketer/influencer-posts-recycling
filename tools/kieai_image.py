"""
kie.ai Bildgenerierung — Nano Banana 2 Model
API: https://api.kie.ai
Polling alle 10 Sekunden bis Bild fertig oder Timeout (15 Min).
"""

import io
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

LOGO_PATH = os.path.join(os.path.dirname(__file__), "..", "Resources", "Jolly Marketer_logo_horizontal.png")
LOGO_PADDING = 28       # Abstand vom Rand in px
LOGO_MAX_WIDTH_RATIO = 0.22  # Logo nimmt max. 22% der Bildbreite ein


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


def generate_image(prompt: str, resolution: str = "1K", aspect_ratio: str = "1:1") -> str:
    """
    Generiert ein Bild via kie.ai Nano Banana Pro Model.

    Args:
        prompt: Bildgenerierungs-Prompt (Infografik-Beschreibung)
        resolution: "1K", "2K" oder "4K" (Standard: 1K)
        aspect_ratio: "1:1", "16:9" etc. (Standard: 1:1 für LinkedIn)

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
        "model": "nano-banana-2",
        "input": {
            "prompt": prompt,
            "image_input": [],
            "aspect_ratio": aspect_ratio,
            "resolution": resolution,
            "output_format": "png",
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
            import json
            result = json.loads(result_json_str)
            urls = result.get("resultUrls", [])
            if not urls:
                raise RuntimeError("kie.ai: Kein Bild in resultUrls")
            image_url = urls[0]
            print(f"  kie.ai: FERTIG -> {image_url}", flush=True)

            # Logo einblenden und lokal speichern
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

            return image_url

        elif state == "fail":
            fail_msg = poll_data["data"].get("failMsg", "Unbekannter Fehler")
            raise RuntimeError(f"kie.ai Generierung fehlgeschlagen: {fail_msg}")

        # Bei waiting / queuing / generating → weiter pollen

    raise RuntimeError(f"kie.ai Timeout nach {MAX_POLL_ATTEMPTS * POLL_INTERVAL_SECONDS}s")


if __name__ == "__main__":
    # Standalone-Test
    test_prompt = (
        "Modern B2B SaaS infographic about RevOps pipeline efficiency. "
        "Clean dark background, data visualization, funnel chart, "
        "professional design, blue and white color scheme."
    )
    print("Teste kie.ai Bildgenerierung ...")
    try:
        url = generate_image(test_prompt)
        print(f"✓ Bild-URL: {url}")
    except Exception as e:
        print(f"✗ Fehler: {e}", file=sys.stderr)
        sys.exit(1)
