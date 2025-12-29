-- Connect to traffic_monitoring database
\c traffic_monitoring

-- Create helmet violations table
CREATE TABLE IF NOT EXISTS helmet_violations (
    id SERIAL PRIMARY KEY,
    violation_id UUID UNIQUE NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    camera_id VARCHAR(100) NOT NULL,
    track_id INTEGER NOT NULL,
    frame_number INTEGER NOT NULL,
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
CREATE INDEX IF NOT EXISTS idx_violations_timestamp ON helmet_violations(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_violations_camera ON helmet_violations(camera_id);
CREATE INDEX IF NOT EXISTS idx_violations_track ON helmet_violations(track_id);
CREATE INDEX IF NOT EXISTS idx_violations_created ON helmet_violations(created_at DESC);

-- Grant permissions
GRANT ALL PRIVILEGES ON TABLE helmet_violations TO airflow;
GRANT USAGE, SELECT ON SEQUENCE helmet_violations_id_seq TO airflow;
