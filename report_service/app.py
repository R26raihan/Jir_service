from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional, List
from io import BytesIO
import os
import json
import tempfile
from pathlib import Path
import mysql.connector
from mysql.connector import Error
from pydantic import BaseModel

try:
    # Preferred: PaddleOCR (no external binary)
    from paddleocr import PaddleOCR  # type: ignore
except Exception:  # pragma: no cover
    PaddleOCR = None

try:
    import easyocr  # type: ignore
except Exception:  # pragma: no cover
    easyocr = None

try:
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None

try:
    import pytesseract
except Exception:  # pragma: no cover
    pytesseract = None

app = FastAPI()

# CORS (allow local dev origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for form validation
class ReportForm(BaseModel):
    report_type: str
    title: str
    description: Optional[str] = None
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    reporter_name: Optional[str] = None
    reporter_phone: Optional[str] = None
    reporter_email: Optional[str] = None
    urgency: str = "sedang"


OCR_ENGINE = {
    "name": None,
    "instance": None
}
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Raihan26",
            database="report_service",
        )
        return connection
    except Error as e:
        print(f"[DB ERROR] {e}")
        return None



@app.on_event("startup")
def load_ocr_engine():
    """Initialize OCR engine (PaddleOCR if available, else Tesseract)."""
    if PaddleOCR is not None:
        try:
            # 'latin' covers Indonesian characters reasonably well
            OCR_ENGINE["instance"] = PaddleOCR(use_angle_cls=True, lang="latin")
            OCR_ENGINE["name"] = "paddleocr"
            return
        except Exception:
            OCR_ENGINE["instance"] = None
    # Try EasyOCR
    if easyocr is not None:
        try:
            OCR_ENGINE["instance"] = easyocr.Reader(["en", "id"], gpu=False)
            OCR_ENGINE["name"] = "easyocr"
            return
        except Exception:
            OCR_ENGINE["instance"] = None
    # Fallback to Tesseract if available
    if pytesseract is not None and Image is not None:
        OCR_ENGINE["name"] = "tesseract"
        OCR_ENGINE["instance"] = True  # marker
    else:
        OCR_ENGINE["name"] = None
        OCR_ENGINE["instance"] = None


## Simplified service: only /ocr endpoint is exposed


def run_ocr_on_bytes(image_bytes: bytes, lang: str = "latin"):
    # Prefer PaddleOCR if loaded
    if OCR_ENGINE["name"] == "paddleocr":
        try:
            ocr = OCR_ENGINE["instance"]
            result = ocr.ocr(image_bytes, cls=True)
            words = []
            texts = []
            # result is list per image; we passed bytes so single image
            for line in (result[0] or []):
                bbox, (txt, conf) = line
                texts.append(txt)
                # bbox is 4 points [[x,y], ...]
                xs = [p[0] for p in bbox]
                ys = [p[1] for p in bbox]
                left, top = min(xs), min(ys)
                width, height = max(xs) - left, max(ys) - top
                words.append({
                    "text": txt,
                    "conf": conf,
                    "bbox": {"left": left, "top": top, "width": width, "height": height}
                })
            return "\n".join(texts), words
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"OCR failed (paddleocr): {e}")

    # EasyOCR path
    if OCR_ENGINE["name"] == "easyocr":
        try:
            reader = OCR_ENGINE["instance"]
            # easyocr expects numpy array or file path; pass bytes via PIL
            if Image is None:
                raise HTTPException(status_code=500, detail="Pillow (PIL) not available for EasyOCR path")
            img = Image.open(BytesIO(image_bytes)).convert("RGB")
            import numpy as np  # local import to avoid hard dep if unused
            arr = np.array(img)
            result = reader.readtext(arr)  # list of [bbox, text, conf]
            texts = []
            words = []
            for bbox, txt, conf in result:
                texts.append(txt)
                xs = [p[0] for p in bbox]
                ys = [p[1] for p in bbox]
                left, top = min(xs), min(ys)
                width, height = max(xs) - left, max(ys) - top
                words.append({
                    "text": txt,
                    "conf": conf,
                    "bbox": {"left": left, "top": top, "width": width, "height": height}
                })
            return "\n".join(texts), words
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"OCR failed (easyocr): {e}")

    # Fallback to Tesseract if available
    if OCR_ENGINE["name"] == "tesseract":
        if Image is None or pytesseract is None:
            raise HTTPException(status_code=500, detail="Tesseract/Pillow not available")
        try:
            img = Image.open(BytesIO(image_bytes))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid image: {e}")
        try:
            img = img.convert("L")
        except Exception:
            pass
        try:
            text = pytesseract.image_to_string(img, lang=lang or "eng")
            data = pytesseract.image_to_data(img, lang=lang or "eng", output_type=pytesseract.Output.DICT)
            words = []
            n = len(data.get('text', []))
            for i in range(n):
                w = data['text'][i]
                if not w or not w.strip():
                    continue
                words.append({
                    "text": w,
                    "conf": data.get('conf', [None])[i],
                    "bbox": {
                        "left": data.get('left', [None])[i],
                        "top": data.get('top', [None])[i],
                        "width": data.get('width', [None])[i],
                        "height": data.get('height', [None])[i],
                    }
                })
            return text, words
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"OCR failed (tesseract): {e}")

    raise HTTPException(status_code=500, detail="No OCR engine available. Install paddleocr or tesseract.")


@app.post("/ocr")
async def ocr_final(file: UploadFile = File(...), lang: Optional[str] = "latin"):
    """Upload dokumen (PDF/PNG/JPG/WebP) dan kembalikan hasil ringkas: message, lokasi, lat, long."""
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    # Save to temp files (handle image or PDF pages) and use existing pipeline from test_ocr.py
    try:
        # reuse pipeline (OCR -> LLM -> geocode)
        try:
            from .test_ocr import run_ocr_for
        except Exception:
            from test_ocr import run_ocr_for

        def _pdf_bytes_to_image_paths(pdf_bytes: bytes) -> List[Path]:
            paths: List[Path] = []
            # Try PyMuPDF (fitz)
            try:
                import fitz  # type: ignore
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                for page_idx in range(min(len(doc), 3)):  # limit first 3 pages
                    page = doc.load_page(page_idx)
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x scale for quality
                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                        tmp_path = Path(tmp.name)
                        tmp.write(pix.tobytes())
                        paths.append(tmp_path)
                doc.close()
                return paths
            except Exception:
                pass
            # Try pdf2image
            try:
                from pdf2image import convert_from_bytes  # type: ignore
                images = convert_from_bytes(pdf_bytes, fmt="png", dpi=200, first_page=1, last_page=3)
                for img in images:
                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                        tmp_path = Path(tmp.name)
                        img.save(tmp_path, format="PNG")
                        paths.append(tmp_path)
                return paths
            except Exception:
                return []

        temp_paths: List[Path] = []
        ctype = (file.content_type or "").lower()
        name = (file.filename or "").lower()
        is_pdf = ctype == "application/pdf" or name.endswith(".pdf")
        if is_pdf:
            temp_paths = _pdf_bytes_to_image_paths(content)
            if not temp_paths:
                raise HTTPException(status_code=415, detail="Cannot convert PDF to images (install PyMuPDF or pdf2image)")
        else:
            with tempfile.NamedTemporaryFile(suffix=os.path.splitext(name)[1] or ".png", delete=False) as tmp:
                tmp_path = Path(tmp.name)
                tmp.write(content)
                temp_paths = [tmp_path]

        # Run OCR on pages, pick best (longest text)
        results = []
        try:
            for p in temp_paths:
                try:
                    results.append(run_ocr_for(p))
                except Exception:
                    continue
        finally:
            for p in temp_paths:
                try:
                    p.unlink(missing_ok=True)
                except Exception:
                    pass

        if not results:
            raise HTTPException(status_code=500, detail="OCR failed for all pages")

        result = max(results, key=lambda r: (r.get("length") or 0))

        # Build minimal object
        geocoding = (result.get("geocoding") or {})
        primary = (geocoding.get("primary") or {}) if isinstance(geocoding, dict) else {}
        llm = (result.get("llm") or {})
        llm_output = (llm.get("output") or {}) if isinstance(llm, dict) else {}
        lokasi = None
        if isinstance(llm_output, dict):
            lb = llm_output.get("lokasi_banjir") or {}
            if isinstance(lb, dict):
                lokasi = lb.get("nama")
        if not lokasi:
            cand = (llm_output.get("normalized_query_candidates") if isinstance(llm_output, dict) else None) or []
            if isinstance(cand, list) and cand:
                lokasi = str(cand[0])
            elif isinstance(primary, dict):
                lokasi = primary.get("display_name")
        message = (llm_output.get("ringkasan") if isinstance(llm_output, dict) else None) or ""

        minimal = [{
            "message": message,
            "lokasi": lokasi or "",
            "lat": primary.get("lat") if isinstance(primary, dict) else None,
            "long": primary.get("lon") if isinstance(primary, dict) else None,
        }]

        # Persist to DB (best-effort)
        try:
            conn = get_db_connection()
            if conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO ocr_results (message, lokasi, latitude, longitude, source_file, engine)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        message,
                        lokasi,
                        (primary.get("lat") if isinstance(primary, dict) else None),
                        (primary.get("lon") if isinstance(primary, dict) else None),
                        file.filename,
                        (OCR_ENGINE.get("name") or "unknown"),
                    ),
                )
                conn.commit()
                cur.close()
                conn.close()
        except Exception as _:
            pass

        return JSONResponse(minimal)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR pipeline failed: {e}")

@app.get("/")
async def root():
    return {"service": "report", "status": "ok", "ocr_engine": OCR_ENGINE.get("name")}


@app.get("/db/health")
async def db_health():
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1")
        row = cur.fetchone()
        return {"status": "ok", "db": "connected", "result": row[0] if row else None}
    except Error as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass

@app.get("/ocr/results")
async def list_ocr_results(limit: int = 50, lokasi: Optional[str] = None):
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    try:
        cur = conn.cursor(dictionary=True)
        if lokasi:
            cur.execute(
                """
                SELECT id, message, lokasi, latitude, longitude, source_file, engine, created_at
                FROM ocr_results
                WHERE lokasi LIKE %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (f"%{lokasi}%", int(limit)),
            )
        else:
            cur.execute(
                """
                SELECT id, message, lokasi, latitude, longitude, source_file, engine, created_at
                FROM ocr_results
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (int(limit),),
            )
        rows = cur.fetchall()
        return {"status": "success", "count": len(rows), "data": rows}
    except Error as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass


@app.get("/ocr/results/{result_id}")
async def get_ocr_result(result_id: int):
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT id, message, lokasi, latitude, longitude, source_file, engine, created_at
            FROM ocr_results
            WHERE id = %s
            """,
            (int(result_id),),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Not found")
        return row
    except Error as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass


@app.delete("/ocr/results/{result_id}")
async def delete_ocr_result(result_id: int):
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    try:
        cur = conn.cursor()
        cur.execute(
            """
            DELETE FROM ocr_results
            WHERE id = %s
            """,
            (int(result_id),),
        )
        if cur.rowcount == 0:
            conn.rollback()
            raise HTTPException(status_code=404, detail="Not found")
        conn.commit()
        return {"status": "success", "deleted_id": int(result_id)}
    except Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass


# Report form submission endpoint
@app.post("/reports")
async def submit_report(
    report_type: str = Form(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    reporter_name: Optional[str] = Form(None),
    reporter_phone: Optional[str] = Form(None),
    reporter_email: Optional[str] = Form(None),
    urgency: str = Form("sedang"),
    evidence_files: List[UploadFile] = File([])
):
    """Submit a form-based report with optional evidence files."""
    
    # Validate report type
    valid_types = ['banjir', 'kebakaran', 'pohon_tumbang', 'kecelakaan', 'lainnya']
    if report_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid report type. Must be one of: {valid_types}")
    
    # Validate urgency
    valid_urgency = ['rendah', 'sedang', 'tinggi', 'darurat']
    if urgency not in valid_urgency:
        raise HTTPException(status_code=400, detail=f"Invalid urgency. Must be one of: {valid_urgency}")
    
    # Process evidence files
    evidence_file_names = []
    if evidence_files:
        # Create uploads directory if it doesn't exist
        upload_dir = Path("uploads")
        upload_dir.mkdir(exist_ok=True)
        
        import time
        import random
        
        for file in evidence_files:
            if file.filename and file.filename.strip():
                try:
                    # Generate unique filename
                    file_extension = Path(file.filename).suffix
                    timestamp = int(time.time())
                    random_num = random.randint(1000, 9999)
                    unique_filename = f"{report_type}_{timestamp}_{random_num}{file_extension}"
                    file_path = upload_dir / unique_filename
                    
                    # Save file
                    content = await file.read()
                    if content:  # Only save if content is not empty
                        with open(file_path, "wb") as f:
                            f.write(content)
                        evidence_file_names.append(unique_filename)
                except Exception as e:
                    print(f"Error processing file {file.filename}: {e}")
                    continue
    
    # Save to database
    try:
        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO reports (report_type, title, description, location, latitude, longitude, 
                               reporter_name, reporter_phone, reporter_email, urgency, evidence_files)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                report_type,
                title,
                description,
                location,
                latitude,
                longitude,
                reporter_name,
                reporter_phone,
                reporter_email,
                urgency,
                json.dumps(evidence_file_names) if evidence_file_names else None
            )
        )
        report_id = cur.lastrowid
        conn.commit()
        cur.close()
        conn.close()
        
        return JSONResponse({
            "status": "success",
            "message": "Report submitted successfully",
            "report_id": report_id,
            "evidence_files": evidence_file_names
        })
        
    except Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error submitting report: {str(e)}")


# Get all reports
@app.get("/reports")
async def get_reports(
    limit: int = 50,
    report_type: Optional[str] = None,
    status: Optional[str] = None,
    urgency: Optional[str] = None
):
    """Get reports with optional filtering."""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        cur = conn.cursor(dictionary=True)
        
        # Build query with filters
        query = """
            SELECT id, report_type, title, description, location, latitude, longitude,
                   reporter_name, reporter_phone, reporter_email, urgency, status,
                   evidence_files, created_at, updated_at
            FROM reports
            WHERE 1=1
        """
        params = []
        
        if report_type:
            query += " AND report_type = %s"
            params.append(report_type)
        
        if status:
            query += " AND status = %s"
            params.append(status)
            
        if urgency:
            query += " AND urgency = %s"
            params.append(urgency)
        
        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(int(limit))
        
        cur.execute(query, params)
        rows = cur.fetchall()
        
        # Parse evidence_files JSON
        for row in rows:
            if row['evidence_files']:
                try:
                    row['evidence_files'] = json.loads(row['evidence_files'])
                except:
                    row['evidence_files'] = []
            else:
                row['evidence_files'] = []
        
        return {"status": "success", "count": len(rows), "data": rows}
        
    except Error as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass


# Get single report
@app.get("/reports/{report_id}")
async def get_report(report_id: int):
    """Get a single report by ID."""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT id, report_type, title, description, location, latitude, longitude,
                   reporter_name, reporter_phone, reporter_email, urgency, status,
                   evidence_files, created_at, updated_at
            FROM reports
            WHERE id = %s
            """,
            (int(report_id),)
        )
        row = cur.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Report not found")
        
        # Parse evidence_files JSON
        if row['evidence_files']:
            try:
                row['evidence_files'] = json.loads(row['evidence_files'])
            except:
                row['evidence_files'] = []
        else:
            row['evidence_files'] = []
        
        return row
        
    except Error as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass


# Update report status
@app.patch("/reports/{report_id}/status")
async def update_report_status(
    report_id: int,
    status: str = Form(...)
):
    """Update report status."""
    valid_statuses = ['dilaporkan', 'diproses', 'selesai', 'ditolak']
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
    
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE reports 
            SET status = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (status, int(report_id))
        )
        
        if cur.rowcount == 0:
            conn.rollback()
            raise HTTPException(status_code=404, detail="Report not found")
        
        conn.commit()
        return {"status": "success", "message": f"Report status updated to {status}"}
        
    except Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass


# Delete report
@app.delete("/reports/{report_id}")
async def delete_report(report_id: int):
    """Delete a report."""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        cur = conn.cursor()
        cur.execute(
            """
            DELETE FROM reports
            WHERE id = %s
            """,
            (int(report_id),)
        )
        
        if cur.rowcount == 0:
            conn.rollback()
            raise HTTPException(status_code=404, detail="Report not found")
        
        conn.commit()
        return {"status": "success", "message": "Report deleted successfully"}
        
    except Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass
