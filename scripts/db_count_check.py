import sqlite3
from pathlib import Path

db_path = Path("data/ibvap_dev.db")
if not db_path.exists():
    print(f"ERROR: {db_path} does not exist!")
    exit(1)

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()
tables = [r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print(f"Database: {db_path} (Size: {db_path.stat().st_size:,} bytes)")
print("Tables:", tables)

total_records = 0
for t in sorted(tables):
    count = cursor.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
    total_records += count
    print(f"  - {t}: {count:,} records")

print(f"Total across all tables: {total_records:,}")
conn.close()
