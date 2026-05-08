#!/usr/bin/env bash
set -euo pipefail

KAFKA_CONTAINER="adwp-kafka"

topics=(
  "tenant.provisioned"
  "tenant.status.changed"
  "tenant.config.updated"
  "agent.subscribed"
  "agent.activated"
  "agent.status.changed"
  "workflow.execution.started"
  "workflow.step.completed"
  "workflow.execution.completed"
  "workflow.execution.failed"
  "escalation.created"
  "escalation.sla.breached"
  "human.task.created"
  "human.task.resolved"
  "integration.connected"
  "integration.connection.failed"
  "integration.token.refreshed"
  "billing.subscription.activated"
  "billing.payment.failed"
  "billing.usage.recorded"
  "agent.collaboration.requested"
  "notification.requested"
  "notification.delivered"
  "audit.event.recorded"
)

echo "Creating Kafka topics..."

for topic in "${topics[@]}"; do
  docker exec $KAFKA_CONTAINER kafka-topics --create \
    --bootstrap-server localhost:9092 \
    --replication-factor 1 \
    --partitions 3 \
    --topic "$topic" \
    --if-not-exists 2>/dev/null || true

  # Create DLQ topic
  docker exec $KAFKA_CONTAINER kafka-topics --create \
    --bootstrap-server localhost:9092 \
    --replication-factor 1 \
    --partitions 1 \
    --topic "${topic}.dlq" \
    --if-not-exists 2>/dev/null || true

  echo "  Created: $topic + ${topic}.dlq"
done

echo ""
echo "All Kafka topics created successfully."
echo "Kafka UI available at: http://localhost:8085"
