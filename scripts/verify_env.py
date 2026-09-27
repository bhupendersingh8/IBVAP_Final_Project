import sys
import torch
import cv2
import ultralytics
import fastapi
import lap
import aiosqlite
import uvicorn
import pydantic
import sqlalchemy

print("=" * 60)
print("IBVAP DELL HOST ENVIRONMENT VERIFICATION")
print("=" * 60)
print(f"Python:       {sys.version.split()[0]} ({sys.executable})")
print(f"PyTorch:      {torch.__version__} (CUDA Available: {torch.cuda.is_available()})")
print(f"OpenCV:       {cv2.__version__}")
print(f"Ultralytics:  {ultralytics.__version__}")
print(f"FastAPI:      {fastapi.__version__}")
print(f"Uvicorn:      {uvicorn.__version__}")
print(f"Lap (lapx):   {lap.__version__}")
print(f"AioSQLite:    {aiosqlite.__version__}")
print(f"SQLAlchemy:   {sqlalchemy.__version__}")
print(f"Pydantic:     {pydantic.__version__}")
print("=" * 60)
print("ENVIRONMENT STATUS: ALL VERIFIED (CPU-FIRST)")
print("=" * 60)
