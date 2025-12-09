# Warehouse REST API

**Author**: SABU

A modular FastAPI-based warehouse management system with camera integration, AI-powered video analytics, and real-time monitoring capabilities.

## 🚀 Features

- **Warehouse Management**: Track and monitor multiple warehouses
- **Camera Integration**: AWS Kinesis Video Streams for live feeds
- **AI-Powered Chat**: AWS Bedrock (Claude 3.5 Haiku) for video analytics
- **Activity Logging**: Track employees, vehicles, and inventory
- **Azure Storage**: Store video chunks and transcripts

## ⚡ Quick Start

```bash
# Clone
git clone https://github.com/parabola9p9/warehouse-api-backend.git
cd warehouse-api-backend
git checkout deployment

# Configure
cp .env.example .env
nano .env

# Deploy (auto-creates .venv, installs deps, starts app)
./deploy.sh start
```

**Access**: http://0.0.0.0:8081 | **Docs**: http://0.0.0.0:8081/docs

## 🎮 Commands

### Standard Deployment (Direct VM)
```bash
./deploy.sh start    # Start (creates .venv, installs deps)
./deploy.sh stop     # Stop
./deploy.sh restart  # Restart
./deploy.sh status   # Check status + health
./deploy.sh test     # Run API tests
./deploy.sh logs     # View live logs
```

### Docker Deployment
```bash
./deploy.sh docker-start    # Build & start with Docker Compose
./deploy.sh docker-stop     # Stop Docker containers
./deploy.sh docker-down     # Stop and remove containers + volumes
./deploy.sh docker-restart  # Restart Docker containers
./deploy.sh docker-status   # Check Docker deployment status
./deploy.sh docker-logs     # View Docker container logs
./deploy.sh docker-clean    # Complete cleanup (remove all)
```

### Docker Compose (Without deploy.sh)
You can also use Docker Compose directly:
```bash
# Start deployment
docker compose up -d

# View logs
docker compose logs -f

# Check status
docker compose ps

# Stop deployment
docker compose down

# Stop and remove volumes
docker compose down -v

# Rebuild and start
docker compose up -d --build
```

## 📋 Environment Variables

```bash
# PostgreSQL
PG_HOST=localhost
PG_PORT=5432
PG_USER=user
PG_PASSWORD=pass
PG_DATABASE=warehouse_db

# AWS
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret

# Azure
AZURE_TENANT_ID=your_tenant
AZURE_CLIENT_ID=your_client
AZURE_CLIENT_SECRET=your_secret
AZURE_STORAGE_ACCOUNT_NAME=storage
AZURE_CONTAINER_NAME=container
```

## 🖥️ VM Deployment (20.84.162.92)

### Option 1: Direct Deployment (Recommended for Development)
```bash
# Copy to VM
scp -r . user@20.84.162.92:/home/user/warehouse-api/

# SSH and deploy
ssh user@20.84.162.92
cd /home/user/warehouse-api
./deploy.sh start

# Open firewall
sudo ufw allow 8081/tcp
sudo ufw reload

# Verify
curl http://20.84.162.92:8081/health
```

### Option 2: Docker Deployment (Recommended for Production)

**Method A: Using deploy.sh (Recommended)**
```bash
# Copy to VM
scp -r . user@20.84.162.92:/home/user/warehouse-api/

# SSH and deploy with Docker
ssh user@20.84.162.92
cd /home/user/warehouse-api
./deploy.sh docker-start

# Open firewall
sudo ufw allow 8081/tcp
sudo ufw reload

# Verify
./deploy.sh docker-status
curl http://20.84.162.92:8081/health
```

**Method B: Using Docker Compose directly**
```bash
# Copy to VM
scp -r . user@20.84.162.92:/home/user/warehouse-api/

# SSH and deploy
ssh user@20.84.162.92
cd /home/user/warehouse-api

# Start with Docker Compose
docker compose up -d

# Open firewall
sudo ufw allow 8081/tcp
sudo ufw reload

# Check status
docker compose ps
docker compose logs -f

# Verify
curl http://20.84.162.92:8081/health
```

**Why Docker?**
- ✅ Isolated environment (no conflicts with system packages)
- ✅ Automatic health checks and restarts
- ✅ Consistent deployment across environments
- ✅ Easy rollback and version control
- ✅ Better resource management

## 📡 API Endpoints

- `GET /health` - Health check
- `GET /docs` - API documentation
- `GET /api/v1/warehouses` - List warehouses
- `GET /api/v1/warehouses/{id}` - Warehouse details
- `GET /api/v1/cameras/{name}/stream` - Camera stream
- `GET /api/v1/cameras/logs/employees` - Employee logs
- `POST /api/v1/chat` - AI chat

## � Docker Management

### Quick Commands
```bash
# Using deploy.sh
./deploy.sh docker-start     # Start
./deploy.sh docker-stop      # Stop
./deploy.sh docker-down      # Stop + remove volumes
./deploy.sh docker-restart   # Restart
./deploy.sh docker-status    # Check status
./deploy.sh docker-logs      # View logs
./deploy.sh docker-clean     # Complete cleanup

# Using docker compose directly
docker compose up -d         # Start in background
docker compose down          # Stop containers
docker compose down -v       # Stop + remove volumes
docker compose ps            # Check status
docker compose logs -f       # Follow logs
docker compose restart       # Restart all services
docker compose build         # Rebuild images
docker compose up -d --build # Rebuild and start
```

### Docker Cleanup
```bash
# Remove containers and volumes
./deploy.sh docker-down

# Complete cleanup (including images and cache)
./deploy.sh docker-clean

# Or manually
docker compose down -v
docker system prune -af --volumes
```

---

## 🧪 Testing

### Test Suite Overview

The project includes comprehensive unit tests for all API endpoints using **pytest**. Tests are located in the `tests/` directory with the following structure:

```
tests/
├── __init__.py
├── conftest.py              # Test fixtures and configuration
├── unit/                    # Unit tests (mocked dependencies)
│   ├── __init__.py
│   ├── test_warehouse_endpoints.py
│   ├── test_camera_endpoints.py
│   └── test_chat_endpoint.py
└── integration/             # Integration tests (real dependencies)
    └── __init__.py
```

### Running Tests

#### Quick API Tests (curl-based)
```bash
# Fast smoke tests for running API
./deploy.sh test

# Expected output:
#   Health Check... ✓
#   API Docs... ✓
#   OpenAPI Schema... ✓
#   Warehouses List... ✓
#   Tests Passed: 4/4
```

#### Full Test Suite (pytest)
```bash
# Run all pytest tests
./deploy.sh test pytest

# Run only unit tests
./deploy.sh test unit

# Run only integration tests
./deploy.sh test integration

# Run with coverage report
./deploy.sh test coverage
```

#### Manual pytest Commands
```bash
# Activate virtual environment
source .venv/bin/activate

# Run all tests with verbose output
pytest -v

# Run specific test file
pytest tests/unit/test_warehouse_endpoints.py -v

# Run specific test class
pytest tests/unit/test_warehouse_endpoints.py::TestGetAllWarehouses -v

# Run specific test function
pytest tests/unit/test_warehouse_endpoints.py::TestGetAllWarehouses::test_get_all_warehouses_success -v

# Run tests with coverage
pytest --cov=app --cov-report=term-missing

# Run tests with HTML coverage report
pytest --cov=app --cov-report=html
# Open htmlcov/index.html in browser

# Run tests matching a pattern
pytest -k "warehouse" -v

# Run with different verbosity
pytest -v        # Verbose
pytest -vv       # Very verbose
pytest -q        # Quiet

# Stop on first failure
pytest -x

# Show local variables in tracebacks
pytest -l

# Run tests in parallel (requires pytest-xdist)
pytest -n auto
```

### Test Coverage

The test suite includes:

#### Warehouse Endpoints (15 tests)
- ✅ GET `/api/v1/warehouses` - All warehouses list
- ✅ GET `/api/v1/warehouses/{warehouse_id}` - Specific warehouse
- ✅ GET `/api/v1/warehouses/{warehouse_id}/dashboard` - Dashboard analytics

**Test scenarios:**
- Successful data retrieval with various data states
- Empty results handling
- NULL value handling (coordinates, optional fields)
- Date validation (format, leap year)
- Database error handling
- HTTP 404, 400, 422, 500 responses

#### Camera Endpoints (18 tests)
- ✅ GET `/api/v1/cameras/stream-url` - HLS streaming URL
- ✅ GET `/api/v1/warehouses/{warehouse_id}/cameras/{cam_id}/chunks` - Video chunks
- ✅ GET `/api/v1/warehouses/{warehouse_id}/cameras/{cam_id}/logs/employees` - Employee logs
- ✅ GET `/api/v1/warehouses/{warehouse_id}/cameras/{cam_id}/logs/gunny-bags` - Bag logs
- ✅ GET `/api/v1/warehouses/{warehouse_id}/cameras/{cam_id}/logs/vehicles` - Vehicle logs
- ✅ GET `/api/v1/warehouses/{warehouse_id}/cameras/{cam_id}/analytics/vehicle-gunny-count` - Analytics

**Test scenarios:**
- AWS Kinesis Video Streams integration (mocked)
- Camera not found, missing stream ARN
- Hourly log grouping
- Action summaries and aggregations
- Date format validation
- AWS ClientError handling

#### Chat Endpoint (12 tests)
- ✅ POST `/api/v1/warehouses/{warehouse_id}/cameras/{cam_id}/chunks/{chunk_id}/chat` - AI chat

**Test scenarios:**
- First message (no conversation history)
- Conversation with history
- Custom inference configuration
- Transaction ID generation
- Chunk not found, no transcript URL
- No transcript files in blob storage
- Transcript merge failures
- Video context build failures
- AWS Bedrock API errors
- Empty Bedrock responses
- Request payload validation

### Test Fixtures

Available in `tests/conftest.py`:

```python
# Application fixtures
test_app          # FastAPI application instance
test_client       # TestClient for making requests

# Database fixtures
mock_db_connection    # Mocked database connection
mock_get_connection   # Patched get_connection function

# Data fixtures
sample_warehouse_data     # Warehouse JSON
sample_employee_data      # Employee JSON
sample_camera_data        # Camera JSON
sample_vehicle_data       # Vehicle JSON
sample_chunk_data         # Video chunk JSON
sample_dashboard_data     # Dashboard analytics
sample_chat_request       # Chat request payload

# Service mocks
mock_aws_bedrock_response   # AWS Bedrock API response
mock_kinesis_hls_response   # Kinesis Video Streams response
sample_transcript_data      # Video transcript data
```

### Writing New Tests

Example unit test:

```python
import pytest

@pytest.mark.unit
def test_my_endpoint(test_client, mock_get_connection, sample_data):
    """Test description"""
    mock_conn, mock_cursor = mock_get_connection
    mock_cursor.fetchall.return_value = sample_data
    
    response = test_client.get("/api/v1/my-endpoint")
    
    assert response.status_code == 200
    assert response.json()["status"] == "success"
```

### CI/CD Integration

```bash
# In GitHub Actions / GitLab CI
- name: Run Tests
  run: |
    source .venv/bin/activate
    pytest --cov=app --cov-report=xml --cov-report=term
    
- name: Upload Coverage
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
```

### Test Markers

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"

# Run tests requiring database
pytest -m requires_db

# Run tests requiring AWS
pytest -m requires_aws
```

### Best Practices

1. **Mock External Dependencies**: Database, AWS, Azure services
2. **Use Fixtures**: Reuse test data and setup code
3. **Test Edge Cases**: NULL values, empty results, errors
4. **Clear Test Names**: Use descriptive function names
5. **Arrange-Act-Assert**: Structure tests clearly
6. **Independent Tests**: Each test should run independently
7. **Coverage Goals**: Aim for >80% code coverage

### Debugging Tests

```bash
# Run with print statements
pytest -s

# Drop into debugger on failure
pytest --pdb

# Show full traceback
pytest --tb=long

# Show only failed tests
pytest --lf

# Verbose output with local variables
pytest -vv -l
```

---

## 🔍 Troubleshooting

### Standard Deployment
```bash
# Check status
./deploy.sh status

# View logs
./deploy.sh logs
tail -n 100 logs/fastapi.log

# Port in use
sudo lsof -i :8081
sudo kill -9 <PID>

# Restart
./deploy.sh restart
```

### Docker Deployment
```bash
# Check container status
./deploy.sh docker-status
docker compose ps

# View logs
./deploy.sh docker-logs
docker compose logs -f

# Restart containers
./deploy.sh docker-restart

# Complete cleanup and restart
./deploy.sh docker-clean
./deploy.sh docker-start

# Check container health
docker inspect warehouse-rest-api | grep -A 10 Health
```

## 📁 Structure

```
warehouse-api-backend/
├── app/
│   ├── main.py              # FastAPI entry
│   ├── core/                # Config & database
│   ├── routers/             # API endpoints
│   ├── models/              # Pydantic models
│   └── services/            # AWS, Azure, transcripts
├── deploy.sh                # Unified deployment
├── Dockerfile               # Docker image
├── docker-compose.yml       # Docker orchestration
└── requirements.txt         # Dependencies
```

## 🚀 Production Setup

### Systemd Service
```ini
[Unit]
Description=Warehouse REST API
After=network.target

[Service]
Type=forking
User=your_user
WorkingDirectory=/path/to/warehouse-api
ExecStart=/path/to/warehouse-api/deploy.sh start
ExecStop=/path/to/warehouse-api/deploy.sh stop
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable warehouse-api
sudo systemctl start warehouse-api
```

### Nginx Reverse Proxy
```nginx
server {
    listen 80;
    server_name api.yourdomain.com;
    location / {
        proxy_pass http://localhost:8081;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

**Built with FastAPI • Docker • AWS • Azure** 🚀
