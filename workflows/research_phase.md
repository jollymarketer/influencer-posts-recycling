# Workflow: Research Phase (Täglicher Run)

## Ziel
Neue LinkedIn-Posts der 20 GTM/RevOps-Influencer finden und als Recycling-Vorschläge in Notion speichern.

## Trigger
- Täglich 07:00 UTC via Railway Cron (`0 7 * * *`)
- Manuell: `python run_research.py` im Projektverzeichnis

## Inputs
- `influencers.csv` — Liste der 20 Influencer-Profile
- Notion DB `778bd719db9147ff994ddbf8a4ecac34` — bestehende Posts (Duplikat-Filter)

## Ausführung

```bash
cd "Jolly Automations/Influencer Posts Recycling"
python run_research.py
```

## Was passiert intern

1. **Duplikat-Filter**: Alle bereits gespeicherten Post-URLs aus Notion laden
2. **Scraping**: Apify Actor `harvestapi/linkedin-profile-posts` für jeden Influencer
   - `maxPosts=10`, `postedLimit="week"` (nur Posts der letzten 7 Tage)
   - Nicht-reposts, keine Comments/Reactions (spart Credits)
3. **Filterung**: Nur Posts die noch nicht in Notion sind
4. **Notion-Eintrag**: Für jeden neuen Post → Eintrag mit Status `Make your Choice`

## Output
- Neue Einträge in Notion DB (Status: `Make your Choice`)
- Console-Log mit Summary (Posts gefunden / gespeichert / Fehler)

## Kosten
- Apify: ~$0.002 pro Post × 200 Posts/Run ≈ $0.40/Tag
- Wenn 10 Posts pro Influencer × 20 Influencer = max. 200 Posts/Run (in Praxis weniger durch Duplikat-Filter)

## Fehlerbehandlung
- Apify-Fehler bei einem Profil → überspringen, Fehler loggen, weiter mit nächstem
- Notion-Schreibfehler → Fehler loggen, weiter mit nächstem Post
- Kein APIFY_API_KEY → Script bricht mit klarer Fehlermeldung ab

## Nach dem Run
→ Notion öffnen: https://www.notion.so/778bd719db9147ff994ddbf8a4ecac34
→ Post auswählen (Status bleibt `Make your Choice`)
→ Claude die Notion-URL des gewünschten Posts geben
→ Weiter mit `content_generation.md`
