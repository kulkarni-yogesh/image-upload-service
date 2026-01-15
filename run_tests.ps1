# PowerShell test runner script
Write-Host "Running Image Upload Service Tests..." -ForegroundColor Green
Write-Host "====================================" -ForegroundColor Green

# Check if virtual environment is activated
if (-not $env:VIRTUAL_ENV) {
    Write-Host "Warning: Virtual environment not activated" -ForegroundColor Yellow
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    if (Test-Path "venv\Scripts\Activate.ps1") {
        & "venv\Scripts\Activate.ps1"
    } else {
        Write-Host "Please activate your virtual environment first" -ForegroundColor Red
    }
}

# Run tests
pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=html

Write-Host ""
Write-Host "Test coverage report generated in htmlcov/index.html" -ForegroundColor Green
