# Fix Bluetooth audio after sleep/wake: toggle Intel BT radio + refresh audio services.
$ErrorActionPreference = 'Continue'
$logDir = Join-Path $env:TEMP 'bt-audio-wake-fix'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir ("fix-{0:yyyyMMdd-HHmmss}.log" -f (Get-Date))
function Log($m) { $line = "{0:HH:mm:ss} {1}" -f (Get-Date), $m; $line | Out-File $log -Append -Encoding utf8 }

Log 'start'
Start-Sleep -Seconds 3

foreach ($svc in @('BTAGService','BthAvctpSvc','bthserv')) {
  try {
    Restart-Service -Name $svc -Force -ErrorAction Stop
    Log "restarted $svc"
  } catch {
    Log "svc $svc : $($_.Exception.Message)"
  }
}

$bt = Get-PnpDevice -FriendlyName 'Intel(R) Wireless Bluetooth(R)' -ErrorAction SilentlyContinue
if (-not $bt) {
  $bt = Get-PnpDevice -Class Bluetooth | Where-Object { $_.FriendlyName -match 'Intel.*Bluetooth|无线 Bluetooth' } | Select-Object -First 1
}
if ($bt) {
  try {
    Disable-PnpDevice -InstanceId $bt.InstanceId -Confirm:$false -ErrorAction Stop
    Log "disabled $($bt.FriendlyName)"
    Start-Sleep -Seconds 2
    Enable-PnpDevice -InstanceId $bt.InstanceId -Confirm:$false -ErrorAction Stop
    Log "enabled $($bt.FriendlyName)"
  } catch {
    Log "toggle fail: $($_.Exception.Message)"
    try {
      & "$env:SystemRoot\System32\pnputil.exe" /disable-device "$($bt.InstanceId)" | Out-Null
      Start-Sleep -Seconds 2
      & "$env:SystemRoot\System32\pnputil.exe" /enable-device "$($bt.InstanceId)" | Out-Null
      Log 'toggled via pnputil'
    } catch {
      Log "pnputil fail: $($_.Exception.Message)"
    }
  }
} else {
  Log 'Intel Bluetooth adapter not found'
}

Log "done log=$log"
