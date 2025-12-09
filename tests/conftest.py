"""
Test Configuration and Fixtures

This module provides pytest fixtures for testing the Warehouse REST API.
Fixtures include test clients, database mocks, and sample test data.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from app.main import app
from datetime import datetime, date
import psycopg2


@pytest.fixture(scope="session")
def test_app():
    """Fixture providing the FastAPI test application"""
    return app


@pytest.fixture(scope="function")
def test_client(test_app):
    """Fixture providing a test client for making API requests"""
    with TestClient(test_app) as client:
        yield client


@pytest.fixture(scope="function")
def mock_db_connection():
    """Fixture providing a mocked database connection"""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    
    # Configure cursor to be usable in context managers
    mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
    mock_cursor.__exit__ = MagicMock(return_value=False)
    
    return mock_conn, mock_cursor


@pytest.fixture(scope="function")
def mock_get_connection(mock_db_connection):
    """Fixture that patches the database get_connection function"""
    mock_conn, mock_cursor = mock_db_connection
    
    # Patch at all router levels where get_connection is imported
    with patch('app.core.database.get_connection', return_value=mock_conn), \
         patch('app.routers.warehouse.get_connection', return_value=mock_conn), \
         patch('app.routers.camera.get_connection', return_value=mock_conn), \
         patch('app.routers.chat.get_connection', return_value=mock_conn):
        yield mock_conn, mock_cursor


# Sample Test Data Fixtures

@pytest.fixture
def sample_warehouse_data():
    """Sample warehouse data for testing"""
    return {
        "warehouse_id": "WH001",
        "warehouse_name": "Central Warehouse",
        "warehouse_capacity": 10000,
        "warehouse_longitude": 77.5946,
        "warehouse_latitude": 12.9716,
        "warehouse_location": "Bangalore, Karnataka"
    }


@pytest.fixture
def sample_warehouse_row():
    """Sample warehouse database row"""
    return (
        "WH001",
        "Central Warehouse",
        10000,
        77.5946,
        12.9716,
        "Bangalore, Karnataka"
    )


@pytest.fixture
def sample_employee_data():
    """Sample employee data for testing"""
    return [
        {
            "emp_id": "EMP001",
            "warehouse_id": "WH001",
            "emp_name": "John Doe",
            "emp_number": "9876543210",
            "role_id": "ROLE_SUP",
            "emp_facecrop": "https://example.com/face1.jpg",
            "role_name": "Supervisor"
        },
        {
            "emp_id": "EMP002",
            "warehouse_id": "WH001",
            "emp_name": "Jane Smith",
            "emp_number": "9876543211",
            "role_id": "ROLE_INC",
            "emp_facecrop": "https://example.com/face2.jpg",
            "role_name": "Incharge"
        }
    ]


@pytest.fixture
def sample_employee_rows():
    """Sample employee database rows"""
    return [
        ("EMP001", "WH001", "John Doe", "9876543210", "ROLE_SUP", "https://example.com/face1.jpg", "Supervisor"),
        ("EMP002", "WH001", "Jane Smith", "9876543211", "ROLE_INC", "https://example.com/face2.jpg", "Incharge")
    ]


@pytest.fixture
def sample_camera_data():
    """Sample camera data for testing"""
    return [
        {
            "cam_id": "CAM001",
            "cam_direction": "ENTRY",
            "camera_status": "active",
            "warehouse_id": "WH001",
            "stream_arn": "arn:aws:kinesisvideo:us-east-1:123456789:stream/test-stream",
            "hls_url": "https://example.com/hls/stream.m3u8",
            "camera_longitude": 77.5946,
            "camera_latitude": 12.9716,
            "services": "vehicle_detection,face_recognition"
        }
    ]


@pytest.fixture
def sample_camera_rows():
    """Sample camera database rows"""
    return [
        ("CAM006", "ENTRY", "active", "WH001", "arn:aws:kinesisvideo:us-east-1:054037105643:stream/WH001_CAM006_Right/1762414730007",
         "https://example.com/hls/stream.m3u8", 77.5946, 12.9716, "vehicle_detection,face_recognition")
    ]


@pytest.fixture
def sample_vehicle_data():
    """Sample vehicle data for testing"""
    return [
        {
            "id": 1,
            "warehouse_id": "WH001",
            "number_plate": "KA01AB1234",
            "bags_capacity": 500,
            "vehicle_access": "authorized",
            "driver_id": "DRV001",
            "created_at": "2025-11-19 10:00:00",
            "driver_name": "Driver One",
            "driver_phone": "9876543210",
            "driver_crop": "https://example.com/driver1.jpg"
        }
    ]


@pytest.fixture
def sample_vehicle_rows():
    """Sample vehicle database rows"""
    return [
        (1, "WH001", "KA01AB1234", 500, "authorized", "DRV001",
         datetime(2025, 11, 19, 10, 0, 0), "Driver One", "9876543210", "https://example.com/driver1.jpg")
    ]


@pytest.fixture
def sample_dashboard_data():
    """Sample dashboard analytics data"""
    return {
        "bags": (150, 120),  # loaded, unloaded
        "vehicles": (25, 5),  # authorized, unauthorized
        "employees": (100, 45, 3)  # total_logs, unique_authorised, unauthorised
    }


@pytest.fixture
def sample_chunk_data():
    """Sample video chunk data"""
    return [
        {
            "chunk_id": "chunk_2025-11-19_10-00-00",
            "warehouse_id": "WH001",
            "cam_id": "CAM001",
            "chunk_blob_url": "https://example.com/chunks/chunk1.mp4",
            "transcripts_url": "https://example.com/transcripts/chunk1.json",
            "date": "2025-11-19",
            "time": "2025-11-19 10:00:00"
        }
    ]


@pytest.fixture
def sample_chunk_rows():
    """Sample chunk database rows"""
    return [
        ("chunk_2025-11-19_10-00-00", "WH001", "CAM001",
         "https://example.com/chunks/chunk1.mp4",
         "https://example.com/transcripts/chunk1.json",
         date(2025, 11, 19),
         datetime(2025, 11, 19, 10, 0, 0))
    ]


@pytest.fixture
def sample_employee_log_rows():
    """Sample employee log database rows"""
    return [
        (1, "WH001", "EMP001", "John Doe", "9876543210", "Supervisor",
         date(2025, 11, 19), datetime(2025, 11, 19, 10, 30, 0),
         "CAM001", "https://example.com/crops/emp1.jpg", "chunk_2025-11-19_10-00-00", "authorized"),
        (2, "WH001", "EMP002", "Jane Smith", "9876543211", "Incharge",
         date(2025, 11, 19), datetime(2025, 11, 19, 10, 35, 0),
         "CAM001", "https://example.com/crops/emp2.jpg", "chunk_2025-11-19_10-00-00", "authorized")
    ]


@pytest.fixture
def sample_gunny_log_rows():
    """Sample gunny bag log database rows"""
    return [
        (1, "WH001", "CAM001", 50, date(2025, 11, 19),
         "chunk_2025-11-19_10-00-00", datetime(2025, 11, 19, 10, 15, 0), "loading"),
        (2, "WH001", "CAM001", 30, date(2025, 11, 19),
         "chunk_2025-11-19_10-00-00", datetime(2025, 11, 19, 10, 45, 0), "unloading")
    ]


@pytest.fixture
def sample_vehicle_log_rows():
    """Sample vehicle log database rows"""
    return [
        (1, "WH001", "CAM001", date(2025, 11, 19),
         "chunk_2025-11-19_10-00-00", "KA01AB1234", "authorized",
         datetime(2025, 11, 19, 10, 20, 0)),
        (2, "WH001", "CAM001", date(2025, 11, 19),
         "chunk_2025-11-19_10-00-00", "KA02CD5678", "unauthorized",
         datetime(2025, 11, 19, 11, 10, 0))
    ]


@pytest.fixture
def mock_aws_bedrock_response():
    """Mock AWS Bedrock response for chat testing"""
    return {
        "output": {
            "message": {
                "content": [
                    {
                        "text": "Based on the video transcript, I can see that there were 3 vehicles detected during this time period. The activity shows normal warehouse operations with authorized vehicle entry and bag loading operations."
                    }
                ]
            }
        },
        "stopReason": "end_turn",
        "usage": {
            "inputTokens": 150,
            "outputTokens": 50,
            "totalTokens": 200
        }
    }


@pytest.fixture
def mock_kinesis_hls_response():
    """Mock AWS Kinesis Video Streams HLS response"""
    return {
        "stream_name": "test-stream",
        "stream_arn": "arn:aws:kinesisvideo:us-east-1:123456789:stream/test-stream",
        "hls_url": "https://example-kvs.kinesisvideo.us-east-1.amazonaws.com/hls/v1/test-stream.m3u8",
        "data_endpoint": "https://example-kvs.kinesisvideo.us-east-1.amazonaws.com",
        "expires": 43200
    }


@pytest.fixture
def sample_chat_request():
    """Sample chat request payload"""
    return {
        "UserQuery": "How many vehicles entered the warehouse?",
        "modelId": "anthropic.claude-3-5-haiku-20241022-v1:0",
        "inferenceConfig": {
            "maxTokens": 2048,
            "temperature": 0.7,
            "topP": 0.9
        },
        "conversation": [],
        "chatTransactionId": None
    }


@pytest.fixture
def sample_transcript_data():
    """Sample video transcript data"""
    return [
        {
            "timestamp": "00:00:05",
            "detections": [
                {"type": "vehicle", "confidence": 0.95, "label": "truck"},
                {"type": "person", "confidence": 0.89, "label": "worker"}
            ]
        },
        {
            "timestamp": "00:00:15",
            "detections": [
                {"type": "bags", "confidence": 0.92, "count": 25}
            ]
        }
    ]


# Pytest configuration

def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "requires_db: mark test as requiring database connection")
    config.addinivalue_line("markers", "requires_aws: mark test as requiring AWS services")
