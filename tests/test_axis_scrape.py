"""Tests fuer den achsengetrennten Begriffs-Scrape. Kein Apify-, kein DB-Aufruf."""
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import run_axis_scrape


def _cfg(by_axis):
    c = MagicMock()
    c.NAME = "testmandant"
    c.KEYWORDS_BY_AXIS = by_axis
    return c


def test_every_axis_writes_its_own_source():
    """Die Herkunft ist der ganze Zweck des Laufs: ohne sie kann das Clustern
    nicht je Achse arbeiten."""
    cfg = _cfg({"a": ["k1"], "b": ["k2"]})
    with patch.object(run_axis_scrape, "scrape_keyword_posts", return_value=[{"x": 1}]), \
         patch.object(run_axis_scrape, "upsert_posts", return_value=1) as mock_up:
        run_axis_scrape.run(cfg=cfg)
    quellen = [c.kwargs["source"] for c in mock_up.call_args_list]
    assert quellen == ["linkedin_search:a", "linkedin_search:b"]


def test_axes_subset_scrapes_only_those():
    cfg = _cfg({"a": ["k1"], "b": ["k2"]})
    with patch.object(run_axis_scrape, "scrape_keyword_posts", return_value=[]) as mock_scr, \
         patch.object(run_axis_scrape, "upsert_posts", return_value=0):
        run_axis_scrape.run(axes=["b"], cfg=cfg)
    assert mock_scr.call_count == 1
    assert mock_scr.call_args.args[0] == ["k2"]


def test_unknown_axis_aborts_before_spending():
    cfg = _cfg({"a": ["k1"]})
    with patch.object(run_axis_scrape, "scrape_keyword_posts") as mock_scr:
        with pytest.raises(SystemExit):
            run_axis_scrape.run(axes=["gibtsnicht"], cfg=cfg)
    assert mock_scr.called is False


def test_no_write_skips_upsert():
    cfg = _cfg({"a": ["k1"]})
    with patch.object(run_axis_scrape, "scrape_keyword_posts", return_value=[{"x": 1}]), \
         patch.object(run_axis_scrape, "upsert_posts") as mock_up:
        run_axis_scrape.run(write=False, cfg=cfg)
    assert mock_up.called is False


def test_missing_mapping_aborts():
    cfg = MagicMock()
    cfg.NAME = "ohne"
    cfg.KEYWORDS_BY_AXIS = {}
    with pytest.raises(SystemExit):
        run_axis_scrape.axis_keywords(cfg)


def test_swot_mapping_covers_every_keyword_exactly_once():
    os.environ["CLIENT"] = "swot"
    from clients import load_client
    cfg = load_client()
    gemappt = [k for v in cfg.KEYWORDS_BY_AXIS.values() for k in v]
    assert len(gemappt) == len(set(gemappt))
    assert set(gemappt) == set(cfg.KEYWORDS)
