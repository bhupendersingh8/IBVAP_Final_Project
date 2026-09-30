# Third-Party Licenses Registry

This registry tracks the open-source and commercial licensing terms for third-party software, libraries, and models incorporated into IBVAP.

| Component | Version | Source / Vendor | License | Commercial / Proprietary Deployment Notes |
| :--- | :--- | :--- | :--- | :--- |
| **MediaMTX** | 1.20.1 | bluenviron/mediamtx | MIT | Permissive. Freely usable in commercial and open-source deployments without copyleft requirements. |
| **FFmpeg** | 9.0.1 | Gyan.FFmpeg (github.com/GyanD) | GPLv3 (Gyan full build) | `REVIEW_REQUIRED`: FFmpeg core is LGPL 2.1+, but the Gyan "full" build includes GPLv3 components (x264, x265). If deploying IBVAP as closed-source proprietary software, use an LGPL-only build. |
| **Ultralytics YOLOv8** | 8.2+ / 8.4+ | Ultralytics Inc. | AGPL-3.0 | `COPYLEFT NOTICE`: AGPL-3.0 applies for open-source research and prototype usage. Closed-source/proprietary commercial deployments require an Ultralytics Enterprise License. |
| **EasyOCR** | 1.7.2 | JaidedAI (github.com/JaidedAI/EasyOCR) | Apache-2.0 | Permissive. Allowed in commercial, academic, and open-source applications without copyleft or disclosure requirements. |
| **PyTorch (torch)** | 2.14.0 | PyTorch Foundation | BSD-3-Clause | Permissive. Compatible with commercial and open-source usage. |
| **torchvision** | 0.29.0 | PyTorch Foundation | BSD-3-Clause | Permissive. Compatible with commercial and open-source usage. |
| **OpenCV (opencv-python)** | 5.0.0+ | OpenCV Foundation | Apache-2.0 | Permissive. Standard computer vision library. |
| **SciPy** | 1.18.1 | SciPy Community | BSD-3-Clause | Permissive. Standard scientific computing library. |
| **Shapely** | 2.1.2 | Shapely Community | BSD-3-Clause | Permissive. Planar geometric computation. |
| **scikit-image** | 0.26.0 | scikit-image team | BSD-3-Clause | Permissive. Image processing utilities. |
| **FastAPI** | 0.139.2 | Tiangolo (Sebastián Ramírez) | MIT | Permissive. Standard Python web framework. |
| **Uvicorn** | 0.51.0 | Encode | BSD-3-Clause | Permissive ASGI server. |
| **WebSockets** | 17.1 | Aymeric Augustin | BSD-3-Clause | Permissive WebSocket implementation. |
| **SQLAlchemy** | 2.0.52 | Mike Bayer | MIT | Permissive database ORM. |
| **Playwright** | 1.62.0 | Microsoft Corporation | Apache-2.0 | Permissive browser automation library. |
| **React** | 18.3.1 | Meta Platforms, Inc. | MIT | Permissive frontend UI library. |
| **Vite** | 5.4+ | Evan You | MIT | Permissive frontend tooling & dev server. |
| **TailwindCSS** | 3.4+ | Tailwind Labs, Inc. | MIT | Permissive styling framework. |
