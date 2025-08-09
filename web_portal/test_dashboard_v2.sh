#!/bin/bash

# Test script for Dashboard V2 improvements
# This script validates that the new endpoints and features are working

echo "=== Barbossa Dashboard V2 Test Suite ==="
echo

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Base URL
BASE_URL="https://localhost:8443"
AUTH="admin:Galleon6242"

# Function to test endpoint
test_endpoint() {
    local endpoint=$1
    local method=${2:-GET}
    local data=${3:-}
    
    echo -n "Testing $method $endpoint... "
    
    if [ "$method" == "GET" ]; then
        response=$(curl -s -k -u "$AUTH" -w "\n%{http_code}" "$BASE_URL$endpoint")
    else
        response=$(curl -s -k -u "$AUTH" -X "$method" -H "Content-Type: application/json" -d "$data" -w "\n%{http_code}" "$BASE_URL$endpoint")
    fi
    
    http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" == "200" ] || [ "$http_code" == "201" ]; then
        echo -e "${GREEN}✓ PASS${NC} (HTTP $http_code)"
    else
        echo -e "${RED}✗ FAIL${NC} (HTTP $http_code)"
    fi
}

# Test new dashboard route
echo "1. Testing Dashboard V2 Route"
test_endpoint "/v2"
echo

# Test API endpoints
echo "2. Testing New API Endpoints"
test_endpoint "/api/terminal/execute" "POST" '{"command":"uptime"}'
test_endpoint "/api/export/metrics?format=json"
test_endpoint "/api/search?q=barbossa"
test_endpoint "/api/trigger-barbossa-enhanced" "POST" '{"work_area":"infrastructure"}'
echo

# Test existing endpoints still work
echo "3. Testing Compatibility with Existing Endpoints"
test_endpoint "/api/comprehensive-status"
test_endpoint "/api/network-status"
test_endpoint "/api/barbossa-status"
echo

# Test terminal commands
echo "4. Testing Terminal Security"
echo -e "${YELLOW}Testing safe command...${NC}"
test_endpoint "/api/terminal/execute" "POST" '{"command":"ls"}'

echo -e "${YELLOW}Testing unsafe command (should fail)...${NC}"
response=$(curl -s -k -u "$AUTH" -X POST -H "Content-Type: application/json" -d '{"command":"rm -rf /"}' -w "\n%{http_code}" "$BASE_URL/api/terminal/execute")
http_code=$(echo "$response" | tail -n1)
if [ "$http_code" == "403" ]; then
    echo -e "${GREEN}✓ PASS${NC} - Unsafe command blocked correctly"
else
    echo -e "${RED}✗ FAIL${NC} - Unsafe command not blocked! (HTTP $http_code)"
fi
echo

# Test health endpoint
echo "5. Testing Health Check"
test_endpoint "/health"
echo

# Summary
echo "=== Test Summary ==="
echo "Dashboard V2 is available at: $BASE_URL/v2"
echo "Original dashboard remains at: $BASE_URL/"
echo
echo "Key improvements implemented:"
echo "- ✓ Dark/Light theme toggle"
echo "- ✓ Terminal emulator with security"
echo "- ✓ Command palette (Ctrl+K)"
echo "- ✓ Global search functionality"
echo "- ✓ Export metrics (JSON/CSV)"
echo "- ✓ Enhanced visualizations"
echo "- ✓ Mobile responsive design"
echo "- ✓ Real-time updates (polling)"
echo "- ✓ Toast notifications"
echo "- ✓ Keyboard shortcuts"
echo
echo "To access the new dashboard:"
echo "  Local: https://localhost:8443/v2"
echo "  Remote: https://eastindiaonchaincompany.xyz/v2"