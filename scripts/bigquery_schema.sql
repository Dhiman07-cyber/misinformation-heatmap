-- BigQuery Schema for Misinformation Heatmap Application
-- Creates datasets, tables, and views for storing and analyzing misinformation data

-- Create main dataset for application data
CREATE SCHEMA IF NOT EXISTS `misinformation_heatmap`
OPTIONS (
  description = "Main dataset for misinformation heatmap application data",
  location = "US"
);

-- Create dataset for raw ingestion data
CREATE SCHEMA IF NOT EXISTS `misinformation_raw`
OPTIONS (
  description = "Raw ingestion data before processing",
  location = "US"
);

-- Create dataset for analytics and reporting
CREATE SCHEMA IF NOT EXISTS `misinformation_analytics`
OPTIONS (
  description = "Analytics and reporting views",
  location = "US"
);

-- Events table - main storage for processed events
CREATE OR REPLACE TABLE `misinformation_heatmap.events` (
  event_id STRING NOT NULL,
  source STRING NOT NULL,
  original_text STRING NOT NULL,
  processed_text STRING,
  timestamp TIMESTAMP NOT NULL,
  ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  lang STRING,
  region_hint STRING,
  lat FLOAT64,
  lon FLOAT64,
  
  -- NLP Analysis Results
  entities ARRAY<STRING>,
  sentiment_score FLOAT64,
  confidence_score FLOAT64,
  
  -- Misinformation Scoring
  virality_score FLOAT64,
  reality_score FLOAT64,
  misinformation_risk FLOAT64,
  
  -- Satellite Validation
  satellite_similarity FLOAT64,
  satellite_anomaly BOOL,
  satellite_confidence FLOAT64,
  satellite_baseline_date DATE,
  
  -- Claims and Categories
  claims ARRAY<STRUCT<
    claim_text STRING,
    claim_type STRING,
    confidence FLOAT64,
    entities ARRAY<STRING>
  >>,
  
  categories ARRAY<STRING>,
  dominant_category STRING,
  
  -- Processing Metadata
  processing_version STRING,
  processing_duration_ms INT64,
  processing_errors ARRAY<STRING>,
  
  -- Validation and Quality
  validation_status STRING,
  quality_score FLOAT64,
  human_reviewed BOOL DEFAULT FALSE,
  human_review_timestamp TIMESTAMP,
  human_reviewer_id STRING,
  
  -- Audit fields
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY DATE(timestamp)
CLUSTER BY region_hint, dominant_category, source
OPTIONS (
  description = "Main events table storing processed misinformation events",
  partition_expiration_days = 1095,  -- 3 years
  require_partition_filter = TRUE
);

-- Raw events table for ingestion pipeline
CREATE OR REPLACE TABLE `misinformation_raw.raw_events` (
  raw_event_id STRING NOT NULL,
  source STRING NOT NULL,
  raw_content STRING NOT NULL,
  content_type STRING,
  source_url STRING,
  source_metadata JSON,
  ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  processing_status STRING DEFAULT 'pending',
  processing_attempts INT64 DEFAULT 0,
  last_processing_attempt TIMESTAMP,
  processing_errors ARRAY<STRING>,
  processed_event_id STRING,  -- Reference to processed event
  
  -- Source-specific fields
  social_media_metadata STRUCT<
    platform STRING,
    user_id STRING,
    post_id STRING,
    engagement_metrics JSON,
    hashtags ARRAY<STRING>,
    mentions ARRAY<STRING>
  >,
  
  news_metadata STRUCT<
    publication STRING,
    author STRING,
    headline STRING,
    publication_date TIMESTAMP,
    article_url STRING,
    category STRING
  >,
  
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY DATE(ingestion_timestamp)
CLUSTER BY source, processing_status
OPTIONS (
  description = "Raw events before NLP processing",
  partition_expiration_days = 365  -- 1 year
);

-- State aggregations table for heatmap data
CREATE OR REPLACE TABLE `misinformation_heatmap.state_aggregations` (
  state_name STRING NOT NULL,
  date DATE NOT NULL,
  hour INT64 NOT NULL,  -- 0-23 for hourly aggregations
  
  -- Event counts
  total_events INT64 DEFAULT 0,
  high_risk_events INT64 DEFAULT 0,
  satellite_validated_events INT64 DEFAULT 0,
  
  -- Score aggregations
  avg_virality_score FLOAT64,
  avg_reality_score FLOAT64,
  avg_misinformation_risk FLOAT64,
  max_misinformation_risk FLOAT64,
  
  -- Category breakdown
  category_counts ARRAY<STRUCT<
    category STRING,
    count INT64,
    avg_risk FLOAT64
  >>,
  
  -- Source breakdown
  source_counts ARRAY<STRUCT<
    source STRING,
    count INT64,
    avg_risk FLOAT64
  >>,
  
  -- Top claims (for state detail views)
  top_claims ARRAY<STRUCT<
    claim_text STRING,
    event_count INT64,
    avg_risk FLOAT64,
    latest_timestamp TIMESTAMP
  >>,
  
  -- Metadata
  last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  calculation_version STRING
)
PARTITION BY date
CLUSTER BY state_name, hour
OPTIONS (
  description = "Hourly state-level aggregations for heatmap visualization",
  partition_expiration_days = 730  -- 2 years
);

-- Claims tracking table
CREATE OR REPLACE TABLE `misinformation_heatmap.claims` (
  claim_id STRING NOT NULL,
  claim_text STRING NOT NULL,
  claim_hash STRING NOT NULL,  -- For deduplication
  claim_type STRING,
  
  -- First occurrence
  first_seen_timestamp TIMESTAMP NOT NULL,
  first_seen_event_id STRING,
  first_seen_location STRING,
  
  -- Spread tracking
  total_occurrences INT64 DEFAULT 1,
  unique_locations ARRAY<STRING>,
  spread_velocity FLOAT64,  -- Events per hour
  geographic_spread_score FLOAT64,
  
  -- Validation results
  fact_check_status STRING,  -- verified, debunked, disputed, unverified
  fact_check_sources ARRAY<STRING>,
  fact_check_timestamp TIMESTAMP,
  
  -- Satellite validation summary
  satellite_validation_count INT64 DEFAULT 0,
  satellite_anomaly_rate FLOAT64,
  avg_satellite_confidence FLOAT64,
  
  -- Risk assessment
  overall_risk_score FLOAT64,
  trend_direction STRING,  -- increasing, decreasing, stable
  
  -- Related claims
  related_claim_ids ARRAY<STRING>,
  
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
CLUSTER BY claim_hash, first_seen_timestamp
OPTIONS (
  description = "Unique claims tracking and analysis"
);

-- System metrics table
CREATE OR REPLACE TABLE `misinformation_heatmap.system_metrics` (
  metric_timestamp TIMESTAMP NOT NULL,
  metric_name STRING NOT NULL,
  metric_value FLOAT64 NOT NULL,
  metric_unit STRING,
  
  -- Dimensions
  component STRING,  -- nlp, satellite, api, ingestion
  environment STRING,  -- production, staging, development
  region STRING,
  
  -- Additional context
  labels JSON,
  
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY DATE(metric_timestamp)
CLUSTER BY component, metric_name
OPTIONS (
  description = "System performance and health metrics",
  partition_expiration_days = 90
);

-- Create views for analytics

-- Real-time heatmap view
CREATE OR REPLACE VIEW `misinformation_analytics.realtime_heatmap` AS
SELECT 
  state_name,
  SUM(total_events) as total_events,
  AVG(avg_misinformation_risk) as avg_misinformation_risk,
  MAX(max_misinformation_risk) as max_misinformation_risk,
  SUM(high_risk_events) as high_risk_events,
  SUM(satellite_validated_events) as satellite_validated_events,
  
  -- Calculate intensity score
  CASE 
    WHEN SUM(total_events) = 0 THEN 0
    ELSE LEAST(1.0, (SUM(high_risk_events) * 1.0 / SUM(total_events)) * AVG(avg_misinformation_risk))
  END as intensity_score,
  
  -- Recent activity (last 24 hours)
  COUNTIF(date >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)) as recent_activity_days,
  
  MAX(last_updated) as last_updated
FROM `misinformation_heatmap.state_aggregations`
WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)  -- Last 7 days
GROUP BY state_name;

-- Trending claims view
CREATE OR REPLACE VIEW `misinformation_analytics.trending_claims` AS
SELECT 
  c.claim_id,
  c.claim_text,
  c.claim_type,
  c.total_occurrences,
  c.spread_velocity,
  c.geographic_spread_score,
  c.overall_risk_score,
  c.fact_check_status,
  
  -- Recent activity
  COUNT(e.event_id) as recent_events_24h,
  ARRAY_AGG(DISTINCT e.region_hint IGNORE NULLS) as recent_locations,
  
  -- Risk trend
  AVG(e.misinformation_risk) as avg_recent_risk,
  
  c.updated_at
FROM `misinformation_heatmap.claims` c
LEFT JOIN `misinformation_heatmap.events` e 
  ON ARRAY_TO_STRING(e.claims, ',') LIKE CONCAT('%', c.claim_text, '%')
  AND e.timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
WHERE c.updated_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
GROUP BY 
  c.claim_id, c.claim_text, c.claim_type, c.total_occurrences,
  c.spread_velocity, c.geographic_spread_score, c.overall_risk_score,
  c.fact_check_status, c.updated_at
ORDER BY c.spread_velocity DESC, recent_events_24h DESC
LIMIT 100;

-- System health dashboard view
CREATE OR REPLACE VIEW `misinformation_analytics.system_health` AS
SELECT 
  component,
  metric_name,
  
  -- Current values (last hour)
  AVG(CASE WHEN metric_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR) 
           THEN metric_value END) as current_value,
  
  -- 24-hour averages
  AVG(CASE WHEN metric_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR) 
           THEN metric_value END) as avg_24h,
  
  -- Trends
  (AVG(CASE WHEN metric_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR) 
            THEN metric_value END) - 
   AVG(CASE WHEN metric_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 25 HOUR) 
            AND metric_timestamp < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
            THEN metric_value END)) as trend_change,
  
  MAX(metric_timestamp) as last_updated,
  metric_unit
  
FROM `misinformation_heatmap.system_metrics`
WHERE metric_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
GROUP BY component, metric_name, metric_unit;

-- Data quality monitoring view
CREATE OR REPLACE VIEW `misinformation_analytics.data_quality` AS
SELECT 
  DATE(timestamp) as date,
  source,
  
  -- Volume metrics
  COUNT(*) as total_events,
  COUNT(CASE WHEN validation_status = 'valid' THEN 1 END) as valid_events,
  COUNT(CASE WHEN validation_status = 'invalid' THEN 1 END) as invalid_events,
  
  -- Quality metrics
  AVG(quality_score) as avg_quality_score,
  AVG(confidence_score) as avg_confidence_score,
  
  -- Processing metrics
  AVG(processing_duration_ms) as avg_processing_time_ms,
  COUNT(CASE WHEN ARRAY_LENGTH(processing_errors) > 0 THEN 1 END) as events_with_errors,
  
  -- Satellite validation coverage
  COUNT(CASE WHEN satellite_similarity IS NOT NULL THEN 1 END) as satellite_validated,
  AVG(satellite_confidence) as avg_satellite_confidence,
  
  -- Geographic coverage
  COUNT(DISTINCT region_hint) as unique_regions,
  COUNT(CASE WHEN lat IS NOT NULL AND lon IS NOT NULL THEN 1 END) as geolocated_events
  
FROM `misinformation_heatmap.events`
WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
GROUP BY DATE(timestamp), source
ORDER BY date DESC, source;

-- Create indexes for better performance
CREATE OR REPLACE TABLE FUNCTION `misinformation_heatmap.get_state_timeline`(
  state_name_param STRING,
  hours_back INT64
)
AS (
  SELECT 
    TIMESTAMP_TRUNC(timestamp, HOUR) as hour,
    COUNT(*) as event_count,
    AVG(misinformation_risk) as avg_risk,
    AVG(virality_score) as avg_virality,
    AVG(reality_score) as avg_reality,
    ARRAY_AGG(DISTINCT dominant_category IGNORE NULLS) as categories
  FROM `misinformation_heatmap.events`
  WHERE region_hint = state_name_param
    AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL hours_back HOUR)
  GROUP BY TIMESTAMP_TRUNC(timestamp, HOUR)
  ORDER BY hour DESC
);

-- Grant permissions (to be run after table creation)
-- These would typically be run separately with appropriate service account

-- GRANT `roles/bigquery.dataViewer` ON SCHEMA `misinformation_heatmap` TO "serviceAccount:your-service-account@project.iam.gserviceaccount.com";
-- GRANT `roles/bigquery.dataEditor` ON TABLE `misinformation_heatmap.events` TO "serviceAccount:your-service-account@project.iam.gserviceaccount.com";
-- GRANT `roles/bigquery.dataEditor` ON TABLE `misinformation_raw.raw_events` TO "serviceAccount:your-service-account@project.iam.gserviceaccount.com";
-- GRANT `roles/bigquery.dataEditor` ON TABLE `misinformation_heatmap.state_aggregations` TO "serviceAccount:your-service-account@project.iam.gserviceaccount.com";
-- GRANT `roles/bigquery.dataEditor` ON TABLE `misinformation_heatmap.claims` TO "serviceAccount:your-service-account@project.iam.gserviceaccount.com";
-- GRANT `roles/bigquery.dataEditor` ON TABLE `misinformation_heatmap.system_metrics` TO "serviceAccount:your-service-account@project.iam.gserviceaccount.com";