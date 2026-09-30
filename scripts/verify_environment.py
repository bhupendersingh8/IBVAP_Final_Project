"""
IBVAP — scripts/verify_environment.py
================================
Validates that all critical Python packages are installed and functional.
"""

import sys
import importlib

def check_module(module_name: str, friendly_name: str = None) -> bool:
    try:
        mod = importlib.import_module(module_name)
        version = getattr(mod, '__version__', 'Installed')
        print(f"✅ {friendly_name or module_name:<20} {version}")
        return True
    except ImportError:
        print(f"❌ {friendly_name or module_name:<20} MISSING")
        return False

def verify():
    print("====================================")
    print(" IBVAP Environment Verification")
    print("====================================\n")
    
    modules = [
        ("fastapi", "FastAPI"),
        ("sqlalchemy", "SQLAlchemy"),
        ("alembic", "Alembic"),
        ("pydantic", "Pydantic"),
        ("cv2", "OpenCV"),
        ("ultralytics", "YOLOv8"),
        ("easyocr", "EasyOCR"),
        ("torch", "PyTorch"),
        ("structlog", "Structlog"),
        ("passlib", "Passlib"),
        ("jose", "python-jose")
    ]
    
    all_ok = True
    for mod, name in modules:
        if not check_module(mod, name):
            all_ok = False

    print("\n--- Hardware Check ---")
    try:
        import torch
        if torch.cuda.is_available():
            print(f"🚀 PyTorch CUDA: Enabled ({torch.cuda.get_device_name(0)})")
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            print("🚀 PyTorch MPS (Mac): Enabled")
        else:
            print("🐢 PyTorch CPU Mode: Active (No GPU/CUDA detected)")
    except ImportError:
        print("⚠️ PyTorch not installed. Hardware mode unknown.")

    print("\n====================================")
    if all_ok:
        print("🎉 STATUS: ALL OK! Environment is ready.")
    else:
        print("⚠️ STATUS: FAILED. Please install missing packages.")
        print("   Run: pip install -r requirements/dev.txt -r requirements/ml.txt")

if __name__ == "__main__":
    verify()
