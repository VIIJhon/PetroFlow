# Reset Database (Development Only)
# WARNING: This will delete all data!

param(
    [switch]$Force
)

if (-not $Force) {
    Write-Host "WARNING: This will delete all data in the database!" -ForegroundColor Red
    $confirmation = Read-Host "Are you sure you want to continue? (yes/no)"
    
    if ($confirmation -ne "yes") {
        Write-Host "Operation cancelled." -ForegroundColor Yellow
        exit 0
    }
}

Write-Host "Resetting database..." -ForegroundColor Yellow

# Change to backend directory
Set-Location $PSScriptRoot\..

# Drop all tables
Write-Host "Dropping all tables..." -ForegroundColor Yellow
python -c "from app.db.init_db import drop_tables; drop_tables()"

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to drop tables" -ForegroundColor Red
    exit $LASTEXITCODE
}

# Run migrations
Write-Host "Running migrations..." -ForegroundColor Green
python -m alembic upgrade head

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to run migrations" -ForegroundColor Red
    exit $LASTEXITCODE
}

# Seed database
Write-Host "Seeding database..." -ForegroundColor Green
python -c "from app.database import SessionLocal; from app.db.seed_data import seed_all; db = SessionLocal(); result = seed_all(db); db.close(); print(f'Seeding completed: {result}')"

if ($LASTEXITCODE -eq 0) {
    Write-Host "Database reset completed successfully!" -ForegroundColor Green
} else {
    Write-Host "Database seeding failed" -ForegroundColor Red
    exit $LASTEXITCODE
}