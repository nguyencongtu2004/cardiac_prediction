
## 🎯 PHASE 3: CONTINUOUS LEARNING (Tuần 2)

### Mục tiêu Phase 3
- Implement feedback loop từ predictions về training
- Enable incremental learning từ streaming data
- Auto-retrain khi có đủ labeled data

---

### BƯỚC 3.1: Database Schema cho Feedback Loop (2 giờ)

#### Nhiệm vụ chính:

1. **Thiết kế bảng `cardiac_ground_truth`**
   - **Columns cần có**:
     - id (primary key)
     - patient_id (foreign key liên kết với predictions)
     - prediction_time (timestamp của prediction gốc)
     - predicted_label (0 hoặc 1)
     - risk_probability (probability từ model)
     - actual_outcome (NULL cho đến khi được gắn nhãn)
     - labeled_at (timestamp khi doctor gắn nhãn)
     - labeled_by (username của doctor)
     - notes (optional, ghi chú thêm)

2. **Create indexes**
   - Index trên patient_id (tra cứu nhanh)
   - Index trên prediction_time (sort by time)
   - Index trên actual_outcome IS NULL (query unlabeled records)

3. **Add vào init_database.sql**
   - SQL script tạo bảng
   - SQL script tạo indexes
   - Test script trong Docker container

#### Output:
- Updated `init_database.sql`
- Database schema document
- Verification: Bảng tạo thành công trong PostgreSQL

---

### BƯỚC 3.2: Streamlit Feedback UI (4 giờ)

#### Nhiệm vụ chính:

1. **Design feedback interface**
   - **New page**: "Doctor Feedback - Label Predictions"
   - **Features**:
     - List unlabeled predictions (top 20 by risk probability)
     - Show patient info + predicted risk
     - Dropdown để select actual outcome:
       - "Not Yet Known"
       - "Patient Admitted (High Risk Confirmed)"
       - "Patient Not Admitted (False Alarm)"
     - Text area cho notes
     - Submit button

2. **Implement query logic**
   - Query PostgreSQL để lấy predictions chưa có ground truth
   - Join giữa `cardiac_predictions` và `cardiac_ground_truth`
   - Filter: WHERE actual_outcome IS NULL
   - Order by risk_probability DESC

3. **Implement submission logic**
   - On submit button click:
     - Insert record vào `cardiac_ground_truth`
     - Update labeled_at = NOW()
     - Update labeled_by = current user
     - Show success message
     - Refresh page

4. **Add user authentication (optional)**
   - Simple username input
   - Hoặc integrate với LDAP/SSO nếu có

#### Output:
- Updated `streamlit_app.py` với feedback page
- Test: Doctor có thể gắn nhãn predictions thành công
- Screenshots của feedback UI

---

### BƯỚC 3.3: Feedback Data Collection Strategy (2 giờ)

#### Nhiệm vụ chính:

1. **Define labeling workflow**
   - **Ai gắn nhãn?**: Doctors, nurses, hoặc từ EMR system
   - **Khi nào gắn nhãn?**: 
     - Option 1: Sau 24-48 giờ (khi outcome rõ ràng)
     - Option 2: Định kỳ review batch predictions
   - **Tiêu chí gắn nhãn**: Patient admitted within 7 days = high risk confirmed

2. **Simulate feedback data (for testing)**
   - Script để tự động gắn nhãn test data
   - Random sampling với realistic distribution
   - Insert vào `cardiac_ground_truth`

3. **Monitor feedback data quality**
   - Track % predictions được gắn nhãn
   - Track label distribution (high risk vs normal)
   - Alert nếu labeling rate quá thấp

#### Output:
- Labeling workflow document
- Script simulate feedback data
- Monitoring query scripts

---

### BƯỚC 3.4: Merge Feedback Data Script (4 giờ)

#### Nhiệm vụ chính:

1. **Design data merging strategy**
   - **Input sources**:
     - Historical training data (parquet files)
     - New feedback data (từ PostgreSQL)
   - **Merging approach**:
     - Union hai datasets
     - Apply weighting: feedback data có weight cao hơn (vd: 3x)
     - Reason: Feedback data gần với distribution hiện tại hơn

2. **Implement merge script**
   - File: `merge_feedback_retrain.py`
   - **Steps**:
     1. Load feedback data từ PostgreSQL (JDBC)
     2. Transform sang Spark DataFrame
     3. Load historical training data
     4. Add weight column (1.0 vs 3.0)
     5. Union datasets
     6. Save merged dataset (parquet)

3. **Handle data quality**
   - Remove duplicates (same patient_id + prediction_time)
   - Validate data schema
   - Check for missing values
   - Log data statistics

#### Output:
- Script `merge_feedback_retrain.py`
- Test: Merge thành công với simulated feedback data
- Merged dataset statistics report

---

### BƯỚC 3.5: Incremental Retraining Logic (5 giờ)

#### Nhiệm vụ chính:

1. **Design retraining strategy**
   - **Trigger conditions**:
     - Option 1: Time-based (weekly)
     - Option 2: Data-based (khi có 1000+ new labels)
     - Option 3: Drift-based (khi detect concept drift)
   - **Recommend**: Kết hợp time-based + data-based

2. **Implement retraining pipeline**
   - Load merged dataset (historical + feedback)
   - Apply same feature engineering pipeline
   - Apply same model training pipeline (với hyperparameters đã tune)
   - Evaluate trên fresh test set (từ feedback data gần nhất)

3. **Model comparison logic**
   - Compare new model vs current production model
   - **Metrics to compare**:
     - AUC-ROC
     - F1 score
     - Recall (critical cho medical use case)
   - **Promotion criteria**:
     - AUC improvement > 0.01 AND
     - Recall không giảm > 2%

4. **Implement trong `merge_feedback_retrain.py`**
   - Reuse training logic từ `cardiac_model_train_v2.py`
   - Add comparison và promotion logic
   - Save new model với version number

#### Output:
- Incremental retraining logic implemented
- Model promotion criteria documented
- Test: Retrain thành công với merged data

---

### BƯỚC 3.6: Incremental Retraining DAG (3 giờ)

#### Nhiệm vụ chính:

1. **Create new DAG: `cardiac_incremental_retrain_dag.py`**
   - **Schedule**: @weekly hoặc manual trigger
   - **Tasks**:
     1. check_feedback_availability (Python sensor)
     2. merge_feedback_data (Bash: spark-submit)
     3. retrain_model (Bash: spark-submit)
     4. evaluate_new_model (Python)
     5. compare_and_promote (Python)
     6. update_production_model (Bash: copy files)

2. **Implement sensor task**
   - Check PostgreSQL:
     - Count records WHERE labeled_at > NOW() - INTERVAL '7 days'
   - If count < threshold (vd: 50), skip DAG run
   - Else, proceed with retraining

3. **Add monitoring và alerting**
   - Send email khi retrain starts
   - Send email khi new model promoted
   - Send alert nếu retrain fails

4. **Test DAG execution**
   - Trigger manually
   - Verify từng task chạy thành công
   - Check model files updated

#### Output:
- DAG file `cardiac_incremental_retrain_dag.py`
- DAG visible trong Airflow UI
- Test execution successful

---

### BƯỚC 3.7: Continuous Learning Validation (3 giờ)

#### Nhiệm vụ chính:

1. **Simulate continuous learning cycle**
   - **Day 0**: Train baseline model
   - **Day 1-7**: Generate predictions
   - **Day 7**: Doctor gắn nhãn batch 1 (100 predictions)
   - **Day 8**: Trigger incremental retrain → Model v2
   - **Day 8-14**: Generate predictions với Model v2
   - **Day 14**: Doctor gắn nhãn batch 2 (100 predictions)
   - **Day 15**: Trigger incremental retrain → Model v3

2. **Track model improvement**
   - Plot AUC over model versions (v1 → v2 → v3)
   - Expect to see improvement hoặc stability
   - Document insights

3. **Validate feedback loop hoàn chỉnh**
   - End-to-end test: prediction → feedback → retrain → deploy → predict again
   - Check không có data leakage
   - Verify model versions tracked correctly

#### Output:
- Simulation test report
- Model improvement chart
- Validation: ✅ Continuous learning working
