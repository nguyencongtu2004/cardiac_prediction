# 📋 DETAILED IMPLEMENTATION CHECKLIST
# Cardiac Prediction System - Improvement Roadmap

> **Hướng dẫn sử dụng**: Đánh dấu `[x]` khi hoàn thành task. Track progress bằng cách count số tasks completed.

## 📊 PROGRESS TRACKING

**Total Tasks**: 67
**Completed**: 0
**In Progress**: 0
**Remaining**: 67

---

## 🎯 PHASE 1: DATASET UPGRADE (Tuần 1 - 21 giờ)

📖 **Chi tiết**: [PHASE-1-DATASET-UPGRADE.md](PHASE-1-DATASET-UPGRADE.md)

### Step 1.1: Nghiên Cứu và Lựa Chọn Dataset (4 giờ)

- [ ] Đọc documentation MIMIC-III dataset
- [ ] Đọc documentation Heart Failure Clinical Records  
- [ ] Đọc documentation UCI Heart Disease dataset
- [ ] So sánh 3 datasets theo tiêu chí: size, features, licensing, complexity
- [ ] Tạo comparison document (markdown)
- [ ] Quyết định chính thức dataset sử dụng
- [ ] Document URL download và credentials setup

**Output**: `docs/dataset_comparison.md`, final decision documented

---

### Step 1.2: Download và Khảo Sát Dữ Liệu (2 giờ)

- [ ] Tạo Kaggle API credentials
- [ ] Configure `~/.kaggle/kaggle.json`
- [ ] Download Heart Failure Clinical Records dataset
- [ ] Verify file integrity
- [ ] Xem 20 rows đầu tiên
- [ ] Check data types và schema
- [ ] Identify missing values
- [ ] Phân tích class distribution
- [ ] Document ý nghĩa y học của từng feature

**Output**: Dataset tại `data/heart_failure_clinical_records_dataset.csv`, `docs/data_exploration.md`

---

### Step 1.3: Thiết Kế Feature Engineering Plan (3 giờ)

- [ ] Map features từ dataset mới sang schema hiện tại
- [ ] Thiết kế derived feature: age_group (Bucketizer)
- [ ] Thiết kế derived feature: kidney_risk (serum_creatinine threshold)
- [ ] Thiết kế derived feature: critical_ejection (ejection_fraction < 30%)
- [ ] Thiết kế derived feature: combo_risk (tổng hợp risk factors)
- [ ] Thiết kế derived feature: risk_interaction (ejection × creatinine)
- [ ] Document medical rationale cho mỗi derived feature
- [ ] Tạo mapping table: old schema → new schema
- [ ] Finalize schema: 18-20 features total

**Output**: `docs/feature_engineering_spec.md`, `docs/schema_mapping.md`

---

### Step 1.4: Implement Data Preprocessing Script (4 giờ)

- [ ] Tạo file `cardiac_data_prep_v2.py`
- [ ] Implement CSV loading logic
- [ ] Implement Bucketizer cho age groups
- [ ] Implement kidney_risk conditional logic
- [ ] Implement critical_ejection threshold
- [ ] Implement combo_risk calculation
- [ ] Implement risk_interaction feature
- [ ] Implement train/valid/test split (70/15/15) stratified
- [ ] Calculate class weight ratio
- [ ] Save to Parquet: train_data, valid_data, test_data
- [ ] Generate metadata.json với counts và distributions
- [ ] Test script execution
- [ ] Verify output files created

**Output**: `scripts/cardiac_data_prep_v2.py`, 3 parquet folders, `data/metadata.json`

---

### Step 1.5: Update Producer Schema (3 giờ)

- [ ] Analyze schema changes (old vs new)
- [ ] Identify breaking changes
- [ ] Create `cardiac_producer_v2.py`
- [ ] Update message schema (13 fields từ Heart Failure dataset)
- [ ] Update data types
- [ ] Update value ranges
- [ ] Test message generation
- [ ] Verify JSON serialization
- [ ] Test Kafka publishing
- [ ] Document schema trong markdown
- [ ] Provide example messages
- [ ] Add medical context cho fields

**Output**: `scripts/cardiac_producer_v2.py`, `docs/kafka_schema.md`

---

### Step 1.6: Update Streaming Inference Schema (3 giờ)

- [ ] Create `cardiac_streaming_inference_v2.py`
- [ ] Update Spark StructType với 13 fields mới
- [ ] Match data types với producer schema
- [ ] Update continuous features list
- [ ] Update binary features list
- [ ] Update VectorAssembler configuration
- [ ] Test producer → kafka integration
- [ ] Test kafka → spark consumption
- [ ] Verify schema parsing
- [ ] Check null value handling
- [ ] Document schema evolution strategy

**Output**: `scripts/cardiac_streaming_inference_v2.py`, integration test passed

---

### Step 1.7: End-to-End Pipeline Test (2 giờ)

- [ ] Execute data prep script
- [ ] Verify train/valid/test files created
- [ ] Check row counts match expectations
- [ ] Start Kafka producer với schema mới
- [ ] Start Spark streaming consumer
- [ ] Check PostgreSQL for predictions
- [ ] Validate no data corruption
- [ ] Validate feature distributions reasonable
- [ ] Validate no null values in critical fields
- [ ] Measure data prep execution time
- [ ] Measure streaming throughput
- [ ] Measure inference latency
- [ ] Document performance baseline

**Output**: `tests/phase1_test_report.md`, ✅ Phase 1 complete

---

## 🎯 PHASE 2: MODEL COMPLEXITY ENHANCEMENT (Tuần 1-2 - 23 giờ)

📖 **Chi tiết**: [PHASE-2-Model-Complexity-Enhancement.md](PHASE-2-Model-Complexity-Enhancement.md)

### Step 2.1: Advanced Feature Engineering Pipeline (4 giờ)

- [ ] Design 7-stage pipeline architecture
- [ ] Implement StringIndexer (nếu có categorical)
- [ ] Implement OneHotEncoder
- [ ] Implement VectorAssembler (continuous)
- [ ] Implement StandardScaler
- [ ] Implement PolynomialExpansion (degree=2)
- [ ] Implement ChiSqSelector (top 15 features)
- [ ] Implement final VectorAssembler
- [ ] Chain tất cả stages thành Pipeline
- [ ] Test output của từng stage
- [ ] Document pipeline flow diagram
- [ ] Write unit tests cho stages

**Output**: Advanced feature engineering pipeline, `docs/pipeline_architecture.md`

---

### Step 2.2: Multiple Classifier Implementation (5 giờ)

- [ ] Implement Random Forest configuration
- [ ] Implement GBT configuration
- [ ] Implement Logistic Regression configuration
- [ ] Train Random Forest trên training data
- [ ] Train GBT trên training data
- [ ] Train Logistic Regression trên training data
- [ ] Evaluate RF trên validation set
- [ ] Evaluate GBT trên validation set
- [ ] Evaluate LR trên validation set
- [ ] Compare metrics: AUC, F1, Precision, Recall
- [ ] Document strengths/weaknesses mỗi model
- [ ] Create comparison chart

**Output**: 3 trained models, `models/comparison_report.md`

---

### Step 2.3: Hyperparameter Tuning (6 giờ)

- [ ] Design param grid cho Random Forest (numTrees, maxDepth, minInstancesPerNode, maxBins)
- [ ] Calculate total combinations (~54)
- [ ] Setup CrossValidator (BinaryClassificationEvaluator, numFolds=5, parallelism=4)
- [ ] Set seed cho reproducibility
- [ ] Execute CrossValidator.fit() - **CHÚ Ý: 2-4 giờ execution**
- [ ] Monitor progress và resource usage
- [ ] Extract best model
- [ ] Extract best hyperparameters
- [ ] Compare tuned vs baseline model
- [ ] Visualize parameter importance
- [ ] Document tuning results

**Output**: Best tuned model, `models/hyperparameter_tuning_report.md`

---

### Step 2.4: Ensemble Strategy (4 giờ)

- [ ] Research ensemble options (Voting, Weighted Voting, Stacking)
- [ ] Design custom VotingClassifier logic (Spark không có built-in)
- [ ] Implement ensemble prediction logic (average probabilities)
- [ ] Train ensemble trên validation set
- [ ] Evaluate ensemble performance
- [ ] Compare ensemble vs best single model
- [ ] Assess computational overhead
- [ ] Make decision: ensemble hay single model?
- [ ] Document trade-offs

**Output**: Ensemble implementation hoặc final model selection, `models/ensemble_decision.md`

---

### Step 2.5: Model Evaluation (3 giờ)

- [ ] Evaluate final model trên test set
- [ ] Calculate AUC-ROC
- [ ] Calculate Precision, Recall, F1
- [ ] Generate Confusion Matrix
- [ ] Generate ROC curve plot
- [ ] Generate PR curve plot
- [ ] Extract feature importance (từ RF/GBT)
- [ ] Create feature importance chart
- [ ] Create prediction distribution histogram
- [ ] Compare với baseline model (old RF)
- [ ] Quantify improvement percentage
- [ ] Validate false positive rate
- [ ] Validate false negative rate
- [ ] Discuss medical implications

**Output**: `models/final_evaluation_report.md`, visualization plots

---

### Step 2.6: Update Training DAG (2 giờ)

- [ ] Modify `cardiac_model_retraining_dag.py`
- [ ] Update task gọi `cardiac_model_train_v2.py`
- [ ] Add task cho hyperparameter tuning
- [ ] Add task cho ensemble (nếu dùng)
- [ ] Implement model versioning (auto-increment)
- [ ] Create metadata file cho mỗi version
- [ ] Update promotion logic (threshold +0.02 AUC)
- [ ] Implement rollback mechanism
- [ ] Test DAG execution
- [ ] Verify model files saved correctly

**Output**: Updated `dags/cardiac_model_retraining_dag.py`, ✅ Phase 2 complete

---

## 🎯 PHASE 3: CONTINUOUS LEARNING (Tuần 2 - 23 giờ)

📖 **Chi tiết**: [PHASE-3-Continuous-Learning.md](PHASE-3-Continuous-Learning.md)

### Step 3.1: Database Schema (2 giờ)

- [ ] Design `cardiac_ground_truth` table schema
- [ ] Add columns: id, patient_id, prediction_time, predicted_label, risk_probability
- [ ] Add columns: actual_outcome, labeled_at, labeled_by, notes
- [ ] Create index trên patient_id
- [ ] Create index trên prediction_time
- [ ] Create index trên actual_outcome IS NULL
- [ ] Update `init_database.sql`
- [ ] Test SQL script trong Docker
- [ ] Verify table created successfully

**Output**: Updated `config/init_database.sql`, database schema verified

---

### Step 3.2: Streamlit Feedback UI (4 giờ)

- [ ] Design "Doctor Feedback" page interface
- [ ] Implement query lấy unlabeled predictions
- [ ] Implement JOIN giữa predictions và ground_truth
- [ ] Add filter: WHERE actual_outcome IS NULL
- [ ] Order by risk_probability DESC
- [ ] Display patient info + predicted risk
- [ ] Add dropdown: actual outcome selection
- [ ] Add text area cho notes
- [ ] Add submit button
- [ ] Implement INSERT logic vào ground_truth table
- [ ] Set labeled_at = NOW()
- [ ] Set labeled_by = username
- [ ] Show success message
- [ ] Implement page refresh
- [ ] Test feedback submission end-to-end

**Output**: Updated `streamlit/streamlit_app.py`, feedback UI working

---

### Step 3.3: Feedback Collection Strategy (2 giờ)

- [ ] Define labeling workflow (ai, khi nào, tiêu chí)
- [ ] Document labeling criteria
- [ ] Create script simulate feedback data
- [ ] Generate realistic label distribution
- [ ] Insert simulated data vào ground_truth
- [ ] Create monitoring queries
- [ ] Track % predictions labeled
- [ ] Track label distribution
- [ ] Setup alert cho low labeling rate

**Output**: `docs/labeling_workflow.md`, `scripts/simulate_feedback.py`

---

### Step 3.4: Merge Feedback Script (4 giờ)

- [ ] Create `merge_feedback_retrain.py`
- [ ] Implement JDBC load từ PostgreSQL
- [ ] Extract feedback data (WHERE actual_outcome IS NOT NULL)
- [ ] Transform sang Spark DataFrame
- [ ] Load historical training data
- [ ] Add weight column (feedback=3.0, historical=1.0)
- [ ] Union datasets
- [ ] Remove duplicates
- [ ] Validate schema
- [ ] Check missing values
- [ ] Log data statistics
- [ ] Save merged dataset (parquet)
- [ ] Test script execution

**Output**: `scripts/merge_feedback_retrain.py`, merged dataset tested

---

### Step 3.5: Incremental Retraining Logic (5 giờ)

- [ ] Design retraining trigger conditions
- [ ] Decide: time-based + data-based
- [ ] Load merged dataset
- [ ] Apply feature engineering pipeline
- [ ] Apply model training pipeline
- [ ] Evaluate trên fresh test set (từ feedback gần nhất)
- [ ] Compare new vs current model (AUC, F1, Recall)
- [ ] Define promotion criteria (AUC +0.01, Recall không giảm >2%)
- [ ] Implement promotion logic
- [ ] Save new model với version number
- [ ] Test incremental retraining end-to-end

**Output**: Incremental retraining logic in `merge_feedback_retrain.py`

---

### Step 3.6: Incremental Retrain DAG (3 giờ)

- [ ] Create `cardiac_incremental_retrain_dag.py`
- [ ] Set schedule: @weekly
- [ ] Add task: check_feedback_availability (Python sensor)
- [ ] Add task: merge_feedback_data (spark-submit)
- [ ] Add task: retrain_model (spark-submit)
- [ ] Add task: evaluate_new_model (Python)
- [ ] Add task: compare_and_promote (Python)
- [ ] Add task: update_production_model (Bash)
- [ ] Implement sensor logic (check count > 50)
- [ ] Add email notification when retrain starts
- [ ] Add email when model promoted
- [ ] Add alert nếu retrain fails
- [ ] Test DAG execution manually
- [ ] Verify tasks chạy đúng sequence

**Output**: `dags/cardiac_incremental_retrain_dag.py`, DAG tested

---

### Step 3.7: Continuous Learning Validation (3 giờ)

- [ ] Simulate Day 0: Train baseline model
- [ ] Simulate Day 1-7: Generate predictions
- [ ] Simulate Day 7: Label 100 predictions
- [ ] Trigger incremental retrain → Model v2
- [ ] Verify Model v2 uses feedback data
- [ ] Simulate Day 8-14: Predictions với v2
- [ ] Simulate Day 14: Label 100 more predictions
- [ ] Trigger retrain → Model v3
- [ ] Plot AUC over versions (v1 → v2 → v3)
- [ ] Validate improvement hoặc stability
- [ ] Check no data leakage
- [ ] Verify model versions tracked correctly
- [ ] Document end-to-end test

**Output**: `tests/continuous_learning_validation.md`, ✅ Phase 3 complete

---

## 🎯 PHASE 4: MONITORING & EXPLAINABILITY (Tuần 3 - 26 giờ)

📖 **Chi tiết**: [PHASE-4-Monitoring-&-Explainability.md](PHASE-4-Monitoring-&-Explainability.md)

### Step 4.1: MLflow Integration (4 giờ)

- [ ] Add MLflow service to `docker-compose.yaml`
- [ ] Configure backend store: PostgreSQL
- [ ] Configure artifact store: `/mlflow/artifacts`
- [ ] Expose port 5000
- [ ] Update training script: import mlflow
- [ ] Set tracking URI: `http://mlflow:5000`
- [ ] Create experiment: "cardiac_admission_prediction"
- [ ] Add mlflow.start_run() wrapper
- [ ] Log parameters (numTrees, maxDepth, etc.)
- [ ] Log metrics (AUC, F1, Precision, Recall)
- [ ] Log artifacts (confusion matrix, ROC curve)
- [ ] Log model: mlflow.spark.log_model()
- [ ] Tag runs với metadata
- [ ] Test MLflow UI: http://localhost:5000
- [ ] Verify experiments visible
- [ ] Verify runs tracked
- [ ] Verify artifacts downloadable

**Output**: MLflow service running, training logs to MLflow

---

### Step 4.2: SHAP Explainability (5 giờ)

- [ ] Research SHAP compatibility với Spark models
- [ ] Create `model_explainer.py`
- [ ] Load trained Spark model
- [ ] Extract RF/GBT classifier stage
- [ ] Create SHAP TreeExplainer
- [ ] Implement explain_prediction() function
- [ ] Generate SHAP values cho patient
- [ ] Generate waterfall plot
- [ ] Generate force plot
- [ ] Add "Explanation" section trong Streamlit patient detail
- [ ] Add "Generate Explanation" button
- [ ] On click: call explainer
- [ ] Display waterfall plot
- [ ] Display feature values table
- [ ] Test với high-risk patient
- [ ] Verify medical sense
- [ ] Verify top features align với domain knowledge

**Output**: `scripts/model_explainer.py`, SHAP in dashboard

---

### Step 4.3: Concept Drift Detection (4 giờ)

- [ ] Design drift detection strategy (KS test, Chi-square)
- [ ] Create `drift_detector.py`
- [ ] Load training data feature statistics
- [ ] Implement collect_recent_streaming_data()
- [ ] Implement KS test cho continuous features
- [ ] Implement Chi-square test cho binary features
- [ ] Set threshold p-value < 0.05
- [ ] Identify drifted features
- [ ] Create `cardiac_drift_monitoring_dag.py`
- [ ] Set schedule: @daily
- [ ] Add task: collect_recent_data (PostgreSQL query)
- [ ] Add task: compute_statistics (Spark)
- [ ] Add task: detect_drift (run tests)
- [ ] Add task: alert_if_drift (email/Slack)
- [ ] Add task: trigger_retrain (TriggerDagRunOperator)
- [ ] Simulate drift (modify producer)
- [ ] Verify drift detected
- [ ] Verify alert sent
- [ ] Verify retrain triggered

**Output**: `scripts/drift_detector.py`, `dags/cardiac_drift_monitoring_dag.py`

---

### Step 4.4: Dashboard - Model Performance Page (3 giờ)

- [ ] Design "Model Performance Timeline" page
- [ ] Add page to Streamlit navigation
- [ ] Query MLflow tracking server (mlflow.search_runs)
- [ ] Extract metrics (AUC, F1) + timestamps
- [ ] Query PostgreSQL prediction statistics
- [ ] Create AUC-ROC line chart over time (Plotly)
- [ ] Create F1 Score line chart
- [ ] Create Precision/Recall line chart
- [ ] Create model versions history table
- [ ] Add confusion matrix comparison (current vs previous)
- [ ] Test page navigation
- [ ] Verify charts display correctly
- [ ] Verify interactivity works

**Output**: "Model Performance" page in dashboard

---

### Step 4.5: Dashboard - Feature Analysis Page (3 giờ)

- [ ] Design "Feature Analysis" page
- [ ] Add page to navigation
- [ ] Load current production model
- [ ] Extract feature importance
- [ ] Create feature importance bar chart (top 15)
- [ ] Load recent predictions từ PostgreSQL
- [ ] Compute correlation matrix
- [ ] Create correlation heatmap (Plotly)
- [ ] Load training data statistics
- [ ] Create distribution comparison histograms
- [ ] Compute KS statistic per feature
- [ ] Display distribution shift indicators
- [ ] Test page functionality
- [ ] Verify visualizations

**Output**: "Feature Analysis" page in dashboard

---

### Step 4.6: Dashboard - System Health Page (3 giờ)

- [ ] Design "System Health" page
- [ ] Add Kafka metrics section
- [ ] Query Kafka topic lag (kafka-python AdminClient)
- [ ] Query messages per second
- [ ] Add Spark streaming metrics section
- [ ] Query batch processing time
- [ ] Query records per batch
- [ ] Add database metrics section
- [ ] Query predictions count (total, 24h)
- [ ] Query ground truth labeling rate
- [ ] Query table sizes
- [ ] Add Airflow DAG status section
- [ ] Query DAG last run times
- [ ] Query success/failure rates
- [ ] Create real-time gauges
- [ ] Create trend line charts
- [ ] Add status indicators (green/yellow/red)
- [ ] Add alert badges
- [ ] Set auto-refresh (30 seconds)
- [ ] Test auto-refresh

**Output**: "System Health" page in dashboard

---

### Step 4.7: Final Integration Testing (4 giờ)

- [ ] Simulate tuần 1 operation
- [ ] Day 0: Train baseline model
- [ ] Day 1-3: Stream predictions
- [ ] Day 3: Label predictions
- [ ] Day 4: Run drift detector → no drift
- [ ] Day 5: Weekly retrain triggers → Model v2
- [ ] Day 6-7: Stream với Model v2
- [ ] Verify real medical dataset loaded ✅
- [ ] Verify Model AUC > 0.85 ✅
- [ ] Verify feedback loop working ✅
- [ ] Verify MLflow tracking ✅
- [ ] Verify SHAP explanations ✅
- [ ] Verify drift detection ✅
- [ ] Verify 5 dashboard pages functional ✅
- [ ] Load test: 1000 messages/second
- [ ] Check Kafka lag
- [ ] Check Spark throughput
- [ ] Check database load
- [ ] Update README với new features
- [ ] Update architecture diagram
- [ ] Create user guide cho dashboard
- [ ] Create deployment guide

**Output**: `tests/final_system_test_report.md`, ✅ Phase 4 complete

---

## 📚 DOCUMENTATION TASKS

### Essential Documentation

- [ ] Update main README.md với system overview
- [ ] Document architecture diagram (draw.io hoặc mermaid)
- [ ] Create user guide cho 5 dashboard pages
- [ ] Document medical rationale cho features
- [ ] Create deployment guide (Docker setup, credentials, etc.)
- [ ] Document API endpoints (nếu có)
- [ ] Create troubleshooting guide
- [ ] Document monitoring alerts và thresholds

### Code Documentation

- [ ] Add docstrings cho tất cả Python functions
- [ ] Add comments cho complex logic
- [ ] Document Spark configurations
- [ ] Document Kafka topics và schemas
- [ ] Document database schema với ERD

### Presentation Materials

- [ ] Create demo script
- [ ] Prepare slides highlighting improvements
- [ ] Create before/after comparison charts
- [ ] Prepare Q&A cho common questions
- [ ] Record demo video (optional)

---

## ✅ FINAL VALIDATION CHECKLIST

### Functional Requirements

- [ ] Real medical dataset successfully integrated
- [ ] Model AUC-ROC > 0.85 achieved
- [ ] Ensemble model hoặc tuned model deployed
- [ ] Feedback loop: predict → label → retrain → deploy
- [ ] MLflow experiment tracking working
- [ ] SHAP explanations available trong UI
- [ ] Drift detection alerts functional
- [ ] Dashboard có đầy đủ 5 pages:
  - [ ] Real-time Predictions
  - [ ] Model Performance Timeline
  - [ ] Feature Analysis
  - [ ] System Health
  - [ ] Doctor Feedback

### Performance Requirements

- [ ] Streaming throughput > 100 messages/second
- [ ] Inference latency < 500ms
- [ ] No Kafka lag accumulation
- [ ] Database queries < 2 seconds
- [ ] Dashboard load time < 3 seconds

### Quality Requirements

- [ ] No critical bugs
- [ ] All DAGs execute successfully
- [ ] No data loss trong streaming
- [ ] Predictions stored correctly
- [ ] Model versions tracked accurately

### Documentation Requirements

- [ ] README complete và accurate
- [ ] Architecture diagram created
- [ ] User guide written
- [ ] Deployment guide tested
- [ ] Code well-commented

---

## 🎯 SUCCESS METRICS

**Phase 1 Success**: Real dataset integrated, 18+ features, pipeline tested ✅  
**Phase 2 Success**: Model AUC > 0.85, CV tuning complete, versioning working ✅  
**Phase 3 Success**: Feedback loop validated, incremental learning proven ✅  
**Phase 4 Success**: Full monitoring stack deployed, explainability working ✅

**Overall Success**: System scores 46/50 (92%) trên 5 yêu cầu đề tài 🎉
