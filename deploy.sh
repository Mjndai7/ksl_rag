#!/bin/bash

# This script helps deploy the GraphRAG engine with Docker Compose

set -e  # Exit on error

echo " GraphRAG Deployment Script"
echo "================================"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo " Error: Docker is not running. Please start Docker first."
    exit 1
fi

# Check if .env.docker exists
if [ ! -f .env.docker ]; then
    echo " Error: .env.docker file not found!"
    echo "Please create .env.docker with your production configuration."
    exit 1
fi

# Check if credentials exist
if [ ! -d "credentials" ]; then
    echo " Warning: credentials directory not found."
    echo " Google Drive integration may not work without credentials."
fi

# Function to show status
show_status() {
    echo ""
    echo "📊 Service Status:"
    echo "-------------------"
    docker compose ps
    echo ""
}

# Function to show logs
show_logs() {
    echo ""
    echo "📋 Following logs (Ctrl+C to exit):"
    echo "-----------------------------------"
    docker compose logs -f
}

# Parse command line arguments
case "${1:-}" in
    "start")
        echo " Starting GraphRAG services..."
        docker compose up -d
        show_status
        echo " GraphRAG is running!"
        echo ""
        echo "📍 Access points:"
        echo "   - API:          http://localhost:8000"
        echo "   - API Docs:     http://localhost:8000/docs"
        echo "   - Neo4j Browser: http://localhost:7474"
        echo "   - Qdrant UI:    http://localhost:6333/dashboard"
        ;;
    
    "stop")
        echo " Stopping GraphRAG services..."
        docker compose down
        echo " All services stopped."
        ;;
    
    "restart")
        echo " Restarting GraphRAG services..."
        docker compose restart
        show_status
        ;;
    
    "logs")
        show_logs
        ;;
    
    "status")
        show_status
        ;;
    
    "build")
        echo "🔨 Building Docker images..."
        docker compose build
        echo " Build complete!"
        ;;
    
    "clean")
        echo " WARNING: This will remove all containers and volumes!"
        echo "All data will be lost. Are you sure? (yes/no)"
        read -r response
        if [[ "$response" == "yes" ]]; then
            docker compose down -v
            echo " All containers and volumes removed."
        else
            echo " Operation cancelled."
        fi
        ;;
    
    "init-db")
        echo " Initializing databases..."
        docker compose up -d postgres neo4j qdrant
        echo " Waiting for databases to be ready..."
        sleep 10
        show_status
        echo " Databases are running!"
        ;;
    
    "help"|*)
        echo ""
        echo "Usage: ./deploy.sh [command]"
        echo ""
        echo "Commands:"
        echo "  start     - Start all services"
        echo "  stop      - Stop all services"
        echo "  restart   - Restart all services"
        echo "  logs      - Show logs (follow mode)"
        echo "  status    - Show service status"
        echo "  build     - Build Docker images"
        echo "  clean     - Remove all containers and volumes (WARNING: deletes data)"
        echo "  init-db   - Start only databases"
        echo "  help      - Show this help message"
        echo ""
        echo "Examples:"
        echo "  ./deploy.sh start     # Start the application"
        echo "  ./deploy.sh logs      # View logs"
        echo "  ./deploy.sh stop      # Stop everything"
        echo ""
        ;;
esac
