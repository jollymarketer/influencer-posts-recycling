-- 2026-08-19: Mandanten-Spalte fuer blog_content_mining (Richard: "sauber
-- umbauen"). Bis heute war das Schema implizit jolly-only. Ein SWOT-Lauf
-- haette seine Beitraege in Jollys Freitag-Mining gespuelt und umgekehrt.
--
-- Apply: ueber SUPABASE_DB_URL (Root-.env), siehe Commit-Message.

-- 1. influencer_posts: client-Spalte, Bestand ist vollstaendig jolly.
ALTER TABLE blog_content_mining.influencer_posts
  ADD COLUMN IF NOT EXISTS client TEXT NOT NULL DEFAULT 'jolly';

COMMENT ON COLUMN blog_content_mining.influencer_posts.client IS
  'Mandant (clients/<name>/config.py). Jeder Lese- und Schreibpfad filtert hierauf; Bestand vor 2026-08-19 ist jolly.';

-- 2. Primaerschluessel auf (client, post_url). Mit post_url allein wuerde der
--    Upsert (merge-duplicates) eines zweiten Mandanten die Zeile des ersten
--    kapern, statt eine eigene anzulegen.
ALTER TABLE blog_content_mining.influencer_posts
  DROP CONSTRAINT influencer_posts_pkey;
ALTER TABLE blog_content_mining.influencer_posts
  ADD CONSTRAINT influencer_posts_pkey PRIMARY KEY (client, post_url);

-- 3. Lesepfad ist immer client + post_date (get_posts_since).
CREATE INDEX IF NOT EXISTS influencer_posts_client_date_idx
  ON blog_content_mining.influencer_posts (client, post_date);

-- 4. topic_decisions: client-Spalte fuer den Taste-Korpus-Filter. Der
--    Primaerschluessel notion_page_id bleibt: Notion-Page-IDs sind global
--    eindeutig und die Themen-DBs sind je Mandant getrennt.
ALTER TABLE blog_content_mining.topic_decisions
  ADD COLUMN IF NOT EXISTS client TEXT NOT NULL DEFAULT 'jolly';

COMMENT ON COLUMN blog_content_mining.topic_decisions.client IS
  'Mandant. get_taste_corpus filtert hierauf: Richards Jolly-Picks kalibrieren nie einen anderen Mandanten.';

CREATE INDEX IF NOT EXISTS topic_decisions_client_decision_idx
  ON blog_content_mining.topic_decisions (client, decision);
