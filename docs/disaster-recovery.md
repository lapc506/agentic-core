# Disaster Recovery & Backup Patterns

## RPO / RTO Targets

| Store | RPO (max data loss) | RTO (max downtime) | Strategy |
|-------|--------------------|--------------------|----------|
| PostgreSQL (sessions, checkpoints) | 5 minutes | 15 minutes | WAL archiving + streaming replication |
| Redis (conversation cache) | 1 hour | 5 minutes | AOF persistence + RDB snapshots |
| FalkorDB (knowledge graph) | 24 hours | 30 minutes | RDB snapshots |
| pgvector (embeddings) | 24 hours | 1 hour | pg_dump + re-embed from source |

## PostgreSQL Backup

### Automated (AWS RDS)
- Automated backups: 7-day retention (dev), 30-day (production)
- Point-in-time recovery via WAL archiving
- Multi-AZ for production

### Manual
```bash
# Full backup
pg_dump -h $PG_HOST -U agentic -Fc agentic > backup_$(date +%Y%m%d).dump

# WAL archiving (postgresql.conf)
archive_mode = on
archive_command = 'aws s3 cp %p s3://backups/wal/%f'

# Restore
pg_restore -h $PG_HOST -U agentic -d agentic backup_20260325.dump
```

## Redis Backup

### Configuration
```
# redis.conf
appendonly yes
appendfsync everysec
save 900 1
save 300 10
save 60 10000
```

### S3 Backup Script
```bash
# Trigger RDB snapshot
redis-cli -h $REDIS_HOST BGSAVE
sleep 5
# Copy to S3
aws s3 cp /data/dump.rdb s3://backups/redis/dump_$(date +%Y%m%d).rdb
```

### Restore
```bash
aws s3 cp s3://backups/redis/dump_20260325.rdb /data/dump.rdb
redis-server --appendonly no  # Load RDB first, then enable AOF
```

## FalkorDB Backup

```bash
# FalkorDB uses Redis protocol — same backup strategy
redis-cli -h $FALKORDB_HOST -p 6380 BGSAVE
aws s3 cp /data/dump.rdb s3://backups/falkordb/dump_$(date +%Y%m%d).rdb
```

## pgvector (Embeddings)

Embeddings can be re-generated from source documents. Backup strategy:

1. **Source documents**: Store originals in S3 (primary backup)
2. **pg_dump**: Include embeddings table in PostgreSQL backup
3. **Re-embed**: If backup is lost, re-run RAG pipeline ingestion

```bash
# Backup embeddings table specifically
pg_dump -h $PG_HOST -U agentic -t agent_embeddings -Fc agentic > embeddings_backup.dump
```

## DR Testing Runbook

### Monthly Test (30 minutes)

1. **Pre-test**: Record current state (session count, last message timestamps)
2. **Simulate**: Stop primary PostgreSQL
3. **Failover**: Verify RDS automatic failover (Multi-AZ) or promote standby
4. **Verify**: Run healthcheck, create session, send message
5. **Restore**: Return to primary
6. **Post-test**: Compare state, document results

### Quarterly Test (2 hours)

1. Full restore from S3 backups to a fresh environment
2. Verify all stores: PG sessions, Redis conversations, FalkorDB graph, pgvector search
3. Run integration test suite against restored environment
4. Document recovery time and any data loss

## Kubernetes CronJobs

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: agentic-pg-backup
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: backup
              image: postgres:16
              command: ["sh", "-c"]
              args:
                - pg_dump -h $PG_HOST -U agentic -Fc agentic | aws s3 cp - s3://backups/pg/$(date +%Y%m%d).dump
              envFrom:
                - secretRef:
                    name: agentic-db-credentials
          restartPolicy: OnFailure
```
