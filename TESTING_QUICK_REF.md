# Unit Testing Quick Reference
**Date:** November 19, 2025

## 🚀 Quick Start

```bash
# Install dependencies
source .venv/bin/activate
pip install -r requirements.txt

# Run all tests
./deploy.sh test pytest

# Run with coverage
./deploy.sh test coverage
```

---

## 📂 Test Location

```
tests/
├── conftest.py                       # Fixtures & configuration
└── unit/
    ├── test_warehouse_endpoints.py   # 15 tests
    ├── test_camera_endpoints.py      # 18 tests
    └── test_chat_endpoint.py         # 12 tests
```

**Total: 46 tests | 37 passing (80.4%)**

---

## 🎯 Test Commands

### Using deploy.sh
```bash
./deploy.sh test              # Quick smoke tests (curl)
./deploy.sh test pytest       # Full pytest suite
./deploy.sh test unit         # Unit tests only
./deploy.sh test integration  # Integration tests only
./deploy.sh test coverage     # With coverage report
```

### Direct pytest
```bash
# All tests
pytest

# Verbose
pytest -v

# Specific file
pytest tests/unit/test_warehouse_endpoints.py

# Specific test
pytest tests/unit/test_warehouse_endpoints.py::TestGetAllWarehouses::test_get_all_warehouses_success

# With coverage
pytest --cov=app --cov-report=term-missing

# HTML coverage
pytest --cov=app --cov-report=html
# Open: htmlcov/index.html

# Pattern matching
pytest -k "warehouse"

# Stop on first failure
pytest -x

# Show print statements
pytest -s

# Debugging
pytest --pdb
```

---

## 📊 Test Coverage

### Warehouse Endpoints (15 tests)
- `GET /api/v1/warehouses` - 4 tests
- `GET /api/v1/warehouses/{warehouse_id}` - 4 tests
- `GET /api/v1/warehouses/{warehouse_id}/dashboard` - 7 tests

### Camera Endpoints (18 tests)
- `GET /api/v1/cameras/stream-url` - 5 tests
- `GET /api/v1/warehouses/.../chunks` - 3 tests
- `GET /api/v1/warehouses/.../logs/employees` - 3 tests
- `GET /api/v1/warehouses/.../logs/gunny-bags` - 2 tests
- `GET /api/v1/warehouses/.../logs/vehicles` - 2 tests
- `GET /api/v1/warehouses/.../analytics/...` - 3 tests

### Chat Endpoint (12 tests)
- `POST /api/v1/warehouses/.../chat` - 12 tests

---

## 🔧 Test Fixtures (conftest.py)

### Application
- `test_app` - FastAPI app
- `test_client` - TestClient

### Database
- `mock_db_connection` - Mocked connection
- `mock_get_connection` - Patched function

### Sample Data
- `sample_warehouse_data` / `sample_warehouse_row`
- `sample_employee_data` / `sample_employee_rows`
- `sample_camera_data` / `sample_camera_rows`
- `sample_vehicle_data` / `sample_vehicle_rows`
- `sample_dashboard_data`
- `sample_chunk_data`

### Service Mocks
- `mock_aws_bedrock_response`
- `mock_kinesis_hls_response`
- `sample_chat_request`

---

## ✍️ Writing Tests

```python
import pytest

@pytest.mark.unit
class TestMyEndpoint:
    def test_success(self, test_client, mock_get_connection, sample_data):
        """Test successful operation"""
        # Arrange
        mock_conn, mock_cursor = mock_get_connection
        mock_cursor.fetchall.return_value = sample_data
        
        # Act
        response = test_client.get("/api/v1/endpoint")
        
        # Assert
        assert response.status_code == 200
        assert response.json()["status"] == "success"
```

---

## 🏷️ Test Markers

```bash
pytest -m unit             # Unit tests only
pytest -m integration      # Integration tests only
pytest -m "not slow"       # Skip slow tests
pytest -m requires_db      # Tests needing database
pytest -m requires_aws     # Tests needing AWS
```

---

## 📈 Coverage Goals

- **Target:** >80% code coverage
- **Focus:** Critical paths first
- **Includes:** All endpoints, error handling, edge cases

---

## 🐛 Debugging

```bash
# Show traceback
pytest --tb=short

# Very verbose
pytest -vv

# Show local variables
pytest -l

# Drop to debugger on failure
pytest --pdb

# Run last failed
pytest --lf

# Test duration
pytest --durations=10
```

---

## 📄 Documentation

- **TESTING_GUIDE.md** - Complete testing guide
- **README.md** - Testing section with examples
- **pytest.ini** - Pytest configuration

---

## ✅ Test Scenarios Covered

- ✅ Successful responses (HTTP 200)
- ✅ Not found errors (HTTP 404)
- ✅ Bad requests (HTTP 400)
- ✅ Validation errors (HTTP 422)
- ✅ Server errors (HTTP 500)
- ✅ NULL value handling
- ✅ Empty result sets
- ✅ Date format validation
- ✅ Database errors
- ✅ AWS/Azure service errors

---

## 🔗 Useful Links

- Pytest Docs: https://docs.pytest.org/
- FastAPI Testing: https://fastapi.tiangolo.com/tutorial/testing/
- Coverage.py: https://coverage.readthedocs.io/

---

**Need help?** Check `TESTING_GUIDE.md` for detailed documentation.
