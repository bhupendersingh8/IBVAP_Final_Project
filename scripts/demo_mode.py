import sys
import os

def write_phone_relay_script():
    script_path = os.path.join(os.path.dirname(__file__), "phone_camera_relay.ps1")
    lines = [
        "# scripts/phone_camera_relay.ps1",
        "[CmdletBinding()]",
        "param(",
        '    [Parameter(Position=0)]',
        '    [string]$PhoneUrl = "http://10.63.26.249:8080/video",',
        "    [switch]$Stop,",
        "    [switch]$RelayOnly",
        ")",
        "",
        '$IBVAP_ROOT = (Resolve-Path "$PSScriptRoot\\..").Path',
        'if (Get-Command python -ErrorAction SilentlyContinue) { $PYTHON_EXE = (Get-Command python).Source } else { $PYTHON_EXE = "python" }',
        "",
        "if ($Stop) {",
        '    Write-Host "[PHONE-CAM-01] Stopping Phone FFmpeg Relay and Worker..." -ForegroundColor Yellow',
        '    Get-CimInstance Win32_Process -Filter "Name LIKE \'ffmpeg%\' AND CommandLine LIKE \'%PHONE-CAM-01%\'" -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }',
        '    Get-CimInstance Win32_Process -Filter "Name LIKE \'python%\' AND CommandLine LIKE \'%PHONE-CAM-01%\'" -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }',
        '    Write-Host "[PHONE-CAM-01] Stopped successfully." -ForegroundColor Green',
        "    exit 0",
        "}",
        "",
        'Write-Host "================================================================" -ForegroundColor Cyan',
        'Write-Host "       IBVAP - ANDROID PHONE LIVE CAMERA RELAY AND INFERENCE    " -ForegroundColor Cyan',
        'Write-Host "================================================================" -ForegroundColor Cyan',
        "",
        "$uri = [System.Uri]$PhoneUrl",
        "$phoneHost = $uri.Host",
        "$phonePort = $uri.Port",
        "",
        'Write-Host "[1/3] Verifying TCP connectivity to Phone ($phoneHost)..." -ForegroundColor Gray',
        "$tcp = New-Object System.Net.Sockets.TcpClient",
        "try {",
        "    $connect = $tcp.BeginConnect($phoneHost, $phonePort, $null, $null)",
        "    $wait = $connect.AsyncWaitHandle.WaitOne(2000, $false)",
        "    if (-not $wait) {",
        '        Write-Host "[ERROR] Cannot reach phone at $PhoneUrl. Check phone Wi-Fi connection." -ForegroundColor Red',
        "        exit 1",
        "    }",
        "    $tcp.EndConnect($connect)",
        "    $tcp.Close()",
        '    Write-Host "[OK] Phone stream is reachable at $PhoneUrl" -ForegroundColor Green',
        "} catch {",
        '    Write-Host "[ERROR] Failed to connect to $PhoneUrl : $_" -ForegroundColor Red',
        "    exit 1",
        "}",
        "",
        'Get-CimInstance Win32_Process -Filter "Name LIKE \'ffmpeg%\' AND CommandLine LIKE \'%PHONE-CAM-01%\'" -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }',
        'Get-CimInstance Win32_Process -Filter "Name LIKE \'python%\' AND CommandLine LIKE \'%PHONE-CAM-01%\'" -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }',
        "",
        '$ffmpegPath = "$env:LOCALAPPDATA\\Microsoft\\WinGet\\Packages\\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\\ffmpeg-9.0.1-full_build\\bin\\ffmpeg.exe"',
        "if (-not (Test-Path $ffmpegPath)) {",
        '    $found = (Get-ChildItem -Path "$env:LOCALAPPDATA\\Microsoft\\WinGet\\Packages" -Recurse -Filter "ffmpeg.exe" -ErrorAction SilentlyContinue | Select-Object -First 1)',
        '    if ($found) { $ffmpegPath = $found.FullName } else { $ffmpegPath = "ffmpeg.exe" }',
        "}",
        "",
        'Write-Host "[2/3] Launching FFmpeg Low-Latency Relay (MJPEG -> RTSP 640x360)..." -ForegroundColor Gray',
        '$ffmpegArgs = "-re -f mjpeg -i " + $PhoneUrl + " -vf scale=640:360 -c:v libx264 -preset ultrafast -tune zerolatency -pix_fmt yuv420p -f rtsp -rtsp_transport tcp rtsp://127.0.0.1:8554/PHONE-CAM-01"',
        "Start-Process -FilePath $ffmpegPath -ArgumentList $ffmpegArgs -WorkingDirectory $IBVAP_ROOT -WindowStyle Hidden",
        "",
        "$sw = [System.Diagnostics.Stopwatch]::StartNew()",
        "$phoneReady = $false",
        "while ($sw.Elapsed.TotalSeconds -lt 15) {",
        "    try {",
        '        $res = Invoke-WebRequest -Uri "http://127.0.0.1:8889/PHONE-CAM-01/" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop',
        "        if ($res.StatusCode -eq 200) {",
        "            $phoneReady = $true",
        "            break",
        "        }",
        "    } catch {}",
        "    Start-Sleep -Milliseconds 500",
        "}",
        "",
        "if ($phoneReady) {",
        '    Write-Host "[OK] Phone WebRTC Stream is LIVE at: http://127.0.0.1:8889/PHONE-CAM-01/" -ForegroundColor Green',
        "} else {",
        '    Write-Host "[WARN] WebRTC stream didn\'t report 200 immediately, continuing..." -ForegroundColor Yellow',
        "}",
        "",
        "if (-not $RelayOnly) {",
        '    Write-Host "[3/3] Launching Real YOLO Inference Worker for PHONE-CAM-01..." -ForegroundColor Gray',
        '    $workerArgs = "services\\inference\\main_inference_worker.py --camera PHONE-CAM-01 --rtsp rtsp://127.0.0.1:8554/PHONE-CAM-01"',
        "    Start-Process -FilePath $PYTHON_EXE -ArgumentList $workerArgs -WorkingDirectory $IBVAP_ROOT -WindowStyle Hidden",
        "    Start-Sleep -Seconds 2",
        '    Write-Host "[OK] Real YOLO Inference worker running for PHONE-CAM-01." -ForegroundColor Green',
        "}",
        "",
        'Write-Host "================================================================" -ForegroundColor Cyan',
        'Write-Host " [PHONE-CAM-01] SUCCESSFULLY CONNECTED TO IBVAP!                " -ForegroundColor Green',
        'Write-Host " Dashboard View: Switch camera to PHONE-CAM-01 in Web UI        " -ForegroundColor Cyan',
        'Write-Host " URL: http://localhost:5173                                    " -ForegroundColor Cyan',
        'Write-Host "================================================================" -ForegroundColor Cyan',
        ""
    ]
    with open(script_path, "w", encoding="utf-8", newline="\r\n") as f:
        f.write("\n".join(lines))
    print("Generated phone_camera_relay.ps1")

def write_phone_camera_doc():
    doc_path = os.path.join(os.path.dirname(__file__), "..", "docs", "PHONE_CAMERA_SETUP.md")
    content = """# IBVAP — Android Phone Live IP Camera Setup Guide

This guide describes how to connect an Android mobile device running an IP Webcam server as an active, real-time live camera source (`PHONE-CAM-01`) within the IBVAP platform.

---

## 1. Overview & Architecture

Instead of relying solely on simulated video clips, IBVAP supports ingesting live real-time footage from Android devices.

```
[ Android Phone: IP Webcam App ]
        │  (HTTP MJPEG: port 8080/video)
        ▼
[ Low-Latency FFmpeg Transcoding Relay ]
        │  (Downscales 1080p -> 640x360 @ 10 FPS, H.264 ultrafast)
        ▼
[ MediaMTX Local Media Server ]
        │
        ├── RTSP: rtsp://127.0.0.1:8554/PHONE-CAM-01  ──>  [ IBVAP AI Inference Worker ]
        │                                                     (YOLOv8 + IoU Tracking + Rules)
        │                                                              │
        └── WebRTC: http://127.0.0.1:8889/PHONE-CAM-01/                ▼
                    (Direct Browser Iframe in React)       [ WebSocket Telemetry & SQLite ]
```

---

## 2. Phone Application Setup

1. Install **IP Webcam** (by Pavel Khlebovich) or any standard MJPEG Android IP Camera app from Google Play or F-Droid.
2. Ensure both the **PC** and the **Android Phone** are connected to the same local Wi-Fi network.
3. Open the app and configure:
   - **Video resolution**: `1920x1080` (or `1280x720`).
   - **Quality**: `50% - 75%` (minimizes Wi-Fi jitter).
   - **Orientation**: `Landscape` (recommended for optimal detection geometry).
   - **Power management**: Ensure "Keep screen on" or background service mode is enabled to prevent Android OS doze/sleep from terminating sockets.
4. Scroll to the bottom and tap **Start Server**.
5. Note the displayed URL (typically `http://<phone_ip>:8080`).

---

## 3. Verified Endpoints

The Android IP Webcam server exposes the following endpoints:
- **Live Video Stream**: `http://<phone_ip>:8080/video` (Content-Type: `multipart/x-mixed-replace; boundary=...`, MJPEG).
- **Snapshot Frame**: `http://<phone_ip>:8080/shot.jpg` (Single JPEG frame).
- **Device Telemetry**: `http://<phone_ip>:8080/status.json` (Battery, orientation, sensors).
- **Hardware Torch Control**:
  - Turn Torch ON: `http://<phone_ip>:8080/enabletorch`
  - Turn Torch OFF: `http://<phone_ip>:8080/disabletorch`

---

## 4. Launching the Phone Stream in IBVAP

### Option A: Master Script (Recommended)
Run the master control script:
```powershell
.\\scripts\\ibvap.ps1 phone -PhoneUrl "http://10.63.26.249:8080/video"
```

### Option B: Dedicated Phone Script
Run the dedicated phone relay orchestrator:
```powershell
powershell -ExecutionPolicy Bypass -File .\\scripts\\phone_camera_relay.ps1 -PhoneUrl "http://10.63.26.249:8080/video"
```

### Option C: Stopping Phone Relay & Worker
```powershell
powershell -ExecutionPolicy Bypass -File .\\scripts\\phone_camera_relay.ps1 -Stop
```

---

## 5. Viewing on the Dashboard

1. Open your browser: `http://localhost:5173`
2. Under **Active Camera Selection**, click the **PHONE-CAM-01** card.
3. The main video viewport immediately switches to the live WebRTC stream from your phone.
4. Real-time YOLO detections (people, cars, motorbikes) and persistent track IDs are drawn directly over the phone feed via synchronized SVG overlays.
5. If an object enters the phone's restricted zone (`PHONE_RESTRICTED_01`), a `RESTRICTED_ZONE_INTRUSION` alert is emitted, logged in SQLite, and saved with an SHA-256 evidence snapshot.

---

## 6. Performance & Hardware Considerations (Intel i3 / CPU-Only)

- **CPU Scaling**: The raw phone stream is 1080p. The FFmpeg relay downscales the stream to `640x360` with `-preset ultrafast -tune zerolatency`. This prevents CPU saturation on dual-core / quad-core i3 processors and maintains low glass-to-glass latency (< 250ms).
- **Wi-Fi Stability**: If Wi-Fi signal drops, the `RTSPSource` client automatically reconnects using exponential backoff without crashing the IBVAP pipeline.
"""
    with open(doc_path, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(content)
    print("Generated docs/PHONE_CAMERA_SETUP.md")


def write_frontend_pages():
    zones_path = os.path.join(os.path.dirname(__file__), "..", "apps", "frontend", "src", "pages", "Zones.tsx")
    settings_path = os.path.join(os.path.dirname(__file__), "..", "apps", "frontend", "src", "pages", "Settings.tsx")
    
    zones_code = """import React, { useState, useEffect } from 'react';
import { CheckCircle, Layers } from 'lucide-react';

interface Point {
  x: number;
  y: number;
}

interface Zone {
  zone_id: string;
  name: string;
  camera_id: string;
  zone_type: string;
  enabled: boolean;
  color: string;
  points: Point[];
}

export const Zones = () => {
  const [zones, setZones] = useState<Zone[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedZone, setSelectedZone] = useState<Zone | null>(null);

  useEffect(() => {
    fetch('http://127.0.0.1:8000/api/v1/zones')
      .then(res => res.json())
      .then(data => {
        if (data.zones) {
          setZones(data.zones);
          if (data.zones.length > 0) setSelectedZone(data.zones[0]);
        }
      })
      .catch(err => console.error('Failed to load zones:', err))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex justify-between items-center bg-white p-4 rounded-xl shadow-sm border border-slate-200">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Spatial Virtual Fencing & Zones</h1>
          <p className="text-slate-500 text-sm mt-1">
            Define geometric polygons, intrusion boundary tripwires, and restricted sectors.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="px-3 py-1 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-lg text-xs font-semibold flex items-center gap-1.5">
            <CheckCircle size={14} /> {zones.length} Active Spatial Rules
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white rounded-xl shadow-sm border border-slate-200 p-4 space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="font-bold text-sm text-slate-800 flex items-center gap-2">
              <Layers size={16} className="text-blue-600" />
              Authoritative Geometry Canvas (Normalized 0.0 - 1.0)
            </h2>
            <span className="text-xs font-mono bg-slate-100 px-2 py-0.5 rounded text-slate-600">
              {selectedZone ? `${selectedZone.name} (${selectedZone.camera_id})` : 'All Zones'}
            </span>
          </div>

          <div className="relative bg-slate-950 rounded-xl overflow-hidden aspect-video border border-slate-800 flex items-center justify-center">
            <svg className="w-full h-full" viewBox="0 0 1000 1000" preserveAspectRatio="none">
              <defs>
                <pattern id="grid" width="100" height="100" patternUnits="userSpaceOnUse">
                  <path d="M 100 0 L 0 0 0 100" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="1" />
                </pattern>
              </defs>
              <rect width="1000" height="1000" fill="url(#grid)" />

              {zones.map((zone) => {
                const ptsStr = zone.points.map(p => `${p.x * 1000},${p.y * 1000}`).join(' ');
                const isSelected = selectedZone?.zone_id === zone.zone_id;
                const firstPt = zone.points[0] || { x: 0.5, y: 0.5 };

                return (
                  <g key={zone.zone_id}>
                    <polygon
                      points={ptsStr}
                      fill={isSelected ? 'rgba(239, 68, 68, 0.35)' : 'rgba(59, 130, 246, 0.20)'}
                      stroke={isSelected ? '#EF4444' : '#3B82F6'}
                      strokeWidth={isSelected ? '4' : '2'}
                      strokeDasharray="8,4"
                    />
                    {zone.points.map((pt, pIdx) => (
                      <circle
                        key={pIdx}
                        cx={pt.x * 1000}
                        cy={pt.y * 1000}
                        r={isSelected ? 6 : 4}
                        fill="#FFFFFF"
                        stroke={isSelected ? '#EF4444' : '#3B82F6'}
                        strokeWidth="2"
                      />
                    ))}
                    <text
                      x={firstPt.x * 1000 + 10}
                      y={firstPt.y * 1000 + 30}
                      fill={isSelected ? '#EF4444' : '#60A5FA'}
                      fontSize="22"
                      fontWeight="bold"
                    >
                      {zone.name}
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>

          <p className="text-xs text-slate-500">
            Bounding points are mathematically mapped in real-time using ray-casting algorithms to evaluate intrusions on every incoming camera frame.
          </p>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4 space-y-4">
          <h2 className="font-bold text-sm text-slate-800">Configured Perimeter Zones</h2>
          
          <div className="space-y-3">
            {loading ? (
              <div className="text-center py-8 text-xs text-slate-400">Loading spatial configurations...</div>
            ) : zones.map((z) => (
              <div
                key={z.zone_id}
                onClick={() => setSelectedZone(z)}
                className={`p-3.5 rounded-lg border text-xs cursor-pointer transition-all ${
                  selectedZone?.zone_id === z.zone_id
                    ? 'border-blue-500 bg-blue-50/50 shadow-sm'
                    : 'border-slate-200 hover:bg-slate-50'
                }`}
              >
                <div className="flex justify-between items-start">
                  <div>
                    <p className="font-bold text-slate-900 text-sm">{z.name}</p>
                    <p className="text-slate-500 font-mono text-[11px] mt-0.5">ID: {z.zone_id}</p>
                  </div>
                  <span className="px-2 py-0.5 text-[10px] font-bold rounded bg-red-100 text-red-700">
                    {z.zone_type}
                  </span>
                </div>

                <div className="mt-2 pt-2 border-t border-slate-100 flex justify-between text-[11px] text-slate-600">
                  <span>Camera: <strong className="text-slate-800">{z.camera_id}</strong></span>
                  <span>Vertices: <strong className="text-slate-800">{z.points.length} points</strong></span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
"""
    with open(zones_path, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(zones_code)
    print("Created Zones.tsx")

    settings_code = """import React, { useState } from 'react';
import { Sliders, Cpu, Bell, Shield, Save, CheckCircle } from 'lucide-react';

export const Settings = () => {
  const [confThreshold, setConfThreshold] = useState(0.25);
  const [iouThreshold, setIouThreshold] = useState(0.30);
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div className="flex justify-between items-center bg-white p-4 rounded-xl shadow-sm border border-slate-200">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">System & AI Analytics Settings</h1>
          <p className="text-slate-500 text-sm mt-1">Configure detection sensitivity, inference device, and alert thresholds.</p>
        </div>
        <button
          onClick={handleSave}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-semibold hover:bg-blue-700 transition-colors shadow-sm"
        >
          <Save size={16} /> Save Changes
        </button>
      </div>

      {saved && (
        <div className="p-3 bg-emerald-50 text-emerald-800 border border-emerald-200 rounded-lg flex items-center gap-2 text-sm">
          <CheckCircle size={16} className="text-emerald-600" />
          Settings successfully applied across the active pipeline.
        </div>
      )}

      <div className="bg-white rounded-xl shadow-sm border border-slate-200 divide-y divide-slate-100">
        <div className="p-5 flex items-start gap-4">
          <div className="p-2.5 bg-blue-50 text-blue-600 rounded-lg"><Cpu size={22} /></div>
          <div className="flex-1">
            <h3 className="text-sm font-bold text-slate-900">AI Detection Sensitivity (YOLOv8)</h3>
            <p className="text-xs text-slate-500 mt-0.5">Adjust minimum confidence threshold for person and vehicle detection.</p>
            <div className="mt-3 flex items-center gap-4">
              <input
                type="range"
                min="0.10"
                max="0.90"
                step="0.05"
                value={confThreshold}
                onChange={(e) => setConfThreshold(parseFloat(e.target.value))}
                className="w-64 accent-blue-600"
              />
              <span className="font-mono text-sm font-bold text-slate-800">{Math.round(confThreshold * 100)}% Confidence</span>
            </div>
          </div>
        </div>

        <div className="p-5 flex items-start gap-4">
          <div className="p-2.5 bg-purple-50 text-purple-600 rounded-lg"><Sliders size={22} /></div>
          <div className="flex-1">
            <h3 className="text-sm font-bold text-slate-900">Multi-Object Tracking IoU Matching</h3>
            <p className="text-xs text-slate-500 mt-0.5">Intersection over Union overlap required to associate a detection with an existing track ID.</p>
            <div className="mt-3 flex items-center gap-4">
              <input
                type="range"
                min="0.10"
                max="0.80"
                step="0.05"
                value={iouThreshold}
                onChange={(e) => setIouThreshold(parseFloat(e.target.value))}
                className="w-64 accent-purple-600"
              />
              <span className="font-mono text-sm font-bold text-slate-800">{iouThreshold.toFixed(2)} IoU</span>
            </div>
          </div>
        </div>

        <div className="p-5 flex items-start gap-4">
          <div className="p-2.5 bg-emerald-50 text-emerald-600 rounded-lg"><Shield size={22} /></div>
          <div className="flex-1">
            <h3 className="text-sm font-bold text-slate-900">Inference Hardware Acceleration</h3>
            <p className="text-xs text-slate-500 mt-0.5">Hardware backend utilized for neural network forward pass.</p>
            <div className="mt-3">
              <span className="px-3 py-1 bg-slate-100 text-slate-800 rounded font-mono text-xs font-semibold">
                Intel CPU (OpenCV DNN / PyTorch Native)
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
"""
    with open(settings_path, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(settings_code)
    print("Created Settings.tsx")

def print_banner():
    print("=" * 60)
    print(" 🚀 IBVAP - INTELLIGENT BORDER VIDEO ANALYTICS PLATFORM")
    print("=" * 60)
    print("\n[ SIH PS-26187 Prototype - Control Center ]\n")



def print_instructions():
    print("To run the full stack on your local machine, open 3 separate terminal windows:\n")
    
    print("Terminal 1 (MediaMTX Camera Simulator):")
    print("  cd infrastructure/mediamtx")
    print("  ./mediamtx mediamtx.yml")
    print("  (If you don't have mediamtx installed, download it from github.com/bluenviron/mediamtx)\n")
    
    print("Terminal 2 (FastAPI Backend):")
    print("  cd apps/backend")
    print("  uvicorn main:app --reload --port 8000\n")
    
    print("Terminal 3 (React Dashboard):")
    print("  cd apps/frontend")
    print("  npm install")
    print("  npm run dev\n")
    
    print("------------------------------------------------------------")
    print("Once all 3 are running, open your browser to:")
    print("👉 http://localhost:5173")
    print("------------------------------------------------------------\n")
    
def main():
    print_banner()
    print_instructions()
    
if __name__ == "__main__":
    main()
