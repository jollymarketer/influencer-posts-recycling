# Hook-Katalog mit Rotation und monatlicher Hook-Audit

Stand 14.09.2026. Mandant zuerst Jolly (Richard, Runner `run_research.py`),
lisocon folgt, sobald Reinhard oder Jae den nativen LinkedIn-Export liefern.
SWOT postet noch nicht ueber die Maschine. Freigabe Richard 14.09.2026 im
Brainstorming (Bericht zuerst, Steuerung sobald das Gate oeffnet).

## 1. Anlass und Befund

Repo-Vergleich mit Jakeschincariol/linkedin-agent-skill (14.09.2026). Das Repo
traegt einen Katalog von 21 Hook-Formeln, je Formel eine Vorlage und eine
"Falle" (wie die Formel misslingt), und ein Audit, das veroeffentlichte Posts
nach Engagement-Rate und Reichweite je Hook auswertet. Beides fehlt hier:

- Der Hook ist Zeile 1 jeder Formatstruktur in `tools/post_scorer.FORMAT_STRUCTURES`,
  eine Anweisung je Format ("kontroverse These", "mitten in eine Szene", "die
  Ergebniszahl"). Ob Sonnet daraus eine Zahl, eine Frage, eine Dialogzeile
  oder eine Behauptung baut, entscheidet das Modell je Lauf. Keine Wahl, keine
  Sperre gegen Wiederholung, keine ID, an der sich Ergebnisse festmachen lassen.
- `tools/engagement_readback.py` liest Likes, Kommentare und Shares je Post
  zurueck, `tools/engagement_stats.py` rechnet Mediane je Dimension und
  druckt ins Railway-Log. Impressions kennt keiner der beiden. Der native
  Export unter `Resources/analytics/` (Impressions je Post) wird von keinem
  Code gelesen. Laut `workflows/research_phase.md` fliesst nichts in die
  Generierung zurueck.

Zwei Grenzen der Datenlage, die das Design bestimmen:

- Impressions gibt es nur aus dem nativen Export, den Richard von Hand zieht.
  Der Export liefert die Top 50 Posts des gewaehlten Fensters. Ein Fenster von
  28 Tagen deckt bei rund 20 Posts im Monat alles ab; das vorhandene
  12-Monats-Fenster deckt nur die Spitze.
- Rund 20 Posts im Monat auf 10 Formate und 17 Formeln ergeben 1 bis 2 Posts
  je Formel. Das Stichproben-Gate (5 Posts je Zelle) oeffnet je Formel
  fruehestens nach einem halben Jahr. Gesteuert wird deshalb auf der Ebene
  von fuenf Hook-Familien (Abschnitt 3.2), berichtet wird je Formel mit n.

## 2. Ziel und Nicht-Ziel

Ziel:

- Jeder neue Post traegt eine Hook-Formel aus einem festen Katalog, gewaehlt
  deterministisch mit Rotation, geschrieben als Select "Hook" in Notion.
- Ein monatlicher Bericht joint den nativen Export mit den Notion-Zeilen und
  weist Engagement-Rate, Comment-Ratio und Reach-Index je Hook-Familie, Hook,
  Format, Laengenband, Persona und Wochentag aus. Jede Aussage traegt n.
- Sobald das Gate oeffnet, schreibt der Bericht STOP- und DO-MORE-Familien in
  `engine_meta`; die Rotation liest sie.

Nicht-Ziel:

- Kein Follower-Stand in der Config (Reach-Index normiert am Monatsmedian).
- Keine Aenderung der Matrix, der Formatwahl oder der Assets.
- Kein woechentlicher Bericht: Readback bleibt woechentlich und still, der
  Bericht ist monatlich und haengt am Export.
- Link im Body gegen Link im ersten Kommentar: nicht im Umfang, spaeter
  moegliche Audit-Dimension.

## 3. Bauteile

### 3.1 Katalog `tools/hooks.py`

Python-Dict `HOOKS`, je Eintrag: `id`, `name`, `family`, `template_de`,
`template_en`, `trap_de`. 16 der 21 Formeln des Repos, deutsch gefasst, plus
die eigene Formel `assumption` fuer Signature: 17 IDs. Weggelassen mit Grund:
Permission Slip (US-Coach-Ton), Callout ("hoer auf damit", Verachtung fuer das
Publikum), Good vs Great (ist unser Signature), Curiosity Gap (Clickbait),
Pattern Interrupt (Einwort-Zeile, kollidiert mit der Pointen-Regel der
Textwache).

Zuordnung `HOOKS_BY_FORMAT`. Zahlenformeln nur dort, wo ein Asset die Zahl
liefert; der Zahlen-Guard (`content_matrix.figures_ok`) bleibt unveraendert.

| Format | Formeln |
| --- | --- |
| Opinion | contrarian, unpopular_rule, myth_bust, warning |
| POV | insider_secret, myth_bust, before_after |
| Signature | assumption (eigene Formel, nur eine ID fuer den Join) |
| Story | cold_open, mistake, walk_away |
| Comparison | comparison, warning |
| Method | direct_value, list_promise |
| CaseProof | number_reveal, time_anchor, receipt |
| Debate | question_trap, contrarian |
| Magnet | direct_value, warning |
| Offer | before_after, number_reveal |

Familien `HOOK_FAMILIES`:

| Familie | Formeln |
| --- | --- |
| These | contrarian, unpopular_rule, myth_bust, warning, assumption |
| Zahl | number_reveal, time_anchor, receipt, before_after |
| Szene | cold_open, mistake, walk_away |
| Frage | question_trap, comparison |
| Gabe | direct_value, list_promise, insider_secret |

Prompt-Zeile: `hook_line(hook_id, lang)` liefert "1. Hook (1-2 Saetze), Formel
{name}: {template}. Falle: {trap}. Entscheidet ob jemand weiterliest." und
ersetzt in `post_scorer._client_structure` die erste Strukturzeile des
Formats. Der Rest der Struktur bleibt zeichengenau. Der EN-Draft bekommt
dieselbe Formel mit `template_en`.

### 3.2 Rotation `hooks.pick_hook(fmt, recent, steering)`

Deterministisch, kein Modellaufruf.

- Kandidaten = `HOOKS_BY_FORMAT[fmt]` minus Formeln, deren Familie auf STOP
  steht. Sperrt STOP alle Kandidaten des Formats, gilt STOP fuer dieses Format
  nicht; das steht im Log.
- Reihenfolge: am laengsten nicht genutzt zuerst, gemessen an `recent` (die
  letzten 20 Hook-IDs aus Notion, neueste zuerst). Formeln einer DO-MORE-
  Familie zaehlen mit halbem Abstand (ihr letzter Einsatz wird doppelt so weit
  zurueckgerechnet), sie kommen also doppelt so oft dran.
- Gleichstand: Katalogreihenfolge. Signature hat nur einen Kandidaten.
- `steering` ist das JSON aus `engine_meta["hook_steering_<client>"]`:
  `{"stop": [...], "do_more": [...], "as_of": "YYYY-MM-DD", "n": int}`.
  Aelter als 60 Tage oder nicht lesbar: leer.

### 3.3 Notion

- Neues Select "Hook" auf der Post-Zeile, Optionen = alle `HOOKS`-IDs.
  Seed-Skript `scripts/add_hook_property.py` nach dem Muster von
  `scripts/add_format_property.py`, idempotent.
- `notion_db.update_with_draft` schreibt "Hook" wie "Format": nicht fatal,
  fehlt die Property, laeuft der Post ohne.
- `notion_db.get_recent_hooks(limit=20)` nach dem Muster von
  `get_recent_formats` (Status Posted/Posting/Approved/Ready to Review).
- `get_published_rows` liefert zusaetzlich `dims["Hook"]`; dazu kommt "Hook"
  in `ENGAGEMENT_DIMENSIONS`.
- Neuer Status "Audit" fuer die Berichtsseite. Der Make-Publisher filtert auf
  Approved und sieht sie nie.
- `system_check`: fehlt "Hook", weicher Befund mit Nennung des Seed-Skripts.

### 3.4 Textwache

`text_gate.shape_notes` bekommt einen weichen Hinweis, wenn die erste
nichtleere Zeile ueber 140 Zeichen hat (mobiler Schnitt "mehr anzeigen").
Bleibt im Neulauf-Hinweis, verwirft nichts.

### 3.5 Export-Parser `hook_audit.read_export(path)`

- Dateien unter `Resources/analytics/`, Namensmuster `top_posts_<von>_<bis>.csv`
  (wie die vorhandene Datei). Der Runner nimmt die Datei mit dem juengsten
  `<bis>`.
- Layout zweiblockig, wie die vorhandene Datei: Spalten `Post URL, Post Publish
  Date, Engagements, <leer>, Post URL, Post Publish Date, Impressions`. Beide
  Bloecke werden getrennt gelesen und ueber die LinkedIn-Objekt-ID (15 bis 25
  Ziffern in der URL, `engagement_readback._ID_RE`) zusammengefuehrt.
- Fenster ueber 35 Tage (aus dem Dateinamen): Warnung im Bericht, weil Top 50
  dann nicht alle Posts deckt.

### 3.6 Join und Metriken `tools/hook_audit.py`

- Notion-Zeilen aus `get_published_rows` (Hook, Format, Persona, Matrix-Box,
  Bild-Variante, Laengenband, Datum, Likes, Kommentare, Shares, Poster-URL).
  Join ueber die Objekt-ID der Poster-URL.
- Je Post:
  - Engagement-Rate = (Likes + Kommentare + Shares) / Impressions; fehlt das
    Readback, Engagements aus dem Export / Impressions.
  - Comment-Ratio = Kommentare / Likes (Likes 0: leer). Geht ohne Export.
  - Reach-Index = Impressions / Median der Impressions aller gejointen Posts
    des Berichts.
  - Score = Likes + 2 Kommentare + 3 Shares (wie `engagement_stats`).
- Aggregation: Median je Zelle, Dimensionen in fester Reihenfolge:
  Hook-Familie, Hook, Format, Laengenband, Persona, Wochentag. Wochentag steht
  zuletzt und wird im Text nur genannt, wenn die anderen nichts zeigen.
- Gate wie `engagement_stats`: 5 Posts je Zelle, 2 auswertbare Zellen je
  Dimension.
- Nenner: Zahl der Export-Zeilen, der Notion-Zeilen, der gejointen Zeilen, der
  Export-Zeilen ohne Notion-Treffer (manuelle Posts) und der Notion-Zeilen
  ohne Hook (Bestand vor Rollout) stehen immer oben im Bericht.

### 3.7 Bericht und Ablage

Aufbau, Reihenfolge fest:

1. Kopf: Monat, Fenster, Nenner (3.6), Warnungen (Fenster, kein Export).
2. Top 5 und Bottom 5 Posts nach Engagement-Rate (ohne Export: nach Score),
   je Post erste Zeile, Hook, Format, Zahlen.
3. Tabellen je Dimension (3.6), Zellen mit n, Median Engagement-Rate,
   Median Comment-Ratio, Median Reach-Index.
4. "Was die Daten sagen": nummerierte Aussagen, jede mit n; ohne offenes Gate
   der Satz "keine Aussage, n=...".
5. STOP und DO MORE (3.8), oder "Gate geschlossen".

Ablage:

- Markdown immer: `Resources/analytics/hook_audit_<YYYY-MM>.md`.
- Notion-Seite in der Content-DB des Mandanten, Status "Audit", Titel
  "Hook-Audit YYYY-MM", Tabellen als Notion-Tabellen in voller
  Seitenbreite, keine Pipe-Tabellen. Schreibfehler: Log, Markdown bleibt.
- Mail ueber `MAKE_AUDIT_WEBHOOK` mit Payload `{"client", "month", "notion_url",
  "summary"}`; ohne Variable stiller Skip. Das Make-Szenario baut Richard.

### 3.8 Steuerung

- Nur bei offenem Gate auf Hook-Familie (5 je Familie, 2 auswertbar).
- STOP = Familie mit dem niedrigsten Median der Engagement-Rate, wenn er unter
  0,6 des Gesamtmedians liegt. DO MORE = Familie mit dem hoechsten Median,
  wenn er ueber 1,4 des Gesamtmedians liegt. Sonst leer.
- Ohne Export keine Steuerung (Engagement-Rate fehlt).
- Schreibt `engine_meta["hook_steering_<client>"]` (3.2). Jeder Audit
  ueberschreibt. Verfall 60 Tage.
- `run_hook_audit.py --clear-steering` leert den Eintrag.

### 3.9 Runner

- `run_hook_audit.py`: CLI, lokal nach dem Export. Argumente `--client`,
  `--export <pfad>` (sonst juengste Datei), `--no-notion`, `--no-mail`,
  `--clear-steering`. Setzt `engine_meta["last_hook_audit_<client>"]`.
- `run_research.py`, Montags-Jobs: liegt `last_hook_audit_<client>` ueber 35
  Tage zurueck oder fehlt, Erinnerung ueber `MAKE_AUDIT_WEBHOOK` mit
  `{"client", "reminder": true}`. Kein Bericht mit halben Daten.

## 4. Datenfluss je Post (neu)

1. Format gewaehlt wie bisher (Matrix, Anti-Repeat, Asset).
2. `pick_hook(format, get_recent_hooks(20), steering)` liefert die Hook-ID.
3. `hook_line` ersetzt Zeile 1 der Formatstruktur im DE- und EN-Prompt.
4. Generierung, Textwache (jetzt mit 140-Zeichen-Hinweis), Reader wie bisher.
5. `update_with_draft` schreibt "Hook" nach Notion.
6. Readback woechentlich wie bisher, Bericht monatlich nach Export.

## 5. Tests

Alle ohne Netz, Muster der bestehenden Suite.

- Katalog gepinnt: jede ID eindeutig, jedes Format hat mindestens eine
  Formel, jede Formel genau eine Familie, Zahlenformeln nur bei CaseProof und
  Offer, jede Formel traegt beide Vorlagen und eine Falle.
- `hook_line` ersetzt genau die erste Strukturzeile, Rest zeichengenau.
- `pick_hook`: Rotation ueber `recent`, DO-MORE halbiert den Abstand, STOP
  sperrt, STOP-alle faellt zurueck, Steuerung ueber 60 Tage wird ignoriert,
  Signature liefert immer `assumption`.
- Export-Parser auf der echten Datei `top_posts_2025-08-20_2026-08-19.csv`
  (Fixture aus der Live-Form): 50 Zeilen, beide Bloecke gejoint, Fenster-
  Warnung bei 12 Monaten.
- Join per Objekt-ID, Zeilen ohne Treffer in beide Richtungen gezaehlt.
- Metriken mit Randfaellen (Likes 0, Impressions fehlt, Readback fehlt).
- Gate und Steuerung: Schwellen 0,6 und 1,4, leer bei geschlossenem Gate.
- Berichtsaufbau: Reihenfolge der Bloecke, n in jeder Aussage.
- Notion-Property-Schreiben nicht fatal; `system_check` nennt das Seed-Skript.

## 6. Reihenfolge mit Pruefkriterium

1. Katalog, Rotation, Prompt-Zeile, Notion-Property, Seed, 140-Zeichen-
   Hinweis. Pruefung: naechster Jolly-Lauf schreibt "Hook" in Notion, Log
   nennt Formel und Falle.
2. Export-Parser, Join, Metriken, Bericht als Markdown. Pruefung: Lauf auf
   der vorhandenen 12-Monats-Datei liefert einen Bericht mit Nenner und
   Fenster-Warnung.
3. Notion-Seite, Mail, Erinnerung. Pruefung: Seite mit Status "Audit" in der
   Jolly-DB, Mail mit Link.
4. Steuerung lesen in `pick_hook` (Code ab Schritt 1, Liste leer) und
   schreiben im Audit. Pruefung: Test mit synthetischen Zahlen fuellt die
   Liste, Test mit leerem Gate laesst sie leer.

## 7. Kosten

Keine neuen Modellaufrufe. Rotation und Audit sind deterministisch. Notion-
Aufrufe: ein Getter je Post (Hook-Historie), eine Seite je Monat.

## 8. Risiken

- Export-Disziplin: ohne Export kein Reach, keine Steuerung. Die Erinnerung
  faengt das, der Bericht ohne Export bleibt ehrlich beschriftet.
- Kleine Stichprobe: je Formel dauert es Monate. Familien-Ebene ist der
  Kompromiss; STOP und DO MORE tragen im Bericht immer n und Schwellen.
- Zeile 1 der Formatstruktur war bisher formatspezifisch formuliert (z. B.
  Comparison "Entscheidungs-Moment bei externer GTM-Unterstuetzung"). Die
  Formel ersetzt sie; die Formatlogik des Restes bleibt. Sollte ein Format
  darunter leiden, wird die alte Zeile als eigene Formel-ID in den Katalog
  genommen, nicht die Rotation abgeschaltet.
- Lisocon nutzt dieselbe Property und dieselbe Rotation ab dem Seed in seiner
  DB; ohne Export dort nur Comment-Ratio und Score.
