"""Kommentar-Kadenz: Wochentags-Gate, Gesamt-Deckel, Poster-Rotation.

Anlass (Richard 2026-07-30, Kundenfeedback Jae): lisocon produzierte 6
Kommentar-Entwuerfe pro Tag = 30 pro Woche. Soll sind 3 pro Woche, verteilt
statt geblockt.
"""
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools.comment_drafts import assign_posts, poster_rotation

POSTS = [{"post_url": f"p{i}", "post_text": "x", "influencer": f"inf{i}"}
         for i in range(10)]
POSTERS = ["Reinhard", "Jae"]
DAYS = (0, 2, 4)


def _day(week: int, offset: int) -> datetime:
    """Montag der ISO-Woche `week` in 2026, plus `offset` Tage."""
    return (datetime.fromisocalendar(2026, week, 1).replace(tzinfo=timezone.utc)
            + timedelta(days=offset))


def test_total_caps_below_per_poster_product():
    assert len(assign_posts(POSTS, POSTERS, 3, total=1)) == 1
    assert len(assign_posts(POSTS, POSTERS, 3, total=4)) == 4


def test_total_none_keeps_old_behaviour():
    assert len(assign_posts(POSTS, POSTERS, 3)) == 6
    assert len(assign_posts(POSTS, POSTERS, 3, total=None)) == 6


def test_total_never_exceeds_available_posts():
    assert len(assign_posts(POSTS[:2], POSTERS, 3, total=5)) == 2


def test_one_post_is_never_assigned_twice():
    assigned = assign_posts(POSTS, POSTERS, 3, total=3)
    assert len({post["post_url"] for _, post in assigned}) == 3


def test_poster_rotation_alternates_across_comment_days():
    """Mo/Mi/Fr liegen alle auf geraden yday-Abstaenden - eine Rotation ueber
    tm_yday % 2 wuerde immer denselben Poster ziehen."""
    seen = [poster_rotation(POSTERS, DAYS, _day(32, o))[0] for o in (0, 2, 4)]
    assert len(set(seen)) == 2, seen


def test_poster_rotation_continues_into_next_week():
    a = [poster_rotation(POSTERS, DAYS, _day(32, o))[0] for o in (0, 2, 4)]
    b = [poster_rotation(POSTERS, DAYS, _day(33, o))[0] for o in (0, 2, 4)]
    assert a != b


def test_poster_rotation_is_stable_within_one_day():
    day = _day(32, 0)
    assert poster_rotation(POSTERS, DAYS, day) == poster_rotation(POSTERS, DAYS, day)


def test_poster_rotation_without_days_falls_back():
    day = _day(32, 0)
    assert set(poster_rotation(POSTERS, None, day)) == set(POSTERS)
    assert poster_rotation([], DAYS, day) == []
