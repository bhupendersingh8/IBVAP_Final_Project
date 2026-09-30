$desktop = [Environment]::GetFolderPath("Desktop")
$wsh = New-Object -ComObject WScript.Shell

$shortcut1 = $wsh.CreateShortcut("$desktop\IBVAP_1_CLICK_START.lnk")
$shortcut1.TargetPath = "C:\Users\anmol\.gemini\antigravity\scratch\IBVAP_Final_Project\00_CLICK_HERE_TO_START_OFFLINE\1_CLICK_RUN_ALL_AND_AUTO_CONNECT.bat"
$shortcut1.WorkingDirectory = "C:\Users\anmol\.gemini\antigravity\scratch\IBVAP_Final_Project"
$shortcut1.Description = "IBVAP - 1-Click Offline Master Launcher"
$shortcut1.Save()

$shortcut2 = $wsh.CreateShortcut("$desktop\IBVAP_CCTV_FOLDER.lnk")
$shortcut2.TargetPath = "C:\Users\anmol\.gemini\antigravity\scratch\IBVAP_Final_Project\00_CLICK_HERE_TO_START_OFFLINE"
$shortcut2.Description = "IBVAP - Offline Files & CCTV Tools Folder"
$shortcut2.Save()

Write-Host "Created shortcuts on Desktop:" $desktop
