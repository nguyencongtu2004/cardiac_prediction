# reset_kafka_topics.ps1 - Reset Kafka topics to clear old messages
# Usage: .\scripts\reset_kafka_topics.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Kafka Topics Reset Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$KAFKA_CONTAINER = "kafka"
$BOOTSTRAP_SERVER = "localhost:9092"

# Topics to reset
$TOPICS = @(
    "helmet_video_frames",
    "helmet_violations",
    "redlight_video_frames", 
    "redlight_violations"
)

foreach ($topic in $TOPICS) {
    Write-Host "`n[1/2] Deleting topic: $topic" -ForegroundColor Yellow
    docker exec $KAFKA_CONTAINER kafka-topics --bootstrap-server $BOOTSTRAP_SERVER --delete --topic $topic 2>$null
    
    Start-Sleep -Seconds 2
    
    Write-Host "[2/2] Creating topic: $topic" -ForegroundColor Green
    docker exec $KAFKA_CONTAINER kafka-topics --bootstrap-server $BOOTSTRAP_SERVER --create --topic $topic --partitions 1 --replication-factor 1 2>$null
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Done! All topics have been reset." -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan

# List topics to verify
Write-Host "`nCurrent topics:" -ForegroundColor Yellow
docker exec $KAFKA_CONTAINER kafka-topics --bootstrap-server $BOOTSTRAP_SERVER --list
