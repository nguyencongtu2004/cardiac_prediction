# Kế Hoạch Cải Thiện Chi Tiết - Cardiac Prediction System

> **Mục tiêu tổng quát**: Nâng điểm hệ thống từ 50-60% lên 90-95% theo 5 yêu cầu đề tài trong vòng 3 tuần

---

## 📊 TỔNG QUAN ROADMAP

### Bảng Điểm Hiện Tại vs Mục Tiêu

| Yêu Cầu | Điểm Hiện Tại | Mục Tiêu | Độ Ưu Tiên |
|---------|---------------|----------|------------|
| YC1: Làm theo thầy dạy | 8/10 | 10/10 | Trung bình |
| YC2: Model phức tạp | 5/10 | 9/10 | **CAO** |
| YC3: Continuous learning | 4/10 | 9/10 | **CAO** |
| YC4: Ứng dụng thực tế | 7/10 | 9/10 | Trung bình |
| YC5: Dataset chất lượng | 3/10 | 9/10 | **QUAN TRỌNG NHẤT** |

### Timeline Tổng Thể

```
Tuần 1: Dataset + Feature Engineering + Model Complexity
Tuần 2: Continuous Learning + Feedback Loop
Tuần 3: Monitoring + Explainability + Production Polish
```

### 📁 Chi Tiết Từng Phase

| Phase | Timeline | Document Chi Tiết | Độ Ưu Tiên |
|-------|----------|-------------------|------------|
| **Phase 1** | Tuần 1 (21 giờ) | [PHASE-1-DATASET-UPGRADE.md](PHASE-1-DATASET-UPGRADE.md) | P0 - BẮT BUỘC |
| **Phase 2** | Tuần 1-2 (23 giờ) | [PHASE-2-Model-Complexity-Enhancement.md](PHASE-2-Model-Complexity-Enhancement.md) | P0 - BẮT BUỘC |
| **Phase 3** | Tuần 2 (23 giờ) | [PHASE-3-Continuous-Learning.md](PHASE-3-Continuous-Learning.md) | P0 - BẮT BUỘC |
| **Phase 4** | Tuần 3 (26 giờ) | [PHASE-4-Monitoring-&-Explainability.md](PHASE-4-Monitoring-&-Explainability.md) | P1 - NÊN LÀM |

**Tổng effort ước tính**: ~93 giờ (3 tuần × 8 giờ/ngày × 4 ngày/tuần)


## 📊 SUCCESS CRITERIA & EXPECTED OUTCOMES

### Quantitative Metrics

| Metric | Before | Target After | Measurement Method |
|--------|--------|--------------|-------------------|
| Dataset Size | 5K synthetic | 299+ real medical | Row count |
| Number of Features | 11 basic | 18-20 engineered | Feature list |
| Model AUC-ROC | ~0.75 | >0.85 | Test set evaluation |
| Model Type | Basic RF | Ensemble + CV tuning | Model architecture |
| Hyperparameter Tuning | None | CrossValidator 5-fold | Training logs |
| Continuous Learning | Static daily | Incremental feedback | Retrain frequency |
| Explainability | None | SHAP values | UI presence |
| Monitoring | Basic logs | MLflow + Drift | Dashboard pages |

### Qualitative Improvements

1. **Dataset Quality**
   - ✅ Real medical data với clinical relevance
   - ✅ Features có ý nghĩa y học rõ ràng
   - ✅ Documented medical rationale

2. **Model Sophistication**
   - ✅ Advanced feature engineering (polynomial, interactions)
   - ✅ Multiple classifiers compared
   - ✅ Systematic hyperparameter tuning
   - ✅ Production-grade model selection

3. **Continuous Learning**
   - ✅ Feedback loop hoàn chỉnh
   - ✅ Incremental learning từ streaming data
   - ✅ Auto-trigger retrain khi cần

4. **Production Readiness**
   - ✅ Comprehensive monitoring
   - ✅ Explainable predictions
   - ✅ Drift detection và auto-response
   - ✅ Multi-page dashboard

### Final Scoring Prediction

| Yêu Cầu | Điểm Dự Kiến | Rationale |
|---------|--------------|-----------|
| YC1: Làm theo thầy dạy | 10/10 | Full stack Big Data + best practices |
| YC2: Model phức tạp | 9/10 | Ensemble + CV + feature engineering |
| YC3: Continuous learning | 9/10 | Feedback loop + incremental retrain |
| YC4: Ứng dụng thực tế | 9/10 | Production dashboard + explainability |
| YC5: Dataset chất lượng | 9/10 | Real medical data + documentation |
| **TỔNG** | **46/50 (92%)** | Excellent system |

---

## 🚨 RISK MITIGATION

### Potential Risks

1. **Risk: MIMIC-III approval delay**
   - **Mitigation**: Use Heart Failure Kaggle dataset as backup
   - **Timeline impact**: Không ảnh hưởng nếu dùng backup

2. **Risk: CrossValidator takes too long**
   - **Mitigation**: Reduce param grid size, tăng parallelism
   - **Fallback**: Manual hyperparameter search

3. **Risk: SHAP không support Spark models directly**
   - **Mitigation**: Extract model, convert sang scikit-learn compatible format
   - **Fallback**: Use built-in feature importance

4. **Risk: Không đủ feedback data để test continuous learning**
   - **Mitigation**: Simulate feedback data với realistic distribution
   - **Acceptance**: Demo với simulated data là acceptable

### Contingency Plans

- **If tuần 1 overrun**: Prioritize dataset + basic model, defer advanced features
- **If tuần 2 overrun**: Simplify continuous learning (time-based only, skip drift detection)
- **If tuần 3 overrun**: Focus on core monitoring, defer nice-to-have features

---

## 📝 DELIVERABLES CHECKLIST

### Phase 1 Deliverables
- [ ] Real medical dataset integrated (Heart Failure or MIMIC-III)
- [ ] 18-20 engineered features documented
- [ ] Data preprocessing script v2 working
- [ ] Producer + streaming inference updated
- [ ] End-to-end pipeline test passed

### Phase 2 Deliverables
- [ ] Advanced feature engineering pipeline implemented
- [ ] 3 classifiers trained và compared
- [ ] CrossValidator hyperparameter tuning completed
- [ ] Best model selected (AUC > 0.85)
- [ ] Model versioning implemented

### Phase 3 Deliverables
- [ ] `cardiac_ground_truth` table created
- [ ] Feedback UI trong Streamlit working
- [ ] Merge feedback script implemented
- [ ] Incremental retrain DAG created
- [ ] Continuous learning cycle validated

### Phase 4 Deliverables
- [ ] MLflow integration complete
- [ ] SHAP explainability trong dashboard
- [ ] Drift detection DAG implemented
- [ ] 5 dashboard pages complete:
  - [ ] Real-time Predictions
  - [ ] Model Performance Timeline
  - [ ] Feature Analysis
  - [ ] System Health
  - [ ] Doctor Feedback
- [ ] Final system test passed

### Documentation Deliverables
- [ ] Updated README
- [ ] Architecture diagram
- [ ] User guide cho dashboard
- [ ] Medical rationale document
- [ ] Deployment guide

---

## 🎓 LEARNING OUTCOMES

Sau khi hoàn thành roadmap này, bạn sẽ:

1. ✅ **Master Spark MLlib** - Advanced feature engineering, ensemble models, hyperparameter tuning
2. ✅ **Production ML Pipeline** - End-to-end từ data prep đến monitoring
3. ✅ **Continuous Learning** - Implement feedback loop và incremental retraining
4. ✅ **ML Explainability** - SHAP values cho medical predictions
5. ✅ **Big Data Best Practices** - Orchestration, versioning, monitoring, drift detection
6. ✅ **Real-world Medical ML** - Work với real clinical data, understand domain constraints

