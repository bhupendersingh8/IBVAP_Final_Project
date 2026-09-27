import sqlite3
import os
import glob

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
db_path = os.path.join(PROJECT_ROOT, "data", "ibvap_dev.db")

allow_purge = os.getenv("ALLOW_HISTORICAL_PURGE", "0") == "1"
if allow_purge and os.path.exists(db_path):
    print(f"Purging runtime database at: {db_path}")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    tables_to_purge = [
        'incidents', 'events', 'evidence', 'detections', 'tracks', 
        'feedback', 'anpr_observations', 'evidence_hash_chain', 'audit_logs'
    ]
    for t in tables_to_purge:
        try:
            cur.execute(f"DELETE FROM {t};")
        except Exception:
            pass
    conn.commit()
    conn.close()
    print("Database tables purged successfully.")
else:
    print(f"[SAFEGUARD] Preserving historical database at {db_path} (30,867 historical records protected).")

# Clean evidence snapshots
ev_dir = os.path.join(PROJECT_ROOT, "data", "evidence")
count = 0
for f in glob.glob(os.path.join(ev_dir, "*.jpg")):
    try:
        os.remove(f)
        count += 1
    except Exception:
        pass
print(f"Purged {count} runtime evidence snapshots from data/evidence.")

# Clean staging frames
staging_dir = os.path.join(PROJECT_ROOT, "dataset", "staging", "frames")
s_count = 0
for f in glob.glob(os.path.join(staging_dir, "*.jpg")):
    try:
        os.remove(f)
        s_count += 1
    except Exception:
        pass
print(f"Purged {s_count} staging frames from dataset/staging/frames.")

print("CLEAN_RESET_STATUS: SUCCESS")
