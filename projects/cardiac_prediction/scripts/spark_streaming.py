from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, current_timestamp, struct, lit
from pyspark.sql.types import StructType, StructField, IntegerType, FloatType, StringType
from pyspark.ml import PipelineModel
import os

# Cấu hình
KAFKA_BOOTSTRAP_SERVERS = 'kafka:9092'
KAFKA_TOPIC = 'cardiac_data'
MODEL_PATH = '/opt/airflow/projects/cardiac_prediction/models/cardiac_rf_model' # Đường dẫn mô hình đã huấn luyện
POSTGRES_URL = "jdbc:postgresql://postgres:5432/airflow"
POSTGRES_PROPERTIES = {
    "user": "airflow",
    "password": "airflow",
    "driver": "org.postgresql.Driver"
}

def get_spark_session():
    return SparkSession.builder \
        .appName("CardiacPredictionStreaming") \
        .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,org.postgresql:postgresql:42.6.0") \
        .getOrCreate()

def main():
    spark = get_spark_session()
    spark.sparkContext.setLogLevel("WARN")

    # Schema dữ liệu đầu vào từ Kafka
    schema = StructType([
        StructField("age", IntegerType()),
        StructField("heart_rate", FloatType()),
        StructField("bp_sys", FloatType()),
        StructField("bp_dia", FloatType()),
        StructField("spo2", FloatType()),
        StructField("resp_rate", FloatType()),
        StructField("sex", IntegerType()),
        StructField("hypertension_history", IntegerType()),
        StructField("diabetes_history", IntegerType()),
        StructField("heart_failure_history", IntegerType()),
        StructField("smoking_status", IntegerType()),
        StructField("timestamp", FloatType())
    ])

    # Đọc dữ liệu từ Kafka
    df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
        .option("subscribe", KAFKA_TOPIC) \
        .option("startingOffsets", "latest") \
        .load()

    # Parse JSON
    json_df = df.select(from_json(col("value").cast("string"), schema).alias("data")).select("data.*")

    # Load Model
    if os.path.exists(MODEL_PATH):
        model = PipelineModel.load(MODEL_PATH)
        predictions = model.transform(json_df)
        
        # Chọn các cột cần thiết để lưu vào DB
        output_df = predictions.select(
            col("age"),
            col("sex"),
            col("heart_rate"),
            col("bp_sys"),
            col("bp_dia"),
            col("spo2"),
            col("resp_rate"),
            col("hypertension_history"),
            col("diabetes_history"),
            col("heart_failure_history"),
            col("smoking_status"),
            col("prediction").cast(IntegerType()).alias("result_class"),
            current_timestamp().alias("prediction_time")
        ).withColumn("model_version", lit("v1"))

        # Ghi vào PostgreSQL
        def write_to_postgres(batch_df, batch_id):
            batch_df.write \
                .jdbc(url=POSTGRES_URL, table="cardiac_predictions", mode="append", properties=POSTGRES_PROPERTIES)

        query = output_df.writeStream \
            .foreachBatch(write_to_postgres) \
            .outputMode("append") \
            .start()

        query.awaitTermination()
    else:
        print(f"❌ Model not found at {MODEL_PATH}. Waiting for model training...")
        
if __name__ == "__main__":
    main()
