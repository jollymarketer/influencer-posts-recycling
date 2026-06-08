# Workflow: Keyword-based LinkedIn Scrape (Topic-Mining Input)

## Ziel
Blog-Themen-Quelle über die 78 Influencer hinaus erweitern: LinkedIn-Posts nach Jolly's
Ziel-Keywords scrapen (die Themen, für die jolly ranken / zitiert werden will) und in denselben
Mining-Topf legen wie der Influencer-Scrape.

## Quelle der Keywords
Abgeleitet aus dem AI-Visibility-Scoreboard (Lücken + Brückenköpfe). Locked 2026-06-08, hinterlegt in
`run_keyword_scrape.py` `KEYWORDS`. Bewusst RAUS: HubSpot, Cold Calling, generisches "AI marketing".

## Architektur (klinkt in die bestehende Mining-Kette ein)
```
run_keyword_scrape.py
  -> harvestapi/linkedin-post-search (searchQueries = KEYWORDS)
  -> Posts (>=50 Wörter, dedup)
  -> supabase_db.upsert_posts(source="linkedin_search")
        └─> blog_content_mining.influencer_posts   (gemeinsam mit Influencer-Posts)
  -> (Freitag) run_topic_mining.py clustert ALLE Quellen der letzten 7 Tage -> Topic-Ideas Notion DB
  -> (manuell) Richard promotet Kandidaten -> Jolly Blogging Agent
  -> (Blogging Agent) Kannibalisierungs-Check filtert Dupes gegen jollymarketer.com live content
```

## Tool
- `tools/linkedin_keyword_scraper.py` — Actor-Call + Parsing (gleiche Post-Dict-Form wie der
  Profil-Scraper). Kein 6-36h-Altersfilter (Mining will Themen-Breite, nicht frische Viralität);
  Recency über `postedLimit` des Actors.

## Ausführen
```
python run_keyword_scrape.py                     # voller Lauf (18 Keywords, 20 Posts/Query)
python run_keyword_scrape.py --max-posts 10       # billiger
python run_keyword_scrape.py --keywords "revops"  # Subset / Verifikations-Lauf
python run_keyword_scrape.py --no-write           # nur scrapen, kein Upsert (Shape prüfen)
```

## Kosten (Apify PAY_PER_EVENT, harvestapi/linkedin-post-search)
- Post-Result: $0.002/Post. Optionale Main-Profile-Anreicherung ggf. +$0.002/Post (unverifiziert).
- 0-Result-Query: $0.001. Actor-Start: ~$0.00005.
- Richtwert voller Lauf: 18 × 20 = 360 Posts ≈ $0.72 (nur Posts) bis ~$1.44 (mit Main-Profile).
- **Spend-Gate ≥1 EUR**: vor dem ersten vollen Lauf Freigabe holen. Empfehlung: erst billiger
  Verifikations-Lauf (3 Keywords × 5) zur Shape- + Kosten-Kontrolle.

## Cadence
On-demand oder wöchentlich VOR der Freitag-Clusterung (damit die Posts im 7-Tage-Fenster liegen).
Eigenständig, kein Railway-Cron (vorerst manuell, bis Kosten/Nutzen bestätigt).

## Self-improvement Log
- 2026-06-08: Tool gebaut. Output-Item-Shape von linkedin-post-search beim ersten Live-Lauf gegen den
  Parser prüfen (Autor-Feld: `author.name` vs `authorFullName`). Real-Kosten/Post messen.
