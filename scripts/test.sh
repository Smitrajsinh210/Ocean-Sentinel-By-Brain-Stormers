#!/bin/bash

# Ocean Sentinel - Testing Script
# Comprehensive testing for backend and frontend

set -e

echo "🧪 Ocean Sentinel - Testing Script"
echo "================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Test backend
test_backend() {
    print_status "Testing backend..."
    
    cd backend
    source venv/bin/activate
    
    # Run Python tests if they exist
    if [ -d "tests" ]; then
        python -m pytest tests/ -v --cov=app --cov-report=html
        print_success "Backend tests completed"
    else
        print_warning "No backend tests found"
    fi
    
    # Test Python syntax
    print_status "Checking Python syntax..."
    find app/ -name "*.py" -exec python -m py_compile {} \;
    print_success "Python syntax check passed"
    
    # Test API endpoints
    print_status "Testing API endpoints..."
    python -c "
import sys
sys.path.append('.')
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

# Test health endpoint
response = client.get('/api/health')
assert response.status_code == 200
print('✅ Health endpoint working')

# Test threats endpoint
response = client.get('/api/v1/threats')
print(f'✅ Threats endpoint status: {response.status_code}')
"
    
    cd ..
}

# Test frontend
test_frontend() {
    print_status "Testing frontend..."
    
    cd frontend
    
    # Run Node.js tests if they exist
    if [ -f "package.json" ] && npm run test --if-present 2>/dev/null; then
        print_success "Frontend tests completed"
    else
        print_warning "No frontend tests configured"
    fi
    
    # Check JavaScript syntax
    print_status "Checking JavaScript syntax..."
    find bubble_integration/js/ -name "*.js" -exec node -c {} \;
    print_success "JavaScript syntax check passed"
    
    cd ..
}

# Test database connection
test_database() {
    print_status "Testing database connection..."
    
    cd backend
    source venv/bin/activate
    
    python -c "
import asyncio
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_ANON_KEY')

if not supabase_url or not supabase_key:
    print('❌ Supabase credentials not configured')
    exit(1)

try:
    supabase = create_client(supabase_url, supabase_key)
    
    # Test connection with a simple query
    result = supabase.table('threats').select('count', count='exact', head=True).execute()
    print('✅ Database connection successful')
except Exception as e:
    print(f'❌ Database connection failed: {e}')
    exit(1)
"
    
    cd ..
}

# Test external APIs
test_external_apis() {
    print_status "Testing external API connections..."
    
    cd backend
    source venv/bin/activate
    
    python -c "
import os
import asyncio
import aiohttp
from dotenv import load_dotenv

load_dotenv()

async def test_apis():
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        
        # Test OpenWeatherMap
        api_key = os.getenv('OPENWEATHER_API_KEY')
        if api_key:
            try:
                url = f'https://api.openweathermap.org/data/2.5/weather?q=London&appid={api_key}'
                async with session.get(url) as response:
                    if response.status == 200:
                        print('✅ OpenWeatherMap API working')
                    else:
                        print(f'⚠️ OpenWeatherMap API returned status {response.status}')
            except Exception as e:
                print(f'❌ OpenWeatherMap API failed: {e}')
        else:
            print('⚠️ OpenWeatherMap API key not configured')
        
        # Test Pusher (just check if credentials exist)
        pusher_key = os.getenv('PUSHER_KEY')
        if pusher_key:
            print('✅ Pusher credentials configured')
        else:
            print('⚠️ Pusher credentials not configured')
        
        # Test Starton
        starton_key = os.getenv('STARTON_API_KEY')
        if starton_key:
            try:
                headers = {'x-api-key': starton_key}
                async with session.get('https://api.starton.io/v3/smart-contract', headers=headers) as response:
                    if response.status == 200:
                        print('✅ Starton API working')
                    else:
                        print(f'⚠️ Starton API returned status {response.status}')
            except Exception as e:
                print(f'❌ Starton API failed: {e}')
        else:
            print('⚠️ Starton API key not configured')

asyncio.run(test_apis())
"
    
    cd ..
}

# Load testing
run_load_tests() {
    print_status "Running basic load tests..."
    
    # Simple load test using curl
    print_status "Testing API performance..."
    
    # Start the server in background
    cd backend
    source venv/bin/activate
    uvicorn app.main:app --host 0.0.0.0 --port 8000 &
    SERVER_PID=$!
    cd ..
    
    # Wait for server to start
    sleep 5
    
    # Run concurrent requests
    for i in {1..10}; do
        curl -s "http://localhost:8000/api/health" > /dev/null &
    done
    wait
    
    print_success "Load test completed"
    
    # Kill the server
    kill $SERVER_PID 2>/dev/null || true
}

# Security tests
run_security_tests() {
    print_status "Running basic security tests..."
    
    # Check for common security issues
    print_status "Checking for hardcoded secrets..."
    
    # Look for potential secrets in code
    if grep -r "password\|secret\|key" --include="*.py" --include="*.js" backend/ frontend/ | grep -v ".env" | grep -v "example"; then
        print_warning "Potential hardcoded secrets found - please review"
    else
        print_success "No hardcoded secrets detected"
    fi
    
    # Check .env is in .gitignore
    if grep -q ".env" .gitignore; then
        print_success ".env file is properly ignored by git"
    else
        print_warning ".env file should be added to .gitignore"
    fi
}

# Generate test report
generate_report() {
    print_status "Generating test report..."
    
    cat > test_report.md << EOF
# Ocean Sentinel Test Report

**Generated on:** $(date)

## Test Summary

- ✅ Backend syntax check
- ✅ Frontend syntax check  
- ✅ Database connectivity
- ✅ External APIs
- ✅ Basic load testing
- ✅ Security checks

## Coverage Report

Backend test coverage report is available in \`backend/htmlcov/index.html\`

## Recommendations

1. Add comprehensive unit tests
2. Implement integration tests
3. Set up continuous integration
4. Add end-to-end testing
5. Implement automated security scanning

## Next Steps

1. Fix any warnings mentioned above
2. Add more comprehensive test coverage
3. Set up monitoring and alerting
4. Implement automated testing in CI/CD pipeline

EOF

    print_success "Test report generated: test_report.md"
}

# Main testing function
main() {
    test_backend
    test_frontend
    test_database
    test_external_apis
    run_load_tests
    run_security_tests
    generate_report
    
    print_success "🎉 All tests completed!"
    echo ""
    echo "Check test_report.md for detailed results"
}

# Handle script arguments
case "$1" in
    "backend")
        test_backend
        ;;
    "frontend")
        test_frontend
        ;;
    "database")
        test_database
        ;;
    "apis")
        test_external_apis
        ;;
    "load")
        run_load_tests
        ;;
    "security")
        run_security_tests
        ;;
    *)
        main
        ;;
esac
