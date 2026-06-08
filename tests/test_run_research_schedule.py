"""The weekday gate in run_research.main(): Thursday -> keyword scrape, Friday -> clustering,
other days -> neither. run_daily always runs. Side-effect functions are mocked (no network)."""
import datetime as dt
from unittest.mock import patch

import run_research

THURSDAY = dt.datetime(2026, 6, 11, tzinfo=dt.timezone.utc)  # weekday 3
FRIDAY = dt.datetime(2026, 6, 12, tzinfo=dt.timezone.utc)    # weekday 4
MONDAY = dt.datetime(2026, 6, 8, tzinfo=dt.timezone.utc)     # weekday 0


def _run(now):
    with patch.object(run_research, "run_daily") as rd, \
         patch.object(run_research, "scrape_and_persist") as ks, \
         patch.object(run_research, "run_topic_mining") as tm:
        run_research.main(now=now)
        return rd, ks, tm


def test_thursday_runs_keyword_scrape_only():
    rd, ks, tm = _run(THURSDAY)
    rd.assert_called_once()
    ks.assert_called_once()
    tm.assert_not_called()


def test_friday_runs_clustering_only():
    rd, ks, tm = _run(FRIDAY)
    rd.assert_called_once()
    tm.assert_called_once()
    ks.assert_not_called()


def test_other_day_runs_neither_extra():
    rd, ks, tm = _run(MONDAY)
    rd.assert_called_once()
    ks.assert_not_called()
    tm.assert_not_called()
