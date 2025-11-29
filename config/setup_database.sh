#!/bin/bash
# setup_database.sh
# ======================================
# Script để khởi tạo database schema trong PostgreSQL container

echo "🔧 Setting up PostgreSQL database schema..."

# Chạy SQL script trong container PostgreSQL
docker exec -i $(docker ps -qf "name=postgres") psql -U airflow -d airflow < /opt/airflow/config/init_database.sql

if [ $? -eq 0 ]; then
    echo "✅ Database schema initialized successfully!"
else
    echo "❌ Failed to initialize database schema"
    exit 1
fi

echo "📊 Checking tables..."
docker exec -i $(docker ps -qf "name=postgres") psql -U airflow -d airflow -c "\dt"

echo "🎯 Checking views..."
docker exec -i $(docker ps -qf "name=postgres") psql -U airflow -d airflow -c "\dv"

echo "✅ Setup completed!"
