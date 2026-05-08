# Deployment Runbook

This runbook covers the complete deployment process for the AI Digital Workforce Platform (ADWP), including staging and production environments.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Step-by-Step Deployment Process](#step-by-step-deployment-process)
4. [Rolling Update Procedure](#rolling-update-procedure)
5. [Rollback Procedure](#rollback-procedure)
6. [Post-Deployment Verification](#post-deployment-verification)
7. [Monitoring Dashboard Links](#monitoring-dashboard-links)

---

## Prerequisites

Ensure the following tools are installed and configured on your workstation:

| Tool        | Minimum Version | Installation                                         |
|-------------|-----------------|------------------------------------------------------|
| `kubectl`   | 1.28+           | `brew install kubectl` or [official docs](https://kubernetes.io/docs/tasks/tools/) |
| `helm`      | 3.14+           | `brew install helm`                                  |
| `aws`       | 2.15+           | `brew install awscli`                                |
| `docker`    | 24.0+           | [Docker Desktop](https://www.docker.com/products/docker-desktop/) |
| `pnpm`      | 9.0+            | `npm install -g pnpm`                                |
| `node`      | 20.0+           | `brew install node@20`                               |
| `python`    | 3.11+           | `brew install python@3.11`                           |

**AWS Credentials:**

```bash
# Verify AWS access
aws sts get-caller-identity

# Ensure you have the correct profile
export AWS_PROFILE=adwp-production  # or adwp-staging
```

**Kubernetes Context:**

```bash
# Update kubeconfig for the target cluster
aws eks update-kubeconfig --name adwp-staging --region me-south-1
# or
aws eks update-kubeconfig --name adwp-production --region me-south-1

# Verify context
kubectl config current-context
kubectl get nodes
```

---

## Environment Setup

### Staging vs Production

| Configuration        | Staging                               | Production                             |
|----------------------|---------------------------------------|----------------------------------------|
| Kubernetes cluster   | `adwp-staging`                        | `adwp-production`                      |
| Namespace            | `adwp-staging`                        | `adwp`                                 |
| Database             | `adwp-staging` RDS instance           | `adwp-production` RDS Multi-AZ         |
| Kafka                | 1-broker dev cluster                  | 3-broker production cluster            |
| Redis                | Single node                           | ElastiCache cluster                    |
| LLM provider         | Mock or development API keys          | Production API keys with rate limits   |
| Domain               | `staging.adwp.io`                     | `app.adwp.io`                          |
| Replicas per service | 1                                     | 2-3                                    |

### Environment Variables

Critical environment variables are managed via Kubernetes Secrets (not ConfigMaps):

```bash
# List current secrets
kubectl get secrets -n adwp

# Required secrets:
# adwp-db-credentials       -- DATABASE_URL
# adwp-redis-credentials    -- REDIS_URL, REDIS_PASSWORD
# adwp-jwt-secret           -- JWT_SECRET
# adwp-llm-keys             -- OPENAI_API_KEY, ANTHROPIC_API_KEY
# adwp-stripe-keys          -- STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET
# adwp-integration-secrets  -- OAuth secrets for third-party integrations
```

---

## Step-by-Step Deployment Process

### 1. Build Docker Images

```bash
# From repository root
# Build all service images
docker build -t adwp/auth-service:$(git rev-parse --short HEAD) -f services/auth-service/Dockerfile .
docker build -t adwp/tenant-service:$(git rev-parse --short HEAD) -f services/tenant-service/Dockerfile .
docker build -t adwp/subscription-service:$(git rev-parse --short HEAD) -f services/subscription-service/Dockerfile .
docker build -t adwp/agent-registry:$(git rev-parse --short HEAD) -f services/agent-registry/Dockerfile .
docker build -t adwp/workflow-service:$(git rev-parse --short HEAD) -f services/workflow-service/Dockerfile .
docker build -t adwp/integration-hub:$(git rev-parse --short HEAD) -f services/integration-hub/Dockerfile .
docker build -t adwp/notification-service:$(git rev-parse --short HEAD) -f services/notification-service/Dockerfile .
docker build -t adwp/analytics-service:$(git rev-parse --short HEAD) -f services/analytics-service/Dockerfile .
docker build -t adwp/ai-runtime:$(git rev-parse --short HEAD) -f ai-runtime/Dockerfile .

# Build frontend apps
docker build -t adwp/portal:$(git rev-parse --short HEAD) -f apps/portal/Dockerfile .
docker build -t adwp/admin:$(git rev-parse --short HEAD) -f apps/admin/Dockerfile .
```

### 2. Push to Container Registry

```bash
# Tag and push to ECR
IMAGE_TAG=$(git rev-parse --short HEAD)
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.me-south-1.amazonaws.com"

# Login to ECR
aws ecr get-login-password --region me-south-1 | docker login --username AWS --password-stdin $ECR_REGISTRY

# Push all images
for SERVICE in auth-service tenant-service subscription-service agent-registry \
               workflow-service integration-hub notification-service analytics-service \
               ai-runtime portal admin; do
  docker tag adwp/${SERVICE}:${IMAGE_TAG} ${ECR_REGISTRY}/adwp/${SERVICE}:${IMAGE_TAG}
  docker push ${ECR_REGISTRY}/adwp/${SERVICE}:${IMAGE_TAG}
done
```

### 3. Run Database Migrations

```bash
# Run migrations BEFORE deploying new code
# Connect to the database via a bastion or port-forward
kubectl port-forward svc/adwp-postgres 5433:5432 -n adwp &

# Run Prisma migrations
DATABASE_URL="postgresql://adwp:PASSWORD@localhost:5433/adwp" pnpm db:migrate:deploy

# Verify migration status
DATABASE_URL="postgresql://adwp:PASSWORD@localhost:5433/adwp" npx prisma migrate status
```

### 4. Deploy Services

```bash
IMAGE_TAG=$(git rev-parse --short HEAD)
NAMESPACE="adwp"  # or "adwp-staging"

# Apply namespace and configmap
kubectl apply -f infrastructure/k8s/namespace.yaml
kubectl apply -f infrastructure/k8s/configmap.yaml

# Deploy services with updated image tag
for SERVICE in auth-service tenant-service subscription-service agent-registry \
               workflow-service integration-hub notification-service analytics-service \
               ai-runtime portal admin; do
  kubectl set image deployment/${SERVICE} ${SERVICE}=${ECR_REGISTRY}/adwp/${SERVICE}:${IMAGE_TAG} \
    -n ${NAMESPACE}
done
```

### 5. Verify Deployment

```bash
# Watch rollout status
kubectl rollout status deployment/auth-service -n adwp --timeout=300s
kubectl rollout status deployment/ai-runtime -n adwp --timeout=300s

# Check all pods are running
kubectl get pods -n adwp -o wide

# Check for crash loops
kubectl get pods -n adwp | grep -E 'CrashLoop|Error|ImagePull'
```

---

## Rolling Update Procedure

For zero-downtime updates, Kubernetes deployments are configured with rolling update strategy:

```yaml
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  minReadySeconds: 10
```

**Steps:**

1. Ensure all health checks are passing on current deployment.
2. Update the image tag:
   ```bash
   kubectl set image deployment/workflow-service \
     workflow-service=${ECR_REGISTRY}/adwp/workflow-service:${NEW_TAG} \
     -n adwp
   ```
3. Monitor the rollout:
   ```bash
   kubectl rollout status deployment/workflow-service -n adwp
   ```
4. Kubernetes will:
   - Start a new pod with the updated image.
   - Wait for readiness probe to pass.
   - Route traffic to the new pod.
   - Terminate the old pod.

**To update all services simultaneously:**

```bash
# Apply the updated manifests
kubectl apply -f infrastructure/k8s/ -n adwp
```

---

## Rollback Procedure

### Quick Rollback (Kubernetes)

```bash
# Roll back to previous revision
kubectl rollout undo deployment/workflow-service -n adwp

# Roll back to a specific revision
kubectl rollout history deployment/workflow-service -n adwp
kubectl rollout undo deployment/workflow-service -n adwp --to-revision=3

# Verify rollback
kubectl rollout status deployment/workflow-service -n adwp
```

### Database Migration Rollback

**CAUTION:** Database rollbacks can cause data loss. Always consult the team before rolling back migrations.

```bash
# Check current migration state
DATABASE_URL="..." npx prisma migrate status

# Rollback is manual -- apply a corrective migration
# Prisma does not support automatic rollback
# Create a new migration that reverses the changes
DATABASE_URL="..." npx prisma migrate dev --name rollback_<migration_name>
```

### Full Environment Rollback

If multiple services need rollback:

```bash
# Roll back all deployments to previous revision
for DEPLOY in $(kubectl get deployments -n adwp -o name); do
  kubectl rollout undo ${DEPLOY} -n adwp
done
```

---

## Post-Deployment Verification

### Health Checks

```bash
# Check service health endpoints
SERVICES=(
  "auth-service:3010"
  "tenant-service:3011"
  "subscription-service:3012"
  "agent-registry:3013"
  "workflow-service:3014"
  "integration-hub:3015"
  "notification-service:3016"
  "analytics-service:3017"
  "ai-runtime:8000"
)

for SVC in "${SERVICES[@]}"; do
  NAME=$(echo $SVC | cut -d: -f1)
  PORT=$(echo $SVC | cut -d: -f2)
  echo "Checking ${NAME}..."
  kubectl exec -n adwp deploy/${NAME} -- curl -s http://localhost:${PORT}/health
  echo ""
done
```

### Smoke Tests

Run the following checks after every deployment:

```bash
# 1. Authentication flow
curl -s https://app.adwp.io/api/auth/health | jq .

# 2. Tenant creation (staging only)
curl -s -X POST https://staging.adwp.io/api/tenants/health | jq .

# 3. Agent registry
curl -s https://app.adwp.io/api/agent-registry/v1/agents | jq .

# 4. AI Runtime health
curl -s https://app.adwp.io/api/ai-runtime/v1/health | jq .

# 5. Execute a test agent task (staging only)
curl -s -X POST https://staging.adwp.io/api/ai-runtime/v1/agents/ai-customer-support-agent/execute \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${STAGING_TOKEN}" \
  -d '{"task_payload": {"message": "What is your return policy?"}, "context": {"tenantId": "test-tenant"}}' | jq .
```

### Database Connectivity

```bash
# Verify Prisma can connect and schema is in sync
kubectl exec -n adwp deploy/workflow-service -- npx prisma migrate status
```

### Kafka Connectivity

```bash
# Check Kafka topic list
kubectl exec -n adwp deploy/workflow-service -- \
  kafka-topics --bootstrap-server adwp-kafka:9092 --list

# Check consumer group lag
kubectl exec -n adwp deploy/workflow-service -- \
  kafka-consumer-groups --bootstrap-server adwp-kafka:9092 --describe --all-groups
```

---

## Monitoring Dashboard Links

| Dashboard                  | URL                                                     | Purpose                        |
|----------------------------|---------------------------------------------------------|--------------------------------|
| Kubernetes (Grafana)       | `https://grafana.adwp.io/d/k8s-overview`                | Pod status, resource usage     |
| Service Health             | `https://grafana.adwp.io/d/service-health`              | HTTP latency, error rates      |
| AI Runtime Metrics         | `https://grafana.adwp.io/d/ai-runtime`                  | Agent execution time, costs    |
| Kafka Consumer Lag         | `https://grafana.adwp.io/d/kafka-lag`                   | Consumer group offsets         |
| Kafka UI (local only)      | `http://localhost:8085`                                  | Topic browser, message viewer  |
| PostgreSQL (RDS)           | `https://grafana.adwp.io/d/rds-postgres`                | Query latency, connections     |
| Redis (ElastiCache)        | `https://grafana.adwp.io/d/redis`                       | Memory usage, hit rate         |
| Alerts                     | `https://grafana.adwp.io/alerting/list`                  | Active alerts and history      |
| PagerDuty                  | `https://adwp.pagerduty.com`                            | On-call schedule, incidents    |
| AWS CloudWatch             | `https://console.aws.amazon.com/cloudwatch`             | Infrastructure-level metrics   |
| Sentry                     | `https://adwp.sentry.io`                                | Application errors             |
