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

### Schritt 3: Infografik-Prompt generieren

**Ziel:** Das Bild soll die Hauptaussage des Posts durch visuelles Storytelling sofort vermitteln — ohne den Post lesen zu müssen. Sprache im Bild = Sprache des Posts (DE → DE, EN → EN).

**Wichtig:** `{core_message_one_sentence}` wird aus dem **neu generierten LinkedIn-Post** (Schritt 2) abgeleitet — nicht aus dem Original-Post des Influencers. Das Bild soll zur eigenen Aussage passen, nicht zur Vorlage.

Extrahiere dazu aus dem generierten Post:

- Die eine zentrale Kernaussage als **Sound Byte** — ein einziger, kurzer, prägnanter Satz, der gut klingt und sofort hängen bleibt. Kein vollständiges Summary des Posts, keine genaue Erklärung — eher ein Satz, der Neugier weckt oder eine starke Reaktion auslöst. Der Post-Inhalt soll erkennbar sein, aber der Satz selbst soll als eigenständige Aussage funktionieren.
- Optional: Für wen ist die Aussage relevant (Zielgruppe/Kontext)

**Prompt-Template:**
```
Create a premium LinkedIn square image (1:1) for Jolly Marketer that communicates the core idea of the post through one clear, strategically strong visual concept.

Core message:
{core_message_one_sentence}

Optional context:
{short_context_or_target_audience_if_relevant}

Language for all visible text in the image:
{language_of_post}

Objective:
Create a scroll-stopping LinkedIn featured image that is understood within 1 to 2 seconds on mobile.
The image should communicate one core idea fast and clearly, not explain an entire framework.

Brand direction:
Use the Jolly Marketer brand system flexibly.
The visual identity should feel confident, clean, structured, modern, and premium.
Use Jolly brand colors and Montserrat-style typography, but do not force one fixed layout, one fixed background color, or one recurring visual trick every time.

Jolly Marketer brand rules:

Background: Always white (#FFFFFF). No dark backgrounds, no colored backgrounds, no gradients.
Headlines: Deep Navy (#1E2A3A), ultra-bold, integrated into the composition
Accent colors: Electric Blue (#0066FF) or Bright Orange (#FF6B35) — use sparingly as accent only
Supporting neutrals: Light Grey #F4F6F8 or #EEF1F5, Mid Grey #8892A4
Do not use more than 3 colors prominently in the same composition
Keep the overall look bright, clean, and brand-consistent

Creative discipline:

Reduce the message to one dominant visual idea
Use one primary visual logic only
Prefer one focal scene, one focal metaphor, or one strong visual mechanism
Design for feed impact first, explanation second
If the concept becomes busy, simplify aggressively
Prioritize compression over completeness
The image should feel like a premium editorial social visual, not a workshop slide or business explainer

Concept selection:
First interpret the message, then choose the strongest visual direction for this specific post.
Possible directions include:

editorial poster
symbolic metaphor
clean comparison
minimal typographic concept
conceptual business illustration
Choose only one primary direction and execute it clearly.
Do not combine multiple competing concepts.

Simplicity and clarity rules:

Maximum 2 to 4 major visual elements in the whole composition
One dominant focal point, or one focal point per side only if a comparison is absolutely necessary
Remove anything that does not strengthen the idea immediately
No clutter
No filler objects
No busy scenes
No over-detailed environments
The concept must still read clearly as a small LinkedIn thumbnail

Text discipline:

Use one strong headline only
Headline must be integrated into the composition
Headline: ultra-bold, maximum 4 to 6 words
Optional support line only if truly necessary, maximum 4 to 8 words
Avoid labels, captions, side notes, repeated text, and explanatory copy by default
Every word in the image must earn its place

Typography:

Use Montserrat-style bold sans serif typography
Typography should feel compact, modern, premium, and highly legible
Avoid weak generic fonts, serif fonts, or presentation-style text layouts

Composition:

Build the image around one clear focal point
Create strong hierarchy and reading flow
Use whitespace intentionally, but do not let the image feel empty or unfinished
The composition should feel designed, not templated

Avoid:

generic stock-business visuals
bland SaaS social graphics
infographic clutter
workshop-slide aesthetics
multiple explanatory sections
too many icons or symbols
literal over-explanation
decorative clutter
chaotic comparison layouts

Final check:

Is the core idea instantly clear?
Is there only one dominant visual concept?
Is the image understandable within 1 to 2 seconds?
Is the text minimal and strong?
Is it still clear at mobile thumbnail size?
Does it feel premium and brand-consistent?

Output:
A premium LinkedIn featured image that expresses one clear strategic idea fast, cleanly, and memorably.
```

### Schritt 4: Bild generieren
```python
from tools.kieai_image import generate_image
image_url = generate_image(image_prompt)
```
→ Modell: **Nano-Banano II** (`nano-banana-2`) via kie.ai API
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
