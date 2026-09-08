$ErrorActionPreference = 'Stop'
$repo = Resolve-Path $PSScriptRoot
$python = Join-Path $repo '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Run .\setup.ps1 first.' }
$backend = Start-Process -FilePath $python -ArgumentList @('manage.py','runserver','127.0.0.1:8000','--noreload') `
  -WorkingDirectory (Join-Path $repo 'backend') -WindowStyle Hidden -PassThru
try {
  $ready = $false
  for ($attempt = 0; $attempt -lt 50; $attempt++) {
    try {
      $response = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/docs' -TimeoutSec 1 -UseBasicParsing
      if ($response.StatusCode -eq 200) { $ready = $true; break }
    } catch { Start-Sleep -Milliseconds 100 }
  }
  if (-not $ready) { throw 'Backend did not become ready on http://127.0.0.1:8000.' }
  & $python (Join-Path $repo 'frontend\app.py')
} finally {
  if (-not $backend.HasExited) { Stop-Process -Id $backend.Id }
}
