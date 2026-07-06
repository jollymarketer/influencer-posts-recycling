"""Notion zaehlt Textlaengen in UTF-16 Code Units (Astral-Zeichen wie Emoji
oder 𝗯𝗼𝗹𝗱-Unicode = 2). Chunking/Truncation muss danach messen, sonst 400:
'content.length should be <= 2000, instead was 2034' (Deploy-Crash 2026-07-06)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools.notion_db import _utf16_chunks, _utf16_len, _utf16_truncate

# Astral-Zeichen (Mathematical Bold 𝗮, U+1D5EE): 1 Python-Codepoint, 2 UTF-16 Units
BOLD_A = "\U0001d5ee"


def test_utf16_len_counts_astral_as_two():
    assert _utf16_len("abc") == 3
    assert _utf16_len(BOLD_A * 5) == 10


def test_chunks_respect_utf16_limit():
    # 1900 Codepoints, davon 200 astral -> 2100 UTF-16 Units (alter Code: 1 Chunk mit 2100)
    text = BOLD_A * 200 + "x" * 1700
    chunks = _utf16_chunks(text, limit=1900)
    assert all(_utf16_len(c) <= 1900 for c in chunks)
    assert "".join(chunks) == text


def test_chunks_plain_ascii_unchanged():
    text = "x" * 4000
    chunks = _utf16_chunks(text, limit=1900)
    assert [len(c) for c in chunks] == [1900, 1900, 200]


def test_truncate_respects_utf16_limit():
    text = BOLD_A * 1500  # 3000 UTF-16 Units
    out = _utf16_truncate(text, limit=2000)
    assert _utf16_len(out) <= 2000
    assert _utf16_truncate("short", limit=2000) == "short"
