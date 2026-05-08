# Incident Response Runbook

This runbook defines the incident response process for the AI Digital Workforce Platform (ADWP), including severity classification, escalation procedures, common incident resolutions, and post-incident review.

---

## Table of Contents

1. [Severity Classification](#severity-classification)
2. [On-Call Escalation Matrix](#on-call-escalation-matrix)
3. [Common Incidents and Resolutions](#common-incidents-and-resolutions)
4. [Post-Incident Review Template](#post-incident-review-template)

---

## Severity Classification

| Severity | Name      | Definition                                                                                     | Response Time | Resolution Target | Notification       |
|----------|-----------|-----------------------------------------------------------------------------------------------|---------------|-------------------|--------------------|
| **P1**   | Critical  | Complete platform outage, data breach, all agents down, payment processing failure             | 15 minutes    | 1 hour            | PagerDuty + Slack #incidents + VP Eng |
| **P2**   | Major     | Single service outage affecting multiple tenants, agent execution failures > 50%, data loss risk | 30 minutes    | 4 hours           | PagerDuty + Slack #incidents |
| **P3**   | Moderate  | Degraded performance, single agent type failing, non-critical service partial outage            | 2 hours       | 24 hours          | Slack #incidents   |
| **P4**   | Minor     | Cosmetic issues, non-blocking bugs, monitoring alert tuning, documentation gaps                 | Next business day | 1 week         | Jira ticket        |

### Severity Decision Tree

```
Is the platform completely unavailable?
  YES --> P1
  NO  --> Is customer data at risk of exposure or loss?
            YES --> P1
            NO  --> Are multiple tenants affected?
                      YES --> Is core functionality broken (agent execution, auth)?
                                YES --> P2
                                NO  --> P3
                      NO  --> Is it a production error or degradation?
                                YES --> P3
                                NO  --> P4
```

---

## On-Call Escalation Matrix

### Primary On-Call Rotation

| Level       | Role                  | Response                                        | Contact Method        |
|-------------|-----------------------|-------------------------------------------------|-----------------------|
| **L1**      | On-call Engineer      | First responder, triage and initial diagnosis    | PagerDuty auto-page   |
| **L2**      | Service Owner         | Domain expertise for the affected service        | PagerDuty escalation  |
| **L3**      | Platform Lead / SRE   | Cross-service issues, infrastructure problems    | PagerDuty + phone     |
| **L4**      | VP Engineering / CTO  | P1 incidents, customer communication decisions   | Phone call            |

### Service Ownership

| Service                | Primary Owner         | Backup Owner          |
|------------------------|-----------------------|-----------------------|
| auth-service           | Identity Team         | Platform Team         |
| tenant-service         | Platform Team         | Identity Team         |
| subscription-service   | Billing Team          | Platform Team         |
| agent-registry         | AI Team               | Platform Team         |
| workflow-service       | AI Team               | Platform Team         |
| integration-hub        | Integration Team      | Platform Team         |
| notification-service   | Platform Team         | Integration Team      |
| analytics-service      | Data Team             | Platform Team         |
| ai-runtime             | AI Team               | Platform Team         |
| Database (RDS)         | SRE / Platform Team   | DBA                   |
| Kafka                  | SRE / Platform Team   | AI Team               |
| Kubernetes             | SRE                   | Platform Team         |

### Communication Channels

| Channel                         | Purpose                                           |
|---------------------------------|---------------------------------------------------|
| Slack `#incidents`              | Real-time incident coordination                   |
| Slack `#incidents-updates`      | Status updates for wider team                     |
| PagerDuty                       | Automated alerting and on-call management         |
| Status page                     | Customer-facing incident updates                  |
| Zoom bridge (auto-created)      | War room for P1/P2 incidents                      |

---

## Common Incidents and Resolutions

### 1. Agent Execution Failures

**Symptoms:**
- `workflow.execution.failed` events spiking in Kafka
- Agent status stuck in `WORKING` or `ESCALATING`
- Increased error rates in AI Runtime health dashboard
- Tenant reports that agent tasks are not completing

**Diagnosis:**

```bash
# Check AI Runtime logs
kubectl logs -n adwp deploy/ai-runtime --tail=200 | grep -i error

# Check recent execution failures in the database
kubectl exec -n adwp deploy/ai-runtime -- python -c "
from db.database import get_db
# Query recent failed executions
"

# Check agent registration
curl -s http://ai-runtime:8000/v1/health | jq '.agents'

# Check LLM gateway connectivity
kubectl exec -n adwp deploy/ai-runtime -- python -c "
from llm.gateway import LLMGateway, _has_openai_key, _has_anthropic_key
print(f'OpenAI key: {_has_openai_key()}')
print(f'Anthropic key: {_has_anthropic_key()}')
"
```

**Resolution:**

| Cause                           | Fix                                                        |
|---------------------------------|------------------------------------------------------------|
| LLM API key expired/invalid     | Rotate key in Kubernetes Secret `adwp-llm-keys`           |
| LLM rate limit exceeded         | Gateway auto-failovers; if both providers limited, wait    |
| Agent not registered            | Check `api/main.py` for missing registration; restart pod  |
| Memory/OOM kill                 | Increase pod memory limits; check for memory leaks         |
| Database connection failure     | See [Database Connection Issues](#3-database-connection-issues) |

---

### 2. LLM Provider Outage

**Symptoms:**
- LLMGateway logs show repeated provider failures
- All agent executions failing or timing out
- `provider` field in responses showing unexpected fallback provider

**Diagnosis:**

```bash
# Check LLM gateway logs for failover events
kubectl logs -n adwp deploy/ai-runtime --tail=200 | grep -i "Provider.*failed"

# Check provider status pages
# OpenAI: https://status.openai.com
# Anthropic: https://status.anthropic.com

# Verify API keys
kubectl get secret adwp-llm-keys -n adwp -o jsonpath='{.data.OPENAI_API_KEY}' | base64 -d | head -c 10
kubectl get secret adwp-llm-keys -n adwp -o jsonpath='{.data.ANTHROPIC_API_KEY}' | base64 -d | head -c 10
```

**Resolution:**

| Cause                            | Fix                                                          |
|----------------------------------|--------------------------------------------------------------|
| Single provider outage           | No action needed -- gateway auto-failovers to backup          |
| Both providers down              | Communicate to tenants; monitor provider status pages         |
| API key quota exhausted          | Increase quota with provider; rotate to backup key            |
| Network connectivity             | Check VPC/security group egress rules for API endpoints      |
| Rate limiting                    | Reduce concurrent agent executions; implement request queuing |

**Temporary Mitigation:**

```bash
# Force all requests to a specific provider
kubectl set env deployment/ai-runtime -n adwp LLM_DEFAULT_PROVIDER=anthropic

# Restart pods to pick up new environment
kubectl rollout restart deployment/ai-runtime -n adwp
```

---

### 3. Database Connection Issues

**Symptoms:**
- Services returning 500 errors
- Prisma client throwing connection timeout errors
- RDS CloudWatch showing high connection count or CPU

**Diagnosis:**

```bash
# Check database connectivity from a pod
kubectl exec -n adwp deploy/auth-service -- \
  node -e "const { PrismaClient } = require('@prisma/client'); const p = new PrismaClient(); p.\$connect().then(() => console.log('OK')).catch(e => console.error(e))"

# Check RDS metrics
aws rds describe-db-instances --db-instance-identifier adwp-production --query 'DBInstances[0].{Status:DBInstanceStatus,Connections:Endpoint}'

# Check connection pool usage
kubectl logs -n adwp deploy/workflow-service --tail=100 | grep -i "pool\|connection\|timeout"

# Check if RDS is in maintenance or failover
aws rds describe-events --source-identifier adwp-production --source-type db-instance --duration 60
```

**Resolution:**

| Cause                            | Fix                                                          |
|----------------------------------|--------------------------------------------------------------|
| Connection pool exhaustion       | Increase pool size in `DATABASE_URL` `?connection_limit=20`  |
| RDS instance at capacity         | Scale up instance class; enable read replicas                |
| RDS failover in progress         | Wait for failover completion (typically 1-2 minutes)         |
| Security group change            | Verify SG allows ingress on port 5432 from EKS nodes        |
| DNS resolution failure           | Check VPC DNS settings; restart CoreDNS pods                 |
| Prisma migration lock            | Release lock: `DELETE FROM _prisma_migrations WHERE ...`     |

---

### 4. Kafka Consumer Lag

**Symptoms:**
- Events not being processed in a timely manner
- Notification delays
- Audit events backlogged
- Kafka UI showing growing consumer lag

**Diagnosis:**

```bash
# Check consumer group lag
kubectl exec -n adwp deploy/workflow-service -- \
  kafka-consumer-groups --bootstrap-server adwp-kafka:9092 --describe --all-groups

# Check for stuck consumers
kubectl exec -n adwp deploy/workflow-service -- \
  kafka-consumer-groups --bootstrap-server adwp-kafka:9092 --describe --group workflow-service-group

# Check Kafka broker health
kubectl exec -n adwp deploy/workflow-service -- \
  kafka-broker-api-versions --bootstrap-server adwp-kafka:9092

# Check for messages in DLQ
kubectl exec -n adwp deploy/workflow-service -- \
  node -e "const { PrismaClient } = require('@prisma/client'); const p = new PrismaClient(); p.dlqEntry.count({where:{status:'pending'}}).then(c => console.log('DLQ pending:', c))"
```

**Resolution:**

| Cause                            | Fix                                                          |
|----------------------------------|--------------------------------------------------------------|
| Consumer crashed/stuck           | Restart the consuming service deployment                      |
| Processing error causing rebalance | Check consumer logs for deserialization errors              |
| Insufficient partitions          | Increase topic partition count                               |
| Slow consumer processing         | Optimize consumer handler; add more consumer instances       |
| Broker disk full                 | Increase broker EBS volume; adjust retention policies        |
| DLQ overflow                     | Process or clear DLQ entries; fix root cause                 |

---

### 5. Integration Connector Failures

**Symptoms:**
- Integration status showing `ERROR` or `DISCONNECTED`
- `integration.connection.failed` events in Kafka
- Agent tasks failing at the tool execution step
- Tenant reports data not syncing from CRM/ERP

**Diagnosis:**

```bash
# Check integration connection status
kubectl exec -n adwp deploy/integration-hub -- \
  node -e "const { PrismaClient } = require('@prisma/client'); const p = new PrismaClient(); p.integrationConnection.findMany({where:{status:'ERROR'},select:{id:true,provider:true,lastErrorMessage:true,tenantId:true}}).then(r => console.log(JSON.stringify(r,null,2)))"

# Check integration logs
kubectl logs -n adwp deploy/integration-hub --tail=200 | grep -i "error\|failed\|timeout"

# Check token expiry
kubectl exec -n adwp deploy/integration-hub -- \
  node -e "const { PrismaClient } = require('@prisma/client'); const p = new PrismaClient(); p.integrationConnection.findMany({where:{tokenExpiresAt:{lt:new Date()}},select:{id:true,provider:true,tenantId:true}}).then(r => console.log('Expired tokens:', JSON.stringify(r,null,2)))"
```

**Resolution:**

| Cause                            | Fix                                                          |
|----------------------------------|--------------------------------------------------------------|
| OAuth token expired              | Trigger token refresh; check refresh token validity          |
| Third-party API outage           | Check provider status page; retry after outage resolves      |
| Rate limit from provider         | Implement backoff; check `rateLimitRemaining` field          |
| Invalid credentials              | Ask tenant to re-authenticate the integration                |
| Network/firewall block           | Check VPC egress rules for provider API endpoints            |
| Schema change in provider API    | Update integration connector code; deploy fix                |

---

## Post-Incident Review Template

Conduct a post-incident review (PIR) within 48 hours of P1/P2 incident resolution, and within 1 week for P3 incidents.

```markdown
# Post-Incident Review: [INCIDENT-ID]

## Incident Summary

| Field               | Value                                           |
|---------------------|-------------------------------------------------|
| **Incident ID**     | INC-YYYY-NNNN                                   |
| **Severity**        | P1 / P2 / P3                                    |
| **Date**            | YYYY-MM-DD                                      |
| **Duration**        | HH:MM (from detection to resolution)            |
| **Impact**          | [Number of tenants affected, services impacted]  |
| **Detection**       | [How was the incident detected? Alert/Customer?] |
| **Incident Lead**   | [Name]                                           |
| **Status**          | Resolved / Monitoring                            |

## Timeline

| Time (UTC)  | Event                                                    |
|-------------|----------------------------------------------------------|
| HH:MM       | [First alert / customer report]                          |
| HH:MM       | [Incident declared, on-call paged]                       |
| HH:MM       | [Root cause identified]                                  |
| HH:MM       | [Fix applied]                                            |
| HH:MM       | [Service restored, monitoring]                           |
| HH:MM       | [Incident resolved]                                      |

## Root Cause

[Detailed description of what caused the incident. Include technical details.]

## Impact Assessment

- **Tenants affected:** [Count and names if relevant]
- **Data impact:** [Any data loss or corruption?]
- **Revenue impact:** [Any billing or payment impact?]
- **SLA breaches:** [Any SLA violations triggered?]

## What Went Well

- [List things that worked during the incident response]

## What Could Be Improved

- [List areas for improvement]

## Action Items

| # | Action                                    | Owner     | Due Date   | Status  |
|---|-------------------------------------------|-----------|------------|---------|
| 1 | [Preventive action]                       | [Name]    | YYYY-MM-DD | Open    |
| 2 | [Monitoring improvement]                  | [Name]    | YYYY-MM-DD | Open    |
| 3 | [Process improvement]                     | [Name]    | YYYY-MM-DD | Open    |

## Lessons Learned

[Key takeaways that should be shared with the broader team]
```
