# POSTGRESQL_PRODUCTION_GUIDE.md — Production Database Architecture & Migration Runbook

**System:** Intelligent Border Video Analytics Platform (IBVAP)  
**Target RDBMS:** PostgreSQL 15.x / 16.x with TimescaleDB / pgvector extension options  
**Development Baseline:** SQLite 3 (single-file zero-configuration local deployment)  
**Security Classification:** MHA / Operational Production Standard  

---

## 1. Overview & Architectural Justification

In development and standalone BOP (Border Out Post) single-node field deployments, IBVAP operates on SQLite (`data/ibvap.db`) with `WAL` (Write-Ahead Logging) mode.

For multi-camera sector headquarters, checkpost clusters, and regional command centers where dozens of RTSP streams write concurrent telemetry, detections, ANPR reads, and cryptographic blocks, **PostgreSQL is the designated production standard**.

### Why PostgreSQL for Regional Command Centers?
1. **High Concurrent Write Throughput:** Decoupled MVCC allows simultaneous writes from multiple inference workers while operator dashboards run analytical queries.
2. **Table Partitioning:** Automatic time-series partitioning of high-volume tables (`detections`, `tracks`, `events`) prevents table scan degradation over months of 24/7 surveillance.
3. **Robust Connection Pooling:** Native asynchronous pool management with `asyncpg` supports high-frequency telemetry without connection exhaustion.
4. **Binary & JSONB Indexing:** Fast GIN indexing on `bbox_json`, `contributing_signals_json`, and license plate matching.

---

## 2. Environment Configuration

To switch IBVAP from SQLite to PostgreSQL, update the `.env` configuration file or environment variables:

```bash
# SQLite (Default Local Dev / Low-Power Standalone BOP)
# DATABASE_URL=sqlite+aiosqlite:///./data/ibvap.db

# Production PostgreSQL (Multi-Camera Sector Command)
DATABASE_URL=postgresql+asyncpg://ibvap_admin:SecureBorderPass2026@localhost:5432/ibvap_production
DATABASE_URL_SYNC=postgresql+psycopg2://ibvap_admin:SecureBorderPass2026@localhost:5432/ibvap_production
```

### Connection Pool Configuration (`apps/backend/database/connection.py`)

In production mode, configure pool parameters according to stream volume:

```python
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=20,              # Persistent connections
    max_overflow=10,           # Burst capacity for simultaneous alert surges
    pool_timeout=30,           # Seconds to wait before timing out
    pool_recycle=1800,         # Recycle connections every 30 minutes
    pool_pre_ping=True,        # Verify connection health before handing to worker
)
```

---

## 3. Database Schema & Indexing Strategy

All 15 tables are defined in `apps/backend/database/models.py` using SQLAlchemy 2.0 DeclarativeBase:

| Table | High-Volume? | Index Optimization | Retention Policy |
|---|:---:|---|---|
| `cameras` | No | `id` (PK), `enabled` | Permanent |
| `zones` | No | `camera_id` (FK), `enabled` | Permanent |
| `detections` | **YES** | `camera_id, timestamp`, `class_name` | 30–90 Days (Partitioned) |
| `tracks` | **YES** | `camera_id, track_id`, `state` | 30–90 Days (Partitioned) |
| `events` | High | `camera_id, timestamp`, `severity` | 180 Days |
| `incidents` | Moderate | `camera_id, status`, `severity`, `acknowledged` | 1–3 Years |
| `evidence` | Moderate | `incident_id`, `sha256` | 1–3 Years |
| `anpr_observations` | Moderate | `plate_text`, `camera_id, timestamp`, `status` | 1 Year |
| `hash_chain` | Moderate | `sequence_id` (PK), `current_hash`, `incident_id` | Immutable / Permanent |
| `remembrance_profiles` | Moderate | `global_id`, `class_name`, `license_plate` | Permanent |
| `feedback` | Low | `incident_id`, `label` | Permanent |
| `models` & `evaluations` | Low | `name, version`, `state` | Permanent |
| `audit_logs` | Moderate | `timestamp, actor_id`, `action` | Immutable / 3 Years |

### Recommended Partitioning SQL for Detections

```sql
-- Create partitioned detections table by month
CREATE TABLE detections_partitioned (
    id UUID NOT NULL,
    camera_id VARCHAR(64) NOT NULL,
    frame_id INTEGER NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    class_name VARCHAR(32) NOT NULL,
    confidence FLOAT NOT NULL,
    bbox_json JSONB NOT NULL,
    model_name VARCHAR(64),
    model_version VARCHAR(32),
    inference_latency_ms FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (id, timestamp)
) PARTITION BY RANGE (timestamp);

-- Example Monthly Partitions
CREATE TABLE detections_2026_09 PARTITION OF detections_partitioned
    FOR VALUES FROM ('2026-09-01 00:00:00+00') TO ('2026-10-01 00:00:00+00');

CREATE TABLE detections_2026_10 PARTITION OF detections_partitioned
    FOR VALUES FROM ('2026-10-01 00:00:00+00') TO ('2026-11-01 00:00:00+00');
```

---

## 4. Alembic Migration Procedure

IBVAP uses Alembic for declarative schema migrations:

### Step 1: Initialize Database
```bash
# Ensure target PostgreSQL instance is reachable
psql -h localhost -U ibvap_admin -d ibvap_production -c "SELECT 1;"
```

### Step 2: Apply Migrations
```bash
# Run migrations to head
alembic upgrade head
```

### Step 3: Verify Table Creation
```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;
```

---

## 5. Offline Border Outpost (BOP) Sync Strategy

In frontline border posts with intermittent satellite / optical fiber backhaul:

```
[BOP Edge Node (Intel i3 / Jetson)]
        │
  (Local Ingestion & Inference)
        │
   [Local SQLite DB] ─── Offline buffer (continuous operation)
        │
  (Network Available)
        │
   [Store & Forward Sync Agent]
        │ (TLS 1.3 / Mutual Auth)
        ▼
[Regional HQ Production PostgreSQL]
```

1. **Autonomous Operation:** When wide-area link drops, the edge node continues writing to local SQLite without disruption.
2. **Delta Sync:** Upon reconnection, the sync agent pushes non-synchronized incidents, evidence digests, and ANPR reads to HQ PostgreSQL.
3. **Hash Chain Integrity:** Each block in the cryptographic hash chain is verified sequentially so edge-generated blocks seamlessly integrate into central command archives.

---

## 6. Maintenance & Backup Schedule

* **Daily:** Automated logical backup of critical tables:
  ```bash
  pg_dump -U ibvap_admin -d ibvap_production -t incidents -t evidence -t hash_chain -t audit_logs -F c -f ibvap_critical_$(date +%Y%m%d).dump
  ```
* **Weekly:** Vacuum analyze:
  ```sql
  VACUUM ANALYZE detections;
  VACUUM ANALYZE tracks;
  ```
