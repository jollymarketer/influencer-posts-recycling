"""Tests for _kie_request_with_retry: kie.ai returns HTTP 200 with a body-level
`code` field. A body-code >= 500 ("Server exception") must be retried like an
HTTP 5xx, not bubbled straight up. time.sleep is patched out so tests are fast."""
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import kieai_image


def _resp(status_code=200, body=None):
    r = MagicMock(status_code=status_code)
    r.json.return_value = body if body is not None else {"code": 200, "data": {}}
    r.text = str(body)
    r.raise_for_status.return_value = None
    return r


def test_body_code_500_then_200_retries_and_succeeds(monkeypatch):
    monkeypatch.setattr(kieai_image.time, "sleep", lambda *a: None)
    server_error = _resp(body={"code": 500, "msg": "Server exception", "data": None})
    ok = _resp(body={"code": 200, "data": {"taskId": "abc"}})
    with patch.object(kieai_image.requests, "request", side_effect=[server_error, ok]) as m:
        out = kieai_image._kie_request_with_retry("POST", "http://x")
    assert m.call_count == 2  # first body-500 retried, second succeeded
    assert out.json()["code"] == 200


def test_body_code_200_returns_immediately_no_retry(monkeypatch):
    monkeypatch.setattr(kieai_image.time, "sleep", lambda *a: None)
    ok = _resp(body={"code": 200, "data": {"taskId": "abc"}})
    with patch.object(kieai_image.requests, "request", side_effect=[ok]) as m:
        out = kieai_image._kie_request_with_retry("GET", "http://x")
    assert m.call_count == 1
    assert out.json()["code"] == 200


def test_persistent_body_code_500_exhausts_and_returns_last(monkeypatch):
    """A persistent backend outage (model down) is retried HTTP_MAX_ATTEMPTS times,
    then the last 500 response is returned for the caller to raise on."""
    monkeypatch.setattr(kieai_image.time, "sleep", lambda *a: None)
    server_error = _resp(body={"code": 500, "msg": "Server exception", "data": None})
    with patch.object(kieai_image.requests, "request", return_value=server_error) as m:
        out = kieai_image._kie_request_with_retry("POST", "http://x")
    assert m.call_count == kieai_image.HTTP_MAX_ATTEMPTS
    assert out.json()["code"] == 500
