# IBVAP — Development Environment Audit

**Generated:** 2026-09-07 19:56:37  
**Script:** `scripts/system_check.py`

```

======================================================================
  IBVAP — Development Machine Audit
======================================================================
  Generated: 2026-09-07 19:56:32
  Script:    scripts/system_check.py

  ── Operating System ──
  ✅  OS                               Windows 11 (AMD64)
  ℹ️   Version                          10.0.26200

  ── Hardware ──
  ✅  CPU                              AMD64 Family 25 Model 124 Stepping 0, AuthenticAMD
  ✅  Physical Cores                   6
  ✅  Logical Cores                    12
  ℹ️   CPU Frequency                    3201 MHz
  ✅  RAM Total                        15.3 GB
  ℹ️   RAM Available                    5.6 GB
  ✅  Disk Free                        144.6 GB
  ℹ️   Disk Total                       265.1 GB

  ── Python ──
  ✅  Python                           3.14.6
  ✅  pip                              26.1.2
  ℹ️   Path                             C:\Users\ddipa\AppData\Local\Programs\Python\Pytho

  ── Node.js ──
  ✅  Node.js                          v24.19.0
  ✅  npm                              11.17.0

  ── Git ──
  ❌  Git                              NOT FOUND

  ── Docker ──
  ⚠️   Docker                           NOT FOUND — Install Docker Desktop
  ⚠️   Docker Compose                   NOT FOUND
        → Install: https://www.docker.com/products/docker-desktop/ 

  ── NVIDIA GPU (nvidia-smi) ──
  ✅  NVIDIA GPU                       0  NVIDIA GeForce RTX 3050 ...  WDDM
  ✅  Driver Version                   
  ✅  CUDA Version (driver)            13.1
  ✅  VRAM                             4096 MiB

  ── PyTorch / CUDA (Python) ──
  ✅  PyTorch                          2.14.0+cpu
  ⚠️   CUDA Available                   False
        → Running in CPU mode          

======================================================================
  Summary & Recommendations
======================================================================

  ❌ MISSING (must install):
     • Docker Desktop — https://www.docker.com/products/docker-desktop/
     • Git — https://git-scm.com

======================================================================
```

---
*This file is auto-generated. Re-run `python scripts/system_check.py` to update.*