"""Pin-Tests: Notion-Titel darf NIE Influencer-Name oder Original-Text tragen.

Hintergrund (Leak 2026-07-10): Der Notion-Titel wurde in Make als LinkedIn-
Bild-Medien-Titel gemappt. LinkedIn rendert den Medien-Titel in Notification-
Kacheln und indexiert ihn in der Suche - Original-Autor + Original-Wortlaut
waren dadurch oeffentlich mit den Recycling-Posts verknuepft. Diese Tests
nageln fest, dass der Titel nur aus dem eigenen Draft-Hook (ohnehin
oeffentlich) oder einem neutralen Fallback besteht.
"""
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import notion_db

ORIGINAL = "Dear Luke Ward, here is my reply to your cold email which hopefully will boost your stats"
DRAFT = "Die meisten Cold Emails scheitern nicht am Kanal.\nZweite Zeile des Drafts."


def _created_title(monkeypatch, **kw):
    monkeypatch.setenv("NOTION_TOKEN", "tok")
    resp = MagicMock(status_code=200, ok=True)
    resp.json.return_value = {"id": "page1"}
    resp.raise_for_status.return_value = None
    with patch("tools.notion_db._notion_request", return_value=resp) as m:
        notion_db.create_post_entry(
            influencer="Jordan Crawford",
            post_url="https://linkedin.com/posts/x",
            post_text=ORIGINAL,
            post_date="2026-07-11",
            **kw,
        )
    payload = m.call_args.kwargs["json"]
    return payload["properties"]["Title"]["title"][0]["text"]["content"]


def test_title_contains_no_influencer_name(monkeypatch):
    title = _created_title(monkeypatch, title_hook=DRAFT)
    assert "Jordan" not in title and "Crawford" not in title


def test_title_contains_no_original_text(monkeypatch):
    title = _created_title(monkeypatch, title_hook=DRAFT)
    assert "Luke Ward" not in title
    # kein 15+-Zeichen-Fragment des Originals im Titel
    for i in range(0, len(ORIGINAL) - 15, 5):
        assert ORIGINAL[i:i + 15] not in title


def test_title_uses_first_draft_line(monkeypatch):
    title = _created_title(monkeypatch, title_hook=DRAFT)
    assert title.startswith("Die meisten Cold Emails scheitern nicht am Kanal.")
    assert "Zweite Zeile" not in title  # nur erste Zeile (Hook)


def test_title_fallback_is_neutral(monkeypatch):
    title = _created_title(monkeypatch)  # kein Hook
    assert title == "Recycling-Post 2026-07-11"
    assert "Jordan" not in title and "Luke Ward" not in title
