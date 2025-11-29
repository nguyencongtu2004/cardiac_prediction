#!/usr/bin/env python3
"""
Cardiac Admission Data Preparation
Load, clean, and prepare cardiac admission dataset for ML training
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when, count
from pyspark.ml.feature import VectorAssembler, StandardScaler
from pyspark.ml import Pipeline
import sys

def main():
    # Initialize Spark
    spark = SparkSession.builder \
        .appName("Cardiac Data Preparation") \
        .config("spark.driver.memory", "4g") \
        .getOrCreate()
    
    print(f"✅ Spark {spark.version} initialized")
    
    # Load data
    csv_file = "/opt/airflow/projects/cardiac_prediction/data/synthetic_cardiac_5000.csv"
    df = spark.read.csv(csv_file, header=True, inferSchema=True)
    
    print("="*80)
    print(f"📊 Dataset loaded: {df.count()} records, {len(df.columns)} features")
    print("="*80)
    df.printSchema()
    df.show(5, truncate=False)
    
    # Check class distribution
    print("\n" + "="*80)
    print("CLASS DISTRIBUTION")
    print("="*80)
    df.groupBy("admission_label").count().orderBy("admission_label").show()
    
    total = df.count()
    class_0 = df.filter(col("admission_label") == 0).count()
    class_1 = df.filter(col("admission_label") == 1).count()
    class_weight = class_0 / class_1
    
    print(f"Class 0: {class_0} ({class_0/total*100:.1f}%)")
    print(f"Class 1: {class_1} ({class_1/total*100:.1f}%)")
    print(f"Imbalance ratio: {class_weight:.2f}:1")
    
    # Check missing values
    print("\n" + "="*80)
    print("MISSING VALUES CHECK")
    print("="*80)
    missing = df.select([count(when(col(c).isNull(), c)).alias(c) for c in df.columns])
    missing.show()
    
    # Data cleaning - drop unnecessary columns
    df_clean = df.drop('timestamp', 'patient_id')
    
    # Define features
    CONTINUOUS_FEATURES = ['heart_rate', 'bp_sys', 'bp_dia', 'spo2', 'resp_rate', 'age']
    BINARY_FEATURES = ['sex', 'hypertension_history', 'diabetes_history', 'heart_failure_history', 'smoking_status']
    ALL_FEATURES = CONTINUOUS_FEATURES + BINARY_FEATURES
    
    print(f"\n✅ Features: {len(ALL_FEATURES)} ({len(CONTINUOUS_FEATURES)} continuous + {len(BINARY_FEATURES)} binary)")
    print(f"   Target: admission_label")
    
    # Summary statistics
    print("\n" + "="*80)
    print("CONTINUOUS FEATURES SUMMARY")
    print("="*80)
    df_clean.select(CONTINUOUS_FEATURES).describe().show()
    
    # Train/Valid/Test Split (70/15/15)
    train_data, temp_data = df_clean.randomSplit([0.7, 0.3], seed=42)
    valid_data, test_data = temp_data.randomSplit([0.5, 0.5], seed=42)
    
    print("\n" + "="*80)
    print("DATA SPLIT")
    print("="*80)
    print(f"Train: {train_data.count()} ({train_data.count()/total*100:.1f}%)")
    print(f"Valid: {valid_data.count()} ({valid_data.count()/total*100:.1f}%)")
    print(f"Test: {test_data.count()} ({test_data.count()/total*100:.1f}%)")
    
    print("\nTrain distribution:")
    train_data.groupBy("admission_label").count().orderBy("admission_label").show()
    print("Valid distribution:")
    valid_data.groupBy("admission_label").count().orderBy("admission_label").show()
    print("Test distribution:")
    test_data.groupBy("admission_label").count().orderBy("admission_label").show()
    
    # Save processed data
    output_base = "/opt/airflow/projects/cardiac_prediction/data"
    
    print("\n" + "="*80)
    print("SAVING PROCESSED DATA")
    print("="*80)
    
    train_data.write.mode("overwrite").parquet(f"{output_base}/train_data")
    print(f"✅ Saved: {output_base}/train_data")
    
    valid_data.write.mode("overwrite").parquet(f"{output_base}/valid_data")
    print(f"✅ Saved: {output_base}/valid_data")
    
    test_data.write.mode("overwrite").parquet(f"{output_base}/test_data")
    print(f"✅ Saved: {output_base}/test_data")
    
    # Save metadata
    metadata = {
        "total_records": total,
        "class_0_count": class_0,
        "class_1_count": class_1,
        "class_weight": class_weight,
        "continuous_features": CONTINUOUS_FEATURES,
        "binary_features": BINARY_FEATURES,
        "train_count": train_data.count(),
        "valid_count": valid_data.count(),
        "test_count": test_data.count()
    }
    
    import json
    with open(f"{output_base}/metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"✅ Saved: {output_base}/metadata.json")
    
    print("\n" + "="*80)
    print("✅ DATA PREPARATION COMPLETE")
    print("="*80)
    
    spark.stop()
    return 0

if __name__ == "__main__":
    sys.exit(main())
