$targets = @(2804, 5216, 10360, 12876, 13768, 14524, 14656, 14708, 16164, 17112, 18920, 19724, 19856)

foreach ($id in $targets) {
    try {
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId = $id"
        if ($proc) {
            $ret = Invoke-CimMethod -InputObject $proc -MethodName Terminate
            Write-Host "Terminated PID $id with return value: $($ret.ReturnValue)"
        } else {
            Write-Host "PID $id not found in Win32_Process"
        }
    } catch {
        Write-Host "Error on PID $($id)"
    }
}
