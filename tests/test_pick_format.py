"""Tests for pick_format. The anthropic client is mocked — no API calls."""
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import post_scorer

POST = {"influencer": "Jane", "post_text": "A post about cold email reply rates."}


def _mock_client(reply_text):
    resp = MagicMock()
    resp.content = [MagicMock(text=reply_text)]
    c = MagicMock()
    c.messages.create.return_value = resp
    return c


def test_returns_llm_choice_when_allowed():
    with patch.object(post_scorer, "client", _mock_client("POV")):
        assert post_scorer.pick_format(POST, ["Opinion"]) == "POV"


def test_never_returns_most_recent_even_if_llm_picks_it():
    # LLM disobeys and returns the forbidden (most recent) format.
    with patch.object(post_scorer, "client", _mock_client("Opinion")):
        result = post_scorer.pick_format(POST, ["Opinion"])
    assert result != "Opinion"
    assert result in ("POV", "Signature")


def test_empty_recent_returns_valid_format():
    with patch.object(post_scorer, "client", _mock_client("Signature")):
        assert post_scorer.pick_format(POST, []) == "Signature"


def test_unrecognized_llm_output_falls_back_without_raising():
    with patch.object(post_scorer, "client", _mock_client("banana")):
        result = post_scorer.pick_format(POST, ["POV"])
    assert result in ("Opinion", "Signature")  # valid, and != most recent


def test_api_exception_falls_back():
    c = MagicMock()
    c.messages.create.side_effect = RuntimeError("api down")
    with patch.object(post_scorer, "client", c):
        result = post_scorer.pick_format(POST, ["Signature"])
    assert result in ("Opinion", "POV")


def test_single_candidate_skips_llm_and_beats_anti_repeat():
    c = MagicMock()  # must not be called
    with patch.object(post_scorer, "client", c):
        assert post_scorer.pick_format(POST, ["CaseProof"], candidates=["CaseProof"]) == "CaseProof"
    c.messages.create.assert_not_called()


def test_candidates_restrict_choice():
    with patch.object(post_scorer, "client", _mock_client("Opinion")):
        result = post_scorer.pick_format(POST, [], candidates=["POV", "Signature"])
    assert result in ("POV", "Signature")  # Opinion not offered


def test_candidate_prompt_lists_only_candidates():
    c = _mock_client("POV")
    with patch.object(post_scorer, "client", c):
        post_scorer.pick_format(POST, [], candidates=["POV", "Signature"])
    prompt = c.messages.create.call_args.kwargs["messages"][0]["content"]
    assert "POV" in prompt and "Signature" in prompt and "Opinion" not in prompt
