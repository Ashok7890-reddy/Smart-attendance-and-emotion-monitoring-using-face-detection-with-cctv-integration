@echo off
REM Start Smart Attendance System in development mode

echo Starting Smart Attendance System in development mode...

REM Check if Docker is available
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Docker is not installed or not in PATH. Please install Docker first.
    exit /b 1
)

REM Check if Docker Compose is available
docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Docker Compose is not installed or not in PATH. Please install Docker Compose first.
    exit /b 1
)

REM Create necessary directories
echo Creating necessary directories...
if not exist models mkdir models
if not exist logs mkdir logs

REM Copy environment file if it doesn't exist
if not exist .env.development (
    echo Creating .env.development from .env.example...
    copy .env.example .env.development
)

REM Start services using Docker Compose
echo Starting services with Docker Compose...
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
if %errorlevel% neq 0 (
    echo Failed to start services
    exit /b %errorlevel%
)

echo Waiting for services to be ready...
timeout /t 30 /nobreak >nul

REM Check service health
echo Checking service health...
docker-compose ps

echo.
echo Development environment started successfully!
echo.
echo Services are available at:
echo - Frontend: http://localhost:3000
echo - API Gateway: http://localhost:8000
echo - Face Recognition Service: http://localhost:8001
echo - Emotion Analysis Service: http://localhost:8002
echo - Attendance Service: http://localhost:8003
echo - Validation Service: http://localhost:8004
echo - WebSocket Server: ws://localhost:8080
echo - PostgreSQL: localhost:5432
echo - Redis: localhost:6379
echo.
echo To view logs: docker-compose logs -f [service_name]
echo To stop services: docker-compose down