#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "========================================="
echo "   Restarting Retirement Calculator     "
echo "========================================="
echo ""

# Stop all services first
echo -e "${YELLOW}Stopping all services...${NC}"
"$SCRIPT_DIR/stop_services.sh"

echo ""
echo -e "${YELLOW}Waiting for services to fully stop...${NC}"
sleep 2

echo ""
echo -e "${YELLOW}Starting services...${NC}"
"$SCRIPT_DIR/check_services.sh"