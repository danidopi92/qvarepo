$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$celery = Join-Path $projectRoot ".venv\Scripts\celery.exe"
$logsDir = Join-Path $projectRoot ".local\logs"
$pidsDir = Join-Path $projectRoot ".local\pids"

New-Item -ItemType Directory -Force -Path $logsDir | Out-Null
New-Item -ItemType Directory -Force -Path $pidsDir | Out-Null

& (Join-Path $PSScriptRoot "start_local_stack.ps1")

function Start-ManagedProcess {
    param(
        [string]$Name,
        [string]$FilePath,
        [string]$Arguments
    )

    $pidFile = Join-Path $pidsDir "$Name.pid"
    $outLog = Join-Path $logsDir "$Name.out.log"
    $errLog = Join-Path $logsDir "$Name.err.log"

    if (Test-Path $pidFile) {
        $existingPid = Get-Content $pidFile -ErrorAction SilentlyContinue
        if ($existingPid) {
            $proc = Get-Process -Id $existingPid -ErrorAction SilentlyContinue
            if ($proc) {
                Write-Host "$Name ya esta corriendo con PID $existingPid" -ForegroundColor Yellow
                return
            }
        }
    }

    $process = Start-Process -FilePath $FilePath -ArgumentList $Arguments -WorkingDirectory $projectRoot -RedirectStandardOutput $outLog -RedirectStandardError $errLog -PassThru
    $process.Id | Set-Content $pidFile
    Write-Host "$Name iniciado con PID $($process.Id)" -ForegroundColor Green
}

Start-ManagedProcess -Name "django" -FilePath $python -Arguments "manage.py runserver 127.0.0.1:8000"
Start-ManagedProcess -Name "celery-worker" -FilePath $celery -Arguments "-A config worker -l info --pool=solo"
Start-ManagedProcess -Name "celery-beat" -FilePath $celery -Arguments "-A config beat -l info"

Write-Host ""
Write-Host "Aplicacion local levantada." -ForegroundColor Green
Write-Host "URL: http://127.0.0.1:8000/"
Write-Host "Logs: $logsDir"
