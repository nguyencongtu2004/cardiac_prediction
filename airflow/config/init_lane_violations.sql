-- Connect to traffic_monitoring database
\c traffic_monitoring

-- Create lane violations table
CREATE TABLE IF NOT EXISTS lane_violations (
    id SERIAL PRIMARY KEY,
    violation_id UUID UNIQUE NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    camera_id VARCHAR(100) NOT NULL,
    track_id INTEGER NOT NULL,
    frame_number INTEGER,
    violation_type VARCHAR(50) NOT NULL DEFAULT 'LANE_VIOLATION',
    vehicle_type VARCHAR(50),
    crossed_line_type VARCHAR(20),    -- 'solid' or 'dashed'
    line_id INTEGER,                   -- which lane line was crossed
    from_side VARCHAR(20),             -- 'left' or 'right'
    to_side VARCHAR(20),               -- 'left' or 'right'
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
CREATE INDEX IF NOT EXISTS idx_lane_timestamp ON lane_violations(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_lane_camera ON lane_violations(camera_id);
CREATE INDEX IF NOT EXISTS idx_lane_type ON lane_violations(violation_type);
CREATE INDEX IF NOT EXISTS idx_lane_vehicle ON lane_violations(vehicle_type);
CREATE INDEX IF NOT EXISTS idx_lane_line_type ON lane_violations(crossed_line_type);
CREATE INDEX IF NOT EXISTS idx_lane_created ON lane_violations(created_at DESC);

-- Grant permissions
GRANT ALL PRIVILEGES ON TABLE lane_violations TO airflow;
GRANT USAGE, SELECT ON SEQUENCE lane_violations_id_seq TO airflow;
