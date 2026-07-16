"""Per-tenant scoring model + classify fields (slate model, spec 2026-07-16)."""
import importlib
import json
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import post_scorer

jolly = importlib.import_module("clients.jolly.config")
lisocon = importlib.import_module("clients.lisocon.config")


def test_lisocon_scoring_model_is_sonnet():
    assert lisocon.SCORING_MODEL == "claude-sonnet-4-6"


def test_jolly_has_no_scoring_model_override():
    assert getattr(jolly, "SCORING_MODEL", None) is None


def test_score_posts_uses_config_model(monkeypatch):
    fake = MagicMock()
    fake.content = [MagicMock(text=json.dumps({
        "topic_fit": 8, "icp_relevanz": 7, "recyclierbarkeit": 8,
        "einzigartigkeit": 6, "themen_diversitaet": 8, "reasoning": "ok"}))]
    with patch.object(post_scorer, "SCORING_MODEL", "claude-sonnet-4-6"), \
         patch.object(post_scorer.client.messages, "create", return_value=fake) as mock_create:
        post_scorer.score_posts([{
            "influencer": "T", "post_text": "x", "post_url": "u",
            "engagement": {"likes": 0, "comments": 0, "shares": 0}}])
    assert mock_create.call_args.kwargs["model"] == "claude-sonnet-4-6"


_CLASSIFY_JSON = {
    "topic_fit": 8, "icp_relevanz": 7, "recyclierbarkeit": 8,
    "einzigartigkeit": 6, "themen_diversitaet": 8, "reasoning": "ok",
    "persona": "kaeufer", "voc_hit": "versteckte DTP-Kostenlinie",
    "topic_angle_de": "Warum jede Sprachversion ein zweites Budget frisst",
    "matrix_job": "Perspective", "matrix_stage": "Awareness",
}


def _scored_with(monkeypatch, payload, classify):
    fake = MagicMock()
    fake.content = [MagicMock(text=json.dumps(payload))]
    with patch.object(post_scorer.client.messages, "create", return_value=fake) as mc:
        out = post_scorer.score_posts([{
            "influencer": "T", "post_text": "x", "post_url": "u",
            "engagement": {"likes": 0, "comments": 0, "shares": 0}}],
            classify=classify)
    return out, mc


def test_classify_adds_fields_to_result(monkeypatch):
    out, _ = _scored_with(monkeypatch, _CLASSIFY_JSON, classify=True)
    assert out[0]["persona"] == "kaeufer"
    assert out[0]["voc_hit"] == "versteckte DTP-Kostenlinie"
    assert out[0]["topic_angle_de"].startswith("Warum")
    assert out[0]["matrix_job"] == "Perspective"
    assert out[0]["matrix_stage"] == "Awareness"


def test_classify_prompt_contains_classification_block(monkeypatch):
    _, mc = _scored_with(monkeypatch, _CLASSIFY_JSON, classify=True)
    prompt = mc.call_args.kwargs["messages"][0]["content"]
    assert "persona" in prompt and "topic_angle_de" in prompt
    assert "matrix_job" in prompt


def test_no_classify_prompt_unchanged(monkeypatch):
    base = {"topic_fit": 8, "icp_relevanz": 7, "recyclierbarkeit": 8,
            "einzigartigkeit": 6, "themen_diversitaet": 8, "reasoning": "ok"}
    _, mc = _scored_with(monkeypatch, base, classify=False)
    prompt = mc.call_args.kwargs["messages"][0]["content"]
    assert "topic_angle_de" not in prompt
    assert "matrix_job" not in prompt


def test_classify_missing_fields_fall_back_to_empty(monkeypatch):
    base = {"topic_fit": 8, "icp_relevanz": 7, "recyclierbarkeit": 8,
            "einzigartigkeit": 6, "themen_diversitaet": 8, "reasoning": "ok"}
    out, _ = _scored_with(monkeypatch, base, classify=True)
    assert out[0]["persona"] == ""
    assert out[0]["topic_angle_de"] == ""
