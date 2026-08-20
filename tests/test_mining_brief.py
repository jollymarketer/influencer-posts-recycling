"""Tests fuer den mandantenfaehigen Mining-Brief im Topic-Clusterer."""
import importlib
import os
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import topic_clusterer as tc


def _posts():
    return [{"influencer": "A", "post_text": "Beitragstext eins", "likes": 5,
             "comments": 1, "shares": 0},
            {"influencer": "B", "post_text": "Beitragstext zwei", "likes": 9,
             "comments": 2, "shares": 1}]


def test_build_user_prompt_uses_client_brief():
    cfg = SimpleNamespace(NAME="x", TOKENS={"TOPIC_MINING_BRIEF": "BRIEF-MARKER-12345"})
    prompt = tc._build_user_prompt(_posts(), ["Alter Titel"], taste=None, cfg=cfg)
    assert "BRIEF-MARKER-12345" in prompt
    assert "Beitragstext eins" in prompt
    assert "AVOID topics that duplicate" in prompt and "Alter Titel" in prompt
    assert "Return ONLY a JSON array" in prompt


def test_build_user_prompt_missing_brief_raises():
    cfg = SimpleNamespace(NAME="x", TOKENS={})
    with pytest.raises(RuntimeError, match="TOPIC_MINING_BRIEF"):
        tc._build_user_prompt(_posts(), [], taste=None, cfg=cfg)


def test_jolly_brief_carries_moved_blog_text():
    jolly = importlib.import_module("clients.jolly.config")
    brief = jolly.TOKENS["TOPIC_MINING_BRIEF"]
    assert "jollymarketer.com" in brief
    assert "ULTRA-LONG-TAIL" in brief
    assert "HubSpot" in brief


def test_swot_brief_targets_linkedin_not_blog():
    swot = importlib.import_module("clients.swot.config")
    brief = swot.TOKENS["TOPIC_MINING_BRIEF"]
    assert "LinkedIn" in brief
    assert "jollymarketer.com" not in brief
    # Vendor-Reframe-Regel muss im Brief stehen, nicht nur in der Rolle.
    assert "LucaNet" in brief


def test_taste_block_still_rendered():
    cfg = SimpleNamespace(NAME="x", TOKENS={"TOPIC_MINING_BRIEF": "B"})
    taste = {"picked": ["Gutes Thema"], "rejected": ["Schlechtes Thema"]}
    prompt = tc._build_user_prompt(_posts(), [], taste=taste, cfg=cfg)
    assert "Gutes Thema" in prompt and "Schlechtes Thema" in prompt
