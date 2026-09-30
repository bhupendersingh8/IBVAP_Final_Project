# ==============================================================================
# IBVAP — Reset Ethernet Adapter back to DHCP (Automatic IP)
# ==============================================================================

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "       IBVAP - RESTORING ETHERNET ADAPTER TO AUTOMATIC DHCP                     " -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

$adapters = Get-NetAdapter | Where-Object { $_.PhysicalMediaType -like "*802.3*" -or $_.Name -like "*Ethernet*" -or $_.InterfaceDescription -like "*Ethernet*" -or $_.InterfaceDescription -like "*Gigabit*" -or $_.InterfaceDescription -like "*Realtek*" }

if (-not $adapters) {
    Write-Host "[!] No Ethernet adapter found." -ForegroundColor Red
    exit 1
}

$adapter = $adapters[0]

try {
    $isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $isAdmin) {
        Start-Process powershell -Verb RunAs -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
        exit 0
    }

    Set-NetIPInterface -InterfaceAlias $adapter.Name -Dhcp Enabled
    Set-DnsClientServerAddress -InterfaceAlias $adapter.Name -ResetServerAddresses
    Write-Host "[PASS] Adapter '$($adapter.Name)' restored to Automatic DHCP successfully!" -ForegroundColor Green
} catch {
    Write-Host "[FAIL] Error resetting DHCP: $($_.Exception.Message)" -ForegroundColor Red
}
