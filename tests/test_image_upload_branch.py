"""Bild-Uploads duerfen master nicht anfassen.

Railway deployt bei jedem Push auf den verbundenen Branch (master) automatisch,
und ein neues Deployment ersetzt das laufende und stoppt dessen Container. Ein
Bild-Upload mitten im Slate-Bau haette den eigenen Lauf abgeschossen (Befund
2026-07-27). Deshalb schreibt der Upload auf einen eigenen Branch.
"""
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import kieai_image


def _run_upload(existing: bool):
    get_resp = MagicMock(status_code=200 if existing else 404)
    get_resp.json.return_value = {"sha": "abc123"} if existing else {}
    put_resp = MagicMock(status_code=201)
    put_resp.raise_for_status.return_value = None
    with patch.object(kieai_image, "GITHUB_TOKEN", "t"), \
         patch.object(kieai_image.requests, "get", return_value=get_resp) as get_mock, \
         patch.object(kieai_image.requests, "put", return_value=put_resp) as put_mock:
        url = kieai_image._upload_to_github(b"png-bytes", "generated_x.png")
    return url, get_mock, put_mock


def test_upload_targets_the_images_branch_not_master():
    url, get_mock, put_mock = _run_upload(existing=False)
    assert put_mock.call_args.kwargs["json"]["branch"] == kieai_image.GITHUB_IMAGES_BRANCH
    assert kieai_image.GITHUB_IMAGES_BRANCH != "master"


def test_returned_raw_url_points_at_the_images_branch():
    url, _, _ = _run_upload(existing=False)
    assert f"/{kieai_image.GITHUB_IMAGES_BRANCH}/{kieai_image.GITHUB_IMAGES_PATH}/" in url
    assert "/master/" not in url


def test_existing_file_sha_is_read_from_the_same_branch():
    # Ein ref=master beim Lesen und branch=images beim Schreiben ergaebe 422,
    # sobald eine Datei zweimal hochgeladen wird (Bild-Reparatur-Pfad).
    _, get_mock, put_mock = _run_upload(existing=True)
    assert get_mock.call_args.kwargs["params"]["ref"] == kieai_image.GITHUB_IMAGES_BRANCH
    assert put_mock.call_args.kwargs["json"]["sha"] == "abc123"


def test_new_file_is_uploaded_without_a_sha():
    _, _, put_mock = _run_upload(existing=False)
    assert "sha" not in put_mock.call_args.kwargs["json"]
