-- ═══════════════════════════════════════════════════════════
-- Quant Edge — Supabase Database Schema
-- Run this SQL in your Supabase SQL Editor to create all tables
-- ═══════════════════════════════════════════════════════════

-- ─── Day Session Analysis ────────────────────────────────
-- Stores London and NY session analyses for intra-day memory
CREATE TABLE IF NOT EXISTS day_session_analysis (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    pair TEXT NOT NULL,
    session TEXT NOT NULL,
    analysis_date DATE NOT NULL,
    metrics JSONB NOT NULL,
    composite_score FLOAT NOT NULL,
    dxy_value FLOAT,
    dxy_trend TEXT,
    macro_bias TEXT,
    ai_analysis TEXT NOT NULL,
    ai_verdict TEXT NOT NULL,
    ai_conditions TEXT DEFAULT '',
    price_at_analysis FLOAT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(pair, session, analysis_date)
);

-- ─── Day Review ──────────────────────────────────────────
-- End-of-day self-review results
CREATE TABLE IF NOT EXISTS day_review (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    review_date DATE NOT NULL,
    pair TEXT NOT NULL,
    london_prediction TEXT,
    london_actual_move FLOAT,
    london_was_correct BOOLEAN,
    ny_prediction TEXT,
    ny_actual_move FLOAT,
    ny_was_correct BOOLEAN,
    ai_self_review TEXT NOT NULL,
    ai_suggested_adjustments TEXT,
    overall_accuracy_pct FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(pair, review_date)
);

-- ─── Swing Daily Analysis ────────────────────────────────
-- Accumulates daily swing analysis throughout the week
CREATE TABLE IF NOT EXISTS swing_daily_analysis (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    pair TEXT NOT NULL,
    analysis_date DATE NOT NULL,
    week_number INT NOT NULL,
    year INT NOT NULL,
    day_of_week INT NOT NULL,
    daily_metrics JSONB NOT NULL,
    four_hour_metrics JSONB NOT NULL,
    weekly_context JSONB,
    composite_score FLOAT NOT NULL,
    dxy_value FLOAT,
    dxy_weekly_trend TEXT,
    macro_regime TEXT,
    ai_analysis TEXT NOT NULL,
    ai_verdict TEXT NOT NULL,
    price_at_analysis FLOAT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(pair, analysis_date)
);

-- ─── Swing Weekly Report ─────────────────────────────────
-- Friday weekly final reports (persisted, not auto-deleted)
CREATE TABLE IF NOT EXISTS swing_weekly_report (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    pair TEXT NOT NULL,
    week_number INT NOT NULL,
    year INT NOT NULL,
    week_open_price FLOAT,
    week_close_price FLOAT,
    week_high FLOAT,
    week_low FLOAT,
    total_move_pct FLOAT,
    ai_weekly_summary TEXT NOT NULL,
    predictions_correct INT,
    predictions_total INT,
    accuracy_pct FLOAT,
    ai_lessons TEXT,
    ai_next_week_outlook TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(pair, week_number, year)
);

-- ─── Indexes for Performance ─────────────────────────────
CREATE INDEX IF NOT EXISTS idx_day_session_pair_date 
    ON day_session_analysis(pair, analysis_date);
CREATE INDEX IF NOT EXISTS idx_day_session_session_date 
    ON day_session_analysis(session, analysis_date);
CREATE INDEX IF NOT EXISTS idx_day_review_pair_date 
    ON day_review(pair, review_date);
CREATE INDEX IF NOT EXISTS idx_swing_daily_pair_week 
    ON swing_daily_analysis(pair, week_number, year);
CREATE INDEX IF NOT EXISTS idx_swing_weekly_pair_week 
    ON swing_weekly_report(pair, week_number, year);

-- ─── RLS Policies ────────────────────────────────────────
-- Enable RLS on all tables
ALTER TABLE day_session_analysis ENABLE ROW LEVEL SECURITY;
ALTER TABLE day_review ENABLE ROW LEVEL SECURITY;
ALTER TABLE swing_daily_analysis ENABLE ROW LEVEL SECURITY;
ALTER TABLE swing_weekly_report ENABLE ROW LEVEL SECURITY;

-- Allow service role full access (our bot uses service role key)
CREATE POLICY "Service role full access on day_session_analysis"
    ON day_session_analysis FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role full access on day_review"
    ON day_review FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role full access on swing_daily_analysis"
    ON swing_daily_analysis FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role full access on swing_weekly_report"
    ON swing_weekly_report FOR ALL
    USING (true)
    WITH CHECK (true);
