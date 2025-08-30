-- Ocean Sentinel Database Migration
-- Migration: 002_add_threats_table.sql
-- Created: 2025-08-30
-- Description: Add threats table and related threat management functionality

-- Create threat-related custom types
CREATE TYPE threat_type AS ENUM ('storm', 'pollution', 'erosion', 'algal_bloom', 'illegal_dumping', 'tsunami', 'oil_spill', 'anomaly');
CREATE TYPE threat_status AS ENUM ('active', 'monitoring', 'investigating', 'resolved', 'false_positive');
CREATE TYPE threat_severity AS ENUM ('low', 'medium', 'high', 'severe', 'extreme');

-- Create threats table
CREATE TABLE threats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    type threat_type NOT NULL,
    severity INTEGER CHECK (severity >= 1 AND severity <= 5) NOT NULL,
    severity_label threat_severity GENERATED ALWAYS AS (
        CASE 
            WHEN severity = 1 THEN 'low'::threat_severity
            WHEN severity = 2 THEN 'medium'::threat_severity
            WHEN severity = 3 THEN 'high'::threat_severity
            WHEN severity = 4 THEN 'severe'::threat_severity
            WHEN severity = 5 THEN 'extreme'::threat_severity
        END
    ) STORED,
    status threat_status DEFAULT 'active',
    location GEOGRAPHY(POINT, 4326) NOT NULL,
    address TEXT,
    description TEXT NOT NULL,
    confidence DECIMAL(5,4) CHECK (confidence >= 0 AND confidence <= 1),
    estimated_impact TEXT,
    affected_population INTEGER DEFAULT 0,
    affected_area_km2 DECIMAL(10,2),
    
    -- Detection and verification
    detected_by VARCHAR(100), -- AI model name or user identifier
    detection_timestamp TIMESTAMPTZ DEFAULT NOW(),
    verified BOOLEAN DEFAULT FALSE,
    verified_by UUID REFERENCES users(id),
    verified_at TIMESTAMPTZ,
    verification_notes TEXT,
    
    -- Blockchain integration
    blockchain_hash TEXT UNIQUE,
    blockchain_transaction_id UUID REFERENCES blockchain_transactions(id),
    
    -- Related data
    supporting_data_ids UUID[] DEFAULT '{}', -- Array of environmental_data IDs
    related_threat_ids UUID[] DEFAULT '{}', -- Array of related threat IDs
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    
    -- AI model information
    ai_model_name VARCHAR(100),
    ai_model_version VARCHAR(20),
    ai_confidence_scores JSONB, -- Detailed confidence breakdown
    
    -- Response tracking
    response_actions JSONB DEFAULT '{}',
    resolution_notes TEXT,
    resolved_at TIMESTAMPTZ,
    resolved_by UUID REFERENCES users(id),
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Threat history table for tracking changes
CREATE TABLE threat_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    threat_id UUID REFERENCES threats(id) ON DELETE CASCADE,
    field_name VARCHAR(50) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    changed_by UUID REFERENCES users(id),
    change_reason TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Threat watchers table for subscription management
CREATE TABLE threat_watchers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    threat_id UUID REFERENCES threats(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    notification_preferences JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(threat_id, user_id)
);

-- Threat affected areas table for geographic impact tracking
CREATE TABLE threat_affected_areas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    threat_id UUID REFERENCES threats(id) ON DELETE CASCADE,
    area_type VARCHAR(50) NOT NULL, -- 'evacuation_zone', 'warning_area', 'watch_area'
    geometry GEOGRAPHY(POLYGON, 4326) NOT NULL,
    population_estimate INTEGER,
    area_description TEXT,
    priority_level INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Threat assessments table for expert evaluations
CREATE TABLE threat_assessments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    threat_id UUID REFERENCES threats(id) ON DELETE CASCADE,
    assessor_id UUID REFERENCES users(id),
    assessment_type VARCHAR(50) NOT NULL, -- 'initial', 'update', 'expert_review', 'final'
    severity_assessment INTEGER CHECK (severity_assessment >= 1 AND severity_assessment <= 5),
    confidence_assessment DECIMAL(5,4) CHECK (confidence_assessment >= 0 AND confidence_assessment <= 1),
    impact_assessment TEXT,
    recommendation TEXT,
    evidence JSONB DEFAULT '{}',
    assessment_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Threat resources table for tracking response resources
CREATE TABLE threat_response_resources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    threat_id UUID REFERENCES threats(id) ON DELETE CASCADE,
    resource_type VARCHAR(50) NOT NULL, -- 'personnel', 'equipment', 'facility', 'vehicle'
    resource_name VARCHAR(200) NOT NULL,
    quantity INTEGER DEFAULT 1,
    status VARCHAR(20) DEFAULT 'available', -- 'available', 'deployed', 'unavailable'
    location GEOGRAPHY(POINT, 4326),
    contact_info JSONB,
    deployment_time TIMESTAMPTZ,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for threats table
CREATE INDEX idx_threats_type ON threats(type);
CREATE INDEX idx_threats_severity ON threats(severity);
CREATE INDEX idx_threats_status ON threats(status);
CREATE INDEX idx_threats_location ON threats USING GIST(location);
CREATE INDEX idx_threats_detection_timestamp ON threats(detection_timestamp);
CREATE INDEX idx_threats_verified ON threats(verified);
CREATE INDEX idx_threats_verified_by ON threats(verified_by);
CREATE INDEX idx_threats_blockchain_hash ON threats(blockchain_hash);
CREATE INDEX idx_threats_ai_model ON threats(ai_model_name, ai_model_version);
CREATE INDEX idx_threats_resolved ON threats(resolved_at) WHERE resolved_at IS NOT NULL;
CREATE INDEX idx_threats_created_at ON threats(created_at);

-- Composite indexes for common queries
CREATE INDEX idx_threats_active_by_location ON threats(status, location) WHERE status = 'active';
CREATE INDEX idx_threats_severity_location ON threats(severity, location) USING GIST(location);
CREATE INDEX idx_threats_type_status_severity ON threats(type, status, severity);

-- GIN indexes for array and JSONB columns
CREATE INDEX idx_threats_supporting_data ON threats USING GIN(supporting_data_ids);
CREATE INDEX idx_threats_related_threats ON threats USING GIN(related_threat_ids);
CREATE INDEX idx_threats_tags ON threats USING GIN(tags);
CREATE INDEX idx_threats_metadata ON threats USING GIN(metadata);
CREATE INDEX idx_threats_ai_confidence ON threats USING GIN(ai_confidence_scores);

-- Full-text search index for threat descriptions
CREATE INDEX idx_threats_description_search ON threats USING GIN(to_tsvector('english', description || ' ' || COALESCE(estimated_impact, '')));

-- Indexes for related tables
CREATE INDEX idx_threat_history_threat ON threat_history(threat_id);
CREATE INDEX idx_threat_history_timestamp ON threat_history(timestamp);
CREATE INDEX idx_threat_watchers_user ON threat_watchers(user_id);
CREATE INDEX idx_threat_areas_threat ON threat_affected_areas(threat_id);
CREATE INDEX idx_threat_areas_geometry ON threat_affected_areas USING GIST(geometry);
CREATE INDEX idx_threat_assessments_threat ON threat_assessments(threat_id);
CREATE INDEX idx_threat_assessments_assessor ON threat_assessments(assessor_id);
CREATE INDEX idx_threat_resources_threat ON threat_response_resources(threat_id);
CREATE INDEX idx_threat_resources_type ON threat_response_resources(resource_type);
CREATE INDEX idx_threat_resources_status ON threat_response_resources(status);

-- Add trigger for threats updated_at
CREATE TRIGGER update_threats_updated_at 
    BEFORE UPDATE ON threats 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Create trigger function for threat history tracking
CREATE OR REPLACE FUNCTION log_threat_changes()
RETURNS TRIGGER AS $$
BEGIN
    -- Log changes to important fields
    IF OLD.severity != NEW.severity THEN
        INSERT INTO threat_history (threat_id, field_name, old_value, new_value, changed_by)
        VALUES (NEW.id, 'severity', OLD.severity::TEXT, NEW.severity::TEXT, NEW.updated_at);
    END IF;
    
    IF OLD.status != NEW.status THEN
        INSERT INTO threat_history (threat_id, field_name, old_value, new_value, changed_by)
        VALUES (NEW.id, 'status', OLD.status::TEXT, NEW.status::TEXT, NEW.updated_at);
    END IF;
    
    IF OLD.verified != NEW.verified THEN
        INSERT INTO threat_history (threat_id, field_name, old_value, new_value, changed_by)
        VALUES (NEW.id, 'verified', OLD.verified::TEXT, NEW.verified::TEXT, NEW.verified_by);
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create the trigger
CREATE TRIGGER threat_history_trigger
    AFTER UPDATE ON threats
    FOR EACH ROW
    EXECUTE FUNCTION log_threat_changes();

-- Create function for calculating threat impact score
CREATE OR REPLACE FUNCTION calculate_threat_impact_score(
    p_severity INTEGER,
    p_confidence DECIMAL,
    p_affected_population INTEGER,
    p_affected_area DECIMAL
)
RETURNS DECIMAL AS $$
DECLARE
    base_score DECIMAL;
    population_factor DECIMAL;
    area_factor DECIMAL;
    confidence_factor DECIMAL;
    impact_score DECIMAL;
BEGIN
    -- Base score from severity (1-5 scale)
    base_score := p_severity * 20; -- Convert to 0-100 scale
    
    -- Population impact factor (logarithmic scale)
    population_factor := CASE 
        WHEN p_affected_population = 0 THEN 0
        WHEN p_affected_population < 1000 THEN 5
        WHEN p_affected_population < 10000 THEN 10
        WHEN p_affected_population < 100000 THEN 20
        WHEN p_affected_population < 1000000 THEN 30
        ELSE 40
    END;
    
    -- Area impact factor
    area_factor := CASE
        WHEN p_affected_area IS NULL OR p_affected_area = 0 THEN 0
        WHEN p_affected_area < 1 THEN 5
        WHEN p_affected_area < 10 THEN 10
        WHEN p_affected_area < 100 THEN 15
        WHEN p_affected_area < 1000 THEN 20
        ELSE 25
    END;
    
    -- Confidence factor
    confidence_factor := COALESCE(p_confidence, 0.5) * 100;
    
    -- Calculate weighted impact score
    impact_score := (base_score * 0.4) + (population_factor * 0.3) + (area_factor * 0.2) + (confidence_factor * 0.1);
    
    RETURN LEAST(impact_score, 100.0); -- Cap at 100
END;
$$ LANGUAGE plpgsql;

-- Create function for finding nearby threats
CREATE OR REPLACE FUNCTION find_nearby_threats(
    p_latitude DECIMAL,
    p_longitude DECIMAL,
    p_radius_km DECIMAL DEFAULT 50,
    p_threat_types threat_type[] DEFAULT NULL,
    p_min_severity INTEGER DEFAULT 1
)
RETURNS TABLE(
    threat_id UUID,
    threat_type threat_type,
    severity INTEGER,
    distance_km DECIMAL,
    description TEXT,
    created_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        t.id,
        t.type,
        t.severity,
        (ST_Distance(t.location, ST_Point(p_longitude, p_latitude)::geography) / 1000)::DECIMAL as distance_km,
        t.description,
        t.created_at
    FROM threats t
    WHERE t.status = 'active'
    AND t.severity >= p_min_severity
    AND (p_threat_types IS NULL OR t.type = ANY(p_threat_types))
    AND ST_DWithin(t.location, ST_Point(p_longitude, p_latitude)::geography, p_radius_km * 1000)
    ORDER BY ST_Distance(t.location, ST_Point(p_longitude, p_latitude)::geography);
END;
$$ LANGUAGE plpgsql;

-- Create function for threat statistics
CREATE OR REPLACE FUNCTION get_threat_statistics(
    p_start_date TIMESTAMPTZ DEFAULT NOW() - INTERVAL '30 days',
    p_end_date TIMESTAMPTZ DEFAULT NOW()
)
RETURNS TABLE(
    total_threats BIGINT,
    by_type JSONB,
    by_severity JSONB,
    by_status JSONB,
    average_confidence DECIMAL,
    total_affected_population BIGINT,
    verified_percentage DECIMAL
) AS $$
DECLARE
    stats RECORD;
BEGIN
    -- Get basic statistics
    SELECT 
        COUNT(*) as total,
        AVG(confidence) as avg_conf,
        SUM(affected_population) as total_pop,
        (COUNT(CASE WHEN verified THEN 1 END) * 100.0 / COUNT(*)) as verified_pct
    INTO stats
    FROM threats t
    WHERE t.created_at BETWEEN p_start_date AND p_end_date;
    
    RETURN QUERY
    SELECT 
        stats.total,
        (SELECT jsonb_object_agg(type, count) FROM (
            SELECT t.type, COUNT(*) as count 
            FROM threats t 
            WHERE t.created_at BETWEEN p_start_date AND p_end_date 
            GROUP BY t.type
        ) type_stats),
        (SELECT jsonb_object_agg(severity, count) FROM (
            SELECT t.severity, COUNT(*) as count 
            FROM threats t 
            WHERE t.created_at BETWEEN p_start_date AND p_end_date 
            GROUP BY t.severity
        ) severity_stats),
        (SELECT jsonb_object_agg(status, count) FROM (
            SELECT t.status, COUNT(*) as count 
            FROM threats t 
            WHERE t.created_at BETWEEN p_start_date AND p_end_date 
            GROUP BY t.status
        ) status_stats),
        stats.avg_conf,
        stats.total_pop,
        stats.verified_pct;
END;
$$ LANGUAGE plpgsql;

-- Create materialized view for threat dashboard
CREATE MATERIALIZED VIEW threat_dashboard_summary AS
SELECT 
    COUNT(*) FILTER (WHERE status = 'active') as active_threats,
    COUNT(*) FILTER (WHERE status = 'active' AND severity >= 4) as critical_threats,
    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours') as new_threats_24h,
    COUNT(*) FILTER (WHERE verified = false AND status = 'active') as unverified_threats,
    AVG(severity) FILTER (WHERE status = 'active') as avg_active_severity,
    SUM(affected_population) FILTER (WHERE status = 'active') as total_affected_population,
    (SELECT type FROM threats WHERE status = 'active' GROUP BY type ORDER BY COUNT(*) DESC LIMIT 1) as most_common_threat_type,
    NOW() as last_updated
FROM threats;

-- Create unique index on materialized view
CREATE UNIQUE INDEX idx_threat_dashboard_summary ON threat_dashboard_summary(last_updated);

-- Create views for common threat queries

-- Active threats view
CREATE VIEW active_threats AS
SELECT 
    t.*,
    u_detected.name as detected_by_name,
    u_verified.name as verified_by_name,
    u_resolved.name as resolved_by_name,
    calculate_threat_impact_score(t.severity, t.confidence, t.affected_population, t.affected_area_km2) as impact_score
FROM threats t
LEFT JOIN users u_detected ON u_detected.id::TEXT = t.detected_by
LEFT JOIN users u_verified ON u_verified.id = t.verified_by  
LEFT JOIN users u_resolved ON u_resolved.id = t.resolved_by
WHERE t.status = 'active';

-- High priority threats view
CREATE VIEW high_priority_threats AS
SELECT 
    t.*,
    calculate_threat_impact_score(t.severity, t.confidence, t.affected_population, t.affected_area_km2) as impact_score
FROM threats t
WHERE t.status = 'active' 
AND (t.severity >= 4 OR t.affected_population > 10000)
ORDER BY t.severity DESC, t.affected_population DESC;

-- Recent threats view
CREATE VIEW recent_threats AS
SELECT 
    t.*,
    calculate_threat_impact_score(t.severity, t.confidence, t.affected_population, t.affected_area_km2) as impact_score,
    EXTRACT(EPOCH FROM (NOW() - t.created_at))/3600 as hours_since_detection
FROM threats t
WHERE t.created_at > NOW() - INTERVAL '7 days'
ORDER BY t.created_at DESC;

-- Update environmental_data table to add threat relationship
ALTER TABLE environmental_data ADD COLUMN threat_id UUID REFERENCES threats(id);
CREATE INDEX idx_env_data_threat ON environmental_data(threat_id);

-- Insert sample configuration for threat management
INSERT INTO system_config (key, value, description, category, is_public) VALUES
('threat_auto_verification_threshold', '0.95', 'Confidence threshold for automatic threat verification', 'threats', false),
('threat_max_age_active_days', '7', 'Maximum days a threat can remain active without updates', 'threats', false),
('threat_notification_radius_km', '50', 'Default radius for threat notifications', 'threats', true),
('threat_severity_escalation_hours', '6', 'Hours before escalating unverified high-severity threats', 'threats', false),
('enable_ai_threat_detection', 'true', 'Enable automatic AI-based threat detection', 'threats', true);

-- Add audit logging for threat operations
CREATE OR REPLACE FUNCTION audit_threat_operations()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO audit_log (action, resource_type, resource_id, new_values, timestamp)
        VALUES ('threat_created', 'threat', NEW.id, row_to_json(NEW)::jsonb, NOW());
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit_log (action, resource_type, resource_id, old_values, new_values, timestamp)
        VALUES ('threat_updated', 'threat', NEW.id, row_to_json(OLD)::jsonb, row_to_json(NEW)::jsonb, NOW());
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO audit_log (action, resource_type, resource_id, old_values, timestamp)
        VALUES ('threat_deleted', 'threat', OLD.id, row_to_json(OLD)::jsonb, NOW());
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Create audit trigger for threats
CREATE TRIGGER audit_threats_trigger
    AFTER INSERT OR UPDATE OR DELETE ON threats
    FOR EACH ROW
    EXECUTE FUNCTION audit_threat_operations();

-- Create notification function for new high-severity threats
CREATE OR REPLACE FUNCTION notify_high_severity_threat()
RETURNS TRIGGER AS $$
BEGIN
    -- Only notify for new active threats with severity >= 4
    IF NEW.severity >= 4 AND NEW.status = 'active' THEN
        -- Insert notification task (would be picked up by background worker)
        INSERT INTO system_metrics (metric_name, metric_value, labels, timestamp)
        VALUES (
            'high_severity_threat_detected',
            NEW.severity,
            jsonb_build_object(
                'threat_id', NEW.id,
                'threat_type', NEW.type,
                'location', ST_AsGeoJSON(NEW.location)::jsonb,
                'affected_population', NEW.affected_population
            ),
            NOW()
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create notification trigger
CREATE TRIGGER notify_high_severity_threat_trigger
    AFTER INSERT ON threats
    FOR EACH ROW
    EXECUTE FUNCTION notify_high_severity_threat();

-- Add comments for documentation
COMMENT ON TABLE threats IS 'Core threats table storing all detected environmental threats';
COMMENT ON TABLE threat_history IS 'Historical changes to threat records for audit trail';
COMMENT ON TABLE threat_watchers IS 'Users subscribed to notifications for specific threats';
COMMENT ON TABLE threat_affected_areas IS 'Geographic areas affected by threats';
COMMENT ON TABLE threat_assessments IS 'Expert assessments and evaluations of threats';
COMMENT ON TABLE threat_response_resources IS 'Resources allocated for threat response';

COMMENT ON COLUMN threats.confidence IS 'AI model confidence score (0.0 to 1.0)';
COMMENT ON COLUMN threats.blockchain_hash IS 'Hash of threat data stored on blockchain';
COMMENT ON COLUMN threats.supporting_data_ids IS 'Array of environmental_data record IDs supporting this threat';
COMMENT ON COLUMN threats.ai_confidence_scores IS 'Detailed AI model confidence breakdown';

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Ocean Sentinel threats table migration completed successfully!';
    RAISE NOTICE 'Added threats table with % related tables and supporting functions', 
        (SELECT COUNT(*) FROM information_schema.tables 
         WHERE table_schema = 'public' AND table_name LIKE 'threat%');
END $$;