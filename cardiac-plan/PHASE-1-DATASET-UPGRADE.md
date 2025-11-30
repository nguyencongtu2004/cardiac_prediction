## 🎯 PHASE 1: DATASET UPGRADE (Tuần 1)

### Mục tiêu Phase 1
- Thay thế dữ liệu synthetic bằng dữ liệu y tế thực tế
- Tăng số lượng features từ 11 lên 18-20
- Đảm bảo data quality và medical relevance

---

### BƯỚC 1.1: Nghiên Cứu và Lựa Chọn Dataset (4 giờ)

#### Nhiệm vụ chính:
1. **Đọc tài liệu 3 dataset được đề xuất**
   - MIMIC-III
   - Heart Failure Clinical Records (Kaggle)
   - UCI Heart Disease

2. **So sánh các tiêu chí:**
   - Số lượng bệnh nhân
   - Số lượng features
   - Tính khả dụng (licensing, download speed)
   - Độ phức tạp integration
   - Medical relevance

3. **Quyết định lựa chọn:**
   - **Khuyến nghị**: Heart Failure Clinical Records
   - **Lý do**: 
     - Download nhanh (không cần approval)
     - Đủ features cho medical prediction
     - Dễ integrate vào pipeline hiện có
     - 299 patients đủ cho proof-of-concept

#### Output:
- Document so sánh 3 datasets (markdown file)
- Quyết định chính thức dataset sử dụng
- URL download và credentials setup

---

### BƯỚC 1.2: Download và Khảo Sát Dữ Liệu (2 giờ)

#### Nhiệm vụ chính:

1. **Setup Kaggle API**
   - Tạo API credentials từ Kaggle account
   - Configure kaggle.json file
   - Test connection

2. **Download dataset**
   - Download Heart Failure Clinical Records
   - Unzip vào thư mục `data/`
   - Verify file integrity

3. **Khảo sát cấu trúc dữ liệu**
   - Xem 20 rows đầu tiên
   - Check data types
   - Xác định missing values
   - Phân tích class distribution
   - Hiểu ý nghĩa y học của từng feature

#### Output:
- Dataset đã download trong `data/heart_failure_clinical_records_dataset.csv`
- Document khảo sát dữ liệu (số records, features, distribution)

---

### BƯỚC 1.3: Thiết Kế Feature Engineering Plan (3 giờ)

#### Nhiệm vụ chính:

1. **Mapping features từ dataset mới sang schema hiện tại**
   - Xác định features nào giữ nguyên
   - Xác định features nào cần transform
   - Xác định features nào bỏ

2. **Thiết kế derived features (5-7 features mới)**
   - **Age groups**: Phân loại độ tuổi (<50, 50-65, 65-75, >75)
   - **Kidney risk**: Indicator dựa trên serum_creatinine
   - **Critical ejection**: Flag khi ejection_fraction < 30%
   - **Combined risk score**: Tổng hợp các yếu tố nguy cơ
   - **Feature interactions**: ejection_fraction × serum_creatinine

3. **Thiết kế schema mới**
   - 13 features gốc từ dataset
   - 5-7 derived features
   - Total: 18-20 features
   - Document ý nghĩa y học của mỗi feature

#### Output:
- Feature engineering specification document
- Mapping table: old schema → new schema
- Medical rationale cho từng derived feature

---

### BƯỚC 1.4: Implement Data Preprocessing Script (4 giờ)

#### Nhiệm vụ chính:

1. **Tạo script preprocessing mới**
   - File: `cardiac_data_prep_v2.py`
   - Load CSV dataset
   - Apply feature transformations
   - Create derived features

2. **Feature transformations cần implement:**
   - **Bucketizer** cho age groups
   - **Conditional logic** cho kidney_risk
   - **Threshold-based** features
   - **Mathematical interactions**

3. **Train/Valid/Test split**
   - 70% training
   - 15% validation
   - 15% test
   - Stratified split để giữ class balance

4. **Class imbalance handling**
   - Tính class weight ratio
   - Lưu metadata về class distribution
   - Document strategy xử lý imbalance (SMOTE? Weighted loss?)

5. **Save processed data**
   - Parquet format cho train/valid/test
   - JSON metadata file (counts, distributions, feature names)

#### Output:
- Script `cardiac_data_prep_v2.py` hoàn chỉnh
- 3 parquet files: train_data, valid_data, test_data
- metadata.json với thông tin dataset

---

### BƯỚC 1.5: Update Producer Schema (3 giờ)

#### Nhiệm vụ chính:

1. **Analyze schema changes**
   - So sánh schema cũ vs schema mới
   - Identify breaking changes
   - Plan migration strategy

2. **Update Kafka message schema**
   - Modify `cardiac_producer_v2.py`
   - Update field names để match dataset mới
   - Update data types
   - Update value ranges

3. **Test message generation**
   - Generate sample messages với schema mới
   - Verify JSON serialization
   - Check message size
   - Test Kafka publishing

4. **Update schema documentation**
   - Document mỗi field trong message
   - Provide example messages
   - Medical context cho từng field

#### Output:
- `cardiac_producer_v2.py` với schema mới
- Schema documentation (markdown)
- Test script verify message generation

---

### BƯỚC 1.6: Update Streaming Inference Schema (3 giờ)

#### Nhiệm vụ chính:

1. **Update Spark StructType**
   - File: `cardiac_streaming_inference_v2.py`
   - Match với schema mới từ producer
   - Ensure data types compatible

2. **Update feature vector assembly**
   - List continuous features mới
   - List binary features mới
   - Update VectorAssembler configuration

3. **Test streaming pipeline**
   - Run producer với data mới
   - Consume từ Kafka
   - Verify schema parsing
   - Check for null values

4. **Handle schema evolution**
   - Strategy khi schema thay đổi trong tương lai
   - Backward compatibility considerations

#### Output:
- `cardiac_streaming_inference_v2.py` updated
- Integration test passed (producer → kafka → spark)
- Documentation về schema evolution strategy

---

### BƯỚC 1.7: End-to-End Data Pipeline Test (2 giờ)

#### Nhiệm vụ chính:

1. **Run complete pipeline**
   - Execute data prep script
   - Verify train/valid/test files created
   - Start producer với schema mới
   - Start streaming inference
   - Check PostgreSQL cho predictions

2. **Validation checks**
   - Row counts match expected
   - No data corruption
   - Feature distributions reasonable
   - No null values in critical fields

3. **Performance benchmarking**
   - Data prep execution time
   - Streaming throughput (messages/second)
   - Inference latency

#### Output:
- Test report document
- Performance metrics baseline
- Checklist: ✅ Phase 1 complete
