$ErrorActionPreference = "Stop"

$redisUrl = "https://github.com/tporadowski/redis/releases/download/v5.0.14.1/Redis-x64-5.0.14.1.zip"
$destDir = Join-Path $PSScriptRoot "..\redis"
$zipPath = Join-Path $destDir "redis.zip"

Write-Host "Setting up Redis for Windows..." -ForegroundColor Cyan

# Create directory
if (-not (Test-Path $destDir)) {
    New-Item -ItemType Directory -Path $destDir | Out-Null
    Write-Host "Created directory: $destDir"
}

# Download
Write-Host "Downloading Redis from $redisUrl..."
Invoke-WebRequest -Uri $redisUrl -OutFile $zipPath

# Extract
Write-Host "Extracting Redis..."
Expand-Archive -Path $zipPath -DestinationPath $destDir -Force

# Cleanup
Remove-Item $zipPath
Write-Host "Redis setup complete!" -ForegroundColor Green
Write-Host "You can now run 'run_redis.bat' to start the server."
