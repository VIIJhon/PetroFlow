# Run Alembic Migrations
# This script runs all pending database migrations

Write-Host "Running database migrations..." -ForegroundColor Green

# Change to backend directory
Set-Location $PSScriptRoot\..

# Run migrations
python -m alembic upgrade head

if ($LASTEXITCODE -eq 0) {
    Write-Host "Migrations completed successfully!" -ForegroundColor Green
} else {
    Write-Host "Migration failed with exit code $LASTEXITCODE" -ForegroundColor Red
    exit $LASTEXITCODE
}