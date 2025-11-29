#!/usr/bin/env python3
"""
Cardiac Admission Model Training
Train Random Forest model with Spark MLlib and save as PipelineModel
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when
from pyspark.ml.feature import VectorAssembler, StandardScaler
from pyspark.ml.classification import RandomForestClassifier
from pyspark.ml import Pipeline
from pyspark.ml.evaluation import BinaryClassificationEvaluator, MulticlassClassificationEvaluator
import sys
import json

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
    
    # Add class weights
    train_with_weights = train_data.withColumn(
        'classWeight',
        when(col('admission_label') == 1, class_weight).otherwise(1.0)
    )
    
    # Define features
    CONTINUOUS_FEATURES = ['heart_rate', 'bp_sys', 'bp_dia', 'spo2', 'resp_rate', 'age']
    BINARY_FEATURES = ['sex', 'hypertension_history', 'diabetes_history', 'heart_failure_history', 'smoking_status']
    
    print(f"\n📋 Features: {len(CONTINUOUS_FEATURES)} continuous + {len(BINARY_FEATURES)} binary")
    
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
    
    # Stage 4: Random Forest Classifier (simple params)
    rf = RandomForestClassifier(
        featuresCol='features',
        labelCol='admission_label',
        weightCol='classWeight',
        numTrees=100,
        maxDepth=10,
        seed=42
    )
    
    # Create pipeline
    pipeline = Pipeline(stages=[assembler_continuous, scaler, assembler_final, rf])
    
    print("✅ Pipeline stages:")
    print("   1. VectorAssembler (continuous)")
    print("   2. StandardScaler")
    print("   3. VectorAssembler (final)")
    print("   4. RandomForestClassifier (numTrees=100, maxDepth=10)")
    
    # Train model
    print("\n" + "="*80)
    print("TRAINING MODEL")
    print("="*80)
    
    model = pipeline.fit(train_with_weights)
    print("✅ Training complete")
    
    # Evaluate on validation set
    print("\n" + "="*80)
    print("VALIDATION RESULTS")
    print("="*80)
    
    predictions = model.transform(valid_data)
    
    evaluators = {
        'AUC-ROC': BinaryClassificationEvaluator(labelCol='admission_label', metricName='areaUnderROC'),
        'AUC-PR': BinaryClassificationEvaluator(labelCol='admission_label', metricName='areaUnderPR'),
        'F1': MulticlassClassificationEvaluator(labelCol='admission_label', metricName='f1'),
        'Precision': MulticlassClassificationEvaluator(labelCol='admission_label', metricName='weightedPrecision'),
        'Recall': MulticlassClassificationEvaluator(labelCol='admission_label', metricName='weightedRecall'),
        'Accuracy': MulticlassClassificationEvaluator(labelCol='admission_label', metricName='accuracy')
    }
    
    metrics = {name: ev.evaluate(predictions) for name, ev in evaluators.items()}
    
    for name, value in metrics.items():
        print(f"{name:12s}: {value:.4f}")
    
    # Save model
    print("\n" + "="*80)
    print("SAVING MODEL")
    print("="*80)
    
    model_path = "/opt/airflow/models/cardiac_rf_model"
    model.write().overwrite().save(model_path)
    print(f"✅ Model saved to: {model_path}")
    
    # Save metrics
    metrics_path = "/opt/airflow/models/cardiac_rf_model_metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"✅ Metrics saved to: {metrics_path}")
    
    print("\n" + "="*80)
    print("✅ MODEL TRAINING COMPLETE")
    print("="*80)
    
    spark.stop()
    return 0

if __name__ == "__main__":
    sys.exit(main())
