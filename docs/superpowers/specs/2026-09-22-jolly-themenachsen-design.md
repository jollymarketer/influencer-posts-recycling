# Jolly Themenachsen: Vielfalt in der Themenwahl

Stand 2026-09-22. Mandant jolly. SWOT und lisocon bleiben unberuehrt.

## Problem, gemessen

Die letzten 40 Drafts aus jollys Content-DB, handklassifiziert am 2026-09-22:

| Themenblock | von 40 |
|---|---|
| Pipeline, Forecast, CRM-Daten | 10 |
| Outbound, Cold Email, Sequenzen | 7 |
| ICP, Targeting, Trigger | 6 |
| System vor Headcount | 4 |
| Auswahl externer GTM-Hilfe | 4 |
| Content, LinkedIn | 3 |
| KI im Vertrieb | 1 |
| Rest | 5 |

Drei Bloecke belegen 23 von 40 Posts, also 58 Prozent. Kein einziger Draft ist ein Tipp oder eine
Anleitung. Vier strukturelle Ursachen:

1. `clients/jolly/config.py:65` `TOPIC_FIT_QUESTION` nennt sieben Felder. Alles ausserhalb bekommt
   niedrigen `topic_fit` und erreicht `MIN_SCORE` nie.
2. `clients/jolly/config.py:29` VOC-Block gibt vier Kaufprobleme vor und weist den Writer an,
   generierte Posts bevorzugt in diese Rahmen zu setzen.
3. `clients/jolly/config.py:224` `MATRIX` mischt Job mal Stage, nie Thema. Anti-Repeat laeuft ueber
   `get_recent_linkedin_drafts(7)`, also sieben Tage Gedaechtnis.
4. `run_keyword_scrape.py` `JOLLY_KEYWORDS`, 20 Begriffe, gelockt 2026-06-08, alle kommerziell eng.
   Was nicht gescrapt wird, kann kein Thema werden.

Quellenlage im Pool, gemessen in `blog_content_mining.influencer_posts` am 2026-09-22:

| Fenster | jolly linkedin | jolly linkedin_search | jolly substack |
|---|---|---|---|
| 7 Tage | 188 | 43 | 3 |
| 30 Tage | 658 | 263 | 11 |
| 90 Tage | 696 | 274 | 14 |

81 Prozent des Pools ist Profil-Scrape und traegt heute keine Achsen-Herkunft.

## Achsen

Acht Achsen, Schluessel wie hier geschrieben:

| Achse | Inhalt |
|---|---|
| `outbound_maschine` | Sequenzen, Kanalmix, Deliverability, Listen, Trigger |
| `daten_und_revops` | CRM-Hygiene, Forecast, Attribution, Reporting, Stage-Definition |
| `positionierung_und_angebot` | ICP, Offer-Design, Preis, Differenzierung, Messaging |
| `sales_prozess` | Qualifizierung, Discovery, Buying Committee, Einwaende, Verhandlung, Closing |
| `team_und_enablement` | erster Sales-Hire, Ramp, Playbook, Provisionsmodell, fractional vs. intern |
| `inbound_und_content` | LinkedIn-System, Content-Ops, SEO und AEO, Webinare, Lead Magnets |
| `bestand_und_expansion` | Onboarding, Retention, Upsell, Churn-Signale, Customer Success |
| `ki_im_gtm` | AI SDR, Agenten, Recherche-Automatisierung, GTM Engineering |

Kriterien: kaufrelevant fuer Founder und Sales-Entscheider, kein Wettbewerber-Terrain (Agentur- und
Vertriebsberatungs-Themen bleiben draussen), genug LinkedIn-Angebot fuer den Scrape.

Bewusst nicht gesetzt: Pricing als eigene Achse (liegt in `positionierung_und_angebot`),
Partnerschaften und Channel-Vertrieb (zu wenig DACH-Angebot, wuerde leer laufen).

## Teil A: Daten und Achsen

`KEYWORDS_BY_AXIS` in `clients/jolly/config.py`, gleiche Struktur wie `clients/swot/config.py:641`.
Die 20 gelockten Keywords werden zugeordnet, nicht ersetzt:

| Achse | aus JOLLY_KEYWORDS |
|---|---|
| `outbound_maschine` | cold email, cold email deliverability, email warmup, intent data |
| `daten_und_revops` | revenue operations, revops automation, sales forecasting |
| `positionierung_und_angebot` | ideal customer profile, fractional cmo, go-to-market strategy, account based marketing |
| `sales_prozess` | buying committee |
| `team_und_enablement` | keiner |
| `inbound_und_content` | b2b lead generation, demand generation, answer engine optimization |
| `bestand_und_expansion` | keiner |
| `ki_im_gtm` | gtm engineering, ai sdr, ai personalization sales |

Ziel sind 6 bis 10 Begriffe je Achse, also grob 60 statt 20. Die Auffuellung, besonders fuer
`team_und_enablement` und `bestand_und_expansion`, wird Richard als Tabelle vorgelegt und erst nach
seinem Blick committet. Profilliste bleibt in diesem Schritt unveraendert.

`JOLLY_KEYWORDS` in `run_keyword_scrape.py` wird zur abgeleiteten Liste aus `KEYWORDS_BY_AXIS`, damit
keine zweite Wahrheit entsteht. Der Donnerstags-Lauf bleibt funktionsgleich. `run_axis_scrape.py`
braucht keine Aenderung, es liest `KEYWORDS_BY_AXIS` per `getattr` und schreibt
`source="linkedin_search:<achse>"`.

Neue Spalte `axis` in `blog_content_mining.influencer_posts`, nullable, per Migrations-SQL in
`scripts/`. Zwei Schreibwege:

- Der Achsen-Scrape (`run_axis_scrape.py`) setzt sie direkt aus der Herkunft.
- `run_keyword_scrape.py` schreibt sie ueber die Umkehrung von `KEYWORDS_BY_AXIS`, also Begriff nach
  Achse. Ohne das bliebe der Donnerstags-Lauf achsenlos und muesste teuer nachklassifiziert werden.
- Profil- und Substack-Posts bekommen sie vom Klassifizierer.

Neues Modul `tools/axis_classifier.py`. Ein Haiku-Call je Post, Ausgabe genau eine Achse oder `null`
fuer "passt in keine". Nur Zeilen mit `axis IS NULL` laufen durch, das Ergebnis wird
zurueckgeschrieben und nie neu berechnet. `null` bleibt `null`, sonst klassifiziert jeder Lauf
dieselben Grenzfaelle neu.

Der Klassifizierer laeuft ausschliesslich bei jolly. Zwei Sperren:

- Feature-Flag `axis_classifier` existiert nur in `clients/jolly/config.py`. Fehlt es, ist der Aufruf
  ein No-Op, kein stiller Fallback.
- Direkter Aufruf mit einem anderen Mandanten scheitert hart mit Klartext, Muster wie
  `resolve_keywords` in `run_keyword_scrape.py` und die Kontowache in `tools/apify_auth.py`.

SWOT bleibt unberuehrt: dort traegt die Achse weiter der `source`-String, `tools/monthly_plan.py`
liest sie wie bisher, die Spalte `axis` wird fuer SWOT nicht geschrieben. lisocon hat weder
`supabase_persist` noch `topic_mining` und faellt heraus.

## Teil B: Auswahl und Deckel

Neue Notion-Property `Achse` in jollys Content-DB, Select mit den acht Werten, angelegt per Skript in
`scripts/` nach dem Muster von `scripts/add_format_property.py`. `run_research.py` schreibt sie beim
Erstellen des Entwurfs, Quelle ist die Achse des Winner-Posts.

Neue Funktion `get_recent_axes(limit=10)` in `tools/notion_db.py`, gebaut wie `get_recent_formats`.

Deckel in Schritt 4 von `run_research.py`: jede Achse, die im Fenster der letzten 10 Posts bereits
zweimal vorkommt, ist gesperrt. Gesperrte Achsen fallen aus den Kandidaten, danach greift die
bestehende Reihenfolge unveraendert weiter, also Matrix-Box, Format, Persona. Posts mit `axis = null`
gelten als frei und werden nie gesperrt.

Pool-Rueckgriff, wenn nach dem Deckel kein Kandidat uebrig ist: `run_research.py` liest
`get_posts_since(7)` aus Supabase, filtert auf freie Achsen und auf Posts, die nicht bereits Winner
waren, scort sie und nimmt den besten ueber `MIN_SCORE`. Das Muster dafuer steht in `run_slate.py`,
das einen Pool-Bestand genau so scort. Erst wenn auch das leer ist, endet der Lauf ohne Entwurf, mit
Log welche Achse blockiert hat und wie viele Kandidaten je Achse vorlagen.

Bekannte Folge: der Rueckgriff kann Posts bis 7 Tage Alter ziehen, das Tagesfenster ist 6 bis 36
Stunden (`SCRAPE` in `clients/jolly/config.py`). Ein Entwurf kann sich dann auf einen aelteren
Quell-Post stuetzen. Bei jolly haengt kein Format an Aktualitaet, deshalb akzeptiert.

## Teil C: Rahmen oeffnen, sonst wirkt der Deckel nicht

Der Deckel wirkt erst, wenn achsenfremde Posts bis zur Auswahl kommen. Zwei Aenderungen in
`clients/jolly/config.py` gehoeren deshalb in dieselbe Lieferung:

- `TOPIC_FIT_QUESTION` (Zeile 65) wird auf die acht Achsen umformuliert. Gleiche Rolle, breiterer
  Rahmen.
- Der VOC-Block (ab Zeile 29) bleibt als Bewertungshilfe, verliert aber die Anweisung, jeden
  generierten Post in die vier Problem-Rahmen zu setzen. Die vier Kaufprobleme sind belegt und
  bleiben stehen. Die harten VOC-Regeln bleiben unveraendert: keine US-Zahlen als DACH-Fakt, nie
  "Kaltakquise ist tot", keine Anbieter- oder Agenturnamen.

## Messung

- Backfill des Klassifizierers ueber die 696 LinkedIn-Zeilen der letzten 90 Tage. Ergebnis ist die
  Achsen-Verteilung des Angebots, belegt statt vermutet.
- Die 40 handklassifizierten Drafts laufen durch denselben Klassifizierer. Das ist der Ausgangswert
  des Outputs.
- Nach 10 neuen Posts die Verteilung erneut ziehen.

Erfolgskriterium: keine Achse ueber 2 von 10, mindestens 5 der 8 Achsen vertreten.

## Tests

In `tests/`, alle ohne Netz mit festen Zeilen:

- Deckel sperrt bei zwei Vorkommen im Fenster, sperrt nicht bei einem.
- `axis = null` wird nie gesperrt.
- Pool-Rueckgriff zieht nur aus freien Achsen und nie einen Post, der bereits Winner war.
- Kein Kandidat und leerer Pool endet ohne Entwurf und ohne Ausnahme.
- Klassifizierer ist No-Op ohne Flag und scheitert hart bei direktem Aufruf mit fremdem Mandanten.
- Bestehende Tests fuer Format, Persona und Matrix bleiben unveraendert gruen.

## Kosten

- Haiku-Backfill fuer 696 plus 40 Zeilen, grob 400.000 Eingabe-Token, unter 1 EUR. Laufender Betrieb
  230 Posts pro Woche, wenige Cent. Anthropic-Konto jolly (`ANTHROPIC_API_KEY`).
- Apify-Achsen-Scrape ist die einzige nennenswerte Position und noch unbeziffert. Actor
  `harvestapi/linkedin-post-search`, Abrechnung je gelieferter Post. Messlauf auf einer Achse mit
  `--max-posts 5`, Hochrechnung auf 8 Achsen mal etwa 60 Begriffe, dann Freigabe durch Richard vor
  dem ersten vollen Lauf.

## Reihenfolge

1. Keyword-Zuordnung je Achse, Richard legt sie frei.
2. Spalte `axis`, Klassifizierer, Backfill, Verteilung messen.
3. Notion-Property `Achse`, `get_recent_axes`, Deckel, Pool-Rueckgriff, Tests.
4. `TOPIC_FIT_QUESTION` und VOC-Block oeffnen.
5. Apify-Messlauf, Freigabe, Achsen-Scrape scharfstellen.
6. Nach 10 Posts nachmessen.
