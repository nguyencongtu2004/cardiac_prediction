-- init_database.sql
-- ======================================
-- Script khởi tạo database schema cho Cardiac Prediction System
-- Chạy script này để tạo bảng cần thiết trong PostgreSQL

-- 1. Bảng lưu kết quả dự đoán từ streaming
CREATE TABLE IF NOT EXISTS cardiac_predictions (
    id SERIAL PRIMARY KEY,
    age INTEGER,
    sex INTEGER,
    heart_rate FLOAT,
    bp_sys FLOAT,
    bp_dia FLOAT,
    spo2 FLOAT,
    resp_rate FLOAT,
    hypertension_history INTEGER,
    diabetes_history INTEGER,
    heart_failure_history INTEGER,
    smoking_status INTEGER,
    result_class INTEGER, -- 0: Negative, 1: Positive
    prediction_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    model_version VARCHAR(255)
);

-- Tạo index cho tăng tốc query
CREATE INDEX IF NOT EXISTS idx_cardiac_predictions_time ON cardiac_predictions(prediction_time DESC);

-- 2. Bảng lưu thông tin mô hình (Model Registry)
CREATE TABLE IF NOT EXISTS model_registry (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(255) UNIQUE NOT NULL,
    timestamp TIMESTAMP,
    metrics JSONB,
    is_production BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index cho model registry
CREATE INDEX IF NOT EXISTS idx_model_registry_production ON model_registry(is_production, created_at DESC);

-- 3. Bảng lưu lịch sử training (Training History)
CREATE TABLE IF NOT EXISTS training_history (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(255) REFERENCES model_registry(model_name),
    training_started_at TIMESTAMP,
    training_completed_at TIMESTAMP,
    training_duration_minutes INTEGER,
    num_samples INTEGER,
    epochs INTEGER,
    learning_rate FLOAT,
    batch_size INTEGER,
    final_metrics JSONB,
    status VARCHAR(50),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. View để xem thống kê nhanh
CREATE OR REPLACE VIEW model_performance_summary AS
SELECT 
    model_name,
    timestamp as trained_at,
    is_production,
    metrics->>'Accuracy' as accuracy,
    metrics->>'F1' as f1_score,
    created_at
FROM model_registry
ORDER BY created_at DESC;

-- 5. Function để auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger cho model_registry
CREATE TRIGGER update_model_registry_updated_at
    BEFORE UPDATE ON model_registry
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE cardiac_predictions IS 'Stores cardiac admission predictions from streaming pipeline';
COMMENT ON TABLE model_registry IS 'Registry of all trained models with metrics and production status';
COMMENT ON TABLE training_history IS 'Complete history of all training runs';
