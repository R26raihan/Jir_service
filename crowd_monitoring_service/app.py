import cv2
import torch
from torchvision import transforms
from model.model import CSRNet
from PIL import Image
import numpy as np
# Selenium imports removed - using local video instead of CCTV
import time
import os
import tempfile
import threading
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import base64
import io
import mysql.connector
from mysql.connector import Error
import requests
import json

app = FastAPI()

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

def send_notification(title: str, body: str, data: dict = None):
    """Send push notification via notification service"""
    try:
        notification_url = "http://localhost:8006/api/notification/admin/push"
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": "admin123"  # Replace with your actual admin API key
        }
        
        payload = {
            "title": title,
            "body": body,
            "data": data or {}
        }
        
        response = requests.post(notification_url, headers=headers, json=payload, timeout=5)
        if response.status_code == 200:
            print(f"[NOTIFICATION] Sent: {title}")
        else:
            print(f"[NOTIFICATION ERROR] Failed to send: {response.status_code}")
    except Exception as e:
        print(f"[NOTIFICATION ERROR] {e}")

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

def load_model():
    model = CSRNet().to(device)
    weights_path = r"/Users/raihansetiawan/JIR_service/crowd_monitoring_service/model/weights.pth"
    checkpoint = torch.load(weights_path, map_location=device)
    model.load_state_dict(checkpoint)
    model.eval()
    return model

model = load_model()

# CCTV URLs disabled - using local video instead
# cctv_urls = {
#     "DPR": "https://cctv.balitower.co.id/Bendungan-Hilir-003-700014_1/embed.html",
#     "Patung Kuda": "https://cctv.balitower.co.id/JPO-Merdeka-Barat-507357_9/embed.html",
# }

# Using local video file instead of CCTV
video_file_path = "/Users/raihansetiawan/backend_JIR/0918(1).mp4"

roi_polygons = {
    "Patung Kuda": np.array([[224, 675], [392, 383], [644, 377], [970, 671]], dtype=np.int32),
    "DPR": np.array([[7, 346], [1067, 375], [1070, 513], [5, 454]], dtype=np.int32),
}

# Driver service removed - using local video instead of selenium

crowd_data = {}
density_maps = {}

def save_to_mysql(location: str, count: int, timestamp: str):
    conn = get_db_connection()
    if not conn:
        print(f"[DB ERROR] Tidak bisa connect ke database untuk {location}")
        return
    
    try:
        cursor = conn.cursor()
        query = """
            INSERT INTO crowd_history (location, count, timestamp)
            VALUES (%s, %s, %s)
        """
        cursor.execute(query, (location, count, timestamp))
        conn.commit()
        print(f"[DB SUCCESS] Data tersimpan: {location} - {count} orang pada {timestamp}")
    except Error as e:
        print(f"[DB ERROR] Gagal menyimpan data untuk {location}: {e}")
    finally:
        cursor.close()
        conn.close()

def monitor_loop(location: str, interval: int = 10):
    roi_polygon = roi_polygons.get(location)
    
    # Check if video file exists
    if not os.path.exists(video_file_path):
        print(f"[ERROR] Video file tidak ditemukan: {video_file_path}")
        return

    # Open video file
    cap = cv2.VideoCapture(video_file_path)
    if not cap.isOpened():
        print(f"[ERROR] Tidak bisa membuka video file: {video_file_path}")
        return

    frame_count = 0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    while True:
        try:
            # Read frame from video
            ret, frame = cap.read()
            if not ret:
                # If video ended, restart from beginning
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = cap.read()
                if not ret:
                    print(f"[ERROR] Tidak bisa membaca frame dari video")
                    break
            
            frame_count += 1
            frame = cv2.resize(frame, (1080, 720))

            if roi_polygon is not None:
                mask = np.zeros_like(frame[:, :, 0])
                cv2.fillPoly(mask, [roi_polygon], 255)
                roi_frame = cv2.bitwise_and(frame, frame, mask=mask)
            else:
                roi_frame = frame

            pil_img = Image.fromarray(cv2.cvtColor(roi_frame, cv2.COLOR_BGR2RGB))
            img_tensor = transform(pil_img).unsqueeze(0).to(device)

            with torch.no_grad():
                output = model(img_tensor)
            count = int(output.sum().item())


            output_np = output.squeeze().cpu().numpy()
            density_map_img = (output_np / output_np.max()) * 255 if output_np.max() > 0 else output_np
            density_map_img = density_map_img.astype(np.uint8)
            pil_density = Image.fromarray(density_map_img)


            buffer = io.BytesIO()
            pil_density.save(buffer, format="PNG")
            base64_img = base64.b64encode(buffer.getvalue()).decode("utf-8")
            density_maps[location] = base64_img


            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            crowd_data[location] = {
                "count": count,
                "timestamp": timestamp
            }

            print(f"[{timestamp}] {location}: {count} orang")
            save_to_mysql(location, count, timestamp)
            
            # Send notification for high crowd levels
            if count > 300:  # Padat level
                send_notification(
                    title="🚨 Kerumunan Padat Terdeteksi!",
                    body=f"Lokasi {location} memiliki {count} orang. Kondisi: PADAT",
                    data={
                        "location": location,
                        "count": count,
                        "level": "padat",
                        "timestamp": timestamp,
                        "service": "crowd_monitoring"
                    }
                )
            elif count > 200:  # Ramai level
                send_notification(
                    title="⚠️ Kerumunan Ramai Terdeteksi",
                    body=f"Lokasi {location} memiliki {count} orang. Kondisi: RAMAI",
                    data={
                        "location": location,
                        "count": count,
                        "level": "ramai",
                        "timestamp": timestamp,
                        "service": "crowd_monitoring"
                    }
                )

        except Exception as e:
            print(f"[ERROR] {location}: {e}")
        
        time.sleep(interval)

# Start monitoring for each location using the same video file
locations = ["DPR", "Patung Kuda"]
for loc in locations:
    threading.Thread(target=monitor_loop, args=(loc,), daemon=True).start()

@app.get("/")
async def health_check():
    return {"service": "crowd", "status": "ok"}

@app.get("/health")
async def health_check_alt():
    return {"service": "crowd", "status": "ok"}

@app.get("/crowd")
async def get_all_crowd_data():
    return crowd_data

@app.get("/crowd/history")
async def get_crowd_history():
    conn = get_db_connection()
    if not conn:
        return {"error": "Database connection failed"}
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT location, count, timestamp 
            FROM crowd_history 
            ORDER BY timestamp DESC 
            LIMIT 5000
        """)
        result = cursor.fetchall()

        def classify_status(n: int):

            if n is None:
                return {"status": "tidak diketahui", "level": 0}
            try:
                v = int(n)
            except Exception:
                v = 0
            if v <= 100:
                return {"status": "ringan", "level": 1}
            if v <= 200:
                return {"status": "sedang", "level": 2}
            if v <= 400:
                return {"status": "ramai", "level": 3}
            return {"status": "padat", "level": 4}


        enriched = []
        for row in result:
            cls = classify_status(row.get("count"))
            row["status"] = cls["status"]
            row["level"] = cls["level"]
            enriched.append(row)

        return {"history": enriched, "count": len(enriched)}
    except Error as e:
        return {"error": str(e)}
    finally:
        cursor.close()
        conn.close()

@app.get("/crowd/densitymap")
async def get_density_map(location: str = Query(..., description="Nama lokasi")):
    if location not in density_maps:
        return JSONResponse(status_code=404, content={"error": "Density map belum tersedia"})
    
    return {
        "location": location,
        "density_map_base64": density_maps[location]
    }

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

@app.get("/db/info")
async def get_db_info():
    """Get detailed database information"""
    conn = get_db_connection()
    if not conn:
        return {"error": "Database connection failed"}
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Get table info
        cursor.execute("SHOW TABLES")
        tables = [row[f"Tables_in_crowd_monitoring"] for row in cursor.fetchall()]
        
        # Get crowd_history table structure
        cursor.execute("DESCRIBE crowd_history")
        table_structure = cursor.fetchall()
        
        # Get recent data sample
        cursor.execute("""
            SELECT location, count, timestamp 
            FROM crowd_history 
            ORDER BY timestamp DESC 
            LIMIT 5
        """)
        recent_data = cursor.fetchall()
        
        # Get statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as total_records,
                MIN(timestamp) as earliest_record,
                MAX(timestamp) as latest_record,
                AVG(count) as avg_count,
                MIN(count) as min_count,
                MAX(count) as max_count
            FROM crowd_history
        """)
        stats = cursor.fetchone()
        
        return {
            "database": "crowd_monitoring",
            "tables": tables,
            "table_structure": table_structure,
            "recent_data": recent_data,
            "statistics": stats
        }
    except Error as e:
        return {"error": str(e)}
    finally:
        cursor.close()
        conn.close()

