# Workflow: Content Generation (Nach User-Auswahl)

## Ziel
Den ausgewählten Influencer-Post in einen eigenen LinkedIn-Thought-Leadership-Post recyceln, eine Infografik generieren und den fertigen Content in Notion speichern.

## Trigger
User gibt Claude die Notion-URL oder Page-ID des ausgewählten Posts.

## Content-Matrix-Regeln (Spec 2026-07-08, gelten auch für den manuellen Pfad)

- Jeder Post gehört in genau EINE Matrix-Box (Job x Stage). Vor der Generierung
  Box + Format wählen: Opinion (Perspective x Awareness), POV/Signature
  (Perspective x Education), Comparison (Perspective x Selection), Story
  (Proof x Awareness), Method (Proof x Education), CaseProof (Proof x Selection),
  Debate (Promotion x Awareness), Magnet (Promotion x Education), Offer
  (Promotion x Selection). Matrix-Job/Matrix-Stage-Properties in Notion setzen.
- Asset-Formate NUR mit Eintrag aus der Mandanten-Config: CaseProof braucht
  PROOF_ASSETS, Magnet LEAD_MAGNETS, Offer OFFERS. Jede Zahl mit Einheit
  (Prozent, Euro, x-fach) wörtlich aus dem Asset: keine anderen Zahlen.
- CTA-Politik: Kein DM-/Angebots-CTA außer in Magnet (genau ein Kommentar-CTA)
  und Offer (genau ein DM- oder Discovery-CTA). Kein künstlicher Zeitdruck.
- Genau EINE Content-Persona pro Post (CONTENT_PERSONAS des Mandanten),
  Wertachsen nie mischen. Persona-Property in Notion setzen.
- Promotion-Posts (Debate/Magnet/Offer) max. 2 von 10; Selection-Spalte
  mind. 2 von 10 (Quota macht das im Cron automatisch, manuell mitzählen).

## Inputs
- Notion Page URL oder ID (z.B. `https://www.notion.so/abc123...`)
- Opcional: Spezifische Perspektive oder Winkel für den Post

## Ausführung durch Claude

### Schritt 1: Notion-Eintrag lesen
```python
from tools.notion_db import get_entry_by_page_id
entry = get_entry_by_page_id("<PAGE_ID>")
post_text = entry["properties"]["Post Excerpt"]["rich_text"][0]["plain_text"]
influencer = entry["properties"]["Influencer"]["rich_text"][0]["plain_text"]
```

### Schritt 2: LinkedIn-Post generieren

**Style-Guide für den generierten Post:**
- Format: First Person Thought Leadership
- Länge: 150–280 Wörter (LinkedIn-optimal)
- Ton: Direkt, konversationell, mit persönlicher Perspektive
- Nicht: Copy-Paste des Originals — eigene Meinung/Erfahrung einbringen
- Struktur:
  - Hook (erste Zeile = Stopper)
  - These oder Beobachtung (2-3 Sätze)
  - Konkrete Erfahrung oder Beispiel
  - Takeaway / Call-to-Reflection
  - Optional: Frage an Community
- Kein Hashtag-Spam (max. 3 relevante Hashtags)

**Beispiel-Prompt für Claude:**
```
Recycel diesen LinkedIn-Post von {influencer} in einen eigenen Thought Leadership Post.
Schreib aus First Person Perspektive. Bringe eine eigene, frische Perspektive ein.
Nutze den Inhalt als Inspiration, nicht als Vorlage.
NICHT pushen: Clay. Jolly setzt Clay nicht mehr ein. Clay nie als Held oder Lösung featuren.
Beiläufige Erwähnungen sind ok; grundsätzlich tool-agnostisch bleiben.

Original Post:
{post_text}
```

### Schritt 3: Bild-Prompt + Infografik-Skelett generieren

Der gleiche Claude-Call (Schritt 2) produziert jetzt zwei Outputs:

**3a — Bild-Prompt** (Editorial Image, automatisch an kie.ai übergeben):
Ziel: Ein LinkedIn Featured Image (3:2), das die Kernaussage bildhaft, sofort verständlich und scroll-stoppend für CEOs von Tech-Unternehmen darstellt. Sprache im Bild = Sprache des Posts (DE → DE, EN → EN).

**3b — Infografik-Skelett** (Canva-Ready, manueller Schritt):
Enthält:
- `TYP`: Vergleichstabelle / Funnel/Pyramide / Eisberg / Framework/Kreise / Horizontaler Vergleich / Timeline / 2x2-Matrix / Flywheel / Waage-Hebel / Vorher-Nachher / Baum-Verzweigung (Typ wird per Logik-Match gewaehlt + Anti-Repeat gegen die letzten 3 Runs; Eisberg nur wenn klar am besten)
- `METAPHER`: Visuelle Metapher wenn sinnvoll (z.B. Eisberg, Rubik's Cube)
- `KOMPLEMENTARITAET`: Infografik zeigt X → Post-Text erklärt Y
- `EBENEN`: Keywords pro Ebene/Spalte (max. 3-4 Keywords, keine Sätze)
- `TOOL-LOGOS`: immer "keine" — das Bild bleibt logofrei (AI-Render verzerrt Marken-Logos)

Das Skelett wird automatisch als Block "Infografik-Skelett (Canva)" in die Notion-Seite geschrieben.

**Warum Infografik-First:** Laut Pierre Rubel (Content Path) sind 95% der Post-Performance auf die Infografik zurückzuführen — nicht auf den Text. Das Skelett gibt die Canva-Vorlage direkt vor, ohne dass man erst ein Konzept entwickeln muss.

**Prompt-Template:**
```
Create an editorial 3:2 cover visual for a tech-business audience. Treat this as a magazine cover photograph or conceptual editorial still — not advertising, not marketing collateral, not branded ad creative.

LinkedIn Post (the message we are visualizing):
{linkedin_post_text}

Goal:
Translate the core message into one strong, editorial image — premium, scroll-stopping, instantly understandable on mobile, provocative enough to make a CEO of a tech company stop scrolling.

Visual style:
- Palette: Deep Navy (#1E2A3A), Bright Orange (#FF6B35) as accent, white as supporting tone
- Typography: Montserrat-style ultra-bold sans-serif. Deep Navy on light surfaces, white on dark.
- Max 6 words headline, integrated into the composition. Image language: {language_of_post}
- Premium editorial feel — magazine-cover or art-direction quality, not stock imagery, not slide layout

Visual variety — IMPORTANT:
- Do NOT default to a plain white background. Make the image visually interesting and scroll-stopping.
- Vary the visual treatment across posts: editorial photography, abstract 3D renders, isometric scenes, conceptual illustrations, tactile textures (paper, concrete, glass), cinematic lighting, dark editorial moods, bold graphic compositions, metaphorical objects, environmental scenes.
- Subtle gradients, vignettes, depth of field, and atmospheric backgrounds are encouraged when they support the message.
- The image should feel like an editorial cover, not a slide template.

Composition rule for the lower-right quadrant:
- The lower-right ~20% of the image must contain only clean, calm background — atmospheric texture, soft blur, plain surface, sky, or pure negative space. No subjects, no objects, no figures, no text, no graphic elements of any kind in this region.

The headline is the only text or graphic element in the image apart from the depicted scene itself. The image is unbranded — no commercial signatures, monograms, or imprinted marks of any kind.
```

### Schritt 4: Bild generieren
```python
from tools.kieai_image import generate_image
image_url = generate_image(image_prompt)
```
→ Modell: **gpt-image-2-text-to-image** via kie.ai API (3:2 default)
→ Polling läuft automatisch alle 10 Sekunden

### Schritt 5: Notion updaten
```python
from tools.notion_db import update_with_draft
update_with_draft(
    page_id="<PAGE_ID>",
    linkedin_draft=linkedin_post_text,
    image_prompt=image_prompt,
    image_url=image_url
)
```
→ Status wird automatisch auf `Ready to Review` gesetzt

## Output
- Notion-Eintrag aktualisiert mit:
  - `LinkedIn Draft` — fertiger Post-Text
  - `Image Prompt` — genutzter Prompt
  - `Image URL` — Link zum generierten Infografik-Bild
  - `Status` → `Ready to Review`

## Qualitätskriterien für den LinkedIn-Post
- [ ] Hook fesselt in der ersten Zeile
- [ ] Eigene Perspektive erkennbar (nicht nur Zusammenfassung)
- [ ] Konkretes Beispiel oder Erfahrung eingebunden
- [ ] Klar actionable oder thought-provoking
- [ ] 150–280 Wörter
- [ ] Max. 3 Hashtags

## Nächste Schritte nach `Ready to Review`
1. LinkedIn Draft in Notion reviewen und ggf. anpassen
2. Bild über `Image URL` herunterladen (URL verfällt nach 24h!)
3. Post auf LinkedIn veröffentlichen (manuell oder via Buffer)

## Self-Improvement Log

### 2026-06-24 — kie.ai gpt-image-2 Server-Ausfall + Nano-Banana-Fallback

- Symptom: Status `Image Failed`, Image Prompt trägt `[IMAGE FAILED] kie.ai ... {'code': 500, 'msg': 'Server exception ...'}`.
- Ursache: kie.ai liefert bei serverseitiger Modell-Stoerung HTTP 200 **mit Body-Code 500**. Nicht unser Code, nicht Prompt/Auth/Credits. Unbekannte Modelle geben sauber 422 ("not supported") zurueck — ein **500 heisst: Modell existiert, Backend ist down**. Betrifft nur `gpt-image-2-text-to-image`; `google/nano-banana` und der createTask-Endpoint liefen normal weiter.
- Code-Fix: `_kie_request_with_retry` wiederholt jetzt auch Body-Code >= 500 (nicht nur HTTP-5xx). `generate_image(..., model=...)` erlaubt einen Per-Call-Modellwechsel; Pipeline-Default bleibt `gpt-image-2-text-to-image`.
- Recovery einer einzelnen Seite ohne Re-Run der ganzen Pipeline (kein Make-Webhook-Refire):
  `python .tmp/regenerate_failed_image.py <PAGE_ID> [MODEL]` — strippt den `[IMAGE FAILED]`-Prefix, erkennt Infografik (1:1, kein Mark-Strip) vs Editorial-Poster (3:2, Mark-Strip), patcht Image + bereinigten Prompt + Status=`Ready to Review`.
- Achtung bei Infografik-Fallback: `strip_marks=False`, daher kann das Modell ein zweites (halluziniertes) Jolly-Logo unten links setzen. Deterministisch entfernbar via `_wipe_bottom_left_zone` auf dem fertigen PNG, dann neu hochladen + Image patchen.

### 2026-06-25 — Bild-Archetyp-Router (weg von der clunky Default-Infografik)

- Problem: Die Pipeline rendert in Schritt 6 fast immer die literale Infografik (`build_infographic_prompt`, 1:1). Der Editorial-Poster war nur Fallback und feuerte nie, weil das LLM immer EBENEN liefert. Resultat: zu oft eine clunky, template-y wirkende Infografik.
- Fix: neues `tools/image_archetypes.py` mit Menue aus 7 Bild-Archetypen (`editorial_cover`, `stat_hero`, `statement_card`, `two_panel_contrast`, `metaphor_object`, `isometric_scene`, `structured_infographic`) + deterministischem, concept-forward Selektor `select_archetype()` + Anti-Repeat gegen die letzten 2 Archetypen. Die Infografik ist jetzt nur EINE Option, starker Kandidat nur bei wirklich strukturellen Posts (struktureller TYP + ≥3 Ebenen).
- run_research Schritt 6 ruft jetzt `select_archetype` + `build_archetype_prompt` statt `build_infographic_prompt`. `generate_post_and_image_prompt` gibt zusaetzlich `soundbyte`/`kontext` zurueck (6-Tupel). Neue Notion-Property **Bild-Variante** (`scripts/add_bild_variante_property.py`) treibt das Anti-Repeat via `get_recent_archetypes()`.
- Alle Archetypen 1:1; `strip_marks=False` nur fuer `structured_infographic`. Guard-Tests: `tests/test_image_archetypes.py`.
- Phase 2 (offen): optionaler Vision-Quality-Gate + 1 Retry. Bewusst nicht gebaut — Review ist human-gated.

### 2026-06-24 — Infografik-Typ-Diversitaet (weg von ~80% Eisberg)

- Problem: ~80% der Bilder waren Eisberge. Drei Biases: (1) Eisberg war das einzige Metaphern-Beispiel im Prompt (Anker), (2) kein Anti-Repeat auf den TYP (nur das Post-Format hatte eins), (3) "sichtbar vs. verborgen" passt scheinbar auf jeden Post.
- Fix (Kombi 1+2+3): Prompt entgiftet (Eisberg-Anker raus, Metaphern-Beispiele neutral, "Eisberg ist ueberstrapaziert"-Regel) + Typ-Menue von 5 auf 11 erweitert (Timeline, 2x2-Matrix, Flywheel, Waage/Hebel, Vorher/Nachher, Baum) + deterministisches Anti-Repeat: `get_recent_infographic_types()` -> `recent_types_line` im Prompt ("vermeide Typ aus den letzten 3 Runs").
- Persistenz: neue Notion-Select-Property **Infografik-Typ** (Seed via `scripts/add_infographic_type_property.py`). `update_with_draft` schreibt sie non-fatal; `parse_infographic_type` + `normalize_infographic_type` (Keyword-Match auf 11 Kanons) liefern den gespeicherten Wert.
- Verifiziert: Trade-off-Post + recent=[Iceberg] -> LLM waehlt Scale/seesaw, nicht Eisberg.
