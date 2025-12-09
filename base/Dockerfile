FROM apache/airflow:2.9.0

USER root

# Cài Java (cho Spark)
RUN apt-get update && apt-get install -y --no-install-recommends openjdk-17-jre-headless libgl1 libglib2.0-0 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH="${JAVA_HOME}/bin:${PATH}"

# Copy file requirements trong chính thư mục base
COPY base/requirements.txt /tmp/base_requirements.txt

USER airflow
RUN pip install --no-cache-dir -r /tmp/base_requirements.txt && \
    # Fix lỗi kafka.vendor.six.moves không tồn tại trong kafka-python 2.0.1
    sed -i "s|from kafka.vendor.six.moves import range|from six.moves import range|" \
        /home/airflow/.local/lib/python3.*/site-packages/kafka/codec.py || true

# ================================
# 🔧 Cardiac Prediction Project
# ================================
USER root
COPY projects/cardiac_prediction/scripts /opt/airflow/projects/cardiac_prediction/scripts
RUN chmod +x /opt/airflow/projects/cardiac_prediction/scripts/*.sh
USER airflow

COPY projects/cardiac_prediction/streamlit /opt/airflow/projects/cardiac_prediction/streamlit

# Cài các thư viện cần thiết cho Streamlit và Spark
USER airflow
RUN pip install --no-cache-dir streamlit psycopg2-binary pandas pyspark scikit-learn