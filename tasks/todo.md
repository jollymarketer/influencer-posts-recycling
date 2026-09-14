# Uebernahme aus Jakeschincariol/linkedin-agent-skill (14.09.2026)

Quelle: Repo-Vergleich 14.09.2026. Vier Punkte, ein PR. Hook-Katalog und
Audit (Punkte 1 und 5) folgen als eigenes Brainstorming.

## Hook-Katalog und Audit (Plan docs/superpowers/plans/2026-09-14-hook-katalog-und-audit.md)

- [x] Tasks 1-6: Katalog, Rotation, Prompt-Zeile, Notion "Hook" (geseedet in
      der Jolly-DB 14.09.2026), Hook-Wahl im Winner-Flow, 140-Zeichen-Hinweis.
      Commits ab63ada, 9d70a07. Suite 767.
- [ ] Tasks 7-11 (Audit): zurueckgestellt, Entscheidung Richard 14.09.2026.
      Median 152 Impressions je Post, Audit misst Rauschen. Wiedervorlage bei
      fuenffacher Reichweite. Stattdessen: Kommentar-Drafts fuer Jolly.

## Kommentar-Drafts Jolly auf Zielgruppen-Watchlist (14.09.2026)

- [x] Messlauf 1 Keyword-Suche: 1-2 Kaeufer-Posts je Woche, verworfen.
- [x] Messlauf 2 HubSpot warm (245): 55 aktiv in 14 Tagen, 5,5 je Werktag.
- [x] ABM-Pfad: Tageslauf, Rotation, Kunden-Sperrliste, Haiku-Gate, Typ im Titel.
- [x] Jolly-Config ABM_COMMENT_DRAFTS (3 je Tag), Verdrahtung in run_research.main,
      Notion-Seed (Kommentar-Ziel, ABM-Autor, ABM-Domain, Poster, Status).
- [x] tools/jolly_watchlist.py (HubSpot + SN-Poster + Pool-aktiv -> CSV).
- [ ] Aktivitaets-Sieb 1.938 Bestandspersonen (Freigabe 3,90 USD), laeuft.
- [ ] Sales Navigator Stack 3 (Poster 30 Tage), 6 Slices, laeuft bis SN-Ende 17./18.09.
- [ ] Watchlist-CSV bauen, committen; Railway zieht den Code beim naechsten Cron.
- [ ] Erster Livelauf pruefen: 3 Zeilen "ABM Kommentar" in der Jolly-DB.

## Plan

- [x] Textwache: Satzlaengen-Rhythmus (Variationskoeffizient unter 0.35 ab
      vier Saetzen), gleichfoermige Listenpunkte (ab drei, Stdabw unter 1.6),
      Dreier-Parallelismus aus Kleinwoertern, Pointen-Frage als Einzeiler.
      Alles weich: nur der eine Neulauf mit Hinweis, kein Verwerfen.
      verify: tests/test_text_gate.py, Kalibrierung an Kulles Schreibproben
- [x] sanitize_generated_text: unsichtbare Zeichen (Unicode Cf) raus, ZWJ in
      Emoji-Sequenzen bleibt, geschuetzte Leerzeichen zu Leerzeichen,
      Auslassungspunkte zu drei Punkten. Deutsche Anfuehrungszeichen bleiben.
      verify: tests/test_sanitize_and_cta.py
- [x] Kommentar-Typen: neun Typen im COMMENT_PROMPT, TYP-Zeile im Output,
      Typ im Titel, letzter Typ des Laufs wird gemieden, deutsche Floskel-
      Sperrliste, kein Emoji als erstes Zeichen.
      verify: tests/test_comment_types.py
- [x] Gesamtsuite gruen (Baseline 731 passed), Commit und Push.

## Nicht uebernommen

- "nicht nur X, sondern auch Y": im Deutschen normale Konstruktion, hohe
  Fehlalarmquote; "kein A, sondern B" faengt naturalness.TICS schon.
- Englisches Slop-Lexikon, VOICE-Score (Kontraktionen, Pronomen): nur englisch.
- Curly Quotes zu geraden: deutsche Typografie ist korrekt.

## Review

- Suite: 746 bestanden (731 Baseline plus 15 neue), keine Netzaufrufe.
- Zwei Altbestandstests in test_distribution_loop mockten draft_comment ohne
  den neuen Schluessel "typ"; Callsite liest ihn per .get, Tests unveraendert.
- Kalibrierung: Kulles Schreibproben ohne Rhythmus-Befund (Regressionstest).
- Verwerfquote vorher/nachher: lokal keine Baseline, nur Railway-Logs.
- Naechster Schritt: Brainstorming Hook-Katalog plus Audit (Punkte 1 und 5).
