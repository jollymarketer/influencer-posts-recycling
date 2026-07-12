# EN LinkedIn Auto-Post Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Auto-publish the EN LinkedIn draft one slot after the DE post, triggered by the same `Status = Approved` flip, with per-language idempotency.

**Architecture:** Two checkbox properties (`DE Posted` / `EN Posted`, already on the data source) act as per-language state guards. Make scenario 8912831 gains a router with a DE branch and an EN branch; the EN branch only fires once `DE Posted = true`, so EN lands on the next slot via the watch re-emit caused by the DE writeback.

**Tech Stack:** Python (requests, pytest), Notion API, Make.com (notion / http / linkedin modules).

---

### Task 1: Add `LinkedIn Draft EN` property to the Notion data source

**Files:** none (Notion API call).

- [ ] **Step 1: Add the property**

Run:
```bash
cd "C:/Users/richa/Jolly_Claude_Code/JollyAutomations/Jolly Influencer Post Recycling" && PYTHONIOENCODING=utf-8 python -c "
import os, requests
from dotenv import load_dotenv
load_dotenv()
tok=os.getenv('NOTION_TOKEN'); db=os.getenv('NOTION_DB_ID','778bd719db9147ff994ddbf8a4ecac34')
h={'Authorization':f'Bearer {tok}','Content-Type':'application/json','Notion-Version':'2022-06-28'}
r=requests.patch(f'https://api.notion.com/v1/databases/{db}',headers=h,json={'properties':{'LinkedIn Draft EN':{'rich_text':{}}}},timeout=30)
print(r.status_code, [k for k in r.json().get('properties',{}) if 'Draft' in k])
"
```
Expected: `200 ['LinkedIn Draft', 'LinkedIn Draft EN']`

---

### Task 2: Pipeline writes EN draft to its own property + lift DE truncation to 3000

**Files:**
- Modify: `tools/notion_db.py` (`update_with_draft`, lines 287-290)
- Test: `tests/test_notion_db_drafts.py` (create)

- [ ] **Step 1: Write the failing test**

Create `tests/test_notion_db_drafts.py`:
```python
"""Tests for update_with_draft property mapping. _notion_request mocked."""
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import notion_db


def _run(monkeypatch, **kw):
    monkeypatch.setenv("NOTION_TOKEN", "tok")
    monkeypatch.setattr(notion_db, "MAKE_REVIEW_WEBHOOK", "", raising=False)
    resp = MagicMock(status_code=200)
    resp.json.return_value = {"id": "page1"}
    resp.raise_for_status.return_value = None
    with patch("tools.notion_db._notion_request", return_value=resp) as m:
        notion_db.update_with_draft(page_id="p1", image_prompt="", image_url="", **kw)
    return m.call_args.kwargs["json"]["properties"]


def test_en_draft_written_to_own_property(monkeypatch):
    props = _run(monkeypatch, linkedin_draft="DE text", en_draft="EN text")
    assert props["LinkedIn Draft EN"]["rich_text"][0]["text"]["content"] == "EN text"


def test_de_and_en_truncate_at_3000(monkeypatch):
    props = _run(monkeypatch, linkedin_draft="D" * 3500, en_draft="E" * 3500)
    assert len(props["LinkedIn Draft"]["rich_text"][0]["text"]["content"]) == 3000
    assert len(props["LinkedIn Draft EN"]["rich_text"][0]["text"]["content"]) == 3000


def test_empty_en_draft_omits_property(monkeypatch):
    props = _run(monkeypatch, linkedin_draft="DE text", en_draft="")
    assert "LinkedIn Draft EN" not in props
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "C:/Users/richa/Jolly_Claude_Code/JollyAutomations/Jolly Influencer Post Recycling" && python -m pytest tests/test_notion_db_drafts.py -v`
Expected: FAIL — `test_en_draft_written_to_own_property` KeyError on `LinkedIn Draft EN`; `test_de_and_en_truncate_at_3000` asserts 2000 != 3000.

- [ ] **Step 3: Edit `update_with_draft`**

In `tools/notion_db.py`, replace the DE-draft block (lines 287-290):
```python
    if linkedin_draft:
        properties["LinkedIn Draft"] = {
            "rich_text": [{"text": {"content": linkedin_draft[:2000]}}]
        }
```
with:
```python
    if linkedin_draft:
        properties["LinkedIn Draft"] = {
            "rich_text": [{"text": {"content": linkedin_draft[:3000]}}]
        }
    if en_draft:
        properties["LinkedIn Draft EN"] = {
            "rich_text": [{"text": {"content": en_draft[:3000]}}]
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "C:/Users/richa/Jolly_Claude_Code/JollyAutomations/Jolly Influencer Post Recycling" && python -m pytest tests/test_notion_db_drafts.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Run full suite (no regressions)**

Run: `cd "C:/Users/richa/Jolly_Claude_Code/JollyAutomations/Jolly Influencer Post Recycling" && python -m pytest -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add tools/notion_db.py tests/test_notion_db_drafts.py
git commit -m "feat(notion): write EN draft to LinkedIn Draft EN property, lift draft truncation to 3000"
```

---

### Task 3: Recon — confirm exact watch-output field paths for the checkbox guards

**Files:** none (Make MCP read-only).

Before editing filters, read a real execution bundle so the checkbox/property paths in the
filter expressions are exact (do not guess `properties_value.\`DE Posted\`.checkbox`).

- [ ] **Step 1: List recent executions**

Use `mcp__claude_ai_Make__executions_list` with `scenarioId: 8912831`. Note the most recent `id`.

- [ ] **Step 2: Read the trigger bundle**

Use `mcp__claude_ai_Make__executions_get-detail` for that execution. From module 1
(`notion:watchDatabaseItems`) output, record the exact expressions for:
- `Status` name (confirm `{{1.properties_value.Status.name}}`)
- `DE Posted` checkbox (expected `{{1.properties_value.\`DE Posted\`.checkbox}}` — confirm key + that value is boolean)
- `EN Posted` checkbox
- `LinkedIn Draft EN` plain text (expected `{{1.properties_value.\`LinkedIn Draft EN\`[].plain_text}}`)

Write the confirmed expressions into Task 4's blueprint before applying.

---

### Task 4: Rewrite Make scenario 8912831 blueprint (router + EN branch)

**Files:** none (Make MCP `scenarios_update`). Apply with the scenario PAUSED.

- [ ] **Step 1: Pause the scenario**

Use `mcp__claude_ai_Make__scenarios_deactivate` with `scenarioId: 8912831`.

- [ ] **Step 2: Build the new blueprint flow**

Trigger module 1 (`notion:watchDatabaseItems`) is unchanged. Replace the linear flow after it
with a `builtin:BasicRouter` (id 2) carrying two routes. Use the connection IDs from the
current blueprint: LinkedIn `__IMTCONN__ 6858705`, the writeback keeps the existing
`http:ActionSendData` shape (raw PATCH) — see Step 4 for the token decision.

Route 1 (DE):
- `http:ActionGetFile` (id 3), `filter` name "DE pending":
  - `Status.name == "Approved"` (text:equal)
  - AND `DE Posted` checkbox `!= true` (boolean) — use the confirmed expression from Task 3
  - `url`: `{{1.properties_value.Image[].external.url}}`
- `linkedin:ShareImage` (id 4): same params as today, `content = {{1.properties_value.\`LinkedIn Draft\`[].plain_text}}`, conn 6858705.
- `http:ActionSendData` (id 5): PATCH `https://api.notion.com/v1/pages/{{1.id}}`, body:
  `{"properties":{"DE Posted":{"checkbox":true},"Richard LinkedIn Posted URL":{"url":"https://www.linkedin.com/feed/update/{{4.id}}/"},"Date Posted":{"date":{"start":"{{now}}"}}}}`

Route 2 (EN):
- `http:ActionGetFile` (id 6), `filter` name "EN pending (DE done)":
  - `Status.name == "Approved"` (text:equal)
  - AND `DE Posted` checkbox `== true`
  - AND `EN Posted` checkbox `!= true`
  - `url`: `{{1.properties_value.Image[].external.url}}`
- `linkedin:ShareImage` (id 7): `content = {{1.properties_value.\`LinkedIn Draft EN\`[].plain_text}}`, conn 6858705, same title/altText/visibility as DE.
- `http:ActionSendData` (id 8): PATCH `https://api.notion.com/v1/pages/{{1.id}}`, body:
  `{"properties":{"EN Posted":{"checkbox":true},"LinkedIn Post URL":{"url":"https://www.linkedin.com/feed/update/{{7.id}}/"},"Status":{"select":{"name":"Posted"}}}}`

Note: `Status → Posted` is set only in the EN branch (route 2), so the row keeps matching
`Status == Approved` through the DE run and the EN run, then exits.

- [ ] **Step 3: Validate the blueprint**

Use `mcp__claude_ai_Make__validate_blueprint_schema` on the assembled blueprint. Fix any
schema errors before applying. Then apply with `mcp__claude_ai_Make__scenarios_update`
(`scenarioId: 8912831`), keeping `scheduling` = the existing 10/13/16 Mon-Fri restrict.

- [ ] **Step 4: Token decision (security)**

The two `http:ActionSendData` writebacks carry a plaintext Notion bearer token in the
`Authorization` header. Either (a) keep as-is (matches current prod, lowest risk to ship),
or (b) replace both writebacks with `notion:updateDatabaseItem` using existing connection
`__IMTCONN__ 5131164` so no token sits in the blueprint. Decision is Richard's; default to
(a) for this rollout and file (b) as a follow-up to avoid scope creep on a live posting flow.

---

### Task 5: Safe live test, then re-arm

**Files:** none.

- [ ] **Step 1: Seed a test row**

In Notion DB `778bd719...`, create or pick a throwaway row with: a short `LinkedIn Draft`,
a short `LinkedIn Draft EN`, an `Image`, `DE Posted` and `EN Posted` unchecked, then set
`Status = Approved`.

- [ ] **Step 2: Run the scenario once manually (DE leg)**

Use `mcp__claude_ai_Make__scenarios_run` (`scenarioId: 8912831`). Verify: DE post appears on
the feed, row now has `DE Posted = true` + `Richard LinkedIn Posted URL` set, `Status` still
`Approved`, `EN Posted` still unchecked.

- [ ] **Step 3: Run the scenario again manually (EN leg)**

Use `mcp__claude_ai_Make__scenarios_run` again. Verify: EN post appears, `EN Posted = true`,
`LinkedIn Post URL` set, `Status = Posted`.

- [ ] **Step 4: Run once more (idempotency)**

Run again. Verify: NO new post (top filter `Status == Approved` no longer matches). Delete
the test row + its two test posts from LinkedIn.

- [ ] **Step 5: Re-arm**

Use `mcp__claude_ai_Make__scenarios_activate` (`scenarioId: 8912831`). Confirm `nextExec` is
set to the next 10/13/16 slot.

---

### Task 6 (optional): Recover yesterday's Giulio EN

**Files:** none.

- [ ] **Step 1: Populate the EN property**

Copy the EN body draft of the Giulio Jun-2 entry (page `3731617b-1baf-816a-b6a4-cda8740d17ca`)
into its `LinkedIn Draft EN` property via Notion API PATCH.

- [ ] **Step 2: Re-approve**

Set that row's `Status = Approved` (it already has `DE Posted = true`, `EN Posted = false`).
At the next slot only the EN branch fires → EN posts, `Status → Posted`. No DE double-post.

---

## Self-Review

- Spec coverage: schema property (T1), pipeline EN + 3000 truncation (T2), Make router/EN branch (T4), recon for exact paths (T3), rollout safety (T5), Giulio recovery (T6), security token flag (T4 Step 4). All spec sections mapped.
- Placeholders: none — code and PATCH bodies are literal; the only deferred values are the watch-output expressions, which T3 confirms before T4 applies them.
- Type consistency: property names `DE Posted` / `EN Posted` / `LinkedIn Draft` / `LinkedIn Draft EN` / `LinkedIn Post URL` / `Richard LinkedIn Posted URL` / `Status` match the live data-source schema; module IDs 1-8 are unique; LinkedIn conn 6858705 and Notion conn 5131164 match the current blueprint.
