# Uebernahme aus Jakeschincariol/linkedin-agent-skill (14.09.2026)

Quelle: Repo-Vergleich 14.09.2026. Vier Punkte, ein PR. Hook-Katalog und
Audit (Punkte 1 und 5) folgen als eigenes Brainstorming.

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
