# Database Maintenance Runbook

This runbook covers database backup and restore procedures, migration management, performance monitoring, index maintenance, dead letter queue cleanup, and audit log archival for the ADWP PostgreSQL database.

---

## Table of Contents

1. [Backup Procedures](#backup-procedures)
2. [Restore Procedures](#restore-procedures)
3. [Migration Process](#migration-process)
4. [Performance Monitoring Queries](#performance-monitoring-queries)
5. [Index Maintenance](#index-maintenance)
6. [Dead Letter Queue Cleanup](#dead-letter-queue-cleanup)
7. [Audit Log Archival](#audit-log-archival)

---

## Backup Procedures

### RDS Automated Backups

AWS RDS is configured with automated daily backups:

| Setting                  | Value                         |
|--------------------------|-------------------------------|
| Backup window            | 02:00-03:00 UTC (off-peak)    |
| Retention period         | 35 days (production)          |
| Retention period         | 7 days (staging)              |
| Multi-AZ                 | Enabled (production only)     |
| Storage encrypted        | Yes (AES-256)                 |

**Verify automated backup status:**

```bash
aws rds describe-db-instances \
  --db-instance-identifier adwp-production \
  --query 'DBInstances[0].{BackupRetention:BackupRetentionPeriod,LatestBackup:LatestRestorableTime,MultiAZ:MultiAZ,Encrypted:StorageEncrypted}'
```

### Manual Snapshots

Create manual snapshots before major deployments, schema migrations, or maintenance windows:

```bash
# Create manual snapshot
SNAPSHOT_ID="adwp-production-pre-migration-$(date +%Y%m%d-%H%M%S)"
aws rds create-db-snapshot \
  --db-instance-identifier adwp-production \
  --db-snapshot-identifier "${SNAPSHOT_ID}" \
  --tags Key=Purpose,Value=pre-migration Key=CreatedBy,Value=$(whoami)

# Monitor snapshot progress
aws rds describe-db-snapshots \
  --db-snapshot-identifier "${SNAPSHOT_ID}" \
  --query 'DBSnapshots[0].{Status:Status,PercentProgress:PercentProgress}'

# List recent snapshots
aws rds describe-db-snapshots \
  --db-instance-identifier adwp-production \
  --query 'DBSnapshots[*].{ID:DBSnapshotIdentifier,Status:Status,Created:SnapshotCreateTime,Size:AllocatedStorage}' \
  --output table
```

### Logical Backup (pg_dump)

For table-level or schema-level backups:

```bash
# Port-forward to RDS
kubectl port-forward svc/adwp-postgres 5433:5432 -n adwp &

# Full logical backup
pg_dump -h localhost -p 5433 -U adwp -d adwp \
  --format=custom --compress=9 \
  --file="adwp-backup-$(date +%Y%m%d-%H%M%S).dump"

# Backup specific tables only
pg_dump -h localhost -p 5433 -U adwp -d adwp \
  --format=custom --compress=9 \
  --table=audit_logs --table=agent_actions \
  --file="adwp-audit-backup-$(date +%Y%m%d).dump"

# Upload to S3
aws s3 cp adwp-backup-*.dump s3://adwp-backups/manual/
```

---

## Restore Procedures

### Restore from RDS Snapshot

```bash
# Restore to a new instance (non-destructive)
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier adwp-production-restored \
  --db-snapshot-identifier "${SNAPSHOT_ID}" \
  --db-instance-class db.r6g.xlarge \
  --db-subnet-group-name adwp-db-subnet-group \
  --vpc-security-group-ids sg-xxxxxxxxx

# Wait for instance to be available
aws rds wait db-instance-available \
  --db-instance-identifier adwp-production-restored

# Verify data by connecting and running test queries
psql -h <restored-endpoint> -U adwp -d adwp -c "SELECT count(*) FROM tenants;"
```

### Point-in-Time Recovery

```bash
# Restore to a specific point in time
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier adwp-production \
  --target-db-instance-identifier adwp-production-pitr \
  --restore-time "2025-03-01T12:00:00Z" \
  --db-instance-class db.r6g.xlarge \
  --db-subnet-group-name adwp-db-subnet-group
```

### Restore from pg_dump

```bash
# Download from S3
aws s3 cp s3://adwp-backups/manual/adwp-backup-YYYYMMDD.dump .

# Restore to target database
pg_restore -h localhost -p 5433 -U adwp -d adwp_restored \
  --format=custom --clean --if-exists \
  adwp-backup-YYYYMMDD.dump

# Restore specific tables only
pg_restore -h localhost -p 5433 -U adwp -d adwp \
  --format=custom --table=audit_logs \
  adwp-backup-YYYYMMDD.dump
```

---

## Migration Process

### Prisma Migrate Workflow

The ADWP platform uses Prisma as the ORM and migration tool. The schema is defined in `database/prisma/schema.prisma`.

**Development (create new migration):**

```bash
# Edit the schema file: database/prisma/schema.prisma

# Generate a new migration
pnpm db:migrate
# This runs: npx prisma migrate dev
# Prompts for a migration name, e.g., "add_contract_renewal_date"

# Verify generated SQL
cat database/prisma/migrations/<timestamp>_<name>/migration.sql
```

**Staging/Production (apply existing migrations):**

```bash
# Apply pending migrations (non-interactive)
pnpm db:migrate:deploy
# This runs: npx prisma migrate deploy

# Check migration status
DATABASE_URL="..." npx prisma migrate status
```

**Generate Prisma client after schema changes:**

```bash
pnpm db:generate
# This runs: npx prisma generate
```

**Seed the database (initial or reference data):**

```bash
pnpm db:seed
# This runs: npx prisma db seed (executes database/prisma/seed.ts)
```

### Migration Safety Checklist

Before applying migrations to production:

- [ ] Migration reviewed by at least one other engineer
- [ ] Migration tested on staging with production-like data volume
- [ ] Manual snapshot created before migration (see [Manual Snapshots](#manual-snapshots))
- [ ] Migration SQL reviewed for destructive operations (DROP, ALTER TYPE, etc.)
- [ ] RLS policies updated if new tenant-scoped tables are added
- [ ] Indexes added for `tenantId` on new tenant-scoped tables
- [ ] Rollback plan documented if migration cannot be reversed
- [ ] Estimated migration duration documented for large tables
- [ ] Off-peak maintenance window scheduled for long-running migrations

### Migration with Downtime Considerations

For migrations that may lock tables (adding columns with defaults, changing column types):

```bash
# 1. Check table size
psql -c "SELECT pg_size_pretty(pg_total_relation_size('workflow_executions'));"

# 2. For large tables, use concurrent index creation
-- In migration SQL:
CREATE INDEX CONCURRENTLY idx_new_column ON table_name(column_name);

# 3. For column additions, avoid DEFAULT in ALTER TABLE on large tables
-- Instead, add column as nullable, then backfill in batches:
ALTER TABLE large_table ADD COLUMN new_col TEXT;
-- Then batch update:
UPDATE large_table SET new_col = 'default' WHERE new_col IS NULL AND id IN (SELECT id FROM large_table WHERE new_col IS NULL LIMIT 10000);
```

---

## Performance Monitoring Queries

Connect to the database and run these queries for performance analysis.

### Active Queries and Locks

```sql
-- Currently running queries (longer than 5 seconds)
SELECT
  pid,
  now() - pg_stat_activity.query_start AS duration,
  query,
  state,
  wait_event_type,
  wait_event
FROM pg_stat_activity
WHERE (now() - pg_stat_activity.query_start) > interval '5 seconds'
  AND state != 'idle'
ORDER BY duration DESC;

-- Blocked queries
SELECT
  blocked.pid AS blocked_pid,
  blocked.query AS blocked_query,
  blocking.pid AS blocking_pid,
  blocking.query AS blocking_query
FROM pg_stat_activity blocked
JOIN pg_locks bl ON blocked.pid = bl.pid
JOIN pg_locks blk ON bl.locktype = blk.locktype
  AND bl.relation = blk.relation
  AND bl.pid != blk.pid
JOIN pg_stat_activity blocking ON blk.pid = blocking.pid
WHERE NOT bl.granted;
```

### Table Statistics

```sql
-- Table sizes and row counts
SELECT
  schemaname || '.' || tablename AS table_name,
  pg_size_pretty(pg_total_relation_size(schemaname || '.' || tablename)) AS total_size,
  pg_size_pretty(pg_relation_size(schemaname || '.' || tablename)) AS data_size,
  pg_size_pretty(pg_indexes_size(schemaname || '.' || tablename)) AS index_size,
  n_live_tup AS estimated_rows
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(schemaname || '.' || tablename) DESC
LIMIT 20;

-- Tables with high dead tuple ratio (need VACUUM)
SELECT
  schemaname || '.' || relname AS table_name,
  n_live_tup,
  n_dead_tup,
  CASE WHEN n_live_tup > 0
    THEN ROUND(100.0 * n_dead_tup / n_live_tup, 2)
    ELSE 0 END AS dead_ratio_pct,
  last_vacuum,
  last_autovacuum
FROM pg_stat_user_tables
WHERE n_dead_tup > 1000
ORDER BY n_dead_tup DESC;
```

### Index Usage

```sql
-- Unused indexes (candidates for removal)
SELECT
  schemaname || '.' || relname AS table_name,
  indexrelname AS index_name,
  pg_size_pretty(pg_relation_size(indexrelid)) AS index_size,
  idx_scan AS times_used
FROM pg_stat_user_indexes
WHERE idx_scan = 0
  AND schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY pg_relation_size(indexrelid) DESC;

-- Most used indexes
SELECT
  schemaname || '.' || relname AS table_name,
  indexrelname AS index_name,
  idx_scan AS times_used,
  idx_tup_read AS tuples_read,
  idx_tup_fetch AS tuples_fetched
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC
LIMIT 20;
```

### Query Performance

```sql
-- Slowest queries (requires pg_stat_statements extension)
SELECT
  query,
  calls,
  ROUND(total_exec_time::numeric, 2) AS total_ms,
  ROUND(mean_exec_time::numeric, 2) AS avg_ms,
  ROUND(max_exec_time::numeric, 2) AS max_ms,
  rows
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 20;

-- Connection stats
SELECT
  datname,
  numbackends AS active_connections,
  xact_commit AS commits,
  xact_rollback AS rollbacks,
  blks_hit,
  blks_read,
  CASE WHEN blks_hit + blks_read > 0
    THEN ROUND(100.0 * blks_hit / (blks_hit + blks_read), 2)
    ELSE 0 END AS cache_hit_ratio
FROM pg_stat_database
WHERE datname = 'adwp';
```

### Tenant-Specific Queries

```sql
-- Largest tenants by data volume
SELECT
  t.name AS tenant_name,
  COUNT(DISTINCT we.id) AS workflow_executions,
  COUNT(DISTINCT al.id) AS audit_logs,
  COUNT(DISTINCT ic.id) AS integrations
FROM tenants t
LEFT JOIN workflow_executions we ON we."tenantId" = t.id
LEFT JOIN audit_logs al ON al."tenantId" = t.id
LEFT JOIN integration_connections ic ON ic."tenantId" = t.id
GROUP BY t.id, t.name
ORDER BY workflow_executions DESC
LIMIT 10;

-- Per-tenant agent usage (last 30 days)
SELECT
  t.name AS tenant_name,
  um."agentId",
  SUM(um."taskCount") AS total_tasks,
  SUM(um."tokenCount") AS total_tokens,
  SUM(um."costUsd"::numeric) AS total_cost_usd
FROM usage_metrics um
JOIN tenants t ON t.id = um."tenantId"
WHERE um."periodStart" >= NOW() - INTERVAL '30 days'
GROUP BY t.name, um."agentId"
ORDER BY total_cost_usd DESC;
```

---

## Index Maintenance

### Reindex Bloated Indexes

```sql
-- Check index bloat
SELECT
  schemaname || '.' || tablename AS table_name,
  indexname,
  pg_size_pretty(pg_relation_size(indexname::regclass)) AS index_size,
  idx_scan
FROM pg_stat_user_indexes psi
JOIN pg_indexes pi ON psi.indexrelname = pi.indexname
WHERE pg_relation_size(indexname::regclass) > 100 * 1024 * 1024  -- > 100MB
ORDER BY pg_relation_size(indexname::regclass) DESC;

-- Reindex concurrently (does not block reads/writes)
REINDEX INDEX CONCURRENTLY idx_workflow_executions_tenant_id;

-- Reindex an entire table
REINDEX TABLE CONCURRENTLY workflow_executions;
```

### Analyze Tables After Bulk Operations

```sql
-- Update planner statistics after large data changes
ANALYZE workflow_executions;
ANALYZE audit_logs;
ANALYZE agent_actions;

-- Analyze all tables
ANALYZE;
```

### Vacuum Maintenance

```sql
-- Check autovacuum settings
SHOW autovacuum;
SHOW autovacuum_vacuum_threshold;
SHOW autovacuum_vacuum_scale_factor;

-- Manual vacuum for specific tables
VACUUM (VERBOSE, ANALYZE) workflow_executions;
VACUUM (VERBOSE, ANALYZE) audit_logs;

-- Full vacuum (locks table -- use during maintenance window only)
VACUUM FULL audit_logs;
```

---

## Dead Letter Queue Cleanup

The DLQ (`dlq_entries` table) stores Kafka messages that failed processing.

### View DLQ Status

```sql
-- Summary by topic and status
SELECT
  topic,
  status,
  COUNT(*) AS count,
  MIN(created_at) AS oldest,
  MAX(created_at) AS newest
FROM dlq_entries
GROUP BY topic, status
ORDER BY count DESC;

-- Recent failures
SELECT
  id,
  topic,
  error,
  retry_count,
  max_retries,
  status,
  created_at
FROM dlq_entries
WHERE status = 'pending'
ORDER BY created_at DESC
LIMIT 20;
```

### Retry DLQ Entries

```sql
-- Mark entries for retry (reset status to 'pending' and increment retry count)
UPDATE dlq_entries
SET
  status = 'pending',
  retry_count = retry_count + 1
WHERE status = 'failed'
  AND retry_count < max_retries
  AND topic = 'workflow.execution.started';

-- Check retry-eligible entries
SELECT COUNT(*) FROM dlq_entries
WHERE status = 'failed' AND retry_count < max_retries;
```

### Purge Old DLQ Entries

```sql
-- Archive processed entries older than 30 days
DELETE FROM dlq_entries
WHERE status = 'processed'
  AND processed_at < NOW() - INTERVAL '30 days';

-- Archive failed entries older than 90 days (after investigation)
DELETE FROM dlq_entries
WHERE status = 'failed'
  AND created_at < NOW() - INTERVAL '90 days';

-- Count remaining entries
SELECT status, COUNT(*) FROM dlq_entries GROUP BY status;
```

---

## Audit Log Archival

The `audit_logs` and `agent_actions` tables grow continuously and should be archived periodically to maintain query performance.

### Archival Strategy

| Data Age          | Location                        | Query Access    |
|-------------------|---------------------------------|-----------------|
| 0-90 days         | Primary database (hot storage)  | Full SQL access |
| 90 days - 1 year  | S3 Parquet files (warm storage) | Athena queries  |
| 1+ years          | S3 Glacier (cold storage)       | Restore on demand |

### Export Audit Logs to S3

```bash
# Port-forward to database
kubectl port-forward svc/adwp-postgres 5433:5432 -n adwp &

# Export old audit logs as CSV
psql -h localhost -p 5433 -U adwp -d adwp -c "\COPY (
  SELECT * FROM audit_logs
  WHERE timestamp < NOW() - INTERVAL '90 days'
  ORDER BY timestamp
) TO '/tmp/audit_logs_archive.csv' WITH CSV HEADER"

# Convert to Parquet (using Python)
python3 -c "
import pandas as pd
df = pd.read_csv('/tmp/audit_logs_archive.csv')
df.to_parquet('/tmp/audit_logs_archive.parquet', index=False)
print(f'Exported {len(df)} rows')
"

# Upload to S3
ARCHIVE_DATE=$(date +%Y%m%d)
aws s3 cp /tmp/audit_logs_archive.parquet \
  s3://adwp-archives/audit_logs/${ARCHIVE_DATE}/audit_logs.parquet

# Upload agent actions similarly
psql -h localhost -p 5433 -U adwp -d adwp -c "\COPY (
  SELECT * FROM agent_actions
  WHERE timestamp < NOW() - INTERVAL '90 days'
  ORDER BY timestamp
) TO '/tmp/agent_actions_archive.csv' WITH CSV HEADER"
```

### Purge Archived Records

**CAUTION:** Only purge after verifying the S3 archive is complete and readable.

```sql
-- Verify archive exists in S3 before purging
-- aws s3 ls s3://adwp-archives/audit_logs/<date>/

-- Delete archived audit logs
DELETE FROM audit_logs
WHERE timestamp < NOW() - INTERVAL '90 days'
  AND id IN (
    SELECT id FROM audit_logs
    WHERE timestamp < NOW() - INTERVAL '90 days'
    LIMIT 10000  -- batch deletion to avoid long locks
  );

-- Repeat until no more rows to delete
-- Then vacuum to reclaim space
VACUUM (VERBOSE) audit_logs;

-- Same for agent_actions
DELETE FROM agent_actions
WHERE timestamp < NOW() - INTERVAL '90 days'
  AND id IN (
    SELECT id FROM agent_actions
    WHERE timestamp < NOW() - INTERVAL '90 days'
    LIMIT 10000
  );

VACUUM (VERBOSE) agent_actions;
```

### Archival Automation

Consider setting up a cron job or Kubernetes CronJob to automate the archival process:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: audit-log-archival
  namespace: adwp
spec:
  schedule: "0 3 1 * *"  # First day of every month at 3 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: archival
              image: adwp/db-maintenance:latest
              command: ["python", "scripts/archive_audit_logs.py"]
              envFrom:
                - secretRef:
                    name: adwp-db-credentials
          restartPolicy: OnFailure
```
