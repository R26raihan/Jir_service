import cv2
import torch
from torchvision import transforms
from model import CSRNet
from PIL import Image
import numpy as np
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
import time
import os
import tempfile
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel

# === Setup FastAPI ===
app = FastAPI()

# === Setup device & model ===
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

def load_model():
    model = CSRNet().to(device)
    weights_path = r"C:\Gemastik 2025!!\model\weights.pth"
    checkpoint = torch.load(weights_path, map_location=device)
    model.load_state_dict(checkpoint)
    model.eval()
    return model

model = load_model()

# === Konfigurasi URL CCTV dan ROI ===
cctv_urls = {
    "DPR": "https://cctv.balitower.co.id/Bendungan-Hilir-003-700014_1/embed.html",
    "Patung Kuda": "https://cctv.balitower.co.id/JPO-Merdeka-Barat-507357_9/embed.html",
}

roi_polygons = {
    "Patung Kuda": np.array([[224, 675], [392, 383], [644, 377], [970, 671]], dtype=np.int32),
    "DPR": np.array([[7, 346], [1067, 375], [1070, 513], [5, 454]], dtype=np.int32),
    "default": None
}

chrome_driver_path = r"C:\Gemastik 2025!!\chromedriver-win64\chromedriver.exe"
driver_service = Service(chrome_driver_path)

# === Fungsi utama ===
async def capture_and_predict(location: str):
    roi_polygon = roi_polygons.get(location, roi_polygons["default"])
    url = cctv_urls.get(location)
    if not url:
        return {"error": f"Lokasi '{location}' tidak ditemukan."}

    try:
        driver = webdriver.Chrome(service=driver_service)
        driver.get(url)
        time.sleep(5)

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmpfile:
            screenshot_path = tmpfile.name
            driver.save_screenshot(screenshot_path)

        frame = cv2.imread(screenshot_path)
        frame = cv2.resize(frame, (1080, 720))
        os.remove(screenshot_path)

        display_frame = frame.copy()

        if roi_polygon is not None:
            mask = np.zeros_like(frame[:, :, 0])
            cv2.fillPoly(mask, [roi_polygon], 255)
            roi_frame = cv2.bitwise_and(frame, frame, mask=mask)

            overlay = display_frame.copy()
            cv2.fillPoly(overlay, [roi_polygon], color=(0, 255, 0))
            cv2.addWeighted(overlay, 0.3, display_frame, 0.7, 0, display_frame)
            cv2.polylines(display_frame, [roi_polygon], isClosed=True, color=(0, 255, 0), thickness=2)
        else:
            roi_frame = frame

        # Prediksi
        pil_img = Image.fromarray(cv2.cvtColor(roi_frame, cv2.COLOR_BGR2RGB))
        img_tensor = transform(pil_img).unsqueeze(0).to(device)
        with torch.no_grad():
            output = model(img_tensor)
        count = int(output.sum().item())

        # Simpan hasil prediksi
        result_path = f"hasil_prediksi_{location}.jpg"
        cv2.putText(display_frame, f"Prediksi: {count} orang", (30, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
        cv2.imwrite(result_path, display_frame)

        return {"count": count, "image_path": result_path, "roi_coordinates": roi_polygon.tolist() if roi_polygon is not None else None}

    except Exception as e:
        return {"error": f"Gagal mengambil gambar: {str(e)}"}
    finally:
        if driver:
            driver.quit()

# === Endpoint API ===
class LocationRequest(BaseModel):
    location: str

@app.get("/locations")
async def get_locations():
    return {"locations": list(cctv_urls.keys())}

@app.post("/predict")
async def predict_crowd(request: LocationRequest):
    result = await capture_and_predict(request.location)
    if "error" in result:
        return result
    return {
        "location": request.location,
        "count": result["count"],
        "roi_coordinates": result["roi_coordinates"],
        "image_url": f"/image/{request.location}"
    }

@app.get("/image/{location}")
async def get_image(location: str):
    result_path = f"hasil_prediksi_{location}.jpg"
    if os.path.exists(result_path):
        return FileResponse(result_path)
    return {"error": "Gambar tidak ditemukan."}