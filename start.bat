@echo off
echo ========================================
echo HRMS Freelancer - Local Development Setup
echo ========================================
echo.

echo Step 1: Pulling Docker images...
docker-compose pull

echo.
echo Step 2: Starting services...
docker-compose up -d

echo.
echo Step 3: Waiting for site creation (this may take 2-3 minutes)...
echo Please wait while the database initializes and ERPNext site is created...
timeout /t 30 /nobreak > nul

:check_site
docker-compose logs create-site 2>&1 | findstr /C:"Successfully created site" > nul
if errorlevel 1 (
    echo Still initializing...
    timeout /t 10 /nobreak > nul
    goto check_site
)

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Access ERPNext at: http://localhost:8080
echo.
echo Login credentials:
echo   Username: Administrator
echo   Password: admin
echo.
echo To install the HRMS Freelancer app, run:
echo   docker-compose exec backend bench --site frontend install-app hrms_freelancer
echo.
echo To stop the services:
echo   docker-compose down
echo.
echo To view logs:
echo   docker-compose logs -f
echo.
pause
