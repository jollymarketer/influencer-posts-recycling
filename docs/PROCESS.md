# Influencer Posts Recycling — Prozessübersicht

> **Ziel:** Täglich die besten LinkedIn-Posts von 20 GTM/RevOps-Influencern sammeln, den besten auswählen und daraus einen eigenen Thought-Leadership-Post mit Infografik recyceln.

---

## Überblick: 2 Phasen

```
Phase 1 (Automatisch, täglich)        Phase 2 (Manuell, nach Auswahl)
─────────────────────────────         ──────────────────────────────────
Influencer-Posts scrapen          →   Post auswählen
Duplikate herausfiltern           →   LinkedIn-Post generieren
In Notion speichern               →   Infografik erstellen
                                  →   Notion-Eintrag fertigstellen
```

---

## Phase 1 — Research (Täglich 07:00 UTC, automatisch)

| Schritt | Was passiert | Tool |
|---------|-------------|------|
| 1 | Bestehende Post-URLs aus Notion laden (Duplikat-Filter) | Notion API |
| 2 | Für alle 20 Influencer: Posts der letzten 7 Tage scrapen | Apify Actor |
| 3 | Nur neue Posts behalten (nicht in Notion vorhanden) | Python-Script |
| 4 | Jeden neuen Post als Notion-Eintrag speichern | Notion API |

**Status nach Phase 1:** `Make your Choice`

**Kosten:** ~$0.40 pro Tag (Apify, ~200 Posts/Run)

---

## Phase 2 — Content Generation (Manuell, nach Auswahl)

| Schritt | Was passiert | Tool |
|---------|-------------|------|
| 1 | Post aus Notion öffnen, Notion-URL an Claude geben | Notion |
| 2 | Original-Post-Text aus Notion lesen | Notion API |
| 3 | Eigenen LinkedIn Thought-Leadership-Post generieren | Claude |
| 4 | Infografik-Prompt erstellen | Claude |
| 5 | Infografik generieren (1:1, LinkedIn-Format) | kie.ai API |
| 6 | Notion-Eintrag aktualisieren (Draft + Bild + Status) | Notion API |

**Status nach Phase 2:** `Ready to Review`

---

## Status-Flow

```
Make your Choice  →  Ready to Review  →  (Manuell) Veröffentlicht
      ↑
  täglich neue
  Posts landen hier
```

---

## Was in jeden Notion-Eintrag gespeichert wird

**Nach Phase 1:**
- Influencer-Name
- Original Post-Text (Excerpt)
- Original Post-URL
- Status: `Make your Choice`

**Nach Phase 2 (ergänzt):**
- `LinkedIn Draft` — fertiger Post-Text (150–280 Wörter)
- `Image Prompt` — genutzter Bildgenerierungs-Prompt
- `Image URL` — Link zur generierten Infografik (24h gültig!)
- Status: `Ready to Review`

---

## LinkedIn-Post Qualitätskriterien

- [ ] Hook fesselt in der ersten Zeile
- [ ] Eigene Perspektive erkennbar (kein Copy-Paste)
- [ ] Konkretes Beispiel oder Erfahrung eingebunden
- [ ] Actionable oder thought-provoking
- [ ] 150–280 Wörter
- [ ] Max. 3 Hashtags

---

## Nächste Schritte nach `Ready to Review`

1. LinkedIn Draft in Notion reviewen und ggf. anpassen
2. Bild über `Image URL` herunterladen (**URL verfällt nach 24h!**)
3. Post auf LinkedIn veröffentlichen (manuell oder via Buffer)

---

## Technische Infrastruktur

| Komponente | Details |
|------------|---------|
| Scheduler | Railway Cron (`0 7 * * *`) |
| Scraping | Apify Actor `harvestapi/linkedin-profile-posts` |
| Bildgenerierung | kie.ai API (Nano-Banano II, 1:1 Format) |
| Datenspeicher | Notion DB `778bd719...` |
| Bildhosting | catbox.moe (permanenter Link) |
| Influencer-Liste | `influencers.csv` (20 Profile) |
