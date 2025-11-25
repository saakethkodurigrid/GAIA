#!/bin/bash

# Setup script for Code Executor Service

echo "========================================="
echo "  Code Executor Service Setup"
echo "========================================="
echo ""

# Check if Docker is installed
echo "Checking Docker installation..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed!"
    echo "Please install Docker from: https://docs.docker.com/get-docker/"
    exit 1
fi
echo "✓ Docker is installed"

# Check if Docker daemon is running
echo ""
echo "Checking Docker daemon..."
if ! docker ps &> /dev/null; then
    echo "❌ Docker daemon is not running!"
    echo "Please start Docker and try again."
    exit 1
fi
echo "✓ Docker daemon is running"

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
pip install docker psutil

# Pull required Docker images
echo ""
echo "Pulling required Docker images..."
echo "This may take a few minutes..."

echo ""
echo "Pulling Python 3.11 image..."
docker pull python:3.11-slim

echo ""
echo "Pulling Node.js 20 image..."
docker pull node:20-slim

echo ""
echo "Pulling OpenJDK 17 image..."
docker pull openjdk:17-slim

# Create output directory
echo ""
echo "Creating output directory..."
mkdir -p outputs
echo "✓ Output directory created"

# Run validation
echo ""
echo "========================================="
echo "  Running validation tests..."
echo "========================================="
echo ""
python validate_service.py

echo ""
echo "========================================="
echo "  Setup Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "  1. Run tests: python test_executor.py"
echo "  2. Check validation: python validate_service.py"
echo "  3. View outputs in: ./outputs/"
echo ""



