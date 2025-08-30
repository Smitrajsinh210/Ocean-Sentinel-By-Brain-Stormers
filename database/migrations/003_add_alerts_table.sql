-- Ocean Sentinel Database Migration
-- Migration: 003_add_alerts_table.sql
-- Created: 2025-08-30
-- Description: Add alerts table and related alert management functionality

-- Create alert-related custom types
CREATE TYPE alert_status AS ENUM ('pending', 'sending', 'sent', 'delivered', 'failed', 'cancelled');
CREATE TYPE alert_channel AS ENUM ('web', 'email', 'sms', 'push', 'webhook', 'radio');
CREATE TYPE alert_priority AS ENUM ('low', 'normal', 'high', 'urgent', 'emergency');

-- Main alerts table
CREATE TABLE alert_notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    threat_id UUID REFERENCES threats(id),
    
    -- Alert content
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    severity INTEGER CHECK (severity >= 1 AND severity <= 5) NOT NULL,
    priority alert_priority DEFAULT 'normal',
    is_emergency BOOLEAN DEFAULT FALSE,
    
    -- Channel configuration
    channels alert_channel[] NOT NULL DEFAULT ARRAY['web']::alert_channel[],
    primary_channel alert_channel,
    
    -- Targeting
    target_location GEOGRAPHY(POINT, 4326),
    target_radius_km DECIMAL(8,2),
    target_area GEOGRAPHY(POLYGON, 4326),
    recipients JSONB DEFAULT '{}', -- Channel-specific recipient lists
    audience_filter JSONB DEFAULT '{}', -- User role, agency, etc. filters
    
    -- Scheduling
    scheduled_for TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    repeat_interval INTERVAL,
    max_repeats INTEGER DEFAULT 1,
    repeat_count INTEGER DEFAULT 0,
    
    -- Status tracking
    status alert_status DEFAULT 'pending',
    status_message TEXT,
    
    -- Delivery tracking
    sent_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    delivery_stats JSONB DEFAULT '{}', -- Per-channel delivery statistics
    delivery_confirmations JSONB DEFAULT '{}', -- Delivery confirmations
    
    -- User interaction
    read_receipts JSONB DEFAULT '{}', -- User read confirmations
    user_responses JSONB DEFAULT '{}', -- User responses/acknowledgments
    feedback JSONB DEFAULT '{}', -- User feedback on alert
    
    -- Blockchain integration
    blockchain_hash TEXT,
    blockchain_transaction_id UUID REFERENCES blockchain_transactions(id),
    
    -- System information
    created_by UUID REFERENCES users(id),
    approved_by UUID REFERENCES users(id),
    approval_required BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    
    -- Performance tracking
    processing_time_ms INTEGER, -- Time to process alert
    delivery_time_ms INTEGER, -- Time to deliver alert
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Alert delivery attempts table
CREATE TABLE alert_delivery_attempts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_id UUID REFERENCES alert_notifications(id) ON DELETE CASCADE,
    channel alert_channel NOT NULL,
    recipient_id VARCHAR(255), -- Email, phone number, user ID, etc.
    recipient_type VARCHAR(50), -- 'user_id', 'email', 'phone', 'webhook_url'
    
    -- Attempt information
    attempt_number INTEGER DEFAULT 1,
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'success', 'failed', 'retry'
    error_message TEXT,
    response_data JSONB,
    
    -- Delivery tracking
    sent_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    read_at TIMESTAMPTZ,
    response_at TIMESTAMPTZ,
    
    -- External service information
    external_id VARCHAR(255), -- ID from email service, SMS service, etc.
    external_status VARCHAR(50),
    
    -- Performance
    processing_time_ms INTEGER,
    delivery_time_ms INTEGER,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Alert templates table
CREATE TABLE alert_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) UNIQUE NOT NULL,
    description TEXT,
    threat_type threat_type,
    severity_range INTEGER[] DEFAULT ARRAY[1,2,3,4,5],
    
    -- Template content
    title_template TEXT NOT NULL,
    message_template TEXT NOT NULL,
    
    -- Default configuration
    default_channels alert_channel[] DEFAULT ARRAY['web']::alert_channel[],
    default_priority alert_priority DEFAULT 'normal',
    requires_approval BOOLEAN DEFAULT FALSE,
    
    -- Audience targeting
    target_roles user_role[] DEFAULT ARRAY['public', 'verified_user', 'expert', 'agency']::user_role[],
    target_agencies TEXT[],
    geographic_scope VARCHAR(50), -- 'local', 'regional', 'national', 'global'
    
    -- Scheduling options
    immediate_send BOOLEAN DEFAULT TRUE,
    schedule_offset INTERVAL, -- Delay before sending
    expiry_duration INTERVAL DEFAULT INTERVAL '24 hours',
    
    -- Template variables
    available_variables TEXT[] DEFAULT '{}',
    variable_descriptions JSONB DEFAULT '{}',
    
    -- Metadata
    category VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    usage_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMPTZ,
    
    -- Ownership
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id),
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Alert subscriptions table
CREATE TABLE alert_subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    
    -- Subscription criteria
    threat_types threat_type[] DEFAULT ARRAY['storm', 'pollution', 'erosion', 'algal_bloom', 'illegal_dumping']::threat_type[],
    min_severity INTEGER DEFAULT 1,
    max_severity INTEGER DEFAULT 5,
    
    -- Geographic filters
    location GEOGRAPHY(POINT, 4326),
    radius_km DECIMAL(8,2) DEFAULT 25,
    custom_areas GEOGRAPHY(POLYGON, 4326)[],
    
    -- Channel preferences
    preferred_channels alert_channel[] DEFAULT ARRAY['web', 'email']::alert_channel[],
    emergency_channels alert_channel[] DEFAULT ARRAY['web', 'email', 'push']::alert_channel[],
    
    -- Contact information per channel
    email_address VARCHAR(255),
    phone_number VARCHAR(20),
    webhook_url TEXT,
    push_subscription JSONB,
    
    -- Filtering options
    quiet_hours JSONB, -- {"start": "22:00", "end": "06:00", "timezone": "UTC"}
    weekend_alerts BOOLEAN DEFAULT TRUE,
    duplicate_suppression BOOLEAN DEFAULT TRUE,
    
    -- Delivery preferences
    immediate_delivery BOOLEAN DEFAULT TRUE,
    batch_delivery BOOLEAN DEFAULT FALSE,
    batch_interval INTERVAL DEFAULT INTERVAL '15 minutes',
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    verified BOOLEAN DEFAULT FALSE,
    verification_token VARCHAR(255),
    
    -- Statistics
    alerts_received INTEGER DEFAULT 0,
    last_alert_at TIMESTAMPTZ,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Alert feedback table
CREATE TABLE alert_feedback (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_id UUID REFERENCES alert_notifications(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id),
    
    -- Feedback data
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    feedback_type VARCHAR(50), -- 'helpful', 'not_helpful', 'false_alarm', 'too_late', 'spam'
    comments TEXT,
    
    -- Context
    received_via alert_channel,
    response_time_seconds INTEGER, -- Time from alert to feedback
    
    -- Additional data
    suggested_improvements TEXT,
    would_recommend BOOLEAN,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Alert escalation rules table
CREATE TABLE alert_escalation_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    
    -- Trigger conditions
    trigger_severity INTEGER,
    trigger_threat_types threat_type[],
    trigger_delay INTERVAL DEFAULT INTERVAL '30 minutes',
    
    -- Escalation actions
    escalate_to_users UUID[],
    escalate_to_roles user_role[],
    additional_channels alert_channel[],
    priority_override alert_priority,
    
    -- Escalation message
    escalation_message_template TEXT,
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for alert_notifications
CREATE INDEX idx_alerts_threat ON alert_notifications(threat_id);
CREATE INDEX idx_alerts_severity ON alert_notifications(severity);
CREATE INDEX idx_alerts_status ON alert_notifications(status);
CREATE INDEX idx_alerts_priority ON alert_notifications(priority);
CREATE INDEX idx_alerts_emergency ON alert_notifications(is_emergency);
CREATE INDEX idx_alerts_channels ON alert_notifications USING GIN(channels);
CREATE INDEX idx_alerts_location ON alert_notifications USING GIST(target_location);
CREATE INDEX idx_alerts_area ON alert_notifications USING GIST(target_area);
CREATE INDEX idx_alerts_scheduled ON alert_notifications(scheduled_for) WHERE scheduled_for IS NOT NULL;
CREATE INDEX idx_alerts_expires ON alert_notifications(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX idx_alerts_created_by ON alert_notifications(created_by);
CREATE INDEX idx_alerts_sent_at ON alert_notifications(sent_at);
CREATE INDEX idx_alerts_delivered_at ON alert_notifications(delivered_at);
CREATE INDEX idx_alerts_created_at ON alert_notifications(created_at);

-- Composite indexes for common queries
CREATE INDEX idx_alerts_active_pending ON alert_notifications(status, scheduled_for) WHERE status IN ('pending', 'sending');
CREATE INDEX idx_alerts_emergency_undelivered ON alert_notifications(is_emergency, status, created_at) WHERE is_emergency = TRUE;
CREATE INDEX idx_alerts_threat_severity ON alert_notifications(threat_id, severity);

-- JSONB indexes
CREATE INDEX idx_alerts_recipients ON alert_notifications USING GIN(recipients);
CREATE INDEX idx_alerts_delivery_stats ON alert_notifications USING GIN(delivery_stats);
CREATE INDEX idx_alerts_metadata ON alert_notifications USING GIN(metadata);

-- Indexes for delivery attempts
CREATE INDEX idx_delivery_attempts_alert ON alert_delivery_attempts(alert_id);
CREATE INDEX idx_delivery_attempts_channel ON alert_delivery_attempts(channel);
CREATE INDEX idx_delivery_attempts_recipient ON alert_delivery_attempts(recipient_id, recipient_type);
CREATE INDEX idx_delivery_attempts_status ON alert_delivery_attempts(status);
CREATE INDEX idx_delivery_attempts_sent_at ON alert_delivery_attempts(sent_at);
CREATE INDEX idx_delivery_attempts_external_id ON alert_delivery_attempts(external_id);

-- Indexes for templates
CREATE INDEX idx_templates_threat_type ON alert_templates(threat_type);
CREATE INDEX idx_templates_active ON alert_templates(is_active);
CREATE INDEX idx_templates_category ON alert_templates(category);
CREATE INDEX idx_templates_severity_range ON alert_templates USING GIN(severity_range);

-- Indexes for subscriptions
CREATE INDEX idx_subscriptions_user ON alert_subscriptions(user_id);
CREATE INDEX idx_subscriptions_location ON alert_subscriptions USING GIST(location);
CREATE INDEX idx_subscriptions_threat_types ON alert_subscriptions USING GIN(threat_types);
CREATE INDEX idx_subscriptions_channels ON alert_subscriptions USING GIN(preferred_channels);
CREATE INDEX idx_subscriptions_active ON alert_subscriptions(is_active);
CREATE INDEX idx_subscriptions_verified ON alert_subscriptions(verified);

-- Indexes for feedback
CREATE INDEX idx_feedback_alert ON alert_feedback(alert_id);
CREATE INDEX idx_feedback_user ON alert_feedback(user_id);
CREATE INDEX idx_feedback_rating ON alert_feedback(rating);
CREATE INDEX idx_feedback_type ON alert_feedback(feedback_type);

-- Add triggers for updated_at columns
CREATE TRIGGER update_alerts_updated_at 
    BEFORE UPDATE ON alert_notifications 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_delivery_attempts_updated_at 
    BEFORE UPDATE ON alert_delivery_attempts 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_templates_updated_at 
    BEFORE UPDATE ON alert_templates 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_subscriptions_updated_at 
    BEFORE UPDATE ON alert_subscriptions 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_escalation_rules_updated_at 
    BEFORE UPDATE ON alert_escalation_rules 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Create function to calculate alert delivery score
CREATE OR REPLACE FUNCTION calculate_alert_delivery_score(
    p_alert_id UUID
)
RETURNS DECIMAL AS $$
DECLARE
    total_attempts INTEGER;
    successful_deliveries INTEGER;
    avg_delivery_time INTEGER;
    delivery_score DECIMAL;
BEGIN
    -- Get delivery statistics
    SELECT 
        COUNT(*),
        COUNT(CASE WHEN status = 'success' THEN 1 END),
        AVG(delivery_time_ms)
    INTO total_attempts, successful_deliveries, avg_delivery_time
    FROM alert_delivery_attempts
    WHERE alert_id = p_alert_id;
    
    -- Calculate score (0-100)
    IF total_attempts = 0 THEN
        RETURN 0;
    END IF;
    
    -- Base score from success rate
    delivery_score := (successful_deliveries::DECIMAL / total_attempts) * 100;
    
    -- Adjust for delivery speed (bonus for fast delivery, penalty for slow)
    IF avg_delivery_time IS NOT NULL THEN
        IF avg_delivery_time < 30000 THEN -- Under 30 seconds
            delivery_score := delivery_score * 1.1;
        ELSIF avg_delivery_time > 300000 THEN -- Over 5 minutes
            delivery_score := delivery_score * 0.9;
        END IF;
    END IF;
    
    RETURN LEAST(delivery_score, 100.0);
END;
$$ LANGUAGE plpgsql;

-- Create function to find matching alert subscriptions
CREATE OR REPLACE FUNCTION find_matching_subscriptions(
    p_threat_type threat_type,
    p_severity INTEGER,
    p_location_lat DECIMAL,
    p_location_lng DECIMAL
)
RETURNS TABLE(
    subscription_id UUID,
    user_id UUID,
    preferred_channels alert_channel[],
    email_address VARCHAR,
    phone_number VARCHAR,
    distance_km DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.id,
        s.user_id,
        s.preferred_channels,
        s.email_address,
        s.phone_number,
        (ST_Distance(s.location, ST_Point(p_location_lng, p_location_lat)::geography) / 1000)::DECIMAL as distance_km
    FROM alert_subscriptions s
    WHERE s.is_active = TRUE
    AND s.verified = TRUE
    AND p_threat_type = ANY(s.threat_types)
    AND p_severity >= s.min_severity 
    AND p_severity <= s.max_severity
    AND (s.location IS NULL OR 
         ST_DWithin(s.location, ST_Point(p_location_lng, p_location_lat)::geography, s.radius_km * 1000))
    ORDER BY distance_km NULLS LAST;
END;
$$ LANGUAGE plpgsql;

-- Create function to process alert template
CREATE OR REPLACE FUNCTION process_alert_template(
    p_template_id UUID,
    p_variables JSONB
)
RETURNS TABLE(
    processed_title TEXT,
    processed_message TEXT
) AS $$
DECLARE
    template RECORD;
    title_result TEXT;
    message_result TEXT;
    var_key TEXT;
    var_value TEXT;
BEGIN
    -- Get template
    SELECT title_template, message_template 
    INTO template 
    FROM alert_templates 
    WHERE id = p_template_id AND is_active = TRUE;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Alert template not found or inactive: %', p_template_id;
    END IF;
    
    title_result := template.title_template;
    message_result := template.message_template;
    
    -- Replace variables
    FOR var_key, var_value IN SELECT * FROM jsonb_each_text(p_variables)
    LOOP
        title_result := REPLACE(title_result, '{{' || var_key || '}}', var_value);
        message_result := REPLACE(message_result, '{{' || var_key || '}}', var_value);
    END LOOP;
    
    RETURN QUERY SELECT title_result, message_result;
END;
$$ LANGUAGE plpgsql;

-- Create function for alert statistics
CREATE OR REPLACE FUNCTION get_alert_statistics(
    p_start_date TIMESTAMPTZ DEFAULT NOW() - INTERVAL '30 days',
    p_end_date TIMESTAMPTZ DEFAULT NOW()
)
RETURNS TABLE(
    total_alerts BIGINT,
    emergency_alerts BIGINT,
    delivered_alerts BIGINT,
    failed_alerts BIGINT,
    avg_delivery_time_ms DECIMAL,
    delivery_success_rate DECIMAL,
    by_channel JSONB,
    by_severity JSONB,
    by_status JSONB
) AS $$
BEGIN
    RETURN QUERY
    WITH alert_stats AS (
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN is_emergency THEN 1 END) as emergency,
            COUNT(CASE WHEN status = 'delivered' THEN 1 END) as delivered,
            COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed,
            AVG(delivery_time_ms) as avg_delivery_time,
            (COUNT(CASE WHEN status = 'delivered' THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0)) as success_rate
        FROM alert_notifications
        WHERE created_at BETWEEN p_start_date AND p_end_date
    ),
    channel_stats AS (
        SELECT jsonb_object_agg(channel, count) as channels
        FROM (
            SELECT unnest(channels) as channel, COUNT(*)
            FROM alert_notifications
            WHERE created_at BETWEEN p_start_date AND p_end_date
            GROUP BY channel
        ) cs
    ),
    severity_stats AS (
        SELECT jsonb_object_agg(severity, count) as severities
        FROM (
            SELECT severity, COUNT(*)
            FROM alert_notifications
            WHERE created_at BETWEEN p_start_date AND p_end_date
            GROUP BY severity
        ) ss
    ),
    status_stats AS (
        SELECT jsonb_object_agg(status, count) as statuses
        FROM (
            SELECT status, COUNT(*)
            FROM alert_notifications
            WHERE created_at BETWEEN p_start_date AND p_end_date
            GROUP BY status
        ) st
    )
    SELECT 
        a.total,
        a.emergency,
        a.delivered,
        a.failed,
        a.avg_delivery_time,
        a.success_rate,
        c.channels,
        s.severities,
        st.statuses
    FROM alert_stats a, channel_stats c, severity_stats s, status_stats st;
END;
$$ LANGUAGE plpgsql;

-- Create materialized view for alert dashboard
CREATE MATERIALIZED VIEW alert_dashboard_summary AS
SELECT 
    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours') as alerts_24h,
    COUNT(*) FILTER (WHERE status = 'pending') as pending_alerts,
    COUNT(*) FILTER (WHERE is_emergency AND created_at > NOW() - INTERVAL '24 hours') as emergency_alerts_24h,
    COUNT(*) FILTER (WHERE status = 'failed') as failed_alerts,
    AVG(delivery_time_ms) FILTER (WHERE delivery_time_ms IS NOT NULL) as avg_delivery_time_ms,
    (COUNT(*) FILTER (WHERE status = 'delivered') * 100.0 / NULLIF(COUNT(*), 0)) as delivery_success_rate,
    COUNT(DISTINCT threat_id) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours') as unique_threats_alerted,
    NOW() as last_updated
FROM alert_notifications
WHERE created_at > NOW() - INTERVAL '7 days';

-- Create unique index for materialized view
CREATE UNIQUE INDEX idx_alert_dashboard_summary ON alert_dashboard_summary(last_updated);

-- Create views for common alert queries

-- Pending alerts view
CREATE VIEW pending_alerts AS
SELECT 
    a.*,
    t.type as threat_type,
    t.location as threat_location,
    t.description as threat_description,
    u.name as created_by_name
FROM alert_notifications a
LEFT JOIN threats t ON a.threat_id = t.id
LEFT JOIN users u ON a.created_by = u.id
WHERE a.status IN ('pending', 'sending')
AND (a.scheduled_for IS NULL OR a.scheduled_for <= NOW())
ORDER BY a.priority DESC, a.created_at ASC;

-- Emergency alerts view
CREATE VIEW emergency_alerts AS
SELECT 
    a.*,
    t.type as threat_type,
    t.severity as threat_severity,
    t.location as threat_location
FROM alert_notifications a
LEFT JOIN threats t ON a.threat_id = t.id
WHERE a.is_emergency = TRUE
ORDER BY a.created_at DESC;

-- Recent alert performance view
CREATE VIEW recent_alert_performance AS
SELECT 
    a.id,
    a.title,
    a.severity,
    a.status,
    a.created_at,
    a.sent_at,
    a.delivered_at,
    (EXTRACT(EPOCH FROM (a.sent_at - a.created_at)) * 1000)::INTEGER as processing_time_ms,
    (EXTRACT(EPOCH FROM (a.delivered_at - a.sent_at)) * 1000)::INTEGER as delivery_time_ms,
    calculate_alert_delivery_score(a.id) as delivery_score,
    (SELECT COUNT(*) FROM alert_delivery_attempts ada WHERE ada.alert_id = a.id) as total_attempts,
    (SELECT COUNT(*) FROM alert_delivery_attempts ada WHERE ada.alert_id = a.id AND ada.status = 'success') as successful_deliveries
FROM alert_notifications a
WHERE a.created_at > NOW() - INTERVAL '24 hours'
ORDER BY a.created_at DESC;

-- Create function to automatically create alerts for high-severity threats
CREATE OR REPLACE FUNCTION auto_create_threat_alert()
RETURNS TRIGGER AS $$
DECLARE
    alert_id UUID;
    template_record RECORD;
BEGIN
    -- Only create alerts for high severity threats (4-5)
    IF NEW.severity >= 4 AND NEW.status = 'active' THEN
        
        -- Find appropriate template
        SELECT * INTO template_record
        FROM alert_templates
        WHERE threat_type = NEW.type
        AND NEW.severity = ANY(severity_range)
        AND is_active = TRUE
        ORDER BY usage_count ASC, created_at DESC
        LIMIT 1;
        
        -- Create alert
        INSERT INTO alert_notifications (
            threat_id,
            title,
            message,
            severity,
            priority,
            is_emergency,
            channels,
            target_location,
            target_radius_km,
            status
        ) VALUES (
            NEW.id,
            COALESCE(template_record.title_template, 'High Severity Threat Alert'),
            COALESCE(template_record.message_template, 'A high severity threat has been detected: ' || NEW.description),
            NEW.severity,
            CASE WHEN NEW.severity = 5 THEN 'emergency'::alert_priority ELSE 'urgent'::alert_priority END,
            NEW.severity = 5,
            COALESCE(template_record.default_channels, ARRAY['web', 'email', 'push']::alert_channel[]),
            NEW.location,
            50, -- 50 km default radius
            'pending'
        ) RETURNING id INTO alert_id;
        
        -- Update template usage count
        IF template_record.id IS NOT NULL THEN
            UPDATE alert_templates 
            SET usage_count = usage_count + 1, last_used_at = NOW()
            WHERE id = template_record.id;
        END IF;
        
        -- Log the auto-created alert
        INSERT INTO audit_log (action, resource_type, resource_id, new_values, timestamp)
        VALUES ('alert_auto_created', 'alert', alert_id, 
                jsonb_build_object('threat_id', NEW.id, 'severity', NEW.severity), NOW());
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for auto-creating alerts
CREATE TRIGGER auto_create_threat_alert_trigger
    AFTER INSERT ON threats
    FOR EACH ROW
    EXECUTE FUNCTION auto_create_threat_alert();

-- Insert default alert templates
INSERT INTO alert_templates (name, description, threat_type, title_template, message_template, default_channels, default_priority) VALUES
('Storm Warning', 'Template for storm-related threats', 'storm', 
 'Storm Warning: {{threat_description}}', 
 'STORM ALERT: {{threat_description}}. Severity: {{severity}}/5. Location: {{location}}. Take immediate precautions and monitor conditions.',
 ARRAY['web', 'email', 'push']::alert_channel[], 'high'),
 
('Pollution Alert', 'Template for pollution threats', 'pollution',
 'Pollution Alert: {{threat_description}}',
 'POLLUTION ALERT: {{threat_description}}. Severity: {{severity}}/5. Affected area: {{location}}. Avoid exposure and follow safety guidelines.',
 ARRAY['web', 'email']::alert_channel[], 'normal'),
 
('Coastal Erosion Notice', 'Template for erosion threats', 'erosion',
 'Coastal Erosion Advisory: {{location}}',
 'EROSION ADVISORY: Coastal erosion detected at {{location}}. Severity: {{severity}}/5. Avoid affected coastal areas and structures.',
 ARRAY['web', 'email']::alert_channel[], 'normal'),
 
('Algal Bloom Warning', 'Template for algal bloom threats', 'algal_bloom',
 'Algal Bloom Warning: {{location}}',
 'ALGAL BLOOM WARNING: Harmful algal bloom detected at {{location}}. Severity: {{severity}}/5. Avoid water contact and consumption.',
 ARRAY['web', 'email', 'push']::alert_channel[], 'high'),
 
('Emergency Evacuation', 'Template for emergency evacuations', NULL,
 'EMERGENCY EVACUATION ORDER',
 'IMMEDIATE EVACUATION REQUIRED: {{threat_description}}. Leave the area immediately and follow evacuation routes. This is not a drill.',
 ARRAY['web', 'email', 'sms', 'push']::alert_channel[], 'emergency');

-- Insert system configuration for alerts
INSERT INTO system_config (key, value, description, category, is_public) VALUES
('alert_max_delivery_attempts', '3', 'Maximum delivery attempts per alert per channel', 'alerts', false),
('alert_retry_delay_minutes', '5', 'Delay between delivery retry attempts in minutes', 'alerts', false),
('alert_default_expiry_hours', '24', 'Default alert expiry time in hours', 'alerts', true),
('alert_emergency_escalation_minutes', '15', 'Minutes before escalating emergency alerts', 'alerts', false),
('alert_rate_limit_per_hour', '100', 'Maximum alerts per user per hour', 'alerts', false),
('enable_auto_threat_alerts', 'true', 'Automatically create alerts for high-severity threats', 'alerts', true),
('alert_feedback_enabled', 'true', 'Enable alert feedback collection', 'alerts', true),
('alert_read_receipts_enabled', 'true', 'Track alert read receipts', 'alerts', true);

-- Add audit logging for alert operations
CREATE OR REPLACE FUNCTION audit_alert_operations()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO audit_log (action, resource_type, resource_id, new_values, timestamp)
        VALUES ('alert_created', 'alert', NEW.id, row_to_json(NEW)::jsonb, NOW());
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit_log (action, resource_type, resource_id, old_values, new_values, timestamp)
        VALUES ('alert_updated', 'alert', NEW.id, row_to_json(OLD)::jsonb, row_to_json(NEW)::jsonb, NOW());
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO audit_log (action, resource_type, resource_id, old_values, timestamp)
        VALUES ('alert_deleted', 'alert', OLD.id, row_to_json(OLD)::jsonb, NOW());
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Create audit trigger for alerts
CREATE TRIGGER audit_alerts_trigger
    AFTER INSERT OR UPDATE OR DELETE ON alert_notifications
    FOR EACH ROW
    EXECUTE FUNCTION audit_alert_operations();

-- Add comments for documentation
COMMENT ON TABLE alert_notifications IS 'Main table for storing alert notifications and their delivery status';
COMMENT ON TABLE alert_delivery_attempts IS 'Detailed tracking of individual alert delivery attempts per channel';
COMMENT ON TABLE alert_templates IS 'Reusable templates for creating standardized alerts';
COMMENT ON TABLE alert_subscriptions IS 'User subscriptions for receiving alerts based on criteria';
COMMENT ON TABLE alert_feedback IS 'User feedback on alert usefulness and effectiveness';
COMMENT ON TABLE alert_escalation_rules IS 'Rules for escalating unacknowledged critical alerts';

COMMENT ON COLUMN alert_notifications.recipients IS 'Channel-specific recipient lists in JSON format';
COMMENT ON COLUMN alert_notifications.delivery_stats IS 'Per-channel delivery statistics and metrics';
COMMENT ON COLUMN alert_notifications.blockchain_hash IS 'Hash of alert data for blockchain verification';

-- Create cleanup function for old alerts
CREATE OR REPLACE FUNCTION cleanup_old_alerts()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Delete delivered alerts older than 90 days
    DELETE FROM alert_notifications 
    WHERE status = 'delivered' 
    AND created_at < NOW() - INTERVAL '90 days';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    -- Delete failed alerts older than 30 days
    DELETE FROM alert_notifications 
    WHERE status = 'failed' 
    AND created_at < NOW() - INTERVAL '30 days';
    
    -- Clean up old delivery attempts (keep only last 30 days)
    DELETE FROM alert_delivery_attempts
    WHERE created_at < NOW() - INTERVAL '30 days';
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Ocean Sentinel alerts table migration completed successfully!';
    RAISE NOTICE 'Added alerts functionality with % tables, % templates, and supporting functions', 
        (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE 'alert%'),
        (SELECT COUNT(*) FROM alert_templates);
END $$;