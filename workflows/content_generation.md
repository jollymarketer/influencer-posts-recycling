# Workflow: Content Generation (Nach User-Auswahl)

## Ziel
Den ausgewählten Influencer-Post in einen eigenen LinkedIn-Thought-Leadership-Post recyceln, eine Infografik generieren und den fertigen Content in Notion speichern.

## Trigger
User gibt Claude die Notion-URL oder Page-ID des ausgewählten Posts.

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

Original Post:
{post_text}
```

### Schritt 3: Bild-Prompt generieren

**Ziel:** Ein LinkedIn Featured Image (3:2), das die Kernaussage des neu generierten Posts (Schritt 2) bildhaft, sofort verständlich und scroll-stoppend für CEOs von Tech-Unternehmen darstellt. Sprache im Bild = Sprache des Posts (DE → DE, EN → EN).

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
