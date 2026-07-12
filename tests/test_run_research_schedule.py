"""The weekday gate in run_research.main(): Thursday -> keyword scrape, Friday -> clustering,
other days -> neither. run_daily always runs. Side-effect functions are mocked (no network)."""
import datetime as dt
from unittest.mock import patch

import pytest

import run_research

THURSDAY = dt.datetime(2026, 6, 11, tzinfo=dt.timezone.utc)  # weekday 3
FRIDAY = dt.datetime(2026, 6, 12, tzinfo=dt.timezone.utc)    # weekday 4
MONDAY = dt.datetime(2026, 6, 8, tzinfo=dt.timezone.utc)     # weekday 0


def _run(now):
    with patch.object(run_research, "run_daily") as rd, \
         patch.object(run_research, "scrape_and_persist") as ks, \
         patch.object(run_research, "run_topic_mining") as tm, \
         patch.object(run_research, "sync_topic_decisions"):
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


def test_daily_sysexit_does_not_kill_friday_mining():
    """run_daily's sys.exit(1) paths must not eat the Friday mining; the daily
    exit code is re-raised AFTER the weekly jobs (keeps Railway ON_FAILURE retry)."""
    with patch.object(run_research, "run_daily", side_effect=SystemExit(1)), \
         patch.object(run_research, "scrape_and_persist") as ks, \
         patch.object(run_research, "run_topic_mining") as tm, \
         patch.object(run_research, "sync_topic_decisions"):
        with pytest.raises(SystemExit) as exc:
            run_research.main(now=FRIDAY)
    tm.assert_called_once()
    ks.assert_not_called()
    assert exc.value.code == 1


def test_daily_crash_does_not_kill_friday_mining():
    with patch.object(run_research, "run_daily", side_effect=RuntimeError("boom")), \
         patch.object(run_research, "run_topic_mining") as tm, \
         patch.object(run_research, "sync_topic_decisions"):
        with pytest.raises(SystemExit) as exc:
            run_research.main(now=FRIDAY)
    tm.assert_called_once()
    assert exc.value.code == 1


def test_decisions_sync_runs_daily_and_is_nonfatal():
    """Sync runs on any weekday (topic_mining feature on) and must never raise."""
    with patch.object(run_research, "run_daily"), \
         patch.object(run_research, "sync_topic_decisions",
                      side_effect=RuntimeError("supabase down")) as sync:
        run_research.main(now=MONDAY)  # must not raise
    sync.assert_called_once()


def test_daily_ok_exits_cleanly():
    rd, ks, tm = _run(FRIDAY)  # run_daily mocked = success; must NOT raise SystemExit
    rd.assert_called_once()
    tm.assert_called_once()
