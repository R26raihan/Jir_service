from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import mysql.connector
from mysql.connector import Error
from typing import List, Optional
from datetime import datetime, date

app = FastAPI()

# === Izinkan semua domain untuk akses API ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # semua domain diperbolehkan
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Data models ===
class MobilityData(BaseModel):
    user_id: str
    latitude: float
    longitude: float
    dest_latitude: float
    dest_longitude: float

class UserData(BaseModel):
    user_id: str
    name: str
    email: str
    phone: str

class FavoriteLocation(BaseModel):
    user_id: str
    name: str
    latitude: float
    longitude: float
    address: str
    is_home: bool = False
    is_work: bool = False

# === DB helper ===
def get_connection():
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Raihan26",
            database="user_mobility"
        )
        return connection
    except Error as e:
        print(f"[DB ERROR] {e}")
        return None

# === Cek koneksi database ===
def check_database_connection():
    try:
        connection = get_connection()
        if connection and connection.is_connected():
            cursor = connection.cursor()
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
            cursor.close()
            connection.close()
            return {"status": "success", "message": "Database connected", "version": version[0]}
        else:
            return {"status": "error", "message": "Database connection failed"}
    except Error as e:
        return {"status": "error", "message": f"Database error: {str(e)}"}

# === Root endpoint ===
@app.get("/")
async def root():
    db_status = check_database_connection()
    return {
        "message": "User Mobility Service is running!", 
        "status": "active",
        "database": db_status
    }

# === Cek koneksi database endpoint ===
@app.get("/health")
async def health_check():
    return check_database_connection()

# === POST data user mobility ===
@app.post("/mobility")
def post_mobility(data: MobilityData):
    conn = get_connection()
    if not conn:
        return {"error": "Database connection failed."}
    
    try:
        cursor = conn.cursor()
        query = """
            INSERT INTO mobility (user_id, latitude, longitude, dest_latitude, dest_longitude)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(query, (
            data.user_id,
            data.latitude,
            data.longitude,
            data.dest_latitude,
            data.dest_longitude
        ))
        conn.commit()
        return {"status": "success", "data": data}
    except Error as e:
        return {"error": str(e)}
    finally:
        cursor.close()
        conn.close()

# === GET seluruh data mobilitas ===
@app.get("/mobility")
def get_all_mobility(limit: Optional[int] = 100):
    conn = get_connection()
    if not conn:
        return {"error": "Database connection failed."}
    
    try:
        cursor = conn.cursor(dictionary=True)
        # sanitize and clamp limit
        try:
            safe_limit = int(limit) if limit is not None else 100
        except Exception:
            safe_limit = 100
        if safe_limit < 1:
            safe_limit = 1
        if safe_limit > 1000:
            safe_limit = 1000

        cursor.execute(f"SELECT * FROM mobility ORDER BY timestamp DESC LIMIT {safe_limit}")
        result = cursor.fetchall()
        return {"status": "success", "data": result, "count": len(result)}
    except Error as e:
        return {"error": str(e)}
    finally:
        cursor.close()
        conn.close()

# === GET data mobilitas berdasarkan user_id ===
@app.get("/mobility/{user_id}")
def get_mobility_by_user(user_id: str):
    conn = get_connection()
    if not conn:
        return {"error": "Database connection failed."}
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM mobility WHERE user_id = %s ORDER BY timestamp DESC", (user_id,))
        result = cursor.fetchall()
        return {"status": "success", "data": result, "count": len(result)}
    except Error as e:
        return {"error": str(e)}
    finally:
        cursor.close()
        conn.close()

# === POST user baru ===
@app.post("/users")
def create_user(user: UserData):
    conn = get_connection()
    if not conn:
        return {"error": "Database connection failed."}
    
    try:
        cursor = conn.cursor()
        query = """
            INSERT INTO users (user_id, name, email, phone)
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(query, (user.user_id, user.name, user.email, user.phone))
        conn.commit()
        return {"status": "success", "data": user}
    except Error as e:
        return {"error": str(e)}
    finally:
        cursor.close()
        conn.close()

# === GET semua users ===
@app.get("/users")
def get_all_users():
    conn = get_connection()
    if not conn:
        return {"error": "Database connection failed."}
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
        result = cursor.fetchall()
        return {"status": "success", "data": result, "count": len(result)}
    except Error as e:
        return {"error": str(e)}
    finally:
        cursor.close()
        conn.close()

# === POST favorite location ===
@app.post("/favorites")
def add_favorite_location(location: FavoriteLocation):
    conn = get_connection()
    if not conn:
        return {"error": "Database connection failed."}
    
    try:
        cursor = conn.cursor()
        query = """
            INSERT INTO favorite_locations (user_id, name, latitude, longitude, address, is_home, is_work)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (
            location.user_id,
            location.name,
            location.latitude,
            location.longitude,
            location.address,
            location.is_home,
            location.is_work
        ))
        conn.commit()
        return {"status": "success", "data": location}
    except Error as e:
        return {"error": str(e)}
    finally:
        cursor.close()
        conn.close()

# === GET favorite locations berdasarkan user_id ===
@app.get("/favorites/{user_id}")
def get_favorite_locations(user_id: str):
    conn = get_connection()
    if not conn:
        return {"error": "Database connection failed."}
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM favorite_locations WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
        result = cursor.fetchall()
        return {"status": "success", "data": result, "count": len(result)}
    except Error as e:
        return {"error": str(e)}
    finally:
        cursor.close()
        conn.close()

# === GET statistik mobilitas ===
@app.get("/stats/{user_id}")
def get_mobility_stats(user_id: str, start_date: Optional[str] = None, end_date: Optional[str] = None):
    conn = get_connection()
    if not conn:
        return {"error": "Database connection failed."}
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        if start_date and end_date:
            query = """
                SELECT COUNT(*) as total_trips, 
                       DATE(timestamp) as date
                FROM mobility 
                WHERE user_id = %s AND DATE(timestamp) BETWEEN %s AND %s
                GROUP BY DATE(timestamp)
                ORDER BY date DESC
            """
            cursor.execute(query, (user_id, start_date, end_date))
        else:
            query = """
                SELECT COUNT(*) as total_trips, 
                       DATE(timestamp) as date
                FROM mobility 
                WHERE user_id = %s
                GROUP BY DATE(timestamp)
                ORDER BY date DESC
                LIMIT 30
            """
            cursor.execute(query, (user_id,))
        
        result = cursor.fetchall()
        return {"status": "success", "data": result, "count": len(result)}
    except Error as e:
        return {"error": str(e)}
    finally:
        cursor.close()
        conn.close()

# === GET database info ===
@app.get("/db-info")
def get_database_info():
    conn = get_connection()
    if not conn:
        return {"error": "Database connection failed."}
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Get table counts
        tables = ['users', 'mobility', 'favorite_locations', 'mobility_stats']
        counts = {}
        
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
            result = cursor.fetchone()
            counts[table] = result['count']
        
        # Get database version
        cursor.execute("SELECT VERSION() as version")
        version = cursor.fetchone()
        
        return {
            "status": "success",
            "database": "user_mobility",
            "version": version['version'],
            "table_counts": counts
        }
    except Error as e:
        return {"error": str(e)}
    finally:
        cursor.close()
        conn.close()

# === Test endpoint ===
@app.get("/test")
async def test_endpoint():
    db_status = check_database_connection()
    return {
        "message": "User Mobility Service test endpoint berhasil!",
        "database_status": db_status,
        "available_endpoints": [
            "GET /health - Cek koneksi database",
            "GET /db-info - Info database",
            "POST /mobility - Tambah data mobilitas",
            "GET /mobility - Ambil semua data mobilitas",
            "GET /mobility/{user_id} - Ambil data mobilitas user",
            "POST /users - Tambah user baru",
            "GET /users - Ambil semua users",
            "POST /favorites - Tambah lokasi favorit",
            "GET /favorites/{user_id} - Ambil lokasi favorit user",
            "GET /stats/{user_id} - Statistik mobilitas user"
        ],
        "status": "ready"
    }
