#!/bin/bash
# Test Enhanced Barbossa System - Comprehensive validation

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "================================================"
echo "BARBOSSA ENHANCED SYSTEM TEST SUITE"
echo "Started: $(date)"
echo "================================================"
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0

# Test function
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    echo -n "Testing $test_name... "
    
    if eval "$test_command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PASSED${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗ FAILED${NC}"
        ((TESTS_FAILED++))
    fi
}

echo "1. SYSTEM PREREQUISITES"
echo "------------------------"

# Test Python version
run_test "Python 3.8+" "python3 -c 'import sys; exit(0 if sys.version_info >= (3,8) else 1)'"

# Test required Python modules
run_test "psutil module" "python3 -c 'import psutil'"
run_test "Flask module" "python3 -c 'import flask'"
run_test "requests module" "python3 -c 'import requests'"

# Test directory structure
run_test "Logs directory" "[ -d 'logs' ]"
run_test "Work tracking directory" "[ -d 'work_tracking' ]"
run_test "State directory" "[ -d 'state' ]"
run_test "Web portal directory" "[ -d 'web_portal' ]"

echo ""
echo "2. CORE MODULES"
echo "----------------"

# Test core Python modules
run_test "Barbossa main module" "python3 -c 'import barbossa'"
run_test "Security guard module" "python3 -c 'import security_guard'"
run_test "Ticket enrichment module" "python3 -c 'import ticket_enrichment'"
run_test "Server manager module" "python3 -c 'import server_manager'"

# Test new scripts
run_test "Enhanced cron script" "[ -x 'setup_enhanced_cron.sh' ]"
run_test "Ticket enrichment script" "[ -x 'run_ticket_enrichment.sh' ]"
run_test "Infrastructure check script" "[ -x 'run_infrastructure_check.sh' ]"
run_test "Daily summary script" "[ -x 'run_daily_summary.sh' ]"
run_test "Performance check script" "[ -x 'run_performance_check.sh' ]"

echo ""
echo "3. WEB PORTAL APIS"
echo "-------------------"

# Start web portal temporarily for testing
echo "Starting web portal for API tests..."
cd web_portal
python3 app.py > /tmp/portal_test.log 2>&1 &
PORTAL_PID=$!
cd ..
sleep 5

# Test API endpoints
run_test "Portal health check" "curl -k -s https://localhost:8443/health | grep -q 'healthy'"
run_test "Work distribution API" "curl -k -s https://localhost:8443/api/v4/work-distribution"
run_test "Anomalies API" "curl -k -s https://localhost:8443/api/v4/anomalies"
run_test "Integrations API" "curl -k -s https://localhost:8443/api/v4/integrations"
run_test "Optimizations API" "curl -k -s https://localhost:8443/api/v4/optimizations"
run_test "Performance metrics API" "curl -k -s https://localhost:8443/api/v4/performance-metrics"

# Kill test portal
kill $PORTAL_PID 2>/dev/null

echo ""
echo "4. TICKET ENRICHMENT"
echo "--------------------"

# Test ticket enrichment functionality
run_test "Ticket engine initialization" "python3 -c 'from ticket_enrichment import TicketEnrichmentEngine; engine = TicketEnrichmentEngine()'"
run_test "GitHub token check" "[ ! -z \"\$GITHUB_TOKEN\" ]"
run_test "Repository whitelist" "[ -f 'config/repository_whitelist.json' ]"

echo ""
echo "5. SCHEDULING SYSTEM"
echo "--------------------"

# Check cron syntax
run_test "Cron syntax validation" "bash -n setup_enhanced_cron.sh"

# Simulate cron entries (dry run)
echo "Simulating cron schedule..."
CRON_ENTRIES=(
    "0 9 * * * - Daily ticket enrichment"
    "0 */6 * * * - Personal projects (6hr)"
    "0 2,10,18 * * * - Davy Jones (8hr)"
    "0 */2 * * * - Infrastructure check (2hr)"
    "0 3 * * 0 - Barbossa self-improvement (weekly)"
    "0 23 * * * - Daily summary"
    "30 */4 * * * - Performance check (4hr)"
)

for entry in "${CRON_ENTRIES[@]}"; do
    echo "  - $entry"
done

echo ""
echo "6. PERFORMANCE TESTS"
echo "--------------------"

# Test performance monitoring
run_test "CPU monitoring" "python3 -c 'import psutil; print(psutil.cpu_percent())'"
run_test "Memory monitoring" "python3 -c 'import psutil; print(psutil.virtual_memory().percent)'"
run_test "Disk monitoring" "python3 -c 'import psutil; print(psutil.disk_usage(\"/\").percent)'"

echo ""
echo "7. SECURITY VALIDATION"
echo "----------------------"

# Test security guard
run_test "Security guard active" "python3 -c 'from security_guard import security_guard; security_guard.is_repository_allowed(\"https://github.com/ADWilkinson/test\")'"
run_test "ZKP2P blocking" "python3 -c 'from security_guard import security_guard; exit(0 if not security_guard.is_repository_allowed(\"https://github.com/zkp2p/test\") else 1)'"

echo ""
echo "8. INTEGRATION TESTS"
echo "--------------------"

# Test work area selection
run_test "Work area selection" "python3 -c 'from barbossa import BarbossaEnhanced; b = BarbossaEnhanced(); area = b.select_work_area(); print(area)'"

# Test work tally
run_test "Work tally loading" "python3 -c 'from barbossa import BarbossaEnhanced; b = BarbossaEnhanced(); tally = b._load_work_tally(); print(tally)'"

echo ""
echo "9. END-TO-END TEST"
echo "------------------"

# Create a test session
echo "Creating test Barbossa session..."
python3 - <<'EOF'
import sys
sys.path.append('.')
from barbossa import BarbossaEnhanced

try:
    barbossa = BarbossaEnhanced()
    print("✓ Barbossa initialized successfully")
    
    # Test ticket engine
    if barbossa.ticket_engine:
        print("✓ Ticket engine available")
    else:
        print("⚠ Ticket engine not available")
    
    # Test server manager
    if barbossa.server_manager:
        print("✓ Server manager available")
    else:
        print("⚠ Server manager not available")
    
    # Test work distribution
    distribution = barbossa._get_work_distribution_stats()
    print(f"✓ Work distribution calculated: {len(distribution)} areas")
    
    sys.exit(0)
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ End-to-end test PASSED${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ End-to-end test FAILED${NC}"
    ((TESTS_FAILED++))
fi

echo ""
echo "================================================"
echo "TEST RESULTS"
echo "================================================"
echo ""
echo -e "Tests Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests Failed: ${RED}$TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ ALL TESTS PASSED!${NC}"
    echo ""
    echo "The enhanced Barbossa system is ready for deployment."
    echo "Run './setup_enhanced_cron.sh' to enable the new scheduling."
    exit 0
else
    echo -e "${RED}⚠️  SOME TESTS FAILED${NC}"
    echo ""
    echo "Please review the failed tests and fix any issues before deployment."
    exit 1
fi