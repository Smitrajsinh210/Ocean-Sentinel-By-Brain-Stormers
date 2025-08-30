-- Ocean Sentinel - Seed Data for Development/Testing
-- Sample data for development and testing purposes

-- Insert sample admin user (password: 'admin123!')
INSERT INTO users (id, email, name, hashed_password, role, agency, preferences) VALUES
('550e8400-e29b-41d4-a716-446655440000', 'admin@oceansentinel.ai', 'System Administrator', 
 '$2b$12$LQv3Pt4SiJSoKmTVjM/VIucoBjgKJE5v.4aTh7VL/RIGVlD2MsReG', 
 'admin', 'Ocean Sentinel', 
 '{"alert_frequency": "immediate", "dashboard_layout": {"theme": "dark"}}');

-- Insert sample emergency manager
INSERT INTO users (id, email, name, hashed_password, role, agency, phone) VALUES
('550e8400-e29b-41d4-a716-446655440001', 'emergency@coastalauth.gov', 'Emergency Manager', 
 '$2b$12$LQv3Pt4SiJSoKmTVjM/VIucoBjgKJE5v.4aTh7VL/RIGVlD2MsReG', 
 'emergency_manager', 'Coastal Authority', '+1-555-0123');

-- Insert sample threats for testing
INSERT INTO threats (id, type, severity, confidence, location, description, estimated_impact, affected_population, data_sources) VALUES
('660e8400-e29b-41d4-a716-446655440000', 'storm', 4, 0.87, 
 ST_GeomFromText('POINT(-74.0059 40.7128)', 4326),
 'Severe storm conditions detected with wind speeds exceeding 35 m/s and pressure drop of 25 hPa',
 'Major coastal flooding and infrastructure damage expected',
 250000, ARRAY['openweather', 'noaa']),

('660e8400-e29b-41d4-a716-446655440001', 'pollution', 3, 0.75,
 ST_GeomFromText('POINT(-118.2437 34.0522)', 4326),
 'Elevated air pollution levels detected with PM2.5 concentrations at 85 μg/m³',
 'Health advisory for sensitive individuals',
 150000, ARRAY['openaq']),

('660e8400-e29b-41d4-a716-446655440002', 'erosion', 2, 0.65,
 ST_GeomFromText('POINT(-80.1918 25.7617)', 4326),
 'Coastal erosion risk identified with wave heights of 2.8m during high tide',
 'Beach access restrictions recommended',
 5000, ARRAY['noaa']);

-- Insert sample environmental data summary
INSERT INTO environmental_data_summary (id, data_hash, timestamp, total_locations, successful_sources, failed_sources, data_completeness) VALUES
('770e8400-e29b-41d4-a716-446655440000', 'a1b2c3d4e5f6789012345678901234567890abcdef', 
 CURRENT_TIMESTAMP - INTERVAL '1 hour', 8, 3, 1, 87.5);

-- Insert sample environmental data details
INSERT INTO environmental_data_details (summary_id, source, location, timestamp, data, quality_score) VALUES
('770e8400-e29b-41d4-a716-446655440000', 'openweather', 
 ST_GeomFromText('POINT(-74.0059 40.7128)', 4326),
 CURRENT_TIMESTAMP - INTERVAL '1 hour',
 '{"temperature": 22.5, "humidity": 78, "pressure": 1008, "wind_speed": 12.3, "precipitation": 0}',
 0.95),

('770e8400-e29b-41d4-a716-446655440000', 'openaq',
 ST_GeomFromText('POINT(-74.0059 40.7128)', 4326),
 CURRENT_TIMESTAMP - INTERVAL '1 hour',
 '{"pm2_5": 28.5, "pm10": 45.2, "no2": 65.1, "aqi": 89}',
 0.88);

-- Insert sample alert notifications
INSERT INTO alert_notifications (alert_id, threat_id, message, severity, channels, recipients_count, status) VALUES
('ALERT_20250830_001', '660e8400-e29b-41d4-a716-446655440000',
 'CRITICAL STORM ALERT: Severe weather conditions detected in NYC area. Seek shelter immediately.',
 4, ARRAY['sms', 'email', 'push'], 125, 'sent'),

('ALERT_20250830_002', '660e8400-e29b-41d4-a716-446655440001',
 'AIR QUALITY ALERT: Elevated pollution levels in LA area. Limit outdoor activities.',
 3, ARRAY['email', 'push'], 85, 'sent');

-- Insert sample blockchain transactions
INSERT INTO blockchain_transactions (transaction_hash, data_hash, timestamp, source, data_type, network, contract_address) VALUES
('0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef12',
 'a1b2c3d4e5f6789012345678901234567890abcdef',
 CURRENT_TIMESTAMP - INTERVAL '1 hour',
 'multi_source_ingestion', 'environmental_data', 'mumbai',
 '0x742d35Cc6634C0532925a3b8D395DBFAF4fB8fE4');

-- Insert sample system logs
INSERT INTO system_logs (level, message, module, function_name) VALUES
('INFO', 'Environmental data collection completed successfully', 'data_ingestion', 'ingest_all_data'),
('WARNING', 'OpenAQ API rate limit approaching', 'api_clients', 'get_air_quality'),
('INFO', 'New threat detected and stored', 'ai_detection', 'detect_threats');

-- Update sequences to avoid conflicts
SELECT setval('threats_id_seq', (SELECT MAX(id::text)::bigint FROM threats WHERE id::text ~ '^[0-9]+$'), true);
