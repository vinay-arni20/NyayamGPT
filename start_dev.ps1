Write-Host "Starting NyayamGPT Development Environment..." -ForegroundColor Cyan

# Check/Start Redis
if (!(Get-Process redis-server -ErrorAction SilentlyContinue)) {
    Write-Host "Starting Redis..." -ForegroundColor Yellow
    # Assuming run_redis.bat is in backend/
    if (Test-Path "backend\run_redis.bat") {
        Start-Process -FilePath "backend\run_redis.bat" -WindowStyle Minimized
        Write-Host "Redis started." -ForegroundColor Green
    } else {
        Write-Host "Redis script not found in backend/run_redis.bat" -ForegroundColor Red
    }
} else {
    Write-Host "Redis is already running." -ForegroundColor Green
}

# Start Backend
Write-Host "Starting Backend (FastAPI)..." -ForegroundColor Yellow
# We use Start-Process to run it in a separate window so logs don't clutter this terminal
# We use -NoExit so the window stays open if it crashes, for debugging
$backendCmd = "cd backend; if (Test-Path 'venv\Scripts\Activate.ps1') { . .\venv\Scripts\Activate.ps1 }; uvicorn app.main:app --reload --log-level warning"
$backendProcess = Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-Command", $backendCmd -PassThru
Write-Host "Backend started (PID: $($backendProcess.Id))" -ForegroundColor Green

# Start Frontend
Write-Host "Starting Frontend (Vite)..." -ForegroundColor Yellow
$frontendCmd = "cd frontend; npm run dev"
$frontendProcess = Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-Command", $frontendCmd -PassThru
Write-Host "Frontend started (PID: $($frontendProcess.Id))" -ForegroundColor Green

Write-Host "`nSystem is running!" -ForegroundColor Cyan
Write-Host "   Backend API:  http://localhost:8000/docs"
Write-Host "   Frontend UI:  http://localhost:5173"
Write-Host "`n(Close the external windows to stop the servers)" -ForegroundColor Gray
