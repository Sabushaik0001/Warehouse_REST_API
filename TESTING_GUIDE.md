# Warehouse REST API - Unit Testing Guide
**Date:** November 19, 2025

## 📋 Overview

This document provides a comprehensive guide to the unit testing structure implemented for the Warehouse REST API. The test suite covers all API endpoints with mocked dependencies for fast, isolated testing.

---

## 📁 Test Structure

```
Warehouse_REST_API/
├── tests/
│   ├── __init__.py                      # Test suite initialization
│   ├── conftest.py                      # Pytest fixtures & configuration
│   │
│   ├── unit/                            # Unit tests (isolated, mocked)
│   │   ├── __init__.py
│   │   ├── test_warehouse_endpoints.py  # 15 tests
│   │   ├── test_camera_endpoints.py     # 18 tests
│   │   └── test_chat_endpoint.py        # 12 tests
│   │
│   └── integration/                     # Integration tests (future)
│       └── __init__.py
│
├── pytest.ini                           # Pytest configuration
├── requirements.txt                     # Updated with test dependencies
└── README.md                            # Updated with testing section
```

---

## 🎯 Test Coverage

### Total: **45 Unit Tests**

#### 1. Warehouse Endpoints (15 tests)
**File:** `tests/unit/test_warehouse_endpoints.py`

##### `GET /api/v1/warehouses` (5 tests)
- ✅ `test_get_all_warehouses_success` - Successful retrieval with employees
- ✅ `test_get_all_warehouses_empty` - No warehouses exist
- ✅ `test_get_all_warehouses_no_employees` - Warehouse without employees
- ✅ `test_get_all_warehouses_database_error` - Database error handling

##### `GET /api/v1/warehouses/{warehouse_id}` (5 tests)
- ✅ `test_get_warehouse_by_id_success` - Full warehouse data retrieval
- ✅ `test_get_warehouse_by_id_not_found` - HTTP 404 handling
- ✅ `test_get_warehouse_by_id_with_null_coordinates` - NULL value handling
- ✅ `test_get_warehouse_by_id_database_error` - Database error handling

##### `GET /api/v1/warehouses/{warehouse_id}/dashboard` (10 tests)
- ✅ `test_get_dashboard_success` - Complete analytics retrieval
- ✅ `test_get_dashboard_invalid_date_format` - Date validation (HTTP 400)
- ✅ `test_get_dashboard_missing_date_parameter` - Required param (HTTP 422)
- ✅ `test_get_dashboard_with_null_values` - NULL defaults to 0
- ✅ `test_get_dashboard_no_data_for_date` - Empty results
- ✅ `test_get_dashboard_database_error` - Database error handling
- ✅ `test_get_dashboard_leap_year_date` - Valid leap year date
- ✅ `test_get_dashboard_invalid_leap_year_date` - Invalid leap year

#### 2. Camera Endpoints (18 tests)
**File:** `tests/unit/test_camera_endpoints.py`

##### `GET /api/v1/cameras/stream-url` (5 tests)
- ✅ `test_get_stream_url_success` - HLS URL with AWS Kinesis
- ✅ `test_get_stream_url_camera_not_found` - HTTP 404 handling
- ✅ `test_get_stream_url_no_stream_arn` - Missing ARN (HTTP 400)
- ✅ `test_get_stream_url_aws_error` - AWS ClientError handling
- ✅ `test_get_stream_url_missing_parameters` - Query param validation

##### `GET /api/v1/warehouses/{warehouse_id}/cameras/{cam_id}/chunks` (3 tests)
- ✅ `test_get_chunks_success` - Video chunk retrieval
- ✅ `test_get_chunks_no_data` - Empty chunks list
- ✅ `test_get_chunks_invalid_date` - Date format validation

##### `GET /api/v1/warehouses/{warehouse_id}/cameras/{cam_id}/logs/employees` (3 tests)
- ✅ `test_get_employee_logs_success` - Hourly grouped logs
- ✅ `test_get_employee_logs_no_data` - Empty logs
- ✅ `test_get_employee_logs_invalid_date` - Date validation

##### `GET /api/v1/warehouses/{warehouse_id}/cameras/{cam_id}/logs/gunny-bags` (2 tests)
- ✅ `test_get_gunny_logs_success` - Bags with action summary
- ✅ `test_get_gunny_logs_no_data` - Empty logs

##### `GET /api/v1/warehouses/{warehouse_id}/cameras/{cam_id}/logs/vehicles` (2 tests)
- ✅ `test_get_vehicle_logs_success` - Vehicle logs with access summary
- ✅ `test_get_vehicle_logs_no_data` - Empty logs

##### `GET /api/v1/warehouses/{warehouse_id}/cameras/{cam_id}/analytics/vehicle-gunny-count` (3 tests)
- ✅ `test_get_vehicle_gunny_analytics_success` - Vehicle-wise bag counts
- ✅ `test_get_vehicle_gunny_analytics_no_vehicles` - Empty analytics
- ✅ `test_get_vehicle_gunny_analytics_invalid_date` - Date validation

#### 3. Chat Endpoint (12 tests)
**File:** `tests/unit/test_chat_endpoint.py`

##### `POST /api/v1/warehouses/{warehouse_id}/cameras/{cam_id}/chunks/{chunk_id}/chat` (12 tests)
- ✅ `test_chat_success_first_message` - New conversation
- ✅ `test_chat_with_conversation_history` - Existing conversation
- ✅ `test_chat_chunk_not_found` - HTTP 404 handling
- ✅ `test_chat_no_transcript_url` - Missing transcript URL
- ✅ `test_chat_no_transcript_files_found` - Azure Blob empty
- ✅ `test_chat_transcript_merge_failure` - Blob storage error
- ✅ `test_chat_context_build_failure` - Context build error
- ✅ `test_chat_aws_bedrock_error` - AWS Bedrock API error
- ✅ `test_chat_empty_bedrock_response` - Empty AI response
- ✅ `test_chat_invalid_request_payload` - Request validation
- ✅ `test_chat_custom_inference_config` - Custom AI parameters
- ✅ `test_chat_transaction_id_generation` - Auto transaction ID

---

## 🔧 Running Tests

### Using deploy.sh Script

```bash
# Quick API smoke tests (curl-based)
./deploy.sh test

# Full pytest suite
./deploy.sh test pytest

# Unit tests only
./deploy.sh test unit

# Integration tests only
./deploy.sh test integration

# Coverage report
./deploy.sh test coverage
```

### Direct pytest Commands

```bash
# Install dependencies first
source .venv/bin/activate
pip install -r requirements.txt

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/unit/test_warehouse_endpoints.py

# Run specific test class
pytest tests/unit/test_warehouse_endpoints.py::TestGetAllWarehouses

# Run specific test
pytest tests/unit/test_warehouse_endpoints.py::TestGetAllWarehouses::test_get_all_warehouses_success

# Run with coverage
pytest --cov=app --cov-report=term-missing

# Generate HTML coverage report
pytest --cov=app --cov-report=html
# Open htmlcov/index.html

# Run tests matching pattern
pytest -k "warehouse"

# Run only unit tests (by marker)
pytest -m unit

# Stop on first failure
pytest -x

# Show local variables on failure
pytest -l

# Quiet mode
pytest -q
```

---

## 🧪 Test Fixtures

Located in `tests/conftest.py`:

### Application Fixtures
- `test_app` - FastAPI application instance
- `test_client` - TestClient for API requests

### Database Fixtures
- `mock_db_connection` - Mocked psycopg2 connection
- `mock_get_connection` - Patched get_connection function

### Sample Data Fixtures
- `sample_warehouse_data` / `sample_warehouse_row`
- `sample_employee_data` / `sample_employee_rows`
- `sample_camera_data` / `sample_camera_rows`
- `sample_vehicle_data` / `sample_vehicle_rows`
- `sample_chunk_data` / `sample_chunk_rows`
- `sample_dashboard_data`
- `sample_employee_log_rows`
- `sample_gunny_log_rows`
- `sample_vehicle_log_rows`

### Service Mock Fixtures
- `mock_aws_bedrock_response` - AWS Bedrock API mock
- `mock_kinesis_hls_response` - Kinesis Video Streams mock
- `sample_chat_request` - Chat API request payload
- `sample_transcript_data` - Video transcript data

---

## 📊 Coverage Report

Run coverage analysis:

```bash
./deploy.sh test coverage
```

**Expected Coverage:** >80%

Coverage includes:
- All API endpoint handlers
- Request validation
- Database query execution
- Error handling (HTTP 400, 404, 422, 500)
- NULL value handling
- Date format validation
- AWS service integration (mocked)
- Azure Blob Storage (mocked)

---

## 🎯 Test Patterns

### Standard Test Structure

```python
import pytest

@pytest.mark.unit
class TestMyEndpoint:
    """Test suite description"""
    
    def test_success_case(self, test_client, mock_get_connection, sample_data):
        """Test successful operation"""
        # Arrange
        mock_conn, mock_cursor = mock_get_connection
        mock_cursor.fetchall.return_value = sample_data
        
        # Act
        response = test_client.get("/api/v1/endpoint")
        
        # Assert
        assert response.status_code == 200
        assert response.json()["status"] == "success"
    
    def test_error_case(self, test_client, mock_get_connection):
        """Test error handling"""
        mock_conn, mock_cursor = mock_get_connection
        mock_cursor.execute.side_effect = Exception("Error")
        
        response = test_client.get("/api/v1/endpoint")
        
        assert response.status_code == 500
```

### Mocking External Services

```python
from unittest.mock import patch

def test_with_aws_mock(test_client, mock_get_connection):
    """Test with AWS service mocked"""
    with patch('app.services.aws_service.bedrock_client.converse') as mock_bedrock:
        mock_bedrock.return_value = {"output": {"message": "Response"}}
        
        response = test_client.post("/api/v1/chat", json={...})
        
        assert response.status_code == 200
        mock_bedrock.assert_called_once()
```

---

## 📦 Dependencies

Added to `requirements.txt`:

```
# Testing dependencies
pytest==7.4.3               # Test framework
pytest-asyncio==0.21.1      # Async test support
pytest-cov==4.1.0           # Coverage plugin
pytest-mock==3.12.0         # Mocking utilities
httpx==0.25.2               # Async HTTP client
faker==20.1.0               # Test data generation
```

---

## 🔍 Debugging Tests

```bash
# Show print statements
pytest -s

# Drop into debugger on failure
pytest --pdb

# Show full traceback
pytest --tb=long

# Run only failed tests from last run
pytest --lf

# Verbose with local variables
pytest -vv -l

# Show duration of tests
pytest --durations=10
```

---

## ✅ CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          python -m venv .venv
          source .venv/bin/activate
          pip install -r requirements.txt
      
      - name: Run tests with coverage
        run: |
          source .venv/bin/activate
          pytest --cov=app --cov-report=xml --cov-report=term
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

---

## 🎓 Best Practices

1. **Mock External Dependencies**
   - Always mock database connections
   - Mock AWS services (Bedrock, Kinesis)
   - Mock Azure Blob Storage
   - Use fixtures for consistent mocking

2. **Test Edge Cases**
   - NULL values in database
   - Empty result sets
   - Invalid date formats
   - Missing required parameters
   - Database connection errors

3. **Use Descriptive Names**
   - `test_get_all_warehouses_success` ✅
   - `test_warehouse1` ❌

4. **Arrange-Act-Assert Pattern**
   ```python
   # Arrange - Setup test data
   mock_cursor.fetchall.return_value = data
   
   # Act - Execute function
   response = test_client.get("/endpoint")
   
   # Assert - Verify results
   assert response.status_code == 200
   ```

5. **Independent Tests**
   - Each test should run independently
   - No shared state between tests
   - Use fixtures for setup/teardown

6. **Coverage Goals**
   - Aim for >80% code coverage
   - Focus on critical paths first
   - Don't sacrifice quality for coverage

7. **Fast Execution**
   - Unit tests should run in seconds
   - Mock slow operations (DB, API calls)
   - Use pytest markers for test selection

---

## 📝 Adding New Tests

### Step 1: Add test to appropriate file

```python
# tests/unit/test_new_endpoint.py
import pytest

@pytest.mark.unit
class TestNewEndpoint:
    def test_new_feature(self, test_client, mock_get_connection):
        """Test description"""
        # Test implementation
        pass
```

### Step 2: Add fixtures if needed

```python
# tests/conftest.py
@pytest.fixture
def sample_new_data():
    """Sample data for new tests"""
    return {"key": "value"}
```

### Step 3: Run tests

```bash
pytest tests/unit/test_new_endpoint.py -v
```

### Step 4: Check coverage

```bash
pytest --cov=app tests/unit/test_new_endpoint.py --cov-report=term-missing
```

---

## 📚 Resources

- **Pytest Documentation**: https://docs.pytest.org/
- **FastAPI Testing**: https://fastapi.tiangolo.com/tutorial/testing/
- **Mock Library**: https://docs.python.org/3/library/unittest.mock.html
- **Pytest Coverage**: https://pytest-cov.readthedocs.io/

---

## 🤝 Contributing

When adding new features:

1. Write tests first (TDD approach)
2. Ensure all tests pass before committing
3. Maintain >80% coverage
4. Follow existing test patterns
5. Add fixtures for reusable test data
6. Document complex test scenarios

---

**Ready to test!** 🚀

Run `./deploy.sh test pytest` to execute the full test suite.
