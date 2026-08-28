# Leser-Gate statt Lektor-Note: Sinn- und Sprachpruefung fuer deutsche Beitraege

Stand 28.08.2026. Mandant SWOT, Runner `run_plan_fill.py`, Text-Maschinerie in
`tools/post_scorer.py`. Freigabe Richard 28.08.2026 (Weg 3, Budget 6-8 EUR).

## 1. Anlass und Befund

Richard las im Redaktionsplan den Opener "Den 13-Wochen-Cashforecast baut man
einmal auf und denkt, die Zahlen muessen stimmen. Stimmen sie nicht. Und das ist
in Ordnung." Drei Defekte in drei Saetzen: Verberststellung als Aussagesatz
(liest sich als abgebrochener Bedingungssatz), Opener widerspricht dem Text
(Absolution vorn, Toleranzpruefung hinten), "einmal aufbauen" ist fachlich
falsch (der Forecast ist rollierend). Derselbe Post traegt "baut kein Modell,
sondern eine persoenliche Ueberzeugung", die verbotene Antithese-Formel ohne
das Wort "Problem", an dem die Regex haengt.

Richards Anforderung: er liest keine Beitraege mehr, weder Bestand noch neue.
Die Pipeline muss ohne menschlichen Lese-Schritt liefern, was der Kunde nicht
zurueckweist.

Messung des DE-Prompts (Werner, Opinion, standard), live gebaut ueber
`post_writer.build_prompt`:

- 19.756 Zeichen, 2.726 Woerter, rund 5.500 Tokens
- 91 Regel- und Aufzaehlungszeilen, 64 davon mit Verneinung
- 8.335 Zeichen Stimmprofil (42 Prozent), 3.064 Zeichen Soundbyte- und
  Infografik-Anweisungen (15 Prozent)

Fuenf Ursachen, alle im Code belegt:

1. Der Prompt widerspricht sich. `_HERSTELLER_POSITION` (Zeichen 528): "schreibe
   nie, wo du etwas siehst". `LANGUAGE_BANS_DE` (Zeichen 12.533): Erlaubt ist
   die Beobachterposition "in Einfuehrungsprojekten sehe ich". Das ist die
   Phrase, die am 27.08. wegen 6 von 8 Treffern aus `_HERSTELLER_POSITION`
   entfernt wurde. Zweiter Widerspruch: werner.md verlangt "Kurze Hauptsaetze,
   kaum Nebensaetze", die Generik-Zeile 134 verbietet "Stakkato-Stil".
2. Verbote liefern den Wortlaut mit. "Das ist kein X-Problem, das ist ein
   Y-Problem" steht dreimal ausgeschrieben im Prompt (werner.md "nie sagen"
   Nr. 1, kulle.md Nr. 2, post_scorer Zeile 141). Dokumentierte Leaks
   derselben Art: "Glaube:" (24.08.), "In Einfuehrungsprojekten sehe ich"
   (27.08.), Fuellwoerter aus dem Profil (25.08.).
3. Gesprochene Sprache wird ungefiltert Schrift. Beide Profile stammen aus
   Call-Transkripten. Der Profilkopf sperrt Fuellwoerter, nicht Syntax.
   Echo-Antworten ("Stimmen sie nicht.") sind muendlich normal.
4. Der Gate misst Oberflaeche. Textwache: CAPS, Umlaute, Laenge (gut,
   deterministisch). Formel-Regex: je Vorfall eine, passt nur auf dessen
   Wortlaut. Lektor: Note 1-10 ueber elf Stilpunkte; eine Note mittelt, ein
   kaputter Opener plus neun saubere Absaetze ergibt eine 7. Keine Stufe fragt
   nach Schriftdeutsch, Kohaerenz oder Fachlogik.
5. Befunde landen nur auf stdout. Note 5 nach zwei Versuchen steht in Notion
   genauso als "Entwurf" wie Note 9.

## 2. Ziel und Nicht-Ziel

Ziel: jeder Beitrag, der in Notion als Entwurf steht, hat eine Leser-Pruefung
ohne offenen Befund bestanden. Was sie nach zwei Reparaturrunden nicht besteht,
steht nicht im Plan. Kein Lese-Schritt bei Jolly.

Nicht-Ziel: Themenmaterial anreichern (Kurzbeschreibung ist ein Satz, das
Modell erfindet den Rest; eigenes Thema), Kommentar-Engine, Bilder, Status-
Kette. Andere Mandanten (jolly, lisocon) bekommen den Leser nicht automatisch;
FEATURES-Flag je Mandant.

## 3. Bauteile

### A. Leser statt Lektor (`tools/naturalness.py`)

`CRITIC_PROMPT` (Note) wird durch `READER_PROMPT` (Befundliste) ersetzt.
Der Leser bekommt Text, Titel, Kurzbeschreibung und das Stimmprofil des
Kontos. Sieben Fragen, jede mit Zitatpflicht; keine Note, kein Mittelwert:

1. Schriftdeutsch: ein Satz, der als geschriebenes Deutsch nicht korrekt ist.
   Verbstellung, fehlendes Satzglied, Fragment, das als Nebensatz gelesen
   wird, Echo-Antwort aus der gesprochenen Sprache.
2. Kohaerenz: der erste Absatz behauptet etwas, das der Rest einschraenkt,
   widerlegt oder nicht aufgreift. Zitat beider Stellen.
3. Deckung: der Text loest ein, was Titel und Kurzbeschreibung versprechen.
4. Fachlogik: eine Aussage, die ein Controller oder Wirtschaftspruefer als
   falsch oder unpraezise erkennt (Verfahren, Frist, Fachbegriff, Zahl).
5. Schablone: rhetorische Formel, beschrieben statt als Wortlaut (Antithese
   in Serie, Negation-Negation-Korrektur, Pointen-Einzeiler, Sentenz,
   Dreier-Parallelismus).
6. Muendlichkeit: Fuellwoerter, Echo, Gespraechsfloskeln in Schrift.
7. Fremdstimme: Passage, die die Person laut Profil nicht schreiben wuerde,
   oder Beratersprech und Lehnuebersetzung, die kein Fachmensch nutzt.

Der Leser darf Beispiel-Wortlaute tragen (er schreibt nichts ab). Prinzip:
Verbotslisten mit Wortlaut gehoeren zum Leser, nie zum Schreiber.

Ausgabe JSON: `{"befunde": [{"art": "<schriftdeutsch|kohaerenz|deckung|
fachlogik|schablone|muendlich|fremdstimme>", "zitat": "<woertlich>",
"grund": "<ein Satz>", "vorschlag": "<wie ein Mensch es schreibt>"}]}`.
Leere Liste heisst sauber. Hoechstens 6 Befunde, schlimmste zuerst.
`parse_findings` gibt None bei unlesbarer Antwort (dann kein Urteil, Text
bleibt; gleiche Regel wie `parse_verdict` heute).

Deterministische Befunde bleiben und fliessen in dieselbe Liste: `tic_hits`
(art "schablone"), `long_sentences` (art "satzlaenge"). Die Regex-Liste
waechst nicht mehr; der Leser ist der allgemeine Fang. `phrases` und
`avoid_note` (Wiederholung ueber den Lauf) bleiben unveraendert, der Leser
sieht keine anderen Beitraege.

### B. Chirurgische Reparatur (`tools/post_scorer.py`)

`_naturalness_loop` (Vollneulauf aus dem 20k-Prompt, bessere Fassung bleibt)
wird durch `_reader_loop` ersetzt:

1. Leser liest den Text (nach `_finish_draft`).
2. Befunde vorhanden: ein Sonnet-Call `FIX_PROMPT` mit Text und Befundliste.
   Vertrag: nur die zitierten Passagen aendern, jede andere Zeile bytegleich,
   Fakten und Zahlen unangetastet, kein Kommentar, nur der Text. Laengen-Guard
   wie `grammar_check` (Abweichung hoechstens 15 Prozent oder 80 Zeichen,
   sonst Reparatur verworfen). Danach `text_gate.hard_violations`; Verstoss
   verwirft die Reparatur.
3. Leser liest erneut. Befunde: Runde 2 wie Schritt 2.
4. Nach `MAX_FIX_ROUNDS = 2` Reparaturen noch Befunde: Text wird "" (verworfen,
   Zeile bleibt ohne Text, naechster Lauf schreibt neu). Fail-closed, gleiche
   Semantik wie CAPS und Ueberlaenge heute. Log nennt die Restbefunde.

Der Vollneulauf entfaellt. Die Neuerzeugung eines verworfenen Beitrags ist
Sache des naechsten Laufs (`text_fill` schreibt Zeilen ohne Text).

### C. Prompt-Diaet (`clients/swot/config.py`, `clients/swot/voices/*.md`, `tools/post_scorer.py`)

Jede Aenderung mit Beleg aus Abschnitt 1:

1. `LANGUAGE_BANS_DE`: Satz "Erlaubt ist die Beobachterposition: ..." raus.
   Interim-CFO-Verbot bleibt, auf zwei Saetze gekuerzt. Zeile "Glaube ist kein
   Fachwort" raus (der Leser faengt es, Signature-Struktur sagt schon Annahme).
2. `post_scorer.py` Zeile 141: die vier ausgeschriebenen Formeln raus. Ersatz
   ohne Wortlaut: "Keine rhetorischen Schablonen: keine Antithesen in Serie,
   keine Pointen-Einzeiler, keine Sentenzen." Gilt fuer alle Mandanten; das
   ist die eine Generik-Aenderung. `post_writer._TOPIC_REPLACEMENTS`-Anker
   bleiben unberuehrt (Assert schuetzt).
3. `werner.md`, `kulle.md`, Abschnitt "Was er nie sagen wuerde": zitierte
   Formeln und Buzzwords durch Beschreibungen ersetzen (Beispiel: "Antithese
   als Formel: er denkt in Faellen" statt des Wortlauts). Typische Wendungen
   bleiben, sie sind gewollt.
4. `load_voice_profile` Profilkopf: "Es beschreibt gesprochene Sprache.
   Uebernimm Rhythmus, Bilder, Haltung und Wortwahl. Der Satzbau bleibt
   Schriftdeutsch: vollstaendige Saetze, Verb an zweiter Stelle, keine
   Echo-Antworten und keine Fragmente als Aussagesatz." Damit ist der
   Widerspruch Stakkato gegen Kurze Hauptsaetze entschieden: Schrift gewinnt.
5. Infografik-Split: TEIL 2 bis 4 (Soundbyte, Kontext, Infografik-Skelett)
   verlassen `DACH_POST_PROMPT`. Der DE-Call liefert nur `===POST===`. Bei
   `FEATURES["en_draft"] = False` erzeugt ein zweiter, kleiner Call
   (`PARTS_PROMPT`, Haiku) Soundbyte, Kontext und Skelett aus dem fertigen
   Text; Ausgabeformat und Parser (`_parse_generation_response`) bleiben.
   Mandanten mit EN-Draft beziehen diese Teile weiter aus dem EN-Call, fuer
   sie aendert sich nur die Laenge des DE-Prompts.

Erfolgskriterium: Befunde je Post im Trockenlauf (8 Posts) niedriger als im
Bestand aus Schritt 1. Prompt-Laenge wird vorher und nachher gemessen und im
Plan notiert; ein Zielwert ist keine Zusage.

### D. Bestandslauf (`run_review_backfill.py`, einmalig, SWOT)

Zwei Modi. `--report`: Leser ueber alle Zeilen Typ LinkedIn-Post, Status
Entwurf, Post-Text nicht leer; schreibt Befunde als Markdown und JSON, nichts
nach Notion. `--write`: je Zeile Leser plus Reparatur (B), bereinigten Text
zurueckschreiben; Restbefund leert den Post-Text, Normal-Lauf fuellt nach.

Regeln:

- Status "Text freigegeben" und hoeher wird nie angefasst. Zusage an den
  Kunden ist Teil der Zusage.
- Backup aller Post-Texte als JSON vor dem ersten Schreiben, Pfad im Log.
- CTA-Zeile ("30 Minuten mit unseren Planungs- und Konsolidierungsexperten,
  kostenfrei: https://www.swot.de/demo-buchen/") wird vor dem Lesen entfernt
  und nach der Reparatur wieder angehaengt; der Leser sieht sie nie.
- Rueckschreiben gechunkt (`_chunks`, 1990 UTF-16-Einheiten), Readback je
  Zeile, Zaehler im Log.
- Notion ueber die API aus Python (kein MCP-Limit).

### E. CTA in der Pipeline (`clients/swot/config.py`)

SWOT hat kein `CTA_DE`; der Buchungslink auf den 51 Posts stammt aus dem
Notion-Handlauf vom 28.08. Jeder neue Pipeline-Post kaeme ohne Link.
`CTA_DE = "30 Minuten mit unseren Planungs- und Konsolidierungsexperten,
kostenfrei: https://www.swot.de/demo-buchen/"`; `_append_cta` haengt ihn an,
`blanket_cta` laesst Magnet und Offer aus (fuer SWOT gesperrt, ohne Wirkung).

## 4. Datenfluss je Beitrag (neu)

1. `_generate_de` (Prompt ohne TEIL 2-4)
2. `text_gate.violations`, ein Neulauf bei Befund (unveraendert)
3. `_finish_draft`: grammar_check, hard_violations (unveraendert)
4. `_reader_loop`: Leser, bis zu zwei Reparaturen, Leser; Rest verwirft
5. `_parts_call` (Haiku) fuer Soundbyte, Kontext, Skelett, nur ohne EN-Draft
6. `enforce_magnet_cta`, `_append_cta` (unveraendert)

Calls je sauberem Beitrag: Generierung, Grammatik, Leser, Teile. Je Reparatur
zwei weitere (Fix, Leser). Kein Vollneulauf mehr.

## 5. Tests

- `test_naturalness.py`: `reader_prompt` enthaelt Titel, Kurzbeschreibung und
  Profil; `parse_findings` liest gueltiges JSON, kappt auf 6, gibt None bei
  Muell; deterministische Befunde werden mit Art gemischt.
- `test_post_scorer_reader.py` (Mock): sauber ohne Reparatur; ein Befund,
  eine Reparatur, dann sauber; Reparatur verworfen bei Laengen-Guard; Rest
  nach zwei Runden gibt ""; Fix-Prompt traegt die Zitate.
- `test_post_writer_machinery.py`: Anker von `_TOPIC_REPLACEMENTS` weiter
  vorhanden; Prompt ohne "sehe ich"-Erlaubnis, ohne ausgeschriebene Formeln,
  ohne TEIL 2-4; Profilkopf traegt die Schriftdeutsch-Regel.
- `test_parts_call.py` (Mock): ohne EN-Draft kommen Soundbyte und Skelett aus
  dem zweiten Call; mit EN-Draft unveraendert aus dem EN-Call.
- `test_review_backfill.py`: Freigegebene Zeilen werden uebersprungen; CTA
  wird entfernt und wieder angehaengt; Restbefund leert den Text; Backup
  wird vor dem ersten Schreiben geschrieben.
- Suite bleibt gruen (heute 608; 4 vorbestehende Fehler nur unter CLIENT=swot).

## 6. Reihenfolge mit Pruefkriterium

1. Leser als `--report` ueber den Bestand. Kriterium: Claude klassifiziert
   jeden Befund als echt oder Fehlalarm; Fehlalarmquote unter 10 Prozent,
   sonst Prompt nachstellen, wiederholen. Ergebnis: Befundrate je Post als
   Basislinie.
2. Diaet, dann 8 Beitraege trocken erzeugen und lesen. Kriterium: Befunde je
   Post unter der Basislinie.
3. Leser und Reparatur verdrahten, Split, CTA. Kriterium: Tests gruen, ein
   Trockenlauf mit Log zeigt Leser, Reparatur, Verwerfen.
4. Bestandslauf `--write`, danach `run_plan_fill --months 2026-09 2026-10
   2026-11 --write` fuer geleerte Zeilen. Kriterium: Live-Read aus Notion,
   kein Entwurf ohne Text, Readback je Zeile, Restbefunde 0.

## 7. Kosten

Basis 0,10 EUR je Beitrag heute (gemessen 25.08., 8 Posts mit Neulauf 0,8 EUR).
Schritt 1 rund 1 EUR (auch bei zwei Durchgaengen), Schritt 2 rund 1 EUR,
Schritt 4 rund 3 EUR plus 1-2 EUR Nachfuellen. Gesamt 6-8 EUR, freigegeben.
SWOT-Konto: Anthropic-Key des Recycling-Repos (kein Mandanten-Key fuer Text).

## 8. Risiken

- Leser-Fehlalarme kosten Reparaturen und verwerfen gute Texte. Deshalb
  Schritt 1 vor allem anderen und die 10-Prozent-Schwelle.
- Die Generik-Zeile 141 und der Split betreffen jolly und lisocon. Beides
  wird per Test gegen Anker und Ausgabequelle gesichert; Output-Semantik fuer
  EN-Mandanten unveraendert.
- Kurzbeschreibung als einziges Material bleibt duenn; der Leser faengt
  Erfindungen, erzeugt aber keinen Inhalt. Getrennt nachziehen.
- Werners "Kurze Hauptsaetze" bleiben im Profil; die Schriftdeutsch-Regel
  entscheidet nur die Syntax, nicht die Satzlaenge. Ob der Ton darunter
  leidet, zeigt Schritt 2.

## 9. Nachtrag 28.08.2026 abends

Drei Abweichungen und Messungen aus der Umsetzung, jede mit Grund. Der Text
oben bleibt als Entwurfsstand stehen; hier gilt der Nachtrag.

1. B.4 (Restbefund verwirft) gilt nicht mehr. Verworfen wird ein Text nur
   noch, wenn harte Befunde (Sinnfehler: schriftdeutsch, kohaerenz, deckung,
   fachlogik, `naturalness.HARD_ARTEN`) oder die Textwache offen bleiben.
   Weiche Reste (Schablone, Fremdstimme, Muendlich, Satzlaenge) bleiben mit
   Log stehen: der Trockenlauf verwarf 3 von 3 Texten, weil der Reparierer
   eine Formel durch die naechste ersetzte und der Leser sie wiederfand.
   Zweite Aenderung nach dem Bestandslauf: hatte der Eingangstext keinen
   harten Befund und traegt erst die Reparatur einen, gilt wieder das
   Original. Beleg: 5 von 7 Leerungen im Bestandslauf gingen auf harte
   Befunde zurueck, die der Eingangstext nicht hatte. Der Loop hielt nur den
   letzten Stand und entschied am Ende ueber ihn, damit war die Reparatur
   der einzige Grund fuer die Leerung.
2. Erfolgskriterium aus Abschnitt 6, Schritt 2 (Befunde je Post unter der
   Basislinie) ist gemessen und NICHT erfuellt: ALT 4,12 Befunde je Post,
   NEU 5,62, n = 8, dieselben acht Themen, derselbe Leser mit demselben
   Prompt. Der DE-Prompt schrumpfte dabei von 20.001 auf 16.739 Zeichen.
   Die Zunahme sitzt bei Schablone (14 auf 22) und stammt aus dem
   Genre-Prior des Modells, nicht aus Beispielen im Prompt. Ruling: der Hebel
   ist der Loop (Leser plus chirurgische Reparatur), nicht die Prompt-Diaet.
   Die Diaet bleibt, weil sie Widersprueche und Wortlaut-Leaks entfernt hat;
   eine dritte Messrunde wird dafuer nicht bezahlt.
3. Der Leser laeuft mit Structured Output (`output_config` mit
   `json_schema`, `naturalness.READER_SCHEMA`, max_tokens 4096) statt mit
   "Antworte NUR mit JSON". Sonde 28.08.2026: Sonnet 4.6 schrieb vorher eine
   Prosa-Analyse samt Volltext-Zitat vor das JSON und lief bei 1024 Tokens
   ins Limit, 7 von 12 Antworten kamen ohne JSON zurueck. Prefill gibt es
   auf diesem Modell nicht mehr. Faellt der Leser aus, ist das kein Urteil
   mehr, sondern ein Ausfall: `ReaderUnavailable`, der Text wird verworfen
   (fail-closed) und `post_scorer.READER_FAILURES` zaehlt ihn.
