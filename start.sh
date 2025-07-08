#!/bin/bash

# GenAI Contract Management System - Quick Start Script

echo "🚀 Starting GenAI Contract Management System..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "📄 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your API keys before continuing!"
    echo "   Required: OPENAI_API_KEY"
    echo "   Optional: DOCUSIGN_CLIENT_ID, DOCUSIGN_CLIENT_SECRET"
    read -p "Press Enter to continue after editing .env file..."
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Create upload directories
echo "📁 Creating upload directories..."
mkdir -p uploads/contracts
mkdir -p uploads/proposals

# Start the application
echo "🐳 Starting Docker containers..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check if services are running
if docker-compose ps | grep -q "Up"; then
    echo "✅ Services started successfully!"
    echo ""
    echo "🌐 Access the application:"
    echo "   Frontend: http://localhost:3000"
    echo "   API Docs: http://localhost:8000/docs"
    echo "   API Health: http://localhost:8000/health"
    echo ""
    echo "🔑 Default admin credentials will be created automatically"
    echo "   Email: admin@company.com"
    echo "   Password: admin123"
    echo ""
    echo "📊 View logs:"
    echo "   docker-compose logs -f"
    echo ""
    echo "🛑 Stop the system:"
    echo "   docker-compose down"
else
    echo "❌ Failed to start services. Check the logs:"
    echo "   docker-compose logs"
fi