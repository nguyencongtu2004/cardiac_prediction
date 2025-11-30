
## 🎯 PHASE 4: MONITORING & EXPLAINABILITY (Tuần 3)

### Mục tiêu Phase 4
- Add MLflow cho experiment tracking
- Implement SHAP explainability
- Concept drift detection
- Enhanced monitoring dashboard

---

### BƯỚC 4.1: MLflow Integration (4 giờ)

#### Nhiệm vụ chính:

1. **Setup MLflow server**
   - Add MLflow service vào `docker-compose.yaml`
   - Configure backend store: PostgreSQL
   - Configure artifact store: Local filesystem `/mlflow/artifacts`
   - Expose port 5000

2. **Integrate MLflow vào training pipeline**
   - Import mlflow library
   - Set tracking URI: `http://mlflow:5000`
   - Create experiment: "cardiac_admission_prediction"
   - **For mỗi training run**:
     - `mlflow.start_run(run_name=f"model_v{version}")`
     - Log parameters: numTrees, maxDepth, dataset size, etc.
     - Log metrics: AUC, F1, Precision, Recall
     - Log artifacts: confusion matrix, ROC curve
     - Log model: `mlflow.spark.log_model(model, "cardiac_model")`

3. **Update model retraining DAG**
   - Add MLflow logging vào training tasks
   - Tag runs với metadata (production, experiment, incremental, etc.)

4. **Test MLflow UI**
   - Access http://localhost:5000
   - Verify experiments hiển thị
   - Verify runs tracked correctly
   - Verify artifacts downloadable

#### Output:
- MLflow service running
- Training pipeline logs to MLflow
- MLflow UI accessible và populated

---

### BƯỚC 4.2: SHAP Explainability (5 giờ)

#### Nhiệm vụ chính:

1. **Research SHAP cho Spark models**
   - **Challenge**: SHAP library primarily supports scikit-learn
   - **Solution**: Extract trained RF/GBT model từ Spark Pipeline → Convert sang format SHAP-compatible

2. **Implement model explainer**
   - File: `model_explainer.py`
   - **Steps**:
     1. Load trained Spark model
     2. Extract RF/GBT classifier stage
     3. Create SHAP TreeExplainer
     4. Define explain function:
        - Input: patient features (pandas DataFrame row)
        - Output: SHAP values array
        - Generate waterfall plot
        - Generate force plot

3. **Integrate vào Streamlit dashboard**
   - **New section** trong patient detail view: "Why is this patient high-risk?"
   - **Button**: "Generate Explanation"
   - **On click**:
     - Call explain function
     - Display waterfall plot (top features contributing to risk)
     - Show feature values table
     - Show model confidence

4. **Test explainability**
   - Select high-risk patient
   - Generate explanation
   - Verify plot makes medical sense
   - Verify top features align với medical knowledge

#### Output:
- `model_explainer.py` module
- SHAP explanation integrated vào Streamlit
- Screenshots của explanation UI
- Test: Explanations generated successfully

---

### BƯỚC 4.3: Concept Drift Detection (4 giờ)

#### Nhiệm vụ chính:

1. **Design drift detection strategy**
   - **Concept drift**: Distribution của input features thay đổi theo thời gian
   - **Impact**: Model trained trên old distribution → underperform trên new distribution
   - **Detection method**: Statistical tests (KS test, Chi-square test)

2. **Implement drift detector**
   - File: `drift_detector.py`
   - **Logic**:
     - Load training data statistics (feature distributions)
     - Collect recent streaming data (last 7 days)
     - For each continuous feature:
       - Run Kolmogorov-Smirnov test
       - If p-value < 0.05 → drift detected
     - For each binary feature:
       - Run Chi-square test
       - If p-value < 0.05 → drift detected

3. **Create drift monitoring DAG**
   - File: `cardiac_drift_monitoring_dag.py`
   - **Schedule**: Daily
   - **Tasks**:
     1. collect_recent_data (query PostgreSQL predictions)
     2. compute_statistics (Spark aggregations)
     3. detect_drift (run statistical tests)
     4. alert_if_drift (send email/Slack notification)
     5. trigger_retrain_if_needed (TriggerDagRunOperator)

4. **Test drift detection**
   - Simulate drift:
     - Modify producer để generate data với different distribution
     - Run for a few days
   - Verify drift detector triggers alert
   - Verify retrain DAG triggered

#### Output:
- `drift_detector.py` module
- `cardiac_drift_monitoring_dag.py`
- Drift detection tested và validated

---

### BƯỚC 4.4: Enhanced Dashboard - Model Performance Page (3 giờ)

#### Nhiệm vụ chính:

1. **Design new page: "Model Performance Timeline"**
   - **Sections**:
     - AUC-ROC over time (line chart)
     - F1 Score over time
     - Precision/Recall over time
     - Model versions history table
     - Confusion matrix comparison (current vs previous)

2. **Implement data fetching**
   - Query MLflow tracking server:
     - Get all runs từ experiment
     - Extract metrics (AUC, F1, etc.)
     - Extract timestamps
   - Query PostgreSQL:
     - Get prediction statistics per day
     - Get ground truth statistics

3. **Implement visualizations**
   - Use Plotly cho interactive charts
   - Line chart: X=date, Y=AUC, color by model version
   - Table: model version, train date, AUC, F1, promotion status

4. **Add to Streamlit navigation**
   - Update sidebar radio buttons
   - Link new page

#### Output:
- "Model Performance Timeline" page trong Streamlit
- Interactive charts working
- Historical data visualized correctly

---

### BƯỚC 4.5: Enhanced Dashboard - Feature Analysis Page (3 giờ)

#### Nhiệm vụ chính:

1. **Design new page: "Feature Analysis"**
   - **Sections**:
     - Feature importance chart (bar chart)
     - Feature correlation heatmap
     - Feature distribution comparison:
       - Training data vs Recent predictions
       - High-risk patients vs Low-risk patients
     - Individual feature trends over time

2. **Implement feature importance extraction**
   - Load current production model
   - Extract feature importance từ RF/GBT
   - Create bar chart: top 15 features

3. **Implement correlation heatmap**
   - Load recent predictions từ PostgreSQL
   - Compute correlation matrix (pandas)
   - Visualize với Plotly heatmap

4. **Implement distribution comparison**
   - Load training data statistics
   - Load recent predictions
   - For each feature:
     - Plot histogram comparison
     - Compute KS statistic (distribution difference)

#### Output:
- "Feature Analysis" page trong Streamlit
- Feature importance chart
- Correlation heatmap
- Distribution comparison plots

---

### BƯỚC 4.6: Enhanced Dashboard - System Health Page (3 giờ)

#### Nhiệm vụ chính:

1. **Design new page: "System Health Monitoring"**
   - **Sections**:
     - Kafka metrics:
       - Topic lag
       - Messages per second
       - Consumer group status
     - Spark streaming metrics:
       - Batch processing time
       - Records processed per batch
       - Memory usage
     - Database metrics:
       - Predictions count (total, last 24h)
       - Ground truth labeling rate
       - Table sizes
     - Airflow DAG status:
       - Last run times
       - Success/failure rates

2. **Implement metrics collection**
   - **Kafka**: Use kafka-python AdminClient to query metrics
   - **Spark**: Parse Spark UI metrics (hoặc log files)
   - **PostgreSQL**: Query system tables
   - **Airflow**: Query Airflow metadata database

3. **Implement visualization**
   - Real-time gauges cho throughput
   - Line charts cho trends
   - Status indicators (green/yellow/red)
   - Alert badges nếu có issues

4. **Auto-refresh**
   - Set Streamlit auto-refresh (every 30 seconds)
   - Show "Last updated: ..." timestamp

#### Output:
- "System Health" page trong Streamlit
- Real-time metrics displayed
- Auto-refresh working

---

### BƯỚC 4.7: Final Integration Testing (4 giờ)

#### Nhiệm vụ chính:

1. **End-to-end system test**
   - **Scenario**: Simulate 1 tuần hoạt động
   - **Day 0**: Train baseline model
   - **Day 1-3**: Streaming predictions
   - **Day 3**: Doctors label batch predictions
   - **Day 4**: Drift detector runs → no drift
   - **Day 5**: Weekly retrain triggers → Model v2
   - **Day 6-7**: Streaming với Model v2
   - **All pages**: Verify dashboard updates correctly

2. **Verification checklist**
   - ✅ Real medical dataset loaded
   - ✅ Model AUC > 0.85
   - ✅ Feedback loop: predict → label → retrain
   - ✅ MLflow tracking working
   - ✅ SHAP explanations displayed
   - ✅ Drift detection alert working
   - ✅ All 5 dashboard pages functional

3. **Performance testing**
   - Load test: 1000 messages/second
   - Verify no Kafka lag
   - Verify Spark keeps up
   - Verify database không overloaded

4. **Documentation final review**
   - README updated với new features
   - Architecture diagram updated
   - User guide cho dashboard pages
   - Deployment guide

#### Output:
- Complete system test report
- All checklist items passed
- Documentation updated
- System ready for demo/presentation
