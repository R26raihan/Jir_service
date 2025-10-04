from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import mysql.connector
from mysql.connector import Error
from datetime import datetime, date
from typing import List, Optional
import json

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Raihan26",
            database="crowd_monitoring"
        )
        return connection
    except Error as e:
        print(f"[DB ERROR] {e}")
        return None

@app.get("/")
async def health_check():
    return {"service": "crowd_llm", "status": "ok"}

@app.get("/health")
async def health_check_alt():
    return {"service": "crowd_llm", "status": "ok"}

@app.get("/crowd/today")
async def get_today_crowd_summary():
    """Get today's crowd summary with total, conditions, and locations"""
    conn = get_db_connection()
    if not conn:
        return {"error": "Database connection failed"}
    
    try:
        cursor = conn.cursor(dictionary=True)
        today = date.today()
        
        # Get today's data
        cursor.execute("""
            SELECT 
                location,
                COUNT(*) as total_records,
                AVG(count) as avg_count,
                MIN(count) as min_count,
                MAX(count) as max_count,
                SUM(count) as total_crowd_today
            FROM crowd_history 
            WHERE DATE(timestamp) = %s
            GROUP BY location
            ORDER BY total_crowd_today DESC
        """, (today,))
        
        location_data = cursor.fetchall()
        
        # Get overall today's summary
        cursor.execute("""
            SELECT 
                COUNT(*) as total_records_today,
                SUM(count) as total_crowd_today,
                AVG(count) as avg_crowd_today,
                MIN(count) as min_crowd_today,
                MAX(count) as max_crowd_today
            FROM crowd_history 
            WHERE DATE(timestamp) = %s
        """, (today,))
        
        summary = cursor.fetchone()
        
        # Get latest conditions for each location
        cursor.execute("""
            SELECT 
                location,
                count,
                timestamp,
                CASE 
                    WHEN count <= 100 THEN 'ringan'
                    WHEN count <= 200 THEN 'sedang'
                    WHEN count <= 400 THEN 'ramai'
                    ELSE 'padat'
                END as kondisi
            FROM crowd_history 
            WHERE DATE(timestamp) = %s
            AND (location, timestamp) IN (
                SELECT location, MAX(timestamp) 
                FROM crowd_history 
                WHERE DATE(timestamp) = %s
                GROUP BY location
            )
            ORDER BY count DESC
        """, (today, today))
        
        latest_conditions = cursor.fetchall()
        
        # Location coordinates (you can modify these based on your actual locations)
        location_coords = {
            "DPR": {"latitude": -6.2088, "longitude": 106.8456},
            "Patung Kuda": {"latitude": -6.1751, "longitude": 106.8263},
            "Bundaran HI": {"latitude": -6.1944, "longitude": 106.8229},
            "Monas": {"latitude": -6.1751, "longitude": 106.8263},
            "GBK": {"latitude": -6.2297, "longitude": 106.8019},
            "Istana Negara": {"latitude": -6.1751, "longitude": 106.8263},
            "Bundaran Senayan": {"latitude": -6.2297, "longitude": 106.8019},
            "Mabes Polri": {"latitude": -6.1751, "longitude": 106.8263}
        }
        
        # Add coordinates to location data
        for location in location_data:
            location_name = location['location']
            if location_name in location_coords:
                location['latitude'] = location_coords[location_name]['latitude']
                location['longitude'] = location_coords[location_name]['longitude']
            else:
                location['latitude'] = None
                location['longitude'] = None
        
        # Add coordinates to latest conditions
        for condition in latest_conditions:
            location_name = condition['location']
            if location_name in location_coords:
                condition['latitude'] = location_coords[location_name]['latitude']
                condition['longitude'] = location_coords[location_name]['longitude']
            else:
                condition['latitude'] = None
                condition['longitude'] = None
        
        return {
            "date": today.isoformat(),
            "summary": summary,
            "locations": location_data,
            "latest_conditions": latest_conditions,
            "total_locations": len(location_data)
        }
        
    except Error as e:
        return {"error": str(e)}
    finally:
        cursor.close()
        conn.close()

@app.get("/crowd/conditions")
async def get_crowd_conditions():
    """Get current crowd conditions for all locations"""
    conn = get_db_connection()
    if not conn:
        return {"error": "Database connection failed"}
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Get latest condition for each location
        cursor.execute("""
            SELECT 
                location,
                count,
                timestamp,
                CASE 
                    WHEN count <= 100 THEN 'ringan'
                    WHEN count <= 200 THEN 'sedang'
                    WHEN count <= 400 THEN 'ramai'
                    ELSE 'padat'
                END as kondisi,
                CASE 
                    WHEN count <= 100 THEN 1
                    WHEN count <= 200 THEN 2
                    WHEN count <= 400 THEN 3
                    ELSE 4
                END as level
            FROM crowd_history 
            WHERE (location, timestamp) IN (
                SELECT location, MAX(timestamp) 
                FROM crowd_history 
                GROUP BY location
            )
            ORDER BY count DESC
        """)
        
        conditions = cursor.fetchall()
        
        # Location coordinates
        location_coords = {
            "DPR": {"latitude": -6.2088, "longitude": 106.8456},
            "Patung Kuda": {"latitude": -6.1751, "longitude": 106.865},
            "Bundaran HI": {"latitude": -6.1944, "longitude": 106.8229},
            "Monas": {"latitude": -6.1751, "longitude": 106.865},
            "GBK": {"latitude": -6.2297, "longitude": 106.6894},
            "Istana Negara": {"latitude": -6.1751, "longitude": 106.865},
            "Bundaran Senayan": {"latitude": -6.2297, "longitude": 106.6894},
            "Mabes Polri": {"latitude": -6.1751, "longitude": 106.865}
        }
        
        # Add coordinates
        for condition in conditions:
            location_name = condition['location']
            if location_name in location_coords:
                condition['latitude'] = location_coords[location_name]['latitude']
                condition['longitude'] = location_coords[location_name]['longitude']
            else:
                condition['latitude'] = None
                condition['longitude'] = None
        
        return {
            "conditions": conditions,
            "total_locations": len(conditions),
            "timestamp": datetime.now().isoformat()
        }
        
    except Error as e:
        return {"error": str(e)}
    finally:
        cursor.close()
        conn.close()

@app.get("/crowd/stats")
async def get_crowd_statistics():
    """Get comprehensive crowd statistics"""
    conn = get_db_connection()
    if not conn:
        return {"error": "Database connection failed"}
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Overall statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as total_records,
                SUM(count) as total_crowd_all_time,
                AVG(count) as avg_crowd_all_time,
                MIN(count) as min_crowd_all_time,
                MAX(count) as max_crowd_all_time,
                COUNT(DISTINCT location) as total_locations,
                MIN(timestamp) as earliest_record,
                MAX(timestamp) as latest_record
            FROM crowd_history
        """)
        
        overall_stats = cursor.fetchone()
        
        # Today's statistics
        today = date.today()
        cursor.execute("""
            SELECT 
                COUNT(*) as records_today,
                SUM(count) as total_crowd_today,
                AVG(count) as avg_crowd_today,
                MIN(count) as min_crowd_today,
                MAX(count) as max_crowd_today
            FROM crowd_history 
            WHERE DATE(timestamp) = %s
        """, (today,))
        
        today_stats = cursor.fetchone()
        
        # Location-wise statistics
        cursor.execute("""
            SELECT 
                location,
                COUNT(*) as total_records,
                SUM(count) as total_crowd,
                AVG(count) as avg_crowd,
                MIN(count) as min_crowd,
                MAX(count) as max_crowd,
                MAX(timestamp) as last_updated
            FROM crowd_history 
            GROUP BY location
            ORDER BY total_crowd DESC
        """)
        
        location_stats = cursor.fetchall()
        
        return {
            "overall": overall_stats,
            "today": today_stats,
            "locations": location_stats,
            "generated_at": datetime.now().isoformat()
        }
        
    except Error as e:
        return {"error": str(e)}
    finally:
        cursor.close()
        conn.close()

@app.get("/db/health")
async def check_db_connection():
    """Check database connection status"""
    conn = get_db_connection()
    if not conn:
        return {
            "status": "error",
            "message": "Database connection failed",
            "connected": False
        }
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM crowd_history")
        record_count = cursor.fetchone()[0]
        
        return {
            "status": "success",
            "message": "Database connected",
            "connected": True,
            "database": "crowd_monitoring",
            "version": version,
            "total_records": record_count
        }
    except Error as e:
        return {
            "status": "error",
            "message": f"Database error: {str(e)}",
            "connected": False
        }
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
