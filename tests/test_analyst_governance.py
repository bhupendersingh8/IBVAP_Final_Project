import pytest
import os
import json
import time
from pathlib import Path
from datetime import datetime, timezone
from fastapi.testclient import TestClient

# Add project root to sys path
import sys
project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

from apps.backend.main import app
from crypto_ledger import CryptoEvidenceLedger

@pytest.fixture
def clean_ledger(tmp_path):
    # Use a temporary SQLite ledger for testing to avoid touching production data
    db_path = tmp_path / "test_ledger.sqlite3"
    ledger = CryptoEvidenceLedger(db_path=db_path, use_sqlite_fallback=True)
    return ledger

def test_governance_disposition_lifecycle(clean_ledger):
    # 1. Create a legacy block
    import numpy as np
    dummy_frame = np.zeros((100, 100, 3), dtype=np.uint8)
    block = clean_ledger.commit_event(
        frame=dummy_frame,
        camera_id="CAM-01",
        event_type="TEST",
        severity="INFO"
    )
    assert block.sequence_id > 0
    
    # Check default (legacy) fallback in get_latest_dispositions (should be empty initially)
    dispositions = clean_ledger.get_latest_dispositions()
    assert block.sequence_id not in dispositions

    # 2. Test Invalid Disposition Rejected
    with pytest.raises(ValueError, match="Invalid disposition"):
        clean_ledger.update_disposition(block.sequence_id, "DESTROY", "analyst_1", "Invalid test")

    # 3. Valid ACCEPT
    time.sleep(0.01)
    assert clean_ledger.update_disposition(block.sequence_id, "ACCEPT", "analyst_1", "Clear") is True
    assert clean_ledger.get_latest_dispositions()[block.sequence_id] == "ACCEPT"

    # 4. Valid REVIEW
    time.sleep(0.01)
    assert clean_ledger.update_disposition(block.sequence_id, "REVIEW", "analyst_2", "Double check") is True
    assert clean_ledger.get_latest_dispositions()[block.sequence_id] == "REVIEW"

    # 5. Valid QUARANTINE
    time.sleep(0.01)
    assert clean_ledger.update_disposition(block.sequence_id, "QUARANTINE", "analyst_3", "Malicious") is True
    assert clean_ledger.get_latest_dispositions()[block.sequence_id] == "QUARANTINE"

    # 6. Audit Trail Check (Direct SQL to verify previous disposition tracking)
    conn = clean_ledger._get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT previous_disposition, new_disposition FROM governance_audit WHERE sequence_id = ? ORDER BY timestamp ASC", (block.sequence_id,))
    rows = cursor.fetchall()
    conn.close()
    
    assert len(rows) == 3
    assert rows[0] == ("REVIEW", "ACCEPT")      # First update assumed REVIEW as previous
    assert rows[1] == ("ACCEPT", "REVIEW")      # Second update
    assert rows[2] == ("REVIEW", "QUARANTINE")  # Third update

def test_api_governance_endpoints():
    client = TestClient(app)
    response = client.post("/api/v1/evidence/ledger_blocks/999/disposition", json={
        "disposition": "INVALID_STATE",
        "reason": "Testing validation"
    })
    assert response.status_code == 400
    assert "Invalid disposition" in response.text
