-- init_traffic_monitoring.sql
-- ======================================
-- Schema cho Real-Time Traffic Violation Monitoring System
-- Thêm vào PostgreSQL database đã có

-- 1. Bảng cameras - Danh sách camera giao thông
CREATE TABLE IF NOT EXISTS cameras (
    id SERIAL PRIMARY KEY,
    camera_id VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    location VARCHAR(500),
    api_id VARCHAR(100),           -- ID từ API HCM City
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Bảng camera_frames - Lưu thông tin frame đã xử lý
CREATE TABLE IF NOT EXISTS camera_frames (
    id SERIAL PRIMARY KEY,
    camera_id VARCHAR(100) REFERENCES cameras(camera_id),
    image_path VARCHAR(500),
    captured_at TIMESTAMP NOT NULL,
    processed BOOLEAN DEFAULT FALSE,
    detection_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Bảng traffic_violations - Các vi phạm được phát hiện
CREATE TABLE IF NOT EXISTS traffic_violations (
    id SERIAL PRIMARY KEY,
    camera_id VARCHAR(100),
    frame_id INTEGER REFERENCES camera_frames(id),
    violation_type VARCHAR(100) NOT NULL,    -- 'stop_line_crossing', 'red_light_running'
    vehicle_type VARCHAR(50) NOT NULL,       -- 'car', 'motorcycle', 'bus', 'truck'
    confidence FLOAT NOT NULL,
    position_x FLOAT,
    position_y FLOAT,
    bbox_x1 FLOAT,
    bbox_y1 FLOAT,
    bbox_x2 FLOAT,
    bbox_y2 FLOAT,
    image_path VARCHAR(500),
    detected_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Bảng detection_summary - Thống kê theo giờ
CREATE TABLE IF NOT EXISTS detection_summary (
    id SERIAL PRIMARY KEY,
    camera_id VARCHAR(100),
    hour_bucket TIMESTAMP NOT NULL,          -- Truncated to hour
    total_frames INTEGER DEFAULT 0,
    total_detections INTEGER DEFAULT 0,      -- Tổng object detected
    total_violations INTEGER DEFAULT 0,      -- Tổng vi phạm
    vehicle_breakdown JSONB,                 -- {"car": 10, "motorcycle": 5, ...}
    violation_breakdown JSONB,               -- {"stop_line_crossing": 3, ...}
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(camera_id, hour_bucket)
);

-- ======================================
-- INDEXES cho tối ưu query
-- ======================================

-- Frames
CREATE INDEX IF NOT EXISTS idx_frames_camera ON camera_frames(camera_id);
CREATE INDEX IF NOT EXISTS idx_frames_captured ON camera_frames(captured_at DESC);
CREATE INDEX IF NOT EXISTS idx_frames_unprocessed ON camera_frames(processed) WHERE processed = FALSE;

-- Violations
CREATE INDEX IF NOT EXISTS idx_violations_camera ON traffic_violations(camera_id);
CREATE INDEX IF NOT EXISTS idx_violations_time ON traffic_violations(detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_violations_type ON traffic_violations(violation_type);
CREATE INDEX IF NOT EXISTS idx_violations_vehicle ON traffic_violations(vehicle_type);

-- Summary
CREATE INDEX IF NOT EXISTS idx_summary_camera ON detection_summary(camera_id);
CREATE INDEX IF NOT EXISTS idx_summary_hour ON detection_summary(hour_bucket DESC);

-- ======================================
-- VIEWS cho Dashboard
-- ======================================

-- View: Violations trong 24h gần nhất
CREATE OR REPLACE VIEW recent_violations AS
SELECT 
    v.id,
    v.camera_id,
    c.name as camera_name,
    v.violation_type,
    v.vehicle_type,
    v.confidence,
    v.detected_at,
    v.image_path
FROM traffic_violations v
LEFT JOIN cameras c ON v.camera_id = c.camera_id
WHERE v.detected_at > NOW() - INTERVAL '24 hours'
ORDER BY v.detected_at DESC;

-- View: Thống kê theo camera
CREATE OR REPLACE VIEW camera_violation_stats AS
SELECT 
    c.camera_id,
    c.name as camera_name,
    c.location,
    COUNT(v.id) as total_violations_24h,
    COUNT(DISTINCT DATE_TRUNC('hour', v.detected_at)) as active_hours
FROM cameras c
LEFT JOIN traffic_violations v ON c.camera_id = v.camera_id 
    AND v.detected_at > NOW() - INTERVAL '24 hours'
WHERE c.is_active = TRUE
GROUP BY c.camera_id, c.name, c.location
ORDER BY total_violations_24h DESC;

-- View: Hourly trend
CREATE OR REPLACE VIEW hourly_violation_trend AS
SELECT 
    DATE_TRUNC('hour', detected_at) as hour,
    violation_type,
    COUNT(*) as count
FROM traffic_violations
WHERE detected_at > NOW() - INTERVAL '24 hours'
GROUP BY DATE_TRUNC('hour', detected_at), violation_type
ORDER BY hour DESC;

-- ======================================
-- SEED DATA: Cameras mặc định
-- ======================================
INSERT INTO cameras (camera_id, name, location, api_id, is_active) VALUES
    ('pasteur_le_duan', 'Pasteur - Lê Duẩn', 'Ngã tư Pasteur - Lê Duẩn, Q1', '662b83ff1afb9c00172dcffb', TRUE),
    ('nguyen_thi_minh_khai', 'Nguyễn Thị Minh Khai', 'Đường Nguyễn Thị Minh Khai, Q3', '582e95d2a978d8001d60eacd', TRUE),
    ('hai_ba_trung', 'Hai Bà Trưng', 'Đường Hai Bà Trưng, Q1', '5826a04b061dda001b6fc009', TRUE),
    ('nam_ky_khoi_nghia', 'Nam Kỳ Khởi Nghĩa', 'Đường Nam Kỳ Khởi Nghĩa, Q1', '582e952aa978d8001d60eacc', TRUE)
ON CONFLICT (camera_id) DO NOTHING;

-- ======================================
-- COMMENTS
-- ======================================
COMMENT ON TABLE cameras IS 'Danh sách camera giao thông từ API HCM City';
COMMENT ON TABLE camera_frames IS 'Lưu thông tin các frame đã capture từ camera';
COMMENT ON TABLE traffic_violations IS 'Các vi phạm giao thông được phát hiện bởi YOLO';
COMMENT ON TABLE detection_summary IS 'Thống kê tổng hợp theo giờ cho dashboard';
