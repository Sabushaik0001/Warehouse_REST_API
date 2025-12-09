"""
Warehouse router - Endpoints for warehouse data and analytics
"""

from fastapi import APIRouter, HTTPException, Path, Query
from app.core.database import get_connection
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/warehouses", tags=["warehouses"])


@router.get("")
def get_all_warehouses():
    """Get all warehouses with their employees"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        warehouse_query = """
            SELECT 
                warehouse_id, 
                warehouse_name, 
                warehouse_capacity,
                warehouse_longitude,
                warehouse_latitude,
                warehouse_location
            FROM public.warehouse
            ORDER BY warehouse_id
        """
        cur.execute(warehouse_query)
        warehouse_rows = cur.fetchall()
        
        if not warehouse_rows:
            cur.close()
            conn.close()
            return {
                "status": "success",
                "total_warehouses": 0,
                "warehouses": []
            }
        
        warehouses_list = []
        
        for warehouse_row in warehouse_rows:
            warehouse_id = warehouse_row[0]
            
            emp_query = """
                SELECT 
                    e.emp_id,
                    e.warehouse_id,
                    e.emp_name,
                    e.emp_number,
                    e.role_id,
                    e.emp_facecrop,
                    r.role_name
                FROM public.wh_emp_data e
                LEFT JOIN public.wh_emp_role r ON e.role_id = r.role_id
                WHERE e.warehouse_id = %s 
                    AND e.role_id IN ('ROLE_SUP', 'ROLE_INC', 'ROLE_DEO')
                ORDER BY 
                    CASE e.role_id
                        WHEN 'ROLE_SUP' THEN 1
                        WHEN 'ROLE_INC' THEN 2
                        WHEN 'ROLE_DEO' THEN 3
                        ELSE 4
                    END,
                    e.emp_name
            """
            cur.execute(emp_query, (warehouse_id,))
            emp_rows = cur.fetchall()
            
            employees = []
            for emp_row in emp_rows:
                employee = {
                    "emp_id": emp_row[0],
                    "warehouse_id": emp_row[1],
                    "emp_name": emp_row[2],
                    "emp_number": emp_row[3],
                    "role_id": emp_row[4],
                    "emp_facecrop": emp_row[5],
                    "role_name": emp_row[6]
                }
                employees.append(employee)
            
            warehouse_data = {
                "warehouse_id": warehouse_row[0],
                "warehouse_name": warehouse_row[1],
                "warehouse_capacity": warehouse_row[2],
                "warehouse_longitude": float(warehouse_row[3]) if warehouse_row[3] else None,
                "warehouse_latitude": float(warehouse_row[4]) if warehouse_row[4] else None,
                "warehouse_location": warehouse_row[5],
                "employees": employees,
                "total_employees": len(employees)
            }
            
            warehouses_list.append(warehouse_data)
        
        cur.close()
        conn.close()
        
        return {
            "status": "success",
            "total_warehouses": len(warehouses_list),
            "warehouses": warehouses_list
        }
        
    except Exception as e:
        logger.error(f"Error fetching all warehouses: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/{warehouse_id}")
def get_warehouse_by_id(
    warehouse_id: str = Path(..., description="Warehouse ID (e.g., WH001)")
):
    """Get specific warehouse details with cameras, vehicles, and employees"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        warehouse_query = """
            SELECT 
                warehouse_id, 
                warehouse_name, 
                warehouse_capacity,
                warehouse_longitude,
                warehouse_latitude,
                warehouse_location
            FROM public.warehouse
            WHERE warehouse_id = %s
        """
        cur.execute(warehouse_query, (warehouse_id,))
        warehouse_row = cur.fetchone()
        
        if not warehouse_row:
            cur.close()
            conn.close()
            raise HTTPException(
                status_code=404, 
                detail=f"Warehouse not found: {warehouse_id}"
            )
        
        camera_query = """
            SELECT 
                cam_id,
                cam_direction,
                camera_status,
                warehouse_id,
                stream_arn,
                hls_url,
                camera_longitude,
                camera_latitude,
                services
            FROM public.cameras
            WHERE warehouse_id = %s
            ORDER BY cam_id
        """
        cur.execute(camera_query, (warehouse_id,))
        camera_rows = cur.fetchall()
        
        cameras = []
        for cam_row in camera_rows:
            camera = {
                "cam_id": cam_row[0],
                "cam_direction": cam_row[1],
                "camera_status": cam_row[2],
                "warehouse_id": cam_row[3],
                "stream_arn": cam_row[4],
                "hls_url": cam_row[5],
                "camera_longitude": float(cam_row[6]) if cam_row[6] else None,
                "camera_latitude": float(cam_row[7]) if cam_row[7] else None,
                "services": cam_row[8]
            }
            cameras.append(camera)
        
        vehicle_query = """
            SELECT 
                v.id,
                v.warehouse_id,
                v.number_plate,
                v.bags_capacity,
                v.vehicle_access,
                v.driver_id,
                v.created_at,
                d.driver_name,
                d.driver_phone,
                d.driver_crop
            FROM public.wh_vehicles v
            LEFT JOIN public.wh_drivers d ON v.driver_id = d.driver_id
            WHERE v.warehouse_id = %s
            ORDER BY v.id
        """
        cur.execute(vehicle_query, (warehouse_id,))
        vehicle_rows = cur.fetchall()
        
        vehicles = []
        for veh_row in vehicle_rows:
            vehicle = {
                "id": veh_row[0],
                "warehouse_id": veh_row[1],
                "number_plate": veh_row[2],
                "bags_capacity": veh_row[3],
                "vehicle_access": veh_row[4],
                "driver_id": veh_row[5],
                "created_at": veh_row[6].strftime('%Y-%m-%d %H:%M:%S') if veh_row[6] else None,
                "driver_name": veh_row[7],
                "driver_phone": veh_row[8],
                "driver_crop": veh_row[9]
            }
            vehicles.append(vehicle)
        
        emp_query = """
            SELECT 
                e.emp_id,
                e.warehouse_id,
                e.emp_name,
                e.emp_number,
                e.role_id,
                e.emp_facecrop,
                r.role_name
            FROM public.wh_emp_data e
            LEFT JOIN public.wh_emp_role r ON e.role_id = r.role_id
            WHERE e.warehouse_id = %s
            ORDER BY e.role_id, e.emp_name
        """
        cur.execute(emp_query, (warehouse_id,))
        emp_rows = cur.fetchall()
        
        employees = []
        for emp_row in emp_rows:
            employee = {
                "emp_id": emp_row[0],
                "warehouse_id": emp_row[1],
                "emp_name": emp_row[2],
                "emp_number": emp_row[3],
                "role_id": emp_row[4],
                "emp_facecrop": emp_row[5],
                "role_name": emp_row[6]
            }
            employees.append(employee)
        
        warehouse_data = {
            "warehouse_id": warehouse_row[0],
            "warehouse_name": warehouse_row[1],
            "warehouse_capacity": warehouse_row[2],
            "warehouse_longitude": float(warehouse_row[3]) if warehouse_row[3] else None,
            "warehouse_latitude": float(warehouse_row[4]) if warehouse_row[4] else None,
            "warehouse_location": warehouse_row[5]
        }
        
        cur.close()
        conn.close()
        
        return {
            "status": "success",
            "warehouse": warehouse_data,
            "cameras": {
                "total_cameras": len(cameras),
                "data": cameras
            },
            "vehicles": {
                "total_vehicles": len(vehicles),
                "data": vehicles
            },
            "employees": {
                "total_employees": len(employees),
                "data": employees
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching warehouse by ID: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/{warehouse_id}/dashboard")
def get_warehouse_dashboard(
    warehouse_id: str = Path(..., description="Warehouse ID (e.g., WH001)"),
    date: str = Query(..., description="Date in YYYY-MM-DD format")
):
    """Get dashboard analytics for a specific warehouse and date"""
    try:
        # Validate date format
        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid date format. Use YYYY-MM-DD"
            )

        conn = get_connection()
        cur = conn.cursor()

        # ------------------------------------------
        # 1) FETCH WAREHOUSE DETAILS (NEW)
        # ------------------------------------------
        warehouse_query = """
            SELECT 
                warehouse_id, 
                warehouse_name, 
                warehouse_capacity,
                warehouse_longitude,
                warehouse_latitude,
                warehouse_location
            FROM public.warehouse
            WHERE warehouse_id = %s
        """
        cur.execute(warehouse_query, (warehouse_id,))
        warehouse_row = cur.fetchone()

        if not warehouse_row:
            cur.close()
            conn.close()
            raise HTTPException(
                status_code=404,
                detail=f"Warehouse not found: {warehouse_id}"
            )

        # Extract warehouse_capacity safely
        warehouse_capacity = warehouse_row[2] if warehouse_row[2] is not None else 0

        # ------------------------------------------
        # 2) BAGS
        # ------------------------------------------
        bags_query = """
            SELECT 
                COALESCE(SUM(CASE WHEN LOWER(action) = 'loading' THEN count ELSE 0 END), 0) as loaded_bags,
                COALESCE(SUM(CASE WHEN LOWER(action) = 'unloading' THEN count ELSE 0 END), 0) as unloaded_bags
            FROM public.wh_gunny_logs
            WHERE warehouse_id = %s AND date = %s
        """
        cur.execute(bags_query, (warehouse_id, date))
        bags_result = cur.fetchone()

        # ------------------------------------------
        # 3) VEHICLES
        # ------------------------------------------
        vehicles_query = """
            SELECT 
                COUNT(DISTINCT CASE 
                    WHEN LOWER(vehicle_access) IN ('authorized', 'authorised') 
                    THEN number_plate 
                END) as authorised_vehicles,
                COUNT(DISTINCT CASE 
                    WHEN LOWER(vehicle_access) IN ('unauthorized', 'unauthorised') 
                    THEN number_plate 
                END) as unauthorised_vehicles
            FROM public.wh_vehicle_logs
            WHERE warehouse_id = %s AND date = %s
        """
        cur.execute(vehicles_query, (warehouse_id, date))
        vehicles_result = cur.fetchone()

        # ------------------------------------------
        # 4) EMPLOYEE SUMMARY
        # ------------------------------------------
        emp_summary_query = """
            SELECT
                COUNT(*) AS total_employee_logs,
                COUNT(DISTINCT emp_id) FILTER (WHERE emp_id IS NOT NULL) AS total_unique_authorised_employees,
                COUNT(*) FILTER (WHERE emp_id IS NULL) AS total_unauthorised_entries
            FROM public.wh_emp_logs
            WHERE warehouse_id = %s AND date = %s
        """
        cur.execute(emp_summary_query, (warehouse_id, date))
        emp_summary = cur.fetchone()

        cur.close()
        conn.close()

        # Safe defaults
        total_loaded_bags = bags_result[0] if bags_result else 0
        total_unloaded_bags = bags_result[1] if bags_result else 0
        total_authorised_vehicles = vehicles_result[0] if vehicles_result else 0
        total_unauthorised_vehicles = vehicles_result[1] if vehicles_result else 0

        total_employee_logs = emp_summary[0] if emp_summary else 0
        total_unique_authorised_employees = emp_summary[1] if emp_summary else 0
        total_unauthorised_entries = emp_summary[2] if emp_summary else 0

        # ------------------------------------------
        # FINAL RESPONSE
        # ------------------------------------------
        return {
            "status": "success",
            "warehouse_id": warehouse_id,
            "date": date,
            "warehouse_capacity": warehouse_capacity,   # <---- NEW FIELD ADDED
            "total_loaded_bags": total_loaded_bags,
            "total_unloaded_bags": total_unloaded_bags,
            "total_authorised_vehicles": total_authorised_vehicles,
            "total_unauthorised_vehicles": total_unauthorised_vehicles,
            "total_employee_logs": total_employee_logs,
            "total_unique_authorised_employees": total_unique_authorised_employees,
            "total_unauthorised_entries": total_unauthorised_entries
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching dashboard data: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
 