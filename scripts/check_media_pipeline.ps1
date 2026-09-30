<#
.SYNOPSIS
    Verifies media pipeline components (FFmpeg, ffprobe, MediaMTX, test video, RTSP publish/read).
#>

$ErrorActionPreference = "Continue"

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host " IBVAP MEDIA PIPELINE INTEGRITY CHECK" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# 1. Check FFmpeg & ffprobe
$ffmpegPath = (Get-ChildItem -Path "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Recurse -Filter "ffmpeg.exe" -ErrorAction SilentlyContinue | Select-Object -First 1).FullName
if (-not $ffmpegPath) {
    $ffmpegCmd = Get-Command ffmpeg -ErrorAction SilentlyContinue
    if ($ffmpegCmd) { $ffmpegPath = $ffmpegCmd.Source }
}

$ffprobePath = (Get-ChildItem -Path "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Recurse -Filter "ffprobe.exe" -ErrorAction SilentlyContinue | Select-Object -First 1).FullName
if (-not $ffprobePath) {
    $ffprobeCmd = Get-Command ffprobe -ErrorAction SilentlyContinue
    if ($ffprobeCmd) { $ffprobePath = $ffprobeCmd.Source }
}

$ffmpegOk = [bool]$ffmpegPath
$ffprobeOk = [bool]$ffprobePath

Write-Host "1. FFmpeg Binary: " -NoNewline
if ($ffmpegOk) { Write-Host "PASS ($ffmpegPath)" -ForegroundColor Green } else { Write-Host "FAIL" -ForegroundColor Red }

Write-Host "2. ffprobe Binary: " -NoNewline
if ($ffprobeOk) { Write-Host "PASS ($ffprobePath)" -ForegroundColor Green } else { Write-Host "FAIL" -ForegroundColor Red }

# 2. Check MediaMTX executable
$mediamtxExe = "infrastructure\mediamtx\mediamtx.exe"
$mediamtxOk = Test-Path $mediamtxExe
Write-Host "3. MediaMTX Executable: " -NoNewline
if ($mediamtxOk) { Write-Host "PASS ($mediamtxExe)" -ForegroundColor Green } else { Write-Host "FAIL" -ForegroundColor Red }

# 3. Check Test Video
$testVideo = "data\raw\test_video.mp4"
$videoExists = Test-Path $testVideo
Write-Host "4. Test Video File: " -NoNewline
if ($videoExists) { Write-Host "PASS ($testVideo)" -ForegroundColor Green } else { Write-Host "FAIL (Missing $testVideo)" -ForegroundColor Yellow }

$videoReadable = $false
if ($videoExists -and $ffprobeOk) {
    $probeOut = & $ffprobePath -v error -show_entries format=duration,size -of default=noprint_wrappers=1:nokey=1 $testVideo 2>&1
    if ($LASTEXITCODE -eq 0) {
        $videoReadable = $true
    }
}
Write-Host "5. Video ffprobe Readable: " -NoNewline
if ($videoReadable) { Write-Host "PASS" -ForegroundColor Green } else { Write-Host "FAIL/SKIPPED" -ForegroundColor Yellow }

# 4. MediaMTX Run & RTSP Port Check
$mtxProcess = $null
$rtspPublished = $false
$rtspReadable = $false

if ($mediamtxOk) {
    Write-Host "`nStarting MediaMTX test process..." -ForegroundColor Gray
    $mtxProcess = Start-Process -FilePath $mediamtxExe -ArgumentList "infrastructure\mediamtx\mediamtx.yml" -PassThru -NoNewWindow
    Start-Sleep -Seconds 3

    $tcpClient = New-Object System.Net.Sockets.TcpClient
    $portOk = $false
    try {
        $tcpClient.Connect("127.0.0.1", 8554)
        $portOk = $tcpClient.Connected
        $tcpClient.Close()
    } catch {
        $portOk = $false
    }

    Write-Host "6. RTSP Port (127.0.0.1:8554) Open: " -NoNewline
    if ($portOk) { Write-Host "PASS" -ForegroundColor Green } else { Write-Host "FAIL" -ForegroundColor Red }

    if ($portOk -and $videoExists -and $ffmpegOk) {
        Write-Host "Publishing test stream to rtsp://127.0.0.1:8554/CAM-01 using FFmpeg..." -ForegroundColor Gray
        $ffmpegProc = Start-Process -FilePath $ffmpegPath -ArgumentList "-re -stream_loop -1 -i `"$testVideo`" -c copy -f rtsp -rtsp_transport tcp rtsp://127.0.0.1:8554/CAM-01" -PassThru -NoNewWindow
        Start-Sleep -Seconds 4

        if (-not $ffmpegProc.HasExited) {
            $rtspPublished = $true
            Write-Host "7. CAM-01 Publish: PASS" -ForegroundColor Green

            # Probe RTSP stream
            if ($ffprobeOk) {
                Write-Host "Probing RTSP stream rtsp://127.0.0.1:8554/CAM-01..." -ForegroundColor Gray
                $rtspProbe = & $ffprobePath -v error -rtsp_transport tcp -show_entries stream=codec_name -of default=noprint_wrappers=1:nokey=1 "rtsp://127.0.0.1:8554/CAM-01" 2>&1
                if ($LASTEXITCODE -eq 0 -and $rtspProbe) {
                    $rtspReadable = $true
                    Write-Host "8. CAM-01 Read: PASS ($($rtspProbe -join ' '))" -ForegroundColor Green
                } else {
                    Write-Host "8. CAM-01 Read: FAIL" -ForegroundColor Red
                }
            }
            Stop-Process -Id $ffmpegProc.Id -Force -ErrorAction SilentlyContinue
        } else {
            Write-Host "7. CAM-01 Publish: FAIL (FFmpeg exited prematurely)" -ForegroundColor Red
        }
    } else {
        Write-Host "7. CAM-01 Publish: SKIPPED (Prerequisites not met)" -ForegroundColor Yellow
        Write-Host "8. CAM-01 Read: SKIPPED (Prerequisites not met)" -ForegroundColor Yellow
    }

    if ($mtxProcess -and -not $mtxProcess.HasExited) {
        Stop-Process -Id $mtxProcess.Id -Force -ErrorAction SilentlyContinue
    }
} else {
    Write-Host "6. RTSP Port: SKIPPED (MediaMTX binary missing)" -ForegroundColor Yellow
}

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host " SUMMARY: Ready for RTSP pipeline: " -NoNewline
if ($ffmpegOk -and $ffprobeOk -and $mediamtxOk -and $videoExists -and $rtspReadable) {
    Write-Host "YES" -ForegroundColor Green
} else {
    Write-Host "NO" -ForegroundColor Red
}
Write-Host "=========================================" -ForegroundColor Cyan
