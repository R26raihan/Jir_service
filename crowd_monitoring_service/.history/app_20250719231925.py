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
import threading
from fastapi import FastAPI
from datetime import datetime

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

# === CCTV dan ROI ===
cctv_urls = {
    "DPR": "https://cctv.balitower.co.id/Bendungan-Hilir-003-700014_1/embed.html",
    "Patung Kuda": "https://cctv.balitower.co.id/JPO-Merdeka-Barat-507357_9/embed.html",
}

roi_polygons = {
    "Patung Kuda": np.array([[224, 675], [392, 383], [644, 377], [970, 671]], dtype=np.int32),
    "DPR": np.array([[7, 346], [1067, 375], [1070, 513], [5, 454]], dtype=np.int32),
}

chrome_driver_path = r"C:\Gemastik 2025!!\chromedriver-win64\chromedriver.exe"
driver_service = Service(chrome_driver_path)

# === Data hasil terakhir ===
crowd_data = {}  # contoh: {"DPR": {"count": 58, "timestamp": "2025-07-19 20:00:00"}}

# === Fungsi monitoring background ===
def monitor_loop(location: str, interval: int = 10):
    roi_polygon = roi_polygons.get(location)
    url = cctv_urls.get(location)
    if not url:
        print(f"[ERROR] Tidak ada URL untuk lokasi {location}")
        return

    while True:
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

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            crowd_data[location] = {
                "count": count,
                "timestamp": timestamp
            }

        except Exception as e:
            print(f"[ERROR] {location}: {e}")
        finally:
            try:
                driver.quit()
            except:
                pass

        time.sleep(interval)

# === Jalankan thread background untuk setiap lokasi ===
for loc in cctv_urls:
    threading.Thread(target=monitor_loop, args=(loc,), daemon=True).start()

# === Endpoint GET hasil seluruh lokasi ===
@app.get("/crowd")
async def get_all_crowd_data():
    return crowd_data
