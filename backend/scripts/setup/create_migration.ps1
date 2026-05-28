# Create New Alembic Migration
# Usage: .\create_migration.ps1 "migration_message"

param(
    [Parameter(Mandatory=$true)]
    [string]$Message
)

Write-Host "Creating new migration: $Message" -ForegroundColor Green

# Change to backend directory
Set-Location $PSScriptRoot\..

# Create migration
python -m alembic revision --autogenerate -m "$Message"

if ($LASTEXITCODE -eq 0) {
    Write-Host "Migration created successfully!" -ForegroundColor Green
    Write-Host "Review the migration file in alembic/versions/ before running it." -ForegroundColor Yellow
} else {
    Write-Host "Migration creation failed with exit code $LASTEXITCODE" -ForegroundColor Red
    exit $LASTEXITCODE
}