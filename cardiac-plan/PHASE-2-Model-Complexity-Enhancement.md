
## 🎯 PHASE 2: MODEL COMPLEXITY ENHANCEMENT (Tuần 1-2)

### Mục tiêu Phase 2
- Nâng cấp model từ basic Random Forest lên ensemble phức tạp
- Implement hyperparameter tuning với CrossValidator
- Tăng AUC-ROC từ ~0.75 lên >0.85

---

### BƯỚC 2.1: Advanced Feature Engineering Pipeline (4 giờ)

#### Nhiệm vụ chính:

1. **Thiết kế Pipeline nâng cao**
   - **Stage 1**: StringIndexer cho categorical features (nếu có)
   - **Stage 2**: OneHotEncoder cho encoded categories
   - **Stage 3**: VectorAssembler cho continuous features
   - **Stage 4**: StandardScaler để normalize
   - **Stage 5**: PolynomialExpansion (degree=2) cho interactions
   - **Stage 6**: ChiSqSelector để feature selection
   - **Stage 7**: Final VectorAssembler

2. **Document pipeline flow**
   - Vẽ diagram cho pipeline stages
   - Explain ý nghĩa từng transformation
   - Document input/output của mỗi stage

3. **Implement trong Spark**
   - Code từng stage riêng biệt
   - Test output của từng stage
   - Chain stages lại thành pipeline

#### Output:
- Pipeline architecture document
- Feature engineering pipeline implementation
- Unit tests cho từng stage

---

### BƯỚC 2.2: Multiple Classifier Implementation (5 giờ)

#### Nhiệm vụ chính:

1. **Implement 3 classifiers**
   - **Random Forest**: Baseline, robust
   - **Gradient Boosted Trees**: Potentially higher accuracy
   - **Logistic Regression**: Interpretable, fast

2. **Configure mỗi classifier**
   - Random Forest:
     - numTrees: 100-300
     - maxDepth: 10-20
     - minInstancesPerNode: 1-10
   - GBT:
     - maxIter: 50-100
     - maxDepth: 5-10
   - Logistic Regression:
     - maxIter: 100
     - regParam: 0.01-0.1
     - elasticNetParam: 0-1

3. **Train và evaluate riêng biệt**
   - Train mỗi model trên cùng training set
   - Evaluate trên validation set
   - So sánh metrics: AUC, F1, Precision, Recall
   - Document strengths/weaknesses của mỗi model

#### Output:
- 3 trained models với metrics
- Comparison report
- Recommendation model nào tốt nhất

---

### BƯỚC 2.3: Hyperparameter Tuning với CrossValidator (6 giờ)

#### Nhiệm vụ chính:

1. **Thiết kế param grid**
   - Xác định hyperparameters quan trọng nhất
   - Define ranges hợp lý cho mỗi param
   - Balance grid size vs computation time
   - **Ví dụ cho Random Forest**:
     - numTrees: [100, 200, 300]
     - maxDepth: [10, 15, 20]
     - minInstancesPerNode: [1, 5, 10]
     - maxBins: [32, 64]
     - → Total: 3×3×3×2 = 54 combinations

2. **Setup CrossValidator**
   - Chọn evaluator (BinaryClassificationEvaluator với AUC metric)
   - numFolds: 5 (trade-off accuracy vs time)
   - parallelism: 4 (tận dụng multi-core)
   - Seed cho reproducibility

3. **Run hyperparameter tuning**
   - Execute CrossValidator.fit()
   - Monitor progress và resource usage
   - **Lưu ý**: Quá trình này có thể mất 2-4 giờ

4. **Analyze results**
   - Extract best model
   - Compare với baseline (model không tune)
   - Document best hyperparameters
   - Visualize parameter importance

#### Output:
- Best model từ CrossValidator
- Hyperparameter tuning report
- Comparison chart: tuned vs baseline

---

### BƯỚC 2.4: Ensemble Strategy (4 giờ)

#### Nhiệm vụ chính:

1. **Evaluate ensemble options**
   - **Option 1**: Voting Classifier (majority vote)
   - **Option 2**: Weighted Voting (based on validation AUC)
   - **Option 3**: Stacking (train meta-model)

2. **Implement ensemble logic**
   - **Lưu ý**: Spark MLlib không có built-in VotingClassifier
   - Cần custom implementation:
     - Train multiple models riêng biệt
     - Combine predictions (average probabilities hoặc vote)
     - Evaluate ensemble performance

3. **Compare ensemble vs single model**
   - Test trên validation set
   - Check if ensemble improves AUC
   - Consider computational overhead

4. **Decision: Use ensemble or best single model?**
   - Trade-off: accuracy gain vs complexity
   - Production deployment considerations

#### Output:
- Ensemble implementation (nếu chọn ensemble)
- Performance comparison report
- Final model selection decision

---

### BƯỚC 2.5: Model Evaluation và Validation (3 giờ)

#### Nhiệm vụ chính:

1. **Comprehensive evaluation trên test set**
   - AUC-ROC
   - Precision, Recall, F1
   - Confusion Matrix
   - PR Curve (Precision-Recall)

2. **Generate evaluation artifacts**
   - Confusion matrix heatmap
   - ROC curve plot
   - Feature importance chart (từ RF/GBT)
   - Prediction distribution histogram

3. **Compare với baseline model**
   - Old model (basic RF 100 trees)
   - New model (tuned ensemble)
   - Quantify improvement

4. **Medical validation**
   - Check false positive rate (không muốn quá nhiều false alarms)
   - Check false negative rate (critical - miss high-risk patients)
   - Discuss trade-offs với domain experts

#### Output:
- Comprehensive evaluation report
- Visualization plots
- Comparison table: baseline vs new model
- Recommendation: Deploy new model?

---

### BƯỚC 2.6: Update Model Training DAG (2 giờ)

#### Nhiệm vụ chính:

1. **Modify `cardiac_model_retraining_dag.py`**
   - Update task để gọi script training mới
   - Add tasks cho hyperparameter tuning
   - Add tasks cho ensemble training (nếu dùng)

2. **Add model versioning**
   - Lưu model với version number tăng dần
   - Metadata file cho mỗi version (hyperparams, metrics, date)

3. **Update model promotion logic**
   - Compare new model với current production model
   - Auto-promote nếu AUC improvement > threshold (vd: +0.02)
   - Rollback mechanism nếu new model underperform

#### Output:
- Updated DAG file
- Model versioning strategy document
- Test DAG execution thành công
