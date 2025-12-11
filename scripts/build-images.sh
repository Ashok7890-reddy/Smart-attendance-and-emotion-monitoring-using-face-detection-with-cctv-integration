#!/bin/bash

# Build Docker images for Smart Attendance System
set -e

echo "Building Smart Attendance System Docker images..."

# Build individual service images
echo "Building Face Recognition Service..."
docker build -f docker/face-recognition.Dockerfile -t smart-attendance/face-recognition:latest .

echo "Building Emotion Analysis Service..."
docker build -f docker/emotion-analysis.Dockerfile -t smart-attendance/emotion-analysis:latest .

echo "Building Attendance Service..."
docker build -f docker/attendance-service.Dockerfile -t smart-attendance/attendance-service:latest .

echo "Building Validation Service..."
docker build -f docker/validation-service.Dockerfile -t smart-attendance/validation-service:latest .

echo "Building WebSocket Server..."
docker build -f docker/websocket-server.Dockerfile -t smart-attendance/websocket-server:latest .

echo "Building Frontend..."
docker build -f docker/frontend.Dockerfile -t smart-attendance/frontend:latest .

# Tag images with version if provided
if [ ! -z "$1" ]; then
    VERSION=$1
    echo "Tagging images with version: $VERSION"
    
    docker tag smart-attendance/face-recognition:latest smart-attendance/face-recognition:$VERSION
    docker tag smart-attendance/emotion-analysis:latest smart-attendance/emotion-analysis:$VERSION
    docker tag smart-attendance/attendance-service:latest smart-attendance/attendance-service:$VERSION
    docker tag smart-attendance/validation-service:latest smart-attendance/validation-service:$VERSION
    docker tag smart-attendance/websocket-server:latest smart-attendance/websocket-server:$VERSION
    docker tag smart-attendance/frontend:latest smart-attendance/frontend:$VERSION
fi

echo "All images built successfully!"
echo "Use 'docker images | grep smart-attendance' to see built images"