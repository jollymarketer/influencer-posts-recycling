# Workflow: Research Phase (Vollautomatisch)

## Ziel
Neue LinkedIn-Posts der GTM/RevOps-Influencer finden, scoren, recyceln und täglich fertig in Notion ablegen — ohne manuellen Schritt.

## Architektur

| Schritt | Wo | Warum |
|---------|-----|-------|
| Scraping + Scoring + Content + Bild | Railway Cron (automatisch) | Vollständig headless, kein manueller Eingriff |
| Email-Reminder | Scheduled Agent (automatisch) | Benachrichtigt wenn "Ready to Review" vorliegt |

## Automatischer Daily Run (Railway)

### Trigger
- Täglich 07:00 UTC via Railway Cron (`0 7 * * *`)
- Manuell: `python run_research.py`

### Inputs
- `clients/<name>/influencers.csv` — Liste der Influencer-Profile (pro Mandant, Default: jolly)
- Notion DB `778bd719db9147ff994ddbf8a4ecac34` — bestehende Posts (Duplikat-Filter)

### Was passiert (run_research.py)
1. Bestehende Post-URLs aus Notion laden
2. Neue Posts scrapen via Apify (`harvestapi/linkedin-profile-posts`) + Substack RSS
   - `maxPosts` und Altersfenster pro Mandant aus `clients/<name>/config.py`, Block `SCRAPE`
   - Fetch-Fenster über `postedLimitDate` = jetzt minus (`max_age_hours` + 4h), **nicht**
     über das Enum `postedLimit`. Der Actor rechnet pro geliefertem Post ab (0,002 USD);
     `postedLimit="week"` lieferte bei einem 36h-Filter rund vier von fünf Posts, die der
     Altersfilter sofort verwarf und die trotzdem bezahlt wurden. Gemessen 30.07.2026:
     gleiches Profil, `week` = 3 Posts (15h, 33h, 55h), `postedLimitDate` = 2 Posts.
   - Posts unter 50 Wörtern werden gefiltert
3. Alle neuen Posts in Notion schreiben (Status: "New")
4. Posts scoren: 5 KI-Dimensionen + Viralität (Engagement), max. 60 Punkte
   - Dimensionen: Topic Fit, ICP-Relevanz, Recyclierbarkeit, Einzigartigkeit, Themen-Diversität
   - Viralität: logarithmisch aus Likes/Comments/Shares (Engagement-Daten aus Apify)
5. Winner wählen: höchster Score, Mindest-Score 25/60
6. DACH-deutschen LinkedIn-Draft + Bild-Prompt generieren (Claude Sonnet)
7. Bild generieren (kie.ai, Nano Banana 2, 1:1)
8. Notion-Eintrag des Winners updaten:
   - LinkedIn Draft, Image Prompt, Bild-URL
   - Status: "Ready to Review"
   - Make.com Webhook → E-Mail-Alert
9. Alle anderen neuen Posts → Status: "Skipped"

### Output
- Genau ein Notion-Eintrag täglich mit Status "Ready to Review" (wenn min. ein Post Mindest-Score erreicht)
- Kosten, gemessen 30.06. bis 30.07.2026 über die Anthropic-Admin-API und die Apify-Run-Liste:
  - Apify `linkedin-profile-posts`: 0,32 bis 0,66 USD/Tag über beide Mandanten (76 bis 123 Runs)
  - Apify `linkedin-post-search`: 0,54 USD pro Jolly-Keyword-Lauf (Do), 0,30 USD pro Lisocon-Lauf
  - Anthropic: 15,94 USD/30d auf dem Projekt-Key, davon 11,15 Sonnet 4.6 und 4,79 Haiku 4.5.
    Normaler Wochentag ca. 0,25 USD, Slate-Tag (Mo+Do, Lisocon) bis 4,44 USD
  - kie.ai: ~0,02 USD pro Bild

## Email-Reminder (Scheduled Agent)

### Trigger
- Täglich 07:30 Canary-Zeit (06:30 UTC) via Scheduled Agent
- Agent ID: `trig_01UxjAikb8EBAhQT9hdu7U8h`

### Was passiert
1. Notion DB nach Einträgen mit Status "Ready to Review" durchsuchen
2. Wenn vorhanden: E-Mail mit Hinweis zum Reviewen
3. Wenn keine: keine E-Mail

### Verwalten
https://claude.ai/code/scheduled/trig_01UxjAikb8EBAhQT9hdu7U8h

## Status-Flow in Notion

```
New → (Daily Run) → Ready to Review → Approved → Posted
New → (Daily Run) → Skipped (nicht als Winner gewählt)
```

## Qualitätsfilter

- Posts unter 50 Wörtern: rausgefiltert beim Scraping
- Score unter 25/60: kein Content wird generiert, alle Posts bleiben "New" (nächster Run versucht es erneut)
- Leerer LinkedIn-Draft: Fehler wird geworfen, kein Notion-Update

## Fehlerbehandlung

- Apify-Fehler bei einem Profil → überspringen, weiter mit nächstem
- Kein APIFY_API_KEY → Script bricht ab
- Scoring-Fehler → nur Viralitäts-Score wird verwendet
- Bildgenerierung fehlgeschlagen → Post wird trotzdem als "Ready to Review" gespeichert (ohne Bild)
- Leerer LinkedIn-Draft → Run bricht ab, kein Notion-Update

## Content-Run (manuell, nur bei Bedarf)

Falls der tägliche Run keinen Winner findet oder ein Post manuell verarbeitet werden soll:

1. User gibt Claude die Notion-URL des gewünschten Posts
2. Workflow: `workflows/content_generation.md`
