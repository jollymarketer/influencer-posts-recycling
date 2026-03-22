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

**Prompt-Template:**
```
Erstelle einen detaillierten Bildgenerierungs-Prompt für eine LinkedIn-Infografik zum Thema "{topic}".

Anforderungen:
- Stil: Professionelle B2B-Infografik, modern, clean
- Farben: Dunkelblau (#1a2e4a), Weiß, Akzent in Hellblau oder Orange
- Inhalt: {key_stat_or_insight} visualisiert (Funnel/Chart/Framework)
- Kein Text im Bild (wird separat als Post-Text verwendet)
- Aspect Ratio: 1:1 (LinkedIn Post)
- Resolution: 1K
```

### Schritt 4: Bild generieren
```python
from tools.kieai_image import generate_image
image_url = generate_image(image_prompt)
```
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
