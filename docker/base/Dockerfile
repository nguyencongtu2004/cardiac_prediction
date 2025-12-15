FROM apache/airflow:2.9.0

USER root

# Cài Java (cho Spark)
# Cài Java (cho Spark)
# Cài Java (cho Spark)
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends openjdk-17-jre-headless libgl1 libglib2.0-0 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH="${JAVA_HOME}/bin:${PATH}"

# Copy file requirements (context is projects/realtime-traffic-monitoring)
COPY docker/base/requirements.txt /tmp/base_requirements.txt

USER airflow
RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    pip install -r /tmp/base_requirements.txt && \
    # Fix lỗi kafka.vendor.six.moves không tồn tại trong kafka-python 2.0.1
    sed -i "s|from kafka.vendor.six.moves import range|from six.moves import range|" \
    /home/airflow/.local/lib/python3.*/site-packages/kafka/codec.py || true

# ================================
# 🔧 Realtime Traffic Monitoring Project
# ================================
# If we need to pre-install specific scripts or tools, do it here.
# For now, we mount the project volume, so we don't strictly need to COPY everything if using dev mode.
# But for production, we might want to COPY.
# Since the user focuses on "realtime-traffic-monitoring", we skip the cardiac code.

# Cài các thư viện cần thiết
USER airflow
RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    pip install streamlit psycopg2-binary pandas pyspark scikit-learn