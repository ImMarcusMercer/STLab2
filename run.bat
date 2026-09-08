@echo off
setlocal
set "REPO=%~dp0"
set "PYTHON=%REPO%.venv\Scripts\python.exe"
if not exist "%PYTHON%" (
  echo Run .\setup.ps1 first, then run this file again.
  exit /b 1
)

echo Starting helper backend...
powershell -NoProfile -Command "$p = Start-Process -FilePath '%PYTHON%' -ArgumentList @('manage.py','runserver','127.0.0.1:8000','--noreload') -WorkingDirectory '%REPO%backend' -WindowStyle Hidden -PassThru; $p.Id | Set-Content -LiteralPath '%TEMP%\sis-backend.pid'"

echo Waiting for the API to become ready on http://127.0.0.1:8000/api/docs ...
powershell -NoProfile -Command "for ($i=0; $i -lt 50; $i++) { try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/docs' -TimeoutSec 1 -UseBasicParsing; if ($r.StatusCode -eq 200) { exit 0 } } catch { Start-Sleep -Milliseconds 100 } }; exit 1"
if errorlevel 1 (
  echo Backend did not become ready. It may already be running from another session.
)

echo Launching the frontend...
"%PYTHON%" frontend\app.py

if exist "%TEMP%\sis-backend.pid" (
  for /f %%P in (%TEMP%\sis-backend.pid) do powershell -NoProfile -Command "if (Get-Process -Id %%P -ErrorAction SilentlyContinue) { Stop-Process -Id %%P -Force }"
  del "%TEMP%\sis-backend.pid" >nul 2>&1
)

endlocal