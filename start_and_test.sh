#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting server and testing new features...${NC}"

# Function to check if server is running
check_server() {
    local max_attempts=10
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
    if curl -s http://localhost:7860/health > /dev/null 2>&1; then
            echo -e "${GREEN}Server is running!${NC}"
            return 0
        fi
        echo "Waiting for server to start... (attempt $((attempt + 1))/$max_attempts)"
        sleep 2
        ((attempt++))
    done
    
    echo -e "${RED}Server failed to start within 20 seconds${NC}"
    return 1
}

# Function to test API endpoints with auth header
test_api() {
    local endpoint=$1
    local method=$2
    local data=$3
    local expected_status=$4
    local description=$5
    local auth_header=$6
    
    echo -e "${YELLOW}Testing: $description${NC}"
    
    if [ "$method" = "GET" ]; then
        if [ -n "$auth_header" ]; then
            response=$(curl -s -w "%{http_code}" -H "Authorization: Bearer $auth_header" -o /tmp/response.json "$endpoint")
        else
            response=$(curl -s -w "%{http_code}" -o /tmp/response.json "$endpoint")
        fi
    else
        if [ -n "$auth_header" ]; then
            response=$(curl -s -w "%{http_code}" -X "$method" -H "Content-Type: application/json" -H "Authorization: Bearer $auth_header" -d "$data" -o /tmp/response.json "$endpoint")
        else
            response=$(curl -s -w "%{http_code}" -X "$method" -H "Content-Type: application/json" -d "$data" -o /tmp/response.json "$endpoint")
        fi
    fi
    
    if [ "$response" = "$expected_status" ]; then
        echo -e "${GREEN}✓ $description - Status: $response${NC}"
        cat /tmp/response.json | jq . 2>/dev/null || cat /tmp/response.json
    else
        echo -e "${RED}✗ $description - Expected: $expected_status, Got: $response${NC}"
        cat /tmp/response.json 2>/dev/null || echo "No response body"
    fi
    echo ""
}

# Kill any existing server process
echo "Stopping any existing server processes..."
pkill -f "server_enhanced.py" || true
pkill -f "uvicorn" || true
sleep 2

# Start the server in the background
echo -e "${GREEN}Starting the server...${NC}"
python server_enhanced.py &
SERVER_PID=$!

# Wait 15 seconds for server to start
echo "Waiting 15 seconds for server to start..."
sleep 15

# Check if server is running
if ! check_server; then
    echo -e "${RED}Failed to start server. Exiting.${NC}"
    kill $SERVER_PID 2>/dev/null || true
    exit 1
fi

echo -e "${GREEN}Server started successfully! PID: $SERVER_PID${NC}"
echo ""

# Test basic health check
test_api "http://localhost:7860/health" "GET" "" "200" "Health check"

# Test root endpoint
test_api "http://localhost:7860/" "GET" "" "200" "Root endpoint"

# Test metrics endpoint
test_api "http://localhost:7860/metrics" "GET" "" "200" "Metrics endpoint"

# Test user registration and login
echo -e "${YELLOW}=== Testing Authentication ===${NC}"

# Register a test user
register_data='{
    "email": "test@example.com",
    "username": "testuser",
    "password": "testpassword123",
    "full_name": "Test User"
}'

test_api "http://localhost:7860/auth/register" "POST" "$register_data" "200" "Register user"

# Login to get token
login_data='{
    "email_or_username": "testuser",
    "password": "testpassword123"
}'

echo -e "${YELLOW}Getting authentication token...${NC}"
login_response=$(curl -s -X POST -H "Content-Type: application/json" \
    -d "$login_data" \
    http://localhost:7860/auth/login)

token=$(echo "$login_response" | jq -r '.token' 2>/dev/null)

if [ "$token" != "null" ] && [ "$token" != "" ]; then
    echo -e "${GREEN}Authentication token obtained: ${token:0:20}...${NC}"
else
    echo -e "${RED}Failed to get authentication token${NC}"
    echo "$login_response"
    token=""
fi
echo ""

# Test authenticated endpoints
echo -e "${YELLOW}=== Testing Authenticated Endpoints ===${NC}"

# Test agents endpoints
test_api "http://localhost:7860/agents/" "GET" "" "401" "Get agents without auth"
test_api "http://localhost:7860/agents/" "GET" "" "200" "Get agents with auth" "$token"

# Test create agent
create_agent_data='{
    "agent_name": "Test Agent",
    "description": "A test agent for API testing",
    "system_prompt": "You are a helpful test agent.",
    "voice_settings": {}
}'

test_api "http://localhost:7860/agents/" "POST" "$create_agent_data" "200" "Create new agent" "$token"

# Test user profile
test_api "http://localhost:7860/auth/profile" "GET" "" "200" "Get user profile" "$token"

# Test API key generation
test_api "http://localhost:7860/auth/api-key" "GET" "" "200" "Get API key" "$token"

# Test rate limiting
echo -e "${YELLOW}=== Testing Rate Limiting ===${NC}"
echo "Making multiple rapid requests to test rate limiting..."

for i in {1..15}; do
    response=$(curl -s -w "%{http_code}" -H "Authorization: Bearer $token" \
        -o /dev/null http://localhost:7860/agents/)
    echo "Request $i: Status $response"
    if [ "$response" = "429" ]; then
        echo -e "${GREEN}✓ Rate limiting working - got 429 Too Many Requests${NC}"
        break
    fi
    sleep 0.1
done

echo -e "${GREEN}=== Testing Complete ===${NC}"
echo "Server is running on PID: $SERVER_PID"
echo "You can access the API at: http://localhost:7860"
echo "API Documentation: http://localhost:7860/docs"
echo ""
echo "To stop the server, run: kill $SERVER_PID"
echo "Or press Ctrl+C to stop this script and the server"

# Keep the script running so server stays up
echo "Press Ctrl+C to stop the server..."
wait $SERVER_PID
