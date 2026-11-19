@echo off
setlocal EnableExtensions
set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
set "FRONTEND=%ROOT%frontend"
set "API=http://127.0.0.1:8000"
set "APP=http://localhost:3000"

title ELECTORaW launcher
echo.
echo  Starting ELECTORaW...
echo  Workspace: %ROOT%
echo.

if not exist "%BACKEND%\app\main.py" (
  echo [ERROR] Backend not found at %BACKEND%
  pause
  exit /b 1
)
if not exist "%FRONTEND%\package.json" (
  echo [ERROR] Frontend not found at %FRONTEND%
  pause
  exit /b 1
)

where python >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Python was not found on PATH.
  pause
  exit /b 1
)
where npm >nul 2>&1
if errorlevel 1 (
  echo [ERROR] npm was not found on PATH.
  pause
  exit /b 1
)

rem Stop only ELECTORaW's old Uvicorn API process so port 8000 cannot serve stale code.
powershell -NoProfile -ExecutionPolicy Bypass -Command "$root='%ROOT%'; Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*uvicorn*app.main:app*--port 8000*' -and ($_.CommandLine -like ('*' + $root + '*') -or $_.CommandLine -like '*ELECTORaW*') } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"

rem Start MongoDB when it is installed and not already listening. Profile mirrors are optional; MySQL and ChromaDB are required.
powershell -NoProfile -ExecutionPolicy Bypass -Command "$data='%ROOT%database\mongodb\data'; $log='%ROOT%database\mongodb\mongod.log'; New-Item -ItemType Directory -Force -Path $data | Out-Null; $tcp=New-Object Net.Sockets.TcpClient; $running=$false; try { $tcp.Connect('127.0.0.1',27017); $running=$true } catch {}; $tcp.Dispose(); if(-not $running){ $mongo=(Get-Command mongod.exe -ErrorAction SilentlyContinue).Source; if(-not $mongo -and (Test-Path 'C:\Program Files\MongoDB\Server')){ $mongo=(Get-ChildItem 'C:\Program Files\MongoDB\Server' -Filter mongod.exe -Recurse -ErrorAction SilentlyContinue | Sort-Object FullName -Descending | Select-Object -First 1 -ExpandProperty FullName) }; if($mongo){ Start-Process -FilePath $mongo -ArgumentList @('--dbpath',$data,'--bind_ip','127.0.0.1','--port','27017','--logpath',$log,'--logappend') -WindowStyle Hidden; Start-Sleep -Seconds 2 } else { Write-Host '[INFO] MongoDB was not found; Mongo mirrors will use fallback mode.' -ForegroundColor Yellow } }"

rem MySQL is the single relational runtime now. Start the installed MySQL80 service and verify port 3306 before launching the API.
powershell -NoProfile -ExecutionPolicy Bypass -Command "$service=Get-Service -Name 'MySQL80' -ErrorAction SilentlyContinue; if($service -and $service.Status -ne 'Running'){ try { Start-Service -Name 'MySQL80' -ErrorAction Stop; Start-Sleep -Seconds 3 } catch { Write-Host '[ERROR] MySQL80 exists but could not be started. Run this launcher as administrator.' -ForegroundColor Red; exit 1 } }; $tcp=New-Object Net.Sockets.TcpClient; $ready=$false; try { $tcp.Connect('127.0.0.1',3306); $ready=$true } catch {}; $tcp.Dispose(); if(-not $ready){ Write-Host '[ERROR] MySQL is not listening on 127.0.0.1:3306. Start MySQL80 and retry.' -ForegroundColor Red; exit 1 }"
if errorlevel 1 (
  pause
  exit /b 1
)

rem Start the backend in its own window.
start "ELECTORaW Backend" powershell -NoProfile -ExecutionPolicy Bypass -NoExit -Command "$ErrorActionPreference='Stop'; $backend='%BACKEND%'; Set-Location -LiteralPath $backend; $env:PYTHONPATH='.'; $env:FRONTEND_ORIGINS='http://localhost:3000,http://127.0.0.1:3000'; $env:WORKFLOW_BACKEND='mysql'; $env:ELECTORAW_DATA_BACKEND='mysql'; if(-not (Test-Path (Join-Path $backend 'app'))){ throw 'Backend folder not found' }; python -c 'import fastapi,uvicorn,pymongo,mysql.connector,dotenv' 2>$null; if($LASTEXITCODE -ne 0){ Write-Host '[INFO] Installing backend dependencies...'; python -m pip install -r requirements.txt; if($LASTEXITCODE -ne 0){ throw 'Backend dependency installation failed' } }; python -m app.services.populate_mysql; python -m app.services.migrate_sqlite_to_mysql; python -m app.services.seed_mongodb_profiles; python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

rem Wait until the API is healthy before starting the frontend.
echo  Waiting for the backend health check...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$api='%API%'; $deadline=(Get-Date).AddSeconds(60); $ready=$false; while((Get-Date) -lt $deadline){ try { $health=Invoke-RestMethod -Uri ($api + '/api/health') -TimeoutSec 2; if($health.status -eq 'ok' -and $health.workflow_ready -eq $true){ $ready=$true; break } } catch {}; Start-Sleep -Seconds 1 }; if(-not $ready){ Write-Host '[ERROR] Backend did not become healthy on port 8000, or an older backend is still running.' -ForegroundColor Red; exit 1 }"
if errorlevel 1 (
  echo [ERROR] Backend startup failed. Check the ELECTORaW Backend window.
  pause
  exit /b 1
)

rem Start the Next.js frontend with an explicit API URL so registration and every public page use the same backend.
start "ELECTORaW Frontend" powershell -NoProfile -ExecutionPolicy Bypass -NoExit -Command "$frontend='%FRONTEND%'; Set-Location -LiteralPath $frontend; $env:NEXT_PUBLIC_API_URL='%API%'; if(-not (Test-Path (Join-Path $frontend 'node_modules'))){ Write-Host '[INFO] Installing frontend dependencies...'; npm install; if($LASTEXITCODE -ne 0){ throw 'Frontend dependency installation failed' } }; npm run dev -- --hostname 127.0.0.1"

rem Wait for Next.js and open the application in the default browser.
echo  Waiting for the frontend...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$app='%APP%'; $deadline=(Get-Date).AddSeconds(60); $ready=$false; while((Get-Date) -lt $deadline){ try { $response=Invoke-WebRequest -Uri $app -UseBasicParsing -TimeoutSec 2; if($response.StatusCode -ge 200 -and $response.StatusCode -lt 500){ $ready=$true; break } } catch {}; Start-Sleep -Seconds 1 }; if($ready){ Start-Process $app } else { Write-Host '[WARN] Frontend is still starting. Open http://localhost:3000 when ready.' -ForegroundColor Yellow }"

echo.
echo  ELECTORaW is ready. Registration will load states and constituencies from the local API.
endlocal
