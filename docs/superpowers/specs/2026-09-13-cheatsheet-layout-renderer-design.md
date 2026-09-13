# Cheat-Sheet-Layouts: gesetzte Bilder statt KI-Render fuer strukturierte Posts

Stand 13.09.2026. Mandant Jolly (zuerst), Runner `run_research.py` und
`run_image_fill.py`, Bild-Maschinerie in `tools/image_archetypes.py` und
`tools/kieai_image.py`. Freigabe Richard 13.09.2026: Struktur von Michel
Lieben, Farben von Jolly, Archetypen in die Pipeline, Logos aus einer lokalen
Bibliothek, Renderer mit Pillow (Weg 2).

## 1. Anlass und Befund

Richard will den Bildstil von Michel Lieben (ColdIQ) fuer eigene LinkedIn-Posts
reproduzieren. Grundlage sind 56 Posts (15.06. bis 10.09.2026), je Bild eine
Strukturbeschreibung als JSON:

```
C:\Users\richa\Jolly_Claude_Code\Jolly Second Brain\michel-lieben\images\json\
```

Was die 56 Dateien zeigen:

- 40 von 56 Bildern sind gesetzte Layouts: Bento-Raster mit nummerierten
  Karten (05, 07, 29, 46, 59, 62, 65, 68), gestapelte Ebenen (04, 19, 56),
  Vergleichstabellen (23, 57), Flowcharts (21, 27, 60, 67), Tool-Landkarten
  (06, 15, 22, 25, 50). Die reichweitenstaerksten Bilder mit Text sind alle
  davon: 59 (757 Likes), 23 (546), 56 (529), 64 (466), 68 (452), 65 (386).
- Kein einziges davon ist ein KI-Render. Text ist pixelgenau, Logos sind echt,
  Layouts wiederholen sich mit identischen Massen (Logo-Kachel 56 px,
  Kartenradius 12 bis 28 px, Zeilenabstand 99 bis 119 px).
- Fester Look: warmer Papiergrund (#F1EBE5 bis #FEFBF6) mit feinem Quadrat-
  raster und Koernung, warme Terrakotta-Rampe je Ebene, Grotesk-Schrift
  (Inter-artig), Titelmuster "fettes Schlagwort + normales Gattungswort"
  ("Signal layer", "Lookalike layer"), Untertitel 3 bis 5 Woerter,
  Autor-Pill oben oder unten, Hochformat 4:5 oder hoeher.
- Fehler im Original, die wir nicht kopieren: alle Ebenen "LAYER 8" (04),
  Bild und Posttext nennen verschiedene Werkzeuge (04, 07, 19, 20, 22, 67, 68),
  Zahlen in der Tabelle summieren sich nicht zum Total (30).

Was die heutige Pipeline kann und nicht kann:

- 7 Archetypen in `tools/image_archetypes.py`, alle ueber kie.ai gerendert,
  alle 1:1, alle textarm (Headline max 4 bis 6 Woerter). `structured_infographic`
  ist der einzige textreiche Pfad und liefert laut Memory (SWOT-Eval 09.09.)
  die Palette am schlechtesten.
- Text-Readback (`kieai_image._verify_rendered_text`) prueft Pflichttext nach
  dem Render und bricht nach 3 Versuchen ab. Ein Cheat-Sheet mit 8 Zeilen aus
  Titel plus Untertitel plus 6 Karten mit je 4 Zeilen ueberfordert das
  (jeder Fehlbuchstabe ist ein Mismatch).
- Brandregel in `clients/jolly/config.py` `ARCHETYPE_BRAND_RULES`: keine
  Logos, weil kie.ai Marken verzerrt. Der Vision-Wipe entfernt sie aktiv.
- Logo-Overlay unten rechts existiert (`kieai_image._overlay_logo`), ebenso
  der permanente Upload (`_upload_to_github`, Branch `images`).

Schluss: Liebens Bilder sind Layoutarbeit, kein Bildmodell-Output. Der
richtige Pfad ist ein Renderer, der Inhalte exakt setzt, nicht ein Prompt,
der ein Bildmodell zum Setzen ueberredet.

## 2. Ziel

Vier neue Bild-Archetypen, die aus einem strukturierten Inhaltsplan ein
Hochformat-Bild (1080 x 1350 px, 4:5) deterministisch mit Pillow zeichnen,
mit Jolly-Farben, Montserrat, echten Tool-Logos aus einer lokalen Bibliothek
und dem bestehenden Jolly-Logo unten rechts. Kein kie.ai-Aufruf, kein
Text-Readback, kein Vision-Wipe auf diesem Pfad.

Erfolgskriterien:

1. Jeder der vier Archetypen rendert aus einem Fixture-Plan ein PNG
   1080 x 1350, byte-identisch bei zweimaligem Aufruf.
2. Jeder Text im Bild stammt woertlich aus dem Plan; der Plan ist im Notion-
   Feld "Image Prompt" gespeichert und ergibt neu gerendert dasselbe Bild.
3. Der Selektor waehlt bei Method, Comparison, Magnet mit mindestens 3 Ebenen
   und bei strukturellem Infografik-Typ einen Layout-Archetyp; die 7 kie.ai-
   Archetypen und ihre Tests bleiben unveraendert gruen.
4. Ein Tool ohne Logo-Datei faellt auf eine Text-Kachel zurueck, nie auf eine
   leere Kachel und nie auf einen Abbruch.
5. Ein Plan, der die Textgrenzen reisst, wird einmal neu angefordert, danach
   fail-closed: Status "Image Failed" mit Klartext-Fehler wie heute.

## 3. Stiluebersetzung: Lieben-Struktur, Jolly-Farben

Gemessen bei Lieben, uebersetzt auf die Jolly-Tokens aus
`ARCHETYPE_BRAND_RULES` (Weiss, Deep Navy #1E2A3A, Electric Blue #0066FF,
Bright Orange #FF6B35, Light Grey #F4F6F8 / #EEF1F5, Mid Grey #8892A4).

| Element | Lieben (gemessen) | Jolly (Spec) |
|---|---|---|
| Grund | Papier #F3EEE7, Koernung, Raster 30 bis 40 px | Weiss #FFFFFF, kein Grain, Raster 40 px in #EEF1F5, 1 px |
| Format | 1280 x 1600 (4:5), Cheat-Sheets bis 4:7 | 1080 x 1350 (4:5), fest |
| Rand | 36 bis 70 px | 64 px links und rechts, 56 px oben, 120 px unten (Logo-Zone) |
| Headline | Grotesk 58 bis 130 px, Zeile 1 leicht kursiv, Zeile 2 fett | Montserrat: Zeile 1 Regular 44 px Mid Grey, Zeile 2 ExtraBold 64 px Navy, ein Wort in Akzent erlaubt |
| Zeilentitel | "Fett + normal", 26 bis 30 px | Montserrat SemiBold 28 px Navy fuer das Schlagwort, Regular 28 px Mid Grey fuer das Gattungswort |
| Untertitel | Regular 17 bis 21 px, 3 bis 5 Woerter | Montserrat Regular 18 px Mid Grey, max 5 Woerter |
| Farbrampe je Ebene | Terrakotta 8 Stufen | Navy-Rampe: Navy mit 100, 85, 70, 55, 40, 30, 20, 12 Prozent Deckung auf Weiss; Akzent nur fuer die eine hervorgehobene Ebene, Spalte oder den Endknoten |
| Karten | Fuellung #FFFEFD, Rand 1 bis 1.5 px warm, Radius 12 bis 28 | Fuellung Weiss, Rand 1.5 px #EEF1F5, Radius 20; Kopfband Navy-Tint mit weisser Nummer |
| Logo-Kachel | 56 px, Radius 12, weiss, Schatten | 56 px, Radius 12, weiss, Rand 1 px #EEF1F5, kein Schatten, Logo max 36 px innen |
| Nummern | Kreis oder Quadrat, weiss auf Sektionsfarbe | Kreis 32 px Navy, Ziffer weiss SemiBold 16 px, zweistellig "01" |
| Verbinder | 6 Punkte, gestrichelte Linien | 6 Punkte 4 px in Mid Grey, Abstand 6 px; Flowchart gestrichelt 2 px Mid Grey |
| Autor | Pill mit Foto, "Michel Lieben, coldiq.com" | entfaellt; Jolly-Logo unten rechts ueber `_overlay_logo` wie heute |
| Tool-Namen | nur Logos, unbeschriftet | Logo-Kachel plus Name Regular 14 px darunter, damit auch Nicht-Insider lesen koennen |

Schrift: Montserrat (OFL) als TTF unter `Resources/fonts/` (Regular,
SemiBold, ExtraBold). Montserrat ist nicht auf dem Rechner installiert und
nicht auf Railway; die Dateien werden ins Repo gelegt (rund 600 KB).

Akzentfarbe: ein Wert je Mandant (`LAYOUT_TOKENS["accent"]`), Jolly Electric
Blue. Orange bleibt den kie.ai-Archetypen; so tragen die gesetzten Bilder
eine wiedererkennbare Farbe.

## 4. Architektur

```
run_research / run_image_fill
  |
  |-- select_archetype(...)            (bestehend, um 4 Keys erweitert)
  |
  |-- if is_layout_archetype(key):
  |     plan = plan_layout(key, soundbyte, kontext, skeleton, language)   (Sonnet, 1 Call)
  |     validate_plan(key, plan)        (rein, Grenzen, Logo-Slugs)
  |     png = render_layout(key, plan)  (rein, Pillow)
  |     url = publish_render(png)       (Jolly-Logo-Overlay + GitHub-Upload, bestehend)
  |     image_prompt = json.dumps(plan) (fuer Notion "Image Prompt" und Repair-Pfad)
  |
  |-- else: bestehender kie.ai-Pfad, unveraendert
```

Neue Datei `tools/layout_render.py` mit drei oeffentlichen Funktionen:

- `plan_layout(archetype, *, soundbyte, kontext, skeleton, language) -> dict`
  Ein Sonnet-Aufruf (`claude-sonnet-4-6`, wie `plan_visual`), Prompt je
  Archetyp mit dem JSON-Schema aus Abschnitt 6 und den Textgrenzen aus
  Abschnitt 5. Bei Verstoss gegen `validate_plan` genau ein zweiter Aufruf
  mit der Fehlerliste im Prompt. Danach `LayoutPlanError` mit Klartext.
- `validate_plan(archetype, plan) -> list[str]` rein, gibt Fehlerzeilen
  zurueck (leer bedeutet gueltig). Prueft Anzahlgrenzen, Wort- und
  Zeichengrenzen, Pflichtfelder, Logo-Slug-Format.
- `render_layout(archetype, plan) -> bytes` rein, kein Netz, kein Zufall.
  Zeichnet auf 1080 x 1350, gibt PNG-Bytes zurueck.

`publish_render(png_bytes) -> str` liegt in `tools/kieai_image.py` als
oeffentliche Huelle um `_overlay_logo` und `_upload_to_github` (mit dem
bestehenden catbox-Fallback). Dateiname `layout_<sha1[:8]>.png` aus dem
PNG-Inhalt, damit derselbe Plan denselben Namen ergibt.

Logo-Bibliothek: `Resources/logos/<slug>.png`, Slug ist klein, nur a bis z,
0 bis 9 und Bindestrich (`hubspot`, `smartlead`, `million-verifier`).
`Resources/logos/README.md` listet Slug, Anzeigename und Quelle. Fehlt die
Datei, zeichnet die Kachel den Anzeigenamen (SemiBold 14 px Navy, bei mehr
als 10 Zeichen die ersten beiden Woerter als Initialen).

Startbestand (Jolly-Stack, alle aus der globalen CLAUDE.md): HubSpot,
Smartlead, Dropleads, Prospeo, Explorium, AI-Ark, Million Verifier,
BounceBan, NeverBounce, Clay, Make, Notion, Fathom, HeyReach, Lemlist,
Apify, Claude, LinkedIn. Beschaffung ist Handarbeit (offizielle
Presse-Kits), nicht Teil des Codes.

## 5. Die vier Layouts

Alle: Canvas 1080 x 1350, Grund Weiss mit Raster, Kopf mit zweizeiliger
Headline (Zeile 1 max 4 Woerter Regular, Zeile 2 max 3 Woerter ExtraBold),
untere 120 px frei fuer das Logo-Overlay, rechts unten nichts.

### 5.1 `layer_stack` (Vorbild 04, 19, 56)

- 5 bis 8 Ebenen. Links isometrischer Stapel aus Quadern (Pillow-Polygone,
  Deckflaeche Raute 300 x 150 px, Dicke 30 px, Versatz 95 px je Ebene),
  Farbe aus der Navy-Rampe von hell (oben) nach dunkel (unten). Auf der
  rechten Vorderflaeche die Nummer "EBENE n" beziehungsweise "LAYER n"
  je Sprache, von oben nach unten absteigend.
- Rechts je Ebene: 6-Punkte-Verbinder, Titel "Schlagwort + Gattungswort"
  (max 3 Woerter, max 22 Zeichen), Untertitel (max 5 Woerter, max 34
  Zeichen), 0 bis 4 Logo-Kacheln.
- Genau eine Ebene darf `highlight: true` tragen; sie bekommt die
  Akzentfarbe statt der Rampe.

### 5.2 `bento_cheatsheet` (Vorbild 05, 29, 65, 68)

- 6 bis 9 Karten, nummeriert "01" bis "09". Raster nach Anzahl, fest
  hinterlegt: 6 = 2 + 3 + 1 (breit), 7 = 1 + 3 + 3, 8 = 2 + 3 + 3,
  9 = 3 + 3 + 3. Spaltenraster 3 Spalten, Rinne 16 px.
- Karte: Kopfband Navy-Tint 44 px mit Nummernkreis und Titel (max 4 Woerter,
  max 28 Zeichen), Koerper mit 2 bis 5 Zeilen (je max 48 Zeichen, mit
  Punkt-Marker), optional eine Takeaway-Zeile am Fuss (max 60 Zeichen,
  SemiBold, Akzentfarbe als linker Balken 4 px).
- Optional je Karte bis zu 3 Logo-Kacheln in einer Reihe unter dem Koerper.
- Kartenhoehe ergibt sich aus dem Inhalt; das Layout skaliert alle Karten
  einer Reihe auf die groesste Hoehe. Passt die Summe nicht in 1350 px,
  ist das ein Validierungsfehler (Zeilenzahl senken), keine Schriftverkleinerung.

### 5.3 `comparison_table` (Vorbild 23, 57)

- 2 bis 3 Vergleichsspalten plus Faktor-Spalte, 5 bis 10 Zeilen.
- Spaltenreiter oben (Radius 20, Hoehe 72 px, Text weiss Bold 24 px), Farben
  Navy, Navy 70 Prozent, Navy 40 Prozent; die Spalte mit `favored: true`
  bekommt den Akzent. Optional je Spalte ein Logo-Slug als Kachel, die den
  Reiter oben ueberlappt.
- Zelle: Zeile 1 SemiBold 18 px (max 3 Woerter, max 20 Zeichen, "Verdikt"),
  Zeilen 2 bis 3 Regular 16 px (je max 40 Zeichen). Faktor-Spalte SemiBold
  18 px, Fuellung #F4F6F8.
- Zeilenhoehe fest 99 px bei 3 Zeilen, Tabelle zentriert; mehr als 10 Zeilen
  ist ein Validierungsfehler.

### 5.4 `flowchart` (Vorbild 21, 27, 60)

- 6 bis 12 Knoten auf einer Mittelachse, Pill-Knoten 420 x 56 px (Fuellung
  #F4F6F8, Rand 1.5 px #EEF1F5, Knopf-Kreis links 32 px weiss), Label
  Regular 20 px (max 4 Woerter, max 28 Zeichen). Verbinder gestrichelt.
- Optional 1 bis 2 Gruppenbaender (breite Kapsel 760 x 72 px Navy-Tint 20
  Prozent mit 2 bis 3 inneren Pills, je max 3 Woerter).
- Letzter Knoten invertiert: Navy-Fuellung, weisser Text, Knopf in Akzent.
- Optional ein Seitenkasten links oder rechts mit 3 Zeilen (max 24 Zeichen),
  angebunden mit gestrichelter Linie. Mehr Verzweigung wird nicht gezeichnet.

## 6. Datenmodell (Plan-JSON)

Gemeinsam:

```json
{
  "archetype": "layer_stack",
  "language": "German",
  "headline": {"line1": "8 Ebenen der", "line2": "B2B-Datenbasis", "accent_word": "Datenbasis"}
}
```

`layer_stack`:

```json
{"layers": [
  {"n": 8, "keyword": "Orchestrierung", "generic": "Ebene",
   "subtitle": "Ein Key, alle Anbieter", "tools": ["clay", "make"], "highlight": false}
]}
```

`bento_cheatsheet`:

```json
{"cards": [
  {"n": 1, "title": "Aufgaben", "lines": ["...", "..."],
   "takeaway": "optional", "tools": ["hubspot"]}
]}
```

`comparison_table`:

```json
{"columns": [{"label": "Cold Email", "logo": "smartlead", "favored": true}, {"label": "LinkedIn"}],
 "rows": [{"factor": "Reichweite", "cells": [{"verdict": "Hoch.", "lines": ["...", "..."]}, {"verdict": "Mittel.", "lines": ["..."]}]}]}
```

`flowchart`:

```json
{"nodes": [{"label": "ICP festlegen"}, {"label": "Signale sammeln"},
           {"band": ["Recherche", "Anreicherung", "Pruefung"]},
           {"label": "Kampagne", "final": true}],
 "side_box": {"side": "left", "attach_to": 2, "lines": ["TOF", "MOF", "BOF"]}}
```

Alle Zeichenketten muessen in der Sprache des Posts sein; `validate_plan`
prueft die Grenzen aus Abschnitt 5 und dass `tools`-Slugs dem Slug-Muster
folgen. Der Plan wird als JSON-Text in "Image Prompt" gespeichert, mit dem
Praefix `LAYOUT-PLAN v1` in der ersten Zeile, damit `image_repair.py` und
`run_image_fill.py` ihn vom kie.ai-Prompt unterscheiden und neu rendern
koennen, ohne Sonnet erneut zu fragen.

## 7. Selektor und Pipeline-Anschluss

`tools/image_archetypes.py`:

- `ARCHETYPES` um vier Eintraege (`layer_stack` "Ebenen-Stapel",
  `bento_cheatsheet` "Cheat-Sheet", `comparison_table` "Vergleichstabelle",
  `flowchart` "Flowchart"), jeweils `strip_marks: False`, plus
  `LAYOUT_ARCHETYPES = {...}` und `is_layout_archetype(key)`.
- `select_archetype` bekommt den Parameter `layouts_enabled: bool = False`.
  Nur wenn True, werden Layout-Keys gerankt; sonst bleibt das Verhalten
  bit-identisch (alle bestehenden Tests unveraendert). Ranking bei True,
  vor den heutigen Eintraegen, in dieser Reihenfolge (die erste zutreffende
  Regel setzt den ersten Kandidaten, weitere zutreffende folgen dahinter):
  - `infographic_type` in {Comparison table, Before/after, Horizontal
    comparison} oder `post_format == "Comparison"`: `comparison_table`
  - `infographic_type` in {Funnel/pyramid, Timeline} und `layers_count >= 5`:
    `layer_stack`
  - `infographic_type` in {Tree/branching, Flywheel/loop, Timeline} oder
    `post_format == "Method"`: `flowchart`
  - `post_format == "Magnet"` und `layers_count >= 3`, oder `layers_count >= 6`:
    `bento_cheatsheet`
  - `structured_infographic` rutscht in der Fallback-Liste hinter die vier
    Layouts.
  - Anti-Repeat unveraendert (letzte zwei Archetypen).
- `layouts_enabled` kommt aus der Mandanten-Config:
  `LAYOUT_TOKENS` vorhanden bedeutet True. Jolly bekommt die Tokens
  (Abschnitt 3), SWOT, Lisocon und Sonocrete nicht; ihr Verhalten aendert
  sich nicht.

`run_research.py` Schritt 6 und `run_image_fill.py`: Verzweigung nach
`is_layout_archetype`. Layout-Pfad liefert `image_url`, `image_prompt`
(Plan-JSON) und `gen_archetype`; Fehler setzen `image_failed` wie heute.
Format-Angabe im Log "4:5".

Notion: `scripts/add_bild_variante_property.py` bekommt die vier Optionen
als Seed; Notion legt neue Select-Optionen beim ersten Schreiben ohnehin an.

`tools/image_repair.py`: `regenerate_page_image` (Zeile 111) reicht heute
"Image Prompt" unveraendert an `generate_image`. Neue Verzweigung an dieser
einen Stelle: Praefix `LAYOUT-PLAN v1` erkannt, dann `render_layout` plus
`publish_render` statt kie.ai.

## 8. Fehlerverhalten

- Sonnet liefert kein JSON oder ein ungueltiges: ein Retry mit Fehlerliste,
  dann `LayoutPlanError`. Der Runner setzt "Image Failed" und schreibt die
  Fehlerliste in "Image Prompt" mit Praefix `[IMAGE FAILED]` wie heute.
- Logo-Datei fehlt: Text-Kachel, Log-Zeile "Logo fehlt: <slug>", kein
  Fehler. Am Ende des Laufs eine Sammelzeile mit allen fehlenden Slugs.
- Schriftdatei fehlt: harter Abbruch beim Import mit Klartext-Pfad; kein
  Rueckfall auf eine Systemschrift (das Bild saehe sonst anders aus, ohne
  dass es jemand merkt).
- Upload scheitert: wie heute GitHub, dann catbox, dann Fehler. Kein
  Rueckfall auf eine lokale Datei, weil Notion eine URL braucht.

## 9. Tests (`tests/test_layout_render.py`, `tests/test_image_archetypes.py`)

Ohne Netz, ohne API:

1. Je Archetyp ein Fixture-Plan aus Abschnitt 6 (Form wie die Live-Antwort,
   nicht erfunden knapper): `render_layout` liefert PNG 1080 x 1350,
   zweimal aufgerufen byte-identisch.
2. `validate_plan`: je Grenze ein Verstoss (zu viele Ebenen, Titel zu lang,
   Slug mit Grossbuchstaben, zwei Highlights) liefert genau eine Fehlerzeile
   mit dem Feldpfad.
3. Logo-Fallback: Slug ohne Datei rendert ohne Ausnahme; das Bild
   unterscheidet sich vom Render mit Datei (Hash ungleich).
4. Selektor: `layouts_enabled=False` ist bit-identisch zum heutigen Verhalten
   (bestehende Tests laufen unveraendert); bei True greifen die Regeln aus
   Abschnitt 7, Anti-Repeat weicht auf den naechsten Layout-Key aus.
5. Plan-Praefix: `LAYOUT-PLAN v1` wird erkannt, kie.ai-Prompts nicht.
6. Untere 120 px und die rechte untere Ecke sind nach dem Render reines
   Weiss beziehungsweise Rasterfarbe (Pixelprobe), damit das Logo frei liegt.

Sichtpruefung vor dem Merge: je Archetyp ein Bild mit echten Jolly-Inhalten
(zum Beispiel die Validierungs-Waterfall aus der CLAUDE.md als
`layer_stack`), von Richard freigegeben. Kein Test ersetzt diesen Blick.

## 10. Style-Guide-Dokument

`docs/image-style-cheatsheets.md`, Deutsch, fuer Richard und fuer die
Plan-Prompts als Quelle:

- Die gemessenen Lieben-Regeln aus Abschnitt 1 mit Verweis auf die JSON-
  Dateien je Regel (Dateinummer).
- Die Jolly-Uebersetzung aus Abschnitt 3 als Tabelle.
- Je Layout: wann es passt, Inhaltsregeln fuer den Autor (Zeilen, Woerter,
  Zeichen), ein ausgefuelltes Beispiel-JSON.
- Die Fehler des Originals, die wir nicht uebernehmen.

## 11. Nicht im Scope

- Playwright- oder HTML-Renderer (Railway-Container hat keinen Browser).
- Aenderungen an den 7 kie.ai-Archetypen, ihren Prompts oder Brandregeln.
- Layouts fuer SWOT, Lisocon, Sonocrete (nur Tokens anlegen, wenn ein
  Kunde es will; Blueprint SWOT liegt unter `Clients/SWOT/Branding/`).
- Tool-Landkarten (06, 15, 22) und Produkt-Mockups (45, 49, 52): brauchen
  Screenshots oder 3D-Icons, kein Renderer-Fall.
- Autor-Pill mit Foto. Das Jolly-Logo bleibt die einzige Markierung.
- Automatisches Beschaffen von Logos.

## 12. Risiken und offene Punkte

- Pillow setzt Text ohne Kerning und ohne Silbentrennung. Die Zeichengrenzen
  aus Abschnitt 5 sind auf Montserrat bei den genannten Groessen bemessen
  und werden bei der Umsetzung gegen echte deutsche Woerter geprueft
  ("Anreicherungs-Waterfall" hat 24 Zeichen). Grenzen sind Validierung,
  keine Schriftverkleinerung.
- Fremde Logos in eigenen Posts: branchenueblich (Lieben, jede Tool-Stack-
  Grafik), aber Markenrecht liegt beim Anbieter. Nur offizielle Presse-Kits,
  keine nachgezeichneten Marken. Bei Widerspruch eines Anbieters Datei
  loeschen; die Kachel faellt automatisch auf Text.
- Ein Bild je Post kostet einen Sonnet-Call (rund 0,01 USD) statt 0,10 bis
  0,15 USD kie.ai plus zwei Vision-Calls.
- Bild-Variante-Statistik (`ENGAGEMENT_DIMENSIONS`) trennt die vier Layouts
  automatisch; ob sie mehr Kommentare und Saves bringen als die kie.ai-
  Archetypen, zeigt sich erst nach 4 bis 6 Wochen Rotation.
- Offen: ob `run_slate.py` (SWOT-Slate) den Layout-Pfad je braucht. Nicht
  Teil dieser Spec.
