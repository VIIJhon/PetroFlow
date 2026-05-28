# Seed Database with Sample Data
# This script populates the database with sample data for development

Write-Host "Seeding database with sample data..." -ForegroundColor Green

# Change to backend directory
Set-Location $PSScriptRoot\..

# Run seed script
python -c "from app.database import SessionLocal; from app.db.seed_data import seed_all; db = SessionLocal(); result = seed_all(db); db.close(); print(f'Seeding completed: {result}')"

if ($LASTEXITCODE -eq 0) {
    Write-Host "Database seeded successfully!" -ForegroundColor Green
} else {
    Write-Host "Database seeding failed with exit code $LASTEXITCODE" -ForegroundColor Red
    exit $LASTEXITCODE
}