#!/bin/bash

# Start Smart Attendance System in development mode
set -e

echo "Starting Smart Attendance System in development mode..."

# Check if Docker and Docker Compose are available
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p models logs

# Copy environment file if it doesn't exist
if [ ! -f .env.development ]; then
    echo "Creating .env.development from .env.example..."
    cp .env.example .env.development
fi

# Start services using Docker Compose
echo "Starting services with Docker Compose..."
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

echo "Waiting for services to be ready..."
sleep 30

# Check service health
echo "Checking service health..."
services=("postgres" "redis" "face_recognition_service" "emotion_analysis_service" "attendance_service" "validation_service" "api_gateway" "websocket_server")

for service in "${services[@]}"; do
    if docker-compose ps | grep -q "$service.*Up"; then
        echo "✓ $service is running"
    else
        echo "✗ $service is not running"
    fi
done

echo ""
echo "Development environment started successfully!"
echo ""
echo "Services are available at:"
echo "- Frontend: http://localhost:3000"
echo "- API Gateway: http://localhost:8000"
echo "- Face Recognition Service: http://localhost:8001"
echo "- Emotion Analysis Service: http://localhost:8002"
echo "- Attendance Service: http://localhost:8003"
echo "- Validation Service: http://localhost:8004"
echo "- WebSocket Server: ws://localhost:8080"
echo "- PostgreSQL: localhost:5432"
echo "- Redis: localhost:6379"
echo ""
echo "To view logs: docker-compose logs -f [service_name]"
echo "To stop services: docker-compose down"