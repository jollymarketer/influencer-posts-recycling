# SWOT Content Engine: Carve-out als eigenstaendiges Repo

Datum: 2026-09-22
Status: Entwurf zur Freigabe durch Richard

## 1. Ziel

Der SWOT-Mandant der LinkedIn Content Creation Engine wird ein eigenes Repo, das SWOT auf eigenen Accounts betreibt. Einmalige Uebergabe ueber GitHub, SWOT importiert nach GitLab. Danach entwickelt Jolly den Multi-Tenant-Motor weiter, SWOT bekommt keine Updates.

Nicht Ziel: der Jolly-Motor wird nicht umgebaut. Kein gemeinsames Paket, kein Sync-Skript.

## 2. Ausgangslage

Quelle: `C:\Users\richa\Jolly_Claude_Code\Jolly Automations\Jolly Linkedin Content Creation` (Git-Remote `jollymarketer/influencer-posts-recycling`, war public, Historie enthaelt Lisocon- und Jolly-Daten).

Der SWOT-Anteil ist reine Konfiguration: `clients/swot/config.py`, `influencers.csv`, `voices/kulle.md`, `voices/werner.md`. Alles andere ist generischer Motor, der ueber `CLIENT=swot` den Mandanten laedt.

Der SWOT-Pfad laeuft heute vollstaendig auf Zuruf per CLI. `run_research.py` mit dem Railway-Cron ist Jollys Tagespfad und wird nicht uebernommen.

Heutige Kopplungen an Jolly-Konten:

| Baustein | Heute | Ziel |
|---|---|---|
| Anthropic | `ANTHROPIC_API_KEY_SWOT`, SWOT-Konto | `ANTHROPIC_API_KEY`, SWOT-Konto |
| Apify | `APIFY_API_TOKEN_SWOT`, Konto `kueswot` | `APIFY_API_KEY`, Konto `kueswot`, Guard bleibt |
| kie.ai | `KIEAI_API_KEY_SWOT`, SWOT-Konto | `KIEAI_API_KEY` |
| Supabase | Jolly-Projekt `smgi...`, Schema `blog_content_mining`, Trennung per Spalte `client` | SWOT-Projekt `wpnh...` (existiert, Outbound-Engine), gleiches Schema |
| Bild-Hosting | GitHub `jollymarketer/influencer-posts-recycling`, Branch `images`, public | Supabase Storage, Bucket `post-images`, SWOT-Projekt |
| Notion Redaktionsplan | DB `4e7b33b3...` unter Jolly OS, Clients Portals, SWOT Dashboard | Kopie im SWOT-Notion-Workspace, eigene Integration |
| Notion Topic Ideas | DB `3c11617b...` unter Jolly Blogging Engine | Kopie im SWOT-Notion-Workspace |
| Make-Webhook | `MAKE_REVIEW_WEBHOOK`, Mail an Richard | optional, leer erlaubt |

Precedent: `C:\Users\richa\Jolly_Claude_Code\Clients\SWOT\swot-outbound-engine` (README, SETUP.md, `.env.example`, `.gitignore` mit Datenregel, GitLab-Mirror-Action). Uebernommen werden Doku-Aufbau und `.gitignore`-Regeln, nicht der Mirror.

## 3. Zielrepo

Pfad: `C:\Users\richa\Jolly_Claude_Code\Clients\SWOT\swot-linkedin-content-engine`
GitHub: `jollymarketer/swot-linkedin-content-engine`, privat.
Git: frisches Repo, ein Initial-Commit, keine Historie aus dem Quellrepo.
Uebergabe: SWOT importiert das GitHub-Repo einmal nach `git.swot.de`. Danach ist GitLab das Original. Kein Mirror-Workflow, Richard pusht nach der Uebergabe nicht mehr.

### 3.1 Layout

```
swot-linkedin-content-engine/
  README.md                 Zweck, Betreiber-Tabelle, Laufbefehle, Freigabekette
  SETUP.md                  Onboarding fuer SWOT-Techniker
  .env.example              alle Variablen, keine Werte, keine IDs
  .gitignore                aus dem Outbound-Repo abgeleitet
  .gitlab-ci.yml            Schedule-Vorlage fuer Scrape, Mining, Kommentare
  requirements.txt
  clients/__init__.py       Loader, Default "swot"
  clients/swot/             config.py, influencers.csv, voices/
  tools/                    Motor, ohne Jolly-only-Module
  run_monthly_plan.py  run_plan_fill.py  run_image_fill.py  run_image_eval.py
  run_axis_scrape.py  run_source_scrape.py  run_keyword_scrape.py
  run_topic_mining.py  run_verworfen_sync.py  run_review_backfill.py
  run_comment_drafts.py     NEU
  scripts/                  nur SWOT-Skripte, siehe 3.2
  db/                       schema.sql, storage.sql
  workflows/                content_generation.md, keyword_scrape.md, research_phase.md
  tests/                    bereinigt
  Resources/swot_logo.png
```

### 3.2 Was nicht mitkommt

- `clients/jolly/`, `clients/lisocon/`, `clients/sonocrete/`, andere Logos
- `run_research.py`, `run_slate.py`, `railway.toml`, `railway.lisocon.toml`, `.railwayignore`
- `tools/abm_comment_drafts.py`, `tools/jolly_watchlist.py`, `tools/jolly_watchlist_competitors.py`
- `scripts/` ausser `add_plan_fill_properties.py`, `revision_next.py`, `measure_diet.py`; die Einmal-Skripte `swot_comment_drafts_once.py` und `swot_redaktionsplan_images.py` entfallen, ihr Zweck steckt in `run_comment_drafts.py` und `run_image_fill.py`
- `docs/superpowers/`, `.superpowers/`, `docs/PROCESS.md` (beschreibt Jollys Recycling-Flow), `tasks/`
- `images/`, `.tmp/`, `runs/`, `Resources/analytics/`, `Resources/transcriptions/`
- Tests, die Lisocon, Jolly-Watchlist, ABM, Slate oder `run_research` testen (27 von 81 Dateien nach erstem Grep, endgueltig entscheidet der Testlauf)

## 4. Code-Aenderungen

Prinzip: kleinster Eingriff. Der Tenant-Loader bleibt, damit `clients/swot/config.py` unveraendert funktioniert.

1. `clients/__init__.py`: Default `os.getenv("CLIENT", "swot")`. Gleicher Default in `run_keyword_scrape.py`.
2. Env-Namen: `clients/swot/config.py` liest `ANTHROPIC_API_KEY`, `APIFY_API_KEY`, `KIEAI_API_KEY` statt der `_SWOT`-Varianten. `APIFY_ACCOUNT = "kueswot"` bleibt, der Guard in `tools/apify_auth.py` schuetzt weiter vor dem falschen Konto. `NOTION_DB_ID`, `TOPIC_IDEAS_DB_ID`, `CONTENT_PLAN_DB_ID` kommen aus der Env, keine Default-IDs mehr im Code.
3. `tools/kieai_image.py`: Upload nach Supabase Storage statt GitHub. Bucket `post-images`, public, Pfad `<yyyy-mm>/<slug>.png`, URL `SUPABASE_URL/storage/v1/object/public/post-images/<pfad>`. `_upload_to_github`, der catbox-Fallback, `GITHUB_TOKEN`, `GITHUB_REPO`, `GITHUB_IMAGES_BRANCH` werden geloescht, nicht nur abgeschaltet. Es gibt genau einen Upload-Pfad; schlaegt er fehl, bricht der Lauf mit Fehler ab statt auf einen anderen Host auszuweichen. Ein Test prueft, dass jede erzeugte Bild-URL mit `SUPABASE_URL` beginnt und `githubusercontent` nirgends im Modul vorkommt. Logo-Default `swot_logo.png`.
4. `run_comment_drafts.py` (neu): laedt den Mandanten, ruft `tools.comment_drafts.run_comment_drafts(cfg, now)`, schreibt Kommentar-Entwuerfe als Zeilen mit Typ `LinkedIn-Kommentar` in den Redaktionsplan. Tages-Gate aus `COMMENT_DRAFTS["days"]` bleibt, `--force` uebergeht es fuer Tests.
5. `scripts/revision_next.py`: Protokoll nach `workspace/pruefberichte/` im Repo statt zwei Ebenen ueber dem Repo.
6. `tools/review_backfill.py`: Report-Ueberschrift bleibt, sie ist SWOT-spezifisch und richtig.
7. `clients/swot/config.py`: Kommentare mit Pfaden nach Obsidian, `Clients/SWOT/` und Notion-Task-URLs raus. Inhalt der Konfiguration unveraendert.
8. `tools/system_check.py`: prueft zusaetzlich, dass der Storage-Bucket erreichbar ist.
9. Alle Modul-Docstrings: `CLIENT=swot` aus den Beispielbefehlen streichen, da Default.

Nicht angefasst: `post_scorer`, `post_writer`, `naturalness`, `monthly_plan`, `topic_pool`, `notion_db`, `supabase_db`. Die Supabase-Spalte `client` bleibt, jede Zeile traegt `swot`.

## 5. Daten-Migration

Reihenfolge ist verbindlich, jeder Schritt hat einen Readback.

1. Supabase, SWOT-Projekt: `db/schema.sql` ausfuehren (Schema `blog_content_mining`, Tabellen `influencer_posts`, `topic_candidates`, `engine_meta`, `topic_decisions`, `comment_watchlist`). Readback: fuenf Tabellen vorhanden, null Zeilen.
2. Zeilen kopieren: aus dem Jolly-Projekt alle Zeilen mit `client = 'swot'` je Tabelle exportieren, im SWOT-Projekt einfuegen. Readback: Zeilenzahl je Tabelle Quelle gleich Ziel, in einer Tabelle im Migrationsprotokoll festgehalten.
3. Storage: Bucket `post-images` per `db/storage.sql` anlegen, public read. Alle Bilder, die heute in Notion-Zeilen des Redaktionsplans auf `raw.githubusercontent.com/jollymarketer/...` zeigen, herunterladen, in den Bucket laden. Readback: Anzahl Bild-URLs in Notion gleich Anzahl Objekte im Bucket.
4. Notion: Zielworkspace ist "Workspace von SWOT" (existiert, Richard ist Admin). Der Claude-Notion-Connector haengt am Jolly-Workspace und sieht den SWOT-Workspace nicht; alle Schreibzugriffe laufen ueber die REST-API mit einer internen Integration, die Richard im SWOT-Workspace anlegt (Token wird `NOTION_TOKEN` der Engine). Richard dupliziert Redaktionsplan-DB und Topic-Ideas-DB per Notion-UI in den SWOT-Workspace (Inhalte und Views kommen mit) und teilt beide DBs mit der Integration. Danach schreibt ein Skript die Bild-Properties der Kopie auf die Supabase-URLs um (einmalig, Trockenlauf zuerst). Readback: Zeilenzahl beider DBs Quelle gleich Ziel, null Bild-URLs mit `githubusercontent`.
5. Cutover: SWOT setzt `.env`, faehrt `python -m tools.system_check`, dann einen Trockenlauf `run_monthly_plan.py --month <naechster Monat>`. Erst danach: Jolly loescht `clients/swot/` im Multi-Tenant-Repo und die `swot`-Zeilen im Jolly-Supabase, die Jolly-Notion-DBs werden archiviert. Loeschung erst nach schriftlicher Bestaetigung von SWOT, dass der Lauf durch ist.

Kosten: Supabase Free Tier reicht (Storage unter 1 GB). Keine neuen Abos. Bestehende Keys (Anthropic, Apify, kie.ai) laufen weiter.

## 6. Betrieb bei SWOT

Alle Laeufe sind CLI-Befehle nach `pip install -r requirements.txt` und gefuellter `.env`.

| Lauf | Befehl | Rhythmus | Gate davor |
|---|---|---|---|
| Quellen-Scrape | `python run_source_scrape.py` | woechentlich | keins |
| Achsen-Scrape | `python run_axis_scrape.py` | woechentlich | keins |
| Topic-Mining | `python run_topic_mining.py` | woechentlich, nach Scrape | keins |
| Monatsplan | `python run_monthly_plan.py --month YYYY-MM --write` | monatlich | Themen-DB gesichtet |
| Plan fuellen | `python run_plan_fill.py --months YYYY-MM --write` | nach Monatsplan | keins |
| Bild | `python run_image_fill.py --write` | auf Zuruf | Status "Text freigegeben" |
| Kommentare | `python run_comment_drafts.py` | Mo, Mi, Fr | keins |
| Verworfen-Sync | `python run_verworfen_sync.py --write` | woechentlich | keins |

`.gitlab-ci.yml` enthaelt drei Schedules als Vorlage (Scrape plus Mining, Kommentare, Verworfen-Sync), Variablen aus den GitLab-CI-Variablen. SWOT aktiviert sie selbst. Monatsplan, Text und Bild bleiben Zuruf, weil Freigaben dazwischen liegen.

`.env.example` (Namen, keine Werte): `ANTHROPIC_API_KEY`, `APIFY_API_KEY`, `KIEAI_API_KEY`, `NOTION_TOKEN`, `NOTION_DB_ID`, `TOPIC_IDEAS_DB_ID`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `MAKE_REVIEW_WEBHOOK` (optional).

Betreiber-Tabelle im README: SWOT haelt Keys, Notion, Supabase, GitLab und faehrt alle Laeufe. Jolly hat nach der Uebergabe keine Rolle im Betrieb.

## 7. Verifikation

Fertig heisst, jeder Punkt ist belegt:

1. Frischer Clone des GitHub-Repos in ein leeres Verzeichnis, `pip install`, `pytest` gruen. Zahl der Tests im README.
2. `grep -ri "richa\|Jolly_Claude_Code\|lisocon\|sonocrete\|jollymarketer\|_SWOT\|obsidian" --exclude-dir=.git` liefert null Treffer.
3. `tools/system_check.py` meldet GO gegen SWOT-Supabase, SWOT-Notion-Kopie, Apify `kueswot`, Anthropic, kie.ai, Storage-Bucket.
4. Ein echter Lauf `run_image_fill.py --write --limit 1` erzeugt ein Bild mit Supabase-URL in der SWOT-Notion-Kopie, Bild im Browser ohne Login sichtbar.
5. Ein echter Lauf `run_comment_drafts.py --force` schreibt Kommentar-Zeilen in die SWOT-Notion-Kopie.
6. Readback-Tabelle der Daten-Migration (Abschnitt 5) liegt im Repo unter `docs/migration-2026-09.md`.
7. `git log` zeigt genau einen Commit vor der Uebergabe.

## 8. Risiken

- Notion-Duplikat kopiert externe Bild-URLs unveraendert. Ohne Schritt 5.4 zeigen die Bilder auf ein Repo, das SWOT nicht kontrolliert. Deshalb ist der URL-Umschreiber Pflicht, nicht Option.
- `post_scorer.FORMAT_STRUCTURES` und `clients/swot/config.py` sind per String gekoppelt (`STRUCTURE_REPLACEMENTS`). Bleibt so, beide Dateien wandern gemeinsam.
- SWOT hat nur einen Notion-Workspace-Admin, wenn er fehlt, stockt Schritt 5.4. Vorab klaeren, wer bei SWOT Notion-Admin ist.
- Der Apify-Guard prueft den Kontonamen. Wechselt SWOT das Apify-Konto, muss `APIFY_ACCOUNT` in `config.py` mitziehen. Steht im SETUP.md.
