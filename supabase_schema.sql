-- Supabase / PostgreSQL Schema for Misinformation Heatmap

-- Enable the UUID extension if needed (optional)
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS public.events (
    event_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    title TEXT,
    content TEXT,
    summary TEXT,
    url TEXT,
    state TEXT,
    category TEXT,
    fake_news_verdict TEXT,
    fake_news_confidence REAL,
    fake_news_score REAL,
    
    -- JSONB allows for faster querying and indexing of JSON objects in Postgres
    ml_classification_result JSONB,
    linguistic_analysis_result JSONB,
    source_credibility_result JSONB,
    fact_check_result JSONB,
    satellite_verification_result JSONB,
    cross_reference_score REAL,
    indian_context_result JSONB,
    indic_bert_embeddings JSONB,
    
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Recommended Indexes for performance
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON public.events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_events_state ON public.events(state);
CREATE INDEX IF NOT EXISTS idx_events_verdict ON public.events(fake_news_verdict);
