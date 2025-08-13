#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
API_PORT=8020
FRONTEND_PORT=5177

echo "========================================="
echo "   Stopping Retirement Calculator       "
echo "========================================="
echo ""

# Function to stop service on a port
stop_service() {
    local port=$1
    local service_name=$2
    
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${YELLOW}Stopping $service_name on port $port...${NC}"
        lsof -ti:$port | xargs kill -9 2>/dev/null
        sleep 1
        
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            echo -e "${RED}✗ Failed to stop $service_name${NC}"
            return 1
        else
            echo -e "${GREEN}✓ $service_name stopped${NC}"
            return 0
        fi
    else
        echo -e "${YELLOW}$service_name is not running on port $port${NC}"
        return 0
    fi
}

# Stop API
stop_service $API_PORT "API"

# Stop Frontend
stop_service $FRONTEND_PORT "Frontend"

echo ""
echo "========================================="
echo -e "${GREEN}All services stopped${NC}"
echo "========================================="