-- Ocean Sentinel - Complete Database Schema
-- PostgreSQL/Supabase Schema with PostGIS Extensions

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "postgis";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Create custom functions for data processing
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Users table with authentication and preferences
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    hashed_password TEXT NOT NULL,
    role VARCHAR(50) DEFAULT 'user' CHECK (role IN ('user', 'analyst', 'emergency_manager', 'admin')),
    agency VARCHAR(255),
    phone VARCHAR(20),
    location GEOMETRY(POINT, 4326),
    preferences JSONB DEFAULT '{}',
    min_alert_severity INTEGER DEFAULT 3 CHECK (min_alert_severity >= 1 AND min_alert_severity <= 5),
    email_notifications BOOLEAN DEFAULT TRUE,
    sms_notifications BOOLEAN DEFAULT FALSE,
    push_notifications BOOLEAN DEFAULT TRUE,
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMPTZ,
    last_logout TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Create spatial index on user locations
CREATE INDEX idx_users_location ON users USING GIST (location);
CREATE INDEX idx_users_email ON users (email);
CREATE INDEX idx_users_role ON users (role);

-- Update trigger for users
CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users 
    FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();

-- Threats table with geospatial data
CREATE TABLE threats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    type VARCHAR(50) NOT NULL CHECK (type IN ('storm', 'pollution', 'erosion', 'algal_bloom', 'illegal_dumping', 'anomaly')),
    severity INTEGER NOT NULL CHECK (severity >= 1 AND severity <= 5),
    confidence DECIMAL(3,2) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    location GEOMETRY(POINT, 4326) NOT NULL,
    address TEXT,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    verified BOOLEAN DEFAULT FALSE,
    verified_by UUID REFERENCES users(id),
    verified_at TIMESTAMPTZ,
    blockchain_hash TEXT,
    description TEXT NOT NULL,
    estimated_impact TEXT,
    affected_population INTEGER CHECK (affected_population >= 0),
    affected_area_km2 DECIMAL(10,2) CHECK (affected_area_km2 >= 0),
    recommendation TEXT,
    data_sources TEXT[] DEFAULT '{}',
    raw_features JSONB DEFAULT '{}',
    resolved BOOLEAN DEFAULT FALSE,
    resolved_by UUID REFERENCES users(id),
    resolved_at TIMESTAMPTZ,
    resolution_notes TEXT,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Spatial and regular indexes for threats
CREATE INDEX idx_threats_location ON threats USING GIST (location);
CREATE INDEX idx_threats_type ON threats (type);
CREATE INDEX idx_threats_severity ON threats (severity);
CREATE INDEX idx_threats_timestamp ON threats (timestamp);
CREATE INDEX idx_threats_resolved ON threats (resolved);
CREATE INDEX idx_threats_verified ON threats (verified);

-- Update trigger for threats
CREATE TRIGGER update_threats_updated_at 
    BEFORE UPDATE ON threats 
    FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();

-- Environmental data summary table
CREATE TABLE environmental_data_summary (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    data_hash VARCHAR(64) UNIQUE NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    total_locations INTEGER NOT NULL DEFAULT 0,
    successful_sources INTEGER NOT NULL DEFAULT 0,
    failed_sources INTEGER NOT NULL DEFAULT 0,
    data_completeness DECIMAL(5,2) NOT NULL DEFAULT 0 CHECK (data_completeness >= 0 AND data_completeness <= 100),
    aggregated_metrics JSONB DEFAULT '{}',
    blockchain_hash TEXT,
    detail_records_count INTEGER DEFAULT 0,
    data_sources TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_env_data_summary_timestamp ON environmental_data_summary (timestamp);
CREATE INDEX idx_env_data_summary_hash ON environmental_data_summary (data_hash);

-- Environmental data details table
CREATE TABLE environmental_data_details (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    summary_id UUID REFERENCES environmental_data_summary(id) ON DELETE CASCADE,
    source VARCHAR(100) NOT NULL,
    location GEOMETRY(POINT, 4326) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    data JSONB NOT NULL DEFAULT '{}',
    quality_score DECIMAL(3,2) DEFAULT 1.0 CHECK (quality_score >= 0 AND quality_score <= 1),
    verified BOOLEAN DEFAULT FALSE,
    hash TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_env_data_details_location ON environmental_data_details USING GIST (location);
CREATE INDEX idx_env_data_details_source ON environmental_data_details (source);
CREATE INDEX idx_env_data_details_timestamp ON environmental_data_details (timestamp);
CREATE INDEX idx_env_data_details_summary ON environmental_data_details (summary_id);

-- Alert notifications table
CREATE TABLE alert_notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_id VARCHAR(100) UNIQUE NOT NULL,
    threat_id UUID REFERENCES threats(id),
    message TEXT NOT NULL,
    severity INTEGER NOT NULL CHECK (severity >= 1 AND severity <= 5),
    channels TEXT[] DEFAULT '{}',
    recipients TEXT[] DEFAULT '{}',
    recipients_count INTEGER DEFAULT 0,
    total_recipients INTEGER DEFAULT 0,
    target_location GEOMETRY(POINT, 4326),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'sending', 'sent', 'failed', 'partial', 'cancelled')),
    priority VARCHAR(20) DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high', 'critical')),
    bulk_alert BOOLEAN DEFAULT FALSE,
    threat_count INTEGER DEFAULT 1,
    sent_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    blockchain_hash TEXT,
    metadata JSONB DEFAULT '{}',
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_alerts_threat_id ON alert_notifications (threat_id);
CREATE INDEX idx_alerts_status ON alert_notifications (status);
CREATE INDEX idx_alerts_severity ON alert_notifications (severity);
CREATE INDEX idx_alerts_created_at ON alert_notifications (created_at);
CREATE INDEX idx_alerts_location ON alert_notifications USING GIST (target_location);

-- Blockchain transactions table
CREATE TABLE blockchain_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    transaction_hash VARCHAR(66) UNIQUE NOT NULL,
    data_hash VARCHAR(64) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    source VARCHAR(100) NOT NULL,
    data_type VARCHAR(50) NOT NULL,
    reference_id UUID,
    network VARCHAR(50) NOT NULL DEFAULT 'mumbai',
    contract_address VARCHAR(42) NOT NULL,
    block_number BIGINT,
    gas_used INTEGER,
    transaction_fee DECIMAL(20,8),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'confirmed', 'failed')),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_blockchain_tx_hash ON blockchain_transactions (transaction_hash);
CREATE INDEX idx_blockchain_data_hash ON blockchain_transactions (data_hash);
CREATE INDEX idx_blockchain_timestamp ON blockchain_transactions (timestamp);
CREATE INDEX idx_blockchain_data_type ON blockchain_transactions (data_type);

-- System logs table
CREATE TABLE system_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    level VARCHAR(20) NOT NULL CHECK (level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')),
    message TEXT NOT NULL,
    module VARCHAR(100),
    function_name VARCHAR(100),
    user_id UUID REFERENCES users(id),
    metadata JSONB DEFAULT '{}',
    stack_trace TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_system_logs_level ON system_logs (level);
CREATE INDEX idx_system_logs_created_at ON system_logs (created_at);
CREATE INDEX idx_system_logs_module ON system_logs (module);

-- User activities table for audit trail
CREATE TABLE user_activities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    activity_type VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    ip_address INET,
    user_agent TEXT,
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_user_activities_user_id ON user_activities (user_id);
CREATE INDEX idx_user_activities_type ON user_activities (activity_type);
CREATE INDEX idx_user_activities_timestamp ON user_activities (timestamp);

-- API keys table for external integrations
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    key_hash TEXT NOT NULL,
    permissions TEXT[] DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    rate_limit INTEGER DEFAULT 1000,
    last_used TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_api_keys_hash ON api_keys (key_hash);
CREATE INDEX idx_api_keys_active ON api_keys (is_active);

-- Monitoring stations table
CREATE TABLE monitoring_stations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    station_code VARCHAR(50) UNIQUE NOT NULL,
    location GEOMETRY(POINT, 4326) NOT NULL,
    station_type VARCHAR(50) NOT NULL,
    agency VARCHAR(255),
    parameters TEXT[] DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',
    last_data_received TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_monitoring_stations_location ON monitoring_stations USING GIST (location);
CREATE INDEX idx_monitoring_stations_type ON monitoring_stations (station_type);
CREATE INDEX idx_monitoring_stations_active ON monitoring_stations (is_active);

-- Create views for common queries
CREATE VIEW active_threats AS
SELECT 
    t.*,
    ST_X(t.location) AS longitude,
    ST_Y(t.location) AS latitude,
    u.name AS created_by_name,
    u.agency AS created_by_agency
FROM threats t
LEFT JOIN users u ON t.created_by = u.id
WHERE t.resolved = FALSE;

CREATE VIEW recent_alerts AS
SELECT 
    a.*,
    t.type AS threat_type,
    t.severity AS threat_severity,
    ST_X(a.target_location) AS longitude,
    ST_Y(a.target_location) AS latitude
FROM alert_notifications a
LEFT JOIN threats t ON a.threat_id = t.id
WHERE a.created_at >= CURRENT_TIMESTAMP - INTERVAL '7 days'
ORDER BY a.created_at DESC;

-- Function to get threats within radius
CREATE OR REPLACE FUNCTION get_threats_within_radius(
    center_lat DOUBLE PRECISION,
    center_lon DOUBLE PRECISION,
    radius_km DOUBLE PRECISION
)
RETURNS TABLE(
    id UUID,
    type VARCHAR(50),
    severity INTEGER,
    confidence DECIMAL(3,2),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    description TEXT,
    timestamp TIMESTAMPTZ,
    distance_km DOUBLE PRECISION
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        t.id,
        t.type,
        t.severity,
        t.confidence,
        ST_Y(t.location) AS latitude,
        ST_X(t.location) AS longitude,
        t.description,
        t.timestamp,
        ST_Distance(
            ST_GeogFromText('POINT(' || center_lon || ' ' || center_lat || ')'),
            t.location::geography
        ) / 1000 AS distance_km
    FROM threats t
    WHERE ST_DWithin(
        ST_GeogFromText('POINT(' || center_lon || ' ' || center_lat || ')'),
        t.location::geography,
        radius_km * 1000
    )
    ORDER BY distance_km;
END;
$$ LANGUAGE plpgsql;

-- Function to get environmental data near location
CREATE OR REPLACE FUNCTION get_latest_environmental_data(
    center_lat DOUBLE PRECISION DEFAULT NULL,
    center_lon DOUBLE PRECISION DEFAULT NULL,
    radius_km DOUBLE PRECISION DEFAULT 50
)
RETURNS TABLE(
    id UUID,
    source VARCHAR(100),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    data JSONB,
    timestamp TIMESTAMPTZ,
    distance_km DOUBLE PRECISION
) AS $$
BEGIN
    IF center_lat IS NULL OR center_lon IS NULL THEN
        RETURN QUERY
        SELECT 
            ed.id,
            ed.source,
            ST_Y(ed.location) AS latitude,
            ST_X(ed.location) AS longitude,
            ed.data,
            ed.timestamp,
            0.0 AS distance_km
        FROM environmental_data_details ed
        WHERE ed.timestamp >= CURRENT_TIMESTAMP - INTERVAL '24 hours'
        ORDER BY ed.timestamp DESC
        LIMIT 100;
    ELSE
        RETURN QUERY
        SELECT 
            ed.id,
            ed.source,
            ST_Y(ed.location) AS latitude,
            ST_X(ed.location) AS longitude,
            ed.data,
            ed.timestamp,
            ST_Distance(
                ST_GeogFromText('POINT(' || center_lon || ' ' || center_lat || ')'),
                ed.location::geography
            ) / 1000 AS distance_km
        FROM environmental_data_details ed
        WHERE ed.timestamp >= CURRENT_TIMESTAMP - INTERVAL '24 hours'
        AND ST_DWithin(
            ST_GeogFromText('POINT(' || center_lon || ' ' || center_lat || ')'),
            ed.location::geography,
            radius_km * 1000
        )
        ORDER BY distance_km
        LIMIT 100;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Function to get blockchain statistics by type
CREATE OR REPLACE FUNCTION get_blockchain_stats_by_type()
RETURNS TABLE(data_type VARCHAR(50), count BIGINT) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        bt.data_type,
        COUNT(*) as count
    FROM blockchain_transactions bt
    WHERE bt.created_at >= CURRENT_TIMESTAMP - INTERVAL '30 days'
    GROUP BY bt.data_type
    ORDER BY count DESC;
END;
$$ LANGUAGE plpgsql;

-- Create RLS (Row Level Security) policies
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE threats ENABLE ROW LEVEL SECURITY;
ALTER TABLE alert_notifications ENABLE ROW LEVEL SECURITY;

-- RLS policy for users - users can only see their own data unless admin
CREATE POLICY users_select_policy ON users
    FOR SELECT USING (
        auth.uid()::text = id::text OR 
        (SELECT role FROM users WHERE id::text = auth.uid()::text) = 'admin'
    );

-- RLS policy for threats - all authenticated users can read, only admins/managers can write
CREATE POLICY threats_select_policy ON threats FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY threats_insert_policy ON threats 
    FOR INSERT WITH CHECK (
        (SELECT role FROM users WHERE id::text = auth.uid()::text) 
        IN ('admin', 'emergency_manager', 'analyst')
    );

-- Grant permissions to authenticated users
GRANT USAGE ON SCHEMA public TO authenticated;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT INSERT ON threats, alert_notifications, user_activities TO authenticated;
GRANT UPDATE ON users TO authenticated;

-- Grant all permissions to service role
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO service_role;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA public TO service_role;

-- Create indexes for performance
CREATE INDEX CONCURRENTLY idx_threats_created_at_desc ON threats (created_at DESC);
CREATE INDEX CONCURRENTLY idx_alerts_created_at_desc ON alert_notifications (created_at DESC);
CREATE INDEX CONCURRENTLY idx_env_data_timestamp_desc ON environmental_data_details (timestamp DESC);

-- Add comments for documentation
COMMENT ON TABLE threats IS 'Environmental threats detected by AI or reported manually';
COMMENT ON TABLE environmental_data_summary IS 'Summary of environmental data collection batches';
COMMENT ON TABLE environmental_data_details IS 'Detailed environmental sensor readings';
COMMENT ON TABLE alert_notifications IS 'Alert messages sent to users and agencies';
COMMENT ON TABLE blockchain_transactions IS 'Blockchain transaction records for data integrity';
COMMENT ON TABLE users IS 'System users with authentication and preferences';

-- Insert default monitoring stations
INSERT INTO monitoring_stations (name, station_code, location, station_type, agency, parameters) VALUES
('New York Harbor Buoy', 'NYC_HARBOR_01', ST_GeomFromText('POINT(-74.0059 40.7128)', 4326), 'weather_ocean', 'NOAA', ARRAY['water_level', 'wave_height', 'temperature', 'wind_speed']),
('Los Angeles Coast Station', 'LA_COAST_01', ST_GeomFromText('POINT(-118.2437 34.0522)', 4326), 'weather_ocean', 'NOAA', ARRAY['water_level', 'wave_height', 'temperature', 'wind_speed']),
('Miami Beach Monitor', 'MIA_BEACH_01', ST_GeomFromText('POINT(-80.1918 25.7617)', 4326), 'weather_ocean', 'NOAA', ARRAY['water_level', 'wave_height', 'temperature', 'wind_speed']),
('San Francisco Bay Station', 'SF_BAY_01', ST_GeomFromText('POINT(-122.4194 37.7749)', 4326), 'weather_ocean', 'NOAA', ARRAY['water_level', 'wave_height', 'temperature', 'wind_speed']);

-- Create database maintenance procedures
CREATE OR REPLACE FUNCTION cleanup_old_data()
RETURNS void AS $$
BEGIN
    -- Clean up old system logs (older than 90 days)
    DELETE FROM system_logs WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '90 days';
    
    -- Clean up old user activities (older than 1 year)
    DELETE FROM user_activities WHERE timestamp < CURRENT_TIMESTAMP - INTERVAL '1 year';
    
    -- Archive old environmental data (older than 6 months)
    -- In production, this would move data to archive tables
    DELETE FROM environmental_data_details 
    WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '6 months';
    
    -- Update statistics
    ANALYZE;
END;
$$ LANGUAGE plpgsql;

-- Schedule cleanup (would be handled by pg_cron extension in production)
-- SELECT cron.schedule('cleanup-old-data', '0 2 * * 0', 'SELECT cleanup_old_data();');
