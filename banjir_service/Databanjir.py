from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import time
import re
import mysql.connector
from mysql.connector import Error
from datetime import datetime
from typing import List, Optional
from urllib.request import urlopen
from xml.etree import ElementTree as ET

app = FastAPI()

# === Izinkan semua domain untuk akses API ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # semua domain diperbolehkan
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Database connection ===
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Raihan26",
            database="banjir_monitoring"
        )
        return connection
    except Error as e:
        print(f"[DB ERROR] {e}")
        return None

# Gunakan Chrome driver dari Homebrew (macOS)
chrome_driver_path = "/opt/homebrew/bin/chromedriver"

def get_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    service = Service(chrome_driver_path)
    return webdriver.Chrome(service=service, options=options)


def save_pintu_air_to_db(data_list: List[str]):
    conn = get_db_connection()
    if not conn:
        print("[DB ERROR] Tidak bisa connect ke database untuk pintu air")
        return
    
    try:
        cursor = conn.cursor()
        
        for data in data_list:
            # Parse data pintu air (format: "Nama Pintu Air - Status - Ketinggian Air - Unit")
            if "Pintu Air" in data:
                parts = data.split(" - ")
                if len(parts) >= 3:
                    nama_pintu_air = parts[0].strip()
                    status = parts[1].strip()
                    
                    # Extract ketinggian air dan unit
                    ketinggian_part = parts[2].strip()
                    ketinggian_match = re.search(r'([\d.]+)\s*(\w+)', ketinggian_part)
                    
                    if ketinggian_match:
                        ketinggian_air = float(ketinggian_match.group(1))
                        unit = ketinggian_match.group(2)
                        
                        query = """
                            INSERT INTO pintu_air (nama_pintu_air, status, ketinggian_air, unit)
                            VALUES (%s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE
                                status = VALUES(status),
                                ketinggian_air = VALUES(ketinggian_air),
                                unit = VALUES(unit),
                                timestamp = CURRENT_TIMESTAMP
                        """
                        cursor.execute(query, (nama_pintu_air, status, ketinggian_air, unit))
        
        conn.commit()
        print(f"[DB SUCCESS] Data pintu air tersimpan: {len(data_list)} records")
    except Error as e:
        print(f"[DB ERROR] Gagal menyimpan data pintu air: {e}")
    finally:
        cursor.close()
        conn.close()

def save_rt_terdampak_to_db(data_list: List[dict]):
    conn = get_db_connection()
    if not conn:
        print("[DB ERROR] Tidak bisa connect ke database untuk RT terdampak")
        return
    
    try:
        cursor = conn.cursor()
        
        for data in data_list:
            query = """
                INSERT INTO rt_terdampak (rt, rw, kelurahan, tinggi_genangan, status_banjir)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    tinggi_genangan = VALUES(tinggi_genangan),
                    status_banjir = VALUES(status_banjir),
                    timestamp = CURRENT_TIMESTAMP
            """
            
            # Determine status banjir based on tinggi genangan
            tinggi = data.get("Tinggi Genangan (cm)", 0)
            if tinggi >= 60:
                status_banjir = "berat"
            elif tinggi >= 30:
                status_banjir = "sedang"
            else:
                status_banjir = "ringan"
            
            cursor.execute(query, (
                data.get("RT"),
                data.get("RW"),
                data.get("Kelurahan"),
                tinggi,
                status_banjir
            ))
        
        conn.commit()
        print(f"[DB SUCCESS] Data RT terdampak tersimpan: {len(data_list)} records")
    except Error as e:
        print(f"[DB ERROR] Gagal menyimpan data RT terdampak: {e}")
    finally:
        cursor.close()
        conn.close()


# === Endpoint: Ambil data pintu air dari XML resmi dan ubah ke JSON ===
@app.get("/pintu-air/xml")
def get_pintu_air_from_xml():
    """Ambil XML dari poskobanjir dan ubah ke JSON list of dicts."""
    xml_url = "https://poskobanjir.dsdadki.web.id/xmldata.xml"
    try:
        with urlopen(xml_url, timeout=15) as resp:
            xml_bytes = resp.read()
    except Exception as e:
        return {"status": "error", "message": f"Gagal ambil XML: {e}"}

    try:
        root = ET.fromstring(xml_bytes)
        # Struktur akar: <DocumentElement>
        items = []
        for el in root.findall("SP_GET_LAST_STATUS_PINTU_AIR"):
            def text(tag: str):
                node = el.find(tag)
                return node.text.strip() if node is not None and node.text is not None else None

            item = {
                "id_pintu_air": text("ID_PINTU_AIR"),
                "kode_stasiun": text("KODE_STASIUN"),
                "nama_pintu_air": text("NAMA_PINTU_AIR"),
                "lokasi": text("LOKASI"),
                "sort_number": text("SORT_NUMBER"),
                "siaga1": text("SIAGA1"),
                "siaga2": text("SIAGA2"),
                "siaga3": text("SIAGA3"),
                "siaga4": text("SIAGA4"),
                "latitude": text("LATITUDE"),
                "longitude": text("LONGITUDE"),
                "file_export": text("FILE_EXPORT"),
                "record_status": text("RECORD_STATUS"),
                "created_date": text("CREATED_DATE"),
                "created_by": text("CREATED_BY"),
                "last_updated_date": text("LAST_UPDATED_DATE"),
                "last_updated_by": text("LAST_UPDATED_BY"),
                "tanggal": text("TANGGAL"),
                "tinggi_air": text("TINGGI_AIR"),
                "tinggi_air_sebelumnya": text("TINGGI_AIR_SEBELUMNYA"),
                "status_siaga": text("STATUS_SIAGA"),
                "tma_unaltered": text("TMA_UNALTERED"),
            }
            items.append(item)

        return {"status": "success", "count": len(items), "data": items}
    except Exception as e:
        return {"status": "error", "message": f"Gagal parse XML: {e}"}

@app.get("/rt-terdampak")
def get_rt_terdampak():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    service = Service(chrome_driver_path)
    driver = webdriver.Chrome(service=service, options=options)

    try:
        url = "https://jakartasatu.jakarta.go.id/portal/apps/dashboards/c2b19d6243dd4a2f80fa1e55481fdb11"
        driver.get(url)
        time.sleep(6)

        # Ambil semua div yang mengandung teks "RT"
        div_elements = driver.find_elements(By.XPATH, "//div[contains(text(), 'RT')]")

        data_list = []
        raw_blocks = []

        for div in div_elements:
            text = div.text.strip()
            if not text:
                continue

            raw_blocks.append(text)  # Simpan blok mentah

            lines = text.split("\n")
            for i in range(0, len(lines) - 1):
                lokasi_match = re.search(r"RT (\d+) / RW (\d+), Kelurahan (.+)", lines[i])
                tinggi_match = re.search(r"Tinggi Genangan : ([\d.]+) cm", lines[i + 1])
                if lokasi_match and tinggi_match:
                    data_list.append({
                        "RT": lokasi_match.group(1),
                        "RW": lokasi_match.group(2),
                        "Kelurahan": lokasi_match.group(3),
                        "Tinggi Genangan (cm)": float(tinggi_match.group(1))
                    })

        driver.quit()

        # Simpan ke database
        if data_list:
            save_rt_terdampak_to_db(data_list)

        if not data_list:
            return {
                "status": "success",
                "message": "Tidak ditemukan data RT terdampak banjir",
                "raw_blocks": raw_blocks
            }

        return {"status": "success", "data": data_list}

    except Exception as e:
        driver.quit()
        return {"status": "error", "message": str(e)}


# === Endpoint untuk data pintu air dari database ===
@app.get("/pintu-air/db")
async def get_pintu_air_from_db():
    conn = get_db_connection()
    if not conn:
        return {"error": "Database connection failed"}
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT nama_pintu_air, status, ketinggian_air, unit, timestamp 
            FROM pintu_air 
            ORDER BY timestamp DESC 
            LIMIT 50
        """)
        result = cursor.fetchall()
        return {"status": "success", "data": result, "count": len(result)}
    except Error as e:
        return {"error": str(e)}
    finally:
        cursor.close()
        conn.close()

# === Endpoint untuk data RT terdampak dari database ===
@app.get("/rt-terdampak/db")
async def get_rt_terdampak_from_db():
    conn = get_db_connection()
    if not conn:
        return {"error": "Database connection failed"}
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT rt, rw, kelurahan, tinggi_genangan, status_banjir, timestamp 
            FROM rt_terdampak 
            ORDER BY timestamp DESC 
            LIMIT 100
        """)
        result = cursor.fetchall()
        return {"status": "success", "data": result, "count": len(result)}
    except Error as e:
        return {"error": str(e)}
    finally:
        cursor.close()
        conn.close()


@app.get("/")
async def root():
    db_status = "connected" if get_db_connection() else "disconnected"
    return {
        "message": "Banjir Service is running!", 
        "status": "active",
        "database": db_status
    }


