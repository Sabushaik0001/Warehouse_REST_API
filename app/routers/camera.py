"""Camera router - Endpoints for camera streams, chunks, and logs
"""

from fastapi import APIRouter, HTTPException, Path, Query
from app.core.database import get_connection
from app.services.aws_service import get_hls_streaming_url
from botocore.exceptions import ClientError
from datetime import datetime
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["cameras"])


@router.get("/cameras/stream-url")
def get_camera_stream_url(
    warehouse_id: str = Query(..., description="Warehouse ID (e.g., WH001)"),
    cam_id: str = Query(..., description="Camera ID")
):
    """Get HLS streaming URL for a specific camera"""
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        camera_query = """
            SELECT 
                cam_id,
                warehouse_id,
                stream_arn,
                hls_url,
                cam_direction,
                camera_status
            FROM public.cameras
            WHERE warehouse_id = %s AND cam_id = %s
        """
        cur.execute(camera_query, (warehouse_id, cam_id))
        camera_row = cur.fetchone()
        
        if not camera_row:
            cur.close()
            conn.close()
            raise HTTPException(
                status_code=404,
                detail=f"Camera not found: cam_id={cam_id}, warehouse_id={warehouse_id}"
            )
        
        stream_arn = camera_row[2]

        print("---------stream_arn",stream_arn)
        
        if not stream_arn:
            cur.close()
            conn.close()
            raise HTTPException(
                status_code=400,
                detail=f"Stream ARN not configured for camera: {cam_id}"
            )
        
        # Get HLS streaming URL using service
        hls_data = get_hls_streaming_url(stream_arn)

        print("---------hls_data",hls_data)

   
        # Check if HLS URL is missing or None
        if ( hls_data["hls_url"] is None
            or hls_data["hls_url"] == ""
        ):
            update_inactive_query = """
                UPDATE public.cameras
                SET camera_status = 'inactive', hls_url = NULL,last_updated_at = DATE_TRUNC('second', NOW())
                WHERE warehouse_id = %s AND cam_id = %s
            """
            cur.execute(update_inactive_query, (warehouse_id, cam_id))
            conn.commit()
            cur.close()
            conn.close()

            raise HTTPException(
                status_code=400,
                detail=f"No HLS URL found for camera {cam_id}. Marked camera_status = 'inactive'."
            )

        # If no HLS data found → Mark camera inactive
        if not hls_data or not hls_data.get("hls_url"):
            update_inactive_query = """
                UPDATE public.cameras
                SET camera_status = 'inactive', hls_url = NULL,last_updated_at = DATE_TRUNC('second', NOW())
                WHERE warehouse_id = %s AND cam_id = %s
            """
            cur.execute(update_inactive_query, (warehouse_id, cam_id))
            conn.commit()
            cur.close()
            conn.close()
            
            raise HTTPException(
                status_code=400,
                detail=f"No HLS URL found for camera {cam_id}. Marked camera_status = 'inactive'."
            )

        
        # Update database with new HLS URL
        update_query = """
            UPDATE public.cameras
            SET camera_status = 'active', hls_url = %s,last_updated_at = DATE_TRUNC('second', NOW())
            WHERE warehouse_id = %s AND cam_id = %s
        """
        cur.execute(update_query, (hls_data["hls_url"], warehouse_id, cam_id))
        conn.commit()
        
        rows_updated = cur.rowcount
        cur.close()
        conn.close()
        
        update_status = "Camera status updated to 'active' and HLS URL saved" if rows_updated > 0 else "Camera update failed"
        
        return {
            "status": "success",
            "stream_arn": stream_arn,
            "stream_name": hls_data["stream_name"],
            "warehouse_id": warehouse_id,
            "cam_id": cam_id,
            "hls_streaming_url": hls_data["hls_url"],
            "expires_in_seconds": hls_data["expires"],
            "data_endpoint": hls_data["data_endpoint"],
            "database_update": update_status
        }
        
    except HTTPException:
        raise
    except ClientError as e:
        if conn:
            conn.close()
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logger.error(f"AWS Error: {error_code} - {error_message}")
        raise HTTPException(
            status_code=400,
            detail=f"AWS Kinesis Error: {error_code} - {error_message}"
        )
    except Exception as e:
        if conn:
            conn.close()
        logger.error(f"Error getting HLS URL: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/warehouses/{warehouse_id}/cameras/{cam_id}/chunks")
def get_camera_chunks(
    warehouse_id: str = Path(..., description="Warehouse ID (e.g., WH001)"),
    cam_id: str = Path(..., description="Camera ID"),
    date: str = Query(..., description="Date in YYYY-MM-DD format")
):
    """Get video chunks for a specific camera and date"""
    try:
        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid date format. Use YYYY-MM-DD"
            )
        
        conn = get_connection()
        cur = conn.cursor()
        
        chunks_query = """
            SELECT 
                chunk_id,
                warehouse_id,
                cam_id,
                chunk_blob_url,
                transcripts_url,
                date,
                time
            FROM public.wh_chunks
            WHERE warehouse_id = %s AND cam_id = %s AND date = %s
            ORDER BY time
        """
        cur.execute(chunks_query, (warehouse_id, cam_id, date))
        chunk_rows = cur.fetchall()
        
        if not chunk_rows:
            cur.close()
            conn.close()
            return {
                "status": "success",
                "message": "No chunks found for the given criteria",
                "warehouse_id": warehouse_id,
                "cam_id": cam_id,
                "date": date,
                "total_chunks": 0,
                "chunks": []
            }
        
        chunks = []
        for chunk_row in chunk_rows:
            chunk = {
                "chunk_id": chunk_row[0],
                "warehouse_id": chunk_row[1],
                "cam_id": chunk_row[2],
                "chunk_blob_url": chunk_row[3],
                "transcripts_url": chunk_row[4],
                "date": chunk_row[5].strftime('%Y-%m-%d') if chunk_row[5] else None,
                "time": chunk_row[6].strftime('%Y-%m-%d %H:%M:%S') if chunk_row[6] else None
            }
            chunks.append(chunk)
        
        cur.close()
        conn.close()
        
        return {
            "status": "success",
            "warehouse_id": warehouse_id,
            "cam_id": cam_id,
            "date": date,
            "total_chunks": len(chunks),
            "chunks": chunks
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching chunks: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/chunks/{chunk_id}")
def get_chunk_by_id(
    chunk_id: str = Path(..., description="Chunk ID")
):
    """Get chunk blob URL and metadata by chunk_id"""
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        chunk_query = """
            SELECT
                chunk_id,
                warehouse_id,
                cam_id,
                chunk_blob_url,
                transcripts_url,
                date,
                time
            FROM public.wh_chunks
            WHERE chunk_id = %s
            LIMIT 1
        """
        cur.execute(chunk_query, (chunk_id,))
        row = cur.fetchone()

        if not row:
            cur.close()
            conn.close()
            raise HTTPException(
                status_code=404,
                detail=f"Chunk not found: chunk_id={chunk_id}"
            )

        chunk = {
            "chunk_id": row[0],
            "warehouse_id": row[1],
            "cam_id": row[2],
            "chunk_blob_url": row[3],
            "transcripts_url": row[4],
            "date": row[5].strftime('%Y-%m-%d') if row[5] else None,
            "time": row[6].strftime('%Y-%m-%d %H:%M:%S') if row[6] else None
        }

        cur.close()
        conn.close()

        return {
            "status": "success",
            "chunk": chunk
        }

    except HTTPException:
        raise
    except Exception as e:
        if conn:
            conn.close()
        logger.error(f"Error fetching chunk by id: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/warehouses/{warehouse_id}/cameras/{cam_id}/logs/employees")
def get_employee_logs(
    warehouse_id: str = Path(..., description="Warehouse ID (e.g., WH001)"),
    cam_id: str = Path(..., description="Camera ID"),
    date: str = Query(..., description="Date in YYYY-MM-DD format")
):
    """Get employee logs for a specific camera and date"""
    try:
        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid date format. Use YYYY-MM-DD"
            )
        
        conn = get_connection()
        cur = conn.cursor()
        
        emp_logs_query = """
            SELECT 
                el.id,
                el.warehouse_id,
                el.emp_id,
                e.emp_name,
                e.emp_number,
                r.role_name,
                el.date,
                el.time,
                el.cam_id,
                el.crop_blob_url,
                el.chunk_id,
                el.emp_access
            FROM public.wh_emp_logs el
            LEFT JOIN public.wh_emp_data e ON el.emp_id = e.emp_id
            LEFT JOIN public.wh_emp_role r ON e.role_id = r.role_id
            WHERE el.warehouse_id = %s AND el.cam_id = %s AND el.date = %s
            ORDER BY el.time
        """
        cur.execute(emp_logs_query, (warehouse_id, cam_id, date))
        log_rows = cur.fetchall()
        
        if not log_rows:
            cur.close()
            conn.close()
            return {
                "status": "success",
                "message": "No employee logs found for the given criteria",
                "warehouse_id": warehouse_id,
                "cam_id": cam_id,
                "date": date,
                "total_logs": 0,
                "hourly_ranges": []
            }
        
        hourly_logs = defaultdict(list)
        
        for row in log_rows:
            log_time = row[7] 
            if log_time:
                hour = log_time.hour
                log_entry = {
                    "log_id": row[0],
                    "warehouse_id": row[1],
                    "emp_id": row[2],
                    "emp_name": row[3],
                    "emp_number": row[4],
                    "role_name": row[5],
                    "date": row[6].strftime('%Y-%m-%d') if row[6] else None,
                    "time": log_time.strftime('%Y-%m-%d %H:%M:%S'),
                    "cam_id": row[8],
                    "crop_blob_url": row[9],
                    "chunk_id": row[10],
                    "emp_access": row[11]
                }
                hourly_logs[hour].append(log_entry)
        
        hourly_ranges = []
        for hour in sorted(hourly_logs.keys()):
            hourly_ranges.append({
                "hour_range": f"{hour:02d}:00 - {hour:02d}:59",
                "start_time": f"{hour:02d}:00",
                "end_time": f"{hour:02d}:59",
                "total_logs": len(hourly_logs[hour]),
                "unique_employees": len(set(log["emp_id"] for log in hourly_logs[hour] if log["emp_id"])),
                "logs": hourly_logs[hour]
            })
        
        cur.close()
        conn.close()
        
        return {
            "status": "success",
            "warehouse_id": warehouse_id,
            "cam_id": cam_id,
            "date": date,
            "total_logs": len(log_rows),
            "unique_employees": len(set(row[2] for row in log_rows if row[2])),
            "hourly_ranges": hourly_ranges
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching employee logs: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/warehouses/{warehouse_id}/cameras/{cam_id}/logs/gunny-bags")
def get_gunny_bag_logs(
    warehouse_id: str = Path(..., description="Warehouse ID (e.g., WH001)"),
    cam_id: str = Path(..., description="Camera ID"),
    date: str = Query(..., description="Date in YYYY-MM-DD format")
):
    """Get gunny bag logs for a specific camera and date"""
    try:
        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid date format. Use YYYY-MM-DD"
            )
        
        conn = get_connection()
        cur = conn.cursor()
        
        gunny_logs_query = """
            SELECT 
                id,
                warehouse_id,
                cam_id,
                count,
                date,
                chunk_id,
                created_at,
                action
                
            FROM public.wh_gunny_logs
            WHERE warehouse_id = %s AND cam_id = %s AND date = %s
            ORDER BY created_at
        """
        cur.execute(gunny_logs_query, (warehouse_id, cam_id, date))
        log_rows = cur.fetchall()
        
        if not log_rows:
            cur.close()
            conn.close()
            return {
                "status": "success",
                "message": "No gunny bag logs found for the given criteria",
                "warehouse_id": warehouse_id,
                "cam_id": cam_id,
                "date": date,
                "total_logs": 0,
                "total_bags": 0,
                "logs": []
            }
        
        logs = []
        total_bags = 0
        action_summary = {}
        
        for row in log_rows:
            bag_count = row[3] or 0
            action = row[7]
            
            log_entry = {
                "log_id": row[0],
                "warehouse_id": row[1],
                "cam_id": row[2],
                "count": bag_count,
                "date": row[4].strftime('%Y-%m-%d') if row[4] else None,
                "chunk_id": row[5],
                "created_at": row[6].strftime('%H:%M:%S') if row[6] else None,
                "action": action
            }
            logs.append(log_entry)
            
            total_bags += bag_count
            
            if action:
                if action not in action_summary:
                    action_summary[action] = {"count": 0, "total_bags": 0}
                action_summary[action]["count"] += 1
                action_summary[action]["total_bags"] += bag_count
        
        cur.close()
        conn.close()
        
        return {
            "status": "success",
            "warehouse_id": warehouse_id,
            "cam_id": cam_id,
            "date": date,
            "total_logs": len(logs),
            "total_bags": total_bags,
            "action_summary": action_summary,
            "logs": logs
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching gunny bag logs: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/warehouses/{warehouse_id}/cameras/{cam_id}/logs/vehicles")
def get_vehicle_logs(
    warehouse_id: str = Path(..., description="Warehouse ID (e.g., WH001)"),
    cam_id: str = Path(..., description="Camera ID"),
    date: str = Query(..., description="Date in YYYY-MM-DD format")
):
    """Get vehicle logs for a specific camera and date"""
    try:
        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid date format. Use YYYY-MM-DD"
            )
        
        conn = get_connection()
        cur = conn.cursor()
        
        vehicle_logs_query = """
            SELECT 
                id,
                warehouse_id,
                cam_id,
                date,
                chunk_id,
                number_plate,
                vehicle_access,
                created_at
            FROM public.wh_vehicle_logs
            WHERE warehouse_id = %s AND cam_id = %s AND date = %s
            ORDER BY created_at
        """
        cur.execute(vehicle_logs_query, (warehouse_id, cam_id, date))
        log_rows = cur.fetchall()
        
        if not log_rows:
            cur.close()
            conn.close()
            return {
                "status": "success",
                "message": "No vehicle logs found for the given criteria",
                "warehouse_id": warehouse_id,
                "cam_id": cam_id,
                "date": date,
                "total_logs": 0,
                "logs": []
            }
        
        logs = []
        unique_vehicles = set()
        access_summary = {}

        # group by number_plate; log_rows already ordered by created_at
        groups = {}  # number_plate -> {"log_id": first_id, "warehouse_id": ..., "cam_id": ..., "date": ..., "chunk_id": first_chunk, "vehicle_access": first_access, "first": datetime, "last": datetime}

        for row in log_rows:
            number_plate = row[5]
            vehicle_access = row[6]
            created_at = row[7]  # expected datetime or None

            # skip rows without number plate
            if not number_plate:
                continue

            # update access_summary for all included rows
            if vehicle_access:
                access_summary[vehicle_access] = access_summary.get(vehicle_access, 0) + 1

            # initialize group if first time seeing this plate
            if number_plate not in groups:
                groups[number_plate] = {
                    "log_id": row[0],
                    "warehouse_id": row[1],
                    "cam_id": row[2],
                    "date": row[3].strftime('%Y-%m-%d') if row[3] else None,
                    "chunk_id": row[4],
                    "vehicle_access": vehicle_access,
                    "first": created_at,
                    "last": created_at
                }
            else:
                # update last seen time (rows are ordered so this will move forward)
                if created_at and (groups[number_plate]["last"] is None or created_at > groups[number_plate]["last"]):
                    groups[number_plate]["last"] = created_at

        # build final logs list from groups
        for plate, info in groups.items():
            first = info["first"]
            last = info["last"]

            # Format created_at as "HH:MM:SS-HH:MM:SS"
            if first and last:
                created_range = f"{first.strftime('%H:%M:%S')}-{last.strftime('%H:%M:%S')}"
            elif first:
                created_range = f"{first.strftime('%H:%M:%S')}-{first.strftime('%H:%M:%S')}"
            else:
                created_range = None

            log_entry = {
                "log_id": info["log_id"],
                "warehouse_id": info["warehouse_id"],
                "cam_id": info["cam_id"],
                "date": info["date"],
                "chunk_id": info["chunk_id"],
                "number_plate": plate,
                "vehicle_access": info["vehicle_access"],
                "created_at": created_range
            }
            logs.append(log_entry)
            unique_vehicles.add(plate)

        cur.close()
        conn.close()

        # you may want to sort logs by the first time (optional)
        # logs.sort(key=lambda x: x["created_at"] if x["created_at"] else "")

        return {
            "status": "success",
            "warehouse_id": warehouse_id,
            "cam_id": cam_id,
            "date": date,
            "total_logs": len(logs),
            "unique_vehicles": len(unique_vehicles),
            "access_summary": access_summary,
            "logs": logs
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching vehicle logs: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/warehouses/{warehouse_id}/cameras/{cam_id}/analytics/vehicle-gunny-count")
def get_vehicle_wise_gunny_count(
    warehouse_id: str = Path(..., description="Warehouse ID (e.g., WH001)"),
    cam_id: str = Path(..., description="Camera ID"),
    date: str = Query(..., description="Date in YYYY-MM-DD format")
):
    """Get vehicle-wise gunny bag count analytics"""
    try:
        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid date format. Use YYYY-MM-DD"
            )
        
        conn = get_connection()
        cur = conn.cursor()
        
        vehicle_logs_query = """
            SELECT 
                number_plate,
                ARRAY_AGG(DISTINCT chunk_id) as chunk_ids
            FROM public.wh_vehicle_logs
            WHERE warehouse_id = %s 
                AND cam_id = %s 
                AND date = %s 
                AND number_plate IS NOT NULL
                AND chunk_id IS NOT NULL
            GROUP BY number_plate
            ORDER BY number_plate
        """
        cur.execute(vehicle_logs_query, (warehouse_id, cam_id, date))
        vehicle_rows = cur.fetchall()
        
        if not vehicle_rows:
            cur.close()
            conn.close()
            return {
                "status": "success",
                "message": "No vehicles found for the given criteria",
                "warehouse_id": warehouse_id,
                "cam_id": cam_id,
                "date": date,
                "total_vehicles": 0,
                "grand_total_bags": 0,
                "vehicles": []
            }
        
        vehicles = []
        grand_total_bags = 0
        
        for row in vehicle_rows:
            number_plate = row[0]
            chunk_ids = row[1]
            
            gunny_query = """
                SELECT 
                    action,
                    SUM(count) as total_count,
                    COUNT(*) as entry_count,
                    MIN(created_at) as first_entry_time,
                    MAX(created_at) as last_entry_time
                FROM public.wh_gunny_logs
                WHERE warehouse_id = %s 
                    AND cam_id = %s 
                    AND date = %s 
                    AND chunk_id = ANY(%s)
                GROUP BY action
                ORDER BY action
            """
            cur.execute(gunny_query, (warehouse_id, cam_id, date, chunk_ids))
            gunny_rows = cur.fetchall()
            
            action_breakdown = []
            total_bags_all_actions = 0
            
            for gunny_row in gunny_rows:
                action = gunny_row[0]
                total_count = gunny_row[1] or 0
                entry_count = gunny_row[2]
                first_entry = gunny_row[3]
                last_entry = gunny_row[4]
                
                action_breakdown.append({
                    "action": action,
                    "total_count": total_count,
                    "number_of_entries": entry_count,
                    "first_entry_time": first_entry.strftime('%H:%M:%S') if first_entry else None,
                    "last_entry_time": last_entry.strftime('%H:%M:%S') if last_entry else None
                })
                
                total_bags_all_actions += total_count
            
            vehicle_entry = {
                "number_plate": number_plate,
                "chunk_ids": chunk_ids,
                "total_bags_all_actions": total_bags_all_actions,
                "action_breakdown": action_breakdown
            }
            
            vehicles.append(vehicle_entry)
            grand_total_bags += total_bags_all_actions
        
        cur.close()
        conn.close()
        
        return {
            "status": "success",
            "warehouse_id": warehouse_id,
            "cam_id": cam_id,
            "date": date,
            "total_vehicles": len(vehicles),
            "grand_total_bags": grand_total_bags,
            "vehicles": vehicles
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching vehicle-wise gunny count: {e}")