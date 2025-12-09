import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
from collections import defaultdict
import json
import uuid
import os
import logging
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from fastapi.middleware.cors import CORSMiddleware
# Load environment variables
load_dotenv()

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# PostgreSQL Configuration
PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = int(os.getenv("PG_PORT", 5432))
PG_USER = os.getenv("PG_USER", "core")
PG_PASSWORD = os.getenv("PG_PASSWORD", "1234")
PG_DATABASE = os.getenv("PG_DATABASE", "coredb")

# FastAPI Application
app = FastAPI(title="Warehouse Sessions API", version="1.0")

# CORS Configuration - Allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allows all headers
)
# ==========================================
# Helper Functions
# ==========================================

def get_connection():
    """Create and return a PostgreSQL connection"""
    return psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        user=PG_USER,
        password=PG_PASSWORD,
        database=PG_DATABASE
    )


def detect_vehicle_sessions(gunny_logs, vehicle_logs):
    if not gunny_logs and not vehicle_logs:
        return []
    
    sessions = {}  # Dictionary to store sessions by vehicle number
    current_vehicle = None
    
    # Combine and sort logs by timestamp
    all_events = []
    
    # Add gunny bag events
    for glog in gunny_logs:
        if glog['start_time']:
            timestamp = glog['start_time']
            if isinstance(timestamp, str):
                try:
                    timestamp = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                except:
                    continue
            
            all_events.append({
                'type': 'gunny',
                'timestamp': timestamp,
                'data': glog
            })
    
    # Add vehicle events
    for vlog in vehicle_logs:
        if vlog['start_time']:
            timestamp = vlog['start_time']
            if isinstance(timestamp, str):
                try:
                    timestamp = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                except:
                    continue
            
            all_events.append({
                'type': 'vehicle',
                'timestamp': timestamp,
                'vehicle_number': vlog['vehicle_number'],
                'data': vlog
            })
    
    # Sort by timestamp
    all_events.sort(key=lambda x: x['timestamp'])
    
    # FALLBACK: If no vehicle logs, create a default session with "XXXX"
    if not vehicle_logs and gunny_logs:
        fallback_vehicle = "XXXX"
        
        first_timestamp = all_events[0]['timestamp'] if all_events else datetime.now()
        
        sessions[fallback_vehicle] = {
            'session_id': str(uuid.uuid4()),
            'vehicle_number': fallback_vehicle,
            'start_time': first_timestamp,
            'end_time': first_timestamp,
            'chunks': [],
            'total_bags_loaded': 0,
            'total_bags_unloaded': 0,
            'vehicle_data': None,
            'authorized_bags': 0,
            'status': 'Unknown',
            'authorization': 'Unknown'
        }
        current_vehicle = fallback_vehicle
    
    for idx, event in enumerate(all_events):
        if event['type'] == 'vehicle':
            vehicle_num = event['vehicle_number']
            
            # Check if this is a new vehicle
            if vehicle_num != current_vehicle:
                current_vehicle = vehicle_num
                
                # Check if we already have a session for this vehicle
                if vehicle_num not in sessions:
                    # Convert bags_capacity to int, handling None and string values
                    bags_capacity = event['data'].get('bags_capacity', 0)
                    if bags_capacity is None:
                        bags_capacity = 0
                    try:
                        bags_capacity = int(bags_capacity)
                    except (ValueError, TypeError):
                        bags_capacity = 0
                    
                    # Create new session for this vehicle
                    sessions[vehicle_num] = {
                        'session_id': str(uuid.uuid4()),
                        'vehicle_number': vehicle_num,
                        'start_time': event['timestamp'],
                        'end_time': event['timestamp'],
                        'chunks': [],
                        'total_bags_loaded': 0,
                        'total_bags_unloaded': 0,
                        'vehicle_data': event['data'],
                        'authorized_bags': bags_capacity,
                        'status': event['data'].get('status', 'Unknown'),
                        'authorization': event['data'].get('vehicle_access', 'Unknown')
                    }
                else:
                    # Update end time
                    sessions[vehicle_num]['end_time'] = event['timestamp']
            else:
                # Same vehicle continuing, just update end time
                if current_vehicle in sessions:
                    sessions[current_vehicle]['end_time'] = event['timestamp']
        
        elif event['type'] == 'gunny' and current_vehicle and current_vehicle in sessions:
            # Add gunny bag data to current vehicle's session
            glog = event['data']
            count = glog.get('count', 0) or 0
            status = glog.get('status', '')
            
            chunk_info = {
                'chunk_id': str(glog['id']),
                'video_url': glog.get('video_s3_url', ''),
                'timestamp': event['timestamp'],
                'status': status,
                'bags_count': count
            }
            
            sessions[current_vehicle]['chunks'].append(chunk_info)
            sessions[current_vehicle]['end_time'] = event['timestamp']
            
            if status == 'LOADING':
                sessions[current_vehicle]['total_bags_loaded'] += count
            elif status == 'UNLOADING':
                sessions[current_vehicle]['total_bags_unloaded'] += count
    
    # Convert sessions dictionary to list
    session_list = []
    for vehicle_num, session in sessions.items():
        session_list.append(session)
    
    # Sort by start time
    session_list.sort(key=lambda x: x['start_time'])
    
    return session_list


def get_warehouse_data_with_sessions(warehouse_id, camera_id, date_str):
    try:
        # Parse date - handle both formats
        try:
            query_date = datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            query_date = datetime.strptime(date_str, '%d-%m-%Y')
        
        display_date = query_date.strftime('%d-%m-%Y')
        end_date = query_date
        start_date = end_date - timedelta(days=4)
        
        conn = psycopg2.connect(
            host=PG_HOST,
            port=PG_PORT,
            user=PG_USER,
            password=PG_PASSWORD,
            database=PG_DATABASE
        )
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # 1. Get Camera Information
        cur.execute("""
            SELECT camera_id, camera_name, warehouse_id, status, 
                   s3_bucket_url, stream_arn, region_name
            FROM warehouse."wh-cameras"
            WHERE camera_id::text = %s AND warehouse_id = %s
        """, (str(camera_id), warehouse_id))
        
        camera_info = cur.fetchone()
        
        if not camera_info:
            return {"error": f"Camera {camera_id} not found in warehouse {warehouse_id}"}
        
        # 2. Get Gunny Bag Logs
        cur.execute("""
            SELECT id, count, date, start_time, end_time, status, 
                   video_s3_url, video_name
            FROM warehouse."wh-gunny-bag-logs"
            WHERE camera_id::text = %s 
                AND date::date = %s
            ORDER BY start_time
        """, (str(camera_id), query_date.date()))
        
        gunny_logs = cur.fetchall()
        
        # 3. Get Vehicle Logs
        cur.execute("""
            SELECT vl.id, vl.vehicle_number, vl.date, vl.start_time, 
                   vl.end_time, vl.status, vl.video_s3_url,
                   v.bags_capacity, v.commodity, v.vehicle_access
            FROM warehouse."wh-vehicle-logs" vl
            LEFT JOIN warehouse."wh-vehicles" v ON vl.vehicle_number = v.number_plates
            WHERE vl.camera_id::text = %s 
                AND vl.date::date = %s
            ORDER BY vl.start_time
        """, (str(camera_id), query_date.date()))
        
        vehicle_logs = cur.fetchall()
        
        # 4. DETECT VEHICLE SESSIONS
        sessions = detect_vehicle_sessions(gunny_logs, vehicle_logs)
        
        # 5. Calculate totals and hourly summary from sessions
        total_loading = 0
        total_unloading = 0
        hourly_summary = defaultdict(lambda: {'LOADING': 0, 'UNLOADING': 0})
        
        for session in sessions:
            total_loading += session['total_bags_loaded']
            total_unloading += session['total_bags_unloaded']
            
            for chunk in session['chunks']:
                hour = chunk['timestamp'].strftime('%H:00')
                if chunk['status'] == 'LOADING':
                    hourly_summary[hour]['LOADING'] += chunk['bags_count']
                elif chunk['status'] == 'UNLOADING':
                    hourly_summary[hour]['UNLOADING'] += chunk['bags_count']
        
        # Convert hourly summary to list
        hourly_list = []
        for hour in sorted(hourly_summary.keys()):
            counts = hourly_summary[hour]
            if counts['LOADING'] > 0:
                hourly_list.append({
                    "start_time": hour,
                    "status": "Loading",
                    "count": counts['LOADING']
                })
            if counts['UNLOADING'] > 0:
                hourly_list.append({
                    "start_time": hour,
                    "status": "Unloading",
                    "count": counts['UNLOADING']
                })
        
        # 6. Get total chunks
        total_chunks = len(gunny_logs)
        
        # 7. Latest chunks
        latest_chunks = []
        for log in gunny_logs[-2:]:
            if log['start_time']:
                timestamp = log['start_time']
                if isinstance(timestamp, str):
                    try:
                        timestamp = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                    except:
                        pass
                
                chunk_id = f"CAM{camera_id:03d}-{timestamp.strftime('%Y-%m-%d-%H-%M-%S')}"
                ts_iso = timestamp.isoformat()
            else:
                chunk_id = str(log['id'])
                ts_iso = None
            
            latest_chunks.append({
                "chunk_id": chunk_id,
                "presigned_url": log['video_s3_url'],
                "transcript": f"{log['status']} - {log['count']} bags",
                "timestamp": ts_iso
            })
        
        # 8. Mismatch is now null (not calculated)
        mismatch = None
        mismatch_trend = "stable"
        
        # 9. Trends
        loading_trend = "positive" if total_loading > 0 else "stable"
        unloading_trend = "positive" if total_unloading > 0 else "stable"
        
        # 10. Build Session-based Logs
        logs = []
        for i, session in enumerate(sessions, 1):
            start_time_str = session['start_time'].strftime('%H:%M')
            end_time_str = session['end_time'].strftime('%H:%M')
            log_date = session['start_time'].strftime('%d-%m-%Y')
            
            net_bags = session['total_bags_loaded'] - session['total_bags_unloaded']
            
            # Ensure authorized_bags is an integer
            authorized_bags = session['authorized_bags']
            if not isinstance(authorized_bags, int):
                try:
                    authorized_bags = int(authorized_bags) if authorized_bags else 0
                except (ValueError, TypeError):
                    authorized_bags = 0
            
            logs.append({
                "session_id": session['session_id'],
                "vehicle_number": session['vehicle_number'],
                "status": session['status'],
                "authorization_status": session['authorization'],
                "date": log_date,
                "start_time": start_time_str,
                "end_time": end_time_str,
                "duration_minutes": int((session['end_time'] - session['start_time']).total_seconds() / 60),
                "authorized_bags": authorized_bags,
                "actual_bags_loaded": session['total_bags_loaded'],
                "actual_bags_unloaded": session['total_bags_unloaded'],
                "net_bags": net_bags,
                "total_chunks": len(session['chunks']),
                "chunks_detail": [
                    {
                        "chunk_id": c['chunk_id'],
                        "timestamp": c['timestamp'].strftime('%H:%M:%S'),
                        "operation": c['status'],
                        "bags_count": c['bags_count']
                    } for c in session['chunks']
                ]
            })
        
        cur.close()
        conn.close()
        
        # 11. Build final output
        output = {
            "camera": {
                "stream_url": camera_info['stream_arn'] or camera_info['s3_bucket_url'],
                "camera_data": {
                    "camera_name": camera_info['camera_name'],
                    "camera_id": str(camera_info['camera_id']),
                    "warehouse_id": camera_info['warehouse_id'],
                    "status": camera_info['status'] or "N/A"
                },
                "total_chunks": total_chunks,
                "latest_chunks": latest_chunks
            },
            "date_range": {
                "start_date": start_date.strftime('%d-%m-%Y'),
                "end_date": end_date.strftime('%d-%m-%Y'),
                "selected_date": display_date
            },
            "summary": {
                "bags": {
                    "paddy": 0,
                    "wheat": 0
                },
                "Hourly_Summary": hourly_list,
                f"Total_Bags_Loaded_on_{display_date}": {
                    "number": total_loading,
                    "trend": loading_trend
                },
                f"Total_Bags_UnLoaded_on_{display_date}": {
                    "number": total_unloading,
                    "trend": unloading_trend
                },
                "Mismatch": {
                    "number": mismatch,
                    "trend": mismatch_trend
                },
                "Total_Vehicle_Sessions": len(sessions),
                "Logs": logs
            }
        }
        
        return output
        
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }


def print_summary_stats(result):
    """Print a formatted summary of the results (CLI mode only)"""
    # This function is kept for backward compatibility with CLI mode
    # but logging is handled via logger object instead
    pass


def get_warehouse_status_summary(date_str: str) -> Dict[str, Any]:
    try:
        # Parse date - handle both formats
        try:
            query_date = datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            query_date = datetime.strptime(date_str, '%d-%m-%Y')
        
        display_date = query_date.strftime('%d-%m-%Y')
        
        conn = psycopg2.connect(
            host=PG_HOST,
            port=PG_PORT,
            user=PG_USER,
            password=PG_PASSWORD,
            database=PG_DATABASE
        )
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # 1. Get all warehouses
        cur.execute("""
            SELECT DISTINCT warehouse_id
            FROM warehouse."wh-cameras"
            WHERE warehouse_id IS NOT NULL
            ORDER BY warehouse_id
        """)
        
        warehouses = [row['warehouse_id'] for row in cur.fetchall()]
        
        # Initialize aggregated data
        total_vehicles_entered = 0
        total_authorized_vehicles = 0
        total_unauthorized_vehicles = 0
        total_bags_loaded = 0
        total_bags_unloaded = 0
        total_hamalis = 0
        total_supervisors = 0
        warehouse_insights = {}
        
        # 2. Process each warehouse
        for warehouse_id in warehouses:
            
            # Get vehicle logs for this warehouse
            cur.execute("""
                SELECT vl.id, vl.vehicle_number, vl.start_time, vl.end_time, 
                       vl.status, v.vehicle_access
                FROM warehouse."wh-vehicle-logs" vl
                LEFT JOIN warehouse."wh-vehicles" v ON vl.vehicle_number = v.number_plates
                WHERE vl.camera_id IN (
                    SELECT camera_id FROM warehouse."wh-cameras" 
                    WHERE warehouse_id = %s
                )
                AND vl.date::date = %s
            """, (warehouse_id, query_date.date()))
            
            vehicle_logs = cur.fetchall() or []
            
            # Get gunny bag logs for this warehouse
            cur.execute("""
                SELECT id, count, status
                FROM warehouse."wh-gunny-bag-logs"
                WHERE camera_id IN (
                    SELECT camera_id FROM warehouse."wh-cameras" 
                    WHERE warehouse_id = %s
                )
                AND date::date = %s
            """, (warehouse_id, query_date.date()))
            
            gunny_logs = cur.fetchall() or []
            
            # Calculate warehouse-specific metrics
            vehicles_entered = len(set(v['vehicle_number'] for v in vehicle_logs if v['vehicle_number']))
            
            authorized_vehicles = len([v for v in vehicle_logs 
                                     if v.get('vehicle_access') in ['Authorized', 'authorized', 'AUTHORIZED']])
            unauthorized_vehicles = len([v for v in vehicle_logs 
                                        if v.get('vehicle_access') in ['Unauthorized', 'unauthorized', 'UNAUTHORIZED']])
            
            bags_loaded = sum(int(g.get('count', 0) or 0) for g in gunny_logs 
                            if g.get('status') == 'LOADING')
            bags_unloaded = sum(int(g.get('count', 0) or 0) for g in gunny_logs 
                               if g.get('status') == 'UNLOADING')
            
            # Get personnel counts (hamalis and supervisors)
            # This would need separate tables - estimating based on activity
            hamalis_count = max(1, len(vehicle_logs) // 5) if vehicle_logs else 0
            supervisors_count = max(1, len(vehicle_logs) // 20) if vehicle_logs else 0
            
            # Update totals
            total_vehicles_entered += vehicles_entered
            total_authorized_vehicles += authorized_vehicles
            total_unauthorized_vehicles += unauthorized_vehicles
            total_bags_loaded += bags_loaded
            total_bags_unloaded += bags_unloaded
            total_hamalis += hamalis_count
            total_supervisors += supervisors_count
            
            # Build warehouse insight
            warehouse_insights[warehouse_id] = {
                "vehicles_entered": vehicles_entered,
                "vehicles_exited": max(0, vehicles_entered - 1),  # Assume most vehicles exit
                "hamalis": hamalis_count,
                "supervisors": supervisors_count,
                "bags_loaded": bags_loaded,
                "bags_unloaded": bags_unloaded
            }
        
        cur.close()
        conn.close()
        
        # Build response
        response = {
            "date": display_date,
            "total_vehicles_entered": total_vehicles_entered,
            "authorized_vehicles": total_authorized_vehicles,
            "unauthorized_vehicles": total_unauthorized_vehicles,
            "total_bags_loaded": total_bags_loaded,
            "total_bags_unloaded": total_bags_unloaded,
            "total_hamalis": total_hamalis,
            "total_supervisors": total_supervisors,
            "warehouse_insights": warehouse_insights
        }
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# FastAPI Routes
# ==========================================

@app.get("/healthz")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "Warehouse Sessions API"}


@app.get("/warehouse-status")
async def api_get_warehouse_status(date: str):
    logger.info(f"Fetching warehouse status summary for date: {date}")
    try:
        result = get_warehouse_status_summary(date)
        return JSONResponse(status_code=status.HTTP_200_OK, content=result)
        
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/warehouse/{warehouse_id}/camera/{camera_id}/date/{date_str}")
async def api_get_warehouse_sessions(warehouse_id: str, camera_id: int, date_str: str):
    logger.info(f"Processing request: warehouse={warehouse_id}, camera={camera_id}, date={date_str}")
    
    try:
        result = get_warehouse_data_with_sessions(warehouse_id, camera_id, date_str)
        
        if "error" in result:
            logger.error(f"Error in get_warehouse_data_with_sessions: {result['error']}")
            raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))
        
        logger.info(f"Successfully processed request for warehouse={warehouse_id}")
        return JSONResponse(status_code=status.HTTP_200_OK, content=result)
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"Unexpected error processing warehouse data")
        raise HTTPException(status_code=500, detail=str(exc))


# ==========================================
# NEW ENDPOINTS: Hamali, Warehouses, and Camera Chunks
# ==========================================

@app.get("/hamali-logs")
def get_hamali_logs(
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    warehouse_id: str = Query(..., description="Warehouse ID (e.g., WH001)")
):
    """
    Get hourly worker logs grouped by role (hamali/supervisor) for a specific date and warehouse
    
    Example: /hamali-logs?date=2025-01-15&warehouse_id=WH001
    """
    try:
        # Validate date format
        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        conn = get_connection()
        cur = conn.cursor()
        
        # Step 1: Get all workers from the warehouse with their roles
        workers_query = """
            SELECT id, name, mobile, role, epf_id, warehouse_id
            FROM warehouse."wh-workers"
            WHERE warehouse_id = %s
        """
        cur.execute(workers_query, (warehouse_id,))
        workers_rows = cur.fetchall()
        
        if not workers_rows:
            cur.close()
            conn.close()
            return {
                "date": date,
                "warehouse_id": warehouse_id,
                "hamali_logs": [],
                "supervisor_logs": []
            }
        
        # Create a dictionary of workers for quick lookup
        workers_dict = {}
        for worker_row in workers_rows:
            workers_dict[worker_row[0]] = {
                "id": worker_row[0],
                "name": worker_row[1],
                "mobile": worker_row[2],
                "role": worker_row[3],
                "epf_id": worker_row[4],
                "warehouse_id": worker_row[5]
            }
        
        # Get worker IDs for this warehouse
        worker_ids = list(workers_dict.keys())
        
        # Step 2: Fetch worker logs for the given date
        logs_query = """
            SELECT id, worker_id, date, start_time, end_time, camera_id, 
                   crop_s3_url, video_s3_url, created_at
            FROM warehouse."wh-worker-logs"
            WHERE worker_id = ANY(%s) AND date = %s
            ORDER BY worker_id, start_time
        """
        cur.execute(logs_query, (worker_ids, date))
        logs_rows = cur.fetchall()
        
        # Group logs by role and hour
        hamali_hourly_dict = defaultdict(list)
        supervisor_hourly_dict = defaultdict(list)
        
        for log_row in logs_rows:
            log_id = log_row[0]
            worker_id = log_row[1]
            
            # Match worker_id with worker info
            if worker_id not in workers_dict:
                continue
            
            worker_info = workers_dict[worker_id]
            role = worker_info["role"].lower() if worker_info["role"] else ""
            
            # Handle start_time and end_time
            start_time = None
            hour_key = None
            
            if log_row[3]:
                if isinstance(log_row[3], str):
                    start_time = log_row[3]
                    # Extract hour from datetime string (format: "2025-09-22 10:08:00")
                    hour_key = start_time.split(' ')[1].split(':')[0] if ' ' in start_time else None
                else:
                    start_time = log_row[3].strftime('%Y-%m-%d %H:%M:%S')
                    hour_key = log_row[3].strftime('%H')
            
            end_time = None
            if log_row[4]:
                if isinstance(log_row[4], str):
                    end_time = log_row[4]
                else:
                    end_time = log_row[4].strftime('%Y-%m-%d %H:%M:%S')
            
            # Skip if we can't determine the hour
            if not hour_key:
                continue
            
            # Create log entry
            log_entry = {
                "log_id": log_id,
                "worker_id": worker_info["id"],
                "name": worker_info["name"],
                "mobile": worker_info["mobile"],
                "epf_id": worker_info["epf_id"],
                "warehouse_id": worker_info["warehouse_id"],
                "role": worker_info["role"],
                "start_time": start_time,
                "end_time": end_time,
                "camera_id": log_row[5]
            }
            
            # Add presigned_url if crop_s3_url exists
            if log_row[6]:
                log_entry["presigned_url"] = log_row[6]
            
            # Group by role and hour
            if role in ["hamali", "worker", "labour"]:
                hamali_hourly_dict[hour_key].append(log_entry)
            elif role in ["supervisor", "incharge"]:
                supervisor_hourly_dict[hour_key].append(log_entry)
        
        # Format the response with hourly summaries
        hamali_logs = []
        for hour in sorted(hamali_hourly_dict.keys()):
            hamali_logs.append({
                "start_time": f"{hour}:00",
                "end_time": f"{hour}:59",
                "hourly_summery": hamali_hourly_dict[hour]
            })
        
        supervisor_logs = []
        for hour in sorted(supervisor_hourly_dict.keys()):
            supervisor_logs.append({
                "start_time": f"{hour}:00",
                "end_time": f"{hour}:59",
                "hourly_summery": supervisor_hourly_dict[hour]
            })
        
        cur.close()
        conn.close()
        
        return {
            "date": date,
            "warehouse_id": warehouse_id,
            "hamali_logs": hamali_logs,
            "supervisor_logs": supervisor_logs
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/warehouses/details")
def get_all_warehouses_with_staff():
    """
    Get all warehouse details along with staff members and cameras for each warehouse
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # Fetch all warehouses
        warehouse_query = """
            SELECT id, name, location, latitude, longitude, capacity
            FROM warehouse."wh-warehouses"
            ORDER BY id
        """
        cur.execute(warehouse_query)
        warehouse_rows = cur.fetchall()
        
        if not warehouse_rows:
            cur.close()
            conn.close()
            return {"warehouses": []}
        
        warehouses_list = []
        
        # For each warehouse, fetch its staff and cameras
        for warehouse_row in warehouse_rows:
            warehouse_id = warehouse_row[0]
            
            # Fetch staff details for this warehouse
            staff_query = """
                SELECT id, name, mobile, role, epf_id, warehouse_id
                FROM warehouse."wh-workers"
                WHERE warehouse_id = %s
                ORDER BY role, name
            """
            cur.execute(staff_query, (warehouse_id,))
            staff_rows = cur.fetchall()
            
            # Fetch camera details for this warehouse
            camera_query = """
                SELECT camera_id, camera_name, warehouse_id, latitude, longitude, 
                       region_name, s3_bucket_url, stream_arn, status, transcript_s3_bucket_uri
                FROM warehouse."wh-cameras"
                WHERE warehouse_id = %s
                ORDER BY camera_id
            """
            cur.execute(camera_query, (warehouse_id,))
            camera_rows = cur.fetchall()
            
            # Build warehouse object
            warehouse_data = {
                "id": warehouse_row[0],
                "name": warehouse_row[1],
                "location": warehouse_row[2],
                "latitude": warehouse_row[3],
                "longitude": warehouse_row[4],
                "capacity": warehouse_row[5],
                "staff": [],
                "cameras": [],
                "total_cameras": len(camera_rows)
            }
            
            # Add staff members
            for staff_row in staff_rows:
                staff_member = {
                    "role": staff_row[3],
                    "id": staff_row[0],
                    "name": staff_row[1],
                    "mobile": staff_row[2],
                    "epf_id": staff_row[4]
                }
                warehouse_data["staff"].append(staff_member)
            
            # Add cameras
            for camera_row in camera_rows:
                camera_data = {
                    "camera_id": camera_row[0],
                    "camera_name": camera_row[1],
                    "warehouse_id": camera_row[2],
                    "latitude": camera_row[3],
                    "longitude": camera_row[4],
                    "region_name": camera_row[5],
                    "s3_bucket_url": camera_row[6],
                    "stream_arn": camera_row[7],
                    "status": camera_row[8],
                    "transcript_s3_bucket_uri": camera_row[9]
                }
                warehouse_data["cameras"].append(camera_data)
            
            warehouses_list.append(warehouse_data)
        
        cur.close()
        conn.close()
        
        return {"warehouses": warehouses_list}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/warehouses/{warehouse_id}/details")
def get_warehouse_with_staff(warehouse_id: str):
    """
    Get specific warehouse details along with staff members and cameras
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # Fetch warehouse details
        warehouse_query = """
            SELECT id, name, location, latitude, longitude, capacity
            FROM warehouse."wh-warehouses"
            WHERE id = %s
        """
        cur.execute(warehouse_query, (warehouse_id,))
        warehouse_row = cur.fetchone()
        
        if not warehouse_row:
            cur.close()
            conn.close()
            raise HTTPException(status_code=404, detail=f"Warehouse not found: {warehouse_id}")
        
        # Fetch staff details for this warehouse
        staff_query = """
            SELECT id, name, mobile, role, epf_id, warehouse_id
            FROM warehouse."wh-workers"
            WHERE warehouse_id = %s
            ORDER BY role, name
        """
        cur.execute(staff_query, (warehouse_id,))
        staff_rows = cur.fetchall()
        
        # Fetch camera details for this warehouse
        camera_query = """
            SELECT camera_id, camera_name, warehouse_id, latitude, longitude, 
                   region_name, s3_bucket_url, stream_arn, status, transcript_s3_bucket_uri
            FROM warehouse."wh-cameras"
            WHERE warehouse_id = %s
            ORDER BY camera_id
        """
        cur.execute(camera_query, (warehouse_id,))
        camera_rows = cur.fetchall()
        
        # Build warehouse object
        warehouse_data = {
            "id": warehouse_row[0],
            "name": warehouse_row[1],
            "location": warehouse_row[2],
            "latitude": warehouse_row[3],
            "longitude": warehouse_row[4],
            "capacity": warehouse_row[5],
            "staff": [],
            "cameras": [],
            "total_cameras": len(camera_rows)
        }
        
        # Add staff members
        for staff_row in staff_rows:
            staff_member = {
                "role": staff_row[3],
                "id": staff_row[0],
                "name": staff_row[1],
                "mobile": staff_row[2],
                "epf_id": staff_row[4]
            }
            warehouse_data["staff"].append(staff_member)
        
        # Add cameras
        for camera_row in camera_rows:
            camera_data = {
                "camera_id": camera_row[0],
                "camera_name": camera_row[1],
                "warehouse_id": camera_row[2],
                "latitude": camera_row[3],
                "longitude": camera_row[4],
                "region_name": camera_row[5],
                "s3_bucket_url": camera_row[6],
                "stream_arn": camera_row[7],
                "status": camera_row[8],
                "transcript_s3_bucket_uri": camera_row[9]
            }
            warehouse_data["cameras"].append(camera_data)
        
        cur.close()
        conn.close()
        
        return warehouse_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/Camera_Chunks")
def get_gunny_bag_videos(
    camera_id: str = Query(..., description="Camera ID to filter videos")
):
    """
    Get all video S3 URLs from gunny-bag-logs table for a specific camera
    
    Example: /Camera_Chunks?camera_id=1
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # Fetch all video URLs for the given camera_id
        query = """
            SELECT id, camera_id, video_s3_url, created_at
            FROM warehouse."wh-gunny-bag-logs"
            WHERE camera_id = %s AND video_s3_url IS NOT NULL
            ORDER BY created_at DESC
        """
        cur.execute(query, (camera_id,))
        rows = cur.fetchall()
        
        # Format the response
        videos = []
        for row in rows:
            video_entry = {
                "log_id": row[0],
                "camera_id": row[1],
                "video_s3_url": row[2],
                "created_at": row[3].strftime('%Y-%m-%d %H:%M:%S') if row[3] else None
            }
            videos.append(video_entry)
        
        cur.close()
        conn.close()
        
        return {
            "camera_id": camera_id,
            "total_videos": len(videos),
            "videos": videos
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


# ==========================================
# CLI Support (for direct execution)
# ==========================================

if __name__ == "__main__":
    import time
    import uvicorn
    
    # Check if running with --api flag for FastAPI server
    import sys
    
    if "--api" in sys.argv:
        # Run as FastAPI server
        port = 8081
        host = "20.46.250.11"
        logger.info(f"Starting FastAPI server on {host}:{port}")
        logger.info(f"API available at http://{host}:{port}/")
        uvicorn.run(app, host=host, port=port, reload=True, log_level=LOG_LEVEL.lower())
    else:
        # Run as CLI script (original behavior)
        # Example payload - CHANGE THESE VALUES
        warehouse_id = "WH001"
        camera_id = 1
        date = "22-09-2025"  # Can also use format "2025-09-22"
        
        start_time = time.time()
        result = get_warehouse_data_with_sessions(warehouse_id, camera_id, date)
        end_time = time.time()
        
        elapsed_time = end_time - start_time
        
        # Print summary statistics
        print_summary_stats(result)