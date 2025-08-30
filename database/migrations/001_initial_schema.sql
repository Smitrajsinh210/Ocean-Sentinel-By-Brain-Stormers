-- Ocean Sentinel Database Initial Schema
-- Migration: 001_initial_schema.sql
-- Created: 2025-08-30
-- Description: Initial database schema for Ocean Sentinel system

-- Enable required PostgreSQL extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "postgis";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Set timezone
SET timezone = 'UTC';

-- Create custom types
CREATE TYPE user_role AS ENUM ('public', 'verified_user', 'expert', 'agency', 'admin');
CREATE TYPE data_source AS ENUM ('weather_api', 'openaq', 'noaa', 'nasa', 'sensor_network', 'manual');
CREATE TYPE verification_status AS ENUM ('pending', 'verified', 'rejected', 'expired');

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    role user_role DEFAULT 'public',
    agency VARCHAR(255),
    location GEOGRAPHY(POINT, 4326),
    preferences JSONB DEFAULT '{}',
    email_verified BOOLEAN DEFAULT FALSE,
    api_key VARCHAR(255) UNIQUE,
    last_login TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Environmental data table
CREATE TABLE environmental_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source data_source NOT NULL,
    data_type VARCHAR(50) NOT NULL,
    value DECIMAL(15,6),
    unit VARCHAR(20),
    location GEOGRAPHY(POINT, 4326),
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    verified verification_status DEFAULT 'pending',
    hash TEXT,
    metadata JSONB DEFAULT '{}',
    submitted_by UUID REFERENCES users(id),
    verified_by UUID REFERENCES users(id),
    verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Data sources tracking
CREATE TABLE data_sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(200) NOT NULL,
    source_type data_source NOT NULL,
    api_endpoint TEXT,
    api_key_required BOOLEAN DEFAULT FALSE,
    update_frequency INTERVAL,
    data_types TEXT[] DEFAULT '{}',
    location_coverage GEOGRAPHY(POLYGON, 4326),
    status VARCHAR(20) DEFAULT 'active',
    last_update TIMESTAMPTZ,
    configuration JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- System configuration
CREATE TABLE system_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key VARCHAR(100) UNIQUE NOT NULL,
    value JSONB,
    description TEXT,
    category VARCHAR(50),
    is_public BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- API usage tracking
CREATE TABLE api_usage (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    status_code INTEGER,
    response_time INTEGER, -- milliseconds
    ip_address INET,
    user_agent TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Session management
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Email verification tokens
CREATE TABLE email_verification_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Password reset tokens
CREATE TABLE password_reset_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Notification preferences
CREATE TABLE notification_preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    channel VARCHAR(20) NOT NULL, -- 'email', 'sms', 'push', 'web'
    threat_types TEXT[] DEFAULT '{}',
    min_severity INTEGER DEFAULT 1,
    location_radius INTEGER DEFAULT 25, -- kilometers
    enabled BOOLEAN DEFAULT TRUE,
    contact_info JSONB, -- email, phone, etc.
    quiet_hours JSONB, -- start/end times
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, channel)
);

-- Blockchain transaction log
CREATE TABLE blockchain_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    transaction_hash VARCHAR(255) UNIQUE NOT NULL,
    contract_address VARCHAR(255) NOT NULL,
    contract_name VARCHAR(100),
    function_name VARCHAR(100),
    block_number BIGINT,
    gas_used INTEGER,
    gas_price BIGINT,
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'confirmed', 'failed'
    event_data JSONB,
    related_record_id UUID, -- Generic reference to related record
    related_record_type VARCHAR(50), -- 'environmental_data', 'threat', 'alert'
    network VARCHAR(50) DEFAULT 'polygon-mumbai',
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Rate limiting
CREATE TABLE rate_limits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    identifier VARCHAR(255) NOT NULL, -- user_id, api_key, or ip_address
    identifier_type VARCHAR(20) NOT NULL, -- 'user', 'api_key', 'ip'
    endpoint VARCHAR(255),
    request_count INTEGER DEFAULT 1,
    window_start TIMESTAMPTZ DEFAULT NOW(),
    window_size INTERVAL DEFAULT '1 hour'::INTERVAL,
    UNIQUE(identifier, identifier_type, endpoint, window_start)
);

-- System health metrics
CREATE TABLE system_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(15,6),
    metric_type VARCHAR(20), -- 'counter', 'gauge', 'histogram'
    labels JSONB DEFAULT '{}',
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Audit log
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id UUID,
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for performance

-- Users table indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_agency ON users(agency);
CREATE INDEX idx_users_location ON users USING GIST(location);
CREATE INDEX idx_users_created_at ON users(created_at);

-- Environmental data indexes
CREATE INDEX idx_env_data_source ON environmental_data(source);
CREATE INDEX idx_env_data_type ON environmental_data(data_type);
CREATE INDEX idx_env_data_timestamp ON environmental_data(timestamp);
CREATE INDEX idx_env_data_verified ON environmental_data(verified);
CREATE INDEX idx_env_data_location ON environmental_data USING GIST(location);
CREATE INDEX idx_env_data_hash ON environmental_data(hash);
CREATE INDEX idx_env_data_submitted_by ON environmental_data(submitted_by);
CREATE INDEX idx_env_data_composite ON environmental_data(source, data_type, timestamp);

-- Data sources indexes
CREATE INDEX idx_data_sources_name ON data_sources(name);
CREATE INDEX idx_data_sources_type ON data_sources(source_type);
CREATE INDEX idx_data_sources_status ON data_sources(status);
CREATE INDEX idx_data_sources_coverage ON data_sources USING GIST(location_coverage);

-- API usage indexes
CREATE INDEX idx_api_usage_user ON api_usage(user_id);
CREATE INDEX idx_api_usage_endpoint ON api_usage(endpoint);
CREATE INDEX idx_api_usage_timestamp ON api_usage(timestamp);
CREATE INDEX idx_api_usage_status ON api_usage(status_code);

-- Session indexes
CREATE INDEX idx_sessions_user ON user_sessions(user_id);
CREATE INDEX idx_sessions_token ON user_sessions(session_token);
CREATE INDEX idx_sessions_expires ON user_sessions(expires_at);

-- Blockchain transaction indexes
CREATE INDEX idx_blockchain_tx_hash ON blockchain_transactions(transaction_hash);
CREATE INDEX idx_blockchain_contract ON blockchain_transactions(contract_address);
CREATE INDEX idx_blockchain_status ON blockchain_transactions(status);
CREATE INDEX idx_blockchain_record ON blockchain_transactions(related_record_id, related_record_type);
CREATE INDEX idx_blockchain_timestamp ON blockchain_transactions(timestamp);

-- Rate limit indexes
CREATE INDEX idx_rate_limits_identifier ON rate_limits(identifier, identifier_type);
CREATE INDEX idx_rate_limits_window ON rate_limits(window_start);

-- Metrics indexes
CREATE INDEX idx_metrics_name ON system_metrics(metric_name);
CREATE INDEX idx_metrics_timestamp ON system_metrics(timestamp);
CREATE INDEX idx_metrics_labels ON system_metrics USING GIN(labels);

-- Audit log indexes
CREATE INDEX idx_audit_user ON audit_log(user_id);
CREATE INDEX idx_audit_action ON audit_log(action);
CREATE INDEX idx_audit_resource ON audit_log(resource_type, resource_id);
CREATE INDEX idx_audit_timestamp ON audit_log(timestamp);

-- Full text search indexes
CREATE INDEX idx_env_data_search ON environmental_data USING GIN(to_tsvector('english', data_type || ' ' || COALESCE(metadata->>'description', '')));

-- Create triggers for updated_at columns
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_data_sources_updated_at 
    BEFORE UPDATE ON data_sources 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_system_config_updated_at 
    BEFORE UPDATE ON system_config 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_notification_preferences_updated_at 
    BEFORE UPDATE ON notification_preferences 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Create function for generating API keys
CREATE OR REPLACE FUNCTION generate_api_key()
RETURNS VARCHAR(255) AS $$
DECLARE
    key_length INTEGER := 32;
    characters TEXT := 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    api_key TEXT := '';
    i INTEGER;
BEGIN
    FOR i IN 1..key_length LOOP
        api_key := api_key || substr(characters, floor(random() * length(characters) + 1)::INTEGER, 1);
    END LOOP;
    RETURN 'os_' || api_key;
END;
$$ LANGUAGE plpgsql;

-- Create function for validating geographic coordinates
CREATE OR REPLACE FUNCTION validate_coordinates(lat DECIMAL, lng DECIMAL)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN lat >= -90 AND lat <= 90 AND lng >= -180 AND lng <= 180;
END;
$$ LANGUAGE plpgsql;

-- Create function for calculating distance between points
CREATE OR REPLACE FUNCTION calculate_distance(lat1 DECIMAL, lng1 DECIMAL, lat2 DECIMAL, lng2 DECIMAL)
RETURNS DECIMAL AS $$
BEGIN
    RETURN ST_Distance(
        ST_Point(lng1, lat1)::geography,
        ST_Point(lng2, lat2)::geography
    ) / 1000; -- Return distance in kilometers
END;
$$ LANGUAGE plpgsql;

-- Create stored procedure for cleaning up expired sessions
CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM user_sessions WHERE expires_at < NOW();
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    DELETE FROM email_verification_tokens WHERE expires_at < NOW();
    DELETE FROM password_reset_tokens WHERE expires_at < NOW();
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Create stored procedure for data retention cleanup
CREATE OR REPLACE FUNCTION cleanup_old_data()
RETURNS VOID AS $$
BEGIN
    -- Clean up API usage logs older than 90 days
    DELETE FROM api_usage WHERE timestamp < NOW() - INTERVAL '90 days';
    
    -- Clean up old metrics older than 1 year
    DELETE FROM system_metrics WHERE timestamp < NOW() - INTERVAL '1 year';
    
    -- Clean up audit logs older than 2 years
    DELETE FROM audit_log WHERE timestamp < NOW() - INTERVAL '2 years';
    
    -- Clean up old rate limit records older than 24 hours
    DELETE FROM rate_limits WHERE window_start < NOW() - INTERVAL '24 hours';
END;
$$ LANGUAGE plpgsql;

-- Insert initial system configuration
INSERT INTO system_config (key, value, description, category, is_public) VALUES
('api_version', '"1.0.0"', 'Current API version', 'system', true),
('max_data_age_days', '365', 'Maximum age for environmental data in days', 'data', false),
('default_alert_radius_km', '25', 'Default radius for location-based alerts', 'alerts', true),
('blockchain_network', '"polygon-mumbai"', 'Blockchain network for data integrity', 'blockchain', true),
('maintenance_mode', 'false', 'System maintenance mode flag', 'system', true),
('max_api_requests_per_hour', '1000', 'Maximum API requests per hour for free tier', 'api', true),
('data_retention_days', '2555', 'Data retention period in days (7 years)', 'data', false),
('emergency_contact_email', '"emergency@ocean-sentinel.com"', 'Emergency contact email', 'alerts', true),
('system_timezone', '"UTC"', 'System timezone', 'system', true),
('enable_realtime_alerts', 'true', 'Enable real-time alert notifications', 'alerts', true);

-- Insert initial data sources
INSERT INTO data_sources (name, display_name, source_type, api_endpoint, api_key_required, update_frequency, data_types, status) VALUES
('openweathermap', 'OpenWeatherMap API', 'weather_api', 'https://api.openweathermap.org/data/2.5/', true, '1 hour'::INTERVAL, ARRAY['temperature', 'humidity', 'pressure', 'wind_speed', 'wind_direction'], 'active'),
('openaq', 'OpenAQ Air Quality API', 'openaq', 'https://api.openaq.org/v2/', false, '1 hour'::INTERVAL, ARRAY['pm25', 'pm10', 'o3', 'no2', 'so2', 'co'], 'active'),
('noaa_tides', 'NOAA Tides and Currents', 'noaa', 'https://api.tidesandcurrents.noaa.gov/api/prod/', false, '6 minutes'::INTERVAL, ARRAY['water_level', 'water_temperature', 'salinity', 'wave_height'], 'active'),
('nasa_earth', 'NASA Earth Data', 'nasa', 'https://api.nasa.gov/planetary/earth/', true, '1 day'::INTERVAL, ARRAY['surface_temperature', 'vegetation_index', 'cloud_cover'], 'active');

-- Create views for common queries

-- Active environmental data view
CREATE VIEW active_environmental_data AS
SELECT 
    ed.*,
    u.name as submitted_by_name,
    u.agency as submitted_by_agency,
    ds.display_name as source_display_name
FROM environmental_data ed
LEFT JOIN users u ON ed.submitted_by = u.id
LEFT JOIN data_sources ds ON ds.source_type = ed.source
WHERE ed.timestamp > NOW() - INTERVAL '7 days'
AND ed.verified IN ('verified', 'pending');

-- User statistics view
CREATE VIEW user_statistics AS
SELECT 
    role,
    COUNT(*) as user_count,
    COUNT(CASE WHEN last_login > NOW() - INTERVAL '30 days' THEN 1 END) as active_users,
    COUNT(CASE WHEN email_verified = true THEN 1 END) as verified_users
FROM users 
GROUP BY role;

-- System health view
CREATE VIEW system_health AS
SELECT 
    'environmental_data' as component,
    COUNT(*) as total_records,
    COUNT(CASE WHEN timestamp > NOW() - INTERVAL '1 hour' THEN 1 END) as recent_records,
    COUNT(CASE WHEN verified = 'verified' THEN 1 END) as verified_records
FROM environmental_data
UNION ALL
SELECT 
    'users' as component,
    COUNT(*) as total_records,
    COUNT(CASE WHEN last_login > NOW() - INTERVAL '24 hours' THEN 1 END) as recent_records,
    COUNT(CASE WHEN email_verified = true THEN 1 END) as verified_records
FROM users
UNION ALL
SELECT 
    'api_usage' as component,
    COUNT(*) as total_records,
    COUNT(CASE WHEN timestamp > NOW() - INTERVAL '1 hour' THEN 1 END) as recent_records,
    COUNT(CASE WHEN status_code < 400 THEN 1 END) as verified_records
FROM api_usage
WHERE timestamp > NOW() - INTERVAL '24 hours';

-- Grant permissions (adjust as needed for your deployment)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO ocean_sentinel_app;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO ocean_sentinel_app;

-- Comment on tables and important columns
COMMENT ON TABLE users IS 'User accounts and authentication information';
COMMENT ON TABLE environmental_data IS 'Environmental sensor data and observations';
COMMENT ON TABLE data_sources IS 'Configuration for external data source APIs';
COMMENT ON TABLE blockchain_transactions IS 'Log of all blockchain transactions for data integrity';
COMMENT ON TABLE audit_log IS 'Comprehensive audit trail of all user actions';

COMMENT ON COLUMN users.location IS 'User location for proximity-based alerts (PostGIS geography point)';
COMMENT ON COLUMN environmental_data.location IS 'Geographic location of the environmental measurement';
COMMENT ON COLUMN environmental_data.hash IS 'Cryptographic hash for blockchain verification';
COMMENT ON COLUMN blockchain_transactions.event_data IS 'Decoded event data from blockchain transaction';

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Ocean Sentinel initial schema migration completed successfully!';
    RAISE NOTICE 'Created % tables with indexes and triggers', 
        (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public');
END $$;