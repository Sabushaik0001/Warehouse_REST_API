#!/bin/bash

# Warehouse REST API - Unified Deployment Script
# Author: Tushar J
# Usage: ./deploy.sh [start|stop|restart|status|test|logs|docker-start|docker-stop|docker-status]

VENV_DIR=".venv"
APP_HOST="0.0.0.0"
APP_PORT="8081"
PID_FILE="app.pid"
LOG_FILE="logs/fastapi.log"
DOCKER_CONTAINER="warehouse-rest-api"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored messages
print_info() { echo -e "${BLUE}ℹ${NC} $1"; }
print_success() { echo -e "${GREEN}✓${NC} $1"; }
print_error() { echo -e "${RED}✗${NC} $1"; }
print_warning() { echo -e "${YELLOW}⚠${NC} $1"; }

# Check if .env exists
check_env() {
    if [ ! -f .env ]; then
        print_error ".env file not found!"
        echo "Please create .env file with required environment variables"
        exit 1
    fi
}

# Setup virtual environment
setup_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        print_info "Creating virtual environment in $VENV_DIR..."
        python3 -m venv "$VENV_DIR"
        print_success "Virtual environment created"
    fi
    
    source "$VENV_DIR/bin/activate"
    
    # Check if requirements need to be installed
    if ! python -c "import fastapi" 2>/dev/null; then
        print_info "Installing dependencies..."
        pip install --upgrade pip -q
        pip install -r requirements.txt -q
        print_success "Dependencies installed"
    fi
}

# Start application
start_app() {
    check_env
    
    # Check if already running
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            print_warning "Application is already running (PID: $PID)"
            print_info "Use './deploy.sh stop' to stop it first"
            exit 1
        else
            rm -f "$PID_FILE"
        fi
    fi
    
    setup_venv
    
    # Create logs directory
    mkdir -p logs
    
    print_info "Starting Warehouse REST API on port $APP_PORT..."
    
    # Start with nohup
    nohup uvicorn app.main:app --host "$APP_HOST" --port "$APP_PORT" --reload > "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    
    # Wait and verify
    sleep 2
    
    if ps -p $(cat "$PID_FILE") > /dev/null 2>&1; then
        print_success "Application started successfully!"
        echo ""
        echo "  PID: $(cat $PID_FILE)"
        echo "  API: http://$APP_HOST:$APP_PORT"
        echo "  Docs: http://$APP_HOST:$APP_PORT/docs"
        echo "  Logs: tail -f $LOG_FILE"
        echo ""
        print_info "Use './deploy.sh status' to check status"
        print_info "Use './deploy.sh logs' to view logs"
    else
        print_error "Failed to start application!"
        print_info "Check $LOG_FILE for errors"
        exit 1
    fi
}

# Stop application
stop_app() {
    if [ ! -f "$PID_FILE" ]; then
        # Try to find process on port
        PID=$(lsof -ti:$APP_PORT 2>/dev/null)
        if [ ! -z "$PID" ]; then
            print_info "Found process on port $APP_PORT (PID: $PID)"
            kill $PID 2>/dev/null
            sleep 2
            if ps -p $PID > /dev/null 2>&1; then
                kill -9 $PID 2>/dev/null
            fi
            print_success "Application stopped"
        else
            print_warning "Application is not running"
        fi
        return
    fi
    
    PID=$(cat "$PID_FILE")
    
    if ps -p "$PID" > /dev/null 2>&1; then
        print_info "Stopping application (PID: $PID)..."
        kill $PID
        
        # Wait for graceful shutdown
        for i in {1..10}; do
            if ! ps -p "$PID" > /dev/null 2>&1; then
                break
            fi
            sleep 1
        done
        
        # Force kill if still running
        if ps -p "$PID" > /dev/null 2>&1; then
            print_warning "Forcing kill..."
            kill -9 $PID
        fi
        
        rm -f "$PID_FILE"
        print_success "Application stopped"
    else
        print_warning "Process not found (stale PID file)"
        rm -f "$PID_FILE"
    fi
}

# Check status
check_status() {
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Warehouse REST API Status"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        
        if ps -p "$PID" > /dev/null 2>&1; then
            print_success "Status: RUNNING"
            echo ""
            echo "  PID: $PID"
            echo "  Port: $APP_PORT"
            
            # Show process info
            ps -p $PID -o pid,ppid,%cpu,%mem,etime,cmd --no-headers
            echo ""
            
            # Test API
            if response=$(curl -s -m 3 http://localhost:$APP_PORT/health 2>&1); then
                if echo "$response" | grep -q "healthy"; then
                    print_success "API Health: HEALTHY"
                else
                    print_warning "API Health: UNKNOWN"
                fi
            else
                print_error "API Health: NOT RESPONDING"
            fi
            
            echo ""
            echo "  API: http://localhost:$APP_PORT"
            echo "  Docs: http://localhost:$APP_PORT/docs"
            
        else
            print_error "Status: NOT RUNNING (stale PID)"
            rm -f "$PID_FILE"
        fi
    else
        print_error "Status: NOT RUNNING"
        echo ""
        print_info "Use './deploy.sh start' to start the application"
    fi
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Run tests
run_tests() {
    print_info "Running test suite..."
    echo ""
    
    # Check if unit tests should run
    if [ "$1" == "unit" ]; then
        print_info "Running unit tests only..."
        setup_venv
        
        # Run tests and capture output
        test_output=$(pytest tests/unit/ -v --tb=short 2>&1)
        test_exit_code=$?
        
        echo "$test_output"
        
        # Extract and display statistics
        if echo "$test_output" | grep -q "passed"; then
            stats_line=$(echo "$test_output" | grep -E "passed|failed" | tail -1)
            passed=$(echo "$stats_line" | grep -oP '\d+(?= passed)' || echo "0")
            failed=$(echo "$stats_line" | grep -oP '\d+(?= failed)' || echo "0")
            total=$((passed + failed))
            
            if [ "$total" -gt 0 ]; then
                percentage=$(awk "BEGIN {printf \"%.1f\", ($passed/$total)*100}")
                echo ""
                echo "Unit Tests: $passed/$total passed (${percentage}%)"
            fi
        fi
        
        return $test_exit_code
    fi
    
    # Check if integration tests should run
    if [ "$1" == "integration" ]; then
        print_info "Running integration tests (requires running API)..."
        setup_venv
        pytest tests/integration/ -v --tb=short
        return $?
    fi
    
    # Check if coverage report should be generated
    if [ "$1" == "coverage" ]; then
        print_info "Running tests with coverage report..."
        setup_venv
        
        # Run pytest with coverage and capture output
        coverage_output=$(pytest --cov=app --cov-report=term-missing --cov-report=html 2>&1)
        coverage_exit_code=$?
        
        # Display the output
        echo "$coverage_output"
        
        # Extract test statistics
        if echo "$coverage_output" | grep -q "passed"; then
            stats_line=$(echo "$coverage_output" | grep -E "passed|failed" | tail -1)
            
            passed=$(echo "$stats_line" | grep -oP '\d+(?= passed)' || echo "0")
            failed=$(echo "$stats_line" | grep -oP '\d+(?= failed)' || echo "0")
            total=$((passed + failed))
            
            if [ "$total" -gt 0 ]; then
                percentage=$(awk "BEGIN {printf \"%.1f\", ($passed/$total)*100}")
                
                echo ""
                echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                echo "  Test Results: $passed/$total passed (${percentage}%)"
                echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            fi
        fi
        
        echo ""
        print_success "Coverage report generated in htmlcov/"
        print_info "Open htmlcov/index.html in your browser"
        
        return $coverage_exit_code
    fi
    
    # Check if all pytest tests should run
    if [ "$1" == "pytest" ]; then
        print_info "Running all pytest tests..."
        setup_venv
        
        # Run pytest and capture output
        pytest_output=$(pytest -v 2>&1)
        pytest_exit_code=$?
        
        # Display the output
        echo "$pytest_output"
        
        # Extract test statistics
        if echo "$pytest_output" | grep -q "passed"; then
            stats_line=$(echo "$pytest_output" | grep -E "passed|failed" | tail -1)
            
            # Extract numbers
            passed=$(echo "$stats_line" | grep -oP '\d+(?= passed)' || echo "0")
            failed=$(echo "$stats_line" | grep -oP '\d+(?= failed)' || echo "0")
            
            # Calculate total and percentage
            total=$((passed + failed))
            
            if [ "$total" -gt 0 ]; then
                percentage=$(awk "BEGIN {printf \"%.1f\", ($passed/$total)*100}")
                
                echo ""
                echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                echo "  Test Results Summary"
                echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                echo ""
                echo "  Total Tests:  $total"
                echo "  Passed:       $passed"
                echo "  Failed:       $failed"
                echo "  Pass Rate:    ${percentage}%"
                echo ""
                
                if [ "$failed" -eq 0 ]; then
                    print_success "All tests passed! 🎉"
                elif (( $(echo "$percentage >= 80" | bc -l) )); then
                    print_success "Good test coverage (≥80%)"
                else
                    print_warning "Some tests need attention"
                fi
                
                echo ""
                echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            fi
        fi
        
        return $pytest_exit_code
    fi
    
    # Default: Quick API endpoint tests (curl-based)
    print_info "Testing API endpoints (use './deploy.sh test pytest' for full test suite)..."
    echo ""
    
    BASE_URL="http://localhost:$APP_PORT"
    PASSED=0
    FAILED=0
    
    # Test 1: Health Check
    echo -n "  Health Check... "
    if response=$(curl -s -f "$BASE_URL/health" 2>&1) && echo "$response" | grep -q "healthy"; then
        echo -e "${GREEN}✓${NC}"
        ((PASSED++))
    else
        echo -e "${RED}✗${NC}"
        ((FAILED++))
    fi
    
    # Test 2: API Docs
    echo -n "  API Docs... "
    if curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/docs" 2>&1 | grep -q "200"; then
        echo -e "${GREEN}✓${NC}"
        ((PASSED++))
    else
        echo -e "${RED}✗${NC}"
        ((FAILED++))
    fi
    
    # Test 3: OpenAPI Schema
    echo -n "  OpenAPI Schema... "
    if curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/openapi.json" 2>&1 | grep -q "200"; then
        echo -e "${GREEN}✓${NC}"
        ((PASSED++))
    else
        echo -e "${RED}✗${NC}"
        ((FAILED++))
    fi
    
    # Test 4: Warehouses Endpoint
    echo -n "  Warehouses Endpoint... "
    if response=$(curl -s -f "$BASE_URL/api/v1/warehouses" 2>&1) && echo "$response" | grep -q '\['; then
        echo -e "${GREEN}✓${NC}"
        ((PASSED++))
    else
        echo -e "${YELLOW}⚠${NC} (may need data)"
        ((PASSED++))
    fi
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Results: $PASSED passed, $FAILED failed"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    [ $FAILED -eq 0 ] && exit 0 || exit 1
}

# View logs
view_logs() {
    if [ -f "$LOG_FILE" ]; then
        print_info "Showing logs (Ctrl+C to exit)..."
        tail -f "$LOG_FILE"
    else
        print_warning "Log file not found: $LOG_FILE"
    fi
}

# Docker deployment functions
docker_start() {
    check_env
    
    print_info "Starting Docker deployment..."
    
    # Check if Docker is running
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running!"
        echo "Please start Docker Desktop or Docker daemon"
        exit 1
    fi
    
    # Check if container is already running
    if docker ps | grep -q "$DOCKER_CONTAINER"; then
        print_warning "Container is already running"
        print_info "Use './deploy.sh docker-stop' to stop it first"
        exit 1
    fi
    
    # Build and start with docker compose
    print_info "Building Docker image..."
    docker compose build
    
    print_info "Starting containers..."
    docker compose up -d
    
    # Wait for health check
    print_info "Waiting for container to be healthy..."
    for i in {1..30}; do
        if docker compose ps | grep -q "healthy"; then
            print_success "Docker deployment successful!"
            echo ""
            echo "  Container: $DOCKER_CONTAINER"
            echo "  API: http://localhost:$APP_PORT"
            echo "  Docs: http://localhost:$APP_PORT/docs"
            echo "  Health: http://localhost:$APP_PORT/health"
            echo ""
            print_info "Use './deploy.sh docker-status' to check status"
            print_info "Use './deploy.sh docker-logs' to view logs"
            return 0
        fi
        sleep 1
    done
    
    print_warning "Container started but health check not confirmed yet"
    print_info "Run './deploy.sh docker-status' to check status"
}

docker_stop() {
    print_info "Stopping Docker containers..."
    
    if ! docker ps | grep -q "$DOCKER_CONTAINER"; then
        print_warning "Container is not running"
        return
    fi
    
    docker compose down
    print_success "Docker containers stopped"
}

docker_down() {
    print_info "Stopping and removing Docker containers, networks, and volumes..."
    
    docker compose down -v
    print_success "Docker containers, networks, and volumes removed"
    echo ""
    print_info "To clean up images as well, run: docker system prune -af"
}

docker_status() {
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Docker Deployment Status"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    # Check if Docker is running
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker daemon is not running"
        exit 1
    fi
    
    print_success "Docker daemon is running"
    echo ""
    
    # Check container status
    if docker ps | grep -q "$DOCKER_CONTAINER"; then
        print_success "Container Status: RUNNING"
        echo ""
        docker compose ps
        echo ""
        
        # Check health
        if docker compose ps | grep -q "healthy"; then
            print_success "Health Status: HEALTHY"
        else
            print_warning "Health Status: CHECKING..."
        fi
        
        echo ""
        
        # Test API
        if response=$(curl -s -m 3 http://localhost:$APP_PORT/health 2>&1); then
            if echo "$response" | grep -q "healthy"; then
                print_success "API Responding: YES"
            else
                print_warning "API Responding: UNKNOWN"
            fi
        else
            print_error "API Responding: NO"
        fi
        
        echo ""
        echo "  API: http://localhost:$APP_PORT"
        echo "  Docs: http://localhost:$APP_PORT/docs"
        
    else
        print_error "Container Status: NOT RUNNING"
        echo ""
        print_info "Use './deploy.sh docker-start' to start Docker deployment"
    fi
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

docker_logs() {
    if ! docker ps | grep -q "$DOCKER_CONTAINER"; then
        print_error "Container is not running"
        exit 1
    fi
    
    print_info "Showing Docker logs (Ctrl+C to exit)..."
    docker compose logs -f
}

docker_restart() {
    docker_stop
    sleep 2
    docker_start
}

docker_clean() {
    print_info "Performing complete Docker cleanup..."
    
    # Stop and remove everything
    docker compose down -v
    
    # Clean up Docker system
    print_info "Removing unused Docker images and cache..."
    docker system prune -af --volumes
    
    print_success "Docker cleanup complete!"
    echo ""
    print_info "Run './deploy.sh docker-start' to rebuild and start"
}

# Show usage
show_usage() {
    cat << EOF
Warehouse REST API Deployment Script
Author: Tushar J

Usage: ./deploy.sh [COMMAND]

Standard Deployment Commands (Direct VM):
  start          Start the application with .venv
  stop           Stop the application
  restart        Restart the application
  status         Check application status
  test [type]    Run tests (types: pytest, unit, integration, coverage)
  logs           View live application logs

Docker Deployment Commands:
  docker-start   Build and start with Docker Compose
  docker-stop    Stop Docker containers
  docker-down    Stop and remove containers, networks, volumes
  docker-restart Restart Docker containers
  docker-status  Check Docker deployment status
  docker-logs    View Docker container logs
  docker-clean   Complete cleanup (stop, remove, prune)

Other:
  help           Show this help message

Examples:
  # Standard deployment
  ./deploy.sh start
  ./deploy.sh status
  ./deploy.sh test

  # Docker deployment
  ./deploy.sh docker-start
  ./deploy.sh docker-status
  ./deploy.sh docker-logs
  ./deploy.sh docker-down

  # Complete cleanup
  ./deploy.sh docker-clean

Configuration:
  Virtual Env: $VENV_DIR
  Host: $APP_HOST
  Port: $APP_PORT
  Logs: $LOG_FILE
  Docker Container: $DOCKER_CONTAINER

Note:
  You can also use Docker Compose directly:
    docker compose up -d          # Start
    docker compose down           # Stop
    docker compose down -v        # Stop and remove volumes
    docker compose logs -f        # View logs

EOF
}

# Main script logic
case "${1:-help}" in
    start)
        start_app
        ;;
    stop)
        stop_app
        ;;
    restart)
        stop_app
        sleep 2
        start_app
        ;;
    status)
        check_status
        ;;
    test)
        run_tests "$2"
        ;;
    logs)
        view_logs
        ;;
    docker-start)
        docker_start
        ;;
    docker-stop)
        docker_stop
        ;;
    docker-restart)
        docker_restart
        ;;
    docker-status)
        docker_status
        ;;
    docker-logs)
        docker_logs
        ;;
    docker-down)
        docker_down
        ;;
    docker-clean)
        docker_clean
        ;;
    help|--help|-h)
        show_usage
        ;;
    *)
        print_error "Unknown command: $1"
        echo ""
        show_usage
        exit 1
        ;;
esac
