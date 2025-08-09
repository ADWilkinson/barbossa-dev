#!/bin/bash
echo "=== Testing Barbossa Dashboard ==="

# Test basic API endpoints
echo "Testing API endpoints..."

# Test status endpoint
curl -s -k -u admin:Galleon6242 https://localhost:8443/api/status | jq . > /dev/null
if [ $? -eq 0 ]; then
    echo "✅ Status API working"
else
    echo "❌ Status API failed"
fi

# Test services endpoint
curl -s -k -u admin:Galleon6242 https://localhost:8443/api/services | jq . > /dev/null
if [ $? -eq 0 ]; then
    echo "✅ Services API working"
else
    echo "❌ Services API failed"
fi

# Test changelogs endpoint
curl -s -k -u admin:Galleon6242 https://localhost:8443/api/changelogs | jq . > /dev/null
if [ $? -eq 0 ]; then
    echo "✅ Changelogs API working"
else
    echo "❌ Changelogs API failed"
fi

# Test main dashboard page
curl -s -k -u admin:Galleon6242 https://localhost:8443/ | grep -q "Barbossa Control Center"
if [ $? -eq 0 ]; then
    echo "✅ Main dashboard page loads"
else
    echo "❌ Main dashboard page failed"
fi

echo "=== Dashboard Test Complete ==="