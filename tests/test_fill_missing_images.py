"""Phase A: Bilder nur fuer text-freigegebene Zeilen ohne Bild."""
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import image_repair

_SECTIONS = {"image_url": "", "de_draft": "d", "en_draft": "",
             "post_text": "t", "post_url": "u", "skeleton": "s",
             "image_prompt": "prompt text"}


def test_fill_missing_images_generates_with_status_approved():
    rows = [{"page_id": "p1", "post_url": "u", "archetype": "stat_hero"}]
    with patch.object(image_repair, "get_approved_missing_image", return_value=rows), \
         patch.object(image_repair, "extract_body_sections", return_value=_SECTIONS), \
         patch.object(image_repair, "regenerate_page_image",
                      return_value="https://img/x.png") as regen:
        n = image_repair.fill_missing_images()
    assert n == 1
    kwargs = regen.call_args.kwargs
    assert kwargs["strip_marks"] is True          # stat_hero strippt Marks
    assert kwargs["status"] == "Approved"          # Text-Freigabe bleibt erhalten


def test_fill_missing_images_infographic_keeps_marks():
    rows = [{"page_id": "p1", "post_url": "u", "archetype": "structured_infographic"}]
    with patch.object(image_repair, "get_approved_missing_image", return_value=rows), \
         patch.object(image_repair, "extract_body_sections", return_value=_SECTIONS), \
         patch.object(image_repair, "regenerate_page_image",
                      return_value="https://img/x.png") as regen:
        image_repair.fill_missing_images()
    assert regen.call_args.kwargs["strip_marks"] is False


def test_fill_missing_images_failure_sets_image_failed():
    rows = [{"page_id": "p1", "post_url": "u", "archetype": ""}]
    with patch.object(image_repair, "get_approved_missing_image", return_value=rows), \
         patch.object(image_repair, "extract_body_sections", return_value=_SECTIONS), \
         patch.object(image_repair, "regenerate_page_image",
                      side_effect=RuntimeError("kie down")), \
         patch.object(image_repair, "set_post_status") as status_mock:
        n = image_repair.fill_missing_images()
    assert n == 0
    status_mock.assert_called_once_with("p1", "Image Failed")


def test_repair_wrong_images_still_defaults_to_ready_to_review():
    """Bestands-Verhalten des Repair-Pfads unveraendert (Regression-Pin)."""
    page = {"id": "p9", "properties": {"Bild-Variante": {"select": {"name": "stat_hero"}}}}
    with patch.object(image_repair, "_query_pages_by_status", return_value=[page]), \
         patch.object(image_repair, "extract_body_sections", return_value=_SECTIONS), \
         patch.object(image_repair, "generate_image", return_value="https://img/x.png"), \
         patch.object(image_repair, "_rebuild_page_body"), \
         patch.object(image_repair, "_notion_request") as req:
        n = image_repair.repair_wrong_images()
    assert n == 1
    body = req.call_args.kwargs["json"]
    assert body["properties"]["Status"]["select"]["name"] == "Ready to Review"
