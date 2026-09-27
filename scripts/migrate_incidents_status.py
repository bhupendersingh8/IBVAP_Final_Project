from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
conn = sqlite3.connect(str(PROJECT_ROOT / "data" / "ibvap_dev.db"))
cur = conn.cursor()
cur.execute("PRAGMA table_info(incidents)")
cols = [c[1] for c in cur.fetchall()]
print("Current columns in incidents:", cols)

if "status" not in cols:
    print("Adding 'status' column...")
    cur.execute("ALTER TABLE incidents ADD COLUMN status VARCHAR(20) DEFAULT 'NEW'")
    # Backfill based on acknowledged column
    cur.execute("UPDATE incidents SET status = 'ACKNOWLEDGED' WHERE acknowledged = 1")
    cur.execute("UPDATE incidents SET status = 'NEW' WHERE acknowledged = 0 OR acknowledged IS NULL")
    conn.commit()
    print("Migration successful.")
else:
    print("'status' column already exists.")

cur.execute("PRAGMA table_info(incidents)")
print("Updated columns:", [c[1] for c in cur.fetchall()])
conn.close()
