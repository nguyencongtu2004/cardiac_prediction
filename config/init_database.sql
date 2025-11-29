-- init_database.sql
-- ======================================
-- Script khởi tạo database schema cho ABSA Streaming System
-- Chạy script này để tạo bảng cần thiết trong PostgreSQL

-- 1. Bảng lưu kết quả ABSA từ streaming
CREATE TABLE IF NOT EXISTS absa_results (
    id SERIAL PRIMARY KEY,
    reviewtext TEXT,
    price VARCHAR(10),
    shipping VARCHAR(10),
    outlook VARCHAR(10),
    quality VARCHAR(10),
    size VARCHAR(10),
    shop_service VARCHAR(10),
    general VARCHAR(10),
    others VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tạo index cho tăng tốc query
CREATE INDEX IF NOT EXISTS idx_absa_results_created_at ON absa_results(created_at DESC);

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
    metrics->>'overall_score' as overall_score,
    metrics->>'mention_f1' as mention_f1,
    metrics->>'sentiment_f1' as sentiment_f1,
    created_at
FROM model_registry
ORDER BY created_at DESC;

-- 5. View thống kê cảm xúc theo aspect
CREATE OR REPLACE VIEW sentiment_statistics AS
SELECT 
    'Price' as aspect,
    price as sentiment,
    COUNT(*) as count
FROM absa_results
WHERE price IS NOT NULL AND price != ''
GROUP BY price
UNION ALL
SELECT 'Shipping', shipping, COUNT(*)
FROM absa_results
WHERE shipping IS NOT NULL AND shipping != ''
GROUP BY shipping
UNION ALL
SELECT 'Outlook', outlook, COUNT(*)
FROM absa_results
WHERE outlook IS NOT NULL AND outlook != ''
GROUP BY outlook
UNION ALL
SELECT 'Quality', quality, COUNT(*)
FROM absa_results
WHERE quality IS NOT NULL AND quality != ''
GROUP BY quality
UNION ALL
SELECT 'Size', size, COUNT(*)
FROM absa_results
WHERE size IS NOT NULL AND size != ''
GROUP BY size
UNION ALL
SELECT 'Shop_Service', shop_service, COUNT(*)
FROM absa_results
WHERE shop_service IS NOT NULL AND shop_service != ''
GROUP BY shop_service
UNION ALL
SELECT 'General', general, COUNT(*)
FROM absa_results
WHERE general IS NOT NULL AND general != ''
GROUP BY general
UNION ALL
SELECT 'Others', others, COUNT(*)
FROM absa_results
WHERE others IS NOT NULL AND others != ''
GROUP BY others;

-- 6. Function để auto-update updated_at timestamp
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

-- 7. Insert sample model entry (optional - cho testing)
-- INSERT INTO model_registry (model_name, timestamp, metrics, is_production)
-- VALUES (
--     'best_absa_hardshare.pt',
--     CURRENT_TIMESTAMP,
--     '{"overall_score": 0.85, "mention_f1": 0.82, "sentiment_f1": 0.88}'::jsonb,
--     TRUE
-- )
-- ON CONFLICT (model_name) DO NOTHING;

COMMENT ON TABLE absa_results IS 'Stores ABSA inference results from streaming pipeline';
COMMENT ON TABLE model_registry IS 'Registry of all trained models with metrics and production status';
COMMENT ON TABLE training_history IS 'Complete history of all training runs';
COMMENT ON VIEW model_performance_summary IS 'Quick summary view of model performance';
COMMENT ON VIEW sentiment_statistics IS 'Aggregated sentiment statistics by aspect';
