-- 2026-09-14: Watchlist fuer Kommentar-Entwuerfe je Mandant. Anlass: das
-- GitHub-Repo ist oeffentlich, Prospect-Listen (Name, Titel, Firma, LinkedIn-
-- URL) gehoeren deshalb nicht als CSV ins Repo, sondern hierher. Der Pfad
-- tools/abm_comment_drafts.py liest bei watchlist_source == "db" von hier,
-- tools/jolly_watchlist.py --push schreibt (Upsert je client + linkedin_url).
--
-- Apply: ueber SUPABASE_DB_URL (Root-.env) mit psycopg, siehe Commit-Message.

CREATE TABLE IF NOT EXISTS blog_content_mining.comment_watchlist (
  client        TEXT        NOT NULL,
  linkedin_url  TEXT        NOT NULL,
  prio          SMALLINT    NOT NULL DEFAULT 9,
  typ           TEXT        NOT NULL DEFAULT 'person',
  domain        TEXT        NOT NULL DEFAULT '',
  company       TEXT        NOT NULL DEFAULT '',
  persona       TEXT        NOT NULL DEFAULT '',
  first_name    TEXT        NOT NULL DEFAULT '',
  last_name     TEXT        NOT NULL DEFAULT '',
  title         TEXT        NOT NULL DEFAULT '',
  source        TEXT        NOT NULL DEFAULT '',
  active_at     TIMESTAMPTZ,
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (client, linkedin_url)
);

COMMENT ON TABLE blog_content_mining.comment_watchlist IS
  'Personen, unter deren Posts ein Mandant kommentiert (tools/abm_comment_drafts). Spalten wie die lisocon-CSV; source = Herkunft (hubspot_warm, sn_poster, pool_active).';

CREATE INDEX IF NOT EXISTS comment_watchlist_client_prio
  ON blog_content_mining.comment_watchlist (client, prio);
