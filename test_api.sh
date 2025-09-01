#!/bin/bash
# Test Personal Assistant API

# Get password
PASS=$(cat ~/.barbossa_credentials.json | jq -r '.admin')

echo "Testing Personal Assistant API..."
echo "================================"

# Test status endpoint
echo "1. Status endpoint:"
curl -k -u admin:$PASS https://localhost:8443/api/assistant/status 2>/dev/null | python3 -m json.tool

echo ""
echo "2. Stats endpoint:"
curl -k -u admin:$PASS https://localhost:8443/api/assistant/stats 2>/dev/null | python3 -m json.tool

echo ""
echo "3. State details:"
curl -k -u admin:$PASS https://localhost:8443/api/assistant/state-details 2>/dev/null | python3 -m json.tool | head -20