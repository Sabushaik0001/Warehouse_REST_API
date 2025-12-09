"""
Unit Tests for Warehouse Endpoints

Tests for:
- GET /api/v1/warehouses - Get all warehouses
- GET /api/v1/warehouses/{warehouse_id} - Get specific warehouse
- GET /api/v1/warehouses/{warehouse_id}/dashboard - Get dashboard analytics
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException


@pytest.mark.unit
class TestGetAllWarehouses:
    """Test suite for GET /api/v1/warehouses endpoint"""
    
    def test_get_all_warehouses_success(
        self, 
        test_client, 
        mock_get_connection,
        sample_warehouse_row,
        sample_employee_rows
    ):
        """Test successful retrieval of all warehouses with employees"""
        mock_conn, mock_cursor = mock_get_connection
        
        # Mock database responses
        mock_cursor.fetchall.side_effect = [
            [sample_warehouse_row],  # warehouse query
            sample_employee_rows     # employee query
        ]
        
        response = test_client.get("/api/v1/warehouses")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert data["total_warehouses"] == 1
        assert len(data["warehouses"]) == 1
        
        warehouse = data["warehouses"][0]
        assert warehouse["warehouse_id"] == "WH001"
        assert warehouse["warehouse_name"] == "Central Warehouse"
        assert warehouse["warehouse_capacity"] == 10000
        assert warehouse["total_employees"] == 2
        assert len(warehouse["employees"]) == 2
        
        # Verify employees are sorted by role
        assert warehouse["employees"][0]["role_id"] == "ROLE_SUP"
        assert warehouse["employees"][1]["role_id"] == "ROLE_INC"
    
    def test_get_all_warehouses_empty(self, test_client, mock_get_connection):
        """Test response when no warehouses exist"""
        mock_conn, mock_cursor = mock_get_connection
        mock_cursor.fetchall.return_value = []
        
        response = test_client.get("/api/v1/warehouses")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert data["total_warehouses"] == 0
        assert data["warehouses"] == []
    
    def test_get_all_warehouses_no_employees(
        self,
        test_client,
        mock_get_connection,
        sample_warehouse_row
    ):
        """Test warehouse with no employees"""
        mock_conn, mock_cursor = mock_get_connection
        
        mock_cursor.fetchall.side_effect = [
            [sample_warehouse_row],  # warehouse query
            []                       # no employees
        ]
        
        response = test_client.get("/api/v1/warehouses")
        
        assert response.status_code == 200
        data = response.json()
        
        warehouse = data["warehouses"][0]
        assert warehouse["total_employees"] == 0
        assert warehouse["employees"] == []
    
    def test_get_all_warehouses_database_error(self, test_client, mock_get_connection):
        """Test handling of database errors"""
        mock_conn, mock_cursor = mock_get_connection
        mock_cursor.execute.side_effect = Exception("Database connection error")
        
        response = test_client.get("/api/v1/warehouses")
        
        assert response.status_code == 500
        assert "Database error" in response.json()["detail"]


@pytest.mark.unit
class TestGetWarehouseById:
    """Test suite for GET /api/v1/warehouses/{warehouse_id} endpoint"""
    
    def test_get_warehouse_by_id_success(
        self,
        test_client,
        mock_get_connection,
        sample_warehouse_row,
        sample_camera_rows,
        sample_vehicle_rows,
        sample_employee_rows
    ):
        """Test successful retrieval of specific warehouse with all related data"""
        mock_conn, mock_cursor = mock_get_connection
        
        # Mock database responses in order
        mock_cursor.fetchone.return_value = sample_warehouse_row
        mock_cursor.fetchall.side_effect = [
            sample_camera_rows,   # cameras
            sample_vehicle_rows,  # vehicles
            sample_employee_rows  # employees
        ]
        
        response = test_client.get("/api/v1/warehouses/WH001")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert data["warehouse"]["warehouse_id"] == "WH001"
        
        # Verify cameras
        assert data["cameras"]["total_cameras"] == 1
        assert data["cameras"]["data"][0]["cam_id"] == "CAM001"
        
        # Verify vehicles
        assert data["vehicles"]["total_vehicles"] == 1
        assert data["vehicles"]["data"][0]["number_plate"] == "KA01AB1234"
        
        # Verify employees
        assert data["employees"]["total_employees"] == 2
    
    def test_get_warehouse_by_id_not_found(self, test_client, mock_get_connection):
        """Test response when warehouse doesn't exist"""
        mock_conn, mock_cursor = mock_get_connection
        mock_cursor.fetchone.return_value = None
        
        response = test_client.get("/api/v1/warehouses/INVALID_ID")
        
        assert response.status_code == 404
        assert "Warehouse not found" in response.json()["detail"]
    
    def test_get_warehouse_by_id_with_null_coordinates(
        self,
        test_client,
        mock_get_connection
    ):
        """Test warehouse with NULL longitude/latitude"""
        mock_conn, mock_cursor = mock_get_connection
        
        warehouse_row_with_nulls = (
            "WH001", "Central Warehouse", 10000,
            None, None,  # NULL coordinates
            "Bangalore, Karnataka"
        )
        
        mock_cursor.fetchone.return_value = warehouse_row_with_nulls
        mock_cursor.fetchall.side_effect = [[], [], []]  # No cameras, vehicles, employees
        
        response = test_client.get("/api/v1/warehouses/WH001")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["warehouse"]["warehouse_longitude"] is None
        assert data["warehouse"]["warehouse_latitude"] is None
    
    def test_get_warehouse_by_id_database_error(self, test_client, mock_get_connection):
        """Test handling of database errors"""
        mock_conn, mock_cursor = mock_get_connection
        mock_cursor.execute.side_effect = Exception("Database connection error")
        
        response = test_client.get("/api/v1/warehouses/WH001")
        
        assert response.status_code == 500
        assert "Database error" in response.json()["detail"]


@pytest.mark.unit
class TestGetWarehouseDashboard:
    """Test suite for GET /api/v1/warehouses/{warehouse_id}/dashboard endpoint"""
    
    def test_get_dashboard_success(
        self,
        test_client,
        mock_get_connection,
        sample_dashboard_data
    ):
        """Test successful dashboard data retrieval"""
        mock_conn, mock_cursor = mock_get_connection
        
        # Mock database responses
        mock_cursor.fetchone.side_effect = [
            sample_dashboard_data["bags"],       # bags query
            sample_dashboard_data["vehicles"],   # vehicles query
            sample_dashboard_data["employees"]   # employees query
        ]
        
        response = test_client.get(
            "/api/v1/warehouses/WH001/dashboard",
            params={"date": "2025-11-19"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert data["warehouse_id"] == "WH001"
        assert data["date"] == "2025-11-19"
        assert data["total_loaded_bags"] == 150
        assert data["total_unloaded_bags"] == 120
        assert data["total_authorised_vehicles"] == 25
        assert data["total_unauthorised_vehicles"] == 5
        assert data["total_employee_logs"] == 100
        assert data["total_unique_authorised_employees"] == 45
        assert data["total_unauthorised_entries"] == 3
    
    def test_get_dashboard_invalid_date_format(self, test_client):
        """Test validation of date format"""
        response = test_client.get(
            "/api/v1/warehouses/WH001/dashboard",
            params={"date": "19-11-2025"}  # Invalid format
        )
        
        assert response.status_code == 400
        assert "Invalid date format" in response.json()["detail"]
    
    def test_get_dashboard_missing_date_parameter(self, test_client):
        """Test missing required date parameter"""
        response = test_client.get("/api/v1/warehouses/WH001/dashboard")
        
        assert response.status_code == 422  # Unprocessable Entity
    
    def test_get_dashboard_with_null_values(
        self,
        test_client,
        mock_get_connection
    ):
        """Test dashboard with NULL database values"""
        mock_conn, mock_cursor = mock_get_connection
        
        # Mock NULL responses
        mock_cursor.fetchone.side_effect = [
            (None, None),      # bags
            (None, None),      # vehicles
            (None, None, None) # employees
        ]
        
        response = test_client.get(
            "/api/v1/warehouses/WH001/dashboard",
            params={"date": "2025-11-19"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should default to 0
        assert data["total_loaded_bags"] == 0
        assert data["total_unloaded_bags"] == 0
        assert data["total_authorised_vehicles"] == 0
        assert data["total_unauthorised_vehicles"] == 0
        assert data["total_employee_logs"] == 0
        assert data["total_unique_authorised_employees"] == 0
        assert data["total_unauthorised_entries"] == 0
    
    def test_get_dashboard_no_data_for_date(
        self,
        test_client,
        mock_get_connection
    ):
        """Test dashboard when no data exists for the date"""
        mock_conn, mock_cursor = mock_get_connection
        
        mock_cursor.fetchone.side_effect = [
            (0, 0),      # no bags
            (0, 0),      # no vehicles
            (0, 0, 0)    # no employees
        ]
        
        response = test_client.get(
            "/api/v1/warehouses/WH001/dashboard",
            params={"date": "2025-11-19"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_loaded_bags"] == 0
        assert data["total_unloaded_bags"] == 0
    
    def test_get_dashboard_database_error(self, test_client, mock_get_connection):
        """Test handling of database errors"""
        mock_conn, mock_cursor = mock_get_connection
        mock_cursor.execute.side_effect = Exception("Database connection error")
        
        response = test_client.get(
            "/api/v1/warehouses/WH001/dashboard",
            params={"date": "2025-11-19"}
        )
        
        assert response.status_code == 500
        assert "Database error" in response.json()["detail"]
    
    def test_get_dashboard_leap_year_date(
        self,
        test_client,
        mock_get_connection,
        sample_dashboard_data
    ):
        """Test dashboard with leap year date"""
        mock_conn, mock_cursor = mock_get_connection
        
        mock_cursor.fetchone.side_effect = [
            sample_dashboard_data["bags"],
            sample_dashboard_data["vehicles"],
            sample_dashboard_data["employees"]
        ]
        
        response = test_client.get(
            "/api/v1/warehouses/WH001/dashboard",
            params={"date": "2024-02-29"}  # Leap year
        )
        
        assert response.status_code == 200
        assert response.json()["date"] == "2024-02-29"
    
    def test_get_dashboard_invalid_leap_year_date(self, test_client):
        """Test dashboard with invalid leap year date"""
        response = test_client.get(
            "/api/v1/warehouses/WH001/dashboard",
            params={"date": "2025-02-29"}  # Not a leap year
        )
        
        assert response.status_code == 400
        assert "Invalid date format" in response.json()["detail"]
