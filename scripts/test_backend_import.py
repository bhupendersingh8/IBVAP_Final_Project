import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

print("Importing apps.backend.main...")
try:
    from apps.backend.main import app
    print("SUCCESS: FastAPI app imported successfully!")
    print(f"Title: {app.title}")
    print(f"Version: {app.version}")
    print(f"Routes: {len(app.routes)} routes registered")
    for r in app.routes:
        print(f"  - {getattr(r, 'path', str(r))}")
except Exception as e:
    import traceback
    print("FAILED to import apps.backend.main:")
    traceback.print_exc()
    sys.exit(1)
