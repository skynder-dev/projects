create schema reveng;
create table reveng.catalog_business_models(model_key text primary key);
create table reveng.catalog_discovery_runs(
 id uuid primary key default gen_random_uuid(), run_key text not null unique, objective text not null, family_scope jsonb not null, source_plan jsonb not null,
 status text not null default 'planned' check (status = any (array['planned','running','completed','cancelled','failed'])),
 candidate_count int not null default 0, normalized_count int not null default 0, rejected_count int not null default 0,
 started_at timestamptz, completed_at timestamptz, created_at timestamptz not null default now(), metadata jsonb not null default '{}'::jsonb);
create table reveng.catalog_candidate_inbox(
 id uuid primary key default gen_random_uuid(), fingerprint text not null unique, candidate_key text not null unique,
 analysis_level text not null check (analysis_level = any (array['market','niche','business_opportunity','offer'])),
 raw_name text not null, normalized_name text not null, buyer_segment text, core_job text, primary_outcome text,
 suggested_model_key text references reveng.catalog_business_models(model_key) on delete set null, suggested_market_key text,
 status text not null default 'new' check (status = any (array['new','normalized','research_queue','rejected','promoted'])),
 source_count int not null default 1 check (source_count >= 1), evidence_hints jsonb not null default '[]'::jsonb, rejection_reason text,
 metadata jsonb not null default '{}'::jsonb, first_seen_at timestamptz not null default now(), last_seen_at timestamptz not null default now());
create table reveng.catalog_discovery_run_candidates(
 run_id uuid not null references reveng.catalog_discovery_runs(id) on delete cascade,
 candidate_id uuid not null references reveng.catalog_candidate_inbox(id) on delete cascade,
 created_at timestamptz not null default now(), primary key (run_id, candidate_id));
