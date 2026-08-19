"""Jeder Mandant muss run_research importieren koennen.

Regression vom 19.08.2026: Commit d5aab0d loeste die Keyword-Liste auf
Modulebene von run_keyword_scrape auf. run_research importiert dieses Modul
unbedingt, also starb lisocon (kein eigenes KEYWORDS, keyword_scrape=False)
schon am Import und der Railway-Lauf brach ab. Die bestehende Testsuite hat
das nicht gesehen, weil sie resolve_keywords nur mit Fake-Config prueft und
sonst gegen den Default CLIENT=jolly laeuft.

Der Import laeuft in einem Subprozess, weil CLIENT ueber load_client()
gecached wird und die Mandantenwahl im selben Prozess nicht umschaltbar ist.
"""
import os
import subprocess
import sys

import pytest

CLIENTS = ["jolly", "lisocon", "swot"]
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.mark.parametrize("client", CLIENTS)
@pytest.mark.parametrize("module", ["run_research", "run_keyword_scrape", "tools.post_scorer"])
def test_module_imports_for_client(client, module):
    env = {**os.environ, "CLIENT": client}
    proc = subprocess.run(
        [sys.executable, "-c", f"import {module}"],
        cwd=REPO, env=env, capture_output=True, text=True, timeout=120,
    )
    assert proc.returncode == 0, (
        f"CLIENT={client}: `import {module}` bricht ab.\n"
        f"stdout: {proc.stdout[-500:]}\nstderr: {proc.stderr[-500:]}"
    )
