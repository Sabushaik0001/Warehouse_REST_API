"""
Unit Tests for Camera Endpoints

Tests for:
- GET /api/v1/cameras/stream-url - Get HLS streaming URL
- GET /api/v1/warehouses/{warehouse_id}/cameras/{cam_id}/chunks - Get video chunks
- GET /api/v1/warehouses/{warehouse_id}/cameras/{cam_id}/logs/employees - Get employee logs
- GET /api/v1/warehouses/{warehouse_id}/cameras/{cam_id}/logs/gunny-bags - Get gunny bag logs
- GET /api/v1/warehouses/{warehouse_id}/cameras/{cam_id}/logs/vehicles - Get vehicle logs
- GET /api/v1/warehouses/{warehouse_id}/cameras/{cam_id}/analytics/vehicle-gunny-count - Get analytics
"""

import pytest
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError


@pytest.mark.unit
class TestGetCameraStreamUrl:
    """Test suite for GET /api/v1/cameras/stream-url endpoint"""
    
    def test_get_stream_url_success(
        self,
        test_client,
        mock_get_connection,
        sample_camera_rows,
        mock_kinesis_hls_response
    ):
        """Test successful HLS URL retrieval"""
        mock_conn, mock_cursor = mock_get_connection
        mock_cursor.fetchone.return_value = sample_camera_rows[0]
        mock_cursor.rowcount = 1
        
        with patch('app.services.aws_service.get_hls_streaming_url', return_value=mock_kinesis_hls_response):
            response = test_client.get(
                "/api/v1/cameras/stream-url",
                params={"warehouse_id": "WH001", "cam_id": "CAM001"}
            )
        print("response:",response.status_code)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["stream_arn"] == sample_camera_rows[0][4]
        assert data["warehouse_id"] == "WH001"
        assert data["cam_id"] == "CAM001"
        assert "hls_streaming_url" in data
        assert "expires_in_seconds" in data
    
    def test_get_stream_url_camera_not_found(self, test_client, mock_get_connection):
        """Test response when camera doesn't exist"""
        mock_conn, mock_cursor = mock_get_connection
        mock_cursor.fetchone.return_value = None
        
        response = test_client.get(
            "/api/v1/cameras/stream-url",
            params={"warehouse_id": "WH999", "cam_id": "CAM999"}
        )
        
        assert response.status_code == 404
        assert "Camera not found" in response.json()["detail"]
    
    def test_get_stream_url_no_stream_arn(
        self,
        test_client,
        mock_get_connection
    ):
        """Test response when stream ARN is not configured"""
        mock_conn, mock_cursor = mock_get_connection
        
        # Camera row with NULL stream ARN
        camera_row = ("CAM001", "ENTRY", "active", "WH001", None, None, 77.5946, 12.9716, "services")
        mock_cursor.fetchone.return_value = camera_row
        
        response = test_client.get(
            "/api/v1/cameras/stream-url",
            params={"warehouse_id": "WH001", "cam_id": "CAM001"}
        )
        
        assert response.status_code == 400
        assert "Stream ARN not configured" in response.json()["detail"]
    
    def test_get_stream_url_aws_error(
        self,
        test_client,
        mock_get_connection,
        sample_camera_rows
    ):
        """Test handling of AWS Kinesis errors"""
        mock_conn, mock_cursor = mock_get_connection
        mock_cursor.fetchone.return_value = sample_camera_rows[0]
        
        # Mock AWS ClientError
        error_response = {
            'Error': {
                'Code': 'ResourceNotFoundException',
                'Message': 'Stream not found'
            }
        }
        
        with patch('app.services.aws_service.get_hls_streaming_url', side_effect=ClientError(error_response, 'GetHLSStreamingSessionURL')):
            response = test_client.get(
                "/api/v1/cameras/stream-url",
                params={"warehouse_id": "WH001", "cam_id": "CAM001"}
            )
        
        assert response.status_code == 400
        assert "AWS Kinesis Error" in response.json()["detail"]
    
    def test_get_stream_url_missing_parameters(self, test_client):
        """Test missing required query parameters"""
        # Missing cam_id
        response = test_client.get(
            "/api/v1/cameras/stream-url",
            params={"warehouse_id": "WH001"}
        )
        assert response.status_code == 422
        
        # Missing warehouse_id
        response = test_client.get(
            "/api/v1/cameras/stream-url",
            params={"cam_id": "CAM001"}
        )
        assert response.status_code == 422



@pytest.mark.unit
class TestGetCameraChunks:
    """Test suite for GET /api/v1/warehouses/{warehouse_id}/cameras/{cam_id}/chunks endpoint"""
    
    def test_get_chunks_success(
        self,
        test_client,
        mock_get_connection,
        sample_chunk_rows
    ):
        """Test successful chunk retrieval"""
        mock_conn, mock_cursor = mock_get_connection
        mock_cursor.fetchall.return_value = sample_chunk_rows
        
        response = test_client.get(
            "/api/v1/warehouses/WH001/cameras/CAM001/chunks",
            params={"date": "2025-11-19"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert data["warehouse_id"] == "WH001"
        assert data["cam_id"] == "CAM001"
        assert data["date"] == "2025-11-19"
        assert data["total_chunks"] == 1
        assert len(data["chunks"]) == 1
        assert data["chunks"][0]["chunk_id"] == "chunk_2025-11-19_10-00-00"
    
    def test_get_chunks_no_data(self, test_client, mock_get_connection):
        """Test response when no chunks exist"""
        mock_conn, mock_cursor = mock_get_connection
        mock_cursor.fetchall.return_value = []
        
        response = test_client.get(
            "/api/v1/warehouses/WH001/cameras/CAM001/chunks",
            params={"date": "2025-11-19"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert data["total_chunks"] == 0
        assert data["chunks"] == []
        assert "No chunks found" in data["message"]
    
    def test_get_chunks_invalid_date(self, test_client):
        """Test invalid date format"""
        response = test_client.get(
            "/api/v1/warehouses/WH001/cameras/CAM001/chunks",
            params={"date": "invalid-date"}
        )
        
        assert response.status_code == 400
        assert "Invalid date format" in response.json()["detail"]


@pytest.mark.unit
class TestGetEmployeeLogs:
    """Test suite for GET /api/v1/warehouses/{warehouse_id}/cameras/{cam_id}/logs/employees endpoint"""
    
    def test_get_employee_logs_success(
        self,
        test_client,
        mock_get_connection,
        sample_employee_log_rows
    ):
        """Test successful employee log retrieval with hourly grouping"""
        mock_conn, mock_cursor = mock_get_connection
        mock_cursor.fetchall.return_value = sample_employee_log_rows
        
        response = test_client.get(
            "/api/v1/warehouses/WH001/cameras/CAM001/logs/employees",
            params={"date": "2025-11-19"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert data["warehouse_id"] == "WH001"
        assert data["cam_id"] == "CAM001"
        assert data["total_logs"] == 2
        assert data["unique_employees"] == 2
        assert len(data["hourly_ranges"]) > 0
        
        # Check hourly range structure
        hourly_range = data["hourly_ranges"][0]
        assert "hour_range" in hourly_range
        assert "total_logs" in hourly_range
        assert "unique_employees" in hourly_range
        assert "logs" in hourly_range
    
    def test_get_employee_logs_no_data(self, test_client, mock_get_connection):
        """Test response when no logs exist"""
        mock_conn, mock_cursor = mock_get_connection
        mock_cursor.fetchall.return_value = []
        
        response = test_client.get(
            "/api/v1/warehouses/WH001/cameras/CAM001/logs/employees",
            params={"date": "2025-11-19"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_logs"] == 0
        assert data["hourly_ranges"] == []
    
    def test_get_employee_logs_invalid_date(self, test_client):
        """Test invalid date format"""
        response = test_client.get(
            "/api/v1/warehouses/WH001/cameras/CAM001/logs/employees",
            params={"date": "2025/11/19"}
        )
        
        assert response.status_code == 400


@pytest.mark.unit
class TestGetGunnyBagLogs:
    """Test suite for GET /api/v1/warehouses/{warehouse_id}/cameras/{cam_id}/logs/gunny-bags endpoint"""
    
    def test_get_gunny_logs_success(
        self,
        test_client,
        mock_get_connection,
        sample_gunny_log_rows
    ):
        """Test successful gunny bag log retrieval"""
        mock_conn, mock_cursor = mock_get_connection
        mock_cursor.fetchall.return_value = sample_gunny_log_rows
        
        response = test_client.get(
            "/api/v1/warehouses/WH001/cameras/CAM001/logs/gunny-bags",
            params={"date": "2025-11-19"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert data["total_logs"] == 2
        assert data["total_bags"] == 80  # 50 + 30
        assert "action_summary" in data
        assert "loading" in data["action_summary"]
        assert "unloading" in data["action_summary"]
        assert data["action_summary"]["loading"]["total_bags"] == 50
        assert data["action_summary"]["unloading"]["total_bags"] == 30
    
    def test_get_gunny_logs_no_data(self, test_client, mock_get_connection):
        """Test response when no logs exist"""
        mock_conn, mock_cursor = mock_get_connection
        mock_cursor.fetchall.return_value = []
        
        response = test_client.get(
            "/api/v1/warehouses/WH001/cameras/CAM001/logs/gunny-bags",
            params={"date": "2025-11-19"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_logs"] == 0
        assert data["total_bags"] == 0


@pytest.mark.unit
class TestGetVehicleLogs:
    """Test suite for GET /api/v1/warehouses/{warehouse_id}/cameras/{cam_id}/logs/vehicles endpoint"""
    
    def test_get_vehicle_logs_success(
        self,
        test_client,
        mock_get_connection,
        sample_vehicle_log_rows
    ):
        """Test successful vehicle log retrieval"""
        mock_conn, mock_cursor = mock_get_connection
        mock_cursor.fetchall.return_value = sample_vehicle_log_rows
        
        response = test_client.get(
            "/api/v1/warehouses/WH001/cameras/CAM001/logs/vehicles",
            params={"date": "2025-11-19"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert data["total_logs"] == 2
        assert data["unique_vehicles"] == 2
        assert "access_summary" in data
        assert data["access_summary"]["authorized"] == 1
        assert data["access_summary"]["unauthorized"] == 1
    
    def test_get_vehicle_logs_no_data(self, test_client, mock_get_connection):
        """Test response when no logs exist"""
        mock_conn, mock_cursor = mock_get_connection
        mock_cursor.fetchall.return_value = []
        
        response = test_client.get(
            "/api/v1/warehouses/WH001/cameras/CAM001/logs/vehicles",
            params={"date": "2025-11-19"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_logs"] == 0
        assert data["unique_vehicles"] == 0


@pytest.mark.unit
class TestGetVehicleGunnyAnalytics:
    """Test suite for vehicle-wise gunny bag count analytics endpoint"""
    
    def test_get_vehicle_gunny_analytics_success(
        self,
        test_client,
        mock_get_connection
    ):
        """Test successful vehicle-wise gunny bag analytics"""
        mock_conn, mock_cursor = mock_get_connection
        
        # Mock vehicle logs query
        vehicle_data = [
            ("KA01AB1234", ["chunk1", "chunk2"]),
            ("KA02CD5678", ["chunk3"])
        ]
        
        # Mock gunny logs query for each vehicle
        gunny_data_vehicle1 = [
            ("loading", 100, 2, "10:00:00", "10:30:00"),
            ("unloading", 50, 1, "11:00:00", "11:00:00")
        ]
        
        gunny_data_vehicle2 = [
            ("loading", 75, 1, "12:00:00", "12:00:00")
        ]
        
        mock_cursor.fetchall.side_effect = [
            vehicle_data,
            gunny_data_vehicle1,
            gunny_data_vehicle2
        ]
        
        response = test_client.get(
            "/api/v1/warehouses/WH001/cameras/CAM001/analytics/vehicle-gunny-count",
            params={"date": "2025-11-19"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert data["total_vehicles"] == 2
        assert data["grand_total_bags"] == 225  # 100 + 50 + 75
        assert len(data["vehicles"]) == 2
        
        # Check first vehicle
        vehicle1 = data["vehicles"][0]
        assert vehicle1["number_plate"] == "KA01AB1234"
        assert vehicle1["total_bags_all_actions"] == 150
        assert len(vehicle1["action_breakdown"]) == 2
    
    def test_get_vehicle_gunny_analytics_no_vehicles(
        self,
        test_client,
        mock_get_connection
    ):
        """Test analytics when no vehicles found"""
        mock_conn, mock_cursor = mock_get_connection
        mock_cursor.fetchall.return_value = []
        
        response = test_client.get(
            "/api/v1/warehouses/WH001/cameras/CAM001/analytics/vehicle-gunny-count",
            params={"date": "2025-11-19"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_vehicles"] == 0
        assert data["grand_total_bags"] == 0
        assert data["vehicles"] == []
    
    def test_get_vehicle_gunny_analytics_invalid_date(self, test_client):
        """Test invalid date format"""
        response = test_client.get(
            "/api/v1/warehouses/WH001/cameras/CAM001/analytics/vehicle-gunny-count",
            params={"date": "11-19-2025"}
        )
        
        assert response.status_code == 400
