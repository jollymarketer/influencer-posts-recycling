# EN LinkedIn Auto-Post — Design

Date: 2026-06-03
Status: Approved (design)

## Problem

The DE LinkedIn post auto-publishes when a Notion entry's `Status` is set to `Approved`
(Make scenario 8912831). The EN draft never publishes: the scenario has a single
`linkedin:ShareImage` module that reads the `LinkedIn Draft` property (DE only), and the
EN draft lives only in page body blocks, which the scenario never reads. EN was never
wired into auto-posting.

## Current scenario (8912831) flow

1. `notion:watchDatabaseItems` — watch data source `e6a3d44c-a050-4660-8ed3-380551b6aa1a`, `select=update`.
2. Filter `Status.name == "Approved"` → `http:ActionGetFile` downloads `Image[].external.url`.
3. `linkedin:ShareImage` — posts image + `content = {{LinkedIn Draft}}` (DE).
4. `http:ActionSendData` PATCH Notion — `Status="Posted"`, `Richard LinkedIn Posted URL`, `Date Posted=now`.

Schedule: Mon–Fri at 10:00 / 13:00 / 16:00 (Europe/Berlin). Idempotency today = the
`Approved → Posted` flip (filter stops matching once `Posted`).

## Target behaviour

When the user sets `Status = Approved`:
- DE posts at the first slot at/after approval.
- EN posts at the next slot (one slot later, +3h; if DE landed on the 16:00 slot, EN posts
  the next workday 10:00). DE and EN are always exactly one slot apart.

## Design

State machine over two checkbox properties `DE Posted` / `EN Posted` (already created on the
data source) as per-language idempotency guards.

New scenario flow (router with two branches after the trigger):

```
notion:watchDatabaseItems (select=update, data_source e6a3d44c)
  └─ Top filter: Status == "Approved"
       ├─ Branch DE:  filter  DE Posted != true
       │     → http GetFile(Image) → linkedin ShareImage(content = {{LinkedIn Draft}})
       │     → Notion update: DE Posted = true, Richard LinkedIn Posted URL = <de-url>
       └─ Branch EN:  filter  DE Posted == true AND EN Posted != true
             → http GetFile(Image) → linkedin ShareImage(content = {{LinkedIn Draft EN}})
             → Notion update: EN Posted = true, LinkedIn Post URL = <en-url>, Status = "Posted"
```

### Why this spaces by exactly one slot

- Run 1 (Approved, both unchecked): DE branch fires. EN branch filter `DE Posted == true`
  is false in the trigger snapshot → EN skipped. DE posts.
- The Notion update bumps `last_edited_time` → the row re-emits at the next slot's watch run.
- Run 2: `DE Posted == true` → DE branch skips, EN branch fires → EN posts, `Status → Posted`.
- Run 3: `Status == Posted` → top filter fails → done.

The 3h slot gap is far larger than the time to PATCH + re-index, so the re-emit is reliable.

### Double-post protection

The `DE Posted` / `EN Posted` checkbox guards. Even if the watch re-emits unexpectedly,
no branch posts twice because the guard property is already `true`. This is the safety net
for the real personal LinkedIn feed.

## Required changes

1. **Notion schema** — add text property `LinkedIn Draft EN` on data source `e6a3d44c`.
2. **Pipeline code** (`tools/notion_db.py`, `update_with_draft`):
   - Write `en_draft` to property `LinkedIn Draft EN` (`[:3000]`).
   - Raise DE truncation in `LinkedIn Draft` from `[:2000]` to `[:3000]` (LinkedIn allows 3000).
   - Body blocks unchanged.
3. **Make scenario 8912831** — add router + EN branch via `scenarios_update`.
4. **Security (recommended)** — the writeback currently uses raw `http:ActionSendData` with a
   plaintext Notion bearer token in the header. Replace the writebacks with `notion`
   update modules using the existing Notion connection (`__IMTCONN__ 5131164`) so no token
   sits in the blueprint.

## Image

Per existing behaviour DE and EN share one generated image. Both branches download the same
`Image[].external.url`. No image change.

## Recovery: yesterday's Giulio EN

Giulio (Jun 2) has `DE Posted = true`, `EN Posted = false`, `Status = Posted`. To publish its
EN: copy the EN body draft into the `LinkedIn Draft EN` property, then set `Status = Approved`.
Only the EN branch fires (DE guard already true) → EN posts, `Status → Posted`. No DE double-post.

## Rollout safety

Editing a live scenario that posts to the real personal profile. Before going live:
pause scenario → set one test Notion row to `Approved` → run once manually → verify feed +
writebacks → re-arm schedule.

## Out of scope

- Slot-time changes (stays 10/13/16 Mon–Fri).
- Company-page posting.
- Backfilling EN for historical entries beyond the Giulio recovery path.
