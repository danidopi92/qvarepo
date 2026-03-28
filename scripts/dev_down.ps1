$projectRoot = Split-Path -Parent $PSScriptRoot
$pidsDir = Join-Path $projectRoot ".local\pids"

if (-not (Test-Path $pidsDir)) {
    Write-Host "No hay procesos administrados." -ForegroundColor Yellow
    exit 0
}

Get-ChildItem $pidsDir -Filter *.pid | ForEach-Object {
    $pidValue = Get-Content $_.FullName -ErrorAction SilentlyContinue
    if ($pidValue) {
        $proc = Get-Process -Id $pidValue -ErrorAction SilentlyContinue
        if ($proc) {
            Stop-Process -Id $pidValue -Force
            Write-Host "$($_.BaseName) detenido (PID $pidValue)" -ForegroundColor Green
        }
    }
    Remove-Item $_.FullName -Force
}
