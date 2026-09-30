# scripts/reset_sih_demo.ps1
# Cleanly resets demo database state and evidence files without touching code, configs, or models.

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " IBVAP SIH DEMO RESET" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

$IBVAP_ROOT = (Resolve-Path "$PSScriptRoot\..").Path
$DB_PATH = "$IBVAP_ROOT\data\ibvap_dev.db"
$EVIDENCE_DIR = "$IBVAP_ROOT\data\evidence"

# 1. Clean Evidence snapshots
if (Test-Path $EVIDENCE_DIR) {
    $evidenceCount = (Get-ChildItem -Path $EVIDENCE_DIR -Filter *.jpg).Count
    Remove-Item -Path "$EVIDENCE_DIR\*.jpg" -Force -ErrorAction SilentlyContinue
    Write-Host "[OK] Cleaned $evidenceCount evidence snapshot files from $EVIDENCE_DIR" -ForegroundColor Green
} else {
    New-Item -ItemType Directory -Force -Path $EVIDENCE_DIR | Out-Null
    Write-Host "[OK] Created clean evidence directory: $EVIDENCE_DIR" -ForegroundColor Green
}

# 2. Reset Database Tables (incidents, events, evidence, detections, tracks)
if (Test-Path $DB_PATH) {
    Write-Host "[INFO] Purging incident & event records from SQLite: $DB_PATH..." -ForegroundColor Yellow
    $pythonCmd = @"
import sqlite3
conn = sqlite3.connect(r'$DB_PATH')
cur = conn.cursor()
tables = ['incidents', 'events', 'evidence', 'detections', 'tracks', 'feedback']
for t in tables:
    try:
        cur.execute(f'DELETE FROM {t};')
    except Exception as e:
        print(f'Skipped {t}: {e}')
conn.commit()
conn.close()
print('SUCCESS')
"@
    $res = python -c "$pythonCmd"
    if ($res -match "SUCCESS") {
        Write-Host "[OK] Database incident tables successfully cleared." -ForegroundColor Green
    } else {
        Write-Host "[WARN] Database cleanup returned: $res" -ForegroundColor Yellow
    }
} else {
    Write-Host "[INFO] No existing SQLite database found at $DB_PATH to reset." -ForegroundColor Gray
}

Write-Host ""
Write-Host "Demo reset complete. Dashboard will show 0 Active Alerts and 0 Incidents." -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
