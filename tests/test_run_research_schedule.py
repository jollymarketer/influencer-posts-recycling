"""The weekday gate in run_research.main(): Thursday -> keyword scrape, Friday -> clustering,
other days -> neither. run_daily always runs. Side-effect functions are mocked (no network)."""
import datetime as dt
from unittest.mock import patch

import pytest

import run_research

THURSDAY = dt.datetime(2026, 6, 11, tzinfo=dt.timezone.utc)  # weekday 3
FRIDAY = dt.datetime(2026, 6, 12, tzinfo=dt.timezone.utc)    # weekday 4
MONDAY = dt.datetime(2026, 6, 8, tzinfo=dt.timezone.utc)     # weekday 0


@pytest.fixture(autouse=True)
def _system_check_go():
    """Phase 0 telefoniert (Notion, Apify, Anthropic). Fuer die Scheduling-Tests
    steht sie auf GO; die Gate-Tests unten patchen sie erneut auf NO-GO."""
    with patch.object(run_research, "run_system_check", return_value=True):
        yield


def _run(now):
    with patch.object(run_research, "run_daily") as rd, \
         patch.object(run_research, "scrape_and_persist") as ks, \
         patch.object(run_research, "run_topic_mining") as tm, \
         patch.object(run_research, "run_readback"), \
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
         patch.object(run_research, "run_readback"), \
         patch.object(run_research, "sync_topic_decisions"):
        with pytest.raises(SystemExit) as exc:
            run_research.main(now=FRIDAY)
    tm.assert_called_once()
    ks.assert_not_called()
    assert exc.value.code == 1


def test_daily_crash_does_not_kill_friday_mining():
    with patch.object(run_research, "run_daily", side_effect=RuntimeError("boom")), \
         patch.object(run_research, "run_topic_mining") as tm, \
         patch.object(run_research, "run_readback"), \
         patch.object(run_research, "sync_topic_decisions"):
        with pytest.raises(SystemExit) as exc:
            run_research.main(now=FRIDAY)
    tm.assert_called_once()
    assert exc.value.code == 1


def test_decisions_sync_runs_daily_and_is_nonfatal():
    """Sync runs on any weekday (topic_mining feature on) and must never raise."""
    with patch.object(run_research, "run_daily"), \
         patch.object(run_research, "run_readback"), \
         patch.object(run_research, "sync_topic_decisions",
                      side_effect=RuntimeError("supabase down")) as sync:
        run_research.main(now=MONDAY)  # must not raise
    sync.assert_called_once()


def test_readback_runs_on_every_weekday():
    """Phase D lief bisher nur im Slate-Pfad (lisocon). Im Winner-Flow (jolly)
    muss sie an jedem Lauftag greifen, sonst bleiben die Zahlen leer."""
    with patch.object(run_research, "run_daily"), \
         patch.object(run_research, "sync_topic_decisions"), \
         patch.object(run_research, "run_readback") as rb:
        run_research.main(now=MONDAY)
    rb.assert_called_once()


def test_readback_failure_is_nonfatal():
    """Ein toter Apify-Run darf den Daily nicht zum Fehlschlag machen: der
    Post ist zu dem Zeitpunkt laengst veroeffentlicht."""
    with patch.object(run_research, "run_daily"), \
         patch.object(run_research, "sync_topic_decisions"), \
         patch.object(run_research, "run_readback",
                      side_effect=RuntimeError("apify down")) as rb:
        run_research.main(now=MONDAY)  # must not raise
    rb.assert_called_once()


def test_readback_runs_even_if_daily_crashed():
    """Gleiche Logik wie bei den Wochen-Jobs: der Readback misst bereits
    veroeffentlichte Posts und haengt nicht am heutigen Draft."""
    with patch.object(run_research, "run_daily", side_effect=SystemExit(1)), \
         patch.object(run_research, "sync_topic_decisions"), \
         patch.object(run_research, "run_readback") as rb:
        with pytest.raises(SystemExit):
            run_research.main(now=MONDAY)
    rb.assert_called_once()


def test_daily_ok_exits_cleanly():
    rd, ks, tm = _run(FRIDAY)  # run_daily mocked = success; must NOT raise SystemExit
    rd.assert_called_once()
    tm.assert_called_once()


def test_system_check_no_go_aborts_before_any_work():
    """Kein halber Lauf: bei NO-GO faellt main() mit Exit 1 raus, bevor
    irgendetwas scrapt, generiert oder nach Notion schreibt."""
    with patch.object(run_research, "run_system_check", return_value=False), \
         patch.object(run_research, "run_daily") as rd, \
         patch.object(run_research, "scrape_and_persist") as ks, \
         patch.object(run_research, "run_topic_mining") as tm, \
         patch.object(run_research, "sync_topic_decisions") as sync:
        with pytest.raises(SystemExit) as exc:
            run_research.main(now=THURSDAY)
    assert exc.value.code == 1
    rd.assert_not_called()
    ks.assert_not_called()
    tm.assert_not_called()
    sync.assert_not_called()


def test_system_check_runs_before_slate_mode():
    """Auch der Slate-Pfad (lisocon) darf nicht ohne bestandenen Check starten."""
    with patch.object(run_research, "run_system_check", return_value=False), \
         patch.dict(run_research._cfg.FEATURES, {"slate_mode": True}):
        with pytest.raises(SystemExit) as exc:
            run_research.main(now=MONDAY)
    assert exc.value.code == 1
