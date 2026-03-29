#!/bin/bash
set -e

echo "🔨 Building Smart Attendance System for Railway..."

# Install backend dependencies
echo "📦 Installing Python dependencies..."
pip install -r backend/requirements.txt

# Install frontend dependencies
echo "📦 Installing Node.js dependencies..."
cd frontend
npm install

# Build frontend
echo "🏗️ Building frontend..."
npm run build

cd ..

echo "✅ Build complete!"
