# ==============================================================================
# IBVAP — Ethernet IP Setup Helper for College CCTV Switch Testing
# Sets Laptop Ethernet Adapter to 192.168.1.50 (255.255.255.0)
# ==============================================================================

param(
    [string]$StaticIP = "192.168.1.50",
    [string]$SubnetMask = "255.255.255.0",
    [string]$Gateway = "192.168.1.1"
)

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "       IBVAP - PHYSICAL CCTV ETHERNET ADAPTER CONFIGURATION HELPER              " -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

# Find active or wired Ethernet adapter
$adapters = Get-NetAdapter | Where-Object { $_.PhysicalMediaType -like "*802.3*" -or $_.Name -like "*Ethernet*" -or $_.InterfaceDescription -like "*Ethernet*" -or $_.InterfaceDescription -like "*Gigabit*" -or $_.InterfaceDescription -like "*Realtek*" }

if (-not $adapters) {
    Write-Host "[!] No wired Ethernet adapter detected. Please plug the Ethernet patch cord into your laptop." -ForegroundColor Red
    Write-Host "Available adapters:" -ForegroundColor Yellow
    Get-NetAdapter | Format-Table -Property Name, InterfaceDescription, Status, LinkSpeed
    exit 1
}

$adapter = $adapters[0]
Write-Host "[+] Target Ethernet Adapter Found: '$($adapter.Name)' ($($adapter.InterfaceDescription))" -ForegroundColor Green
Write-Host "[+] Setting Static IP: $StaticIP / Subnet: $SubnetMask / Gateway: $Gateway" -ForegroundColor Cyan

try {
    # Check admin privileges
    $isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $isAdmin) {
        Write-Host "`n[!] Administrator elevation required to change network IP." -ForegroundColor Yellow
        Write-Host "[*] Requesting UAC elevation..." -ForegroundColor Cyan
        Start-Process powershell -Verb RunAs -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
        exit 0
    }

    # Remove existing static IP on this adapter if any
    Remove-NetIPAddress -InterfaceAlias $adapter.Name -AddressFamily IPv4 -Confirm:$false -ErrorAction SilentlyContinue
    Remove-NetRoute -InterfaceAlias $adapter.Name -AddressFamily IPv4 -Confirm:$false -ErrorAction SilentlyContinue

    # Set new static IP
    New-NetIPAddress -InterfaceAlias $adapter.Name -IPAddress $StaticIP -PrefixLength 24 -DefaultGateway $Gateway -ErrorAction Stop
    Set-DnsClientServerAddress -InterfaceAlias $adapter.Name -ServerAddresses ("8.8.8.8", "1.1.1.1") -ErrorAction SilentlyContinue

    Write-Host "`n================================================================================" -ForegroundColor Green
    Write-Host " [PASS] Ethernet Adapter successfully configured to $StaticIP!" -ForegroundColor Green
    Write-Host " You are now ready to communicate with the College Camera Switch on 192.168.1.x" -ForegroundColor Green
    Write-Host "================================================================================" -ForegroundColor Green
} catch {
    Write-Host "`n[FAIL] Could not set IP automatically: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Manual steps in Windows Settings:" -ForegroundColor Yellow
    Write-Host "1. Open 'Network Connections' (Win+R -> ncpa.cpl)" -ForegroundColor White
    Write-Host "2. Right-click 'Ethernet' -> Properties -> 'Internet Protocol Version 4 (TCP/IPv4)'" -ForegroundColor White
    Write-Host "3. Set IP address: $StaticIP, Subnet mask: $SubnetMask, Gateway: $Gateway" -ForegroundColor White
}
