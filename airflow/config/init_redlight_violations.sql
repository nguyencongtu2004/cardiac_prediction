-- Connect to traffic_monitoring database
\c traffic_monitoring

-- Create redlight violations table
CREATE TABLE IF NOT EXISTS redlight_violations (
    id SERIAL PRIMARY KEY,
    violation_id UUID UNIQUE NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    camera_id VARCHAR(100) NOT NULL,
    track_id INTEGER NOT NULL,
    frame_number INTEGER NOT NULL,
    violation_type VARCHAR(50) NOT NULL DEFAULT 'RED_LIGHT',
    vehicle_type VARCHAR(50),
    traffic_light_state VARCHAR(20),
    confidence FLOAT,
    bbox_x INTEGER,
    bbox_y INTEGER,
    bbox_w INTEGER,
    bbox_h INTEGER,
    image_path TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_redlight_timestamp ON redlight_violations(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_redlight_camera ON redlight_violations(camera_id);
CREATE INDEX IF NOT EXISTS idx_redlight_type ON redlight_violations(violation_type);
CREATE INDEX IF NOT EXISTS idx_redlight_vehicle ON redlight_violations(vehicle_type);
CREATE INDEX IF NOT EXISTS idx_redlight_created ON redlight_violations(created_at DESC);

-- Grant permissions
GRANT ALL PRIVILEGES ON TABLE redlight_violations TO airflow;
GRANT USAGE, SELECT ON SEQUENCE redlight_violations_id_seq TO airflow;
