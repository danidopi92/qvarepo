$projectRoot = Split-Path -Parent $PSScriptRoot
$pgCtl = "C:\Program Files\PostgreSQL\16\bin\pg_ctl.exe"
$psql = "C:\Program Files\PostgreSQL\16\bin\psql.exe"
$pgData = Join-Path $projectRoot ".local\postgres-data"
$redisCli = "C:\Program Files\Redis\redis-cli.exe"

Write-Host "Verificando PostgreSQL local..." -ForegroundColor Cyan
& $psql -h 127.0.0.1 -p 5433 -U postgres -d postgres -c "SELECT 1;" 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    & $pgCtl -D $pgData -l (Join-Path $pgData "server.log") start | Out-Null
    Start-Sleep -Seconds 3
}

Write-Host "Verificando Redis..." -ForegroundColor Cyan
& $redisCli ping 2>$null

Write-Host ""
Write-Host "Stack local listo." -ForegroundColor Green
Write-Host "Django: .\.venv\Scripts\python.exe manage.py runserver"
Write-Host "Celery worker: .\.venv\Scripts\celery.exe -A config worker -l info"
Write-Host "Celery beat: .\.venv\Scripts\celery.exe -A config beat -l info"
