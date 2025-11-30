#!/usr/bin/env python3
"""
Cardiac Admission Model Training
Train ensemble models (RF + XGBoost + LogisticRegression) with SMOTE balancing
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when, lit
from pyspark.ml.feature import VectorAssembler, StandardScaler
from pyspark.ml.classification import RandomForestClassifier, LogisticRegression, GBTClassifier
from pyspark.ml import Pipeline
from pyspark.ml.evaluation import BinaryClassificationEvaluator, MulticlassClassificationEvaluator
import sys
import json
import pandas as pd
from imblearn.over_sampling import SMOTE
import numpy as np

def main():
    # Initialize Spark
    spark = SparkSession.builder \
        .appName("Cardiac Model Training") \
        .config("spark.driver.memory", "4g") \
        .getOrCreate()
    
    print(f"✅ Spark {spark.version} initialized")
    
    # Load metadata
    with open("/opt/airflow/projects/cardiac_prediction/data/metadata.json", "r") as f:
        metadata = json.load(f)
    
    class_weight = metadata["class_weight"]
    print(f"📊 Class weight for imbalance: {class_weight:.2f}")
    
    # Load data
    data_base = "/opt/airflow/projects/cardiac_prediction/data"
    train_data = spark.read.parquet(f"{data_base}/train_data")
    valid_data = spark.read.parquet(f"{data_base}/valid_data")
    
    print(f"\n✅ Data loaded:")
    print(f"   Train: {train_data.count()} records")
    print(f"   Valid: {valid_data.count()} records")
    
    # Define features
    CONTINUOUS_FEATURES = ['heart_rate', 'bp_sys', 'bp_dia', 'spo2', 'resp_rate', 'age']
    BINARY_FEATURES = ['sex', 'hypertension_history', 'diabetes_history', 'heart_failure_history', 'smoking_status']
    
    print(f"\n📋 Features: {len(CONTINUOUS_FEATURES)} continuous + {len(BINARY_FEATURES)} binary")
    
    # SMOTE Balancing (like in notebook)
    print("\n" + "="*80)
    print("APPLYING SMOTE BALANCING")
    print("="*80)
    
    # Convert to pandas for SMOTE
    train_pd = train_data.toPandas()
    X_train = train_pd[CONTINUOUS_FEATURES + BINARY_FEATURES]
    y_train = train_pd['admission_label']
    
    print(f"Original class distribution:")
    print(f"   Class 0: {(y_train == 0).sum()}")
    print(f"   Class 1: {(y_train == 1).sum()}")
    
    # Apply SMOTE
    smote = SMOTE(random_state=42)
    X_train_balanced, y_train_balanced = smote.fit_resample(X_train, y_train)
    
    print(f"\nBalanced class distribution:")
    print(f"   Class 0: {(y_train_balanced == 0).sum()}")
    print(f"   Class 1: {(y_train_balanced == 1).sum()}")
    
    # Convert back to Spark DataFrame
    balanced_pd = pd.DataFrame(X_train_balanced, columns=CONTINUOUS_FEATURES + BINARY_FEATURES)
    balanced_pd['admission_label'] = y_train_balanced
    train_data = spark.createDataFrame(balanced_pd)
    
    # Build Pipeline
    print("\n" + "="*80)
    print("BUILDING ML PIPELINE")
    print("="*80)
    
    # Stage 1: Assemble continuous features
    assembler_continuous = VectorAssembler(
        inputCols=CONTINUOUS_FEATURES,
        outputCol="continuous_vec"
    )
    
    # Stage 2: Scale continuous features
    scaler = StandardScaler(
        inputCol="continuous_vec",
        outputCol="scaled_continuous",
        withMean=True,
        withStd=True
    )
    
    # Stage 3: Combine scaled continuous + binary features
    assembler_final = VectorAssembler(
        inputCols=["scaled_continuous"] + BINARY_FEATURES,
        outputCol="features"
    )
    
    # Stage 4: Classifiers (tuned like in notebook)
    # Random Forest: n_estimators=100 (numTrees), max_depth=25, criterion=gini
    rf = RandomForestClassifier(
        featuresCol='features',
        labelCol='admission_label',
        numTrees=100,
        maxDepth=25,
        seed=42
    )
    
    # Logistic Regression: penalty=l2
    lr = LogisticRegression(
        featuresCol='features',
        labelCol='admission_label',
        regParam=0.01,
        elasticNetParam=0.0,  # L2 penalty
        maxIter=100
    )
    
    # Gradient Boosting Trees (similar to XGBoost)
    gbt = GBTClassifier(
        featuresCol='features',
        labelCol='admission_label',
        maxDepth=5,
        maxIter=100,
        seed=42
    )
    
    # Create pipelines for each model
    pipeline_rf = Pipeline(stages=[assembler_continuous, scaler, assembler_final, rf])
    pipeline_lr = Pipeline(stages=[assembler_continuous, scaler, assembler_final, lr])
    pipeline_gbt = Pipeline(stages=[assembler_continuous, scaler, assembler_final, gbt])
    
    print("✅ Pipeline stages:")
    print("   1. VectorAssembler (continuous)")
    print("   2. StandardScaler")
    print("   3. VectorAssembler (final)")
    print("   4. Three models: RandomForest + LogisticRegression + GBT")
    
    # Train models
    print("\n" + "="*80)
    print("TRAINING ENSEMBLE MODELS")
    print("="*80)
    
    print("Training Random Forest...")
    model_rf = pipeline_rf.fit(train_data)
    print("✅ Random Forest trained")
    
    print("Training Logistic Regression...")
    model_lr = pipeline_lr.fit(train_data)
    print("✅ Logistic Regression trained")
    
    print("Training Gradient Boosting Trees...")
    model_gbt = pipeline_gbt.fit(train_data)
    print("✅ Gradient Boosting Trees trained")
    
    # Evaluate each model on validation set
    print("\n" + "="*80)
    print("VALIDATION RESULTS - INDIVIDUAL MODELS")
    print("="*80)
    
    evaluators = {
        'AUC-ROC': BinaryClassificationEvaluator(labelCol='admission_label', metricName='areaUnderROC'),
        'AUC-PR': BinaryClassificationEvaluator(labelCol='admission_label', metricName='areaUnderPR'),
        'F1': MulticlassClassificationEvaluator(labelCol='admission_label', metricName='f1'),
        'Precision': MulticlassClassificationEvaluator(labelCol='admission_label', metricName='weightedPrecision'),
        'Recall': MulticlassClassificationEvaluator(labelCol='admission_label', metricName='weightedRecall'),
        'Accuracy': MulticlassClassificationEvaluator(labelCol='admission_label', metricName='accuracy')
    }
    
    # Evaluate RF
    print("\n📊 Random Forest:")
    pred_rf = model_rf.transform(valid_data)
    metrics_rf = {name: ev.evaluate(pred_rf) for name, ev in evaluators.items()}
    for name, value in metrics_rf.items():
        print(f"   {name:12s}: {value:.4f}")
    
    # Evaluate LR
    print("\n📊 Logistic Regression:")
    pred_lr = model_lr.transform(valid_data)
    metrics_lr = {name: ev.evaluate(pred_lr) for name, ev in evaluators.items()}
    for name, value in metrics_lr.items():
        print(f"   {name:12s}: {value:.4f}")
    
    # Evaluate GBT
    print("\n📊 Gradient Boosting Trees:")
    pred_gbt = model_gbt.transform(valid_data)
    metrics_gbt = {name: ev.evaluate(pred_gbt) for name, ev in evaluators.items()}
    for name, value in metrics_gbt.items():
        print(f"   {name:12s}: {value:.4f}")
    
    # Hard Voting Ensemble (like in notebook: weights=(2,0,2) for RF, XGB, LR)
    print("\n" + "="*80)
    print("ENSEMBLE VOTING (RF + LR + GBT)")
    print("="*80)
    
    # Get predictions from each model
    pred_rf_pd = pred_rf.select('admission_label', 'prediction').toPandas()
    pred_lr_pd = pred_lr.select('prediction').toPandas()
    pred_gbt_pd = pred_gbt.select('prediction').toPandas()
    
    # Hard voting with weights (RF:2, LR:2, GBT:1)
    votes = (pred_rf_pd['prediction'] * 2 + 
             pred_lr_pd['prediction'] * 2 + 
             pred_gbt_pd['prediction'] * 1)
    ensemble_pred = (votes >= 2.5).astype(int)
    
    # Calculate ensemble metrics
    from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
    
    y_true = pred_rf_pd['admission_label'].values
    ensemble_accuracy = accuracy_score(y_true, ensemble_pred)
    ensemble_f1 = f1_score(y_true, ensemble_pred, average='weighted')
    ensemble_precision = precision_score(y_true, ensemble_pred, average='weighted')
    ensemble_recall = recall_score(y_true, ensemble_pred, average='weighted')
    
    print(f"Ensemble Accuracy : {ensemble_accuracy:.4f}")
    print(f"Ensemble F1       : {ensemble_f1:.4f}")
    print(f"Ensemble Precision: {ensemble_precision:.4f}")
    print(f"Ensemble Recall   : {ensemble_recall:.4f}")
    
    # Use best performing model for production (RF typically performs best)
    best_model = model_rf
    metrics = metrics_rf
    print(f"\n✅ Selected Random Forest as production model (best F1: {metrics_rf['F1']:.4f})")
    
    # Save all models
    print("\n" + "="*80)
    print("SAVING MODELS")
    print("="*80)
    
    # Save Random Forest (production model)
    model_path = "/opt/airflow/models/cardiac_rf_model"
    best_model.write().overwrite().save(model_path)
    print(f"✅ Random Forest model saved to: {model_path}")
    
    # Save Logistic Regression
    lr_path = "/opt/airflow/models/cardiac_lr_model"
    model_lr.write().overwrite().save(lr_path)
    print(f"✅ Logistic Regression model saved to: {lr_path}")
    
    # Save GBT
    gbt_path = "/opt/airflow/models/cardiac_gbt_model"
    model_gbt.write().overwrite().save(gbt_path)
    print(f"✅ GBT model saved to: {gbt_path}")
    
    # Save metrics (all models + ensemble)
    metrics_path = "/opt/airflow/models/cardiac_rf_model_metrics.json"
    all_metrics = {
        "random_forest": metrics_rf,
        "logistic_regression": metrics_lr,
        "gradient_boosting": metrics_gbt,
        "ensemble": {
            "accuracy": float(ensemble_accuracy),
            "f1": float(ensemble_f1),
            "precision": float(ensemble_precision),
            "recall": float(ensemble_recall)
        },
        "production_model": "random_forest"
    }
    with open(metrics_path, "w") as f:
        json.dump(all_metrics, f, indent=2)
    print(f"✅ Metrics saved to: {metrics_path}")
    
    print("\n" + "="*80)
    print("✅ MODEL TRAINING COMPLETE")
    print("="*80)
    print(f"📊 Production Model: Random Forest")
    print(f"   Accuracy: {metrics_rf['Accuracy']:.4f}")
    print(f"   F1 Score: {metrics_rf['F1']:.4f}")
    print(f"   AUC-ROC : {metrics_rf['AUC-ROC']:.4f}")
    
    spark.stop()
    return 0

if __name__ == "__main__":
    sys.exit(main())
