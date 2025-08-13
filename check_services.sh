#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
API_PORT=8020
FRONTEND_PORT=5177
API_URL="http://localhost:${API_PORT}"
FRONTEND_URL="http://localhost:${FRONTEND_PORT}"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "========================================="
echo "   Retirement Calculator Service Check   "
echo "========================================="
echo ""

# Function to check if a port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Function to check API health
check_api_health() {
    if curl -s -f "${API_URL}/health" >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Function to start the API
start_api() {
    echo -e "${YELLOW}Starting API server...${NC}"
    cd "$REPO_DIR/src/backend"
    
    # Kill any existing process on the port
    if check_port $API_PORT; then
        echo "Killing existing process on port $API_PORT..."
        lsof -ti:$API_PORT | xargs kill -9 2>/dev/null
        sleep 2
    fi
    
    # Start the API in background
    nohup uv run uvicorn main:app --reload --port $API_PORT > "$REPO_DIR/api.log" 2>&1 &
    local api_pid=$!
    echo "API started with PID: $api_pid"
    
    # Wait for API to be ready
    echo -n "Waiting for API to be ready"
    for i in {1..30}; do
        if check_api_health; then
            echo ""
            echo -e "${GREEN}✓ API is ready!${NC}"
            return 0
        fi
        echo -n "."
        sleep 1
    done
    echo ""
    echo -e "${RED}✗ API failed to start${NC}"
    return 1
}

# Function to start the frontend
start_frontend() {
    echo -e "${YELLOW}Starting frontend server...${NC}"
    cd "$REPO_DIR/frontend"
    
    # Kill any existing process on the port
    if check_port $FRONTEND_PORT; then
        echo "Killing existing process on port $FRONTEND_PORT..."
        lsof -ti:$FRONTEND_PORT | xargs kill -9 2>/dev/null
        sleep 2
    fi
    
    # Start the frontend in background
    nohup npm run dev > "$REPO_DIR/frontend.log" 2>&1 &
    local frontend_pid=$!
    echo "Frontend started with PID: $frontend_pid"
    
    # Wait for frontend to be ready
    echo -n "Waiting for frontend to be ready"
    for i in {1..30}; do
        if check_port $FRONTEND_PORT; then
            echo ""
            echo -e "${GREEN}✓ Frontend is ready!${NC}"
            return 0
        fi
        echo -n "."
        sleep 1
    done
    echo ""
    echo -e "${RED}✗ Frontend failed to start${NC}"
    return 1
}

# Check API status
echo "Checking API status..."
if check_port $API_PORT; then
    if check_api_health; then
        echo -e "${GREEN}✓ API is running and healthy on port $API_PORT${NC}"
        api_status="running"
    else
        echo -e "${YELLOW}⚠ API port $API_PORT is in use but not responding to health check${NC}"
        echo "Do you want to restart the API? (y/n)"
        read -r restart_api
        if [[ $restart_api == "y" ]]; then
            start_api
            api_status="restarted"
        else
            api_status="unhealthy"
        fi
    fi
else
    echo -e "${RED}✗ API is not running${NC}"
    start_api
    api_status="started"
fi

echo ""

# Check Frontend status
echo "Checking frontend status..."
if check_port $FRONTEND_PORT; then
    # Try to fetch the frontend
    if curl -s -f "$FRONTEND_URL" >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Frontend is running on port $FRONTEND_PORT${NC}"
        frontend_status="running"
    else
        echo -e "${YELLOW}⚠ Frontend port $FRONTEND_PORT is in use but not responding${NC}"
        echo "Do you want to restart the frontend? (y/n)"
        read -r restart_frontend
        if [[ $restart_frontend == "y" ]]; then
            start_frontend
            frontend_status="restarted"
        else
            frontend_status="unresponsive"
        fi
    fi
else
    echo -e "${RED}✗ Frontend is not running${NC}"
    start_frontend
    frontend_status="started"
fi

echo ""
echo "========================================="
echo "              Service Summary            "
echo "========================================="
echo ""

# Print summary
if [[ $api_status == "running" ]] || [[ $api_status == "started" ]] || [[ $api_status == "restarted" ]]; then
    echo -e "${GREEN}✓ API:${NC}"
    echo "  - URL: $API_URL"
    echo "  - Docs: $API_URL/docs"
    echo "  - Health: $API_URL/health"
    if [[ $api_status == "started" ]] || [[ $api_status == "restarted" ]]; then
        echo "  - Logs: $REPO_DIR/api.log"
    fi
else
    echo -e "${RED}✗ API: Not available${NC}"
fi

echo ""

if [[ $frontend_status == "running" ]] || [[ $frontend_status == "started" ]] || [[ $frontend_status == "restarted" ]]; then
    echo -e "${GREEN}✓ Frontend:${NC}"
    echo "  - URL: $FRONTEND_URL"
    if [[ $frontend_status == "started" ]] || [[ $frontend_status == "restarted" ]]; then
        echo "  - Logs: $REPO_DIR/frontend.log"
    fi
else
    echo -e "${RED}✗ Frontend: Not available${NC}"
fi

echo ""
echo "========================================="

# Show running processes
echo ""
echo "Running processes:"
echo ""
ps aux | grep -E "(uvicorn|vite|npm)" | grep -v grep | awk '{print "  PID " $2 ": " $11 " " $12 " " $13 " " $14}'

echo ""

# Exit with appropriate code
if [[ ($api_status == "running" || $api_status == "started" || $api_status == "restarted") && 
      ($frontend_status == "running" || $frontend_status == "started" || $frontend_status == "restarted") ]]; then
    echo -e "${GREEN}All services are operational!${NC}"
    exit 0
else
    echo -e "${YELLOW}Some services may need attention${NC}"
    exit 1
fi